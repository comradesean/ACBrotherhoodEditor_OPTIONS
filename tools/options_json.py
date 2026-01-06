#!/usr/bin/env python3
"""
OPTIONS JSON Serializer for AC Brotherhood
===========================================

Converts OPTIONS binary files to JSON and back.
Supports both PC and PS3 formats with automatic detection.

Usage:
    # Convert OPTIONS to JSON (auto-detects format)
    python options_json.py OPTIONS.bin -o options.json
    python options_json.py OPTIONS.PS3 -o options.json

    # Force specific format
    python options_json.py OPTIONS.bin --format pc -o options.json
    python options_json.py OPTIONS.bin --format ps3 -o options.json

    # Convert JSON back to OPTIONS
    python options_json.py options.json -o OPTIONS.bin --to-binary

    # Pretty print JSON
    python options_json.py OPTIONS.bin -o options.json --pretty
"""

import sys
import os
import json
import struct
import argparse

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lzss import compress
from lzss_decompressor_pc import LZSSDecompressor


# =============================================================================
# CONSTANTS
# =============================================================================

# Section identification hashes (found at offset 0x0A in decompressed data)
SECTION_HASHES = {
    0xBDBE3B52: "section1_system",
    0x305AE1A8: "section2_settings",
    0xC9876D66: "section3_progress",
    0xB4B55039: "section4_controller",  # PS3 only
}

# Known property hashes with human-readable names
KNOWN_HASHES = {
    # Section 2 - Controls
    0xA15FACF2: "invert_3p_x",
    0xC36B150F: "invert_3p_y",
    0x9CCE0247: "invert_1p_x",
    0x56932719: "invert_1p_y",
    0x962BD533: "action_camera_frequency",
    0x7ED0EABB: "brightness",
    0xDE6CD4AB: "blood_enabled",
    # Section 2 - HUD
    0x039BEE69: "hud_health_meter",
    0x761E3CE0: "hud_minimap",
    # Section 2 - Unlocks
    0x00788F42: "templar_lair_trajans_market",
    0x006FF456: "templar_lair_tivoli_aqueduct",
    # Section 2 - Costumes
    0x0286EAC2: "costume_bitfield",
    # Section 3
    0x4DBC7DA7: "popup_dismissed_flag",
    0xBF4C2013: "unknown_s3_1",
    0x3B546966: "unknown_s3_2",
    0x5B95F10B: "unknown_s3_3",
    0x2A4E8A90: "unknown_s3_4",
    0x496F8780: "unknown_s3_5",
}

# Record type descriptions
TYPE_NAMES = {
    0x00: "complex",
    0x04: "controller",
    0x0E: "boolean",
    0x11: "integer",
    0x12: "version_v10",
    0x15: "float_related",
    0x16: "version_v105",
    0x1E: "special",
    0x4F: "section1_special",
}

# PS3 file characteristics
PS3_FILE_SIZE = 51200  # PS3 files are always padded to this size


# =============================================================================
# CHECKSUM FUNCTIONS
# =============================================================================

def adler32_zero_seed(data: bytes) -> int:
    """Adler-32 with zero seed (AC Brotherhood variant)"""
    MOD_ADLER = 65521
    s1 = 0
    s2 = 0
    for byte in data:
        s1 = (s1 + byte) % MOD_ADLER
        s2 = (s2 + s1) % MOD_ADLER
    return (s2 << 16) | s1


def crc32_ps3(data: bytes) -> int:
    """CRC32 with PS3's custom parameters"""
    crc = 0xBAE23CD0
    for byte in data:
        byte = int('{:08b}'.format(byte)[::-1], 2)
        crc ^= (byte << 24)
        for _ in range(8):
            if crc & 0x80000000:
                crc = ((crc << 1) ^ 0x04C11DB7) & 0xFFFFFFFF
            else:
                crc = (crc << 1) & 0xFFFFFFFF
    crc = int('{:032b}'.format(crc)[::-1], 2)
    return (crc ^ 0xFFFFFFFF) & 0xFFFFFFFF


# =============================================================================
# FORMAT DETECTION
# =============================================================================

def detect_format(data: bytes) -> str:
    """
    Auto-detect whether OPTIONS file is PC or PS3 format.

    Detection criteria:
    1. PS3 files are exactly 51,200 bytes (padded)
    2. PS3 has 8-byte prefix: [data_size BE][crc32 BE]
    3. PS3 has 4 sections, PC has 3

    Returns:
        'PC' or 'PS3'
    """
    # Check file size - PS3 is always 51,200 bytes
    if len(data) == PS3_FILE_SIZE:
        # Verify PS3 prefix structure
        if len(data) >= 8:
            data_size = struct.unpack('>I', data[0:4])[0]
            # PS3 data size should be reasonable (< file size - 8)
            if 100 < data_size < PS3_FILE_SIZE - 8:
                # Look for magic pattern to confirm
                MAGIC = b'\x33\xAA\xFB\x57\x99\xFA\x04\x10'
                if MAGIC in data[8:100]:
                    return 'PS3'

    # Check for PC format characteristics
    # PC files end with 5-byte footer and have 3 sections
    if len(data) > 5:
        # PC footer is 01 00 00 00 XX (where XX is network interface count)
        footer = data[-5:]
        if footer[0:4] == b'\x01\x00\x00\x00':
            return 'PC'

    # Default to PC if unsure
    return 'PC'


# =============================================================================
# SECTION PARSING
# =============================================================================

def find_sections(data: bytes, format_type: str) -> list:
    """
    Find compressed sections in OPTIONS file.

    Args:
        data: Raw file data
        format_type: 'PC' or 'PS3'

    Returns:
        List of section dictionaries with header info and compressed data
    """
    MAGIC = b'\x33\xAA\xFB\x57\x99\xFA\x04\x10\x01\x00\x02\x00\x80\x00\x00\x01'

    sections = []
    start_pos = 8 if format_type == 'PS3' else 0
    pos = start_pos

    while True:
        # Find the magic pattern
        pattern_pos = data.find(MAGIC, pos)
        if pattern_pos == -1:
            break

        # Header starts 0x10 bytes before the pattern
        header_start = pattern_pos - 0x10
        if header_start < start_pos:
            pos = pattern_pos + len(MAGIC)
            continue

        # Read header fields based on format
        if format_type == 'PS3':
            # PS3: Fields 0,1,2 are big-endian
            field0 = struct.unpack('>I', data[header_start:header_start+4])[0]
            field1 = struct.unpack('>I', data[header_start+4:header_start+8])[0]
            field2 = struct.unpack('>I', data[header_start+8:header_start+12])[0]
        else:
            # PC: All fields little-endian
            field0 = struct.unpack('<I', data[header_start:header_start+4])[0]
            field1 = struct.unpack('<I', data[header_start+4:header_start+8])[0]
            field2 = struct.unpack('<I', data[header_start+8:header_start+12])[0]

        # Field 3 onwards are always little-endian
        field3 = struct.unpack('<I', data[header_start+12:header_start+16])[0]  # uncompressed size

        # After magic pattern: compressed_size, uncompressed_size, checksum
        sizes_offset = pattern_pos + len(MAGIC)
        if sizes_offset + 12 > len(data):
            break

        compressed_size = struct.unpack('<I', data[sizes_offset:sizes_offset+4])[0]
        uncompressed_size = struct.unpack('<I', data[sizes_offset+4:sizes_offset+8])[0]
        checksum = struct.unpack('<I', data[sizes_offset+8:sizes_offset+12])[0]

        # Compressed data starts after the header (44 bytes from header_start)
        data_start = header_start + 44
        compressed_data = data[data_start:data_start + compressed_size]

        section = {
            'header_offset': header_start,
            'data_offset': data_start,
            'field0': field0,
            'field1': field1,
            'field2': field2,
            'compressed_size': compressed_size,
            'uncompressed_size': uncompressed_size,
            'checksum': checksum,
            'compressed_data': compressed_data,
        }
        sections.append(section)

        pos = data_start + compressed_size

    return sections


# =============================================================================
# RECORD PARSING
# =============================================================================

def parse_section1_records(data: bytes) -> list:
    """
    Parse Section 1 records (21-byte with exceptions).
    Section 1 has variable record sizes, identified by 0x0B markers.
    """
    records = []

    # Find all 0x0B markers and parse records
    pos = 0x26  # First record typically at 0x26
    while pos < len(data) - 13:
        if data[pos] == 0x0B:
            # Determine record size by finding next marker
            next_pos = pos + 1
            while next_pos < len(data) and next_pos < pos + 35:
                if data[next_pos] == 0x0B and next_pos - pos >= 13:
                    break
                next_pos += 1

            record_size = min(next_pos - pos, 29) if next_pos < len(data) else 21
            record_data = data[pos:pos + record_size]

            if len(record_data) >= 13:
                record = {
                    'offset': pos,
                    'size': len(record_data),
                    'marker': record_data[0],
                    'value': record_data[1:5].hex(),
                    'type': record_data[5],
                    'type_name': TYPE_NAMES.get(record_data[5], f"0x{record_data[5]:02x}"),
                    'hash': struct.unpack('<I', record_data[9:13])[0],
                    'raw': record_data.hex(),
                }

                if record['hash'] in KNOWN_HASHES:
                    record['name'] = KNOWN_HASHES[record['hash']]

                records.append(record)

            pos = next_pos
        else:
            pos += 1

    return records


def parse_section2_records(data: bytes) -> list:
    """Parse Section 2 records (18-byte property records)"""
    records = []
    pos = 0

    while pos < len(data) - 18:
        if data[pos] == 0x0B:
            record_data = data[pos:pos+18]

            record = {
                'offset': pos,
                'marker': record_data[0],
                'value': record_data[1],
                'type': record_data[2],
                'type_name': TYPE_NAMES.get(record_data[2], f"0x{record_data[2]:02x}"),
                'padding': record_data[3:6].hex(),
                'hash': struct.unpack('<I', record_data[6:10])[0],
                'type_data': record_data[10:18].hex(),
            }

            if record['hash'] in KNOWN_HASHES:
                record['name'] = KNOWN_HASHES[record['hash']]

            # Parse type-specific data
            if record['type'] == 0x11:
                # Integer type - byte 0x10 is the integer value
                record['int_value'] = record_data[16]
            elif record['type'] == 0x00:
                # Complex type - may contain float or other data
                record['extra_value'] = struct.unpack('<I', record_data[10:14])[0]

            records.append(record)
            pos += 18
        else:
            pos += 1

    return records


def parse_section3_records(data: bytes) -> list:
    """Parse Section 3 records (18-byte, hash at start)"""
    records = []
    pos = 0x18  # Skip header

    while pos < len(data) - 18:
        # Section 3 has different layout - look for marker at +0x0C
        if pos + 12 < len(data) and data[pos + 12] == 0x0B:
            record_data = data[pos:pos+18]

            record = {
                'offset': pos,
                'hash': struct.unpack('<I', record_data[0:4])[0],
                'padding1': record_data[4:12].hex(),
                'marker': record_data[12],
                'value': record_data[13],
                'type': record_data[14],
                'type_name': TYPE_NAMES.get(record_data[14], f"0x{record_data[14]:02x}"),
                'padding2': record_data[15:18].hex(),
            }

            if record['hash'] in KNOWN_HASHES:
                record['name'] = KNOWN_HASHES[record['hash']]

            records.append(record)
            pos += 18
        else:
            pos += 1

    return records


def parse_section4_records(data: bytes) -> list:
    """Parse Section 4 (PS3 controller mappings) - 85-byte button records"""
    records = []

    # Button record signature
    BUTTON_SIG = b'\xA8\xCF\x5F\xF9\x43'

    pos = 0
    while True:
        sig_pos = data.find(BUTTON_SIG, pos)
        if sig_pos == -1 or sig_pos + 85 > len(data):
            break

        record_data = data[sig_pos:sig_pos+85]

        record = {
            'offset': sig_pos,
            'signature': record_data[0:5].hex(),
            'record_size': struct.unpack('>I', record_data[5:9])[0],
            'record_count': struct.unpack('>I', record_data[9:13])[0],
            'controller_hash': struct.unpack('>I', record_data[13:17])[0],
            'button_id': record_data[29],
            'raw': record_data.hex(),
        }

        records.append(record)
        pos = sig_pos + 85

    return records


# =============================================================================
# OPTIONS TO JSON
# =============================================================================

def options_to_json(input_file: str, format_type: str = None, verbose: bool = False) -> dict:
    """
    Convert OPTIONS binary file to JSON structure.

    Stores only essential data - headers, checksums, and CRCs are recalculated
    during reconstruction.

    Args:
        input_file: Path to OPTIONS file
        format_type: 'PC', 'PS3', or None for auto-detect
        verbose: Include parsed record details (for debugging/inspection)

    Returns:
        Dictionary suitable for JSON serialization
    """
    with open(input_file, 'rb') as f:
        data = f.read()

    # Auto-detect format if not specified
    if format_type is None:
        format_type = detect_format(data)

    result = {
        'format': format_type,
        'sections': [],
    }

    # PC-only: preserve network interface count (footer byte from uPlay)
    if format_type == 'PC' and len(data) >= 5:
        result['pc_network_interface_count'] = data[-1]

    # Find and decompress sections
    sections = find_sections(data, format_type)
    decompressor = LZSSDecompressor()

    for i, section_info in enumerate(sections):
        section_num = i + 1
        decompressed = decompressor.decompress(section_info['compressed_data'])

        section = {
            'section_number': section_num,
            'data': decompressed.hex(),
        }

        # Verbose mode: add parsed details for inspection
        if verbose:
            section_hash = 0
            if len(decompressed) >= 14:
                section_hash = struct.unpack('<I', decompressed[10:14])[0]

            section['_info'] = {
                'hash': f"0x{section_hash:08X}",
                'name': SECTION_HASHES.get(section_hash, "unknown"),
                'size': len(decompressed),
            }

            records = []
            if section_num == 1:
                records = parse_section1_records(decompressed)
            elif section_num == 2:
                records = parse_section2_records(decompressed)
            elif section_num == 3:
                records = parse_section3_records(decompressed)
            elif section_num == 4:
                records = parse_section4_records(decompressed)

            if records:
                section['_info']['record_count'] = len(records)
                section['_records'] = records

        result['sections'].append(section)

    return result


# =============================================================================
# JSON TO OPTIONS
# =============================================================================

def build_section_header_pc(section_num: int, compressed_data: bytes, uncompressed_size: int) -> bytes:
    """Build PC section header (44 bytes)"""
    compressed_size = len(compressed_data)
    checksum = adler32_zero_seed(compressed_data)

    MAGIC1 = 0x57FBAA33
    MAGIC2 = 0x1004FA99
    MAGIC3 = 0x00020001
    MAGIC4 = 0x01000080

    if section_num == 1:
        field0, field1, field2 = 0x00000016, 0x00FEDBAC, 0x000000C5
    elif section_num == 2:
        field0, field1, field2 = compressed_size + 40, 0x00000003, 0x11FACE11
    elif section_num == 3:
        field0, field1, field2 = compressed_size + 40, 0x00000000, 0x21EFFE22
    else:
        raise ValueError(f"Invalid PC section number: {section_num}")

    return struct.pack('<11I',
        field0, field1, field2, uncompressed_size,
        MAGIC1, MAGIC2, MAGIC3, MAGIC4,
        compressed_size, uncompressed_size, checksum
    )


def build_section_header_ps3(section_num: int, compressed_data: bytes, uncompressed_size: int) -> bytes:
    """Build PS3 section header (44 bytes) - fields 0-2 big-endian"""
    compressed_size = len(compressed_data)
    checksum = adler32_zero_seed(compressed_data)

    MAGIC1 = 0x57FBAA33
    MAGIC2 = 0x1004FA99
    MAGIC3 = 0x00020001
    MAGIC4 = 0x01000080

    if section_num == 1:
        field0, field1, field2 = 0x00000016, 0x00FEDBAC, 0x000000C6
    elif section_num == 2:
        field0, field1, field2 = compressed_size + 40, 0x00000003, 0x11FACE11
    elif section_num == 3:
        field0, field1, field2 = compressed_size + 40, 0x00000000, 0x21EFFE22
    elif section_num == 4:
        field0, field1, field2 = 0x22FEEF21, 0x00000004, 0x00000007
    else:
        raise ValueError(f"Invalid PS3 section number: {section_num}")

    header = bytearray()
    # PS3: Fields 0,1,2 are big-endian
    header.extend(struct.pack('>I', field0))
    header.extend(struct.pack('>I', field1))
    header.extend(struct.pack('>I', field2))
    # Fields 3-10 are little-endian
    header.extend(struct.pack('<I', uncompressed_size))
    header.extend(struct.pack('<I', MAGIC1))
    header.extend(struct.pack('<I', MAGIC2))
    header.extend(struct.pack('<I', MAGIC3))
    header.extend(struct.pack('<I', MAGIC4))
    header.extend(struct.pack('<I', compressed_size))
    header.extend(struct.pack('<I', uncompressed_size))
    header.extend(struct.pack('<I', checksum))

    return bytes(header)


def json_to_options(json_data: dict, output_file: str) -> int:
    """
    Convert JSON structure back to OPTIONS binary file.

    Args:
        json_data: Dictionary from options_to_json
        output_file: Path to output file

    Returns:
        Size of output file in bytes
    """
    format_type = json_data.get('format', 'PC')
    is_ps3 = format_type == 'PS3'

    output = bytearray()

    if is_ps3:
        # Reserve space for PS3 prefix (will fill in later)
        output.extend(b'\x00' * 8)

    for section in json_data['sections']:
        section_num = section['section_number']

        # Get raw data from JSON (support both 'data' and legacy 'raw_data' keys)
        raw_data = bytes.fromhex(section.get('data', section.get('raw_data', '')))

        # Compress the section
        compressed_data = compress(raw_data)

        # Build header
        if is_ps3:
            header = build_section_header_ps3(section_num, compressed_data, len(raw_data))
        else:
            header = build_section_header_pc(section_num, compressed_data, len(raw_data))

        # Add gap marker before Section 4 on PS3
        if is_ps3 and section_num == 4:
            section4_size = len(header) + len(compressed_data)
            gap_marker = struct.pack('>I', section4_size + 4) + struct.pack('>I', 0x08)
            output.extend(gap_marker)

        output.extend(header)
        output.extend(compressed_data)

    if is_ps3:
        # Fill in PS3 prefix
        data_size = len(output) - 8
        crc32_value = crc32_ps3(bytes(output[8:]))
        struct.pack_into('>I', output, 0, data_size)
        struct.pack_into('>I', output, 4, crc32_value)

        # Pad to 51,200 bytes
        padding_needed = PS3_FILE_SIZE - len(output)
        if padding_needed > 0:
            output.extend(b'\x00' * padding_needed)
    else:
        # Add PC footer (5 bytes: 01 00 00 00 XX)
        # XX is network interface count from uPlay - use preserved value or default
        nic_count = json_data.get('pc_network_interface_count',
                                   json_data.get('pc_footer_byte', 0x54))  # backward compat
        output.extend(b'\x01\x00\x00\x00')
        output.append(nic_count)

    with open(output_file, 'wb') as f:
        f.write(output)

    return len(output)


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Convert AC Brotherhood OPTIONS files to/from JSON',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert OPTIONS to JSON (auto-detects format)
  python options_json.py OPTIONS.bin -o options.json --pretty

  # Force PS3 format
  python options_json.py OPTIONS.PS3 --format ps3 -o options.json

  # Convert JSON back to binary
  python options_json.py options.json --to-binary -o OPTIONS_new.bin
        """
    )

    parser.add_argument('input', help='Input file (OPTIONS binary or JSON)')
    parser.add_argument('-o', '--output', required=True, help='Output file')
    parser.add_argument('--format', choices=['pc', 'ps3', 'auto'], default='auto',
                       help='File format (default: auto-detect)')
    parser.add_argument('--to-binary', action='store_true',
                       help='Convert JSON to binary OPTIONS file')
    parser.add_argument('--pretty', action='store_true',
                       help='Pretty-print JSON output with indentation')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Include parsed record details in JSON output')

    args = parser.parse_args()

    if args.to_binary:
        # JSON to OPTIONS
        print(f"Converting JSON to OPTIONS binary")
        print(f"  Input: {args.input}")

        with open(args.input, 'r') as f:
            json_data = json.load(f)

        format_type = json_data.get('format', 'PC')
        output_size = json_to_options(json_data, args.output)

        print(f"  Format: {format_type}")
        print(f"  Output: {args.output}")
        print(f"  Size: {output_size} bytes")
        print("Done!")
    else:
        # OPTIONS to JSON
        format_type = None if args.format == 'auto' else args.format.upper()

        print(f"Converting OPTIONS to JSON")
        print(f"  Input: {args.input}")

        json_data = options_to_json(args.input, format_type, verbose=args.verbose)

        print(f"  Detected format: {json_data['format']}")
        print(f"  Sections: {len(json_data['sections'])}")

        for section in json_data['sections']:
            size = len(section['data']) // 2
            if '_info' in section:
                print(f"    Section {section['section_number']}: {section['_info']['name']} ({size} bytes, {section['_info'].get('record_count', 0)} records)")
            else:
                print(f"    Section {section['section_number']}: {size} bytes")

        with open(args.output, 'w') as f:
            if args.pretty:
                json.dump(json_data, f, indent=2)
            else:
                json.dump(json_data, f)

        print(f"  Output: {args.output}")
        print("Done!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
