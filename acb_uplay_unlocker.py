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

import lzss

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
        decompressed = lzss.decompress(compressed_data)

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
        compressed = lzss.compress(bytes(section['decompressed']))
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

def run_with_save(stdscr, filepath: str, sections: list, platform: str) -> bool:
    """Run UI and return True if user wants to save."""
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

        if key in (ord('q'), ord('Q'), 27):
            if modified:
                stdscr.addstr(height - 3, 2, "Discard changes? (y/n) ", curses.A_BOLD)
                stdscr.refresh()
                confirm = stdscr.getch()
                if confirm not in (ord('y'), ord('Y')):
                    continue
            return False

        elif key in (ord('s'), ord('S')):
            save_unlock_states(items, sections)
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


# =============================================================================
# MAIN
# =============================================================================

def _load_options_file(filepath: str):
    """
    Load and validate OPTIONS file.

    Returns (sections, platform, trailing_data) on success, or None on error.
    """
    if not os.path.exists(filepath):
        print(f"Error: File not found: {filepath}")
        return None

    print(f"Loading {filepath}...")

    with open(filepath, 'rb') as f:
        data = f.read()

    platform = detect_format(data)
    if platform == 'unknown':
        print("Error: Could not detect file format (PC or PS3)")
        return None

    print(f"Detected format: {platform}")

    sections = find_sections(data, platform)
    if len(sections) < 3:
        print(f"Error: Expected at least 3 sections, found {len(sections)}")
        return None

    print(f"Found {len(sections)} sections")

    trailing_data = get_trailing_data(data, platform, sections)

    return sections, platform, trailing_data


def main():
    """Main entry point."""
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

    result = _load_options_file(filepath)
    if result is None:
        return 1

    sections, platform, trailing_data = result

    # Run appropriate UI
    if HAS_CURSES:
        try:
            save = curses.wrapper(
                lambda stdscr: run_with_save(stdscr, filepath, sections, platform))
        except KeyboardInterrupt:
            print("\nCancelled.")
            return 0
    else:
        save = run_text_ui(filepath, sections, platform)

    if save:
        print(f"\nSaving to {filepath}...")
        save_options_file(filepath, sections, platform, trailing_data)
        print("Done!")
    else:
        print("\nNo changes saved.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
