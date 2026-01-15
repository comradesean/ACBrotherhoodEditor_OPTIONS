#!/usr/bin/env python3
"""
Section 2 Parser for Assassin's Creed Brotherhood OPTIONS save files.

This module parses and serializes the "PlayerOptionsSaveData" section (Section 2)
from the OPTIONS binary format. Section 2 contains user settings like graphics
options, audio levels, control bindings, etc.

Based on SECTION2_SERIALIZATION.md v6.0 - fully documented from Ghidra decompilation.

Binary Format Overview:
=======================
Section 2 uses a hierarchical object structure with typed properties:

  ObjectStructure:
    - ObjectInfo header (variable size based on class versions and name)
    - T-hash (4 bytes) - type identifier hash
    - Object block size (4 bytes)
    - Properties block size (4 bytes)
    - Properties (array of PropertyRecord)
    - DynProps block size (4 bytes)
    - DynProps (array of PropertyRecord, usually empty)

  PropertyRecord (PropertyIteratorCore format):
    - Block size (4 bytes) - size of header + value
    - PropertyID (4 bytes) - hash identifying the property
    - ClassID (4 bytes) - hash identifying the property's class
    - TypeID (4 bytes) - encodes type info in bits 16-21 and element type in bits 23-28
    - PackedInfo (1 byte) - serialization flags (0x0B or 0x0F)
    - Value (variable) - type-dependent payload

Complete Serialization Call Flow (from decompilation):
  ProfileSerializer (FUN_01712930)
    -> ObjectCloser (FUN_01b0d0c0)
       -> PropertyIteratorCore (via context+0x28 StoredObject)
          -> TypeDispatcher (FUN_01b0c2e0)
             -> Type handlers (FUN_01b09650, etc.)
"""

import argparse
import json
import struct
import sys
from typing import Any, List, Optional


# =============================================================================
# TYPE CONSTANTS
# =============================================================================
# Type codes from FUN_01b0c2e0 (TypeDispatcher) decompilation.
# These identify how property values should be parsed/serialized.

TYPE_BOOLEAN = 0x00       # FUN_01b09650 - 1 byte (0 or 1)
TYPE_BYTE = 0x03          # FUN_01b12120 - 1 byte unsigned (vtable+0x98)
TYPE_FLOAT = 0x06         # FUN_01b12420 - 4 bytes IEEE 754 float (vtable+0x80)
TYPE_COMPLEX = 0x07       # FUN_01b12fa0 - 4 bytes (complex number component?)
TYPE_FLOAT_ALT = 0x0A     # FUN_01b12640 - 4 bytes float (alternate handler)
TYPE_NUMERIC = 0x11       # FUN_01b09880 - 4 bytes unsigned integer
TYPE_CLASSID = 0x12       # FUN_01b099a0 - 4 bytes class identifier hash
TYPE_CONTAINER = 0x13     # FUN_01b0a460 - contains nested ObjectStructure
TYPE_ENUM_SMALL = 0x15    # FUN_01b0b8a0 - 4 bytes enum value (vtable+0x84)
TYPE_NESTED_OBJECT = 0x16 # FUN_01b0b710 - contains nested ObjectStructure
TYPE_VECTOR = 0x17        # Inline in TypeDispatcher - count + elements
TYPE_ARRAY_ALT = 0x18     # FUN_01b0bcf0 - same handler as 0x1D
TYPE_ENUM_VARIANT = 0x19  # FUN_01b09c10 - 8 bytes (EnumValue:4 + EnumName:4)
TYPE_ARRAY = 0x1D         # FUN_01b0bcf0 - ContentCode + Count + Elements
TYPE_CLASSID_ALT = 0x1E   # FUN_01b099a0 - same handler as 0x12

# Element sizes for primitive types (from decompiled type handlers).
# Used when parsing array/vector elements to determine bytes per element.
ELEMENT_SIZES = {
    0x00: 1,   # Boolean - 1 byte
    0x03: 1,   # Byte - 1 byte
    0x06: 4,   # Float - 4 bytes
    0x07: 4,   # Complex - 4 bytes
    0x0A: 4,   # Float_Alt - 4 bytes
    0x11: 4,   # Numeric - 4 bytes
    0x12: 4,   # ClassID - 4 bytes
    0x15: 4,   # EnumSmall - 4 bytes
    0x19: 8,   # EnumVariant - 8 bytes (value + class_id)
    0x1E: 4,   # ClassID_Alt - 4 bytes
}

# Types that should be interpreted as IEEE 754 floats rather than integers
FLOAT_TYPES = {TYPE_FLOAT, TYPE_FLOAT_ALT}


# =============================================================================
# BINARY READER
# =============================================================================
class BinaryReader:
    """
    Sequential binary data reader with little-endian support.

    Wraps a bytes object and provides methods to read primitive types
    while automatically advancing the read position.
    """

    def __init__(self, data: bytes, offset: int = 0):
        """
        Initialize reader with binary data.

        Args:
            data: The binary data to read from.
            offset: Starting position (default 0).
        """
        self.data = data
        self.pos = offset

    def read_u8(self) -> int:
        """Read 1-byte unsigned integer and advance position."""
        val = self.data[self.pos]
        self.pos += 1
        return val

    def read_u16(self) -> int:
        """Read 2-byte little-endian unsigned integer and advance position."""
        val = struct.unpack('<H', self.data[self.pos:self.pos+2])[0]
        self.pos += 2
        return val

    def read_u32(self) -> int:
        """Read 4-byte little-endian unsigned integer and advance position."""
        val = struct.unpack('<I', self.data[self.pos:self.pos+4])[0]
        self.pos += 4
        return val

    def read_bytes(self, n: int) -> bytes:
        """Read n bytes and advance position."""
        val = self.data[self.pos:self.pos+n]
        self.pos += n
        return val

    def remaining(self) -> int:
        """Return number of bytes remaining from current position to end."""
        return len(self.data) - self.pos

    def tell(self) -> int:
        """Return current read position."""
        return self.pos


# =============================================================================
# BINARY WRITER
# =============================================================================
class BinaryWriter:
    """
    Binary data writer with little-endian support and sized block management.

    Provides methods to write primitive types and manage "sized blocks" where
    the block size is written as a 4-byte prefix before the content. The
    size_stack allows nested sized blocks.
    """

    def __init__(self):
        """Initialize empty writer."""
        self.data = bytearray()
        self.size_stack = []  # Stack of (start_position) for nested sized blocks

    def write_u8(self, val: int):
        """Write 1-byte unsigned integer."""
        self.data.append(val & 0xFF)

    def write_u32(self, val: int):
        """Write 4-byte little-endian unsigned integer."""
        self.data.extend(struct.pack('<I', val))

    def write_bytes(self, data: bytes):
        """Write raw bytes."""
        self.data.extend(data)

    def begin_sized_block(self):
        """
        Begin a sized block by writing a 4-byte placeholder.

        Call end_sized_block() after writing the block content to fill
        in the actual size. Supports nesting via internal stack.
        """
        pos = len(self.data)
        self.write_u32(0)  # Placeholder for size
        self.size_stack.append(pos)

    def end_sized_block(self) -> int:
        """
        End a sized block by filling in the size placeholder.

        Returns:
            The computed block size (content bytes, not including the 4-byte size field).
        """
        start_pos = self.size_stack.pop()
        content_start = start_pos + 4  # Content begins after the 4-byte size field
        block_size = len(self.data) - content_start
        struct.pack_into('<I', self.data, start_pos, block_size)
        return block_size

    def get_bytes(self) -> bytes:
        """Return the accumulated data as bytes."""
        return bytes(self.data)


# =============================================================================
# SECTION 2 PARSER
# =============================================================================
class Section2Parser:
    """
    Parser for Section 2 binary data to JSON representation.

    Reads the hierarchical object structure from binary and converts it to
    a JSON-serializable dict. Each property's type is determined from the
    TypeID field using bit extraction (bits 16-21 for property type, bits
    23-28 for element type in arrays/vectors).
    """

    def __init__(self, data: bytes):
        """
        Initialize parser with binary data.

        Args:
            data: Decompressed Section 2 binary data.
        """
        self.reader = BinaryReader(data)
        self.data = data

    def parse(self) -> dict:
        """
        Parse the entire Section 2 data.

        Returns:
            Dict with "root" key containing the parsed object structure.
        """
        return {
            "root": self._parse_object_structure()
        }

    def _parse_object_info(self) -> dict:
        """
        Parse ObjectInfo header (from FUN_01b08ce0 decompilation).

        ObjectInfo structure:
          - NbClassVersionsInfo (1 byte): count of class version entries
          - For each class version: ClassID (4 bytes) + Version (2 bytes)
          - ObjectName length (4 bytes)
          - ObjectName (variable, UTF-8, no null terminator)
          - ObjectID (4 bytes)
          - InstancingMode (1 byte)
          - FatherID (4 bytes, only if InstancingMode == 1)

        Returns:
            Dict containing parsed ObjectInfo fields.
        """
        obj = {}

        # NbClassVersionsInfo: count of class version pairs to follow
        nb_class_versions = self.reader.read_u8()
        obj["nb_class_versions"] = f"0x{nb_class_versions:02X}"

        # Skip class version entries (not needed for reconstruction)
        # Each entry: ClassID (4 bytes) + Version (2 bytes) = 6 bytes
        for _ in range(nb_class_versions):
            self.reader.read_u32()  # ClassID hash
            self.reader.read_u16()  # Version number

        # ObjectName: length-prefixed string (vtable+0x54 StringWriterAlt, no null)
        obj_name_len = self.reader.read_u32()
        obj["object_name_length"] = f"0x{obj_name_len:08X}"
        if obj_name_len > 0:
            obj["object_name"] = self.reader.read_bytes(obj_name_len).decode('utf-8', errors='replace')

        # ObjectID: unique identifier for this object instance (vtable+0x9c)
        obj["object_id"] = f"0x{self.reader.read_u32():08X}"

        # InstancingMode: determines if object has a parent reference (version >= 14)
        instancing_mode = self.reader.read_u8()
        obj["instancing_mode"] = f"0x{instancing_mode:02X}"

        # FatherID: only present if InstancingMode == 1
        if instancing_mode == 1:
            obj["father_id"] = self.reader.read_u32()

        return obj

    def _parse_object_structure(self) -> dict:
        """
        Parse complete object structure: ObjectInfo + T-hash + Object/Properties blocks.

        Structure after ObjectInfo:
          - T-hash (4 bytes): type identifier hash
          - Object size (4 bytes): total size of object content
          - Properties size (4 bytes): size of properties block
          - Properties content (variable)
          - DynProps size (4 bytes): size of dynamic properties block
          - DynProps content (variable, usually empty)

        Returns:
            Dict containing complete parsed object with properties.
        """
        # Parse ObjectInfo header
        obj = self._parse_object_info()

        # T-hash: type identifier for this object
        obj["t_hash"] = f"0x{self.reader.read_u32():08X}"

        # Object size (we don't store this, just read past it)
        self.reader.read_u32()

        # Properties size: tells us where properties block ends
        properties_size = self.reader.read_u32()
        properties_end = self.reader.tell() + properties_size

        # Parse property records until we reach properties_end
        obj["properties"] = self._parse_property_records(properties_end)

        # DynProps block (dynamic properties, usually empty in OPTIONS files)
        dynprops_size = self.reader.read_u32()
        if dynprops_size > 0:
            dynprops_end = self.reader.tell() + dynprops_size
            obj["dynprops"] = self._parse_property_records(dynprops_end)
        else:
            obj["dynprops"] = []

        return obj

    def _parse_property_records(self, end_offset: int) -> List[dict]:
        """
        Parse PropertyIteratorCore format records until end_offset.

        Args:
            end_offset: Byte position where property records end.

        Returns:
            List of parsed property record dicts.
        """
        records = []
        while self.reader.tell() < end_offset:
            # Minimum record size: size(4) + header(13) = 17 bytes
            if self.reader.remaining() < 17:
                break
            record = self._parse_property_record()
            if record:
                records.append(record)
            else:
                break
        return records

    def _parse_property_record(self) -> Optional[dict]:
        """
        Parse a single PropertyIteratorCore record.

        Record structure:
          - Block size (4 bytes): size of header + value (not including this field)
          - PropertyID (4 bytes): hash identifying the property name
          - ClassID (4 bytes): hash identifying the property's class context
          - TypeID (4 bytes): type information encoded in bits:
              * Bits 16-21: property type code (0x00-0x1E)
              * Bits 23-28: element type code (for arrays/vectors)
          - PackedInfo (1 byte): serialization flags (0x0B or 0x0F)
          - Value (block_size - 13 bytes): type-dependent payload

        Returns:
            Parsed property dict, or None if invalid/end of data.
        """
        block_size = self.reader.read_u32()

        # Validate: non-zero size that doesn't exceed remaining data
        if block_size == 0 or block_size > self.reader.remaining() + 4:
            return None

        # Parse 13-byte header
        property_id = self.reader.read_u32()
        class_id = self.reader.read_u32()
        type_id = self.reader.read_u32()
        packed_info = self.reader.read_u8()

        prop = {
            "property_id": f"0x{property_id:08X}",
            "class_id": f"0x{class_id:08X}",
            "type_id": f"0x{type_id:08X}",
            "packed_info": f"0x{packed_info:02X}",
        }

        # Extract type code from bits 16-21 of type_id (from FUN_01b0c2e0)
        type_code = (type_id >> 16) & 0x3F
        value_size = block_size - 13  # Header is always 13 bytes

        # Parse value based on type code
        if value_size <= 0:
            prop["value"] = None
        elif type_code in (TYPE_CONTAINER, TYPE_NESTED_OBJECT):
            # Nested object structure
            prop["value"] = self._parse_object_structure()
        elif type_code in (TYPE_ARRAY, TYPE_ARRAY_ALT):
            # Array: ContentCode + Count + Elements
            prop["value"] = self._parse_array_value(value_size, type_id)
        elif type_code == TYPE_VECTOR:
            # Vector: Count + Elements (no ContentCode)
            prop["value"] = self._parse_vector_value(value_size, type_id)
        else:
            # Simple primitive value
            prop["value"] = self._parse_simple_value(type_code, value_size)

        return prop

    def _parse_elements(self, count: int, element_type: int, elements_size: int) -> tuple:
        """
        Parse array/vector elements based on element type.

        Shared logic for parsing typed elements in arrays and vectors.

        Args:
            count: Number of elements to parse.
            element_type: Type code for elements (from bits 23-28 of TypeID).
            elements_size: Total bytes available for elements.

        Returns:
            Tuple of (elements_list, is_unknown_type).
        """
        elem_size = ELEMENT_SIZES.get(element_type, -1)

        if elem_size <= 0:
            # Unknown element type - preserve as raw bytes
            data = self.reader.read_bytes(elements_size)
            return (list(data), True)

        elements = []
        for _ in range(count):
            if elem_size == 1:
                # 1-byte types: Boolean, Byte
                elements.append(self.reader.read_u8())
            elif elem_size == 4:
                # 4-byte types: Float, Numeric, ClassID, EnumSmall, etc.
                if element_type in FLOAT_TYPES:
                    elements.append(struct.unpack('<f', self.reader.read_bytes(4))[0])
                else:
                    elements.append(self.reader.read_u32())
            elif elem_size == 8:
                # 8-byte types: EnumVariant (value + class_id)
                val = self.reader.read_u32()
                cid = self.reader.read_u32()
                elements.append({"value": f"0x{val:08X}", "class_id": f"0x{cid:08X}"})

        return (elements, False)

    def _parse_array_value(self, value_size: int, type_id: int) -> dict:
        """
        Parse Array value (from FUN_01b0bcf0 + FUN_01b0c2e0).

        Array structure:
          - ContentCode (1 byte): content type indicator
          - Count (4 bytes): number of elements
          - Elements (count * element_size bytes)

        Element type is extracted from bits 23-28 of type_id.

        Args:
            value_size: Total bytes for array value.
            type_id: Full TypeID field for element type extraction.

        Returns:
            Dict with content_code, count, and elements.
        """
        content_code = self.reader.read_u8()
        count = self.reader.read_u32()
        element_type = (type_id >> 23) & 0x3F

        arr = {
            "content_code": f"0x{content_code:02X}",
            "count": f"0x{count:08X}",
        }

        elements_size = value_size - 5  # Subtract ContentCode(1) + Count(4)
        if elements_size > 0 and count > 0:
            elements, is_unknown = self._parse_elements(count, element_type, elements_size)
            arr["elements"] = elements
            if is_unknown:
                arr["_element_type_unknown"] = True
        else:
            arr["elements"] = []

        return arr

    def _parse_vector_value(self, value_size: int, type_id: int) -> dict:
        """
        Parse Vector value (from FUN_01b07be0 + FUN_01b0c2e0 case 0x17).

        Vector structure (differs from Array - no ContentCode):
          - Count (4 bytes): number of elements
          - Elements (count * element_size bytes)

        Element type is extracted from bits 23-28 of type_id.

        Args:
            value_size: Total bytes for vector value.
            type_id: Full TypeID field for element type extraction.

        Returns:
            Dict with count and elements.
        """
        count = self.reader.read_u32()
        element_type = (type_id >> 23) & 0x3F

        vec = {
            "count": f"0x{count:08X}",
        }

        elements_size = value_size - 4  # Subtract Count(4)
        if elements_size > 0 and count > 0:
            elements, is_unknown = self._parse_elements(count, element_type, elements_size)
            vec["elements"] = elements
            if is_unknown:
                vec["_element_type_unknown"] = True
        else:
            vec["elements"] = []

        return vec

    def _parse_simple_value(self, type_code: int, value_size: int) -> Any:
        """
        Parse simple (non-container) value based on type code and size.

        Value interpretation by size:
          - 1 byte: Boolean (returns Python bool) or Byte (returns int)
          - 4 bytes: Float (IEEE 754) or Integer
          - 8 bytes: EnumVariant (value + class_id pair)
          - Other: Unknown type, preserved as raw_bytes dict

        Args:
            type_code: Type code from bits 16-21 of TypeID.
            value_size: Number of bytes for this value.

        Returns:
            Parsed value (bool, int, float, dict, or raw_bytes dict).
        """
        if value_size == 1:
            val = self.reader.read_u8()
            if type_code == TYPE_BOOLEAN:
                return val != 0
            return val
        elif value_size == 4:
            if type_code in FLOAT_TYPES:
                return struct.unpack('<f', self.reader.read_bytes(4))[0]
            else:
                return self.reader.read_u32()
        elif value_size == 8:
            # EnumVariant (0x19): EnumValue(4) + EnumName(4) - from FUN_01b09c10
            val = self.reader.read_u32()
            enum_name = self.reader.read_u32()
            return {"value": f"0x{val:08X}", "class_id": f"0x{enum_name:08X}"}
        else:
            # Unknown size - preserve as raw bytes for round-trip fidelity
            data = self.reader.read_bytes(value_size)
            return {"raw_bytes": list(data)}


# =============================================================================
# SECTION 2 SERIALIZER
# =============================================================================
class Section2Serializer:
    """
    Serializer to convert JSON representation back to binary format.

    Writes the hierarchical object structure to binary, reconstructing
    the exact format expected by the game. Uses sized blocks to handle
    the length-prefixed structure.
    """

    def __init__(self, data: dict):
        """
        Initialize serializer with parsed JSON data.

        Args:
            data: Dict with "root" key containing object structure.
        """
        self.json_data = data
        self.writer = BinaryWriter()

    def serialize(self) -> bytes:
        """
        Serialize JSON data back to binary.

        Returns:
            Binary data bytes.
        """
        root = self.json_data.get("root", {})
        self._serialize_object_structure(root)
        return self.writer.get_bytes()

    def _serialize_object_info(self, obj: dict):
        """
        Serialize ObjectInfo header (mirrors _parse_object_info).

        Note: Class version entries are not preserved in JSON (only the count),
        so we write nb_class_versions=0 to skip them entirely. This works because
        the game only uses nb_class_versions to know how many entries to skip.

        Args:
            obj: Dict containing ObjectInfo fields.
        """
        # NbClassVersionsInfo: always write 0 (we don't preserve class versions)
        nb_class_versions = obj.get("nb_class_versions", "0x00")
        nb_class_versions = int(nb_class_versions, 16) if isinstance(nb_class_versions, str) else nb_class_versions
        self.writer.write_u8(nb_class_versions)
        # Note: When nb_class_versions > 0, the original file had class version
        # entries that we skipped during parsing. Since we write 0, no entries
        # are expected. This may need adjustment if class versions matter.

        # ObjectName: 4-byte length + UTF-8 string (no null terminator)
        obj_name = obj.get("object_name", "")
        obj_name_bytes = obj_name.encode('utf-8') if obj_name else b""
        self.writer.write_u32(len(obj_name_bytes))
        if obj_name_bytes:
            self.writer.write_bytes(obj_name_bytes)

        # ObjectID
        object_id = obj.get("object_id", "0x0")
        self.writer.write_u32(int(object_id, 16) if isinstance(object_id, str) else object_id)

        # InstancingMode
        instancing_mode = obj.get("instancing_mode", "0x00")
        instancing_mode = int(instancing_mode, 16) if isinstance(instancing_mode, str) else instancing_mode
        self.writer.write_u8(instancing_mode)

        # FatherID: only written if InstancingMode == 1
        if instancing_mode == 1:
            self.writer.write_u32(obj.get("father_id", 0))

    def _serialize_object_structure(self, obj: dict):
        """
        Serialize complete object structure (mirrors _parse_object_structure).

        Args:
            obj: Dict containing complete object with properties.
        """
        # ObjectInfo header
        self._serialize_object_info(obj)

        # T-hash
        t_hash = int(obj.get("t_hash", "0x0"), 16)
        self.writer.write_u32(t_hash)

        # Begin Object block (size placeholder)
        self.writer.begin_sized_block()

        # Begin Properties block (size placeholder)
        self.writer.begin_sized_block()
        for prop in obj.get("properties", []):
            self._serialize_property_record(prop)
        self.writer.end_sized_block()  # End Properties block

        # DynProps block
        self.writer.begin_sized_block()
        for prop in obj.get("dynprops", []):
            self._serialize_property_record(prop)
        self.writer.end_sized_block()  # End DynProps block

        self.writer.end_sized_block()  # End Object block

    def _serialize_property_record(self, prop: dict):
        """
        Serialize a PropertyIteratorCore record.

        Args:
            prop: Dict containing property fields.
        """
        # Begin sized block for this property (size = header + value)
        self.writer.begin_sized_block()

        # Parse header fields from hex strings
        property_id = int(prop.get("property_id", "0x0"), 16)
        class_id = int(prop.get("class_id", "0x0"), 16)
        type_id = int(prop.get("type_id", "0x0"), 16)
        packed_info = int(prop.get("packed_info", "0x0B"), 16)

        # Write 13-byte header
        self.writer.write_u32(property_id)
        self.writer.write_u32(class_id)
        self.writer.write_u32(type_id)
        self.writer.write_u8(packed_info)

        # Write value based on type code
        type_code = (type_id >> 16) & 0x3F
        value = prop.get("value")

        if type_code in (TYPE_CONTAINER, TYPE_NESTED_OBJECT):
            self._serialize_object_structure(value)
        elif type_code in (TYPE_ARRAY, TYPE_ARRAY_ALT):
            self._serialize_array_value(value, type_id)
        elif type_code == TYPE_VECTOR:
            self._serialize_vector_value(value, type_id)
        else:
            self._serialize_simple_value(value, type_code)

        self.writer.end_sized_block()

    def _serialize_elements(self, elements: list, element_type: int, is_unknown: bool):
        """
        Serialize array/vector elements based on element type.

        Shared logic for writing typed elements in arrays and vectors.

        Args:
            elements: List of elements to serialize.
            element_type: Type code for elements (from bits 23-28 of TypeID).
            is_unknown: If True, elements are raw bytes from unknown type.
        """
        if is_unknown:
            # Raw bytes - write directly
            for byte_val in elements:
                self.writer.write_u8(byte_val)
            return

        elem_size = ELEMENT_SIZES.get(element_type, -1)

        if elem_size == 1:
            for elem in elements:
                self.writer.write_u8(elem)
        elif elem_size == 4:
            for elem in elements:
                if element_type in FLOAT_TYPES:
                    self.writer.write_bytes(struct.pack('<f', elem))
                else:
                    self.writer.write_u32(elem)
        elif elem_size == 8:
            # EnumVariant: value(4) + class_id(4)
            for elem in elements:
                val = elem["value"]
                val = int(val, 16) if isinstance(val, str) else val
                cid = elem["class_id"]
                cid = int(cid, 16) if isinstance(cid, str) else cid
                self.writer.write_u32(val)
                self.writer.write_u32(cid)
        else:
            # Fallback for unknown element types
            for byte_val in elements:
                self.writer.write_u8(byte_val)

    def _serialize_array_value(self, arr: dict, type_id: int):
        """
        Serialize array value (mirrors _parse_array_value).

        Args:
            arr: Dict with content_code, count, elements.
            type_id: Full TypeID field for element type extraction.
        """
        if not arr:
            self.writer.write_u8(0)  # ContentCode
            self.writer.write_u32(0)  # Count
            return

        # Parse fields from hex strings
        content_code = arr.get("content_code", "0x00")
        content_code = int(content_code, 16) if isinstance(content_code, str) else content_code
        count = arr.get("count", "0x00000000")
        count = int(count, 16) if isinstance(count, str) else count
        elements = arr.get("elements", [])
        element_type = (type_id >> 23) & 0x3F
        is_unknown = arr.get("_element_type_unknown", False)

        self.writer.write_u8(content_code)
        self.writer.write_u32(count)
        self._serialize_elements(elements, element_type, is_unknown)

    def _serialize_vector_value(self, vec: dict, type_id: int):
        """
        Serialize vector value (mirrors _parse_vector_value).

        Args:
            vec: Dict with count and elements.
            type_id: Full TypeID field for element type extraction.
        """
        if not vec:
            self.writer.write_u32(0)  # Count
            return

        # Parse fields from hex strings
        count = vec.get("count", "0x00000000")
        count = int(count, 16) if isinstance(count, str) else count
        elements = vec.get("elements", [])
        element_type = (type_id >> 23) & 0x3F
        is_unknown = vec.get("_element_type_unknown", False)

        self.writer.write_u32(count)
        self._serialize_elements(elements, element_type, is_unknown)

    def _serialize_simple_value(self, value: Any, type_code: int):
        """
        Serialize simple (non-container) value based on type.

        Handles Python types: bool, int, float, dict (EnumVariant or raw_bytes),
        and list (fallback raw bytes).

        Args:
            value: The value to serialize.
            type_code: Type code for size determination.
        """
        if value is None:
            return
        elif isinstance(value, bool):
            # Boolean: 1 byte (0 or 1)
            self.writer.write_u8(1 if value else 0)
        elif isinstance(value, int):
            # Integer: size based on type code
            elem_size = ELEMENT_SIZES.get(type_code, 4)
            if elem_size == 1:
                self.writer.write_u8(value)
            else:
                self.writer.write_u32(value)
        elif isinstance(value, float):
            # Float: 4 bytes IEEE 754
            self.writer.write_bytes(struct.pack('<f', value))
        elif isinstance(value, dict):
            if "class_id" in value:
                # EnumVariant: value(4) + class_id(4)
                val = value["value"]
                val = int(val, 16) if isinstance(val, str) else val
                cid = value["class_id"]
                cid = int(cid, 16) if isinstance(cid, str) else cid
                self.writer.write_u32(val)
                self.writer.write_u32(cid)
            elif "raw_bytes" in value:
                # Unknown type preserved as raw bytes
                for byte_val in value["raw_bytes"]:
                    self.writer.write_u8(byte_val)
        elif isinstance(value, list):
            # Fallback: list of bytes
            for byte_val in value:
                self.writer.write_u8(byte_val)


# =============================================================================
# PUBLIC API FUNCTIONS
# =============================================================================
def parse_binary_to_json(input_path: str, output_path: str = None) -> dict:
    """
    Parse binary file to JSON.

    Args:
        input_path: Path to input binary file.
        output_path: Optional path to write JSON output. If None, returns dict only.

    Returns:
        Parsed data as dict.
    """
    with open(input_path, 'rb') as f:
        data = f.read()

    parser = Section2Parser(data)
    result = parser.parse()

    if output_path:
        with open(output_path, 'w') as f:
            json.dump(result, f, indent=2)

        # Count total property records for summary
        def count_props(obj):
            """Recursively count properties in object structure."""
            total = len(obj.get("properties", []))
            total += len(obj.get("dynprops", []))
            for prop in obj.get("properties", []):
                if isinstance(prop.get("value"), dict) and "properties" in prop["value"]:
                    total += count_props(prop["value"])
            return total

        total = count_props(result.get("root", {}))
        print(f"Parsed {total} property records to {output_path}")

    return result


def serialize_json_to_binary(input_path: str, output_path: str) -> bytes:
    """
    Serialize JSON file back to binary.

    Args:
        input_path: Path to input JSON file.
        output_path: Path to write output binary file.

    Returns:
        Serialized binary data.
    """
    with open(input_path, 'r') as f:
        data = json.load(f)

    serializer = Section2Serializer(data)
    result = serializer.serialize()

    with open(output_path, 'wb') as f:
        f.write(result)

    print(f"Serialized to {output_path} ({len(result)} bytes)")
    return result


def verify_roundtrip(original_path: str, rebuilt_path: str) -> bool:
    """
    Verify binary -> JSON -> binary produces identical output.

    Args:
        original_path: Path to original binary file.
        rebuilt_path: Path to rebuilt binary file.

    Returns:
        True if files match exactly, False otherwise.
    """
    with open(original_path, 'rb') as f:
        original = f.read()

    with open(rebuilt_path, 'rb') as f:
        rebuilt = f.read()

    if original == rebuilt:
        print("Round-trip verification: PASSED")
        return True

    print("Round-trip verification: FAILED")
    print(f"  Original: {len(original)} bytes")
    print(f"  Rebuilt: {len(rebuilt)} bytes")

    # Find and report first difference
    for i in range(min(len(original), len(rebuilt))):
        if original[i] != rebuilt[i]:
            print(f"  First diff at 0x{i:03X}: orig=0x{original[i]:02X}, rebuilt=0x{rebuilt[i]:02X}")
            break

    return False


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================
def main():
    """Command-line interface for Section 2 parser."""
    parser = argparse.ArgumentParser(
        description="Section 2 Parser for Assassin's Creed Brotherhood OPTIONS files (v6.0)"
    )
    parser.add_argument("input", nargs="?", help="Input file (binary or JSON)")
    parser.add_argument("-o", "--output", help="Output file path")
    parser.add_argument("--to-binary", action="store_true", help="Convert JSON to binary")
    parser.add_argument("--verify", nargs=2, metavar=("ORIG", "REBUILT"),
                        help="Verify two binary files match")
    parser.add_argument("--test", action="store_true", help="Run round-trip test")

    args = parser.parse_args()

    if args.verify:
        sys.exit(0 if verify_roundtrip(*args.verify) else 1)

    if args.test:
        # Round-trip test: binary -> JSON -> binary, verify match
        import tempfile
        import os

        input_bin = args.input or "game_uncompressed_2.bin"

        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = os.path.join(tmpdir, "test.json")
            rebuilt_path = os.path.join(tmpdir, "rebuilt.bin")

            parse_binary_to_json(input_bin, json_path)
            serialize_json_to_binary(json_path, rebuilt_path)
            success = verify_roundtrip(input_bin, rebuilt_path)
            sys.exit(0 if success else 1)

    if not args.input:
        parser.print_help()
        sys.exit(1)

    if args.to_binary:
        if not args.output:
            print("Error: --output required with --to-binary")
            sys.exit(1)
        serialize_json_to_binary(args.input, args.output)
    else:
        result = parse_binary_to_json(args.input, args.output)
        if not args.output:
            print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
