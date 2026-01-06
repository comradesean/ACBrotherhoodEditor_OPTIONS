#!/usr/bin/env python3
"""
OPTIONS File Serializer for AC Brotherhood PS3
===============================================

This script takes 3-4 decompressed section files and recreates a complete
PS3 OPTIONS file with proper headers, LZSS compression, CRC32 prefix,
and zero-padding.

PS3 OPTIONS File Structure:
--------------------------

1. **8-byte Prefix** (big-endian):
   - Bytes 0-3: Data size (excludes prefix and padding)
   - Bytes 4-7: CRC32 checksum of section data

2. **Section 1** (44-byte header):
   - Fields 0,1,2: Big-endian (Field2=0xC6 for PS3)
   - Fields 3-10: Little-endian (same as PC)
   - Followed by compressed LZSS data

3. **Section 2** (44-byte header):
   - Field2=0x11FACE11
   - Followed by compressed LZSS data

4. **Section 3** (44-byte header):
   - Field2=0x21EFFE22
   - Followed by compressed LZSS data

5. **8-byte Gap Marker** (big-endian):
   - Bytes 0-3: Size (Section 4 total size + 4)
   - Bytes 4-7: Type marker (0x08)

6. **Section 4** (44-byte header):
   - Field0=0x22FEEF21 (previous section ID byte-swapped)
   - Field1=0x00000004 (section number)
   - Field2=0x07 (PS3 controller mappings)
   - Followed by compressed LZSS data

7. **Zero Padding**: Pad to exactly 51,200 bytes (0xC800)

NOTE: Unlike PC files, PS3 files have NO 5-byte footer after section data.

Usage:
------
    python options_serializer_ps3.py sec1.bin sec2.bin sec3.bin sec4.bin -o OPTIONS.PS3
    python options_serializer_ps3.py sec1.bin sec2.bin sec3.bin -o OPTIONS.PS3  # No section 4
"""

import sys
import os
import struct
import argparse


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
# LZSS COMPRESSION (Imported from shared module)
# ============================================================================

from lzss import compress as compress_lzss_lazy


# ============================================================================
# SECTION HEADER CONSTRUCTION (PS3 Format)
# ============================================================================

def build_section_header_ps3(section_num, compressed_data, uncompressed_size):
    """
    Build a complete PS3 section header using the 44-byte structure.

    PS3 headers have fields 0,1,2 in big-endian format.
    Fields 3-10 remain in little-endian format.

    Args:
        section_num: Section number (1, 2, 3, or 4)
        compressed_data: Compressed LZSS bytes
        uncompressed_size: Size of uncompressed data

    Returns:
        Complete 44-byte header bytes

    Header Structure (PS3):
        Fields 0,1,2: Big-endian
        Fields 3-10: Little-endian

    | Offset | Field  | Section 1        | Section 2              | Section 3              | Section 4              |
    |--------|--------|------------------|------------------------|------------------------|------------------------|
    | 0x00   | Field0 | 0x00000016       | compressed_size + 40   | compressed_size + 40   | compressed_size + 40   |
    | 0x04   | Field1 | 0x00FEDBAC       | 0x00000003             | 0x00000000             | 0x00000003             |
    | 0x08   | Field2 | 0x000000C6       | 0x11FACE11             | 0x21EFFE22             | 0x00000007             |
    | 0x0C   | Field3 | uncompressed_size| uncompressed_size      | uncompressed_size      | uncompressed_size      |
    | 0x10   | Magic1 | 0x57FBAA33       | 0x57FBAA33             | 0x57FBAA33             | 0x57FBAA33             |
    | 0x14   | Magic2 | 0x1004FA99       | 0x1004FA99             | 0x1004FA99             | 0x1004FA99             |
    | 0x18   | Magic3 | 0x00020001       | 0x00020001             | 0x00020001             | 0x00020001             |
    | 0x1C   | Magic4 | 0x01000080       | 0x01000080             | 0x01000080             | 0x01000080             |
    | 0x20   | Field5 | compressed_size  | compressed_size        | compressed_size        | compressed_size        |
    | 0x24   | Field6 | uncompressed_size| uncompressed_size      | uncompressed_size      | uncompressed_size      |
    | 0x28   | Field7 | checksum         | checksum               | checksum               | checksum               |
    """
    compressed_size = len(compressed_data)
    checksum = adler32(compressed_data)

    # Common magic values (fields 4-7 in struct) - little-endian
    MAGIC1 = 0x57FBAA33
    MAGIC2 = 0x1004FA99
    MAGIC3 = 0x00020001
    MAGIC4 = 0x01000080

    # Field values by section (PS3 specific values)
    if section_num == 1:
        field0 = 0x00000016
        field1 = 0x00FEDBAC
        field2 = 0x000000C6  # PS3 uses 0xC6 (PC uses 0xC5)
    elif section_num == 2:
        field0 = compressed_size + 40
        field1 = 0x00000003
        field2 = 0x11FACE11
    elif section_num == 3:
        field0 = compressed_size + 40
        field1 = 0x00000000
        field2 = 0x21EFFE22
    elif section_num == 4:
        # Section 4 has a special format:
        # Field 0 = Previous section's identifier (0x21EFFE22) byte-swapped
        # Field 1 = 0x00000004 (section number)
        # Field 2 = 0x00000007 (section 4 identifier)
        field0 = 0x22FEEF21  # 0x21EFFE22 byte-swapped as BE
        field1 = 0x00000004
        field2 = 0x00000007
    else:
        raise ValueError(f"Invalid section number: {section_num}")

    # Build header: fields 0,1,2 big-endian; fields 3-10 little-endian
    header = bytearray()

    # Fields 0, 1, 2 - big-endian
    header.extend(struct.pack('>I', field0))
    header.extend(struct.pack('>I', field1))
    header.extend(struct.pack('>I', field2))

    # Fields 3-10 - little-endian
    header.extend(struct.pack('<I', uncompressed_size))  # Field3
    header.extend(struct.pack('<I', MAGIC1))             # Magic1
    header.extend(struct.pack('<I', MAGIC2))             # Magic2
    header.extend(struct.pack('<I', MAGIC3))             # Magic3
    header.extend(struct.pack('<I', MAGIC4))             # Magic4
    header.extend(struct.pack('<I', compressed_size))    # Field5
    header.extend(struct.pack('<I', uncompressed_size))  # Field6
    header.extend(struct.pack('<I', checksum))           # Field7

    return bytes(header)


def build_gap_marker(section4_size):
    """
    Build the 8-byte gap marker that appears before Section 4.

    Format (big-endian):
        Bytes 0-3: Size (Section 4 header + compressed data + 4)
        Bytes 4-7: Type marker (0x08)

    Args:
        section4_size: Total size of Section 4 (header + compressed data)

    Returns:
        8-byte gap marker
    """
    size = section4_size + 4  # Add 4 to section size
    marker = struct.pack('>I', size)  # Size (big-endian)
    marker += struct.pack('>I', 0x08)  # Type marker (big-endian)
    return marker


# ============================================================================
# PS3 OPTIONS FILE SERIALIZATION
# ============================================================================

# PS3 file must be exactly this size
PS3_FILE_SIZE = 51200  # 0xC800

# NOTE: PS3 files do NOT have a footer after section data.
# The PC version has a 5-byte footer (01 00 00 00 54), but PS3 files
# end immediately after Section 4's LZSS terminator, followed by zero padding.


def serialize_options_file_ps3(section_files, output_file):
    """
    Create a complete PS3 OPTIONS file from 3-4 decompressed section files.

    Args:
        section_files: List of 3 or 4 paths to decompressed section files
        output_file: Path to output PS3 OPTIONS file

    Returns:
        Dictionary with statistics and validation info
    """
    num_sections = len(section_files)
    if num_sections < 3 or num_sections > 4:
        raise ValueError(f"Expected 3 or 4 section files, got {num_sections}")

    results = {
        'sections': [],
        'total_size': 0,
        'total_compressed_size': 0,
        'total_uncompressed_size': 0,
        'has_section4': num_sections == 4,
    }

    # Build section data (without PS3 prefix)
    section_data = bytearray()

    # Process sections 1-3
    for section_num in range(1, 4):
        section_file = section_files[section_num - 1]
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

        # Build section header (PS3 format)
        header = build_section_header_ps3(section_num, compressed_data, uncompressed_size)
        print(f"  Header size: {len(header)} bytes")

        # Calculate checksum for verification
        checksum = adler32(compressed_data)
        print(f"  Adler-32 Checksum: 0x{checksum:08X}")

        # Append to section data
        section_offset = len(section_data)
        section_data.extend(header)
        section_data.extend(compressed_data)

        section_info = {
            'section_num': section_num,
            'offset': section_offset,
            'header_size': len(header),
            'compressed_size': compressed_size,
            'uncompressed_size': uncompressed_size,
            'checksum': checksum,
            'compression_ratio': uncompressed_size / compressed_size if compressed_size > 0 else 0,
        }
        results['sections'].append(section_info)

        results['total_compressed_size'] += compressed_size
        results['total_uncompressed_size'] += uncompressed_size

    # Process Section 4 if provided
    if num_sections == 4:
        section_file = section_files[3]
        print(f"\nProcessing Section 4 (PS3 Controller Mappings):")
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

        # Build section header (PS3 format)
        header = build_section_header_ps3(4, compressed_data, uncompressed_size)
        print(f"  Header size: {len(header)} bytes")

        # Calculate total Section 4 size for gap marker
        section4_total = len(header) + compressed_size

        # Build gap marker
        gap_marker = build_gap_marker(section4_total)
        print(f"  Gap marker: {gap_marker.hex()} ({len(gap_marker)} bytes)")

        # Calculate checksum for verification
        checksum = adler32(compressed_data)
        print(f"  Adler-32 Checksum: 0x{checksum:08X}")

        # Append gap marker, header, and compressed data
        section_offset = len(section_data)
        section_data.extend(gap_marker)
        section_data.extend(header)
        section_data.extend(compressed_data)

        section_info = {
            'section_num': 4,
            'offset': section_offset,
            'header_size': len(header),
            'gap_marker_size': len(gap_marker),
            'compressed_size': compressed_size,
            'uncompressed_size': uncompressed_size,
            'checksum': checksum,
            'compression_ratio': uncompressed_size / compressed_size if compressed_size > 0 else 0,
        }
        results['sections'].append(section_info)

        results['total_compressed_size'] += compressed_size
        results['total_uncompressed_size'] += uncompressed_size

    # NOTE: PS3 files have no footer - data ends with Section 4's LZSS terminator
    # (Unlike PC files which have a 5-byte footer: 01 00 00 00 54)

    # Calculate data size (for PS3 prefix)
    data_size = len(section_data)
    print(f"Section data size: {data_size} bytes (0x{data_size:04X})")

    # Calculate CRC32 of section data
    crc32_value = crc32_ps3(bytes(section_data))
    print(f"CRC32: 0x{crc32_value:08X}")

    # Build PS3 prefix (8 bytes, big-endian)
    ps3_prefix = struct.pack('>I', data_size) + struct.pack('>I', crc32_value)
    print(f"PS3 prefix: {ps3_prefix.hex()} ({len(ps3_prefix)} bytes)")

    # Build complete file
    options_data = bytearray()
    options_data.extend(ps3_prefix)
    options_data.extend(section_data)

    # Calculate padding needed
    current_size = len(options_data)
    padding_needed = PS3_FILE_SIZE - current_size

    if padding_needed < 0:
        print(f"\nWARNING: File is larger than PS3 fixed size!")
        print(f"  Current size: {current_size} bytes")
        print(f"  PS3 fixed size: {PS3_FILE_SIZE} bytes")
        print(f"  Overflow: {-padding_needed} bytes")
        padding_needed = 0
    else:
        print(f"\nAdding {padding_needed} bytes of zero padding")

    options_data.extend(bytes(padding_needed))

    # Write OPTIONS file
    with open(output_file, 'wb') as f:
        f.write(options_data)

    results['total_size'] = len(options_data)
    results['data_size'] = data_size
    results['crc32'] = crc32_value
    results['padding_size'] = padding_needed

    return results


# ============================================================================
# VALIDATION
# ============================================================================

def validate_ps3_options_file(options_file, original_sections):
    """
    Validate the generated PS3 OPTIONS file by decompressing and comparing.

    Args:
        options_file: Path to generated PS3 OPTIONS file
        original_sections: List of original uncompressed section files

    Returns:
        Validation results dictionary
    """
    print("\n" + "=" * 70)
    print("VALIDATION: Decompressing and Comparing")
    print("=" * 70)

    # Import decompression functions from PS3 decompressor
    try:
        from lzss_decompressor_ps3 import LZSSDecompressor, find_sections_ps3, parse_ps3_prefix
    except ImportError:
        return {
            'valid': False,
            'error': "Could not import lzss_decompressor_ps3.py"
        }

    # Read OPTIONS file
    with open(options_file, 'rb') as f:
        options_data = f.read()

    # Validate PS3 prefix
    data_size, crc32_expected, crc32_actual, crc_valid = parse_ps3_prefix(options_data)
    print(f"\nPS3 Prefix Validation:")
    print(f"  Data size: {data_size} bytes")
    print(f"  Expected CRC32: 0x{crc32_expected:08X}")
    print(f"  Actual CRC32: 0x{crc32_actual:08X}")
    print(f"  CRC32 Valid: {'YES' if crc_valid else 'NO'}")

    # Find sections
    sections = find_sections_ps3(options_data, prefix_offset=8)

    expected_sections = len(original_sections)
    if len(sections) != expected_sections:
        return {
            'valid': False,
            'error': f"Expected {expected_sections} sections, found {len(sections)}",
            'crc_valid': crc_valid
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
        'valid': all_valid and crc_valid,
        'crc_valid': crc_valid,
        'sections': validation_results,
    }


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Serialize 3-4 decompressed sections into a PS3 OPTIONS file',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # With 4 sections (includes controller mappings)
  python options_serializer_ps3.py sec1.bin sec2.bin sec3.bin sec4.bin -o OPTIONS.PS3

  # With 3 sections (no controller mappings)
  python options_serializer_ps3.py section1.bin section2.bin section3.bin -o OPTIONS.PS3

  # With validation
  python options_serializer_ps3.py sec1.bin sec2.bin sec3.bin sec4.bin -o OPTIONS.PS3 --validate
        """
    )

    parser.add_argument('sections', nargs='+', help='3 or 4 decompressed section files')
    parser.add_argument('-o', '--output', required=True, help='Output PS3 OPTIONS file')
    parser.add_argument('--validate', action='store_true',
                       help='Validate by decompressing and comparing to original sections')

    args = parser.parse_args()

    # Validate number of section files
    if len(args.sections) < 3 or len(args.sections) > 4:
        print(f"Error: Expected 3 or 4 section files, got {len(args.sections)}")
        return 1

    print("=" * 70)
    print("PS3 OPTIONS File Serializer for AC Brotherhood")
    print("=" * 70)
    print()
    print(f"Input sections: {len(args.sections)}")
    for i, sf in enumerate(args.sections, 1):
        print(f"  Section {i}: {sf}")

    # Serialize
    try:
        results = serialize_options_file_ps3(args.sections, args.output)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Print summary
    print("\n" + "=" * 70)
    print("SERIALIZATION COMPLETE")
    print("=" * 70)
    print(f"\nOutput file: {args.output}")
    print(f"Total size: {results['total_size']} bytes (0x{results['total_size']:04X})")
    print(f"  PS3 prefix: 8 bytes")
    print(f"  Section data: {results['data_size']} bytes")
    print(f"  Zero padding: {results['padding_size']} bytes")
    print(f"CRC32: 0x{results['crc32']:08X}")
    print(f"  Compressed data: {results['total_compressed_size']} bytes")
    print(f"  Uncompressed data: {results['total_uncompressed_size']} bytes")
    if results['total_compressed_size'] > 0:
        print(f"  Overall compression ratio: {results['total_uncompressed_size'] / results['total_compressed_size']:.2f}x")

    print("\nSection Details:")
    for section in results['sections']:
        print(f"  Section {section['section_num']}:")
        print(f"    Offset: 0x{section['offset']:08X} ({section['offset']})")
        if 'gap_marker_size' in section:
            print(f"    Gap marker: {section['gap_marker_size']} bytes")
        print(f"    Compressed: {section['compressed_size']} bytes")
        print(f"    Uncompressed: {section['uncompressed_size']} bytes")
        print(f"    Ratio: {section['compression_ratio']:.2f}x")
        print(f"    Checksum: 0x{section['checksum']:08X}")

    # Validate if requested
    if args.validate:
        try:
            validation = validate_ps3_options_file(args.output, args.sections)

            print("\n" + "=" * 70)
            if validation['valid']:
                print("VALIDATION PASSED: All sections match original data and CRC32 is valid!")
            else:
                if not validation.get('crc_valid', True):
                    print("VALIDATION FAILED: CRC32 mismatch")
                else:
                    print("VALIDATION FAILED: Some sections do not match")
            print("=" * 70)

            return 0 if validation['valid'] else 1

        except ImportError:
            print("\nWARNING: Could not import decompressor for validation")
            print("Make sure lzss_decompressor_ps3.py is in the same directory")

    return 0


if __name__ == "__main__":
    sys.exit(main())
