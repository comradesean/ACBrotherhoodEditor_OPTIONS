#!/usr/bin/env python3
"""
ACB Brotherhood Facebook Cape Unlocker
=======================================

A self-contained tool for unlocking Facebook-exclusive capes and changing
player name in AC Brotherhood SAV files.
Supports both PC and PS3 formats with a console UI.

Cape structure in Block 4:
  [cape_hash 4B] [8 zeros] [0x0B marker] [ownership_flag 1B] [cape_id 1B] ...

Cape identification:
  Venetian Cape: Hash 0x4470F39F, ID 0x0E
  Medici Cape:   Hash 0xDD79A225, ID 0x11

Ownership flag is at hash_offset + 13, followed by cape_id at hash_offset + 14.

Name structure in Block 1:
  [1A] [00 0B] [length 4B LE] [string bytes]
  Default name is "Desmond" (7 bytes)

Usage:
    python acb_facebookcape_unlocker.py save.SAV
    python acb_facebookcape_unlocker.py AC2_0.SAV
"""

import sys
import os
import struct

try:
    import curses
    HAS_CURSES = True
except ImportError:
    HAS_CURSES = False

# Import LZSS compression/decompression
from lzss import compress, decompress

# =============================================================================
# CONSTANTS
# =============================================================================

# Cape definitions: (hash, expected_id, name)
# The cape_id appears at hash+14 and is used for validation
CAPE_DEFINITIONS = [
    (0x4470F39F, 0x0E, "Venetian Cape"),
    (0xDD79A225, 0x11, "Medici Cape"),
]

# Ownership flag is at hash_offset + 13, cape_id at hash_offset + 14
OWNERSHIP_FLAG_OFFSET = 13
CAPE_ID_OFFSET = 14

# Name string marker pattern in Block 1: [1A] [00 0B] [length 4B] [string]
NAME_MARKER = bytes([0x1A, 0x00, 0x0B])
MAX_NAME_LENGTH = 17  # Game limit

# PS3 file size (padded)
PS3_FILE_SIZE = 307200  # 0x4B000

# =============================================================================
# CHECKSUMS
# =============================================================================

def adler32_zero_seed(data: bytes) -> int:
    """Adler-32 with zero seed (AC Brotherhood variant)."""
    MOD_ADLER = 65521
    s1 = 0
    s2 = 0
    for byte in data:
        s1 = (s1 + byte) % MOD_ADLER
        s2 = (s2 + s1) % MOD_ADLER
    return (s2 << 16) | s1


def crc32_ps3(data: bytes) -> int:
    """CRC32 with PS3 parameters."""
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
    """Detect PC or PS3 SAV format."""
    # PS3 files are padded to 307200 bytes
    if len(data) == PS3_FILE_SIZE:
        if len(data) >= 8:
            prefix_size = struct.unpack('>I', data[0:4])[0]
            prefix_crc = struct.unpack('>I', data[4:8])[0]
            if prefix_size < len(data) - 8:
                actual_crc = crc32_ps3(data[8:8 + prefix_size])
                if actual_crc == prefix_crc:
                    return 'PS3'

    # Check for PC format by looking for magic pattern in Block 1 header
    if len(data) > 0x14:
        magic = data[0x10:0x14]
        if magic == b'\x33\xAA\xFB\x57':  # GUID low
            return 'PC'

    return 'unknown'


# =============================================================================
# PC SAV PARSING (from cape_unlocker.py)
# =============================================================================

def parse_pc_sav_blocks(data: bytes) -> dict:
    """Parse PC SAV file and extract all 5 blocks."""
    total_size = len(data)

    # Block 1: 44-byte header at offset 0, then compressed data
    block1_compressed_size = struct.unpack('<I', data[0x20:0x24])[0]
    block1_compressed = data[0x2C:0x2C + block1_compressed_size]

    # Block 2: 44-byte header immediately after Block 1
    block2_header_offset = 0x2C + block1_compressed_size
    block2_compressed_size = struct.unpack('<I', data[block2_header_offset + 0x20:block2_header_offset + 0x24])[0]
    block2_data_offset = block2_header_offset + 44
    block2_compressed = data[block2_data_offset:block2_data_offset + block2_compressed_size]

    # Block 3: Raw data with 4 regions
    block3_offset = block2_data_offset + block2_compressed_size

    # Find all 4 region headers in Block 3
    block3_regions = []
    search_pos = block3_offset
    for region_num in range(4):
        while search_pos < total_size - 8:
            if (data[search_pos] == 0x01 and
                data[search_pos+4:search_pos+8] == b'\x00\x00\x80\x00'):
                region_size = struct.unpack('<I', data[search_pos+1:search_pos+4] + b'\x00')[0]
                if 0 < region_size < 50000:
                    block3_regions.append((search_pos, region_size))
                    # Move past header + data + 5-byte gap
                    search_pos = search_pos + 8 + region_size + 5
                    break
            search_pos += 1

    # Region 4's declared size equals Block 4's compressed size
    if len(block3_regions) >= 4:
        region4_offset, block4_compressed_size = block3_regions[3]
        # Block 3 ends after Region 4 header (8 bytes) + 5-byte local data
        block3_end = region4_offset + 8 + 5
        block3_size = block3_end - block3_offset
    else:
        raise ValueError(f"Could not parse Block 3 headers, found {len(block3_regions)} regions")

    block3_raw = data[block3_offset:block3_offset + block3_size]

    # Calculate Region 4's offset within Block 3 (for later patching)
    region4_offset_in_block3 = region4_offset - block3_offset

    # Block 4: LZSS compressed, size from Region 4's declared value
    block4_offset = block3_offset + block3_size
    block4_compressed = data[block4_offset:block4_offset + block4_compressed_size]

    # Block 5: Rest of file
    block5_offset = block4_offset + block4_compressed_size
    block5_raw = data[block5_offset:]

    return {
        'block1_header': data[0:0x2C],
        'block1_compressed': block1_compressed,
        'block2_header_offset': block2_header_offset,
        'block2_header': data[block2_header_offset:block2_header_offset + 44],
        'block2_compressed': block2_compressed,
        'block3_raw': block3_raw,
        'block4_compressed': block4_compressed,
        'block5_raw': block5_raw,
        'region4_offset_in_block3': region4_offset_in_block3,
    }


# =============================================================================
# PS3 SAV PARSING (from cape_unlocker_ps3.py)
# =============================================================================

def parse_ps3_sav_blocks(data: bytes) -> dict:
    """Parse PS3 SAV file and extract all 5 blocks."""
    # Verify PS3 prefix
    if len(data) < 8:
        raise ValueError("File too small for PS3 SAV format")

    ps3_size = struct.unpack('>I', data[0:4])[0]
    ps3_checksum = struct.unpack('>I', data[4:8])[0]

    # SAV data starts after 8-byte prefix
    sav_data = data[8:]
    total_size = len(sav_data)

    # Block 1: 44-byte header, sizes at offset 0x20 (LE)
    b1_comp_size = struct.unpack('<I', sav_data[0x20:0x24])[0]
    b1_uncomp_size = struct.unpack('<I', sav_data[0x24:0x28])[0]
    b1_checksum = struct.unpack('<I', sav_data[0x28:0x2C])[0]
    b1_compressed = sav_data[44:44 + b1_comp_size]

    # Block 2: 44-byte header immediately after Block 1
    b2_header_offset = 44 + b1_comp_size
    b2_comp_size = struct.unpack('<I', sav_data[b2_header_offset + 0x20:b2_header_offset + 0x24])[0]
    b2_uncomp_size = struct.unpack('<I', sav_data[b2_header_offset + 0x24:b2_header_offset + 0x28])[0]
    b2_checksum = struct.unpack('<I', sav_data[b2_header_offset + 0x28:b2_header_offset + 0x2C])[0]
    b2_data_offset = b2_header_offset + 44
    b2_compressed = sav_data[b2_data_offset:b2_data_offset + b2_comp_size]

    # Block 3: Raw data with 4 regions
    b3_offset = b2_data_offset + b2_comp_size

    # Find all 4 region headers in Block 3
    block3_regions = []
    search_pos = b3_offset
    for region_num in range(4):
        while search_pos < total_size - 8:
            if (sav_data[search_pos] == 0x01 and
                sav_data[search_pos+4:search_pos+8] == b'\x00\x00\x80\x00'):
                region_size = struct.unpack('<I', sav_data[search_pos+1:search_pos+4] + b'\x00')[0]
                if 0 < region_size < 50000:
                    block3_regions.append((search_pos, region_size))
                    search_pos = search_pos + 8 + region_size + 5
                    break
            search_pos += 1

    if len(block3_regions) < 4:
        raise ValueError(f"Could not parse Block 3 headers, found {len(block3_regions)} regions")

    # Region 4's declared size equals Block 4's compressed size
    region4_offset, b4_comp_size = block3_regions[3]
    b3_end = region4_offset + 8 + 5
    b3_size = b3_end - b3_offset
    b3_raw = sav_data[b3_offset:b3_offset + b3_size]

    region4_offset_in_block3 = region4_offset - b3_offset

    # Block 4: LZSS compressed
    b4_offset = b3_offset + b3_size
    b4_compressed = sav_data[b4_offset:b4_offset + b4_comp_size]

    # Block 5: Rest of actual data (before padding)
    b5_offset = b4_offset + b4_comp_size
    actual_end = ps3_size
    b5_raw = sav_data[b5_offset:actual_end]

    return {
        'ps3_size': ps3_size,
        'ps3_checksum': ps3_checksum,
        'block1_header': sav_data[0:44],
        'block1_compressed': b1_compressed,
        'block2_header_offset': b2_header_offset,
        'block2_header': sav_data[b2_header_offset:b2_header_offset + 44],
        'block2_compressed': b2_compressed,
        'block3_raw': b3_raw,
        'block4_compressed': b4_compressed,
        'block5_raw': b5_raw,
        'region4_offset_in_block3': region4_offset_in_block3,
    }


# =============================================================================
# NAME HANDLING (from cape_unlocker.py)
# =============================================================================

def find_name_in_block1(data: bytes) -> tuple:
    """
    Find the player name in Block 1.
    Returns (offset, length, name) where offset is the start of the length field.
    Returns (None, None, None) if not found.
    """
    pos = 0
    while True:
        pos = data.find(NAME_MARKER, pos)
        if pos == -1:
            return None, None, None

        length_offset = pos + 3
        if length_offset + 4 > len(data):
            pos += 1
            continue

        name_length = struct.unpack('<I', data[length_offset:length_offset + 4])[0]

        if 1 <= name_length <= 64:
            name_offset = length_offset + 4
            if name_offset + name_length <= len(data):
                name = data[name_offset:name_offset + name_length].decode('utf-8', errors='replace')
                return length_offset, name_length, name

        pos += 1

    return None, None, None


def change_name_in_block1(data: bytearray, new_name: str) -> bytearray:
    """
    Change the player name in Block 1.

    Block 1 contains internal size fields at offsets 0x0E and 0x91 that must be
    adjusted when the name length changes. These are cumulative size fields that
    include the name string in their calculation.
    """
    length_offset, old_length, old_name = find_name_in_block1(data)

    if length_offset is None:
        raise ValueError("Could not find name in Block 1")

    new_name_bytes = new_name.encode('utf-8')

    # Enforce max length
    if len(new_name_bytes) > MAX_NAME_LENGTH:
        new_name_bytes = new_name_bytes[:MAX_NAME_LENGTH]
        print(f"WARNING: Name truncated to {MAX_NAME_LENGTH} characters")

    new_length = len(new_name_bytes)
    length_diff = new_length - old_length
    print(f"Name: \"{old_name}\" -> \"{new_name_bytes.decode('utf-8')}\" (length: {old_length} -> {new_length})")

    # Build new Block 1 data with name replaced
    name_offset = length_offset + 4

    result = bytearray()
    result.extend(data[:length_offset])  # Everything before length field
    result.extend(struct.pack('<I', new_length))  # New length
    result.extend(new_name_bytes)  # New name
    result.extend(data[name_offset + old_length:])  # Everything after old name

    # Adjust internal size fields by the length difference
    # These fields are cumulative sizes that include the name string
    # Single-byte size fields
    SIZE_FIELD_OFFSETS_1BYTE = [0x0E, 0x91]
    for offset in SIZE_FIELD_OFFSETS_1BYTE:
        if offset < len(result):
            old_val = result[offset]
            new_val = old_val + length_diff
            if 0 <= new_val <= 255:
                result[offset] = new_val
                print(f"  Size field at 0x{offset:02X}: 0x{old_val:02X} -> 0x{new_val:02X}")

    # 2-byte size field at 0x12
    if 0x14 <= len(result):
        old_val = struct.unpack('<H', result[0x12:0x14])[0]
        new_val = old_val + length_diff
        if 0 <= new_val <= 65535:
            result[0x12:0x14] = struct.pack('<H', new_val)
            print(f"  Size field at 0x12 (2-byte): {old_val} -> {new_val}")

    return result


# =============================================================================
# CAPE ACCESS (exact copy from cape_unlocker.py)
# =============================================================================

def find_cape_in_block4(data: bytes, cape_hash: int, expected_id: int) -> int:
    """
    Find a cape in Block 4 by searching for its hash.

    Cape structure: [hash 4B] [8 zeros] [0B] [flag 1B] [cape_id 1B]

    Returns the offset of the ownership flag, or -1 if not found.
    Verifies the cape_id at hash_offset + 14 matches expected_id.
    """
    hash_bytes = struct.pack('<I', cape_hash)
    pos = 0

    while True:
        pos = data.find(hash_bytes, pos)
        if pos == -1:
            return -1

        # Check if cape_id matches at expected offset
        id_offset = pos + CAPE_ID_OFFSET
        if id_offset < len(data):
            actual_id = data[id_offset]
            if actual_id == expected_id:
                # Found it! Return ownership flag offset
                return pos + OWNERSHIP_FLAG_OFFSET

        pos += 1

    return -1


def get_cape_state(data: bytes, cape_hash: int, expected_id: int) -> bool:
    """Get cape unlock state (True = unlocked)."""
    offset = find_cape_in_block4(data, cape_hash, expected_id)
    if offset == -1 or offset >= len(data):
        return False
    return data[offset] != 0


def set_cape_state(data: bytearray, cape_hash: int, expected_id: int, unlocked: bool):
    """Set cape unlock state."""
    offset = find_cape_in_block4(data, cape_hash, expected_id)
    if offset != -1 and offset < len(data):
        data[offset] = 0x01 if unlocked else 0x00


# =============================================================================
# FILE SERIALIZATION
# =============================================================================

def save_pc_sav(filepath: str, blocks: dict, block1_data: bytearray,
                block4_data: bytearray, block1_modified: bool, block4_modified: bool):
    """Save modified PC SAV file."""
    block3_raw = bytearray(blocks['block3_raw'])
    region4_offset = blocks['region4_offset_in_block3']
    total_size_diff = 0

    # Handle Block 1 (recompress if modified)
    if block1_modified:
        block1_recompressed = compress(bytes(block1_data))
        block1_checksum = adler32_zero_seed(block1_recompressed)
        block1_header = struct.pack('<11I',
            0x00000016,              # Field1
            0x00FEDBAC,              # Field2
            len(block1_recompressed) + 32,  # Field3
            len(block1_data),        # Field4
            0x57FBAA33,              # Magic1
            0x1004FA99,              # Magic2
            0x00020001,              # Magic3
            0x01000080,              # Magic4
            len(block1_recompressed),  # Compressed size
            len(block1_data),        # Uncompressed size
            block1_checksum          # Checksum
        )
        block1_header_and_data = block1_header + block1_recompressed
        total_size_diff += len(block1_recompressed) - len(blocks['block1_compressed'])
    else:
        block1_header_and_data = blocks['block1_header'] + blocks['block1_compressed']

    # Handle Block 4 (recompress if modified)
    if block4_modified:
        block4_recompressed = compress(bytes(block4_data))

        # Patch Block 3's Region 4 header with new Block 4 size
        old_b4_size = struct.unpack('<I', bytes(block3_raw[region4_offset+1:region4_offset+4]) + b'\x00')[0]
        new_b4_size = len(block4_recompressed)
        if old_b4_size != new_b4_size:
            size_bytes = struct.pack('<I', new_b4_size)[:3]
            block3_raw[region4_offset+1:region4_offset+4] = size_bytes

        # Update Block 4 checksum
        old_checksum = struct.unpack('<I', bytes(block3_raw[region4_offset+9:region4_offset+13]))[0]
        new_checksum = adler32_zero_seed(block4_recompressed)
        if old_checksum != new_checksum:
            block3_raw[region4_offset+9:region4_offset+13] = struct.pack('<I', new_checksum)

        total_size_diff += len(block4_recompressed) - len(blocks['block4_compressed'])
    else:
        block4_recompressed = blocks['block4_compressed']

    # Get Block 2 header+data
    block2_header_and_data = bytearray(blocks['block2_header'] + blocks['block2_compressed'])

    # Patch Block 2 header Field1 if file size changed
    if total_size_diff != 0:
        old_field1 = struct.unpack('<I', block2_header_and_data[0:4])[0]
        new_field1 = old_field1 + total_size_diff
        block2_header_and_data[0:4] = struct.pack('<I', new_field1)

    # Assemble output file
    output = bytearray()
    output.extend(block1_header_and_data)
    output.extend(block2_header_and_data)
    output.extend(block3_raw)
    output.extend(block4_recompressed)
    output.extend(blocks['block5_raw'])

    with open(filepath, 'wb') as f:
        f.write(output)


def save_ps3_sav(filepath: str, blocks: dict, block1_data: bytearray,
                 block4_data: bytearray, block1_modified: bool, block4_modified: bool):
    """Save modified PS3 SAV file."""
    block3_raw = bytearray(blocks['block3_raw'])
    region4_offset = blocks['region4_offset_in_block3']

    # Handle Block 1 (recompress if modified)
    if block1_modified:
        block1_recompressed = compress(bytes(block1_data))
        block1_checksum = adler32_zero_seed(block1_recompressed)
        # PS3 format: fields 0-2 BE, rest LE
        block1_header = bytearray()
        block1_header.extend(struct.pack('>I', 0x00000016))  # Field0 BE
        block1_header.extend(struct.pack('>I', 0x00FEDBAC))  # Field1 BE
        block1_header.extend(struct.pack('>I', len(block1_recompressed) + 32))  # Field2 BE
        block1_header.extend(struct.pack('<I', len(block1_data)))  # Field3 LE
        block1_header.extend(struct.pack('<I', 0x57FBAA33))  # Magic1 LE
        block1_header.extend(struct.pack('<I', 0x1004FA99))  # Magic2 LE
        block1_header.extend(struct.pack('<I', 0x00020001))  # Magic3 LE
        block1_header.extend(struct.pack('<I', 0x01000080))  # Magic4 LE
        block1_header.extend(struct.pack('<I', len(block1_recompressed)))  # CompSize LE
        block1_header.extend(struct.pack('<I', len(block1_data)))  # UncompSize LE
        block1_header.extend(struct.pack('<I', block1_checksum))  # Checksum LE
    else:
        block1_header = blocks['block1_header']
        block1_recompressed = blocks['block1_compressed']

    # Handle Block 4 (recompress if modified)
    if block4_modified:
        block4_recompressed = compress(bytes(block4_data))

        # Patch Block 3's Region 4 header
        old_b4_size = struct.unpack('<I', bytes(block3_raw[region4_offset+1:region4_offset+4]) + b'\x00')[0]
        new_b4_size = len(block4_recompressed)
        if old_b4_size != new_b4_size:
            size_bytes = struct.pack('<I', new_b4_size)[:3]
            block3_raw[region4_offset+1:region4_offset+4] = size_bytes

        # Update Block 4 checksum
        old_checksum = struct.unpack('<I', bytes(block3_raw[region4_offset+9:region4_offset+13]))[0]
        new_checksum = adler32_zero_seed(block4_recompressed)
        if old_checksum != new_checksum:
            block3_raw[region4_offset+9:region4_offset+13] = struct.pack('<I', new_checksum)
    else:
        block4_recompressed = blocks['block4_compressed']

    # Build Block 2 header+data
    block2_header = bytearray(blocks['block2_header'])
    block2_compressed = blocks['block2_compressed']

    # Calculate size difference for Block 2 Field1
    old_b1_size = len(blocks['block1_compressed'])
    new_b1_size = len(block1_recompressed)
    old_b4_size = len(blocks['block4_compressed'])
    new_b4_size = len(block4_recompressed)
    total_size_diff = (new_b1_size - old_b1_size) + (new_b4_size - old_b4_size)

    if total_size_diff != 0:
        # Update Block 2 Field1 (BE in PS3)
        old_field1 = struct.unpack('>I', block2_header[0:4])[0]
        new_field1 = old_field1 + total_size_diff
        block2_header[0:4] = struct.pack('>I', new_field1)

    # Assemble SAV payload
    sav_payload = bytearray()
    sav_payload.extend(block1_header)
    sav_payload.extend(block1_recompressed)
    sav_payload.extend(block2_header)
    sav_payload.extend(block2_compressed)
    sav_payload.extend(block3_raw)
    sav_payload.extend(block4_recompressed)
    sav_payload.extend(blocks['block5_raw'])

    # Calculate new PS3 prefix
    new_ps3_size = len(sav_payload)
    new_ps3_checksum = crc32_ps3(bytes(sav_payload))

    # Build final output with PS3 prefix and padding
    output = bytearray()
    output.extend(struct.pack('>I', new_ps3_size))  # Size BE
    output.extend(struct.pack('>I', new_ps3_checksum))  # Checksum BE
    output.extend(sav_payload)

    # Pad to PS3 file size
    if len(output) < PS3_FILE_SIZE:
        output.extend(b'\x00' * (PS3_FILE_SIZE - len(output)))

    with open(filepath, 'wb') as f:
        f.write(output)


# =============================================================================
# UI HELPERS
# =============================================================================

class UnlockItem:
    def __init__(self, name: str, category: str, item_type: str,
                 hash_value: int = None, expected_id: int = None, is_name: bool = False):
        self.name = name
        self.category = category
        self.item_type = item_type
        self.hash_value = hash_value
        self.expected_id = expected_id
        self.is_name = is_name
        self.checked = False
        self.name_value = ""  # For name field


def build_unlock_items() -> list:
    items = []
    # Name item
    items.append(UnlockItem("Player Name", "PLAYER", "name", is_name=True))
    # Cape items
    for hash_val, expected_id, name in CAPE_DEFINITIONS:
        items.append(UnlockItem(name, "FACEBOOK CAPES", "cape",
                                hash_value=hash_val, expected_id=expected_id))
    return items


def load_unlock_states(items: list, block1_data: bytes, block4_data: bytes):
    """Load current states from decompressed block data."""
    for item in items:
        if item.is_name:
            _, _, name = find_name_in_block1(block1_data)
            item.name_value = name if name else "Unknown"
        else:
            item.checked = get_cape_state(block4_data, item.hash_value, item.expected_id)


def apply_unlock_states(items: list, block1_data: bytearray, block4_data: bytearray,
                        new_name: str = None) -> tuple:
    """Apply states to block data. Returns (block1_modified, block4_modified)."""
    block1_modified = False
    block4_modified = False

    for item in items:
        if item.is_name:
            continue  # Name handled separately
        else:
            old_state = get_cape_state(block4_data, item.hash_value, item.expected_id)
            if old_state != item.checked:
                set_cape_state(block4_data, item.hash_value, item.expected_id, item.checked)
                block4_modified = True

    return (block1_modified, block4_modified)


# =============================================================================
# CURSES UI
# =============================================================================

def run_ui(stdscr, filepath: str, platform: str, blocks: dict,
           block1_data: bytearray, block4_data: bytearray) -> tuple:
    """Run the curses UI. Returns (should_save, new_name or None)."""
    curses.curs_set(0)
    curses.use_default_colors()

    if curses.has_colors():
        curses.init_pair(1, curses.COLOR_CYAN, -1)
        curses.init_pair(2, curses.COLOR_GREEN, -1)
        curses.init_pair(3, curses.COLOR_YELLOW, -1)

    items = build_unlock_items()
    load_unlock_states(items, block1_data, block4_data)

    selected = 0
    modified = False
    new_name = None
    editing_name = False

    while True:
        stdscr.clear()
        height, width = stdscr.getmaxyx()

        # Title
        title = " ACB Brotherhood Facebook Cape Unlocker "
        stdscr.addstr(0, max(0, (width - len(title)) // 2), title,
                      curses.A_BOLD | curses.A_REVERSE)

        # File info
        filename = os.path.basename(filepath)
        info = f" File: {filename} ({platform} format) "
        stdscr.addstr(2, 2, info, curses.color_pair(1) if curses.has_colors() else 0)

        if modified:
            stdscr.addstr(2, 2 + len(info) + 1, "[MODIFIED]",
                          curses.color_pair(3) if curses.has_colors() else curses.A_BOLD)

        # Items
        row = 4
        current_category = None

        for i, item in enumerate(items):
            if row >= height - 4:
                break

            # Category header
            if item.category != current_category:
                current_category = item.category
                if row > 4:
                    row += 1
                stdscr.addstr(row, 2, current_category,
                              curses.A_BOLD | (curses.color_pair(2) if curses.has_colors() else 0))
                row += 1

            attr = curses.A_REVERSE if i == selected else 0

            if item.is_name:
                # Name display
                display_name = new_name if new_name else item.name_value
                stdscr.addstr(row, 4, f"{item.name}: ", attr)
                stdscr.addstr(row, 4 + len(item.name) + 2, display_name, attr | curses.A_BOLD)
                stdscr.addstr(row, 4 + len(item.name) + 2 + len(display_name) + 1,
                              "[Enter to edit]", curses.A_DIM)
            else:
                # Checkbox
                checkbox = "[x]" if item.checked else "[ ]"
                stdscr.addstr(row, 4, checkbox, attr)
                stdscr.addstr(row, 8, item.name, attr)
            row += 1

        # Footer
        footer_row = height - 2
        footer = " [Space] Toggle  [Enter] Edit Name  [A] All On  [N] All Off  [S] Save  [Q] Quit "
        stdscr.addstr(footer_row, max(0, (width - len(footer)) // 2), footer, curses.A_REVERSE)

        stdscr.refresh()

        # Input
        key = stdscr.getch()

        if key in (ord('q'), ord('Q'), 27):  # Q or Escape
            if modified:
                stdscr.addstr(height - 3, 2, "Discard changes? (y/n) ", curses.A_BOLD)
                stdscr.refresh()
                confirm = stdscr.getch()
                if confirm not in (ord('y'), ord('Y')):
                    continue
            return (False, None)

        elif key in (ord('s'), ord('S')):
            # Apply changes to block data
            apply_unlock_states(items, block1_data, block4_data)
            return (True, new_name)

        elif key in (curses.KEY_UP, ord('k')):
            selected = max(0, selected - 1)

        elif key in (curses.KEY_DOWN, ord('j')):
            selected = min(len(items) - 1, selected + 1)

        elif key in (ord(' '),):
            if not items[selected].is_name:
                items[selected].checked = not items[selected].checked
                modified = True

        elif key in (curses.KEY_ENTER, 10):
            if items[selected].is_name:
                # Edit name
                curses.echo()
                curses.curs_set(1)
                stdscr.addstr(height - 3, 2, "Enter new name (max 17 chars): ")
                stdscr.clrtoeol()
                stdscr.refresh()
                try:
                    input_bytes = stdscr.getstr(height - 3, 33, MAX_NAME_LENGTH)
                    input_str = input_bytes.decode('utf-8', errors='replace').strip()
                    if input_str:
                        new_name = input_str
                        modified = True
                except:
                    pass
                curses.noecho()
                curses.curs_set(0)
            else:
                items[selected].checked = not items[selected].checked
                modified = True

        elif key in (ord('a'), ord('A')):
            for item in items:
                if not item.is_name:
                    item.checked = True
            modified = True

        elif key in (ord('n'), ord('N')):
            for item in items:
                if not item.is_name:
                    item.checked = False
            modified = True

    return (False, None)


# =============================================================================
# TEXT UI (fallback)
# =============================================================================

def clear_screen():
    """Clear the console screen."""
    os.system('cls' if os.name == 'nt' else 'clear')


def run_text_ui(filepath: str, platform: str, blocks: dict,
                block1_data: bytearray, block4_data: bytearray) -> tuple:
    """Run simple text-based UI. Returns (should_save, new_name or None)."""
    items = build_unlock_items()
    load_unlock_states(items, block1_data, block4_data)
    new_name = None

    while True:
        clear_screen()
        print("=" * 60)
        print(" ACB Brotherhood Facebook Cape Unlocker")
        print("=" * 60)
        print(f" File: {os.path.basename(filepath)} ({platform} format)")
        print("=" * 60)
        print()

        # Display items grouped by category
        current_category = None
        item_num = 1

        for item in items:
            if item.category != current_category:
                current_category = item.category
                print(f"\n  {current_category}")
                print("  " + "-" * 40)

            if item.is_name:
                display_name = new_name if new_name else item.name_value
                print(f"  {item_num:2d}. {item.name}: {display_name}")
            else:
                checkbox = "[x]" if item.checked else "[ ]"
                print(f"  {item_num:2d}. {checkbox} {item.name}")
            item_num += 1

        print()
        print("=" * 60)
        print(" Commands: 1-{} toggle/edit | A=all on | N=all off | S=save | Q=quit".format(len(items)))
        print("=" * 60)

        try:
            choice = input("\n> ").strip().upper()
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
            return (False, None)

        if choice == 'Q':
            return (False, None)
        elif choice == 'S':
            apply_unlock_states(items, block1_data, block4_data)
            return (True, new_name)
        elif choice == 'A':
            for item in items:
                if not item.is_name:
                    item.checked = True
        elif choice == 'N':
            for item in items:
                if not item.is_name:
                    item.checked = False
        elif choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(items):
                if items[idx].is_name:
                    try:
                        new_input = input(f"  Enter new name (max {MAX_NAME_LENGTH} chars): ").strip()
                        if new_input:
                            new_name = new_input[:MAX_NAME_LENGTH]
                    except:
                        pass
                else:
                    items[idx].checked = not items[idx].checked

    return (False, None)


# =============================================================================
# MAIN
# =============================================================================

def main():
    if len(sys.argv) < 2:
        print("ACB Brotherhood Facebook Cape Unlocker")
        print()
        print("Usage: python acb_facebookcape_unlocker.py <SAV_FILE>")
        print()
        print("Examples:")
        print("  python acb_facebookcape_unlocker.py save.SAV")
        print("  python acb_facebookcape_unlocker.py AC2_0.SAV")
        return 1

    filepath = sys.argv[1]

    if not os.path.exists(filepath):
        print(f"Error: File not found: {filepath}")
        return 1

    print(f"Loading {filepath}...")

    with open(filepath, 'rb') as f:
        data = f.read()

    platform = detect_format(data)
    if platform == 'unknown':
        print("Error: Could not detect file format (PC or PS3)")
        return 1

    print(f"Detected format: {platform}")

    # Parse blocks
    try:
        if platform == 'PC':
            blocks = parse_pc_sav_blocks(data)
        else:
            blocks = parse_ps3_sav_blocks(data)
    except Exception as e:
        print(f"Error parsing SAV file: {e}")
        return 1

    # Decompress Block 1 and Block 4
    print("Decompressing blocks...")
    block1_data = bytearray(decompress(blocks['block1_compressed']))
    block4_data = bytearray(decompress(blocks['block4_compressed']))

    print(f"Block 1: {len(block1_data)} bytes")
    print(f"Block 4: {len(block4_data)} bytes")

    # Run UI
    if HAS_CURSES:
        try:
            should_save, new_name = curses.wrapper(
                lambda stdscr: run_ui(stdscr, filepath, platform, blocks,
                                      block1_data, block4_data))
        except KeyboardInterrupt:
            print("\nCancelled.")
            return 0
    else:
        should_save, new_name = run_text_ui(filepath, platform, blocks,
                                            block1_data, block4_data)

    if should_save:
        # Check what was modified
        block1_modified = False
        block4_modified = False

        # Check if name was actually changed (compare to original)
        if new_name:
            orig_block1 = decompress(blocks['block1_compressed'])
            _, _, orig_name = find_name_in_block1(orig_block1)
            if new_name != orig_name:
                block1_data = change_name_in_block1(block1_data, new_name)
                block1_modified = True
            else:
                print(f"Name unchanged: {new_name}")

        # Check if any capes were modified
        orig_block4 = decompress(blocks['block4_compressed'])
        for hash_val, expected_id, name in CAPE_DEFINITIONS:
            orig_state = get_cape_state(orig_block4, hash_val, expected_id)
            new_state = get_cape_state(block4_data, hash_val, expected_id)
            if orig_state != new_state:
                block4_modified = True
                status = "UNLOCKED" if new_state else "LOCKED"
                print(f"{name}: {status}")

        if not block1_modified and not block4_modified:
            print("\nNo changes to save.")
        else:
            print(f"\nSaving to {filepath}...")
            if platform == 'PC':
                save_pc_sav(filepath, blocks, block1_data, block4_data,
                            block1_modified, block4_modified)
            else:
                save_ps3_sav(filepath, blocks, block1_data, block4_data,
                             block1_modified, block4_modified)
            print("Done!")
    else:
        print("\nNo changes saved.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
