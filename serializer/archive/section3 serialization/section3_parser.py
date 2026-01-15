#!/usr/bin/env python3
"""
Section 3 Binary Parser - Fully Dynamic Implementation

Parses game_uncompressed_3.bin to JSON format.
Based on 1:1 reverse engineering from GHIDRA decompilation and WinDbg TTD tracing.

See docs/SECTION3_SERIALIZATION.md for detailed trace notes.

FILE STRUCTURE (from docs/SECTION3_SERIALIZATION.md):
=====================================
=== OBJECTINFO HEADER (0x00-0x0D) - Written by FUN_01b08ce0 ===
0x00    (1 byte)  NbClassVersionsInfo    - FUN_01b0d500 (vtable[0x98])
0x01    (4 bytes) ObjectName length      - FUN_01b48e90 (vtable[0x54])
0x05    (4 bytes) ObjectID               - FUN_01b48e70 (vtable[0x9c])
0x09    (1 byte)  InstancingMode         - FUN_01b0d500 (vtable[0x98])
0x0A    (4 bytes) TypeHash               - FUN_01b48fb0 (vtable[0x50])

=== SECTION SIZE RESERVATIONS (0x0E-0x19) - Reserved via OpenSection ===
0x0E    (4 bytes) "Object" section size      - Backpatched at E68A1F:D0
0x12    (4 bytes) "Properties" section size  - Backpatched at E68A1D:B87
0x16    (4 bytes) Base class section size    - Backpatched at E68A19:CF7

=== CONTENT (0x1A onwards) ===
0x1A    (4 bytes) base_class_hash        - 0xbf4c2013
0x1E    (8 bytes) base_class_type_info
0x26    (1 byte)  base_class_flags       - 0x0b (property flags byte!)
0x27    (4 bytes) base_class_value       - uint32 value
0x2B    (N bytes) Properties             - [size 4][hash 4][type_info 8][flags 1][value N]
...     (4 bytes) Trailing zeros         - Dynamic Properties section size = 0

SERIALIZER VERSION:
===================
[context+0x24] = 0x10 (16) means version >= 9, so type_info is 8 bytes direct.

SECTION NESTING (LIFO):
=======================
Push: OpenSection("Object")     -> saves position 0x0e, stack[0]
Push: OpenSection("Properties") -> saves position 0x12, stack[1]
Push: OpenSection(base class)   -> saves position 0x16, stack[2]
Pop:  CloseSection              -> patches 0x16 with size 17
Pop:  CloseSection              -> patches 0x12 with size 136
Pop:  CloseSection              -> patches 0x0e with size 144

PROPERTY FORMAT:
================
[size 4][hash 4][type_info 8][flags 1][value N]
- Size: Backpatched by CloseSection with (hash + type_info + flags + value) = content size
- Hash: 4 bytes, property identifier
- Type_info: 8 bytes, type descriptor (version >= 9 uses direct 8-byte format)
- Flags: 1 byte, always 0x0b in traces (PropertyHeaderFlag)
- Value: Variable size (1 byte for bool, 8 bytes for uint64)

KNOWN PROPERTY HASHES (from traces):
====================================
0xbf4c2013 = base class field (SaveGameDataObject)
0x3b546966 = bool_field_0x20
0x4dbc7da7 = bool_field_0x21
0x5b95f10b = bool_field_0x22
0x2a4e8a90 = bool_field_0x23
0x496f8780 = uint64_field_0x18
0x6f88b05b = bool_field_0x24

Class Hierarchy:
  AssassinSingleProfileData (0xc9876d66)
    -> SaveGameDataObject (0xb7806f86)

Binary Format: Little-endian (confirmed via WinDbg)
"""

import struct
import json
import sys
from dataclasses import dataclass, field
from typing import List, Any, Dict, Optional, Tuple


# =============================================================================
# Constants from Reverse Engineering (docs/SECTION3_SERIALIZATION.md)
# =============================================================================

# Type hashes (from GHIDRA)
TYPE_HASH_ASSASSIN_SINGLE_PROFILE_DATA = 0xc9876d66
TYPE_HASH_SAVE_GAME_DATA_OBJECT = 0xb7806f86

# Base class field hash (from DAT_027ecf90)
# Traced at 0x1a-0x1d in the file
BASE_CLASS_FIELD_HASH = 0xbf4c2013

# Property hashes (from DAT_02973250 etc. in GHIDRA)
# Maps hash -> (name, type_code, object_offset)
# Type code 0x00 = bool, 0x09 = uint64 (from type_info bits 16-21)
KNOWN_PROPERTY_HASHES = {
    0x3b546966: ("bool_field_0x20", 0x00, 0x20),    # DAT_02973250
    0x4dbc7da7: ("bool_field_0x21", 0x00, 0x21),    # DAT_02973270
    0x5b95f10b: ("bool_field_0x22", 0x00, 0x22),    # DAT_02973290
    0x2a4e8a90: ("bool_field_0x23", 0x00, 0x23),    # DAT_029732b0
    0x496f8780: ("uint64_field_0x18", 0x09, 0x18),  # DAT_029732d0
    0x6f88b05b: ("bool_field_0x24", 0x00, 0x24),    # DAT_029732f0
}

# Type info encoding (from FUN_01b0ca30 analysis)
# Type code is at bits 16-21 of the second uint32 in type_info
# Type 0x00 = bool (type_info is all zeros)
# Type 0x09 = uint64 (type_info has 0x09 at byte offset 6)
#
# Type codes derived from vtable order at 0x02555c60 (see docs/SECTION3_SERIALIZATION.md):
# Vtable offset -> Type (byte count)
# 0x58 -> bool (1)     0x5c -> vec4 (16)    0x60 -> mat4x4 (64)
# 0x64 -> mat3x3 (36)  0x68 -> quat (16)    0x6c -> vec3 (12)
# 0x70 -> vec2 (8)     0x74 -> float32 (4)  0x78 -> float64 (8)
# 0x7c -> uint64 (8)   0x80 -> int32 (4)    0x84 -> uint32 (4)
# 0x88 -> uint16 (2)   0x8c -> int16 (2)    0x90 -> uint8 (1)
# 0x94 -> int8 (1)

# Primitive type codes
# CONFIRMED from Ghidra PropertyDescriptor analysis:
#   0x00 = bool, 0x07 = uint32, 0x09 = uint64
# Other codes below are SPECULATIVE and unverified
TYPE_CODE_BOOL = 0x00     # CONFIRMED from Ghidra
TYPE_CODE_INT8 = 0x01     # speculative
TYPE_CODE_UINT8 = 0x02    # speculative
TYPE_CODE_INT16 = 0x03    # speculative
TYPE_CODE_UINT16 = 0x04   # speculative
TYPE_CODE_INT32 = 0x05    # speculative
TYPE_CODE_UINT32 = 0x07   # CONFIRMED from Ghidra (was incorrectly 0x06)
TYPE_CODE_INT64 = 0x08    # speculative (moved from 0x07 to avoid conflict)
TYPE_CODE_UINT64 = 0x09   # CONFIRMED from Ghidra

# Floating point type codes
TYPE_CODE_FLOAT32 = 0x0A
TYPE_CODE_FLOAT64 = 0x0B

# Vector/Matrix type codes
TYPE_CODE_VEC2 = 0x0C      # 2x float32 (8 bytes)
TYPE_CODE_VEC3 = 0x0D      # 3x float32 (12 bytes)
TYPE_CODE_VEC4 = 0x0E      # 4x float32 (16 bytes)
TYPE_CODE_QUAT = 0x0F      # 4x float32 (16 bytes, quaternion)
TYPE_CODE_MAT3X3 = 0x10    # 9x float32 (36 bytes)
TYPE_CODE_MAT4X4 = 0x11    # 16x float32 (64 bytes)

# Property flags byte - "PropertyHeaderFlag"
# Written by FUN_01b076f0 via vtable[0x98] (FUN_01b48b70 - WriteByte)
# The value 0x0b (binary: 00001011):
#   - Bit 0 (Final) = 1
#   - Bit 1 (Owned) = 1
#   - Bit 3 = 1
# Always 0x0b in all traces (both READ and WRITE paths)
PROPERTY_FLAGS_BYTE = 0x0b


# =============================================================================
# Binary Reader (mirrors stream reader from WinDbg - FUN_01b6f3b0, FUN_01b6f440, FUN_01b6f490)
# =============================================================================

class BinaryReader:
    """
    Mirrors the game's stream reader.

    From WinDbg trace (docs/SECTION3_SERIALIZATION.md):
    - Stream object at [serializer+0x08]
    - Buffer position at [stream+0x18]
    - Position adjusts by type size (1, 4, or 8 bytes)

    Core read functions traced:
    - FUN_01b6f3b0: 1-byte read (vtable[0x24])
    - FUN_01b6f440: 4-byte read (vtable[0x1c])
    - FUN_01b6f490: 8-byte read (vtable[0x18])
    """

    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0
        self.size = len(data)

    def read_int8(self) -> int:
        """Read 1 byte signed - mirrors FUN_01b6f150 (inner_vtable[0x24])"""
        if self.pos >= self.size:
            raise EOFError(f"Read past end at offset 0x{self.pos:x}")
        val = struct.unpack_from('<b', self.data, self.pos)[0]
        self.pos += 1
        return val

    def read_uint8(self) -> int:
        """Read 1 byte unsigned - mirrors FUN_01b6f150 (inner_vtable[0x24])"""
        if self.pos >= self.size:
            raise EOFError(f"Read past end at offset 0x{self.pos:x}")
        val = self.data[self.pos]
        self.pos += 1
        return val

    def read_int16(self) -> int:
        """Read 2 bytes signed - mirrors FUN_01b6f400 (inner_vtable[0x20])"""
        if self.pos + 2 > self.size:
            raise EOFError(f"Read past end at offset 0x{self.pos:x}")
        val = struct.unpack_from('<h', self.data, self.pos)[0]
        self.pos += 2
        return val

    def read_uint16(self) -> int:
        """Read 2 bytes unsigned - mirrors FUN_01b6f400 (inner_vtable[0x20])"""
        if self.pos + 2 > self.size:
            raise EOFError(f"Read past end at offset 0x{self.pos:x}")
        val = struct.unpack_from('<H', self.data, self.pos)[0]
        self.pos += 2
        return val

    def read_int32(self) -> int:
        """Read 4 bytes signed - mirrors FUN_01b6f440 (inner_vtable[0x1c])"""
        if self.pos + 4 > self.size:
            raise EOFError(f"Read past end at offset 0x{self.pos:x}")
        val = struct.unpack_from('<i', self.data, self.pos)[0]
        self.pos += 4
        return val

    def read_uint32(self) -> int:
        """Read 4 bytes unsigned - mirrors FUN_01b6f440 (inner_vtable[0x1c])"""
        if self.pos + 4 > self.size:
            raise EOFError(f"Read past end at offset 0x{self.pos:x}")
        val = struct.unpack_from('<I', self.data, self.pos)[0]
        self.pos += 4
        return val

    def read_int64(self) -> int:
        """Read 8 bytes signed - mirrors FUN_01b6f490 (inner_vtable[0x18])"""
        if self.pos + 8 > self.size:
            raise EOFError(f"Read past end at offset 0x{self.pos:x}")
        val = struct.unpack_from('<q', self.data, self.pos)[0]
        self.pos += 8
        return val

    def read_uint64(self) -> int:
        """Read 8 bytes unsigned - mirrors FUN_01b6f490 (inner_vtable[0x18])"""
        if self.pos + 8 > self.size:
            raise EOFError(f"Read past end at offset 0x{self.pos:x}")
        val = struct.unpack_from('<Q', self.data, self.pos)[0]
        self.pos += 8
        return val

    def read_float32(self) -> float:
        """Read 4-byte float - mirrors FUN_01b6f440 (inner_vtable[0x1c])"""
        if self.pos + 4 > self.size:
            raise EOFError(f"Read past end at offset 0x{self.pos:x}")
        val = struct.unpack_from('<f', self.data, self.pos)[0]
        self.pos += 4
        return val

    def read_float64(self) -> float:
        """Read 8-byte double - mirrors FUN_01b6f490 (inner_vtable[0x18])"""
        if self.pos + 8 > self.size:
            raise EOFError(f"Read past end at offset 0x{self.pos:x}")
        val = struct.unpack_from('<d', self.data, self.pos)[0]
        self.pos += 8
        return val

    def read_vec2(self) -> List[float]:
        """Read vec2 (2x float32, 8 bytes) - vtable[0x70]"""
        return [self.read_float32() for _ in range(2)]

    def read_vec3(self) -> List[float]:
        """Read vec3 (3x float32, 12 bytes) - vtable[0x6c]"""
        return [self.read_float32() for _ in range(3)]

    def read_vec4(self) -> List[float]:
        """Read vec4 (4x float32, 16 bytes) - vtable[0x5c]"""
        return [self.read_float32() for _ in range(4)]

    def read_quat(self) -> List[float]:
        """Read quaternion (4x float32, 16 bytes) - vtable[0x68]"""
        return [self.read_float32() for _ in range(4)]

    def read_mat3x3(self) -> List[List[float]]:
        """Read mat3x3 (9x float32, 36 bytes) - vtable[0x64]"""
        return [[self.read_float32() for _ in range(3)] for _ in range(3)]

    def read_mat4x4(self) -> List[List[float]]:
        """Read mat4x4 (16x float32, 64 bytes) - vtable[0x60]"""
        return [[self.read_float32() for _ in range(4)] for _ in range(4)]

    def read_bytes(self, count: int) -> bytes:
        """Read N bytes"""
        if self.pos + count > self.size:
            raise EOFError(f"Read past end at offset 0x{self.pos:x}")
        val = self.data[self.pos:self.pos + count]
        self.pos += count
        return val

    def peek_uint32(self) -> int:
        """Peek 4 bytes without advancing position"""
        if self.pos + 4 > self.size:
            return 0
        return struct.unpack_from('<I', self.data, self.pos)[0]

    def remaining(self) -> int:
        return self.size - self.pos

    def tell(self) -> int:
        return self.pos

    def seek(self, pos: int):
        self.pos = pos


# =============================================================================
# Binary Writer (mirrors stream writer from WinDbg - FUN_01b6f370, FUN_01b6fea0, FUN_01b6fef0)
# =============================================================================

class BinaryWriter:
    """
    Mirrors the game's stream writer with section nesting support.

    From WinDbg trace (docs/SECTION3_SERIALIZATION.md):
    - Stream object stores buffer pointer at [stream+0x18]
    - Position advances after each write

    Core write functions traced:
    - FUN_01b6f370: 1-byte write (inner_vtable[0x3c])
    - FUN_01b6fea0: 4-byte write (inner_vtable[0x34])
    - FUN_01b6fef0: 8-byte write (inner_vtable[0x30])

    Section Stack (LIFO):
    - OpenSection reserves 4 bytes, pushes position to stack
    - CloseSection pops position, calculates size, patches the reservation
    """

    def __init__(self):
        self.data = bytearray()
        self.section_stack: List[int] = []  # Stack of section start positions

    def write_int8(self, val: int):
        """Write 1 byte signed - mirrors FUN_01b6f370 (inner_vtable[0x3c])"""
        self.data.extend(struct.pack('<b', val))

    def write_uint8(self, val: int):
        """Write 1 byte unsigned - mirrors FUN_01b6f370 (inner_vtable[0x3c])"""
        self.data.append(val & 0xFF)

    def write_int16(self, val: int):
        """Write 2 bytes signed - mirrors FUN_01b6fe40 (inner_vtable[0x38])"""
        self.data.extend(struct.pack('<h', val))

    def write_uint16(self, val: int):
        """Write 2 bytes unsigned - mirrors FUN_01b6fe40 (inner_vtable[0x38])"""
        self.data.extend(struct.pack('<H', val))

    def write_int32(self, val: int):
        """Write 4 bytes signed - mirrors FUN_01b6fea0 (inner_vtable[0x34])"""
        self.data.extend(struct.pack('<i', val))

    def write_uint32(self, val: int):
        """Write 4 bytes unsigned - mirrors FUN_01b6fea0 (inner_vtable[0x34])"""
        self.data.extend(struct.pack('<I', val))

    def write_int64(self, val: int):
        """Write 8 bytes signed - mirrors FUN_01b6f4e0 (inner_vtable[0x30])"""
        self.data.extend(struct.pack('<q', val))

    def write_uint64(self, val: int):
        """Write 8 bytes unsigned - mirrors FUN_01b6f4e0 (inner_vtable[0x30])"""
        self.data.extend(struct.pack('<Q', val))

    def write_float32(self, val: float):
        """Write 4-byte float - mirrors FUN_01b6fea0 (inner_vtable[0x34])"""
        self.data.extend(struct.pack('<f', val))

    def write_float64(self, val: float):
        """Write 8-byte double - mirrors FUN_01b6f4e0 (inner_vtable[0x30])"""
        self.data.extend(struct.pack('<d', val))

    def write_vec2(self, val: List[float]):
        """Write vec2 (2x float32, 8 bytes) - vtable[0x70]"""
        for v in val[:2]:
            self.write_float32(v)

    def write_vec3(self, val: List[float]):
        """Write vec3 (3x float32, 12 bytes) - vtable[0x6c]"""
        for v in val[:3]:
            self.write_float32(v)

    def write_vec4(self, val: List[float]):
        """Write vec4 (4x float32, 16 bytes) - vtable[0x5c]"""
        for v in val[:4]:
            self.write_float32(v)

    def write_quat(self, val: List[float]):
        """Write quaternion (4x float32, 16 bytes) - vtable[0x68]"""
        for v in val[:4]:
            self.write_float32(v)

    def write_mat3x3(self, val: List[List[float]]):
        """Write mat3x3 (9x float32, 36 bytes) - vtable[0x64]"""
        for row in val[:3]:
            for v in row[:3]:
                self.write_float32(v)

    def write_mat4x4(self, val: List[List[float]]):
        """Write mat4x4 (16x float32, 64 bytes) - vtable[0x60]"""
        for row in val[:4]:
            for v in row[:4]:
                self.write_float32(v)

    def write_bytes(self, data: bytes):
        """Write raw bytes"""
        self.data.extend(data)

    def open_section(self) -> int:
        """
        OpenSection - FUN_01b48890 (vtable[0x0c])

        Reserves 4 bytes for section size and pushes position to stack.
        The size will be backpatched by close_section().

        Returns: Position of the size field (for reference)
        """
        pos = len(self.data)
        self.section_stack.append(pos)
        # Reserve 4 bytes for size (will be backpatched)
        self.write_uint32(0)
        return pos

    def close_section(self):
        """
        CloseSection - FUN_01b48920 (vtable[0x14])

        Pops section start from stack and backpatches the size field.
        Size = current_position - (section_start + 4)

        From docs/SECTION3_SERIALIZATION.md Section Nesting:
        - inner_vtable[0x50]: Seek to saved position
        - inner_vtable[0x34]: Write size via FUN_01b6fea0
        - inner_vtable[0x54]: Seek back to current position
        """
        if not self.section_stack:
            raise RuntimeError("CloseSection called with empty section stack")

        section_start = self.section_stack.pop()
        current_pos = len(self.data)
        # Size is bytes after the 4-byte size field itself
        section_size = current_pos - (section_start + 4)

        # Backpatch the size field
        struct.pack_into('<I', self.data, section_start, section_size)

    def patch_uint32(self, pos: int, val: int):
        """Patch a uint32 at a specific position"""
        struct.pack_into('<I', self.data, pos, val)

    def get_bytes(self) -> bytes:
        return bytes(self.data)

    def tell(self) -> int:
        return len(self.data)


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class Property:
    """A serialized property parsed from the binary."""
    file_offset: int        # Offset of property start (size field)
    size: int               # Size field value (content size after size field)
    hash: int               # Property hash (4 bytes)
    type_info: bytes        # Type info (8 bytes)
    flags: int              # Flags byte (always 0x0b in traces)
    name: str               # Property name from hash lookup
    prop_type: str          # Type string ("bool" or "uint64")
    value: Any              # Parsed value


@dataclass
class Section3Data:
    """Complete parsed Section 3 data."""
    file_size: int
    header: Dict[str, Any]
    base_class: Dict[str, Any]
    properties: List[Property]
    trailing_size: int      # Dynamic Properties section size (should be 0)


# =============================================================================
# Type Info Helpers
# =============================================================================

def type_info_to_type_code(type_info: bytes) -> int:
    """
    Extract type code from type_info bytes.

    From FUN_01b0ca30 analysis:
    - Type code is at bits 16-21 of the second uint32
    - For version >= 9, type_info is 8 bytes direct

    Bool type_info: 00 00 00 00 00 00 00 00 -> type code 0x00
    Uint64 type_info: 00 00 00 00 00 00 09 00 -> type code 0x09
    """
    if len(type_info) < 8:
        return TYPE_CODE_BOOL

    # Type code is at byte offset 6 (bits 16-21 of second dword)
    return type_info[6] & 0x3F


def make_type_info(type_code: int) -> bytes:
    """
    Create type_info bytes from type code.

    From docs/SECTION3_SERIALIZATION.md:
    - Bool type_info: 00 00 00 00 00 00 00 00
    - Uint64 type_info: 00 00 00 00 00 00 09 00
    """
    type_info = bytearray(8)
    if type_code != TYPE_CODE_BOOL:
        type_info[6] = type_code
    return bytes(type_info)


# Type code to string mapping
TYPE_CODE_NAMES = {
    TYPE_CODE_BOOL: "bool",
    TYPE_CODE_INT8: "int8",
    TYPE_CODE_UINT8: "uint8",
    TYPE_CODE_INT16: "int16",
    TYPE_CODE_UINT16: "uint16",
    TYPE_CODE_INT32: "int32",
    TYPE_CODE_UINT32: "uint32",
    TYPE_CODE_INT64: "int64",
    TYPE_CODE_UINT64: "uint64",
    TYPE_CODE_FLOAT32: "float32",
    TYPE_CODE_FLOAT64: "float64",
    TYPE_CODE_VEC2: "vec2",
    TYPE_CODE_VEC3: "vec3",
    TYPE_CODE_VEC4: "vec4",
    TYPE_CODE_QUAT: "quat",
    TYPE_CODE_MAT3X3: "mat3x3",
    TYPE_CODE_MAT4X4: "mat4x4",
}

# Type code to size mapping (in bytes)
TYPE_CODE_SIZES = {
    TYPE_CODE_BOOL: 1,
    TYPE_CODE_INT8: 1,
    TYPE_CODE_UINT8: 1,
    TYPE_CODE_INT16: 2,
    TYPE_CODE_UINT16: 2,
    TYPE_CODE_INT32: 4,
    TYPE_CODE_UINT32: 4,
    TYPE_CODE_INT64: 8,
    TYPE_CODE_UINT64: 8,
    TYPE_CODE_FLOAT32: 4,
    TYPE_CODE_FLOAT64: 8,
    TYPE_CODE_VEC2: 8,      # 2x float32
    TYPE_CODE_VEC3: 12,     # 3x float32
    TYPE_CODE_VEC4: 16,     # 4x float32
    TYPE_CODE_QUAT: 16,     # 4x float32
    TYPE_CODE_MAT3X3: 36,   # 9x float32
    TYPE_CODE_MAT4X4: 64,   # 16x float32
}


def type_code_to_string(type_code: int) -> str:
    """Convert type code to string representation."""
    return TYPE_CODE_NAMES.get(type_code, f"unknown_0x{type_code:02x}")


def value_size_for_type(type_code: int) -> int:
    """Get value size in bytes for a type code."""
    if type_code in TYPE_CODE_SIZES:
        return TYPE_CODE_SIZES[type_code]
    raise ValueError(f"Unknown type code: 0x{type_code:02x}")


# =============================================================================
# Parser Implementation (READ Path)
# =============================================================================

def parse_section3(filepath: str) -> Section3Data:
    """
    Parse Section 3 binary file.

    Follows the exact READ path traced in docs/SECTION3_SERIALIZATION.md:

    FUN_01710580 (AssassinSingleProfileData::Serialize)
      -> Mode check: [serializer+4]+4 == 0x01 (READ mode)
      -> Skip header write (READ mode)
      -> FUN_005e3700 (SaveGameDataObject::Serialize base class)
      -> FUN_01b09650 (bool property) x5
      -> FUN_01b09760 (uint64 property) x1
      -> FUN_01b0d0c0 (finalization)
    """

    with open(filepath, 'rb') as f:
        data = f.read()

    reader = BinaryReader(data)

    # =========================================================================
    # Parse ObjectInfo Header (0x00-0x0D)
    # Written by FUN_01b08ce0
    # =========================================================================
    header = {}

    # 0x00: NbClassVersionsInfo (1 byte)
    # Written by FUN_01b0d500("NbClassVersionsInfo", &byte) via vtable[0x98]
    header['nb_class_versions_info'] = reader.read_uint8()

    # 0x01-0x04: ObjectName length (4 bytes)
    # Written by FUN_01b48e90 (vtable[0x54]) - string serializer
    # Value 0 = empty string (no string data follows)
    header['object_name_length'] = reader.read_uint32()

    # 0x05-0x08: ObjectID (4 bytes)
    # Written by FUN_01b48e70 (vtable[0x9c]) - uint32 serializer
    header['object_id'] = reader.read_uint32()

    # 0x09: InstancingMode (1 byte)
    # Written by FUN_01b0d500("InstancingMode", &byte) via vtable[0x98]
    header['instancing_mode'] = reader.read_uint8()

    # 0x0A-0x0D: TypeHash (4 bytes)
    # Written by FUN_01b48fb0 (vtable[0x50]) - type info serializer
    # For version where [serializer+0x1012] = 0, only writes hash, no string
    header['type_hash'] = reader.read_uint32()

    # Resolve type name
    if header['type_hash'] == TYPE_HASH_ASSASSIN_SINGLE_PROFILE_DATA:
        header['type_name'] = "AssassinSingleProfileData"
    else:
        header['type_name'] = f"Unknown_0x{header['type_hash']:08x}"

    # =========================================================================
    # Parse Section Size Reservations (0x0E-0x19)
    # Reserved by OpenSection calls, backpatched by CloseSection
    # =========================================================================

    # 0x0E-0x11: "Object" section size
    # OpenSection in FUN_01b08ce0, backpatched at E68A1F:D0
    # Size covers: offset 0x12 to EOF
    header['object_section_size'] = reader.read_uint32()

    # 0x12-0x15: "Properties" section size
    # OpenSection in FUN_01b08ce0, backpatched at E68A1D:B87
    # Size covers: offset 0x1a to EOF
    header['properties_section_size'] = reader.read_uint32()

    # 0x16-0x19: Base class section size
    # OpenSection in SaveGameDataObject::Serialize, backpatched at E68A19:CF7
    # Size covers: base class property only (17 bytes)
    header['base_class_section_size'] = reader.read_uint32()

    # =========================================================================
    # Parse Base Class Field Property (0x1A-0x2A)
    # Serialized by FUN_01b0a1f0 -> FUN_01b12fa0 -> FUN_01b076f0
    # Format: [hash 4][type_info 8][flags 1][value 4] = 17 bytes
    # NOTE: No size field - base class uses shortened property format
    # =========================================================================
    base_class = {}
    base_class_start = reader.tell()

    # 0x1A-0x1D: Base class hash (4 bytes)
    base_class['hash'] = reader.read_uint32()

    # 0x1E-0x25: Base class type_info (8 bytes)
    # Written by FUN_01b0e980 via vtable[0x4c] (version >= 9 path)
    base_class['type_info'] = reader.read_bytes(8)

    # 0x26: Base class flags (1 byte)
    # Written by FUN_01b076f0 via vtable[0x98]
    # This is the property flags byte (0x0b), NOT NbClassVersionsInfo!
    base_class['flags'] = reader.read_uint8()

    # 0x27-0x2A: Base class value (4 bytes)
    # Actual field value from SaveGameDataObject at object+0x04
    # Read by FUN_01b6f440 (4-byte read) at B1F2B:B7B
    base_class['value'] = reader.read_uint32()

    # Verify we read exactly the expected size
    base_class_bytes_read = reader.tell() - base_class_start
    if base_class_bytes_read != header['base_class_section_size']:
        print(f"Warning: Base class section size mismatch: expected {header['base_class_section_size']}, read {base_class_bytes_read}")

    # =========================================================================
    # Parse Properties (0x2B onwards)
    # Each property: [size 4][hash 4][type_info 8][flags 1][value N]
    # =========================================================================
    properties = []

    # Calculate expected end of properties section
    # properties_section_size = bytes from base class start to EOF minus trailing zeros
    # trailing_size is the Dynamic Properties section size (4 bytes of zeros)
    # Properties end = file_size - 4 (trailing zeros)
    properties_end = len(data) - 4

    while reader.tell() < properties_end:
        prop_start = reader.tell()

        # Read size field (4 bytes)
        # Written by OpenSection("Property"), backpatched by CloseSection
        prop_size = reader.read_uint32()

        # Sanity check: size should be at least 13 (hash + type_info + flags)
        if prop_size < 13:
            # Might be trailing zeros or invalid data
            reader.seek(prop_start)
            break

        # Read hash (4 bytes)
        # Written by FUN_01b0e680 -> FUN_01b48fb0 -> FUN_01b49610
        prop_hash = reader.read_uint32()

        # Read type_info (8 bytes)
        # Written by FUN_01b0e980 -> FUN_01b49020 -> FUN_01b496d0
        # Version >= 9 uses direct 8-byte format
        type_info = reader.read_bytes(8)

        # Read flags (1 byte)
        # Written by FUN_01b076f0 via vtable[0x98]
        flags = reader.read_uint8()

        # Determine type from type_info
        type_code = type_info_to_type_code(type_info)
        prop_type = type_code_to_string(type_code)

        # Read value based on type
        # Each type uses specific vtable entry and inner read function
        if type_code == TYPE_CODE_BOOL:
            # vtable[0x58] -> FUN_01b497f0 (1 byte)
            value = bool(reader.read_uint8())
        elif type_code == TYPE_CODE_INT8:
            # vtable[0x94] -> FUN_01b49490 (1 byte signed)
            value = reader.read_int8()
        elif type_code == TYPE_CODE_UINT8:
            # vtable[0x90] -> FUN_01b494f0 (1 byte unsigned)
            value = reader.read_uint8()
        elif type_code == TYPE_CODE_INT16:
            # vtable[0x8c] -> FUN_01b49550 (2 bytes signed)
            value = reader.read_int16()
        elif type_code == TYPE_CODE_UINT16:
            # vtable[0x88] -> FUN_01b495b0 (2 bytes unsigned)
            value = reader.read_uint16()
        elif type_code == TYPE_CODE_INT32:
            # vtable[0x80] -> FUN_01b49670 (4 bytes signed)
            value = reader.read_int32()
        elif type_code == TYPE_CODE_UINT32:
            # vtable[0x84] -> FUN_01b49610 (4 bytes unsigned)
            value = reader.read_uint32()
        elif type_code == TYPE_CODE_INT64:
            # 8 bytes signed
            value = reader.read_int64()
        elif type_code == TYPE_CODE_UINT64:
            # vtable[0x7c] -> FUN_01b496d0 (8 bytes)
            value = reader.read_int64()  # Signed int64 based on trace
        elif type_code == TYPE_CODE_FLOAT32:
            # vtable[0x74] -> FUN_01b49790 (4 bytes float)
            value = reader.read_float32()
        elif type_code == TYPE_CODE_FLOAT64:
            # vtable[0x78] -> FUN_01b49730 (8 bytes double)
            value = reader.read_float64()
        elif type_code == TYPE_CODE_VEC2:
            # vtable[0x70] -> 2x inner[0x34] (8 bytes)
            value = reader.read_vec2()
        elif type_code == TYPE_CODE_VEC3:
            # vtable[0x6c] -> 3x inner[0x34] (12 bytes)
            value = reader.read_vec3()
        elif type_code == TYPE_CODE_VEC4:
            # vtable[0x5c] -> 4x inner[0x34] (16 bytes)
            value = reader.read_vec4()
        elif type_code == TYPE_CODE_QUAT:
            # vtable[0x68] -> 4x inner[0x34] (16 bytes, quaternion)
            value = reader.read_quat()
        elif type_code == TYPE_CODE_MAT3X3:
            # vtable[0x64] -> 9x inner[0x34] (36 bytes)
            value = reader.read_mat3x3()
        elif type_code == TYPE_CODE_MAT4X4:
            # vtable[0x60] -> 16x inner[0x34] (64 bytes)
            value = reader.read_mat4x4()
        else:
            # Unknown type - read based on size field
            remaining_value_bytes = prop_size - 13  # size - (hash + type_info + flags)
            value = reader.read_bytes(remaining_value_bytes).hex()
            prop_type = f"unknown_0x{type_code:02x}"

        # Look up property name
        if prop_hash in KNOWN_PROPERTY_HASHES:
            prop_name = KNOWN_PROPERTY_HASHES[prop_hash][0]
        else:
            prop_name = f"unknown_0x{prop_hash:08x}"

        properties.append(Property(
            file_offset=prop_start,
            size=prop_size,
            hash=prop_hash,
            type_info=type_info,
            flags=flags,
            name=prop_name,
            prop_type=prop_type,
            value=value
        ))

    # =========================================================================
    # Parse Trailing Bytes (Dynamic Properties section size)
    # Written by CloseSection("Dynamic Properties") at B1F2B:1CB2
    # Size = 0x00000000 (no dynamic properties in this file)
    # =========================================================================
    trailing_size = reader.read_uint32()

    return Section3Data(
        file_size=len(data),
        header=header,
        base_class=base_class,
        properties=properties,
        trailing_size=trailing_size
    )


# =============================================================================
# Serializer Implementation (WRITE Path)
# =============================================================================

def serialize_section3(data: Section3Data) -> bytes:
    """
    Serialize Section3Data back to binary format.

    Follows the exact WRITE path traced in docs/SECTION3_SERIALIZATION.md:

    FUN_01710580 (AssassinSingleProfileData::Serialize)
      -> Mode check: [serializer+4]+4 == 0x00 (WRITE mode)
      -> FUN_01b08ce0 (header writer)
      -> FUN_005e3700 (SaveGameDataObject::Serialize base class)
      -> FUN_01b09650 (bool property) x5
      -> FUN_01b09760 (uint64 property) x1
      -> FUN_01b0d0c0 (finalization - writes trailing zeros)

    Section Stack (LIFO):
      Push: OpenSection("Object")     -> offset 0x0e
      Push: OpenSection("Properties") -> offset 0x12
      Push: OpenSection(base class)   -> offset 0x16
      Pop:  CloseSection              -> patches 0x16
      Pop:  CloseSection              -> patches 0x12
      Pop:  CloseSection              -> patches 0x0e
    """
    writer = BinaryWriter()
    header = data.header
    base_class = data.base_class

    # =========================================================================
    # Write ObjectInfo Header (0x00-0x0D)
    # Written by FUN_01b08ce0
    # =========================================================================

    # 0x00: NbClassVersionsInfo (1 byte)
    # FUN_01b0d500("NbClassVersionsInfo") via vtable[0x98] -> FUN_01b6f370
    writer.write_uint8(header['nb_class_versions_info'])

    # 0x01-0x04: ObjectName length (4 bytes)
    # FUN_01b48e90 (vtable[0x54]) via FUN_01b49610 -> FUN_01b6fea0
    writer.write_uint32(header['object_name_length'])

    # 0x05-0x08: ObjectID (4 bytes)
    # FUN_01b48e70 (vtable[0x9c]) via FUN_01b49610 -> FUN_01b6fea0
    writer.write_uint32(header['object_id'])

    # 0x09: InstancingMode (1 byte)
    # FUN_01b0d500("InstancingMode") via vtable[0x98] -> FUN_01b6f370
    writer.write_uint8(header['instancing_mode'])

    # 0x0A-0x0D: TypeHash (4 bytes)
    # FUN_01b48fb0 (vtable[0x50]) - [serializer+0x1012]=0 means no string, just hash
    writer.write_uint32(header['type_hash'])

    # =========================================================================
    # Write Section Size Reservations (0x0E-0x19)
    # These are reserved by OpenSection and backpatched by CloseSection
    # =========================================================================

    # 0x0E-0x11: OpenSection("Object")
    # Backpatched at the very end with total object size
    object_section_pos = writer.open_section()

    # 0x12-0x15: OpenSection("Properties")
    # Backpatched after all properties written
    properties_section_pos = writer.open_section()

    # 0x16-0x19: OpenSection(base class)
    # Backpatched after base class property written
    base_class_section_pos = writer.open_section()

    # =========================================================================
    # Write Base Class Field Property (0x1A-0x2A)
    # FUN_01b0a1f0 -> FUN_01b12fa0 -> FUN_01b076f0
    # Format: [hash 4][type_info 8][flags 1][value 4] = 17 bytes
    # NOTE: No size field - shortened format for base class
    # =========================================================================

    # 0x1A-0x1D: Base class hash (4 bytes)
    # FUN_01b0e680 -> FUN_01b49610 -> FUN_01b6fea0
    writer.write_uint32(base_class['hash'])

    # 0x1E-0x25: Base class type_info (8 bytes)
    # FUN_01b0e980 -> FUN_01b49020 -> FUN_01b496d0 (version >= 9)
    writer.write_bytes(base_class['type_info'])

    # 0x26: Base class flags (1 byte)
    # FUN_01b076f0 via vtable[0x98] -> FUN_01b6f370
    writer.write_uint8(base_class['flags'])

    # 0x27-0x2A: Base class value (4 bytes)
    # vtable[0x84] (uint32 serializer) -> FUN_01b6fea0
    writer.write_uint32(base_class['value'])

    # CloseSection(base class) - patches 0x16 with size 17
    writer.close_section()

    # =========================================================================
    # Write Properties (0x2B onwards)
    # Each property: [size 4][hash 4][type_info 8][flags 1][value N]
    # =========================================================================

    for prop in data.properties:
        # OpenSection("Property") via vtable[0x0c] = FUN_01b48890
        # Reserves 4 bytes for size
        prop_section_pos = writer.open_section()

        # Write hash (4 bytes)
        # FUN_01b0e680 -> FUN_01b48fb0 -> FUN_01b49610 -> FUN_01b6fea0
        writer.write_uint32(prop.hash)

        # Write type_info (8 bytes)
        # FUN_01b0e980 -> FUN_01b49020 -> FUN_01b496d0 (version >= 9)
        writer.write_bytes(prop.type_info)

        # Write flags (1 byte)
        # FUN_01b076f0 via vtable[0x98] -> FUN_01b6f370
        writer.write_uint8(prop.flags)

        # Write value based on type
        type_code = type_info_to_type_code(prop.type_info)
        if type_code == TYPE_CODE_BOOL:
            # Bool: vtable[0x58] -> FUN_01b48e80 -> FUN_01b497f0 -> FUN_01b6f370
            writer.write_uint8(1 if prop.value else 0)
        elif type_code == TYPE_CODE_INT8:
            # vtable[0x94] -> FUN_01b49490 (1 byte signed)
            writer.write_int8(prop.value)
        elif type_code == TYPE_CODE_UINT8:
            # vtable[0x90] -> FUN_01b494f0 (1 byte unsigned)
            writer.write_uint8(prop.value)
        elif type_code == TYPE_CODE_INT16:
            # vtable[0x8c] -> FUN_01b49550 (2 bytes signed)
            writer.write_int16(prop.value)
        elif type_code == TYPE_CODE_UINT16:
            # vtable[0x88] -> FUN_01b495b0 (2 bytes unsigned)
            writer.write_uint16(prop.value)
        elif type_code == TYPE_CODE_INT32:
            # vtable[0x80] -> FUN_01b49670 (4 bytes signed)
            writer.write_int32(prop.value)
        elif type_code == TYPE_CODE_UINT32:
            # vtable[0x84] -> FUN_01b49610 (4 bytes unsigned)
            writer.write_uint32(prop.value)
        elif type_code == TYPE_CODE_INT64:
            # 8 bytes signed
            writer.write_int64(prop.value)
        elif type_code == TYPE_CODE_UINT64:
            # Uint64: vtable[0x7c] -> FUN_01b48be0 -> FUN_01b496d0 -> FUN_01b6f4e0
            writer.write_int64(prop.value)
        elif type_code == TYPE_CODE_FLOAT32:
            # vtable[0x74] -> FUN_01b49790 (4 bytes float)
            writer.write_float32(prop.value)
        elif type_code == TYPE_CODE_FLOAT64:
            # vtable[0x78] -> FUN_01b49730 (8 bytes double)
            writer.write_float64(prop.value)
        elif type_code == TYPE_CODE_VEC2:
            # vtable[0x70] -> 2x inner[0x34] (8 bytes)
            writer.write_vec2(prop.value)
        elif type_code == TYPE_CODE_VEC3:
            # vtable[0x6c] -> 3x inner[0x34] (12 bytes)
            writer.write_vec3(prop.value)
        elif type_code == TYPE_CODE_VEC4:
            # vtable[0x5c] -> 4x inner[0x34] (16 bytes)
            writer.write_vec4(prop.value)
        elif type_code == TYPE_CODE_QUAT:
            # vtable[0x68] -> 4x inner[0x34] (16 bytes, quaternion)
            writer.write_quat(prop.value)
        elif type_code == TYPE_CODE_MAT3X3:
            # vtable[0x64] -> 9x inner[0x34] (36 bytes)
            writer.write_mat3x3(prop.value)
        elif type_code == TYPE_CODE_MAT4X4:
            # vtable[0x60] -> 16x inner[0x34] (64 bytes)
            writer.write_mat4x4(prop.value)
        else:
            # Unknown type - try writing as raw bytes (hex string)
            if isinstance(prop.value, str):
                writer.write_bytes(bytes.fromhex(prop.value))
            else:
                raise ValueError(f"Unknown type code: 0x{type_code:02x}")

        # CloseSection("Property") via vtable[0x14] = FUN_01b48920
        # Patches size field with (hash + type_info + flags + value)
        writer.close_section()

    # CloseSection("Properties") - patches 0x12 with properties size
    writer.close_section()

    # =========================================================================
    # Write Trailing Bytes (Dynamic Properties section)
    # FUN_01b0d0c0 finalization:
    #   OpenSection("Dynamic Properties") - reserves 4 bytes
    #   (no dynamic properties)
    #   CloseSection("Dynamic Properties") - patches size to 0
    # =========================================================================

    # Write Dynamic Properties section size (always 0 - no dynamic properties support)
    writer.write_uint32(0)

    # CloseSection("Object") - patches 0x0e with object size
    writer.close_section()

    return writer.get_bytes()


def serialize_section3_from_dict(json_data: dict) -> bytes:
    """Convert JSON dict to Section3Data and serialize to binary."""

    # Convert header
    header = json_data['header'].copy()

    # Parse hex strings back to integers where needed
    if isinstance(header.get('nb_class_versions_info'), str):
        header['nb_class_versions_info'] = int(header['nb_class_versions_info'], 16)
    if isinstance(header.get('object_name_length'), str):
        header['object_name_length'] = int(header['object_name_length'], 16)
    if isinstance(header.get('object_id'), str):
        header['object_id'] = int(header['object_id'], 16)
    if isinstance(header.get('instancing_mode'), str):
        header['instancing_mode'] = int(header['instancing_mode'], 16)
    if isinstance(header.get('type_hash'), str):
        header['type_hash'] = int(header['type_hash'], 16)
    # Section sizes are computed during serialization, not needed from JSON

    # Convert base_class
    base_class = json_data['base_class'].copy()
    if isinstance(base_class.get('hash'), str):
        base_class['hash'] = int(base_class['hash'], 16)
    if isinstance(base_class.get('type_info'), str):
        base_class['type_info'] = bytes.fromhex(base_class['type_info'])
    if isinstance(base_class.get('flags'), str):
        base_class['flags'] = int(base_class['flags'], 16)
    if isinstance(base_class.get('value'), str):
        base_class['value'] = int(base_class['value'], 16)

    # Convert properties
    properties = []
    for p in json_data['properties']:
        prop_hash = int(p['hash'], 16) if isinstance(p['hash'], str) else p['hash']
        type_info = bytes.fromhex(p['type_info']) if isinstance(p['type_info'], str) else p['type_info']
        flags = int(p['flags'], 16) if isinstance(p['flags'], str) else p['flags']

        # Derive type from type_info
        type_code = type_info_to_type_code(type_info)
        prop_type = type_code_to_string(type_code)

        properties.append(Property(
            file_offset=0,  # Not used during serialization
            size=0,  # Computed during serialization
            hash=prop_hash,
            type_info=type_info,
            flags=flags,
            name=p.get('_label', p.get('name', '')),
            prop_type=prop_type,
            value=p['value']
        ))

    data = Section3Data(
        file_size=0,  # Not used during serialization
        header=header,
        base_class=base_class,
        properties=properties,
        trailing_size=0  # Always 0 - no dynamic properties support
    )

    return serialize_section3(data)


def serialize_section3_from_file(json_filepath: str, output_filepath: str) -> int:
    """Load JSON and serialize back to binary."""
    with open(json_filepath, 'r') as f:
        json_data = json.load(f)

    binary_data = serialize_section3_from_dict(json_data)

    with open(output_filepath, 'wb') as f:
        f.write(binary_data)

    return len(binary_data)


# =============================================================================
# JSON Output
# =============================================================================

def to_json(data: Section3Data) -> dict:
    """Convert Section3Data to JSON-serializable dict."""
    return {
        "header": {
            "nb_class_versions_info": f"0x{data.header['nb_class_versions_info']:02x}",
            "object_name_length": f"0x{data.header['object_name_length']:08x}",
            "object_id": f"0x{data.header['object_id']:08x}",
            "instancing_mode": f"0x{data.header['instancing_mode']:02x}",
            "type_hash": f"0x{data.header['type_hash']:08x}",
            "type_name": data.header['type_name'],
        },
        "base_class": {
            "hash": f"0x{data.base_class['hash']:08x}",
            "type_info": data.base_class['type_info'].hex(),
            "flags": f"0x{data.base_class['flags']:02x}",
            "value": f"0x{data.base_class['value']:08x}",
        },
        "properties": [
            {
                "_label": p.name,
                "hash": f"0x{p.hash:08x}",
                "type_info": p.type_info.hex(),
                "flags": f"0x{p.flags:02x}",
                "value": p.value,
            }
            for p in data.properties
        ],
    }


# =============================================================================
# Main
# =============================================================================

def main():
    input_file = sys.argv[1] if len(sys.argv) > 1 else 'game_uncompressed_3.bin'
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'section3_output.json'

    print("=" * 60)
    print("Section 3 Parser - Dynamic Implementation")
    print("Based on WinDbg TTD Trace (docs/SECTION3_SERIALIZATION.md)")
    print("=" * 60)
    print(f"Input: {input_file}")

    with open(input_file, 'rb') as f:
        f.seek(0, 2)
        size = f.tell()
    print(f"Size: {size} bytes (0x{size:02x})")
    print()

    # Parse the binary
    data = parse_section3(input_file)

    # Print header info
    print("Header (0x00-0x0D - FUN_01b08ce0):")
    print(f"  NbClassVersionsInfo: 0x{data.header['nb_class_versions_info']:02x}")
    print(f"  ObjectName length:   0x{data.header['object_name_length']:08x}")
    print(f"  ObjectID:            0x{data.header['object_id']:08x}")
    print(f"  InstancingMode:      0x{data.header['instancing_mode']:02x}")
    print(f"  TypeHash:            0x{data.header['type_hash']:08x} ({data.header['type_name']})")
    print()

    print("Section Sizes (0x0E-0x19 - OpenSection/CloseSection):")
    print(f"  Object section:      0x{data.header['object_section_size']:08x} ({data.header['object_section_size']} bytes)")
    print(f"  Properties section:  0x{data.header['properties_section_size']:08x} ({data.header['properties_section_size']} bytes)")
    print(f"  Base class section:  0x{data.header['base_class_section_size']:08x} ({data.header['base_class_section_size']} bytes)")
    print()

    print("Base Class Field (0x1A-0x2A - FUN_01b0a1f0):")
    print(f"  Hash:      0x{data.base_class['hash']:08x}")
    print(f"  Type info: {data.base_class['type_info'].hex()}")
    print(f"  Flags:     0x{data.base_class['flags']:02x}")
    print(f"  Value:     0x{data.base_class['value']:08x}")
    print()

    print(f"Properties ({len(data.properties)}):")
    for prop in data.properties:
        if prop.prop_type == "bool":
            print(f"  [{prop.prop_type:6}] {prop.name}: {prop.value} (hash=0x{prop.hash:08x}, offset=0x{prop.file_offset:02x}, size={prop.size})")
        else:
            print(f"  [{prop.prop_type:6}] {prop.name}: {prop.value} (0x{prop.value & 0xFFFFFFFFFFFFFFFF:016x}) (hash=0x{prop.hash:08x}, offset=0x{prop.file_offset:02x}, size={prop.size})")
    print()

    print(f"Trailing (Dynamic Properties section size): 0x{data.trailing_size:08x}")
    print()

    # Write JSON output
    result = to_json(data)
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)
    print(f"JSON output written to: {output_file}")

    # Roundtrip test: Section3Data -> Binary
    roundtrip_file = output_file.replace('.json', '_roundtrip.bin')
    roundtrip_data = serialize_section3(data)
    with open(roundtrip_file, 'wb') as f:
        f.write(roundtrip_data)
    print(f"Roundtrip binary written to: {roundtrip_file}")

    # Verify roundtrip matches original
    with open(input_file, 'rb') as f:
        original_data = f.read()

    if original_data == roundtrip_data:
        print("ROUNDTRIP VERIFIED: Output matches original byte-for-byte")
    else:
        print("ROUNDTRIP FAILED: Output differs from original")
        print(f"  Original size: {len(original_data)}")
        print(f"  Roundtrip size: {len(roundtrip_data)}")
        # Find first difference
        for i in range(min(len(original_data), len(roundtrip_data))):
            if original_data[i] != roundtrip_data[i]:
                print(f"  First difference at offset 0x{i:04x}: original=0x{original_data[i]:02x}, roundtrip=0x{roundtrip_data[i]:02x}")
                break
        # Show hex comparison around the difference
        print()
        print("Hex comparison (original vs roundtrip):")
        for i in range(0, min(len(original_data), len(roundtrip_data), 176), 16):
            orig_line = ' '.join(f'{b:02x}' for b in original_data[i:i+16])
            rt_line = ' '.join(f'{b:02x}' for b in roundtrip_data[i:i+16]) if i < len(roundtrip_data) else ''
            match = "==" if original_data[i:i+16] == roundtrip_data[i:i+16] else "!="
            print(f"  {i:08x}: {orig_line:<48} {match} {rt_line}")

    # Print hex dump for reference
    print()
    print("Raw Hex Dump:")
    with open(input_file, 'rb') as f:
        raw = f.read()
    for i in range(0, len(raw), 16):
        hex_part = ' '.join(f'{b:02x}' for b in raw[i:i+16])
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in raw[i:i+16])
        print(f"  {i:08x}: {hex_part:<48} {ascii_part}")


if __name__ == '__main__':
    main()
