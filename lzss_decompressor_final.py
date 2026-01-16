#!/usr/bin/env python3
"""
Unified LZSS Decompressor for AC Brotherhood OPTIONS Files
===========================================================

This decompressor implements the exact LZSS format used by Assassin's Creed
Brotherhood for compressing OPTIONS file sections.

LZSS Format Documentation:
-------------------------

The format uses a bit-stream for encoding decisions, reading bits from LSB to MSB:

1. **Literal Bytes (flag bit = 0)**:
   - Flag bit: 0
   - Data: 8 bits (literal byte value)
   - Action: Output the literal byte

2. **Short Match (flag bits = 10)**:
   - Flag bits: 10 (read as bit 1, then bit 0)
   - Length: 2 bits (0-3, representing lengths 2-5)
   - Offset: 8 bits (0-255, representing distances 1-256)
   - Action: Copy 'length' bytes from 'offset' bytes back in output

3. **Long Match (flag bits = 11)**:
   - Flag bits: 11 (read as bit 1, then bit 1)
   - Encoding: 16-bit value split as:
     * Byte 1: [length_field:3][offset_low:5]
     * Byte 2: [offset_high:8]
   - Offset: ((offset_high << 5) | offset_low) represents distance 0-8191
   - Length:
     * If length_field = 0: Extended length encoding
       - Base length = 9
       - Read bytes: 0x00 adds 255, non-zero byte N adds N and stops
     * If length_field = 1-7: length = length_field + 2 (lengths 3-9)
   - Action: Copy 'length' bytes from 'offset' bytes back in output

4. **Terminator Sequence**:
   - A long match with offset=0 (bytes 0x20 0x00) terminates decompression
   - This is detected by checking if distance == 0 before the copy loop

Bit Reading:
-----------
- Bits are read from LSB to MSB within each flag byte
- Flag bytes are consumed as needed when flag_bits < required bits
- The decompressor maintains a flag register and bit counter

Edge Cases:
----------
- Negative src_pos (offset beyond start): Output zero bytes
- Offset of 0 in long match: Terminator - stop decompression immediately
- Extended length with trailing 0x00 bytes: Each adds 255 to length

OPTIONS File Structure:
----------------------
Full OPTIONS files contain 3 compressed sections. Each section has metadata
stored in a header block that appears BEFORE the compressed data:

Section Header Block (before compressed data):
  - Various metadata fields (18 bytes before the pattern)
  - Common pattern (18 bytes): 33 AA FB 57 99 FA 04 10 01 00 02 00 80 00 00 01
  - Compressed length (4 bytes, little-endian): Size of compressed data
  - Uncompressed length (4 bytes, little-endian): Size after decompression
  - Checksum (4 bytes, little-endian): Adler-32 checksum with zero seed (s1=0, s2=0)
  - Then compressed data begins

Compressed Section Format:
  - Header: 06 00 e1 00 (4 bytes) - marks section start
  - Compressed data: LZSS compressed bytes
  - Terminator: 20 00 (2 bytes) - marks section end

NOTE: The header bytes (06 00 e1 00) are part of the LZSS compressed stream
and decompress to produce the leading zeros in the output. They should be
included when decompressing, not stripped.

Header Validation:
  - Compressed size validation: Compares header value with actual section size
  - Uncompressed size validation: Compares header value with decompressed size
  - Checksum validation: Adler-32 with zero seed - validates compressed data integrity
  - Files without headers fall back to basic decompression (backward compatible)
"""

import sys
import os
import struct

# Import core LZSS functionality from shared module
from lzss import LZSSDecompressor, decompress


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


class SectionHeader:
    """
    Represents a section header with metadata
    """
    def __init__(self, pattern_offset: int, compressed_length: int,
                 uncompressed_length: int, checksum: int, data_offset: int):
        self.pattern_offset = pattern_offset
        self.compressed_length = compressed_length
        self.uncompressed_length = uncompressed_length
        self.checksum = checksum
        self.data_offset = data_offset  # Offset where compressed data starts (after checksum)

    def __repr__(self):
        return (f"SectionHeader(pattern_offset=0x{self.pattern_offset:x}, "
                f"compressed={self.compressed_length}, uncompressed={self.uncompressed_length}, "
                f"checksum=0x{self.checksum:08x}, data_offset=0x{self.data_offset:x})")


def find_section_headers(data: bytes) -> list:
    """
    Find and parse section headers in OPTIONS file

    Each header contains:
    - Common pattern (18 bytes): 33 AA FB 57 99 FA 04 10 01 00 02 00 80 00 00 01
    - Compressed length (4 bytes, little-endian)
    - Uncompressed length (4 bytes, little-endian)
    - Adler-32 checksum (4 bytes, little-endian)
    - Then compressed data starts with: 06 00 e1 00

    Args:
        data: Full OPTIONS file data

    Returns:
        List of SectionHeader objects
    """
    # The common pattern that appears before length/checksum fields
    COMMON_PATTERN = b'\x33\xAA\xFB\x57\x99\xFA\x04\x10\x01\x00\x02\x00\x80\x00\x00\x01'

    headers = []
    search_pos = 0

    while True:
        # Find next occurrence of the common pattern
        pattern_pos = data.find(COMMON_PATTERN, search_pos)
        if pattern_pos == -1:
            break

        # After the pattern, we should have:
        # - 4 bytes: compressed length
        # - 4 bytes: uncompressed length
        # - 4 bytes: Adler-32 checksum
        header_data_pos = pattern_pos + len(COMMON_PATTERN)

        # Make sure we have enough bytes for the header fields
        if header_data_pos + 12 > len(data):
            break

        # Parse the header fields
        compressed_length = struct.unpack('<I', data[header_data_pos:header_data_pos+4])[0]
        uncompressed_length = struct.unpack('<I', data[header_data_pos+4:header_data_pos+8])[0]
        checksum = struct.unpack('<I', data[header_data_pos+8:header_data_pos+12])[0]

        # Data starts right after the checksum
        data_offset = header_data_pos + 12

        header = SectionHeader(
            pattern_offset=pattern_pos,
            compressed_length=compressed_length,
            uncompressed_length=uncompressed_length,
            checksum=checksum,
            data_offset=data_offset
        )

        headers.append(header)

        # Continue searching after this pattern
        search_pos = pattern_pos + len(COMMON_PATTERN)

    return headers


# ============================================================================
# OPTIONS FILE HANDLING
# ============================================================================

def find_sections(data: bytes) -> list:
    """
    Find all compressed sections in an OPTIONS file

    Each section starts with: 06 00 e1 00
    Each section ends with: 20 00

    Now also attempts to find and associate section headers with metadata.

    Args:
        data: Full OPTIONS file data

    Returns:
        List of tuples: [(section_num, start_offset, end_offset, compressed_data, header_info), ...]
        where header_info is a SectionHeader object or None if no header found
    """
    HEADER = b'\x06\x00\xe1\x00'
    TERMINATOR = b'\x20\x00'

    sections = []
    search_pos = 0
    section_num = 1

    # Try to find section headers for validation
    section_headers = find_section_headers(data)

    while True:
        # Find next section header
        header_pos = data.find(HEADER, search_pos)
        if header_pos == -1:
            break

        # Find the terminator after this header
        # Start searching after the header
        term_search_start = header_pos + len(HEADER)
        term_pos = data.find(TERMINATOR, term_search_start)

        if term_pos == -1:
            print(f"Warning: Section {section_num} at offset {header_pos} has no terminator")
            break

        # Extract compressed data INCLUDING the header (it's part of the LZSS stream)
        # The header bytes 06 00 e1 00 decompress to the leading zeros in the output
        compressed_start = header_pos
        compressed_end = term_pos + len(TERMINATOR)
        compressed_data = data[compressed_start:compressed_end]

        # Try to find matching section header
        # The section header should be before the compressed data
        matching_header = None
        for hdr in section_headers:
            # The data_offset in the header should point to this section's start
            if hdr.data_offset == header_pos:
                matching_header = hdr
                break

        sections.append((section_num, header_pos, compressed_end, compressed_data, matching_header))

        # Continue searching after this section
        search_pos = compressed_end
        section_num += 1

    return sections


def decompress_options_file(input_file: str, section_filter: int = None) -> dict:
    """
    Decompress sections from an OPTIONS file with header validation

    Args:
        input_file: Path to OPTIONS file
        section_filter: Optional section number (1, 2, or 3) to decompress only that section

    Returns:
        Dictionary with results: {
            'sections': [(section_num, offset, size, decompressed_data, validation), ...],
            'errors': [error_messages, ...]
        }
        where validation is a dict with validation results
    """
    # Read input file
    if not os.path.exists(input_file):
        return {'sections': [], 'errors': [f"Input file not found: {input_file}"]}

    with open(input_file, 'rb') as f:
        data = f.read()

    # Find all sections
    sections = find_sections(data)

    if not sections:
        return {'sections': [], 'errors': ["No compressed sections found in file"]}

    # Filter by section number if specified
    if section_filter is not None:
        sections = [s for s in sections if s[0] == section_filter]
        if not sections:
            return {'sections': [], 'errors': [f"Section {section_filter} not found"]}

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

            results.append((section_num, start_offset, len(compressed_data), decompressed, validation))
        except Exception as e:
            errors.append(f"Error decompressing section {section_num}: {str(e)}")

    return {'sections': results, 'errors': errors}


def main():
    """
    Main entry point for command-line usage

    Usage:
        python lzss_decompressor_final.py OPTIONS.bin        # Decompress all sections
        python lzss_decompressor_final.py OPTIONS.bin 2      # Decompress only section 2
    """
    if len(sys.argv) < 2 or sys.argv[1] in ['-h', '--help', 'help']:
        print("LZSS Decompressor for AC Brotherhood OPTIONS Files")
        print("=" * 70)
        print()
        print("Usage:")
        print("  python lzss_decompressor_final.py <OPTIONS_FILE> [SECTION]")
        print()
        print("Arguments:")
        print("  OPTIONS_FILE    Path to OPTIONS.bin file")
        print("  SECTION         Optional: Section number (1, 2, or 3)")
        print()
        print("Examples:")
        print("  python lzss_decompressor_final.py OPTIONS.bin        # All sections")
        print("  python lzss_decompressor_final.py OPTIONS.bin 2      # Section 2 only")
        print()
        print("Output files:")
        print("  game_uncompressed_1.bin - Section 1 decompressed data")
        print("  game_uncompressed_2.bin - Section 2 decompressed data")
        print("  game_uncompressed_3.bin - Section 3 decompressed data")
        print()
        return 0

    input_file = sys.argv[1]
    section_filter = None

    if len(sys.argv) >= 3:
        try:
            section_filter = int(sys.argv[2])
            if section_filter not in [1, 2, 3]:
                print(f"Error: Section number must be 1, 2, or 3 (got {section_filter})")
                return 1
        except ValueError:
            print(f"Error: Invalid section number: {sys.argv[2]}")
            return 1

    # Get directory of input file for output
    output_dir = os.path.dirname(os.path.abspath(input_file))

    print("=" * 70)
    print("LZSS Decompressor for AC Brotherhood OPTIONS Files")
    print("=" * 70)
    print()
    print(f"Input file: {input_file}")
    if section_filter:
        print(f"Decompressing: Section {section_filter} only")
    else:
        print(f"Decompressing: All sections")
    print()

    # Decompress
    result = decompress_options_file(input_file, section_filter)

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

    for section_num, start_offset, compressed_size, decompressed_data, validation in sections:
        print(f"Section {section_num}:")
        print(f"  Offset:           0x{start_offset:08x} ({start_offset})")
        print(f"  Compressed size:  {compressed_size:6d} bytes")
        print(f"  Decompressed size: {len(decompressed_data):6d} bytes")
        print(f"  Compression ratio: {len(decompressed_data)/compressed_size:.2f}x")

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

            # Overall validation status (based on size and checksum validation)
            all_valid = (validation['compressed_size_match'] and
                        validation['uncompressed_size_match'] and
                        validation['checksum_match'])
            print(f"    Overall:           {'ALL VALIDATION PASSED' if all_valid else 'VALIDATION FAILED'}")
        else:
            print()
            print("  Header Validation: No header found (backward compatibility mode)")

        # Save output
        output_file = os.path.join(output_dir, f"game_uncompressed_{section_num}.bin")
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
    """Test harness to verify decompressor against game output"""
    import os

    print("=" * 70)
    print("LZSS Decompressor Test Suite")
    print("=" * 70)
    print()

    # Test 1: Verify against game_compressed_2.bin -> game_uncompressed_2.bin
    print("Test 1: Game Compressed Data Verification")
    print("-" * 70)

    # Use references/ folder for test files
    script_dir = os.path.dirname(os.path.abspath(__file__))
    compressed_file = os.path.join(script_dir, 'references', 'game_compressed_2.bin')
    uncompressed_file = os.path.join(script_dir, 'references', 'game_uncompressed_2.bin')

    if not os.path.exists(compressed_file):
        print(f"ERROR: Compressed file not found: {compressed_file}")
        return False

    if not os.path.exists(uncompressed_file):
        print(f"ERROR: Uncompressed file not found: {uncompressed_file}")
        return False

    # Load test data
    with open(compressed_file, 'rb') as f:
        compressed = f.read()

    with open(uncompressed_file, 'rb') as f:
        expected = f.read()

    print(f"Compressed size:   {len(compressed):6d} bytes")
    print(f"Expected size:     {len(expected):6d} bytes")
    print()

    # Decompress
    decompressor = LZSSDecompressor()
    result = decompressor.decompress(compressed)

    print(f"Decompressed size: {len(result):6d} bytes")
    print()

    # Verify
    if len(result) != len(expected):
        print(f"FAIL: Size mismatch!")
        print(f"  Expected: {len(expected)} bytes")
        print(f"  Got:      {len(result)} bytes")
        print(f"  Diff:     {abs(len(result) - len(expected))} bytes")
        return False

    # Byte-by-byte comparison
    mismatches = []
    for i in range(len(result)):
        if result[i] != expected[i]:
            mismatches.append(i)
            if len(mismatches) <= 5:  # Show first 5 mismatches
                print(f"Mismatch at byte {i}:")
                print(f"  Expected: 0x{expected[i]:02x}")
                print(f"  Got:      0x{result[i]:02x}")

    if mismatches:
        print(f"\nFAIL: {len(mismatches)} byte mismatches found")
        return False

    print("PASS: All bytes match perfectly!")
    print()

    # Save decompressed output to output/ folder
    output_file = os.path.join(script_dir, 'output', 'lzss_uncompressed.bin')
    with open(output_file, 'wb') as f:
        f.write(result)
    print(f"Saved decompressed output to: lzss_uncompressed.bin ({len(result)} bytes)")
    print()

    # Show sample of output
    print("Sample output (first 64 bytes):")
    for i in range(0, min(64, len(result)), 16):
        hex_str = ' '.join(f'{b:02x}' for b in result[i:i+16])
        print(f"  {i:04x}: {hex_str}")
    print()

    print("=" * 70)
    print("RESULT: 100% ACCURACY - Decompressor is working correctly!")
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
