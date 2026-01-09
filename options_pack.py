#!/usr/bin/env python3
"""
OPTIONS Pack - Reassemble AC Brotherhood OPTIONS Files
=======================================================

This script takes 3 or 4 decompressed section files and recreates a complete
OPTIONS file for either PC or PS3 platforms.

Platform Differences:
--------------------
| Aspect              | PC                      | PS3                          |
|---------------------|-------------------------|------------------------------|
| File prefix         | None                    | 8 bytes (size + CRC32, BE)   |
| Header fields 0-2   | Little-endian           | Big-endian                   |
| Header fields 3-10  | Little-endian           | Little-endian                |
| Section 1 Field3    | 0x000000C5              | 0x000000C6                   |
| Gap marker (sec 4)  | LE, type=0x0E           | BE, type=0x08                |
| Footer              | 5 bytes (01 00 00 00 XX)| None                         |
| Padding             | None                    | Zero-pad to 51,200 bytes     |

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
    python options_pack.py sec1.bin sec2.bin sec3.bin -o OPTIONS.bin --pc
    python options_pack.py sec1.bin sec2.bin sec3.bin sec4.bin -o OPTIONS.PS3 --ps3
    python options_pack.py sec1.bin sec2.bin sec3.bin sec4.bin -o OPTIONS.bin --validate
"""

import sys
import os
import struct
import argparse


# =============================================================================
# CONSTANTS
# =============================================================================

# PS3 file is always padded to this size
PS3_FILE_SIZE = 51200  # 0xC800

# PC footer (5 bytes)
PC_FOOTER = bytes([0x01, 0x00, 0x00, 0x00, 0x54])

# Section names for display
SECTION_NAMES = {
    1: "SaveGame",
    2: "AssassinGlobalProfileData",
    3: "AssassinSingleProfileData",
    4: "AssassinMultiProfileData",
}


# =============================================================================
# CHECKSUMS
# =============================================================================

def adler32_zero_seed(data: bytes) -> int:
    """
    Calculate Adler-32 checksum with zero seed (AC Brotherhood variant).
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
    Used for the PS3 file prefix.

    Parameters: poly=0x04C11DB7, init=0xBAE23CD0, xorout=0xFFFFFFFF,
                refin=true, refout=true
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
# LZSS COMPRESSION
# =============================================================================

from lzss import compress as compress_lzss


# =============================================================================
# SECTION HEADER CONSTRUCTION
# =============================================================================

def build_section_header(section_num: int, compressed_data: bytes,
                         uncompressed_size: int, platform: str) -> bytes:
    """
    Build a complete 44-byte section header.

    Args:
        section_num: Section number (1, 2, 3, or 4)
        compressed_data: Compressed LZSS bytes
        uncompressed_size: Size of uncompressed data
        platform: 'PC' or 'PS3'

    Returns:
        Complete 44-byte header bytes
    """
    compressed_size = len(compressed_data)
    checksum = adler32_zero_seed(compressed_data)

    # Common magic values (always little-endian)
    MAGIC1 = 0x57FBAA33
    MAGIC2 = 0x1004FA99
    MAGIC3 = 0x00020001
    MAGIC4 = 0x01000080

    # Section-specific field values
    if section_num == 1:
        field0 = 0x00000016
        field1 = 0x00FEDBAC
        field2 = 0x000000C6 if platform == 'PS3' else 0x000000C5
    elif section_num == 2:
        field0 = compressed_size + 40
        field1 = 0x00000003
        field2 = 0x11FACE11
    elif section_num == 3:
        field0 = compressed_size + 40
        field1 = 0x00000000
        field2 = 0x21EFFE22
    elif section_num == 4:
        # Section 4 has special format
        field0 = 0x22FEEF21  # Previous section ID byte-swapped
        field1 = 0x00000004
        field2 = 0x00000007
    else:
        raise ValueError(f"Invalid section number: {section_num}")

    # Build header based on platform
    header = bytearray()

    if platform == 'PS3':
        # PS3: Fields 0-2 big-endian, fields 3-10 little-endian
        header.extend(struct.pack('>I', field0))
        header.extend(struct.pack('>I', field1))
        header.extend(struct.pack('>I', field2))
    else:
        # PC: All fields little-endian
        header.extend(struct.pack('<I', field0))
        header.extend(struct.pack('<I', field1))
        header.extend(struct.pack('<I', field2))

    # Fields 3-10 are always little-endian
    header.extend(struct.pack('<I', uncompressed_size))  # Field3
    header.extend(struct.pack('<I', MAGIC1))             # Magic1
    header.extend(struct.pack('<I', MAGIC2))             # Magic2
    header.extend(struct.pack('<I', MAGIC3))             # Magic3
    header.extend(struct.pack('<I', MAGIC4))             # Magic4
    header.extend(struct.pack('<I', compressed_size))    # Field5
    header.extend(struct.pack('<I', uncompressed_size))  # Field6
    header.extend(struct.pack('<I', checksum))           # Field7

    return bytes(header)


def build_gap_marker(section4_size: int, platform: str) -> bytes:
    """
    Build the 8-byte gap marker that appears before Section 4.

    Args:
        section4_size: Total size of Section 4 (header + compressed data)
        platform: 'PC' or 'PS3'

    Returns:
        8-byte gap marker
    """
    size = section4_size + 4

    if platform == 'PS3':
        # PS3: Big-endian, type=0x08
        return struct.pack('>II', size, 0x08)
    else:
        # PC: Little-endian, type=0x0E
        return struct.pack('<II', size, 0x0E)


# =============================================================================
# MAIN SERIALIZATION
# =============================================================================

def serialize_options_file(section_files: list, output_file: str,
                           platform: str) -> dict:
    """
    Create a complete OPTIONS file from decompressed section files.

    Args:
        section_files: List of 3 or 4 paths to decompressed section files
        output_file: Path to output OPTIONS file
        platform: 'PC' or 'PS3'

    Returns:
        Dictionary with statistics and validation info
    """
    num_sections = len(section_files)
    if num_sections not in [3, 4]:
        raise ValueError(f"Expected 3 or 4 section files, got {num_sections}")

    results = {
        'platform': platform,
        'sections': [],
        'total_compressed_size': 0,
        'total_uncompressed_size': 0,
        'has_section4': num_sections == 4,
    }

    # Build section data
    section_data = bytearray()

    for section_num in range(1, num_sections + 1):
        section_file = section_files[section_num - 1]
        section_name = SECTION_NAMES.get(section_num, f"Section {section_num}")

        print(f"\nProcessing Section {section_num} ({section_name}):")
        print(f"  Input file: {section_file}")

        # Read uncompressed data
        if not os.path.exists(section_file):
            raise FileNotFoundError(f"Section file not found: {section_file}")

        with open(section_file, 'rb') as f:
            uncompressed_data = f.read()

        uncompressed_size = len(uncompressed_data)
        print(f"  Uncompressed size: {uncompressed_size} bytes")

        # Compress the section
        compressed_data = compress_lzss(uncompressed_data)
        compressed_size = len(compressed_data)
        ratio_pct = 100 * compressed_size / uncompressed_size if uncompressed_size > 0 else 0
        print(f"  Compressed size: {compressed_size} bytes ({ratio_pct:.1f}%)")

        # Build section header
        header = build_section_header(section_num, compressed_data,
                                      uncompressed_size, platform)
        print(f"  Header size: {len(header)} bytes")

        # Calculate checksum
        checksum = adler32_zero_seed(compressed_data)
        print(f"  Adler-32: 0x{checksum:08X}")

        # For section 4, add gap marker before header
        gap_marker_size = 0
        if section_num == 4:
            section4_total = len(header) + compressed_size
            gap_marker = build_gap_marker(section4_total, platform)
            section_data.extend(gap_marker)
            gap_marker_size = len(gap_marker)
            print(f"  Gap marker: {gap_marker.hex()} ({gap_marker_size} bytes)")

        # Record section offset (after gap marker if any)
        section_offset = len(section_data)

        # Append header and compressed data
        section_data.extend(header)
        section_data.extend(compressed_data)

        section_info = {
            'section_num': section_num,
            'name': section_name,
            'offset': section_offset,
            'header_size': len(header),
            'gap_marker_size': gap_marker_size,
            'compressed_size': compressed_size,
            'uncompressed_size': uncompressed_size,
            'checksum': checksum,
            'compression_ratio': uncompressed_size / compressed_size if compressed_size > 0 else 0,
        }
        results['sections'].append(section_info)

        results['total_compressed_size'] += compressed_size
        results['total_uncompressed_size'] += uncompressed_size

    # Build complete file based on platform
    options_data = bytearray()

    if platform == 'PS3':
        # PS3: 8-byte prefix (size + CRC32, big-endian)
        data_size = len(section_data)
        crc32_value = crc32_ps3(bytes(section_data))

        ps3_prefix = struct.pack('>II', data_size, crc32_value)
        options_data.extend(ps3_prefix)
        options_data.extend(section_data)

        # Pad to PS3_FILE_SIZE
        current_size = len(options_data)
        padding_needed = PS3_FILE_SIZE - current_size

        if padding_needed < 0:
            print(f"\nWARNING: File exceeds PS3 fixed size ({PS3_FILE_SIZE} bytes)")
            padding_needed = 0
        else:
            print(f"\nAdding {padding_needed} bytes of zero padding")

        options_data.extend(bytes(padding_needed))

        results['prefix_size'] = 8
        results['data_size'] = data_size
        results['crc32'] = crc32_value
        results['padding_size'] = padding_needed
        results['footer_size'] = 0

        print(f"PS3 prefix: size={data_size} (0x{data_size:04X}), CRC32=0x{crc32_value:08X}")

    else:
        # PC: No prefix, 5-byte footer
        options_data.extend(section_data)
        options_data.extend(PC_FOOTER)

        results['prefix_size'] = 0
        results['data_size'] = len(section_data)
        results['padding_size'] = 0
        results['footer_size'] = len(PC_FOOTER)

        print(f"\nAdded PC footer: {PC_FOOTER.hex()} ({len(PC_FOOTER)} bytes)")

    # Write output file
    with open(output_file, 'wb') as f:
        f.write(options_data)

    results['total_size'] = len(options_data)

    return results


# =============================================================================
# VALIDATION
# =============================================================================

def validate_options_file(options_file: str, original_sections: list,
                          platform: str) -> dict:
    """
    Validate the generated OPTIONS file by decompressing and comparing.

    Args:
        options_file: Path to generated OPTIONS file
        original_sections: List of original uncompressed section files
        platform: 'PC' or 'PS3'

    Returns:
        Validation results dictionary
    """
    print("\n" + "=" * 70)
    print("VALIDATION: Decompressing and Comparing")
    print("=" * 70)

    # Import unified decompressor
    try:
        from options_unpack import decompress_options_file
    except ImportError:
        return {
            'valid': False,
            'error': "Could not import options_unpack.py"
        }

    # Decompress the generated file
    result = decompress_options_file(options_file, force_platform=platform)

    if result['errors']:
        return {
            'valid': False,
            'error': '; '.join(result['errors'])
        }

    # Validate PS3 prefix if applicable
    prefix_valid = True
    if platform == 'PS3' and result.get('prefix'):
        prefix = result['prefix']
        prefix_valid = prefix['valid']
        print(f"\nPS3 Prefix:")
        print(f"  Expected CRC32: 0x{prefix['crc32_expected']:08X}")
        print(f"  Actual CRC32:   0x{prefix['crc32_actual']:08X}")
        print(f"  Status: {'VALID' if prefix_valid else 'INVALID'}")

    # Compare each section
    sections = result['sections']
    expected_count = len(original_sections)

    if len(sections) != expected_count:
        return {
            'valid': False,
            'error': f"Expected {expected_count} sections, found {len(sections)}",
            'prefix_valid': prefix_valid
        }

    all_valid = True
    validation_results = []

    for i, section in enumerate(sections):
        section_num = section['section_num']
        decompressed = section['decompressed_data']

        # Read original
        with open(original_sections[i], 'rb') as f:
            original = f.read()

        matches = (decompressed == original)

        print(f"\nSection {section_num}:")
        print(f"  Decompressed: {len(decompressed)} bytes")
        print(f"  Original:     {len(original)} bytes")
        print(f"  Match:        {'YES' if matches else 'NO'}")

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
                    print(f"  First diff at byte {j}: got 0x{decompressed[j]:02X}, expected 0x{original[j]:02X}")
                    break
            if len(decompressed) != len(original):
                print(f"  Size mismatch: {len(decompressed)} vs {len(original)}")

    return {
        'valid': all_valid and prefix_valid,
        'prefix_valid': prefix_valid,
        'sections': validation_results,
    }


# =============================================================================
# CLI INTERFACE
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='OPTIONS Pack - Reassemble AC Brotherhood OPTIONS Files (PC & PS3)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Section Names:
  1: SaveGame                   - Core save game data
  2: AssassinGlobalProfileData  - Global profile settings
  3: AssassinSingleProfileData  - Single-player profile data
  4: AssassinMultiProfileData   - Multiplayer profile data (optional)

Examples:
  python options_pack.py sec1.bin sec2.bin sec3.bin -o OPTIONS.bin --pc
  python options_pack.py sec1.bin sec2.bin sec3.bin sec4.bin -o OPTIONS.PS3 --ps3
  python options_pack.py sec1.bin sec2.bin sec3.bin -o OPTIONS.bin --pc --validate
        """
    )

    parser.add_argument('sections', nargs='+', help='3 or 4 decompressed section files')
    parser.add_argument('-o', '--output', required=True, help='Output OPTIONS file')
    parser.add_argument('--pc', action='store_true', help='Output PC format')
    parser.add_argument('--ps3', action='store_true', help='Output PS3 format')
    parser.add_argument('--validate', action='store_true',
                        help='Validate by decompressing and comparing')

    args = parser.parse_args()

    # Validate arguments
    if len(args.sections) not in [3, 4]:
        parser.error(f"Expected 3 or 4 section files, got {len(args.sections)}")

    if args.pc and args.ps3:
        parser.error("Cannot specify both --pc and --ps3")

    if not args.pc and not args.ps3:
        parser.error("Must specify either --pc or --ps3")

    platform = 'PS3' if args.ps3 else 'PC'

    print("=" * 70)
    print("OPTIONS Pack for AC Brotherhood")
    print("=" * 70)
    print()
    print(f"Platform: {platform}")
    print(f"Input sections: {len(args.sections)}")
    for i, sf in enumerate(args.sections, 1):
        section_name = SECTION_NAMES.get(i, f"Section {i}")
        print(f"  {i}. {section_name}: {sf}")

    # Serialize
    try:
        results = serialize_options_file(args.sections, args.output, platform)
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
    print(f"Platform:    {platform}")
    print(f"Total size:  {results['total_size']} bytes (0x{results['total_size']:04X})")

    if platform == 'PS3':
        print(f"  PS3 prefix:    8 bytes (CRC32=0x{results['crc32']:08X})")
        print(f"  Section data:  {results['data_size']} bytes")
        print(f"  Zero padding:  {results['padding_size']} bytes")
    else:
        print(f"  Section data:  {results['data_size']} bytes")
        print(f"  PC footer:     {results['footer_size']} bytes")

    print(f"\nCompression:")
    print(f"  Uncompressed: {results['total_uncompressed_size']} bytes")
    print(f"  Compressed:   {results['total_compressed_size']} bytes")
    if results['total_compressed_size'] > 0:
        ratio = results['total_uncompressed_size'] / results['total_compressed_size']
        print(f"  Ratio:        {ratio:.2f}x")

    print("\nSection Details:")
    for section in results['sections']:
        print(f"  Section {section['section_num']} ({section['name']}):")
        print(f"    Offset:       0x{section['offset']:04X}")
        if section['gap_marker_size'] > 0:
            print(f"    Gap marker:   {section['gap_marker_size']} bytes")
        print(f"    Compressed:   {section['compressed_size']} bytes")
        print(f"    Uncompressed: {section['uncompressed_size']} bytes")
        print(f"    Ratio:        {section['compression_ratio']:.2f}x")
        print(f"    Checksum:     0x{section['checksum']:08X}")

    # Validate if requested
    if args.validate:
        validation = validate_options_file(args.output, args.sections, platform)

        print("\n" + "=" * 70)
        if validation['valid']:
            print("VALIDATION PASSED: All sections match original data!")
        else:
            error = validation.get('error', 'Unknown error')
            print(f"VALIDATION FAILED: {error}")
        print("=" * 70)

        return 0 if validation['valid'] else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
