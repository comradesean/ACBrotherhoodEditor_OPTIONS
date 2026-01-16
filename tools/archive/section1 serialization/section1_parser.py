#!/usr/bin/env python3
"""
Section 1 Parser - Based on decompiled code analysis

From FUN_005e3560 (Section 1 Serializer):
  - FUN_01b09e20("SaveGame", 0, 0xbdbe3b52, ...) writes container header
  - Direct calls to field serializers (FUN_01b0a1f0, FUN_01b09650, etc.)

From FUN_01b0c2e0 (Type Dispatcher):
  - Descriptor type extracted from type_id: (type_id >> 16) & 0x3F
  - Descriptor types: 0x00=Bool, 0x07=Complex, 0x12=Pointer, 0x1A=String, etc.

From FUN_01b0d140 (PropertyHeaderWriter) + WinDbg verification:
  - Mode is ALWAYS 0 (verified via bp 01b0d140)
  - Root property: BeginBlock("Property") called → writes block size, but Type prefix skipped
  - Child properties: BeginBlock skipped (ctx+0x4e & 1 flag), but Type prefix written

Type Prefix Mapping (Descriptor → Binary):
  - 0x07 (Complex)  → 0x11 (Numeric format, 4 bytes)
  - 0x00 (Bool)     → 0x0E (BoolAlt format, 1 byte)
  - 0x1A (String)   → 0x19 (Enum format, string)
  - 0x12 (Pointer)  → 0x11 (Numeric format, 4 bytes)

Binary Layout (RE Verified via WinDbg):
  [Zero Prefix: 10 bytes]
  [Container Hash: 4 bytes] = 0xBDBE3B52 ("SaveGame")
  [Object Block Size: 4 bytes] = 265 (from BeginBlock "Object")
  [Properties Block Size: 4 bytes] = 257 (from BeginBlock "Properties")
  [Root Block Size: 4 bytes] = 17 (from BeginBlock "Property" for root)
  [Root Property: 17 bytes] = Hash + ClassID + type_id + PackedInfo + Value (NO Type prefix)
  [Child Properties: 18-29+ bytes] = Type + Hash + ClassID + type_id + PackedInfo + Value (NO block size)
  [Dynamic Props Block: 4 bytes] = 0x00000000 (empty block from FUN_01b0d0c0)
"""

import struct
import json
import sys

# Descriptor type codes from FUN_01b0c2e0 (extracted from type_id)
DESCRIPTOR_BOOL = 0x00
DESCRIPTOR_COMPLEX = 0x07
DESCRIPTOR_POINTER = 0x12
DESCRIPTOR_ARRAY = 0x17
DESCRIPTOR_STRING = 0x1A
DESCRIPTOR_POINTER_ALT = 0x1E

# Binary Type prefix codes (written to file for child properties)
# These determine how to parse/serialize the VALUE portion
TYPE_PREFIX_BOOL = 0x0E      # 1-byte value (from FUN_01b11fb0)
TYPE_PREFIX_NUMERIC = 0x11   # 4-byte value (from FUN_01b12fa0, FUN_01b099a0)
TYPE_PREFIX_STRING = 0x19    # String value: len(4) + chars + null (from FUN_01b12cf0)

# Human-readable names for display
TYPE_NAMES = {
    # Descriptor types (from type_id)
    0x00: "Bool",
    0x07: "Complex",
    0x12: "Pointer",
    0x17: "Array",
    0x1A: "String",
    0x1E: "PointerAlt",
    # Binary Type prefixes
    0x0E: "BoolAlt",
    0x11: "Numeric",
    0x19: "Enum",
}

# Constants
# Zero prefix is part of decompressed LZSS output, not from serializer
ZERO_PREFIX_SIZE = 10

# From FUN_01b0d0c0: After Properties block ends, it opens "Dynamic Properties" block
# which is empty (size=0), then closes it. This 0x00000000 is that empty block size.
DYNAMIC_PROPS_BLOCK_SIZE = 0x00000000

# PackedInfo computation (FUN_01b0d140 @ 01b0d269-01b0d2ac)
# Traced: FUN_005e3560 → PTR_DAT_027ecf54 → DAT_027ecd98[0x00] = 0x02000001 (Flags)
# Assembly: MOV EAX,[EBX]; SHR EAX,0x11; AND AL,0x1; ADD AL,AL; ADD AL,AL; AND AL,0xEF; OR AL,0x0B
# Formula: ((Flags >> 17) & 1) * 4 | 0x0B → bit 17 of 0x02000001 = 0 → 0x0B
PACKED_INFO = 0x0B


def extract_descriptor_type(type_id: int) -> int:
    """
    Extract descriptor type code from type_id field.
    From FUN_01b0c2e0: (type_id >> 16) & 0x3F
    """
    return (type_id >> 16) & 0x3F


def get_value_size_from_type_prefix(type_prefix: int) -> str:
    """
    Determine value format based on binary Type prefix.
    From FUN_01b0c2e0 type dispatcher switch statement.
    """
    if type_prefix == TYPE_PREFIX_BOOL:
        return "bool"      # 1 byte
    elif type_prefix == TYPE_PREFIX_STRING:
        return "string"    # len(4) + chars + null
    else:
        return "numeric"   # 4 bytes (default for 0x11 and others)


def get_value_size_from_descriptor(descriptor_type: int) -> str:
    """
    Determine value format based on descriptor type (for root property).
    Root properties have no Type prefix, so we use descriptor type.
    """
    if descriptor_type == DESCRIPTOR_BOOL:
        return "bool"
    elif descriptor_type == DESCRIPTOR_STRING:
        return "string"
    else:
        return "numeric"  # Complex, Pointer, etc. are all 4 bytes


def compute_type_prefix(descriptor_type: int) -> int:
    """
    Compute binary Type Prefix from descriptor type.

    From RE analysis of serializer functions:
    - FUN_01b11fb0 (Bool, type 0x00) writes Type Prefix 0x0E
    - FUN_01b12fa0 (Complex, type 0x07) writes Type Prefix 0x11
    - FUN_01b099a0 (Pointer, type 0x12) writes Type Prefix 0x11
    - FUN_01b12cf0 (String, type 0x1A) writes Type Prefix 0x19
    """
    TYPE_PREFIX_MAP = {
        DESCRIPTOR_BOOL: TYPE_PREFIX_BOOL,        # 0x00 → 0x0E
        DESCRIPTOR_COMPLEX: TYPE_PREFIX_NUMERIC,  # 0x07 → 0x11
        DESCRIPTOR_POINTER: TYPE_PREFIX_NUMERIC,  # 0x12 → 0x11
        DESCRIPTOR_STRING: TYPE_PREFIX_STRING,    # 0x1A → 0x19
    }
    return TYPE_PREFIX_MAP.get(descriptor_type, TYPE_PREFIX_NUMERIC)  # Default to Numeric


def parse_value(data: bytes, offset: int, value_format: str) -> tuple:
    """
    Parse a value based on its format.
    Returns (value, size_consumed, extra_fields).

    From RE analysis:
    - bool: 1 byte (FUN_01b11fb0 calls vtable+0x58)
    - numeric: 4 bytes (FUN_01b12fa0 calls vtable+0x84)
    - string: len(4) + chars + null (FUN_01b12cf0 calls vtable+0x48)
    """
    if value_format == "bool":
        return data[offset], 1, {}
    elif value_format == "string":
        str_len = struct.unpack_from('<I', data, offset)[0]
        string_data = data[offset + 4:offset + 4 + str_len]
        # Size: length field (4) + string bytes + null terminator (1)
        # Note: string_length is NOT preserved - it's computed from len(value) during serialization
        # (FUN_01b12cf0 → vtable+0x48 → FUN_01b49920 computes strlen)
        return string_data.decode('utf-8', errors='replace'), 4 + str_len + 1, {}
    else:  # numeric
        return struct.unpack_from('<I', data, offset)[0], 4, {}


def parse_section1(data: bytes) -> dict:
    """Parse Section 1 binary data."""
    result = {
        "container_hash": None,
        "root_property": None,
        "properties": [],
    }

    pos = 0

    # Zero prefix (10 bytes) - validate but don't store
    zero_prefix = data[pos:pos + ZERO_PREFIX_SIZE]
    if zero_prefix != b'\x00' * ZERO_PREFIX_SIZE:
        raise ValueError(f"Invalid zero prefix at offset 0: {zero_prefix.hex()}")
    pos += ZERO_PREFIX_SIZE

    # Container hash (4 bytes)
    result["container_hash"] = struct.unpack_from('<I', data, pos)[0]
    pos += 4

    # Container header (12 bytes = 3 uint32)
    # All three are block sizes from nested BeginBlock calls (RE verified via WinDbg)
    # These are skipped during parsing - they're computed during serialization
    pos += 12

    # Root property (HAS block size at 0x16, NO Type prefix)
    # WinDbg verified: mode is always 0, but root gets BeginBlock("Property") while
    # child properties skip it (via ctx+0x4e & 1 flag). Root skips Type prefix writing.
    # Format: Hash(4) + ClassID(4) + type_id(4) + PackedInfo(1) + Value(variable)
    root_hash = struct.unpack_from('<I', data, pos)[0]
    root_class_id = struct.unpack_from('<I', data, pos + 4)[0]
    root_type_id = struct.unpack_from('<I', data, pos + 8)[0]
    root_packed_info = data[pos + 12]
    root_descriptor_type = extract_descriptor_type(root_type_id)

    # Determine value format from descriptor type (no Type prefix for root)
    root_value_format = get_value_size_from_descriptor(root_descriptor_type)
    root_value, root_value_size, root_extra = parse_value(data, pos + 13, root_value_format)

    result["root_property"] = {
        "hash": root_hash,
        "class_id": root_class_id,
        "type_id": root_type_id,
        "packed_info": root_packed_info,
        "value": root_value,
        **root_extra
    }
    pos += 13 + root_value_size  # header (13 bytes) + value

    # Child properties (NO block size, WITH Type prefix)
    # WinDbg verified: children skip BeginBlock (ctx+0x4e & 1 flag) but write Type prefix
    while pos + 4 <= len(data):
        # Check for Dynamic Properties block (size=0, signals end of child properties)
        marker = struct.unpack_from('<I', data, pos)[0]
        if marker == DYNAMIC_PROPS_BLOCK_SIZE:
            pos += 4
            break

        # Parse property with Type prefix
        prop = parse_property(data, pos)
        if prop is None:
            break
        result["properties"].append(prop)
        pos += prop["_size"]

    # Validate we consumed all data
    if pos != len(data):
        raise ValueError(f"Unexpected trailing data: {len(data) - pos} bytes at offset 0x{pos:X}")

    return result


def parse_property(data: bytes, offset: int) -> dict:
    """
    Parse a single child property record WITH Type prefix.

    Child property format (from FUN_01b0d140 in mode 0):
      Type(4) + Hash(4) + ClassID(4) + type_id(4) + PackedInfo(1) + Value(variable)

    The Type prefix determines value format:
      0x0E → 1 byte (FUN_01b11fb0)
      0x11 → 4 bytes (FUN_01b12fa0)
      0x19 → string (FUN_01b12cf0)
    """
    # Minimum size: Type(4) + Hash(4) + ClassID(4) + type_id(4) + PackedInfo(1) = 17 bytes
    if offset + 17 > len(data):
        return None

    # Read header fields
    type_prefix = struct.unpack_from('<I', data, offset)[0]
    hash_val = struct.unpack_from('<I', data, offset + 4)[0]
    class_id = struct.unpack_from('<I', data, offset + 8)[0]
    type_id = struct.unpack_from('<I', data, offset + 12)[0]
    packed_info = data[offset + 16]

    # Extract descriptor type from type_id for reference
    descriptor_type = extract_descriptor_type(type_id)

    # Determine value format from Type prefix (NOT descriptor type!)
    value_format = get_value_size_from_type_prefix(type_prefix)
    value, value_size, extra_fields = parse_value(data, offset + 17, value_format)

    prop = {
        "hash": hash_val,
        "class_id": class_id,
        "type_id": type_id,
        "packed_info": packed_info,
        "value": value,
        "_size": 17 + value_size,  # header + value
        **extra_fields
    }

    return prop


def serialize_value(value, value_format: str) -> bytes:
    """
    Serialize a value based on its format.

    From RE analysis:
    - bool: 1 byte (FUN_01b11fb0 calls vtable+0x58)
    - numeric: 4 bytes (FUN_01b12fa0 calls vtable+0x84)
    - string: len(4) + chars + null (FUN_01b12cf0 calls vtable+0x48)

    String length is COMPUTED via strlen (FUN_01b12cf0 → vtable+0x48 → FUN_01b49920).
    """
    output = bytearray()

    if value_format == "bool":
        output.append(value)
    elif value_format == "string":
        string_bytes = value.encode('utf-8')
        # String length computed from len(string) per FUN_01b49920 strlen loop
        output.extend(struct.pack('<I', len(string_bytes)))
        output.extend(string_bytes)
        output.append(0)  # null terminator
    else:  # numeric
        output.extend(struct.pack('<I', value))

    return bytes(output)


def compute_value_size(value, value_format: str) -> int:
    """
    Compute serialized size of a value.
    From RE: bool=1 byte, numeric=4 bytes, string=len(4)+chars+null(1)

    String length is COMPUTED via strlen (FUN_01b12cf0 → vtable+0x48 → FUN_01b49920).
    """
    if value_format == "bool":
        return 1
    elif value_format == "string":
        # String length computed from len(string) per FUN_01b49920 strlen loop
        string_bytes = value.encode('utf-8')
        return 4 + len(string_bytes) + 1  # length field + chars + null
    else:  # numeric
        return 4


def serialize_section1(json_data: dict) -> bytes:
    """
    Serialize JSON structure back to Section 1 binary.

    From RE analysis of FUN_005e3560 + WinDbg verification:
    - Zero prefix (from LZSS decompression layer)
    - Container hash and block sizes (Object, Properties, Root)
    - Root property (HAS block size, NO Type prefix)
    - Child properties (NO block size, WITH Type prefix)
    - Dynamic Properties block (size=0, empty)

    Block sizes are COMPUTED following BeginBlock/EndBlock logic from RE:
    - root_block_size = root property content (13 bytes header + value)
    - properties_block_size = root_block_size_field(4) + root_content + child_properties
    - object_block_size = properties_block_size_field(4) + properties_block_size + dynamic_props(4)
    """
    # First, compute all sizes (following BeginBlock/EndBlock from FUN_01b48890/920)
    r = json_data["root_property"]

    # Root property content size: Hash(4) + ClassID(4) + type_id(4) + PackedInfo(1) + Value
    # Extract descriptor type from type_id: (type_id >> 16) & 0x3F
    root_descriptor_type = extract_descriptor_type(r["type_id"])
    root_value_format = get_value_size_from_descriptor(root_descriptor_type)
    root_value_size = compute_value_size(r["value"], root_value_format)
    root_block_size = 13 + root_value_size  # 13 = Hash(4) + ClassID(4) + type_id(4) + PackedInfo(1)

    # Child properties total size
    child_total = 0
    for prop in json_data["properties"]:
        # Type(4) + Hash(4) + ClassID(4) + type_id(4) + PackedInfo(1) = 17 bytes header
        # Compute value format from descriptor type (extracted from type_id)
        desc_type = extract_descriptor_type(prop["type_id"])
        value_format = get_value_size_from_descriptor(desc_type)
        value_size = compute_value_size(prop["value"], value_format)
        child_total += 17 + value_size

    # Properties block: root_block_size_field(4) + root_content + children
    # From FUN_01b08ce0: BeginBlock("Properties") then BeginBlock("Property") for root
    properties_block_size = 4 + root_block_size + child_total

    # Object block: properties_block_size_field(4) + properties_content + dynamic_props_block(4)
    # From FUN_01b08ce0/FUN_01b0d0c0: BeginBlock("Object"), then Properties, then Dynamic Properties
    object_block_size = 4 + properties_block_size + 4

    # Now serialize
    output = bytearray()

    # Zero prefix (10 bytes)
    output.extend(b'\x00' * ZERO_PREFIX_SIZE)

    # Container hash (4 bytes)
    output.extend(struct.pack('<I', json_data["container_hash"]))

    # Container header - COMPUTED block sizes (not preserved)
    # From BeginBlock calls in FUN_01b08ce0 and FUN_01b0d140
    output.extend(struct.pack('<I', object_block_size))      # BeginBlock("Object")
    output.extend(struct.pack('<I', properties_block_size))  # BeginBlock("Properties")
    output.extend(struct.pack('<I', root_block_size))        # BeginBlock("Property") for root

    # Root property (NO Type prefix - block size already written above)
    # WinDbg: root gets BeginBlock but skips Type prefix writing
    # Format: Hash(4) + ClassID(4) + type_id(4) + PackedInfo(1) + Value(variable)
    output.extend(struct.pack('<I', r["hash"]))
    output.extend(struct.pack('<I', r["class_id"]))
    output.extend(struct.pack('<I', r["type_id"]))
    output.append(PACKED_INFO)  # Computed: 0x0B (see constant definition)
    output.extend(serialize_value(r["value"], root_value_format))

    # Child properties (WITH Type prefix, NO block size)
    # WinDbg: children skip BeginBlock (ctx+0x4e & 1) but write Type prefix
    for prop in json_data["properties"]:
        # Compute Type prefix from descriptor type (extracted from type_id)
        # From RE: descriptor_type = (type_id >> 16) & 0x3F
        descriptor_type = extract_descriptor_type(prop["type_id"])
        type_prefix = compute_type_prefix(descriptor_type)

        # Write header: Type(4) + Hash(4) + ClassID(4) + type_id(4) + PackedInfo(1)
        output.extend(struct.pack('<I', type_prefix))
        output.extend(struct.pack('<I', prop["hash"]))
        output.extend(struct.pack('<I', prop["class_id"]))
        output.extend(struct.pack('<I', prop["type_id"]))
        output.append(PACKED_INFO)  # Computed: 0x0B (see constant definition)

        # Value format derived from descriptor type
        value_format = get_value_size_from_descriptor(descriptor_type)
        output.extend(serialize_value(prop["value"], value_format))

    # Dynamic Properties block size (0 = empty block)
    # From FUN_01b0d0c0: BeginBlock("Dynamic Properties") immediately followed by EndBlock
    output.extend(struct.pack('<I', DYNAMIC_PROPS_BLOCK_SIZE))

    return bytes(output)


def format_json(data: dict) -> dict:
    """Format data for JSON output with hex strings for hashes."""
    def format_hash(v):
        return f"0x{v:08X}"

    def format_type(type_code):
        return TYPE_NAMES.get(type_code, f"0x{type_code:02X}")

    # Format root property
    root = data["root_property"]
    formatted_root = {
        "hash": format_hash(root["hash"]),
        "class_id": format_hash(root["class_id"]),
        "type_id": format_hash(root["type_id"]),
        "packed_info": f"0x{root['packed_info']:02X}",
        "value": root["value"],
    }

    result = {
        "container_hash": format_hash(data["container_hash"]),
        "root_property": formatted_root,
        "properties": []
    }

    # Format child properties
    for prop in data["properties"]:
        p = {
            "hash": format_hash(prop["hash"]),
            "class_id": format_hash(prop["class_id"]),
            "type_id": format_hash(prop["type_id"]),
            "packed_info": f"0x{prop['packed_info']:02X}",
            "value": prop["value"],
        }
        result["properties"].append(p)

    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: python section1_parser.py <input.bin> [output.json] [reconstructed.bin]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_json = sys.argv[2] if len(sys.argv) > 2 else "section1_output.json"
    output_bin = sys.argv[3] if len(sys.argv) > 3 else "section1_reconstructed.bin"

    with open(input_file, 'rb') as f:
        original_data = f.read()

    print(f"Input: {input_file} ({len(original_data)} bytes)")

    parsed = parse_section1(original_data)

    # Print summary
    print(f"\nContainer hash: 0x{parsed['container_hash']:08X}")

    # Root property (no Type prefix)
    r = parsed["root_property"]
    dtype = TYPE_NAMES.get(extract_descriptor_type(r["type_id"]), f"0x{extract_descriptor_type(r['type_id']):02X}")
    print(f"\nRoot property (no Type prefix):")
    print(f"  hash=0x{r['hash']:08X} descriptor={dtype} value={r['value']}")

    # Child properties
    print(f"\nChild properties: {len(parsed['properties'])}")
    for i, prop in enumerate(parsed['properties']):
        descriptor_type = extract_descriptor_type(prop["type_id"])
        descriptor_name = TYPE_NAMES.get(descriptor_type, f"0x{descriptor_type:02X}")

        if descriptor_type == DESCRIPTOR_STRING:
            print(f"  [{i:2d}] desc={descriptor_name:8s} hash=0x{prop['hash']:08X} value=\"{prop['value']}\"")
        else:
            val = prop['value']
            val_str = f"0x{val:X}" if isinstance(val, int) and val > 255 else str(val)
            cid = f" class_id=0x{prop['class_id']:08X}" if prop['class_id'] != 0 else ""
            print(f"  [{i:2d}] desc={descriptor_name:8s} hash=0x{prop['hash']:08X}{cid} value={val_str}")

    # Save formatted JSON
    formatted = format_json(parsed)
    with open(output_json, 'w') as f:
        json.dump(formatted, f, indent=2)
    print(f"\nJSON: {output_json}")

    # Reconstruct and verify
    reconstructed = serialize_section1(parsed)
    with open(output_bin, 'wb') as f:
        f.write(reconstructed)
    print(f"Binary: {output_bin}")

    if original_data == reconstructed:
        print("\n*** SUCCESS: 1:1 match ***")
    else:
        print(f"\n*** MISMATCH ***")
        print(f"Original: {len(original_data)} bytes")
        print(f"Reconstructed: {len(reconstructed)} bytes")
        for i in range(min(len(original_data), len(reconstructed))):
            if original_data[i] != reconstructed[i]:
                print(f"First diff at 0x{i:04X}: orig=0x{original_data[i]:02X} vs recon=0x{reconstructed[i]:02X}")
                break


if __name__ == "__main__":
    main()
