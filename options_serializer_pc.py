#!/usr/bin/env python3
"""
OPTIONS File Serializer for AC Brotherhood
===========================================

This script takes 3 decompressed section files and recreates a complete OPTIONS file
with proper headers, LZSS compression, and Adler-32 checksums.

The OPTIONS file structure:

Section 1 (40-byte header):
  1. Section ID (16 bytes, all static)
  2. Common pattern (16 bytes): 33 AA FB 57 99 FA 04 10 01 00 02 00 80 00 00 01
  3. Compressed length (4 bytes, little-endian)
  4. Uncompressed length (4 bytes, little-endian)
  5. Adler-32 checksum (4 bytes, little-endian, zero-seed variant)
  6. Compressed LZSS data

Sections 2 & 3 (44-byte header):
  1. Section ID (12 bytes, first 4 bytes = compressed_size + 40, rest static)
  2. Uncompressed length (4 bytes, little-endian)
  3. Common pattern (16 bytes): 33 AA FB 57 99 FA 04 10 01 00 02 00 80 00 00 01
  4. Compressed length (4 bytes, little-endian)
  5. Uncompressed length DUPLICATE (4 bytes, little-endian)
  6. Adler-32 checksum (4 bytes, little-endian, zero-seed variant)
  7. Compressed LZSS data

Footer (5 bytes):
  01 00 00 00 54

Usage:
    python options_serializer_pc.py section1.bin section2.bin section3.bin -o OPTIONS.bin
"""

import sys
import os
import struct
import argparse


# ============================================================================
# ADLER-32 CHECKSUM (Zero-Seed Variant)
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
# LZSS COMPRESSION (Embedded - Exact 1:1 Implementation)
# ============================================================================

def add_bit(output, bit_accum, bit_counter, flag_byte_ptr, bit_value):
    """Add single bit - exact Ghidra implementation"""
    old_bit_counter = bit_counter

    if bit_counter == 0:
        flag_byte_ptr = len(output)
        output.append(0)

    bit_counter += 1
    bit_accum |= (bit_value & 1) << (old_bit_counter & 0x1f)

    if (bit_counter > 7):
        output[flag_byte_ptr] = bit_accum & 0xFF
        bit_accum >>= 8
        bit_counter -= 8
        if bit_counter > 0:
            flag_byte_ptr = len(output)
            output.append(0)

    return output, bit_accum, bit_counter, flag_byte_ptr


def find_best_match(data, pos):
    """
    Find best match scanning backward from current position.
    Data includes 2-byte prefix, pos >= 2.
    """
    if pos < 2:
        return 0, 0

    best_length = 0
    best_offset = 0
    second_best_offset = 0
    max_length = min(263, len(data) - pos)
    max_offset = min(8192, pos)

    # CRITICAL FIX: Reject matches that reference position 0 or 1 (the 2-byte prefix)
    # The game encoder doesn't use matches that go back to the prefix area
    # This typically only affects the very end of files with long runs of zeros
    max_offset = min(max_offset, pos - 2)

    # Scan BACKWARD from current position (closer matches found last)
    for check_pos in range(pos - 1, max(0, pos - max_offset) - 1, -1):
        offset = pos - check_pos
        length = 0

        while (length < max_length and
               pos + length < len(data) and
               data[check_pos + length] == data[pos + length]):
            length += 1

        # Update only if strictly longer (keeps first equal match = highest offset)
        if length > best_length and length >= 2:
            best_length = length
            second_best_offset = best_offset
            best_offset = offset

    # Game adds +1 to LONG match offsets only, requires final offset >= 2
    if best_offset > 0 and best_length >= 2:
        is_short_match = (2 <= best_length <= 5 and (best_offset + 1) <= 256)
        if not is_short_match:
            best_offset += 1
            # Only reject offset < 2 for LONG matches (short matches allow offset=1 for RLE)
            if best_offset < 2:
                return 0, 0  # Reject if final offset < 2

    return best_length, best_offset


def calculate_match_cost(length, offset):
    """Calculate cost in bits for encoding a match"""
    if 2 <= length <= 5 and offset <= 256:
        # Short match: 1 flag + 1 type + 2 length + 8 offset = 12 bits
        return 12
    elif length < 10:
        # Long match: 1 flag + 1 type + 16 data = 18 bits
        return 18
    else:
        # Very long match with continuation bytes
        extra_bytes = (length - 9 + 254) // 255
        return 18 + (extra_bytes * 8)


def compress_lzss_lazy(data):
    """
    Compress using lazy matching (lookahead optimization).
    Uses 2-byte zero prefix - input starts at buffer position 2.
    """
    # Add 2-byte zero prefix
    buffered_data = bytearray([0x00, 0x00]) + bytearray(data)

    output = bytearray()
    bit_accum = 0
    bit_counter = 0
    flag_byte_ptr = 0

    # Start at position 2 (after 2-byte prefix)
    pos = 2

    while pos < len(buffered_data):
        # Find best match at current position
        curr_length, curr_offset = find_best_match(buffered_data, pos)

        # Force literal at the very first position (game behavior)
        if pos == 2:
            curr_length = 0

        # LAZY MATCHING with exact game logic
        if curr_length >= 2 and pos + 1 < len(buffered_data):
            next_length, next_offset = find_best_match(buffered_data, pos + 1)

            # Determine match types
            curr_is_short = (2 <= curr_length <= 5 and curr_offset <= 256)
            next_is_short = (2 <= next_length <= 5 and next_offset <= 256)

            # Calculate adjustment (from decompiled code logic)
            if curr_is_short:
                adjustment = 2
            else:
                adjustment = 1

            # Adjust based on transition between short/long matches
            if curr_is_short and not next_is_short and next_length >= 2:
                adjustment += 2  # local_10 = 2

            if next_is_short and not curr_is_short:
                adjustment -= 1

            if adjustment < 1:
                adjustment = 1

            # SHORT→SHORT transitions use adjustment=1
            if curr_is_short and next_is_short:
                adjustment = 1

            # Compare: if next_length >= curr_length + adjustment, use literal (lazy)
            if next_length >= curr_length + adjustment:
                curr_length = 0  # Force literal

        if curr_length >= 2:
            # Check if match is worth encoding (vs literal)
            match_cost = calculate_match_cost(curr_length, curr_offset)
            literal_cost = 9 * curr_length  # 1 flag bit + 8 data bits per byte

            if match_cost >= literal_cost:
                # Match is not beneficial, use literal (prefer literals when costs equal)
                curr_length = 0

        if curr_length >= 2:
            # Encode match

            # Flag bit 1
            output, bit_accum, bit_counter, flag_byte_ptr = add_bit(
                output, bit_accum, bit_counter, flag_byte_ptr, 1
            )

            if 2 <= curr_length <= 5 and curr_offset <= 256:
                # Short match
                output, bit_accum, bit_counter, flag_byte_ptr = add_bit(
                    output, bit_accum, bit_counter, flag_byte_ptr, 0
                )

                len_bits = curr_length - 2
                for i in range(2):
                    output, bit_accum, bit_counter, flag_byte_ptr = add_bit(
                        output, bit_accum, bit_counter, flag_byte_ptr, (len_bits >> i) & 1
                    )

                output.append((curr_offset - 1) & 0xFF)
            else:
                # Long match
                output, bit_accum, bit_counter, flag_byte_ptr = add_bit(
                    output, bit_accum, bit_counter, flag_byte_ptr, 1
                )

                if curr_length < 10:
                    byte1 = ((curr_length - 2) << 5) | ((curr_offset - 1) & 0x1F)
                    byte2 = ((curr_offset - 1) >> 5) & 0xFF
                    output.append(byte1)
                    output.append(byte2)
                else:
                    byte1 = (curr_offset - 1) & 0x1F
                    byte2 = ((curr_offset - 1) >> 5) & 0xFF
                    output.append(byte1)
                    output.append(byte2)

                    remaining = curr_length - 9
                    while remaining >= 0xFF:
                        output.append(0)
                        remaining -= 0xFF
                    output.append(remaining & 0xFF)

            pos += curr_length
        else:
            # Encode literal
            byte_val = buffered_data[pos]

            output, bit_accum, bit_counter, flag_byte_ptr = add_bit(
                output, bit_accum, bit_counter, flag_byte_ptr, 0
            )
            output.append(byte_val)

            pos += 1

    # Terminator
    output, bit_accum, bit_counter, flag_byte_ptr = add_bit(
        output, bit_accum, bit_counter, flag_byte_ptr, 1
    )
    output, bit_accum, bit_counter, flag_byte_ptr = add_bit(
        output, bit_accum, bit_counter, flag_byte_ptr, 1
    )

    output.append(0x20)
    output.append(0x00)

    # Flush final bits
    if bit_counter > 0:
        output[flag_byte_ptr] = ((1 << bit_counter) - 1) & bit_accum

    return bytes(output)


# ============================================================================
# SECTION HEADER CONSTRUCTION
# ============================================================================

def build_section_header(section_num, compressed_data, uncompressed_size):
    """
    Build a complete section header using the correct 44-byte structure.

    ALL sections use 11 × 4-byte fields (44 bytes total).

    Args:
        section_num: Section number (1, 2, or 3)
        compressed_data: Compressed LZSS bytes (includes 4-byte prefix from LZSS encoder)
        uncompressed_size: Size of uncompressed data

    Returns:
        Complete 44-byte header bytes

    Header Structure (11 fields × 4 bytes = 44 bytes):

    | Offset | Field  | Section 1        | Section 2              | Section 3              |
    |--------|--------|------------------|------------------------|------------------------|
    | 0x00   | Field1 | 0x00000016       | compressed_size + 40   | compressed_size + 40   |
    | 0x04   | Field2 | 0x00FEDBAC       | 0x00000003             | 0x00000000             |
    | 0x08   | Field3 | 0x000000C5       | 0x11FACE11             | 0x21EFFE22             |
    | 0x0C   | Field4 | uncompressed_size| uncompressed_size      | uncompressed_size      |
    | 0x10   | Magic1 | 0x57FBAA33       | 0x57FBAA33             | 0x57FBAA33             |
    | 0x14   | Magic2 | 0x1004FA99       | 0x1004FA99             | 0x1004FA99             |
    | 0x18   | Magic3 | 0x00020001       | 0x00020001             | 0x00020001             |
    | 0x1C   | Magic4 | 0x01000080       | 0x01000080             | 0x01000080             |
    | 0x20   | Field5 | compressed_size  | compressed_size        | compressed_size        |
    | 0x24   | Field6 | uncompressed_size| uncompressed_size      | uncompressed_size      |
    | 0x28   | Field7 | checksum         | checksum               | checksum               |
    """
    compressed_size = len(compressed_data)
    checksum = adler32(compressed_data)

    # Common magic values (fields 5-8) shared by all sections
    MAGIC1 = 0x57FBAA33
    MAGIC2 = 0x1004FA99
    MAGIC3 = 0x00020001
    MAGIC4 = 0x01000080

    if section_num == 1:
        # Section 1 header
        header = struct.pack('<11I',
            0x00000016,        # Field1: Static
            0x00FEDBAC,        # Field2: Static
            0x000000C5,        # Field3: Static
            uncompressed_size, # Field4: Uncompressed size
            MAGIC1,            # Magic1
            MAGIC2,            # Magic2
            MAGIC3,            # Magic3
            MAGIC4,            # Magic4
            compressed_size,   # Field5: Compressed size
            uncompressed_size, # Field6: Uncompressed size (duplicate)
            checksum           # Field7: Checksum
        )
    elif section_num == 2:
        # Section 2 header
        header = struct.pack('<11I',
            compressed_size + 40, # Field1: Calculated
            0x00000003,           # Field2: Static
            0x11FACE11,           # Field3: Static
            uncompressed_size,    # Field4: Uncompressed size
            MAGIC1,               # Magic1
            MAGIC2,               # Magic2
            MAGIC3,               # Magic3
            MAGIC4,               # Magic4
            compressed_size,      # Field5: Compressed size
            uncompressed_size,    # Field6: Uncompressed size (duplicate)
            checksum              # Field7: Checksum
        )
    elif section_num == 3:
        # Section 3 header
        header = struct.pack('<11I',
            compressed_size + 40, # Field1: Calculated
            0x00000000,           # Field2: Static
            0x21EFFE22,           # Field3: Static
            uncompressed_size,    # Field4: Uncompressed size
            MAGIC1,               # Magic1
            MAGIC2,               # Magic2
            MAGIC3,               # Magic3
            MAGIC4,               # Magic4
            compressed_size,      # Field5: Compressed size
            uncompressed_size,    # Field6: Uncompressed size (duplicate)
            checksum              # Field7: Checksum
        )
    else:
        raise ValueError(f"Invalid section number: {section_num}")

    return header


# ============================================================================
# OPTIONS FILE SERIALIZATION
# ============================================================================

def serialize_options_file(section_files, output_file):
    """
    Create a complete OPTIONS file from 3 decompressed section files

    Args:
        section_files: List of 3 paths to decompressed section files
        output_file: Path to output OPTIONS file

    Returns:
        Dictionary with statistics and validation info
    """
    if len(section_files) != 3:
        raise ValueError(f"Expected 3 section files, got {len(section_files)}")

    results = {
        'sections': [],
        'total_size': 0,
        'total_compressed_size': 0,
        'total_uncompressed_size': 0,
    }

    options_data = bytearray()

    for section_num, section_file in enumerate(section_files, 1):
        print(f"\nProcessing Section {section_num}:")
        print(f"  Input file: {section_file}")

        # Read uncompressed data
        if not os.path.exists(section_file):
            raise FileNotFoundError(f"Section file not found: {section_file}")

        with open(section_file, 'rb') as f:
            uncompressed_data = f.read()

        uncompressed_size = len(uncompressed_data)
        print(f"  Uncompressed size: {uncompressed_size} bytes")

        # Compress the section
        compressed_data = compress_lzss_lazy(uncompressed_data)
        compressed_size = len(compressed_data)
        print(f"  Compressed size: {compressed_size} bytes ({100*compressed_size/uncompressed_size:.1f}%)")

        # Build section header
        header = build_section_header(section_num, compressed_data, uncompressed_size)
        print(f"  Header size: {len(header)} bytes")

        # Calculate checksum for verification
        checksum = adler32(compressed_data)
        print(f"  Checksum: 0x{checksum:08X}")

        # Append to OPTIONS file
        section_offset = len(options_data)
        options_data.extend(header)
        options_data.extend(compressed_data)

        section_info = {
            'section_num': section_num,
            'offset': section_offset,
            'header_size': len(header),
            'compressed_size': compressed_size,
            'uncompressed_size': uncompressed_size,
            'checksum': checksum,
            'compression_ratio': uncompressed_size / compressed_size,
        }
        results['sections'].append(section_info)

        results['total_compressed_size'] += compressed_size
        results['total_uncompressed_size'] += uncompressed_size

    # Add footer (5 bytes)
    # The OPTIONS file ends with a 5-byte footer:
    # 01 00 00 00 54
    FOOTER = bytes([0x01, 0x00, 0x00, 0x00, 0x54])
    options_data.extend(FOOTER)
    print(f"\nAdded footer: {FOOTER.hex()} ({len(FOOTER)} bytes)")

    # Write OPTIONS file
    with open(output_file, 'wb') as f:
        f.write(options_data)

    results['total_size'] = len(options_data)

    return results


# ============================================================================
# VALIDATION
# ============================================================================

def validate_options_file(options_file, original_sections):
    """
    Validate the generated OPTIONS file by decompressing and comparing

    Args:
        options_file: Path to generated OPTIONS file
        original_sections: List of original uncompressed section files

    Returns:
        Validation results dictionary
    """
    print("\n" + "=" * 70)
    print("VALIDATION: Decompressing and Comparing")
    print("=" * 70)

    # Import decompression functions
    from lzss_decompressor_pc import LZSSDecompressor, find_sections

    # Read OPTIONS file
    with open(options_file, 'rb') as f:
        options_data = f.read()

    # Find sections
    sections = find_sections(options_data)

    if len(sections) != 3:
        return {
            'valid': False,
            'error': f"Expected 3 sections, found {len(sections)}"
        }

    decompressor = LZSSDecompressor()
    validation_results = []
    all_valid = True

    for i, (section_num, start_offset, end_offset, compressed_data, header_info) in enumerate(sections):
        print(f"\nValidating Section {section_num}:")

        # Decompress
        decompressed = decompressor.decompress(compressed_data)

        # Read original
        with open(original_sections[i], 'rb') as f:
            original = f.read()

        # Compare
        matches = (decompressed == original)

        print(f"  Decompressed size: {len(decompressed)} bytes")
        print(f"  Original size: {len(original)} bytes")
        print(f"  Match: {'YES' if matches else 'NO'}")

        if header_info:
            print(f"  Header validation:")
            print(f"    Compressed size: {header_info.compressed_length} bytes (expected: {len(compressed_data)})")
            print(f"    Uncompressed size: {header_info.uncompressed_length} bytes (expected: {len(original)})")
            print(f"    Checksum: 0x{header_info.checksum:08X}")

        validation_results.append({
            'section_num': section_num,
            'matches': matches,
            'decompressed_size': len(decompressed),
            'original_size': len(original),
        })

        if not matches:
            all_valid = False
            # Find first difference
            for j in range(min(len(decompressed), len(original))):
                if decompressed[j] != original[j]:
                    print(f"  First difference at byte {j}: got 0x{decompressed[j]:02X}, expected 0x{original[j]:02X}")
                    break

    return {
        'valid': all_valid,
        'sections': validation_results,
    }


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Serialize 3 decompressed sections into an OPTIONS file',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python options_serializer_pc.py sec1.bin sec2.bin sec3.bin -o OPTIONS.bin
  python options_serializer_pc.py game_uncompressed_*.bin -o OPTIONS.bin --validate
        """
    )

    parser.add_argument('sections', nargs=3, help='3 decompressed section files')
    parser.add_argument('-o', '--output', required=True, help='Output OPTIONS file')
    parser.add_argument('--validate', action='store_true',
                       help='Validate by decompressing and comparing to original sections')

    args = parser.parse_args()

    print("=" * 70)
    print("OPTIONS File Serializer for AC Brotherhood")
    print("=" * 70)

    # Serialize
    try:
        results = serialize_options_file(args.sections, args.output)
    except Exception as e:
        print(f"\nERROR: {e}")
        return 1

    # Print summary
    print("\n" + "=" * 70)
    print("SERIALIZATION COMPLETE")
    print("=" * 70)
    print(f"\nOutput file: {args.output}")
    print(f"Total size: {results['total_size']} bytes")
    print(f"  Headers: {results['total_size'] - results['total_compressed_size']} bytes")
    print(f"  Compressed data: {results['total_compressed_size']} bytes")
    print(f"  Uncompressed data: {results['total_uncompressed_size']} bytes")
    print(f"  Overall compression ratio: {results['total_uncompressed_size'] / results['total_compressed_size']:.2f}x")

    print("\nSection Details:")
    for section in results['sections']:
        print(f"  Section {section['section_num']}:")
        print(f"    Offset: 0x{section['offset']:08X} ({section['offset']})")
        print(f"    Compressed: {section['compressed_size']} bytes")
        print(f"    Uncompressed: {section['uncompressed_size']} bytes")
        print(f"    Ratio: {section['compression_ratio']:.2f}x")
        print(f"    Checksum: 0x{section['checksum']:08X}")

    # Validate if requested
    if args.validate:
        try:
            validation = validate_options_file(args.output, args.sections)

            print("\n" + "=" * 70)
            if validation['valid']:
                print("VALIDATION PASSED: All sections match original data!")
            else:
                print("VALIDATION FAILED: Some sections do not match")
            print("=" * 70)

            return 0 if validation['valid'] else 1

        except ImportError:
            print("\nWARNING: Could not import decompressor for validation")
            print("Make sure lzss_decompressor_pc.py is in the same directory")

    return 0


if __name__ == "__main__":
    sys.exit(main())
