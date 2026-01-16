#!/usr/bin/env python3
"""
OPTIONS Unpack - Extract sections from AC Brotherhood OPTIONS files
===================================================================

Extracts and decompresses sections from OPTIONS save files. Supports both
PC and PS3 formats with automatic detection.

Use options_pack.py to reassemble sections back into an OPTIONS file.

Section Names:
-------------
| Section | Name                      | Field3 (ID)  |
|---------|---------------------------|--------------|
| 1       | SaveGame                  | 0xC5 / 0xC6  |
| 2       | AssassinGlobalProfileData | 0x11FACE11   |
| 3       | AssassinSingleProfileData | 0x21EFFE22   |
| 4       | AssassinMultiProfileData  | 0x00000007   |

Section 4 is optional on both platforms.

Usage:
------
    python options_unpack.py OPTIONS.bin              # Auto-detect, all sections
    python options_unpack.py OPTIONS.bin 2            # Section 2 only
    python options_unpack.py OPTIONS.bin --pc         # Force PC format
    python options_unpack.py OPTIONS.bin --ps3        # Force PS3 format
    python options_unpack.py OPTIONS.bin -o ./output/ # Custom output directory
"""

import sys
import os
import struct
import argparse


# =============================================================================
# CONSTANTS
# =============================================================================

# Magic pattern found at offset 0x10 in each section header
MAGIC_PATTERN = b'\x33\xAA\xFB\x57\x99\xFA\x04\x10\x01\x00\x02\x00\x80\x00\x00\x01'

# Section identifiers
SECTION_IDS = {
    0x000000C5: (1, "PC"),      # Section 1 PC
    0x000000C6: (1, "PS3"),     # Section 1 PS3
    0x11FACE11: (2, "Both"),    # Section 2
    0x21EFFE22: (3, "Both"),    # Section 3
    0x00000007: (4, "Both"),    # Section 4 (optional)
}

# Section names for display
SECTION_NAMES = {
    1: "SaveGame",
    2: "AssassinGlobalProfileData",
    3: "AssassinSingleProfileData",
    4: "AssassinMultiProfileData",
}

# PS3 file is always padded to this size
PS3_FILE_SIZE = 51200


# =============================================================================
# CHECKSUMS
# =============================================================================

def adler32_zero_seed(data: bytes) -> int:
    """
    Calculate Adler-32 checksum with zero seed (AC Brotherhood variant).

    Standard Adler-32 uses s1=1, s2=0. This game uses s1=0, s2=0.
    Used for validating compressed data integrity.
    """
    MOD_ADLER = 65521
    s1 = 0
    s2 = 0

    for byte in data:
        s1 = (s1 + byte) % MOD_ADLER
        s2 = (s2 + s1) % MOD_ADLER

    return (s2 << 16) | s1


def crc32_ps3(data: bytes) -> int:
    """
    Calculate CRC32 using PS3's custom parameters.

    Parameters:
        poly=0x04C11DB7, init=0xBAE23CD0, xorout=0xFFFFFFFF
        refin=true, refout=true

    Used for validating the PS3 file prefix.
    """
    crc = 0xBAE23CD0

    for byte in data:
        # Reflect input byte
        byte = int('{:08b}'.format(byte)[::-1], 2)
        crc ^= (byte << 24)

        for _ in range(8):
            if crc & 0x80000000:
                crc = ((crc << 1) ^ 0x04C11DB7) & 0xFFFFFFFF
            else:
                crc = (crc << 1) & 0xFFFFFFFF

    # Reflect output
    crc = int('{:032b}'.format(crc)[::-1], 2)
    return (crc ^ 0xFFFFFFFF) & 0xFFFFFFFF


# =============================================================================
# FORMAT DETECTION
# =============================================================================

def detect_format(data: bytes) -> str:
    """
    Auto-detect whether the file is PC or PS3 format.

    Detection methods:
    1. PS3 files are always padded to exactly 51,200 bytes
    2. Check magic pattern location (PC: 0x10, PS3: 0x18)
    3. Verify PS3 prefix CRC32 if applicable

    Returns:
        'PC', 'PS3', or 'unknown'
    """
    # Method 1: PS3 files are padded to exactly 51,200 bytes
    if len(data) == PS3_FILE_SIZE:
        # Verify with CRC32 check
        if len(data) >= 8:
            prefix_size = struct.unpack('>I', data[0:4])[0]
            prefix_crc = struct.unpack('>I', data[4:8])[0]
            if prefix_size < len(data) - 8:
                actual_crc = crc32_ps3(data[8:8 + prefix_size])
                if actual_crc == prefix_crc:
                    return 'PS3'

    # Method 2: Check magic pattern location
    magic_short = MAGIC_PATTERN[:4]  # 0x33 0xAA 0xFB 0x57

    # PC: Magic at offset 0x10 (header starts at 0x00)
    if len(data) > 0x14 and data[0x10:0x14] == magic_short:
        return 'PC'

    # PS3: Magic at offset 0x18 (8-byte prefix + header at 0x08)
    if len(data) > 0x1C and data[0x18:0x1C] == magic_short:
        return 'PS3'

    return 'unknown'


# =============================================================================
# LZSS DECOMPRESSOR
# =============================================================================

class LZSSDecompressor:
    """
    LZSS Decompressor matching AC Brotherhood's exact format.
    Identical between PC and PS3 versions.

    Encoding types:
    - Literal (flag=0): 8-bit byte
    - Short match (flags=10): length 2-5, offset 1-256
    - Long match (flags=11): length 3+, offset 0-8191
    - Terminator: offset=0 (bytes 0x20 0x00)
    """

    def decompress(self, compressed: bytes) -> bytes:
        """Decompress LZSS data."""
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

                    # Terminator check (distance == 0)
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


# =============================================================================
# SECTION HEADER PARSING
# =============================================================================

class SectionHeader:
    """Represents a parsed section header."""

    def __init__(self, header_offset: int, data_offset: int,
                 compressed_size: int, uncompressed_size: int,
                 checksum: int, field3: int, platform: str):
        self.header_offset = header_offset
        self.data_offset = data_offset
        self.compressed_size = compressed_size
        self.uncompressed_size = uncompressed_size
        self.checksum = checksum
        self.field3 = field3
        self.platform = platform


def find_section_headers(data: bytes, platform: str, prefix_offset: int = 0) -> list:
    """
    Find and parse all section headers in the file.

    Args:
        data: File data
        platform: 'PC' or 'PS3'
        prefix_offset: Byte offset where sections start (8 for PS3, 0 for PC)

    Returns:
        List of SectionHeader objects
    """
    headers = []
    search_pos = prefix_offset

    while True:
        # Find magic pattern
        pattern_pos = data.find(MAGIC_PATTERN, search_pos)
        if pattern_pos == -1:
            break

        # Header starts 0x10 bytes before the magic pattern
        header_start = pattern_pos - 0x10

        if header_start < prefix_offset or header_start + 44 > len(data):
            search_pos = pattern_pos + len(MAGIC_PATTERN)
            continue

        # Parse header fields based on platform
        if platform == 'PS3':
            # PS3: Fields 0-2 are big-endian, fields 3-10 are little-endian
            field0 = struct.unpack('>I', data[header_start:header_start+4])[0]
            field1 = struct.unpack('>I', data[header_start+4:header_start+8])[0]
            field2 = struct.unpack('>I', data[header_start+8:header_start+12])[0]
        else:
            # PC: All fields are little-endian
            field0 = struct.unpack('<I', data[header_start:header_start+4])[0]
            field1 = struct.unpack('<I', data[header_start+4:header_start+8])[0]
            field2 = struct.unpack('<I', data[header_start+8:header_start+12])[0]

        # Fields 3-10 are always little-endian
        field3 = struct.unpack('<I', data[header_start+12:header_start+16])[0]

        # After magic pattern: compressed_size, uncompressed_size, checksum
        sizes_offset = pattern_pos + len(MAGIC_PATTERN)
        if sizes_offset + 12 > len(data):
            break

        compressed_size = struct.unpack('<I', data[sizes_offset:sizes_offset+4])[0]
        uncompressed_size = struct.unpack('<I', data[sizes_offset+4:sizes_offset+8])[0]
        checksum = struct.unpack('<I', data[sizes_offset+8:sizes_offset+12])[0]

        # Data starts after 44-byte header
        data_offset = header_start + 44

        # Use field2 for section identification (Field3 in the structure)
        header = SectionHeader(
            header_offset=header_start,
            data_offset=data_offset,
            compressed_size=compressed_size,
            uncompressed_size=uncompressed_size,
            checksum=checksum,
            field3=field2,
            platform=platform
        )

        headers.append(header)
        search_pos = pattern_pos + len(MAGIC_PATTERN)

    return headers


# =============================================================================
# MAIN DECOMPRESSION LOGIC
# =============================================================================

def decompress_options_file(input_file: str, section_filter: int = None,
                            force_platform: str = None) -> dict:
    """
    Decompress an OPTIONS file (PC or PS3).

    Args:
        input_file: Path to OPTIONS file
        section_filter: Optional section number (1-4) to decompress
        force_platform: Optional 'PC' or 'PS3' to skip auto-detection

    Returns:
        Dictionary with results
    """
    if not os.path.exists(input_file):
        return {'sections': [], 'errors': [f"File not found: {input_file}"]}

    with open(input_file, 'rb') as f:
        data = f.read()

    # Detect or use forced platform
    if force_platform:
        platform = force_platform
    else:
        platform = detect_format(data)
        if platform == 'unknown':
            return {'sections': [], 'errors': ["Could not detect file format (PC or PS3)"]}

    # Set prefix offset based on platform
    prefix_offset = 8 if platform == 'PS3' else 0

    # Parse PS3 prefix if applicable
    prefix_info = None
    if platform == 'PS3' and len(data) >= 8:
        prefix_size = struct.unpack('>I', data[0:4])[0]
        prefix_crc_expected = struct.unpack('>I', data[4:8])[0]
        prefix_crc_actual = crc32_ps3(data[8:8 + prefix_size])
        prefix_info = {
            'data_size': prefix_size,
            'crc32_expected': prefix_crc_expected,
            'crc32_actual': prefix_crc_actual,
            'valid': prefix_crc_expected == prefix_crc_actual
        }

    # Find section headers
    headers = find_section_headers(data, platform, prefix_offset)

    if not headers:
        return {
            'platform': platform,
            'prefix': prefix_info,
            'sections': [],
            'errors': ["No sections found in file"]
        }

    # Filter by section number if specified
    if section_filter is not None:
        headers = [h for i, h in enumerate(headers, 1) if i == section_filter]
        if not headers:
            return {
                'platform': platform,
                'prefix': prefix_info,
                'sections': [],
                'errors': [f"Section {section_filter} not found"]
            }

    # Decompress sections
    decompressor = LZSSDecompressor()
    results = []
    errors = []

    for section_num, header in enumerate(headers, 1):
        if section_filter:
            section_num = section_filter

        try:
            # Extract compressed data
            compressed_start = header.data_offset
            compressed_end = compressed_start + header.compressed_size
            compressed_data = data[compressed_start:compressed_end]

            # Decompress
            decompressed = decompressor.decompress(compressed_data)

            # Validate
            validation = {
                'compressed_size_expected': header.compressed_size,
                'compressed_size_actual': len(compressed_data),
                'compressed_size_match': len(compressed_data) == header.compressed_size,
                'uncompressed_size_expected': header.uncompressed_size,
                'uncompressed_size_actual': len(decompressed),
                'uncompressed_size_match': len(decompressed) == header.uncompressed_size,
                'checksum_expected': header.checksum,
                'checksum_actual': adler32_zero_seed(compressed_data),
                'checksum_match': adler32_zero_seed(compressed_data) == header.checksum,
                'field3': header.field3,
            }

            results.append({
                'section_num': section_num,
                'header_offset': header.header_offset,
                'data_offset': header.data_offset,
                'compressed_size': len(compressed_data),
                'decompressed_data': decompressed,
                'validation': validation,
            })

        except Exception as e:
            errors.append(f"Error decompressing section {section_num}: {str(e)}")

    return {
        'platform': platform,
        'prefix': prefix_info,
        'sections': results,
        'errors': errors,
    }


# =============================================================================
# CLI INTERFACE
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='OPTIONS Unpack - Extract sections from AC Brotherhood OPTIONS Files (PC & PS3)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Section Names:
  1: SaveGame                   - Core save game data
  2: AssassinGlobalProfileData  - Global profile settings
  3: AssassinSingleProfileData  - Single-player profile data
  4: AssassinMultiProfileData   - Multiplayer profile data (optional)

Examples:
  python options_unpack.py OPTIONS.bin           # Auto-detect, all sections
  python options_unpack.py OPTIONS.bin 2         # Section 2 only
  python options_unpack.py OPTIONS.bin --pc      # Force PC format
  python options_unpack.py OPTIONS.PS3 --ps3     # Force PS3 format
        """
    )

    parser.add_argument('input', help='Input OPTIONS file')
    parser.add_argument('section', nargs='?', type=int, choices=[1, 2, 3, 4],
                        help='Section number to decompress (1-4)')
    parser.add_argument('--pc', action='store_true', help='Force PC format')
    parser.add_argument('--ps3', action='store_true', help='Force PS3 format')
    parser.add_argument('-o', '--output-dir', help='Output directory (default: same as input)')

    args = parser.parse_args()

    # Check for conflicting flags
    if args.pc and args.ps3:
        parser.error("Cannot specify both --pc and --ps3")

    force_platform = None
    if args.pc:
        force_platform = 'PC'
    elif args.ps3:
        force_platform = 'PS3'

    # Set output directory
    output_dir = args.output_dir or os.path.dirname(os.path.abspath(args.input))
    if not output_dir:
        output_dir = '.'

    print("=" * 70)
    print("OPTIONS Unpack for AC Brotherhood")
    print("=" * 70)
    print()
    print(f"Input file: {args.input}")

    # Decompress
    result = decompress_options_file(args.input, args.section, force_platform)

    # Show detected platform
    platform = result.get('platform', 'unknown')
    print(f"Platform:   {platform}" + (" (forced)" if force_platform else " (auto-detected)"))

    if args.section:
        print(f"Section:    {args.section} only")
    else:
        print(f"Sections:   All")
    print()

    # Show PS3 prefix validation
    if result.get('prefix'):
        prefix = result['prefix']
        print("PS3 Prefix Validation:")
        print(f"  Data size:      {prefix['data_size']} bytes (0x{prefix['data_size']:04X})")
        print(f"  Expected CRC32: 0x{prefix['crc32_expected']:08X}")
        print(f"  Actual CRC32:   0x{prefix['crc32_actual']:08X}")
        print(f"  Status:         {'VALID' if prefix['valid'] else 'INVALID'}")
        print()

    # Handle errors
    if result['errors']:
        print("ERRORS:")
        for error in result['errors']:
            print(f"  - {error}")
        return 1

    # Process sections
    sections = result['sections']
    print(f"Found {len(sections)} section(s):")
    print()

    for section in sections:
        section_num = section['section_num']
        section_name = SECTION_NAMES.get(section_num, f"Section {section_num}")
        validation = section['validation']
        decompressed = section['decompressed_data']

        print(f"Section {section_num} ({section_name}):")
        print(f"  Header offset:    0x{section['header_offset']:08X}")
        print(f"  Data offset:      0x{section['data_offset']:08X}")
        print(f"  Compressed:       {section['compressed_size']:6d} bytes")
        print(f"  Decompressed:     {len(decompressed):6d} bytes")
        print(f"  Ratio:            {len(decompressed)/section['compressed_size']:.2f}x")
        print(f"  Field3 (ID):      0x{validation['field3']:08X}")
        print()
        print("  Validation:")

        # Compressed size
        status = "PASS" if validation['compressed_size_match'] else "FAIL"
        print(f"    Compressed size:   {validation['compressed_size_expected']:6d} expected, "
              f"{validation['compressed_size_actual']:6d} actual [{status}]")

        # Uncompressed size
        status = "PASS" if validation['uncompressed_size_match'] else "FAIL"
        print(f"    Uncompressed size: {validation['uncompressed_size_expected']:6d} expected, "
              f"{validation['uncompressed_size_actual']:6d} actual [{status}]")

        # Checksum
        status = "MATCH" if validation['checksum_match'] else "DIFF"
        print(f"    Checksum:          0x{validation['checksum_expected']:08X} expected, "
              f"0x{validation['checksum_actual']:08X} actual [{status}]")

        # Overall
        all_valid = (validation['compressed_size_match'] and
                     validation['uncompressed_size_match'] and
                     validation['checksum_match'])
        print(f"    Overall:           {'ALL PASSED' if all_valid else 'FAILED'}")

        # Save output
        output_file = os.path.join(output_dir, f"section{section_num}.bin")
        with open(output_file, 'wb') as f:
            f.write(decompressed)
        print(f"  Output: {output_file}")

        # Sample
        print(f"  Sample (first 32 bytes):")
        for i in range(0, min(32, len(decompressed)), 16):
            hex_str = ' '.join(f'{b:02x}' for b in decompressed[i:i+16])
            print(f"    {i:04x}: {hex_str}")
        print()

    print("=" * 70)
    print(f"SUCCESS: Decompressed {len(sections)} section(s) from {platform} format")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
