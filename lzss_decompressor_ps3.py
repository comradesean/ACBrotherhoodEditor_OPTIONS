#!/usr/bin/env python3
"""
LZSS Decompressor for AC Brotherhood PS3 OPTIONS Files
=======================================================

This decompressor handles the PS3-specific format of Assassin's Creed
Brotherhood OPTIONS files, which differs from the PC version in several ways:

PS3-Specific Format Differences:
-------------------------------

1. **8-byte Prefix**:
   - Bytes 0-3: Data size (big-endian) - excludes prefix and padding
   - Bytes 4-7: CRC32 checksum (big-endian)
   - CRC32 params: poly=0x04C11DB7, init=0xBAE23CD0, xorout=0xFFFFFFFF, refin=true, refout=true

2. **4 Sections** (vs 3 on PC):
   - Section 1: Field3=0xC6 (PC uses 0xC5)
   - Section 2: Field3=0x11FACE11 (same as PC)
   - Section 3: Field3=0x21EFFE22 (same as PC)
   - Section 4: Field3=0x07 (PS3-only, controller mappings)

3. **8-byte Gap Marker** between Section 3 and 4:
   - Format: [4-byte size BE] [4-byte type=0x08 BE]
   - Size = Section 4 total size + 4

4. **Header Byte-Swapping**:
   - Fields 0, 1, 2 (offsets 0x00, 0x04, 0x08) are big-endian
   - Fields 3-10 remain little-endian (same as PC)

5. **Footer**: Last byte is 0x54 (vs 0x0C on PC)

6. **Padding**: File padded with zeros to exactly 51,200 bytes (0xC800)

LZSS Format:
-----------
The LZSS compression is identical between PC and PS3 versions.
See lzss_decompressor_pc.py for full LZSS documentation.

Usage:
------
    python lzss_decompressor_ps3.py OPTIONS.PS3        # Decompress all sections
    python lzss_decompressor_ps3.py OPTIONS.PS3 2      # Decompress only section 2
"""

import sys
import os
import struct


# ============================================================================
# CRC32 (PS3 Custom Parameters)
# ============================================================================

def crc32_ps3(data: bytes) -> int:
    """
    Calculate CRC32 using PS3's custom parameters.

    Parameters:
        poly=0x04C11DB7
        init=0xBAE23CD0
        xorout=0xFFFFFFFF
        refin=true (reflect input bytes)
        refout=true (reflect output)

    Args:
        data: Bytes to checksum

    Returns:
        CRC32 checksum as 32-bit integer
    """
    crc = 0xBAE23CD0  # Custom initial value

    for byte in data:
        # Reflect input byte (reverse bits)
        byte = int('{:08b}'.format(byte)[::-1], 2)
        crc ^= (byte << 24)

        for _ in range(8):
            if crc & 0x80000000:
                crc = ((crc << 1) ^ 0x04C11DB7) & 0xFFFFFFFF
            else:
                crc = (crc << 1) & 0xFFFFFFFF

    # Reflect output (reverse all 32 bits)
    crc = int('{:032b}'.format(crc)[::-1], 2)
    # XOR with final value
    return (crc ^ 0xFFFFFFFF) & 0xFFFFFFFF


# ============================================================================
# ADLER-32 CHECKSUM (Zero-Seed Variant - Same as PC)
# ============================================================================

def adler32(data: bytes) -> int:
    """
    Calculate Adler-32 checksum using AC Brotherhood's non-standard variant.

    The game uses Adler-32 with ZERO SEED (s1=0, s2=0) instead of the
    standard Adler-32 seed (s1=1, s2=0).

    Args:
        data: Bytes to checksum

    Returns:
        Adler-32 checksum as 32-bit integer (zero seed variant)
    """
    MOD_ADLER = 65521
    s1 = 0  # NON-STANDARD: standard Adler-32 uses s1=1
    s2 = 0

    for byte in data:
        s1 = (s1 + byte) % MOD_ADLER
        s2 = (s2 + s1) % MOD_ADLER

    return (s2 << 16) | s1


# ============================================================================
# SECTION HEADER
# ============================================================================

class SectionHeader:
    """
    Represents a section header with metadata
    """
    def __init__(self, pattern_offset: int, compressed_length: int,
                 uncompressed_length: int, checksum: int, data_offset: int,
                 field3: int = None):
        self.pattern_offset = pattern_offset
        self.compressed_length = compressed_length
        self.uncompressed_length = uncompressed_length
        self.checksum = checksum
        self.data_offset = data_offset  # Offset where compressed data starts
        self.field3 = field3  # Section identifier (0xC6, 0x11FACE11, etc.)

    def __repr__(self):
        return (f"SectionHeader(pattern_offset=0x{self.pattern_offset:x}, "
                f"compressed={self.compressed_length}, uncompressed={self.uncompressed_length}, "
                f"checksum=0x{self.checksum:08x}, data_offset=0x{self.data_offset:x}, "
                f"field3=0x{self.field3:08x})")


def find_section_headers_ps3(data: bytes, prefix_offset: int = 8) -> list:
    """
    Find and parse section headers in PS3 OPTIONS file.

    PS3 headers have fields 0,1,2 in big-endian format.
    Fields 3-10 remain in little-endian.

    The common pattern (magic bytes) appears at offset 0x10 in each header.

    Args:
        data: Full OPTIONS file data (including 8-byte prefix)
        prefix_offset: Offset where section data starts (after PS3 prefix)

    Returns:
        List of SectionHeader objects
    """
    # The common pattern that appears at offset 0x10 in each header
    COMMON_PATTERN = b'\x33\xAA\xFB\x57\x99\xFA\x04\x10\x01\x00\x02\x00\x80\x00\x00\x01'

    headers = []
    search_pos = prefix_offset

    while True:
        # Find next occurrence of the common pattern
        pattern_pos = data.find(COMMON_PATTERN, search_pos)
        if pattern_pos == -1:
            break

        # The header starts 0x10 bytes before the pattern
        header_start = pattern_pos - 0x10

        # Make sure we have enough bytes for the full header
        if header_start < prefix_offset or header_start + 44 > len(data):
            search_pos = pattern_pos + len(COMMON_PATTERN)
            continue

        # Read header fields
        # PS3: Fields 0,1,2 are big-endian; fields 3-10 are little-endian

        # Read fields 0, 1, 2 as big-endian
        field0 = struct.unpack('>I', data[header_start:header_start+4])[0]
        field1 = struct.unpack('>I', data[header_start+4:header_start+8])[0]
        field2 = struct.unpack('>I', data[header_start+8:header_start+12])[0]

        # Read fields 3-10 as little-endian (same as PC)
        field3_offset = header_start + 12
        field3 = struct.unpack('<I', data[field3_offset:field3_offset+4])[0]  # Uncompressed size

        # After the pattern (at offset 0x20 from header start):
        # - compressed_size (4 bytes LE)
        # - uncompressed_size (4 bytes LE)
        # - checksum (4 bytes LE)
        sizes_offset = pattern_pos + len(COMMON_PATTERN)

        if sizes_offset + 12 > len(data):
            break

        compressed_length = struct.unpack('<I', data[sizes_offset:sizes_offset+4])[0]
        uncompressed_length = struct.unpack('<I', data[sizes_offset+4:sizes_offset+8])[0]
        checksum = struct.unpack('<I', data[sizes_offset+8:sizes_offset+12])[0]

        # Data starts right after the checksum (44-byte header total)
        data_offset = header_start + 44

        header = SectionHeader(
            pattern_offset=pattern_pos,
            compressed_length=compressed_length,
            uncompressed_length=uncompressed_length,
            checksum=checksum,
            data_offset=data_offset,
            field3=field2  # field2 contains the section identifier
        )

        headers.append(header)

        # Continue searching after this pattern
        search_pos = pattern_pos + len(COMMON_PATTERN)

    return headers


# ============================================================================
# LZSS DECOMPRESSOR
# ============================================================================

class LZSSDecompressor:
    """
    LZSS Decompressor matching AC Brotherhood's exact format
    (Identical between PC and PS3 versions)
    """

    def decompress(self, compressed: bytes) -> bytes:
        """
        Decompress LZSS data

        Args:
            compressed: Compressed bytes from OPTIONS file

        Returns:
            Decompressed bytes
        """
        if not compressed:
            return b''

        output = bytearray()
        in_ptr = 0
        flags = 0
        flag_bits = 0

        while in_ptr < len(compressed):
            # Read flag bit
            if flag_bits < 1:
                if in_ptr >= len(compressed):
                    break
                flags = compressed[in_ptr]
                in_ptr += 1
                flag_bits = 8

            flag_bit = flags & 1
            flags >>= 1
            flag_bits -= 1

            if flag_bit == 0:
                # Literal byte
                if in_ptr >= len(compressed):
                    break
                output.append(compressed[in_ptr])
                in_ptr += 1
            else:
                # Match - read second flag bit
                if flag_bits < 1:
                    if in_ptr >= len(compressed):
                        break
                    flags = compressed[in_ptr]
                    in_ptr += 1
                    flag_bits = 8

                flag_bit2 = flags & 1
                flags >>= 1
                flag_bits -= 1

                if flag_bit2 == 0:
                    # Short match (length 2-5, offset 1-256)
                    if flag_bits < 2:
                        if in_ptr >= len(compressed):
                            break
                        flags |= compressed[in_ptr] << flag_bits
                        in_ptr += 1
                        flag_bits += 8

                    length = (flags & 3) + 2
                    flags >>= 2
                    flag_bits -= 2

                    if in_ptr >= len(compressed):
                        break
                    offset_byte = compressed[in_ptr]
                    in_ptr += 1

                    distance = offset_byte + 1
                    src_pos = len(output) - distance

                    for _ in range(length):
                        if src_pos < 0:
                            output.append(0)
                        else:
                            output.append(output[src_pos])
                        src_pos += 1
                else:
                    # Long match (length 3+, offset 0-8191)
                    if in_ptr + 1 >= len(compressed):
                        break

                    byte1 = compressed[in_ptr]
                    byte2 = compressed[in_ptr + 1]
                    in_ptr += 2

                    len_field = byte1 >> 5
                    low_offset = byte1 & 0x1F
                    high_offset = byte2
                    distance = (high_offset << 5) | low_offset

                    # CRITICAL: Check for terminator (distance == 0)
                    if distance == 0:
                        break

                    if len_field == 0:
                        # Variable length encoding
                        length = 9
                        while in_ptr < len(compressed) and compressed[in_ptr] == 0:
                            in_ptr += 1
                            length += 255
                        if in_ptr >= len(compressed):
                            break
                        length += compressed[in_ptr]
                        in_ptr += 1
                    else:
                        length = len_field + 2

                    src_pos = len(output) - distance

                    for _ in range(length):
                        if src_pos < 0:
                            output.append(0)
                        else:
                            output.append(output[src_pos])
                        src_pos += 1

        return bytes(output)


def decompress(data: bytes) -> bytes:
    """
    Convenience function for decompression

    Args:
        data: Compressed bytes

    Returns:
        Decompressed bytes
    """
    decompressor = LZSSDecompressor()
    return decompressor.decompress(data)


# ============================================================================
# PS3 OPTIONS FILE HANDLING
# ============================================================================

def parse_ps3_prefix(data: bytes) -> tuple:
    """
    Parse the 8-byte PS3 prefix.

    Format:
        Bytes 0-3: Data size (big-endian) - size of payload after prefix
        Bytes 4-7: CRC32 (big-endian) - checksum of payload

    Args:
        data: Full PS3 OPTIONS file data

    Returns:
        Tuple of (data_size, crc32, is_valid)
    """
    if len(data) < 8:
        return (0, 0, False)

    data_size = struct.unpack('>I', data[0:4])[0]
    crc32_expected = struct.unpack('>I', data[4:8])[0]

    # Calculate actual CRC32 of payload
    payload = data[8:8 + data_size]
    crc32_actual = crc32_ps3(payload)

    is_valid = (crc32_expected == crc32_actual)

    return (data_size, crc32_expected, crc32_actual, is_valid)


def find_sections_ps3(data: bytes, prefix_offset: int = 8) -> list:
    """
    Find all compressed sections in a PS3 OPTIONS file.

    PS3 files have 4 sections:
    - Sections 1-3: Similar to PC but with big-endian header fields 0-2
    - Section 4: PS3-only controller mappings, preceded by 8-byte gap marker

    Unlike PC files, PS3 compressed data doesn't always start with a fixed pattern.
    We use section headers (identified by magic bytes) to locate compressed data.

    Args:
        data: Full OPTIONS file data (including 8-byte prefix)
        prefix_offset: Offset where section data starts

    Returns:
        List of tuples: [(section_num, start_offset, end_offset, compressed_data, header_info), ...]
    """
    TERMINATOR = b'\x20\x00'

    # Find section headers using magic bytes
    section_headers = find_section_headers_ps3(data, prefix_offset)

    if not section_headers:
        return []

    sections = []

    for section_num, header_info in enumerate(section_headers, 1):
        # Compressed data starts at data_offset
        compressed_start = header_info.data_offset
        compressed_size = header_info.compressed_length

        # Calculate end offset
        compressed_end = compressed_start + compressed_size

        # Verify terminator is present
        if compressed_end >= 2:
            term_bytes = data[compressed_end - 2:compressed_end]
            if term_bytes != TERMINATOR:
                print(f"Warning: Section {section_num} terminator mismatch: expected 20 00, got {term_bytes.hex()}")

        # Extract compressed data
        compressed_data = data[compressed_start:compressed_end]

        sections.append((section_num, compressed_start, compressed_end, compressed_data, header_info))

    return sections


def decompress_ps3_options_file(input_file: str, section_filter: int = None) -> dict:
    """
    Decompress sections from a PS3 OPTIONS file with header validation

    Args:
        input_file: Path to PS3 OPTIONS file
        section_filter: Optional section number (1-4) to decompress only that section

    Returns:
        Dictionary with results: {
            'prefix': { 'data_size': int, 'crc32_expected': int, 'crc32_actual': int, 'valid': bool },
            'sections': [(section_num, offset, size, decompressed_data, validation), ...],
            'errors': [error_messages, ...]
        }
    """
    # Read input file
    if not os.path.exists(input_file):
        return {'sections': [], 'errors': [f"Input file not found: {input_file}"]}

    with open(input_file, 'rb') as f:
        data = f.read()

    # Parse PS3 prefix
    data_size, crc32_expected, crc32_actual, is_valid = parse_ps3_prefix(data)
    prefix_info = {
        'data_size': data_size,
        'crc32_expected': crc32_expected,
        'crc32_actual': crc32_actual,
        'valid': is_valid
    }

    # Find all sections (skip 8-byte prefix)
    sections = find_sections_ps3(data, prefix_offset=8)

    if not sections:
        return {'prefix': prefix_info, 'sections': [], 'errors': ["No compressed sections found in file"]}

    # Filter by section number if specified
    if section_filter is not None:
        sections = [s for s in sections if s[0] == section_filter]
        if not sections:
            return {'prefix': prefix_info, 'sections': [], 'errors': [f"Section {section_filter} not found"]}

    # Decompress sections
    decompressor = LZSSDecompressor()
    results = []
    errors = []

    for section_num, start_offset, end_offset, compressed_data, header_info in sections:
        try:
            decompressed = decompressor.decompress(compressed_data)

            # Perform validation if header is available
            validation = {
                'has_header': header_info is not None,
                'expected_compressed_size': None,
                'actual_compressed_size': len(compressed_data),
                'compressed_size_match': None,
                'expected_uncompressed_size': None,
                'actual_uncompressed_size': len(decompressed),
                'uncompressed_size_match': None,
                'expected_checksum': None,
                'actual_checksum': None,
                'checksum_match': None,
                'field3': None,
            }

            if header_info:
                # Validate compressed size
                validation['expected_compressed_size'] = header_info.compressed_length
                validation['compressed_size_match'] = (len(compressed_data) == header_info.compressed_length)

                # Validate uncompressed size
                validation['expected_uncompressed_size'] = header_info.uncompressed_length
                validation['uncompressed_size_match'] = (len(decompressed) == header_info.uncompressed_length)

                # Validate checksum (Adler-32 of compressed data)
                validation['expected_checksum'] = header_info.checksum
                validation['actual_checksum'] = adler32(compressed_data)
                validation['checksum_match'] = (validation['actual_checksum'] == header_info.checksum)

                # Store field3 for identification
                validation['field3'] = header_info.field3

            results.append((section_num, start_offset, len(compressed_data), decompressed, validation))
        except Exception as e:
            errors.append(f"Error decompressing section {section_num}: {str(e)}")

    return {'prefix': prefix_info, 'sections': results, 'errors': errors}


# ============================================================================
# MAIN
# ============================================================================

def main():
    """
    Main entry point for command-line usage

    Usage:
        python lzss_decompressor_ps3.py OPTIONS.PS3        # Decompress all sections
        python lzss_decompressor_ps3.py OPTIONS.PS3 2      # Decompress only section 2
    """
    if len(sys.argv) < 2 or sys.argv[1] in ['-h', '--help', 'help']:
        print("LZSS Decompressor for AC Brotherhood PS3 OPTIONS Files")
        print("=" * 70)
        print()
        print("Usage:")
        print("  python lzss_decompressor_ps3.py <OPTIONS_FILE> [SECTION]")
        print()
        print("Arguments:")
        print("  OPTIONS_FILE    Path to PS3 OPTIONS file")
        print("  SECTION         Optional: Section number (1, 2, 3, or 4)")
        print()
        print("Examples:")
        print("  python lzss_decompressor_ps3.py OPTIONS.PS3        # All sections")
        print("  python lzss_decompressor_ps3.py OPTIONS.PS3 2      # Section 2 only")
        print("  python lzss_decompressor_ps3.py OPTIONS.PS3 4      # Section 4 only (controller mappings)")
        print()
        print("Output files:")
        print("  section1.bin - Section 1 decompressed data")
        print("  section2.bin - Section 2 decompressed data")
        print("  section3.bin - Section 3 decompressed data")
        print("  section4.bin - Section 4 decompressed data (PS3 controller mappings)")
        print()
        print("PS3-Specific Features:")
        print("  - Verifies 8-byte PS3 prefix (size + CRC32)")
        print("  - Handles 4 sections (vs 3 on PC)")
        print("  - Section 4 contains DualShock 3 controller mappings")
        print()
        return 0

    input_file = sys.argv[1]
    section_filter = None

    if len(sys.argv) >= 3:
        try:
            section_filter = int(sys.argv[2])
            if section_filter not in [1, 2, 3, 4]:
                print(f"Error: Section number must be 1, 2, 3, or 4 (got {section_filter})")
                return 1
        except ValueError:
            print(f"Error: Invalid section number: {sys.argv[2]}")
            return 1

    # Get directory of input file for output
    output_dir = os.path.dirname(os.path.abspath(input_file))

    print("=" * 70)
    print("LZSS Decompressor for AC Brotherhood PS3 OPTIONS Files")
    print("=" * 70)
    print()
    print(f"Input file: {input_file}")
    if section_filter:
        print(f"Decompressing: Section {section_filter} only")
    else:
        print(f"Decompressing: All sections")
    print()

    # Decompress
    result = decompress_ps3_options_file(input_file, section_filter)

    # Report PS3 prefix validation
    if 'prefix' in result:
        prefix = result['prefix']
        print("PS3 Prefix Validation:")
        print(f"  Data size:     {prefix['data_size']} bytes (0x{prefix['data_size']:04X})")
        print(f"  Expected CRC32: 0x{prefix['crc32_expected']:08X}")
        print(f"  Actual CRC32:   0x{prefix['crc32_actual']:08X}")
        print(f"  CRC32 Valid:   {'YES' if prefix['valid'] else 'NO - MISMATCH!'}")
        print()

    # Report errors
    if result['errors']:
        print("ERRORS:")
        for error in result['errors']:
            print(f"  - {error}")
        print()
        return 1

    # Report sections found
    sections = result['sections']
    print(f"Found {len(sections)} section(s):")
    print()

    # Section identifiers for display
    SECTION_NAMES = {
        0x000000C6: "Section 1 (PS3)",
        0x11FACE11: "Section 2 (settings)",
        0x21EFFE22: "Section 3 (additional)",
        0x00000007: "Section 4 (controller mappings)",
    }

    for section_num, start_offset, compressed_size, decompressed_data, validation in sections:
        # Determine section name
        field3 = validation.get('field3')
        section_name = SECTION_NAMES.get(field3, f"Section {section_num}")

        print(f"Section {section_num} ({section_name}):")
        print(f"  Offset:           0x{start_offset:08x} ({start_offset})")
        print(f"  Compressed size:  {compressed_size:6d} bytes")
        print(f"  Decompressed size: {len(decompressed_data):6d} bytes")
        print(f"  Compression ratio: {len(decompressed_data)/compressed_size:.2f}x")

        if field3 is not None:
            print(f"  Field3 (ID):      0x{field3:08X}")

        # Show validation results
        if validation['has_header']:
            print()
            print("  Header Validation:")

            # Compressed size validation
            if validation['expected_compressed_size'] is not None:
                match_str = "PASS" if validation['compressed_size_match'] else "FAIL"
                print(f"    Compressed size:   Expected {validation['expected_compressed_size']:6d} bytes, "
                      f"Got {validation['actual_compressed_size']:6d} bytes [{match_str}]")

            # Uncompressed size validation
            if validation['expected_uncompressed_size'] is not None:
                match_str = "PASS" if validation['uncompressed_size_match'] else "FAIL"
                print(f"    Uncompressed size: Expected {validation['expected_uncompressed_size']:6d} bytes, "
                      f"Got {validation['actual_uncompressed_size']:6d} bytes [{match_str}]")

            # Checksum validation (Adler-32 with zero seed)
            if validation['expected_checksum'] is not None:
                match_str = "MATCH" if validation['checksum_match'] else "DIFF"
                print(f"    Checksum:          Expected 0x{validation['expected_checksum']:08X}, "
                      f"Calculated 0x{validation['actual_checksum']:08X} [{match_str}]")

            # Overall validation status
            all_valid = (validation['compressed_size_match'] and
                        validation['uncompressed_size_match'] and
                        validation['checksum_match'])
            print(f"    Overall:           {'ALL VALIDATION PASSED' if all_valid else 'VALIDATION FAILED'}")
        else:
            print()
            print("  Header Validation: No header found (backward compatibility mode)")

        # Save output
        output_file = os.path.join(output_dir, f"section{section_num}.bin")
        with open(output_file, 'wb') as f:
            f.write(decompressed_data)
        print(f"  Output file:      {output_file}")

        # Show sample
        print(f"  Sample (first 32 bytes):")
        for i in range(0, min(32, len(decompressed_data)), 16):
            hex_str = ' '.join(f'{b:02x}' for b in decompressed_data[i:i+16])
            print(f"    {i:04x}: {hex_str}")
        print()

    print("=" * 70)
    print(f"SUCCESS: Decompressed {len(sections)} section(s)")
    print("=" * 70)

    return 0


# ============================================================================
# TEST HARNESS
# ============================================================================

def run_tests():
    """Test harness to verify decompressor against PS3 OPTIONS file"""
    print("=" * 70)
    print("PS3 LZSS Decompressor Test Suite")
    print("=" * 70)
    print()

    test_file = '/mnt/f/ClaudeHole/assassincreedbrotherhood/OPTIONS.PS3'

    if not os.path.exists(test_file):
        print(f"Test file not found: {test_file}")
        return False

    print(f"Testing with: {test_file}")
    print()

    result = decompress_ps3_options_file(test_file)

    # Check prefix
    if 'prefix' in result:
        prefix = result['prefix']
        print(f"PS3 Prefix: {'VALID' if prefix['valid'] else 'INVALID'}")
        print()

    if result['errors']:
        print("ERRORS:")
        for error in result['errors']:
            print(f"  - {error}")
        return False

    print(f"Successfully decompressed {len(result['sections'])} sections:")
    for section_num, _, _, decompressed_data, validation in result['sections']:
        print(f"  Section {section_num}: {len(decompressed_data)} bytes")

    print()
    print("=" * 70)
    print("RESULT: Decompression successful!")
    print("=" * 70)

    return True


if __name__ == "__main__":
    # If no arguments provided, run tests
    if len(sys.argv) == 1:
        success = run_tests()
        exit(0 if success else 1)
    else:
        # Run main decompressor
        exit(main())
