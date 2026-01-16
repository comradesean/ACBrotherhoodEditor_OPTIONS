#!/usr/bin/env python3
"""
ACB Brotherhood uPlay Rewards Unlocker
=============================

A self-contained tool for toggling unlocks in AC Brotherhood OPTIONS files.
Supports both PC and PS3 formats with a console UI.

Usage:
    python acb_uplay_unlocker.py OPTIONS.PC
    python acb_uplay_unlocker.py OPTIONS.PS3
"""

import sys
import os
import struct

try:
    import curses
    HAS_CURSES = True
except ImportError:
    HAS_CURSES = False

# =============================================================================
# CONSTANTS
# =============================================================================

MAGIC_PATTERN = b'\x33\xAA\xFB\x57\x99\xFA\x04\x10\x01\x00\x02\x00\x80\x00\x00\x01'
PS3_FILE_SIZE = 51200
PC_FOOTER = bytes([0x01, 0x00, 0x00, 0x00, 0x54])

# =============================================================================
# UNLOCK DEFINITIONS
# =============================================================================

SECTION2_BOOL_UNLOCKS = [
    (0x41027E09, "Shopaholic - Mercati di Traiano", "TEMPLAR LAIRS"),
    (0x788F42CC, "Liquid Gold - Tivoli Aqueducts", "TEMPLAR LAIRS"),
    (0x21D9D09F, "The Harlequin", "MULTIPLAYER CHARACTERS"),
    (0x36A2C4DC, "The Officer", "MULTIPLAYER CHARACTERS"),
    (0x52C3A915, "The Hellequin", "MULTIPLAYER CHARACTERS"),
]

COSTUME_HASH = 0x9C81BB39
COSTUME_BITS = [
    (0x01, "Florentine Noble Attire"),
    (0x02, "Armor of Altair"),
    (0x04, "Altair's Robes"),
    (0x08, "Drachen Armor"),
    (0x10, "Desmond"),
    (0x20, "Raiden"),
]

SECTION3_BOOL_UNLOCKS = [
    (0x4DBC7DA7, "Gun Capacity Upgrade", "UPGRADES"),
]

# =============================================================================
# CHECKSUMS (exact copy from options_unpack.py)
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
# LZSS DECOMPRESSOR (exact copy from options_unpack.py)
# =============================================================================

def decompress_lzss(compressed: bytes) -> bytes:
    """Decompress LZSS data."""
    if not compressed:
        return b''

    output = bytearray()
    in_ptr = 0
    flags = 0
    flag_bits = 0

    while in_ptr < len(compressed):
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
            if in_ptr >= len(compressed):
                break
            output.append(compressed[in_ptr])
            in_ptr += 1
        else:
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
                if in_ptr + 1 >= len(compressed):
                    break

                byte1 = compressed[in_ptr]
                byte2 = compressed[in_ptr + 1]
                in_ptr += 2

                len_field = byte1 >> 5
                low_offset = byte1 & 0x1F
                high_offset = byte2
                distance = (high_offset << 5) | low_offset

                if distance == 0:
                    break

                if len_field == 0:
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
# LZSS COMPRESSOR (exact copy from lzss.py)
# =============================================================================

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


def find_best_match(data, pos, max_match_length=2048):
    """Find best match scanning backward from current position."""
    if pos < 2:
        return 0, 0

    best_length = 0
    best_offset = 0
    max_length = min(max_match_length, len(data) - pos)
    max_offset = min(8192, pos)
    max_offset = min(max_offset, pos - 2)

    for check_pos in range(pos - 1, max(0, pos - max_offset) - 1, -1):
        offset = pos - check_pos

        if best_length >= 2:
            if data[check_pos] != data[pos]:
                continue
            if check_pos + best_length < len(data) and pos + best_length < len(data):
                if data[check_pos + best_length] != data[pos + best_length]:
                    continue

        length = 0
        while (length < max_length and
               pos + length < len(data) and
               data[check_pos + length] == data[pos + length]):
            length += 1

        if length > best_length and length >= 2:
            best_length = length
            best_offset = offset
            if best_length >= max_length:
                break

    if best_offset > 0 and best_length >= 2:
        is_short_match = (2 <= best_length <= 5 and best_offset <= 256)
        if not is_short_match:
            if best_offset < 1:
                return 0, 0

    return best_length, best_offset


def calculate_match_cost(length, offset):
    """Calculate cost in bits for encoding a match"""
    if 2 <= length <= 5 and offset <= 256:
        return 12
    elif length < 10:
        return 18
    else:
        extra_bytes = (length - 9 + 254) // 255
        return 18 + (extra_bytes * 8)


def find_optimal_match_length(buffered_data, pos, match_length, match_offset):
    """
    Find optimal length for a match by looking ahead within it.

    NOTE: This optimization was DISABLED because the game compressor does NOT
    truncate matches based on future opportunities. Keeping matches whole
    ensures byte-for-byte accuracy with game output.

    The game uses a simple greedy approach - it takes whatever match it finds
    without looking ahead for potentially better truncation points.
    """
    # DISABLED: Always return full match length to match game behavior
    return match_length


def peek_next_decision(buffered_data, pos, curr_length):
    """Peek ahead to determine what the next encoding decision will be."""
    next_pos = pos + curr_length
    if next_pos >= len(buffered_data):
        return (False, 0, 0)

    next_length, next_offset = find_best_match(buffered_data, next_pos)

    if next_length >= 2 and next_pos + 1 < len(buffered_data):
        lookahead_length, lookahead_offset = find_best_match(buffered_data, next_pos + 1)

        next_is_short = (2 <= next_length <= 5 and next_offset <= 256)
        lookahead_is_short = (2 <= lookahead_length <= 5 and lookahead_offset <= 256)

        if next_is_short:
            adjustment = 2
        else:
            adjustment = 1

        if next_is_short and not lookahead_is_short and lookahead_length >= 2:
            adjustment += 2
        if lookahead_is_short and not next_is_short:
            adjustment -= 1
        if adjustment < 1:
            adjustment = 1
        if next_is_short and lookahead_is_short:
            adjustment = 1

        if lookahead_length >= next_length + adjustment:
            next_length = 0

    if next_length >= 2:
        match_cost = calculate_match_cost(next_length, next_offset)
        literal_cost = 9 * next_length
        if match_cost >= literal_cost:
            next_length = 0

    is_match = (next_length >= 2)
    return (is_match, next_length, next_offset)


def compress_lzss(data: bytes) -> bytes:
    """Compress using lazy matching with Scenario 1 optimization."""
    buffered_data = bytearray([0x00, 0x00]) + bytearray(data)

    output = bytearray()
    bit_accum = 0
    bit_counter = 0
    flag_byte_ptr = 0

    prev_token_pos = None
    prev_was_match = False

    pos = 2

    while pos < len(buffered_data):
        curr_length, curr_offset = find_best_match(buffered_data, pos)

        if pos == 2:
            curr_length = 0

        if curr_length >= 2 and pos + 1 < len(buffered_data):
            next_length, next_offset = find_best_match(buffered_data, pos + 1)

            curr_is_short = (2 <= curr_length <= 5 and curr_offset <= 256)
            next_is_short = (2 <= next_length <= 5 and next_offset <= 256)

            if curr_is_short:
                adjustment = 2
            else:
                adjustment = 1

            if curr_is_short and not next_is_short and next_length >= 2:
                adjustment += 2
            if next_is_short and not curr_is_short:
                adjustment -= 1
            if adjustment < 1:
                adjustment = 1
            if curr_is_short and next_is_short:
                adjustment = 1

            if next_length >= curr_length + adjustment:
                curr_length = 0

        if curr_length >= 2:
            match_cost = calculate_match_cost(curr_length, curr_offset)
            literal_cost = 9 * curr_length
            if match_cost >= literal_cost:
                curr_length = 0

        if curr_length >= 2:
            curr_length = find_optimal_match_length(buffered_data, pos, curr_length, curr_offset)

        # Scenario 1 optimization
        if curr_length == 3 and prev_was_match and prev_token_pos is not None:
            if (output[prev_token_pos] & 0x03) == 0:
                next_is_match, _, _ = peek_next_decision(buffered_data, pos, curr_length)
                if next_is_match:
                    for i in range(3):
                        byte_val = buffered_data[pos + i]
                        output, bit_accum, bit_counter, flag_byte_ptr = add_bit(
                            output, bit_accum, bit_counter, flag_byte_ptr, 0
                        )
                        output.append(byte_val)
                    prev_was_match = False
                    pos += 3
                    continue

        if curr_length >= 2:
            output, bit_accum, bit_counter, flag_byte_ptr = add_bit(
                output, bit_accum, bit_counter, flag_byte_ptr, 1
            )

            if 2 <= curr_length <= 5 and curr_offset <= 256:
                output, bit_accum, bit_counter, flag_byte_ptr = add_bit(
                    output, bit_accum, bit_counter, flag_byte_ptr, 0
                )

                len_bits = curr_length - 2
                for i in range(2):
                    output, bit_accum, bit_counter, flag_byte_ptr = add_bit(
                        output, bit_accum, bit_counter, flag_byte_ptr, (len_bits >> i) & 1
                    )

                prev_token_pos = len(output)
                output.append((curr_offset - 1) & 0xFF)
                prev_was_match = True
            else:
                output, bit_accum, bit_counter, flag_byte_ptr = add_bit(
                    output, bit_accum, bit_counter, flag_byte_ptr, 1
                )

                prev_token_pos = len(output)

                if curr_length < 10:
                    byte1 = ((curr_length - 2) << 5) | (curr_offset & 0x1F)
                    byte2 = (curr_offset >> 5) & 0xFF
                    output.append(byte1)
                    output.append(byte2)
                else:
                    byte1 = curr_offset & 0x1F
                    byte2 = (curr_offset >> 5) & 0xFF
                    output.append(byte1)
                    output.append(byte2)

                    remaining = curr_length - 9
                    while remaining >= 0xFF:
                        output.append(0)
                        remaining -= 0xFF
                    output.append(remaining & 0xFF)
                prev_was_match = True

            pos += curr_length
        else:
            byte_val = buffered_data[pos]
            output, bit_accum, bit_counter, flag_byte_ptr = add_bit(
                output, bit_accum, bit_counter, flag_byte_ptr, 0
            )
            output.append(byte_val)
            prev_was_match = False
            pos += 1

    output, bit_accum, bit_counter, flag_byte_ptr = add_bit(
        output, bit_accum, bit_counter, flag_byte_ptr, 1
    )
    output, bit_accum, bit_counter, flag_byte_ptr = add_bit(
        output, bit_accum, bit_counter, flag_byte_ptr, 1
    )

    output.append(0x20)
    output.append(0x00)

    if bit_counter > 0:
        output[flag_byte_ptr] = ((1 << bit_counter) - 1) & bit_accum

    return bytes(output)


# =============================================================================
# FORMAT DETECTION (exact copy from options_unpack.py)
# =============================================================================

def detect_format(data: bytes) -> str:
    """Detect PC or PS3 format."""
    if len(data) == PS3_FILE_SIZE:
        if len(data) >= 8:
            prefix_size = struct.unpack('>I', data[0:4])[0]
            prefix_crc = struct.unpack('>I', data[4:8])[0]
            if prefix_size < len(data) - 8:
                actual_crc = crc32_ps3(data[8:8 + prefix_size])
                if actual_crc == prefix_crc:
                    return 'PS3'

    magic_short = MAGIC_PATTERN[:4]
    if len(data) > 0x14 and data[0x10:0x14] == magic_short:
        return 'PC'
    if len(data) > 0x1C and data[0x18:0x1C] == magic_short:
        return 'PS3'

    return 'unknown'


# =============================================================================
# SECTION PARSING (exact copy from options_unpack.py)
# =============================================================================

def find_sections(data: bytes, platform: str) -> list:
    """Find and parse all section headers."""
    headers = []
    prefix_offset = 8 if platform == 'PS3' else 0
    search_pos = prefix_offset

    while True:
        pattern_pos = data.find(MAGIC_PATTERN, search_pos)
        if pattern_pos == -1:
            break

        header_start = pattern_pos - 0x10
        if header_start < prefix_offset or header_start + 44 > len(data):
            search_pos = pattern_pos + len(MAGIC_PATTERN)
            continue

        sizes_offset = pattern_pos + len(MAGIC_PATTERN)
        if sizes_offset + 12 > len(data):
            break

        compressed_size = struct.unpack('<I', data[sizes_offset:sizes_offset+4])[0]
        uncompressed_size = struct.unpack('<I', data[sizes_offset+4:sizes_offset+8])[0]

        data_offset = header_start + 44
        compressed_data = data[data_offset:data_offset + compressed_size]
        decompressed = decompress_lzss(compressed_data)

        # Parse field2 (section ID) to preserve it
        if platform == 'PS3':
            field2 = struct.unpack('>I', data[header_start+8:header_start+12])[0]
        else:
            field2 = struct.unpack('<I', data[header_start+8:header_start+12])[0]

        headers.append({
            'header_offset': header_start,
            'data_offset': data_offset,
            'compressed_size': compressed_size,
            'uncompressed_size': uncompressed_size,
            'decompressed': bytearray(decompressed),
            'field2': field2,
        })

        search_pos = pattern_pos + len(MAGIC_PATTERN)

    return headers


# =============================================================================
# TRAILING DATA EXTRACTION
# =============================================================================

def get_trailing_data(data: bytes, platform: str, sections: list) -> bytes:
    """Extract trailing data after sections (PS3 only)."""
    if platform != 'PS3' or not sections:
        return b''

    prefix_size = struct.unpack('>I', data[0:4])[0]
    last_section = sections[-1]
    sections_end = last_section['data_offset'] + last_section['compressed_size'] - 8  # -8 for PS3 prefix offset

    if prefix_size > sections_end:
        return data[8 + sections_end:8 + prefix_size]
    return b''


# =============================================================================
# SECTION HEADER CONSTRUCTION (exact copy from options_pack.py)
# =============================================================================

def build_section_header(section_num: int, compressed_data: bytes,
                         uncompressed_size: int, platform: str,
                         orig_field2: int = None) -> bytes:
    """Build a complete 44-byte section header."""
    compressed_size = len(compressed_data)
    checksum = adler32_zero_seed(compressed_data)

    MAGIC1, MAGIC2, MAGIC3, MAGIC4 = 0x57FBAA33, 0x1004FA99, 0x00020001, 0x01000080

    if section_num == 1:
        field0 = 0x00000016
        field1 = 0x00FEDBAC
        # Use original field2 if provided, otherwise default
        field2 = orig_field2 if orig_field2 is not None else (0x000000C6 if platform == 'PS3' else 0x000000C5)
    elif section_num == 2:
        field0 = compressed_size + 40
        field1 = 0x00000003
        field2 = orig_field2 if orig_field2 is not None else 0x11FACE11
    elif section_num == 3:
        field0 = compressed_size + 40
        field1 = 0x00000000
        field2 = orig_field2 if orig_field2 is not None else 0x21EFFE22
    elif section_num == 4:
        field0 = 0x22FEEF21
        field1 = 0x00000004
        field2 = orig_field2 if orig_field2 is not None else 0x00000007
    else:
        raise ValueError(f"Invalid section number: {section_num}")

    header = bytearray()
    if platform == 'PS3':
        header.extend(struct.pack('>I', field0))
        header.extend(struct.pack('>I', field1))
        header.extend(struct.pack('>I', field2))
    else:
        header.extend(struct.pack('<I', field0))
        header.extend(struct.pack('<I', field1))
        header.extend(struct.pack('<I', field2))

    header.extend(struct.pack('<I', uncompressed_size))
    header.extend(struct.pack('<I', MAGIC1))
    header.extend(struct.pack('<I', MAGIC2))
    header.extend(struct.pack('<I', MAGIC3))
    header.extend(struct.pack('<I', MAGIC4))
    header.extend(struct.pack('<I', compressed_size))
    header.extend(struct.pack('<I', uncompressed_size))
    header.extend(struct.pack('<I', checksum))

    return bytes(header)


def build_gap_marker(section4_size: int, platform: str) -> bytes:
    """Build the 8-byte gap marker before Section 4."""
    size = section4_size + 4
    if platform == 'PS3':
        return struct.pack('>II', size, 0x08)
    else:
        return struct.pack('<II', size, 0x0E)


# =============================================================================
# FILE SERIALIZATION (exact copy from options_pack.py)
# =============================================================================

def save_options_file(filepath: str, sections: list, platform: str, trailing_data: bytes = b''):
    """Save sections back to OPTIONS file."""
    section_data = bytearray()

    for section_num, section in enumerate(sections, 1):
        compressed = compress_lzss(bytes(section['decompressed']))
        orig_field2 = section.get('field2')
        header = build_section_header(section_num, compressed,
                                      len(section['decompressed']), platform, orig_field2)

        if section_num == 4:
            gap_marker = build_gap_marker(len(header) + len(compressed), platform)
            section_data.extend(gap_marker)

        section_data.extend(header)
        section_data.extend(compressed)

    output = bytearray()

    if platform == 'PS3':
        # Include trailing data in prefix
        prefix_data = section_data + trailing_data
        data_size = len(prefix_data)
        crc32_value = crc32_ps3(bytes(prefix_data))
        output.extend(struct.pack('>II', data_size, crc32_value))
        output.extend(prefix_data)
        padding = PS3_FILE_SIZE - len(output)
        if padding > 0:
            output.extend(bytes(padding))
    else:
        output.extend(section_data)
        output.extend(PC_FOOTER)

    with open(filepath, 'wb') as f:
        f.write(output)


# =============================================================================
# PROPERTY ACCESS
# =============================================================================

def find_property_value_offset(section_data: bytes, hash_value: int) -> int:
    """Find property by hash and return offset to value byte(s)."""
    hash_bytes = struct.pack('<I', hash_value)
    pos = 0

    while True:
        found = section_data.find(hash_bytes, pos)
        if found == -1:
            return -1

        if found >= 4:
            type_prefix = struct.unpack('<I', section_data[found-4:found])[0]
            if type_prefix in (0x0E, 0x11):
                return found + 13

        pos = found + 1

    return -1


def get_bool_unlock_state(section_data: bytes, hash_value: int) -> bool:
    """Get bool unlock state (True = unlocked)."""
    offset = find_property_value_offset(section_data, hash_value)
    if offset == -1 or offset >= len(section_data):
        return False
    return section_data[offset] != 0


def set_bool_unlock_state(section_data: bytearray, hash_value: int, unlocked: bool):
    """Set bool unlock state."""
    offset = find_property_value_offset(section_data, hash_value)
    if offset != -1 and offset < len(section_data):
        section_data[offset] = 0x01 if unlocked else 0x00


def get_costume_bitmask(section_data: bytes) -> int:
    """Get costume bitmask value."""
    offset = find_property_value_offset(section_data, COSTUME_HASH)
    if offset == -1 or offset + 4 > len(section_data):
        return 0
    return struct.unpack('<I', section_data[offset:offset+4])[0]


def set_costume_bitmask(section_data: bytearray, value: int):
    """Set costume bitmask value."""
    offset = find_property_value_offset(section_data, COSTUME_HASH)
    if offset != -1 and offset + 4 <= len(section_data):
        section_data[offset:offset+4] = struct.pack('<I', value & 0x3F)


# =============================================================================
# UI HELPERS
# =============================================================================

class UnlockItem:
    def __init__(self, name: str, category: str, section: int,
                 hash_value: int = None, bit: int = None, is_costume: bool = False):
        self.name = name
        self.category = category
        self.section = section
        self.hash_value = hash_value
        self.bit = bit
        self.is_costume = is_costume
        self.checked = False


def build_unlock_items() -> list:
    items = []
    for hash_val, name, category in SECTION2_BOOL_UNLOCKS:
        items.append(UnlockItem(name, category, 2, hash_value=hash_val))
    for bit, name in COSTUME_BITS:
        items.append(UnlockItem(name, "COSTUMES", 2, bit=bit, is_costume=True))
    for hash_val, name, category in SECTION3_BOOL_UNLOCKS:
        items.append(UnlockItem(name, category, 3, hash_value=hash_val))
    return items


def load_unlock_states(items: list, sections: list):
    section2 = sections[1]['decompressed'] if len(sections) > 1 else None
    section3 = sections[2]['decompressed'] if len(sections) > 2 else None
    costume_mask = get_costume_bitmask(section2) if section2 else 0

    for item in items:
        if item.section == 2 and section2:
            if item.is_costume:
                item.checked = (costume_mask & item.bit) != 0
            else:
                item.checked = get_bool_unlock_state(section2, item.hash_value)
        elif item.section == 3 and section3:
            item.checked = get_bool_unlock_state(section3, item.hash_value)


def save_unlock_states(items: list, sections: list):
    section2 = sections[1]['decompressed'] if len(sections) > 1 else None
    section3 = sections[2]['decompressed'] if len(sections) > 2 else None

    costume_mask = 0
    for item in items:
        if item.is_costume and item.checked:
            costume_mask |= item.bit

    for item in items:
        if item.section == 2 and section2:
            if item.is_costume:
                set_costume_bitmask(section2, costume_mask)
            else:
                set_bool_unlock_state(section2, item.hash_value, item.checked)
        elif item.section == 3 and section3:
            set_bool_unlock_state(section3, item.hash_value, item.checked)


# =============================================================================
# CURSES UI
# =============================================================================

def run_ui(stdscr, filepath: str, sections: list, platform: str) -> bool:
    """Run the curses UI. Returns True if user wants to save."""
    curses.curs_set(0)
    curses.use_default_colors()

    if curses.has_colors():
        curses.init_pair(1, curses.COLOR_CYAN, -1)
        curses.init_pair(2, curses.COLOR_GREEN, -1)
        curses.init_pair(3, curses.COLOR_YELLOW, -1)

    items = build_unlock_items()
    load_unlock_states(items, sections)

    selected = 0
    modified = False

    while True:
        stdscr.clear()
        height, width = stdscr.getmaxyx()

        # Title
        title = " ACB Brotherhood uPlay Rewards Unlocker "
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

            # Checkbox
            checkbox = "[x]" if item.checked else "[ ]"
            attr = curses.A_REVERSE if i == selected else 0

            stdscr.addstr(row, 4, checkbox, attr)
            stdscr.addstr(row, 8, item.name, attr)
            row += 1

        # Footer
        footer_row = height - 2
        footer = " [Space] Toggle  [A] All On  [N] All Off  [S] Save  [Q] Quit "
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
            return False

        elif key in (ord('s'), ord('S')):
            return True

        elif key in (curses.KEY_UP, ord('k')):
            selected = max(0, selected - 1)

        elif key in (curses.KEY_DOWN, ord('j')):
            selected = min(len(items) - 1, selected + 1)

        elif key in (ord(' '), curses.KEY_ENTER, 10):
            items[selected].checked = not items[selected].checked
            modified = True

        elif key in (ord('a'), ord('A')):
            for item in items:
                item.checked = True
            modified = True

        elif key in (ord('n'), ord('N')):
            for item in items:
                item.checked = False
            modified = True

    return False


def run_with_save(stdscr, filepath: str, sections: list, platform: str) -> tuple:
    """Run UI and return (should_save, items)."""
    curses.curs_set(0)
    curses.use_default_colors()

    if curses.has_colors():
        curses.init_pair(1, curses.COLOR_CYAN, -1)
        curses.init_pair(2, curses.COLOR_GREEN, -1)
        curses.init_pair(3, curses.COLOR_YELLOW, -1)

    items = build_unlock_items()
    load_unlock_states(items, sections)

    selected = 0
    modified = False

    while True:
        stdscr.clear()
        height, width = stdscr.getmaxyx()

        # Title
        title = " ACB Brotherhood uPlay Rewards Unlocker "
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

            if item.category != current_category:
                current_category = item.category
                if row > 4:
                    row += 1
                stdscr.addstr(row, 2, current_category,
                              curses.A_BOLD | (curses.color_pair(2) if curses.has_colors() else 0))
                row += 1

            checkbox = "[x]" if item.checked else "[ ]"
            attr = curses.A_REVERSE if i == selected else 0

            stdscr.addstr(row, 4, checkbox, attr)
            stdscr.addstr(row, 8, item.name, attr)
            row += 1

        footer_row = height - 2
        footer = " [Space] Toggle  [A] All On  [N] All Off  [S] Save  [Q] Quit "
        stdscr.addstr(footer_row, max(0, (width - len(footer)) // 2), footer, curses.A_REVERSE)

        stdscr.refresh()

        key = stdscr.getch()

        if key in (ord('q'), ord('Q'), 27):
            if modified:
                stdscr.addstr(height - 3, 2, "Discard changes? (y/n) ", curses.A_BOLD)
                stdscr.refresh()
                confirm = stdscr.getch()
                if confirm not in (ord('y'), ord('Y')):
                    continue
            return (False, items)

        elif key in (ord('s'), ord('S')):
            save_unlock_states(items, sections)
            return (True, items)

        elif key in (curses.KEY_UP, ord('k')):
            selected = max(0, selected - 1)

        elif key in (curses.KEY_DOWN, ord('j')):
            selected = min(len(items) - 1, selected + 1)

        elif key in (ord(' '), curses.KEY_ENTER, 10):
            items[selected].checked = not items[selected].checked
            modified = True

        elif key in (ord('a'), ord('A')):
            for item in items:
                item.checked = True
            modified = True

        elif key in (ord('n'), ord('N')):
            for item in items:
                item.checked = False
            modified = True

    return (False, items)


# =============================================================================
# SIMPLE TEXT UI (fallback when curses unavailable)
# =============================================================================

def clear_screen():
    """Clear the console screen."""
    os.system('cls' if os.name == 'nt' else 'clear')


def run_text_ui(filepath: str, sections: list, platform: str) -> bool:
    """Run simple text-based UI. Returns True if user wants to save."""
    items = build_unlock_items()
    load_unlock_states(items, sections)

    while True:
        clear_screen()
        print("=" * 60)
        print(" ACB Brotherhood uPlay Rewards Unlocker")
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

            checkbox = "[x]" if item.checked else "[ ]"
            print(f"  {item_num:2d}. {checkbox} {item.name}")
            item_num += 1

        print()
        print("=" * 60)
        print(" Commands: 1-{} toggle | A=all on | N=all off | S=save | Q=quit".format(len(items)))
        print("=" * 60)

        try:
            choice = input("\n> ").strip().upper()
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
            return False

        if choice == 'Q':
            return False
        elif choice == 'S':
            save_unlock_states(items, sections)
            return True
        elif choice == 'A':
            for item in items:
                item.checked = True
        elif choice == 'N':
            for item in items:
                item.checked = False
        elif choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(items):
                items[idx].checked = not items[idx].checked

    return False


# =============================================================================
# MAIN
# =============================================================================

def main_v2():
    if len(sys.argv) < 2:
        print("ACB Brotherhood uPlay Rewards Unlocker")
        print()
        print("Usage: python acb_uplay_unlocker.py <OPTIONS_FILE>")
        print()
        print("Examples:")
        print("  python acb_uplay_unlocker.py OPTIONS.PC")
        print("  python acb_uplay_unlocker.py OPTIONS.PS3")
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

    sections = find_sections(data, platform)
    if len(sections) < 3:
        print(f"Error: Expected at least 3 sections, found {len(sections)}")
        return 1

    print(f"Found {len(sections)} sections")

    # Capture trailing data for PS3
    trailing_data = get_trailing_data(data, platform, sections)

    try:
        save, items = curses.wrapper(
            lambda stdscr: run_with_save(stdscr, filepath, sections, platform))
    except KeyboardInterrupt:
        print("\nCancelled.")
        return 0

    if save:
        print(f"\nSaving to {filepath}...")
        save_options_file(filepath, sections, platform, trailing_data)
        print("Done!")
    else:
        print("\nNo changes saved.")

    return 0


def main_text():
    """Main entry point for text UI."""
    if len(sys.argv) < 2:
        print("ACB Brotherhood uPlay Rewards Unlocker")
        print()
        print("Usage: python acb_uplay_unlocker.py <OPTIONS_FILE>")
        print()
        print("Examples:")
        print("  python acb_uplay_unlocker.py OPTIONS.PC")
        print("  python acb_uplay_unlocker.py OPTIONS.PS3")
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

    sections = find_sections(data, platform)
    if len(sections) < 3:
        print(f"Error: Expected at least 3 sections, found {len(sections)}")
        return 1

    print(f"Found {len(sections)} sections")

    # Capture trailing data for PS3
    trailing_data = get_trailing_data(data, platform, sections)

    save = run_text_ui(filepath, sections, platform)

    if save:
        print(f"\nSaving to {filepath}...")
        save_options_file(filepath, sections, platform, trailing_data)
        print("Done!")
    else:
        print("\nNo changes saved.")

    return 0


if __name__ == "__main__":
    if HAS_CURSES:
        sys.exit(main_v2())
    else:
        sys.exit(main_text())
