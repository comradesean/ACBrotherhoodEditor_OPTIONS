#!/usr/bin/env python3
"""
Section 4 Binary Parser - TRACED CODE ONLY

Based on decompiled functions from both Section 3 and Section 4 WinDbg TTD traces.
Section 3 and Section 4 use the SAME serialization system but different modes:
  - Section 3 (OPTIONS): Mode 0 (text-like) - includes property flags byte
  - Section 4 (MULTI PROFILE): Mode 3 (binary) - skips property flags

=== FILE STRUCTURE OVERVIEW ===

Section 4 files have a fixed structure:
  [22 bytes] File header (ObjectInfo + type hash + size fields)
  [N bytes]  Property data (size from size_field_2)
  [4 bytes]  Dynamic properties section size (always 0 in test files)

=== BINARY FORMAT DETAILS ===

File Header (22 bytes):
  Offset  Size  Field
  0x00    1     NbClassVersionsInfo - class version count
  0x01    4     ObjectName - null string hash
  0x05    4     ObjectID
  0x09    1     InstancingMode
  0x0A    4     Type hash (identifies root object type)
  0x0E    4     Size field 1 (content + size fields = size_field_2 + 8)
  0x12    4     Size field 2 (content only, used for property parsing)

Property Format (Mode 3 Binary):
  [4 bytes] section_size - bytes in this property excluding this field
  [4 bytes] property_id - hash identifying the property
  [8 bytes] type_descriptor - type_hash (4) + type_info (4)
  [N bytes] value data - format depends on type_code

Type Descriptor (8 bytes):
  [4 bytes] type_hash - identifies the type class
  [4 bytes] type_info - bit field:
    - bits 16-21: primary type code (& 0x3F)
    - bits 23-28: element type for containers (& 0x3F)

=== SERIALIZER MODE VTABLE (PTR_FUN_02555c60 / 0x02c35c60 WinDbg) ===
Offset | Ghidra Addr | Function      | Purpose
-------|-------------|---------------|----------------------------------------
0x00   | 02555c60    | FUN_01b49b10  | Destructor
0x08   | 02555c68    | LAB_01b48770  | StartElement (NO-OP in binary WRITE)
0x0c   | 02555c6c    | FUN_01b48890  | OpenSection - reads 4-byte section size
0x10   | 02555c70    | LAB_01b487a0  | EndElement (NO-OP in binary WRITE)
0x14   | 02555c74    | FUN_01b48920  | CloseSection - backpatches size
0x50   | 02555cb0    | FUN_01b48fb0  | TypeInfo serializer (4-byte hash)
0x54   | 02555cb4    | FUN_01b48e90  | String serializer (4-byte len + data)
0x58   | 02555cb8    | FUN_01b48e80  | Bool (1 byte) -> FUN_01b49430
0x70   | 02555cd0    | FUN_01b48c10  | vec2 (8 bytes)
0x74   | 02555cd4    | FUN_01b48c00  | float32 (4 bytes) -> FUN_01b49790
0x78   | 02555cd8    | FUN_01b48bf0  | float64 (8 bytes) -> FUN_01b49730
0x7c   | 02555cdc    | FUN_01b48be0  | uint64 (8 bytes) -> FUN_01b496d0
0x80   | 02555ce0    | FUN_01b48bd0  | int32 (4 bytes) -> FUN_01b49670
0x84   | 02555ce4    | FUN_01b48bc0  | uint32 (4 bytes) -> FUN_01b49610
0x88   | 02555ce8    | FUN_01b48bb0  | uint16 (2 bytes) -> FUN_01b495b0
0x8c   | 02555cec    | FUN_01b48ba0  | int16 (2 bytes) -> FUN_01b49550
0x90   | 02555cf0    | FUN_01b48b90  | uint8 (1 byte) -> FUN_01b494f0
0x94   | 02555cf4    | FUN_01b48b80  | int8 (1 byte) -> FUN_01b49490
0x98   | 02555cf8    | FUN_01b48b70  | WriteByte -> FUN_01b49430
0x9c   | 02555cfc    | FUN_01b48e70  | uint32 (ObjectID) -> FUN_01b49610

=== STREAM INNER VTABLE (PTR_FUN_02556168 / 0x02c36168 WinDbg) ===
Offset | Index | Purpose                | Read Function   | Write Function
-------|-------|------------------------|-----------------|----------------
0x0c   | [3]   | IsAtEnd               | LAB_01b6f010    | LAB_01b6f010
0x18   | [6]   | 8-byte read/write      | FUN_01b6f490    | FUN_01b6f4e0
0x1c   | [7]   | 4-byte read/write      | FUN_01b6f440    | FUN_01b6f4d0
0x20   | [8]   | 2-byte read            | FUN_01b6f400    | -
0x24   | [9]   | 1-byte read            | FUN_01b6f150    | -
0x28   | [10]  | N-byte read            | FUN_01b6f030    | -
0x34   | [13]  | 4-byte write           | -               | FUN_01b6fea0
0x3c   | [15]  | 1-byte write           | -               | FUN_01b6f370
0x40   | [16]  | N-byte write           | -               | FUN_01b6f3b0

=== KEY FUNCTIONS ===
- FUN_01b48890: BeginSection (vtable+0x0C) - reads EXACTLY 4 bytes (section size)
  * Binary mode: reads 4-byte section size via stream vtable+0x1c
  * Maintains depth counter at serializer+0x1010 (uint16)
  * Stores section size at [serializer + depth*8 + 0x10]

- FUN_01b077d0: Property header reader (CRITICAL - MODE DEPENDENT)
  * MODE 3 (binary): reads EXACTLY 12 BYTES total:
    - 4 bytes: Property ID via vtable+0x84
    - 8 bytes: Type Descriptor via FUN_01b0e980
    - PropertyHeaderFlag (FUN_01b076f0) is SKIPPED!
  * MODE 0 (text): reads property name, ID, type desc, AND flags

- FUN_01b0d140: Property header WRITER (Section 3 traced)
  * MODE 0: Writes [size 4][hash 4][type_info 8][flags 1][value N]
  * MODE 1/2/3: Returns early, skips writing header!

- FUN_01b0e980: TypeDescriptor reader (8 bytes via vtable+0x4c)
  * Reads 8 bytes: type_hash (4B) + type_info (4B)
  * Type code extraction: (type_info >> 16) & 0x3F

- FUN_01b076f0: PropertyHeaderFlag reader/writer
  * Version >= 11: 1 byte via vtable+0x98 (always 0x0b in Section 3)
  * SKIPPED in modes 1, 2, 3 (binary)

- FUN_01b0c2e0: Type dispatcher (31-way switch)
- FUN_01b09760: uint64 property serializer -> FUN_01b124e0
- FUN_01b07b90: MAP count reader (4 bytes via vtable+0x84)
- FUN_01b0bcf0: MAP/MAP_ALT handler

BINARY MODE: ctx+0x58 == 3
- FUN_01b077d0 reads EXACTLY 12 bytes for property header (ID + TypeDesc)
- FUN_01b076f0 (property flags) is SKIPPED in binary mode!
- BeginSection reads EXACTLY 4 bytes (section_size), no extra bytes
"""

import struct
import sys
import json
from dataclasses import dataclass
from typing import Any, Optional, Dict
from enum import IntEnum


# =============================================================================
# TYPE DEFINITIONS
# =============================================================================

class PropertyType(IntEnum):
    """
    Type codes from FUN_01b0c2e0 switch table (31-way dispatcher).

    Each type code corresponds to a specific vtable handler or function call
    in the serialization system. The type code is extracted from type_info
    using: (type_info >> 16) & 0x3F

    NOTE: Type sizes may vary between files/modes. The section_size field
    in each property determines the ACTUAL byte count. This enum provides
    default sizes, but section_size takes precedence.

    Verified via binary analysis of actual game save files.
    """
    # 1-byte types (TRACED via vtable+0x58, 0x90, 0x94)
    BOOL = 0         # Bool via vtable+0x58
    BOOL_ALT = 1     # Bool variant
    UINT8 = 2        # Unsigned byte via vtable+0x90
    INT8 = 3         # Signed byte via vtable+0x94

    # 2-byte types (TRACED via vtable+0x88, 0x8c)
    UINT16 = 4       # Unsigned 16-bit via vtable+0x88
    INT16 = 5        # Signed 16-bit via vtable+0x8c

    # 4-byte types (TRACED via vtable+0x74, 0x80, 0x84)
    INT32_V2 = 6     # Signed 32-bit via vtable+0x74 (binary data confirms integer values)
    UINT32 = 7       # Unsigned 32-bit via vtable+0x84
    INT32 = 8        # Signed 32-bit via vtable+0x80

    # 8-byte types (TRACED via vtable+0x78, 0x7c - binary data confirms 8 bytes)
    UINT64 = 9       # Unsigned 64-bit via vtable+0x7c (confirmed: nested properties have 8-byte values)
    FLOAT_ALT = 10   # Float variant - 4 bytes IEEE 754 (confirmed: root property has 4-byte value = 1.0f)
    FLOAT64 = 11     # Double via vtable+0x78

    # Vector types (multi-component floats)
    VECTOR2 = 12     # 8 bytes (2x float32) via vtable+0x70
    VECTOR3 = 13     # 12 bytes (3x float32)
    VECTOR4 = 14     # 16 bytes (4x float32)

    # Matrix types
    MATRIX3X3 = 15   # 36 bytes (9x float32)
    MATRIX4X4 = 16   # 64 bytes (16x float32)

    # String/reference types
    STRING = 17      # 4-byte hash in binary mode via vtable+0x54
    OBJECTREF = 18   # Object reference
    OBJECTREF_EMB = 19  # Embedded object reference

    # Enum types
    ENUM = 20        # Enumeration
    STRUCT = 21      # Structure
    CLASS = 22       # Class object (nested serialization)

    # Container types (TRACED via FUN_01b0bcf0)
    ARRAY = 23       # Array container
    MAP = 24         # Map container (case 0x18)
    ENUM_ALT = 25    # Enum variant: 4-byte value + 4-byte name hash
    GUID = 26        # GUID (16 bytes typically)

    # Variable-length types
    VARSTRING = 27   # Variable-length UTF-16 string (FUN_01b48e90)
    POINTER = 28     # Pointer reference
    MAP_ALT = 29     # Map variant (case 0x1D)


# Fixed-size type mapping: type_code -> byte count (excluding 0x0B marker)
# Types NOT in this dict are variable-length and handled separately
TYPE_SIZES: Dict[PropertyType, int] = {
    # 1-byte types
    PropertyType.BOOL: 1,
    PropertyType.BOOL_ALT: 1,
    PropertyType.UINT8: 1,
    PropertyType.INT8: 1,

    # 2-byte types
    PropertyType.UINT16: 2,
    PropertyType.INT16: 2,

    # 4-byte types
    PropertyType.INT32_V2: 4,
    PropertyType.UINT32: 4,
    PropertyType.INT32: 4,
    PropertyType.STRING: 4,  # Hash only in binary mode

    # 8-byte types
    PropertyType.UINT64: 8,
    PropertyType.FLOAT64: 8,

    # 4-byte float (type 10 confirmed as float via binary data: 0x3f800000 = 1.0f)
    PropertyType.FLOAT_ALT: 4,
    PropertyType.VECTOR2: 8,
    PropertyType.ENUM_ALT: 8,  # Type 25: value (4) + name hash (4)

    # Multi-byte fixed types
    PropertyType.VECTOR3: 12,
    PropertyType.VECTOR4: 16,
    PropertyType.MATRIX3X3: 36,
    PropertyType.MATRIX4X4: 64,
    # NOTE: VARSTRING (27) is NOT fixed - it's variable UTF-16 string
}

# Known type hashes -> class names (for display only, not used in serialization)
# These are traced from SECTION4_SERIALIZATION.md and Ghidra analysis
KNOWN_TYPE_HASHES: Dict[int, str] = {
    0xB4B55039: "AssassinMultiProfileData",
    0xC292F31F: "MultiplayerUserData",
    0x94DAAEE6: "AbilityProfileData",
    0xF95FCFA8: "OutfitData",
}


def get_type_name(type_hash: int) -> str:
    """Get human-readable class name for a type hash, or hex if unknown."""
    if type_hash == 0:
        return None
    return KNOWN_TYPE_HASHES.get(type_hash, f"0x{type_hash:08X}")


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class DynamicProperty:
    """
    Represents a single property parsed from the binary format.

    Binary Layout (Mode 3):
      [4 bytes] section_size - total bytes following this field
      [4 bytes] property_id - hash identifying the property name
      [8 bytes] type_descriptor - type_hash (4) + type_info (4)
      [N bytes] value - format depends on type_code

    The type_descriptor encodes:
      - type_hash: identifies the type class (first 4 bytes)
      - type_info: bit field with type_code and element_type (second 4 bytes)
        - bits 16-21: primary type code
        - bits 23-28: element type for containers

    Attributes:
        offset: Byte offset where this property starts in the file
        section_size: Number of bytes in this property (excluding section_size field)
        property_id: Hash identifying the property name
        type_descriptor: Raw 8-byte type descriptor
        type_code: Extracted type code from (type_info >> 16) & 0x3F
        value: Parsed value (type depends on type_code)
        raw_bytes: Original raw bytes for this entire property (for debugging)
    """
    offset: int
    section_size: int
    property_id: int
    type_descriptor: bytes
    type_code: int
    value: Any
    raw_bytes: bytes


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_element_size(element_type: int) -> int:
    """
    Get the byte size for a given element type code.

    Used for MAP/MAP_ALT containers to determine entry sizes based on
    the element_type extracted from type_info bits 23-28.

    Args:
        element_type: Type code from (type_info >> 23) & 0x3F

    Returns:
        Byte size for the element type, or 0 if unknown/variable-length
    """
    try:
        return TYPE_SIZES.get(PropertyType(element_type), 0)
    except ValueError:
        return 0


def parse_hex_string(value: str) -> int:
    """
    Parse a hex string like '0x1234ABCD' to an integer.

    Args:
        value: Hex string with '0x' prefix

    Returns:
        Integer value
    """
    return int(value, 16)


def format_hex_32(value: int) -> str:
    """
    Format a 32-bit integer as a hex string.

    Args:
        value: Integer value

    Returns:
        Hex string like '0x1234ABCD'
    """
    return f'0x{value:08X}'


# =============================================================================
# PARSER CLASS
# =============================================================================

class Section4Parser:
    """
    Parser for Section 4 binary format.

    This parser reads the binary data sequentially, following the exact
    read sequence traced from the game's decompiled code. All parsing
    logic is derived from FUN_01b077d0 (property header reader) and
    FUN_01b0c2e0 (type dispatcher).

    Binary Mode (ctx+0x58 == 3):
      - Property header is exactly 12 bytes (ID + TypeDesc, NO flags)
      - BeginSection reads exactly 4 bytes (section_size)
      - PropertyHeaderFlag (0x0B) is written before each value, NOT in header

    Attributes:
        data: Raw binary data being parsed
        pos: Current read position
        size: Total size of the data
    """

    def __init__(self, data: bytes):
        """
        Initialize parser with binary data.

        Args:
            data: Raw binary data to parse
        """
        self.data = data
        self.pos = 0
        self.size = len(data)

    # -------------------------------------------------------------------------
    # LOW-LEVEL READ METHODS
    # -------------------------------------------------------------------------

    def read_bytes(self, n: int) -> bytes:
        """
        Read N raw bytes from current position and advance.

        Args:
            n: Number of bytes to read

        Returns:
            Raw bytes
        """
        result = self.data[self.pos:self.pos + n]
        self.pos += n
        return result

    def read_uint8(self) -> int:
        """
        Read unsigned 8-bit integer (1 byte).

        TRACED via vtable+0x90 -> FUN_01b494f0

        Returns:
            Unsigned byte value (0-255)
        """
        return self.read_bytes(1)[0]

    def read_int32(self) -> int:
        """
        Read signed 32-bit integer (4 bytes, little-endian).

        TRACED via vtable+0x80 -> FUN_01b49670

        Returns:
            Signed 32-bit integer
        """
        return struct.unpack('<i', self.read_bytes(4))[0]

    def read_uint32(self) -> int:
        """
        Read unsigned 32-bit integer (4 bytes, little-endian).

        TRACED via vtable+0x84 -> FUN_01b49610

        Returns:
            Unsigned 32-bit integer
        """
        return struct.unpack('<I', self.read_bytes(4))[0]

    def is_at_end(self) -> bool:
        """
        Check if parser has reached end of data.

        TRACED via inner_vtable+0x0c -> LAB_01b6f010

        Returns:
            True if at or past end of data
        """
        return self.pos >= self.size

    # -------------------------------------------------------------------------
    # TYPE DESCRIPTOR PARSING
    # -------------------------------------------------------------------------

    def parse_type_descriptor(self) -> tuple:
        """
        Parse 8-byte type descriptor.

        TRACED: FUN_01b0e980 reads 8 bytes via vtable+0x4c

        Section 3 WinDbg Trace (E68A1B:2D0):
          - Version check: [ECX + 0x24] >= 9 -> current path (direct 8-byte)
          - Version < 9: legacy path with FUN_01b0e3d0 conversion
          - vtable[0x08]("Type") -> StartElement (NO-OP in binary)
          - vtable[0x4c](format, &local_c) -> FUN_01b49020 -> FUN_01b496d0
          - vtable[0x10]("Type") -> EndElement (NO-OP in binary)

        Binary Layout (8 bytes):
          [4 bytes] type_hash - identifies the type class
          [4 bytes] type_info - bit field:
            - bits 16-21: primary type code (& 0x3F)
            - bits 23-28: element/value type for containers (& 0x3F)

        Type code extraction (via FUN_01b0e3d0 bit masks):
          - (type_info >> 16) & 0x3F = primary type code (bits 16-21)
          - (type_info >> 23) & 0x3F = element/value type for containers

        Returns:
            Tuple of (raw_bytes, type_code, type_hash, element_type)
        """
        raw = self.read_bytes(8)
        type_hash = struct.unpack('<I', raw[0:4])[0]
        type_info = struct.unpack('<I', raw[4:8])[0]
        type_code = (type_info >> 16) & 0x3F
        element_type = (type_info >> 23) & 0x3F
        return raw, type_code, type_hash, element_type

    # -------------------------------------------------------------------------
    # PRIMITIVE VALUE PARSING
    # -------------------------------------------------------------------------

    def read_primitive_value(self, type_code: int) -> Any:
        """
        Read a primitive value based on type code.

        This is the SINGLE unified path for all primitive types. Each type
        maps to a specific vtable handler in the game's serialization system.

        TRACED handlers:
          - BOOL/BOOL_ALT: vtable+0x58 -> FUN_01b49430 (1 byte)
          - UINT8: vtable+0x90 -> FUN_01b494f0 (1 byte)
          - INT8: vtable+0x94 -> FUN_01b49490 (1 byte)
          - UINT16: vtable+0x88 -> FUN_01b495b0 (2 bytes)
          - INT16: vtable+0x8c -> FUN_01b49550 (2 bytes)
          - FLOAT32: vtable+0x74 -> FUN_01b49790 (4 bytes)
          - UINT32: vtable+0x84 -> FUN_01b49610 (4 bytes)
          - INT32: vtable+0x80 -> FUN_01b49670 (4 bytes)
          - STRING: vtable+0x54 -> 4-byte hash in binary mode
          - UINT64 (type 9): 8 bytes via vtable+0x7c (confirmed in nested properties)
          - FLOAT_ALT (type 10): 4 bytes IEEE 754 (confirmed: 0x3f800000 = 1.0f)
          - FLOAT64: vtable+0x78 -> FUN_01b49730 (8 bytes)
          - ENUM_ALT: 4-byte value + 4-byte name hash

        Args:
            type_code: Type code from PropertyType enum

        Returns:
            Parsed value (type depends on type_code)

        Raises:
            ValueError: If type_code is not a known primitive type
        """
        # 1-byte types
        if type_code == PropertyType.BOOL or type_code == PropertyType.BOOL_ALT:
            return bool(self.read_uint8())
        elif type_code == PropertyType.UINT8:
            return self.read_uint8()
        elif type_code == PropertyType.INT8:
            return struct.unpack('<b', self.read_bytes(1))[0]

        # 2-byte types
        elif type_code == PropertyType.UINT16:
            return struct.unpack('<H', self.read_bytes(2))[0]
        elif type_code == PropertyType.INT16:
            return struct.unpack('<h', self.read_bytes(2))[0]

        # 4-byte types
        elif type_code == PropertyType.INT32_V2:
            return struct.unpack('<i', self.read_bytes(4))[0]
        elif type_code == PropertyType.UINT32:
            return struct.unpack('<I', self.read_bytes(4))[0]
        elif type_code == PropertyType.INT32:
            return struct.unpack('<i', self.read_bytes(4))[0]
        elif type_code == PropertyType.STRING:
            # In binary mode, STRING is just a 4-byte hash
            return struct.unpack('<I', self.read_bytes(4))[0]

        # 8-byte types
        elif type_code == PropertyType.UINT64:
            return struct.unpack('<Q', self.read_bytes(8))[0]
        elif type_code == PropertyType.FLOAT64:
            return struct.unpack('<d', self.read_bytes(8))[0]

        # 4-byte float (type 10 - confirmed via binary: 0x3f800000 = 1.0f)
        elif type_code == PropertyType.FLOAT_ALT:
            return struct.unpack('<f', self.read_bytes(4))[0]

        # Enum variant type 25: 4-byte value + 4-byte name hash
        elif type_code == PropertyType.ENUM_ALT:
            value = struct.unpack('<I', self.read_bytes(4))[0]
            name_hash = struct.unpack('<I', self.read_bytes(4))[0]
            return {'value': value, 'name_hash': format_hex_32(name_hash)}

        else:
            raise ValueError(f"Unknown primitive type code: {type_code}")

    # -------------------------------------------------------------------------
    # VALUE PARSING (TYPE DISPATCHER)
    # -------------------------------------------------------------------------

    def parse_value(self, type_code: int, bytes_remaining: int,
                    element_type: int = 0, type_hash: int = 0) -> tuple:
        """
        Parse a property value based on type code.

        TRACED: FUN_01b0c2e0 is a 31-way switch dispatcher that routes
        each type code to its specific handler.

        Binary Format for Fixed Types:
          [1 byte]  0x0B marker (PropertyHeaderFlag from FUN_01b0d530)
          [N bytes] value data (size from TYPE_SIZES)

        Binary Format for MAP/MAP_ALT (types 24, 29):
          [1 byte]  0x0B marker
          [1 byte]  content_code (usually 0x01, purpose unknown)
          [4 bytes] count (signed 32-bit)
          [N bytes] entries (format depends on element_type)

        Binary Format for VARSTRING (type 27):
          [1 byte]  0x0B marker
          [4 bytes] char_count
          [N bytes] UTF-16LE string data (char_count * 2)
          [2 bytes] UTF-16 null terminator (only if char_count > 0)

        Args:
            type_code: Primary type from (type_info >> 16) & 0x3F
            bytes_remaining: Section size minus header bytes
            element_type: For containers, from (type_info >> 23) & 0x3F
            type_hash: Type hash for CLASS entries

        Returns:
            Tuple of (parsed_value, bytes_consumed)
        """
        # TRACED: FUN_01af9930 -> FUN_01b2c6d0 -> FUN_01b0d530
        # All property values have: [0x0B marker] + [value bytes]
        if type_code in TYPE_SIZES:
            expected_size = 1 + TYPE_SIZES[PropertyType(type_code)]

            # Check if section provides expected bytes
            if bytes_remaining < expected_size:
                # Section_size doesn't match expected type - read raw bytes
                raw_value = self.read_bytes(bytes_remaining)
                print(f"    Type {type_code}: Section has {bytes_remaining} bytes, "
                      f"expected {expected_size}, storing raw")
                return {'_raw_type': type_code, '_raw_bytes': raw_value}, bytes_remaining

            # Read marker byte (0x0B) - TRACED via FUN_01b0d530
            self.read_uint8()  # marker, always 0x0B

            # Use unified primitive reader
            value = self.read_primitive_value(type_code)

            return value, expected_size

        # Type 27 - Variable-length UTF-16 string
        elif type_code == PropertyType.VARSTRING:
            return self._parse_varstring()

        # Case 0x18/0x1D - MAP/MAP_ALT containers
        elif type_code == PropertyType.MAP or type_code == PropertyType.MAP_ALT:
            return self._parse_map(bytes_remaining, element_type)

        # Case 0x17 - ARRAY (special handling in mode 3)
        elif type_code == PropertyType.ARRAY:
            # TRACED: In mode 3, count comes from outer context, not read here
            print(f"    ARRAY: In mode 3, count not read by FUN_01b07be0 "
                  f"(passed from caller)")
            return f'<ARRAY: count from caller, elements follow>', 0

        # Unknown types - store raw bytes for perfect roundtrip
        else:
            if bytes_remaining > 0:
                raw_value = self.read_bytes(bytes_remaining)
                print(f"    Type {type_code}: Unknown type, "
                      f"storing {bytes_remaining} raw bytes")
                return {'_raw_type': type_code, '_raw_bytes': raw_value}, bytes_remaining
            else:
                print(f"    Type {type_code}: Unknown type with no value bytes")
                return {'_raw_type': type_code, '_raw_bytes': b''}, 0

    def _parse_varstring(self) -> tuple:
        """
        Parse a variable-length UTF-16 string (type 27).

        TRACED: FUN_01b48e90 handles string serialization

        Binary Format:
          [1 byte]  0x0B marker
          [4 bytes] char_count (number of UTF-16 characters)
          [N bytes] UTF-16LE string data (char_count * 2 bytes)
          [2 bytes] UTF-16 null terminator (only if char_count > 0)

        Empty strings (char_count=0) have no string data and no null terminator.

        Returns:
            Tuple of (string_value, bytes_consumed)
        """
        self.read_uint8()  # 0x0B marker
        char_count = self.read_uint32()

        if char_count > 0:
            string_bytes = self.read_bytes(char_count * 2)
            string_value = string_bytes.decode('utf-16-le')
            self.read_bytes(2)  # UTF-16 null terminator
            bytes_consumed = 1 + 4 + (char_count * 2) + 2
        else:
            string_value = ''
            bytes_consumed = 1 + 4

        return string_value, bytes_consumed

    def _parse_map(self, bytes_remaining: int, element_type: int) -> tuple:
        """
        Parse a MAP or MAP_ALT container (types 24, 29).

        TRACED: FUN_01b0bcf0 handles MAP/MAP_ALT serialization
                FUN_01b07b90 reads count via vtable+0x84 (4 bytes)

        Binary Format:
          [1 byte]  0x0B marker
          [1 byte]  content_code (usually 0x01, purpose unknown)
          [4 bytes] count (signed 32-bit, number of entries)
          [N bytes] entries (format depends on element_type)

        Entry format depends on element_type:
          - Fixed types (UINT32, INT8, etc.): raw values
          - CLASS: nested ObjectInfo + properties structure

        Args:
            bytes_remaining: Bytes available for this value
            element_type: Type code for entries from (type_info >> 23) & 0x3F

        Returns:
            Tuple of (map_dict, bytes_consumed)
        """
        # Read header
        marker = self.read_uint8()  # 0x0B (PropertyHeaderFlag)
        content_code = self.read_uint8()  # Usually 0x01, purpose unknown (traced via FUN_01b147e0)
        count = self.read_int32()
        bytes_consumed = 2 + 4  # marker + content_code + count

        elem_size = get_element_size(element_type)
        entry_data_size = bytes_remaining - bytes_consumed
        entries = []

        if count > 0 and elem_size > 0:
            # Fixed-size elements
            entries = self._parse_fixed_map_entries(count, elem_size)
            bytes_consumed += count * elem_size

        elif count > 0 and element_type == PropertyType.CLASS:
            # Nested CLASS entries
            entries = self._parse_class_map_entries(count)
            bytes_consumed += entry_data_size

        elif count > 0:
            # Unknown element type - read raw
            raw_entries = self.read_bytes(entry_data_size)
            entries = f'<{count} raw entries: {raw_entries[:32].hex()}...>'
            bytes_consumed += entry_data_size

        value = {
            'marker': f'0x{marker:02X}',
            'content_code': f'0x{content_code:02X}',
            'count': f'0x{count:08X}',
            'entries': entries,
        }

        return value, bytes_consumed

    def _parse_fixed_map_entries(self, count: int, elem_size: int) -> list:
        """
        Parse fixed-size MAP entries.

        Args:
            count: Number of entries
            elem_size: Size of each entry in bytes

        Returns:
            List of parsed entries
        """
        entries = []
        for _ in range(count):
            if elem_size == 1:
                entries.append(self.read_uint8())
            elif elem_size == 4:
                val = self.read_uint32()
                entries.append(format_hex_32(val))
            elif elem_size == 8:
                val = struct.unpack('<Q', self.read_bytes(8))[0]
                entries.append(f'0x{val:016X}')
            else:
                entries.append(self.read_bytes(elem_size).hex())
        return entries

    def _parse_class_map_entries(self, count: int) -> list:
        """
        Parse MAP entries containing CLASS objects.

        TRACED structure (via FUN_01af6b80 ObjectInfo):
          ObjectInfo (10 bytes):
            [1 byte]  NbClassVersionsInfo - class version count
            [4 bytes] ObjectName - null string hash
            [4 bytes] ObjectID
            [1 byte]  InstancingMode
          Entry metadata:
            [4 bytes] type_hash
            [4 bytes] content_size (bytes following this field)
            [4 bytes] prop_data_size
            [prop_data_size bytes] properties
            [padding] to fill content_size

        Args:
            count: Number of CLASS entries

        Returns:
            List of parsed CLASS entry dicts
        """
        entries = []

        for _ in range(count):
            # ObjectInfo (10 bytes) - TRACED via FUN_01af6b80
            nb_class_versions = self.read_uint8()
            object_name = self.read_uint32()
            object_id = self.read_uint32()
            instancing_mode = self.read_uint8()

            # Entry metadata
            entry_type_hash = self.read_uint32()
            entry_content_size = self.read_uint32()
            entry_end = self.pos + entry_content_size

            entry_prop_size = self.read_uint32()
            prop_end = self.pos + entry_prop_size

            # Parse nested properties
            nested_props = []
            while self.pos < prop_end:
                prop = self._parse_nested_property(prop_end)
                if prop is None:
                    break
                nested_props.append(prop)

            # Read dynamic_properties_size (4 bytes at end of ObjectInfo-headed structures)
            # This is the size of dynamic properties - typically 0 but CAN be non-zero
            # Same pattern as root's dynamic_properties_size
            dynamic_props_size = 0
            if self.pos < entry_end:
                remaining = entry_end - self.pos
                if remaining == 4:
                    dynamic_props_size = struct.unpack('<I', self.read_bytes(4))[0]
                else:
                    # Unexpected size - skip but warn
                    self.read_bytes(remaining)

            # Get human-readable class name if known (informational only)
            type_name = get_type_name(entry_type_hash)

            entry_dict = {
                'nb_class_versions': f'0x{nb_class_versions:02X}',
                'object_name': format_hex_32(object_name),
                'object_id': format_hex_32(object_id),
                'instancing_mode': f'0x{instancing_mode:02X}',
                'type_hash': format_hex_32(entry_type_hash),
                'properties': nested_props,
                'dynamic_properties_size': dynamic_props_size,
            }
            if type_name:
                entry_dict['_type_name'] = type_name
            entries.append(entry_dict)

        return entries

    def _parse_nested_property(self, prop_end: int) -> Optional[dict]:
        """
        Parse a single nested property within a CLASS entry.

        Uses the SAME format as root properties:
          [4 bytes] section_size
          [4 bytes] property_id
          [8 bytes] type_descriptor
          [N bytes] value

        Args:
            prop_end: Position where property data ends

        Returns:
            Property dict or None if invalid
        """
        prop_section_size = self.read_int32()

        # Validate section_size
        if prop_section_size <= 0 or self.pos + prop_section_size > prop_end + 4:
            return None

        prop_id = self.read_uint32()
        prop_type_hash = self.read_uint32()
        prop_type_info = self.read_uint32()
        prop_type_code = (prop_type_info >> 16) & 0x3F
        prop_element_type = (prop_type_info >> 23) & 0x3F

        # Calculate bytes remaining for value (section_size - header)
        value_size = prop_section_size - 12

        if value_size > 0:
            prop_value, _ = self.parse_value(
                prop_type_code, value_size, prop_element_type, prop_type_hash
            )
        else:
            prop_value = None

        result = {
            'prop_id': format_hex_32(prop_id),
            'type_hash': format_hex_32(prop_type_hash),
            'type_info': format_hex_32(prop_type_info),
            'value': prop_value
        }
        # Add human-readable type name for containers with CLASS elements (informational only)
        type_name = get_type_name(prop_type_hash)
        if type_name:
            result['_type_name'] = type_name
        return result

    # -------------------------------------------------------------------------
    # PROPERTY PARSING
    # -------------------------------------------------------------------------

    def parse_property(self) -> Optional[DynamicProperty]:
        """
        Parse a single property from binary mode (ctx+0x58 == 3).

        TRACED: FUN_01b077d0 for property header, FUN_01b0c2e0 for value

        Binary Layout (Mode 3):
          [4 bytes] section_size - via BeginSection (vtable+0x0C, FUN_01b48890)
          [4 bytes] property_id - via vtable+0x84 (FUN_01b49610)
          [8 bytes] type_descriptor - via FUN_01b0e980
          [N bytes] value - via FUN_01b0c2e0 type dispatcher

        IMPORTANT: Mode 3 SKIPS PropertyHeaderFlag (FUN_01b076f0)!
        The 0x0B marker appears in the VALUE, not the header.

        Returns:
            DynamicProperty object or None if at end of data
        """
        if self.is_at_end():
            return None

        prop_offset = self.pos

        # BeginSection via vtable+0x0c (FUN_01b48890) reads 4-byte section size
        section_size = self.read_int32()
        section_end = self.pos + section_size

        # Property ID via vtable+0x84 (FUN_01b49610) reads 4 bytes
        property_id = self.read_uint32()

        # Type descriptor via FUN_01b0e980 reads 8 bytes
        type_desc, type_code, type_hash, element_type = self.parse_type_descriptor()

        # Calculate bytes remaining for value
        # Header in mode 3 = ID(4) + TypeDesc(8) = 12 bytes, NO flags
        bytes_remaining = section_size - 12

        # Value via FUN_01b0c2e0 type dispatcher
        value, _ = self.parse_value(type_code, bytes_remaining, element_type, type_hash)

        # Skip any untraced trailing bytes to reach section end
        if self.pos != section_end:
            skipped = section_end - self.pos
            if skipped > 0:
                skip_data = self.read_bytes(skipped)
                print(f"    Skipping {skipped} untraced bytes: {skip_data.hex()}")
            self.pos = section_end

        raw_bytes = self.data[prop_offset:self.pos]

        return DynamicProperty(
            offset=prop_offset,
            section_size=section_size,
            property_id=property_id,
            type_descriptor=type_desc,
            type_code=type_code,
            value=value,
            raw_bytes=raw_bytes,
        )

    # -------------------------------------------------------------------------
    # FILE PARSING
    # -------------------------------------------------------------------------

    def parse(self) -> dict:
        """
        Parse complete Section 4 file structure.

        TRACED file header (22 bytes) via FUN_01af6b80 + FUN_01b404c0:
          [1 byte]  NbClassVersionsInfo - class version count
          [4 bytes] ObjectName - null string hash
          [4 bytes] ObjectID
          [1 byte]  InstancingMode
          [4 bytes] Type hash (identifies root object type)
          [4 bytes] Size field 1 (content + size fields = size_field_2 + 8)
          [4 bytes] Size field 2 (content only, defines property region)

        TRACED Dynamic Properties footer (4 bytes) via FUN_01b38d90 + FUN_01b404c0:
          [4 bytes] Size of dynamic properties section (0 when empty)

        Returns:
            Dict containing parsed file structure
        """
        # ObjectInfo structure (10 bytes) - TRACED via FUN_01af6b80
        nb_class_versions = self.read_uint8()
        object_name = self.read_uint32()
        object_id = self.read_uint32()
        instancing_mode = self.read_uint8()

        # Type hash - identifies the root object type
        type_hash = self.read_uint32()

        # Size fields - TRACED via FUN_01b404c0
        size_field_1 = self.read_uint32()  # content + size fields
        size_field_2 = self.read_int32()   # content only
        dyn_section_end = self.pos + size_field_2

        print(f"ObjectInfo: nb_class_versions={nb_class_versions}, "
              f"object_name=0x{object_name:08X}, object_id=0x{object_id:08X}, "
              f"instancing_mode={instancing_mode}")
        type_name = get_type_name(type_hash)
        if type_name:
            print(f"Type hash: 0x{type_hash:08X} ({type_name})")
        else:
            print(f"Type hash: 0x{type_hash:08X}")
        print(f"Size fields: {size_field_1} (with sizes), {size_field_2} (content only)")
        print(f"Properties: {size_field_2} bytes "
              f"(0x{self.pos:04X} to 0x{dyn_section_end:04X})")
        print()

        # Parse all properties
        properties = []
        prop_num = 0

        while self.pos < dyn_section_end:
            print(f"Property {prop_num} at 0x{self.pos:04X}:")
            prop = self.parse_property()
            if prop is None:
                break
            properties.append(prop)
            print(f"  ID=0x{prop.property_id:08X}, type={prop.type_code}, "
                  f"value={prop.value}")
            print()
            prop_num += 1

        # Dynamic Properties footer - TRACED via FUN_01b38d90 + FUN_01b404c0
        dynamic_properties_size = self.read_uint32()

        # Get human-readable class name if known (informational only)
        type_name = get_type_name(type_hash)

        result = {
            'nb_class_versions': f'0x{nb_class_versions:02X}',
            'object_name': format_hex_32(object_name),
            'object_id': format_hex_32(object_id),
            'instancing_mode': f'0x{instancing_mode:02X}',
            'type_hash': format_hex_32(type_hash),
            # size_field_1 and size_field_2 are NOT stored - calculated during serialization
            'properties': properties,
            'dynamic_properties_size': dynamic_properties_size,
        }
        if type_name:
            result['_type_name'] = type_name
        return result


# =============================================================================
# SERIALIZER CLASS
# =============================================================================

class Section4Serializer:
    """
    Serializer for Section 4 binary format.

    Mirrors the parser structure exactly to ensure perfect roundtrip.
    All serialization logic follows the same traced code paths as parsing.

    Attributes:
        buffer: Byte buffer being written to
    """

    def __init__(self):
        """Initialize serializer with empty buffer."""
        self.buffer = bytearray()

    # -------------------------------------------------------------------------
    # LOW-LEVEL WRITE METHODS
    # -------------------------------------------------------------------------

    def write_bytes(self, data: bytes):
        """
        Write raw bytes to buffer.

        Args:
            data: Bytes to write
        """
        self.buffer.extend(data)

    def write_uint8(self, value: int):
        """
        Write unsigned 8-bit integer (1 byte).

        Args:
            value: Value to write (0-255)
        """
        self.buffer.append(value & 0xFF)

    def write_int32(self, value: int):
        """
        Write signed 32-bit integer (4 bytes, little-endian).

        Args:
            value: Signed 32-bit value
        """
        self.buffer.extend(struct.pack('<i', value))

    def write_uint32(self, value: int):
        """
        Write unsigned 32-bit integer (4 bytes, little-endian).

        Args:
            value: Unsigned 32-bit value
        """
        self.buffer.extend(struct.pack('<I', value))

    # -------------------------------------------------------------------------
    # PRIMITIVE VALUE SERIALIZATION
    # -------------------------------------------------------------------------

    def write_primitive_value(self, type_code: int, value: Any) -> bytes:
        """
        Write a primitive value based on type code.

        This is the SINGLE unified path for all primitive types, mirroring
        read_primitive_value() in the parser.

        Args:
            type_code: Type code from PropertyType enum
            value: Value to serialize

        Returns:
            Serialized bytes (without 0x0B marker)

        Raises:
            ValueError: If type_code is not a known primitive type
        """
        buf = bytearray()

        # 1-byte types
        if type_code == PropertyType.BOOL or type_code == PropertyType.BOOL_ALT:
            buf.append(1 if value else 0)
        elif type_code == PropertyType.UINT8:
            buf.append(value & 0xFF)
        elif type_code == PropertyType.INT8:
            buf.extend(struct.pack('<b', value))

        # 2-byte types
        elif type_code == PropertyType.UINT16:
            buf.extend(struct.pack('<H', value))
        elif type_code == PropertyType.INT16:
            buf.extend(struct.pack('<h', value))

        # 4-byte types
        elif type_code == PropertyType.INT32_V2:
            buf.extend(struct.pack('<i', value))
        elif type_code == PropertyType.UINT32:
            buf.extend(struct.pack('<I', value))
        elif type_code == PropertyType.INT32:
            buf.extend(struct.pack('<i', value))
        elif type_code == PropertyType.STRING:
            buf.extend(struct.pack('<I', value))

        # 8-byte types
        elif type_code == PropertyType.UINT64:
            buf.extend(struct.pack('<Q', value))
        elif type_code == PropertyType.FLOAT64:
            buf.extend(struct.pack('<d', value))

        # 4-byte float (type 10 - confirmed via binary: 0x3f800000 = 1.0f)
        elif type_code == PropertyType.FLOAT_ALT:
            buf.extend(struct.pack('<f', value))

        # Enum variant type 25: 4-byte value + 4-byte name hash
        elif type_code == PropertyType.ENUM_ALT:
            buf.extend(struct.pack('<I', value['value']))
            name_hash = value['name_hash']
            if isinstance(name_hash, str):
                name_hash = parse_hex_string(name_hash)
            buf.extend(struct.pack('<I', name_hash))

        else:
            raise ValueError(f"Unknown primitive type code: {type_code}")

        return bytes(buf)

    # -------------------------------------------------------------------------
    # VALUE SERIALIZATION
    # -------------------------------------------------------------------------

    def serialize_value(self, type_code: int, value: Any,
                        element_type: int = 0, type_hash: int = 0) -> bytes:
        """
        Serialize a value based on type code.

        TRACED: FUN_01af9930 -> FUN_01b2c6d0 -> FUN_01b0d530
        All property values have: [0x0B marker] + [value bytes]

        Args:
            type_code: Type code from PropertyType enum
            value: Value to serialize
            element_type: For containers, element type code
            type_hash: Type hash for CLASS entries

        Returns:
            Serialized bytes including 0x0B marker
        """
        buf = bytearray()

        # RAW BYTES - check FIRST before type-specific handling
        # This handles cases where section_size didn't match expected type
        if isinstance(value, dict) and '_raw_bytes' in value:
            raw_bytes = value['_raw_bytes']
            if isinstance(raw_bytes, bytes):
                buf.extend(raw_bytes)
            elif isinstance(raw_bytes, dict) and '_hex' in raw_bytes:
                buf.extend(bytes.fromhex(raw_bytes['_hex']))
            return bytes(buf)

        # Fixed types: marker (0x0B) + value
        if type_code in TYPE_SIZES:
            buf.append(0x0B)
            buf.extend(self.write_primitive_value(type_code, value))

        # Type 27 - Variable-length UTF-16 string
        elif type_code == PropertyType.VARSTRING:
            buf.extend(self._serialize_varstring(value))

        # MAP/MAP_ALT types
        elif type_code == PropertyType.MAP or type_code == PropertyType.MAP_ALT:
            buf.extend(self._serialize_map(value, element_type))

        return bytes(buf)

    def _serialize_varstring(self, value: str) -> bytes:
        """
        Serialize a variable-length UTF-16 string.

        Binary Format:
          [1 byte]  0x0B marker
          [4 bytes] char_count
          [N bytes] UTF-16LE string data
          [2 bytes] null terminator (only if char_count > 0)

        Args:
            value: String to serialize

        Returns:
            Serialized bytes
        """
        buf = bytearray()
        buf.append(0x0B)

        char_count = len(value)
        buf.extend(struct.pack('<I', char_count))

        if char_count > 0:
            string_bytes = value.encode('utf-16-le')
            buf.extend(string_bytes)
            buf.extend(b'\x00\x00')

        return bytes(buf)

    def _serialize_map(self, value: dict, element_type: int) -> bytes:
        """
        Serialize a MAP or MAP_ALT container.

        Binary Format:
          [1 byte]  marker (0x0B)
          [1 byte]  content_code (usually 0x01, purpose unknown)
          [4 bytes] count
          [N bytes] entries

        Args:
            value: Map dict with 'marker', 'content_code', 'count', 'entries'
            element_type: Element type code

        Returns:
            Serialized bytes
        """
        buf = bytearray()

        marker = value['marker']
        if isinstance(marker, str):
            marker = parse_hex_string(marker)
        content_code = value['content_code']
        if isinstance(content_code, str):
            content_code = parse_hex_string(content_code)

        buf.append(marker)
        buf.append(content_code)
        count = value['count']
        if isinstance(count, str):
            count = parse_hex_string(count)
        buf.extend(struct.pack('<i', count))

        entries = value['entries']
        if isinstance(entries, list):
            if count > 0 and element_type == PropertyType.CLASS:
                for entry in entries:
                    buf.extend(self.serialize_class_entry(entry))
            elif count > 0:
                buf.extend(self._serialize_fixed_entries(entries, element_type))

        return bytes(buf)

    def _serialize_fixed_entries(self, entries: list, element_type: int) -> bytes:
        """
        Serialize fixed-size MAP entries.

        Args:
            entries: List of entry values
            element_type: Element type code

        Returns:
            Serialized bytes
        """
        buf = bytearray()
        elem_size = get_element_size(element_type)

        for entry in entries:
            if isinstance(entry, str) and entry.startswith('0x'):
                val = parse_hex_string(entry)
            elif isinstance(entry, int):
                val = entry
            else:
                continue

            if elem_size == 1:
                buf.append(val & 0xFF)
            elif elem_size == 4:
                buf.extend(struct.pack('<I', val))
            elif elem_size == 8:
                buf.extend(struct.pack('<Q', val))

        return bytes(buf)

    def serialize_class_entry(self, entry: dict) -> bytes:
        """
        Serialize a CLASS entry within a MAP.

        All ObjectInfo-headed structures follow this pattern:
          ObjectInfo (10 bytes):
            [1 byte]  NbClassVersionsInfo
            [4 bytes] ObjectName
            [4 bytes] ObjectID
            [1 byte]  InstancingMode
          Metadata:
            [4 bytes] type_hash
            [4 bytes] content_size (calculated: 4 + prop_size + 4)
            [4 bytes] prop_size (calculated: len(properties))
          Content:
            [N bytes] properties
            [4 bytes] footer (always 0, same as root's dynamic_properties_size)

        Args:
            entry: CLASS entry dict

        Returns:
            Serialized bytes
        """
        buf = bytearray()

        # ObjectInfo (10 bytes)
        nb_class_versions = entry.get('nb_class_versions', 0)
        if isinstance(nb_class_versions, str):
            nb_class_versions = parse_hex_string(nb_class_versions)
        buf.append(nb_class_versions)
        object_name = entry.get('object_name', 0)
        if isinstance(object_name, str):
            object_name = parse_hex_string(object_name)
        buf.extend(struct.pack('<I', object_name))
        object_id = entry.get('object_id', 0)
        if isinstance(object_id, str):
            object_id = parse_hex_string(object_id)
        buf.extend(struct.pack('<I', object_id))
        instancing_mode = entry.get('instancing_mode', 0)
        if isinstance(instancing_mode, str):
            instancing_mode = parse_hex_string(instancing_mode)
        buf.append(instancing_mode)

        # Type hash
        type_hash = entry['type_hash']
        if isinstance(type_hash, str):
            type_hash = parse_hex_string(type_hash)
        buf.extend(struct.pack('<I', type_hash))

        # Serialize nested properties first to calculate sizes
        props_buf = bytearray()
        for prop in entry['properties']:
            props_buf.extend(self.serialize_nested_property(prop))

        # Calculate sizes
        # content_size = prop_size_field(4) + properties + footer(4)
        prop_size = len(props_buf)
        content_size = 4 + prop_size + 4

        buf.extend(struct.pack('<I', content_size))
        buf.extend(struct.pack('<I', prop_size))
        buf.extend(props_buf)

        # Footer - dynamic_properties_size (can be non-zero if dynamic properties exist)
        # Same pattern as root's dynamic_properties_size
        buf.extend(struct.pack('<I', entry.get('dynamic_properties_size', 0)))

        return bytes(buf)

    def serialize_nested_property(self, prop: dict) -> bytes:
        """
        Serialize a nested property within a CLASS entry.

        Uses the SAME format as root properties:
          [4 bytes] section_size
          [4 bytes] property_id
          [8 bytes] type_descriptor
          [N bytes] value

        Args:
            prop: Property dict

        Returns:
            Serialized bytes
        """
        prop_id = prop['prop_id']
        if isinstance(prop_id, str):
            prop_id = parse_hex_string(prop_id)

        type_hash = prop.get('type_hash', 0)
        if isinstance(type_hash, str):
            type_hash = parse_hex_string(type_hash)
        type_info = prop.get('type_info', 0)
        if isinstance(type_info, str):
            type_info = parse_hex_string(type_info)
        type_code = (type_info >> 16) & 0x3F
        element_type = (type_info >> 23) & 0x3F

        # Serialize value
        value_bytes = self.serialize_value(
            type_code, prop['value'], element_type, type_hash
        )

        # Build property content
        content = bytearray()
        content.extend(struct.pack('<I', prop_id))
        content.extend(struct.pack('<I', type_hash))
        content.extend(struct.pack('<I', type_info))
        content.extend(value_bytes)

        # Build full property with section_size
        buf = bytearray()
        buf.extend(struct.pack('<I', len(content)))
        buf.extend(content)

        return bytes(buf)

    def serialize_property(self, prop: DynamicProperty) -> bytes:
        """
        Serialize a single DynamicProperty.

        Binary Layout:
          [4 bytes] section_size
          [4 bytes] property_id
          [8 bytes] type_descriptor
          [N bytes] value

        Args:
            prop: DynamicProperty to serialize

        Returns:
            Serialized bytes
        """
        # Extract element_type and type_hash from type_descriptor
        td = prop.type_descriptor
        th = struct.unpack('<I', td[0:4])[0]
        ti = struct.unpack('<I', td[4:8])[0]
        et = (ti >> 23) & 0x3F

        # Serialize the value
        value_bytes = self.serialize_value(prop.type_code, prop.value, et, th)

        # Build property content
        content = bytearray()
        content.extend(struct.pack('<I', prop.property_id))
        content.extend(prop.type_descriptor)
        content.extend(value_bytes)

        # Build full property with section_size
        result = bytearray()
        result.extend(struct.pack('<i', len(content)))
        result.extend(content)

        return bytes(result)

    # -------------------------------------------------------------------------
    # FILE SERIALIZATION
    # -------------------------------------------------------------------------

    def serialize(self, parsed: dict) -> bytes:
        """
        Serialize a complete Section 4 file structure.

        TRACED file header (22 bytes) via FUN_01af6b80 + FUN_01b404c0:
          [1 byte]  NbClassVersionsInfo
          [4 bytes] ObjectName
          [4 bytes] ObjectID
          [1 byte]  InstancingMode
          [4 bytes] Type hash
          [4 bytes] Size field 1 (content + 8)
          [4 bytes] Size field 2 (content only)

        TRACED Dynamic Properties footer (4 bytes) via FUN_01b38d90 + FUN_01b404c0

        Args:
            parsed: Parsed file structure dict

        Returns:
            Complete serialized binary
        """
        self.buffer = bytearray()

        # Serialize all properties first to calculate sizes
        props_data = bytearray()
        for prop in parsed['properties']:
            props_data.extend(self.serialize_property(prop))

        # Calculate size fields
        size_field_2 = len(props_data)
        size_field_1 = size_field_2 + 8

        # ObjectInfo (10 bytes)
        nb_class_versions = parsed.get('nb_class_versions', 0)
        if isinstance(nb_class_versions, str):
            nb_class_versions = parse_hex_string(nb_class_versions)
        self.write_uint8(nb_class_versions)
        object_name = parsed.get('object_name', 0)
        if isinstance(object_name, str):
            object_name = parse_hex_string(object_name)
        self.write_uint32(object_name)
        object_id = parsed.get('object_id', 0)
        if isinstance(object_id, str):
            object_id = parse_hex_string(object_id)
        self.write_uint32(object_id)
        instancing_mode = parsed.get('instancing_mode', 0)
        if isinstance(instancing_mode, str):
            instancing_mode = parse_hex_string(instancing_mode)
        self.write_uint8(instancing_mode)

        # Type hash
        type_hash = parsed.get('type_hash', 0)
        if isinstance(type_hash, str):
            type_hash = parse_hex_string(type_hash)
        self.write_uint32(type_hash)

        # Size fields
        self.write_uint32(size_field_1)
        self.write_int32(size_field_2)

        # Properties
        self.write_bytes(props_data)

        # Dynamic Properties footer
        self.write_uint32(parsed.get('dynamic_properties_size', 0))

        return bytes(self.buffer)


# =============================================================================
# JSON CONVERSION UTILITIES
# =============================================================================

def convert_bytes_to_hex(obj: Any) -> Any:
    """
    Recursively convert bytes to hex strings for JSON serialization.

    Bytes are stored as {'_hex': 'hexstring'} to distinguish from regular dicts.

    Args:
        obj: Object to convert (bytes, dict, list, or primitive)

    Returns:
        Converted object with bytes as hex dicts
    """
    if isinstance(obj, bytes):
        return {'_hex': obj.hex()}
    elif isinstance(obj, dict):
        return {k: convert_bytes_to_hex(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_bytes_to_hex(item) for item in obj]
    else:
        return obj


def convert_hex_to_bytes(obj: Any) -> Any:
    """
    Recursively convert hex dicts back to bytes.

    Recognizes {'_hex': 'hexstring'} format from convert_bytes_to_hex().

    Args:
        obj: Object to convert

    Returns:
        Converted object with hex dicts as bytes
    """
    if isinstance(obj, dict):
        if '_hex' in obj and len(obj) == 1:
            return bytes.fromhex(obj['_hex'])
        return {k: convert_hex_to_bytes(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_hex_to_bytes(item) for item in obj]
    else:
        return obj


def property_to_json(prop: DynamicProperty) -> Dict:
    """
    Convert a DynamicProperty to a JSON-serializable dict.

    Decodes type_descriptor into type_hash and type_info components.
    Removes padding from CLASS entries (it's reconstructed from sizes).

    Args:
        prop: DynamicProperty to convert

    Returns:
        JSON-serializable dict
    """
    type_hash = struct.unpack('<I', prop.type_descriptor[0:4])[0]
    type_info = struct.unpack('<I', prop.type_descriptor[4:8])[0]

    # Clean up value - remove padding from CLASS entries
    value = prop.value
    if isinstance(value, dict) and 'entries' in value:
        cleaned_entries = []
        for entry in value.get('entries', []):
            if isinstance(entry, dict) and 'padding' in entry:
                entry = {k: v for k, v in entry.items() if k != 'padding'}
            cleaned_entries.append(entry)
        value = {**value, 'entries': cleaned_entries}

    value = convert_bytes_to_hex(value)

    return {
        'property_id': format_hex_32(prop.property_id),
        'type_hash': format_hex_32(type_hash),
        'type_info': format_hex_32(type_info),
        'value': value,
    }


def json_to_property(d: Dict) -> DynamicProperty:
    """
    Convert a JSON dict back to a DynamicProperty.

    Reconstructs type_descriptor from type_hash and type_info.

    Args:
        d: JSON dict from property_to_json()

    Returns:
        DynamicProperty object
    """
    type_hash = d['type_hash']
    if isinstance(type_hash, str):
        type_hash = parse_hex_string(type_hash)

    type_info = d['type_info']
    if isinstance(type_info, str):
        type_info = parse_hex_string(type_info)

    type_descriptor = struct.pack('<I', type_hash) + struct.pack('<I', type_info)
    type_code = (type_info >> 16) & 0x3F

    value = convert_hex_to_bytes(d['value'])

    property_id = d['property_id']
    if isinstance(property_id, str):
        property_id = parse_hex_string(property_id)

    return DynamicProperty(
        offset=0,
        section_size=0,
        property_id=property_id,
        type_descriptor=type_descriptor,
        type_code=type_code,
        value=value,
        raw_bytes=b'',
    )


def parsed_to_json(parsed: Dict) -> Dict:
    """
    Convert parsed file structure to JSON-serializable format.

    Args:
        parsed: Parsed structure from Section4Parser.parse()

    Returns:
        JSON-serializable dict
    """
    return {
        'nb_class_versions': parsed['nb_class_versions'],
        'object_name': parsed['object_name'],  # Already hex formatted
        'object_id': parsed['object_id'],  # Already hex formatted
        'instancing_mode': parsed['instancing_mode'],
        'type_hash': parsed['type_hash'],  # Already hex formatted
        'properties': [property_to_json(p) for p in parsed['properties']],
        'dynamic_properties_size': parsed['dynamic_properties_size'],
    }


def json_to_parsed(data: Dict) -> Dict:
    """
    Convert JSON data back to format expected by serializer.

    Args:
        data: JSON data from parsed_to_json()

    Returns:
        Dict for Section4Serializer.serialize()
    """
    object_name = data['object_name']
    if isinstance(object_name, str):
        object_name = parse_hex_string(object_name)

    object_id = data['object_id']
    if isinstance(object_id, str):
        object_id = parse_hex_string(object_id)

    type_hash = data['type_hash']
    if isinstance(type_hash, str):
        type_hash = parse_hex_string(type_hash)

    return {
        'nb_class_versions': data['nb_class_versions'],
        'object_name': object_name,
        'object_id': object_id,
        'instancing_mode': data['instancing_mode'],
        'type_hash': type_hash,
        'properties': [json_to_property(p) for p in data['properties']],
        'dynamic_properties_size': data['dynamic_properties_size'],
    }


# =============================================================================
# PUBLIC API FUNCTIONS
# =============================================================================

def to_json_file(input_bin: str, output_json: str):
    """
    Parse a binary file and save to JSON.

    Args:
        input_bin: Path to input .bin file
        output_json: Path to output .json file
    """
    with open(input_bin, 'rb') as f:
        data = f.read()

    parser = Section4Parser(data)
    parsed = parser.parse()

    json_data = parsed_to_json(parsed)

    with open(output_json, 'w') as f:
        json.dump(json_data, f, indent=2)

    print(f"Saved {output_json}")


def from_json_file(input_json: str, output_bin: str):
    """
    Load a JSON file and save to binary.

    Args:
        input_json: Path to input .json file
        output_bin: Path to output .bin file
    """
    with open(input_json, 'r') as f:
        json_data = json.load(f)

    parsed = json_to_parsed(json_data)

    serializer = Section4Serializer()
    binary = serializer.serialize(parsed)

    with open(output_bin, 'wb') as f:
        f.write(binary)

    print(f"Saved {output_bin} ({len(binary)} bytes)")


def roundtrip_test(filename: str) -> bool:
    """
    Test roundtrip: parse -> serialize -> compare.

    This verifies that the parser and serializer are perfect inverses.
    Any byte difference indicates a bug in the traced code understanding.

    Args:
        filename: Path to binary file to test

    Returns:
        True if roundtrip succeeds (files identical), False otherwise
    """
    with open(filename, 'rb') as f:
        original = f.read()

    print(f"Roundtrip test for {filename}")
    print("=" * 60)

    # Parse
    parser = Section4Parser(original)
    parsed = parser.parse()

    print()
    print("Serializing...")

    # Serialize
    serializer = Section4Serializer()
    serialized = serializer.serialize(parsed)

    # Compare
    print(f"Original size:   {len(original)} bytes")
    print(f"Serialized size: {len(serialized)} bytes")

    if original == serialized:
        print("ROUNDTRIP SUCCESS: Files are identical!")
        return True
    else:
        # Find first difference for debugging
        min_len = min(len(original), len(serialized))
        for i in range(min_len):
            if original[i] != serialized[i]:
                print(f"ROUNDTRIP FAILED: First difference at offset 0x{i:04X}")
                print(f"  Original:   0x{original[i]:02X}")
                print(f"  Serialized: 0x{serialized[i]:02X}")
                start = max(0, i - 8)
                end = min(min_len, i + 8)
                print(f"  Original context:   {original[start:end].hex()}")
                print(f"  Serialized context: {serialized[start:end].hex()}")
                break
        else:
            if len(original) != len(serialized):
                print(f"ROUNDTRIP FAILED: Size mismatch")

        # Save serialized for manual comparison
        out_file = filename.replace('.bin', '_serialized.bin')
        with open(out_file, 'wb') as f:
            f.write(serialized)
        print(f"Serialized output saved to: {out_file}")

        return False


def main():
    """
    Main entry point for command-line usage.

    Usage:
        python section4_parser.py <file> [options]

    Options:
        --roundtrip          Test parse -> serialize -> compare
        --to-json <out.json> Parse .bin and save to JSON
        --to-bin <out.bin>   Parse .json and save to binary

    Examples:
        section4_parser.py game.bin --to-json game.json
        section4_parser.py game.json --to-bin game.bin
        section4_parser.py game.bin --roundtrip
    """
    if len(sys.argv) < 2:
        print("Usage: python section4_parser.py <file> [options]")
        print()
        print("Options:")
        print("  --roundtrip              Test parse -> serialize -> compare")
        print("  --to-json <out.json>     Parse .bin and save to JSON")
        print("  --to-bin <out.bin>       Parse .json and save to binary")
        print()
        print("Examples:")
        print("  section4_parser.py game.bin --to-json game.json")
        print("  section4_parser.py game.json --to-bin game.bin")
        sys.exit(1)

    filename = sys.argv[1]
    do_roundtrip = '--roundtrip' in sys.argv

    # Handle --to-bin mode (JSON -> binary)
    if '--to-bin' in sys.argv:
        idx = sys.argv.index('--to-bin')
        if idx + 1 >= len(sys.argv):
            output_bin = filename.replace('.json', '.bin')
        else:
            output_bin = sys.argv[idx + 1]
        from_json_file(filename, output_bin)
        return

    # Handle --to-json mode (binary -> JSON)
    if '--to-json' in sys.argv:
        idx = sys.argv.index('--to-json')
        if idx + 1 >= len(sys.argv):
            output_json = filename.replace('.bin', '.json')
        else:
            output_json = sys.argv[idx + 1]
        to_json_file(filename, output_json)
        return

    # Default: parse and display
    with open(filename, 'rb') as f:
        data = f.read()

    print(f"Parsing {filename} ({len(data)} bytes)")
    print("=" * 60)
    print()

    parser = Section4Parser(data)
    result = parser.parse()

    print("=" * 60)
    print(f"Properties parsed: {len(result['properties'])}")
    print(f"Final position: 0x{parser.pos:04X} / 0x{parser.size:04X}")

    remaining = parser.size - parser.pos
    if remaining > 0:
        print(f"Remaining: {remaining} bytes")

    if do_roundtrip:
        print()
        roundtrip_test(filename)


if __name__ == '__main__':
    main()
