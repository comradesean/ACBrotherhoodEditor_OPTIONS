# SAV Blocks 3 and 5 Compact Format Specification

## Overview

Blocks 3 and 5 in AC Brotherhood SAV files use a compact binary format for serializing game object properties. Unlike Blocks 2 and 4 which use LZSS compression with raw type hashes, these blocks use table ID lookup for type resolution, resulting in more compact property references.

## Block Characteristics

| Property | Block 3 | Block 5 |
|----------|---------|---------|
| Compression | Uncompressed | Uncompressed |
| Size | 7,972 bytes | 6,266 bytes |
| First TABLE_REF offset | 0x004E | 0x0113 |
| Preamble size | 70 bytes | 267 bytes |
| TABLE_REF count | 80 | 10 |
| Primary table | 0x5E (63 refs) | Distributed |

## Block Header (8 bytes)

Both blocks share the same header structure:

```
Offset  Size  Description
0x00    1     Version (always 0x01)
0x01    3     Data size (little-endian 24-bit)
0x04    4     Flags (always 0x00800000)
```

### Header Examples

```
Block 3: 01 39 0E 00 00 00 80 00
         |  |        |
         |  |        +- Flags: 0x00800000
         |  +---------- Size: 0x0E39 (3641)
         +------------- Version: 0x01

Block 5: 01 57 07 00 00 00 80 00
         |  |        |
         |  |        +- Flags: 0x00800000
         |  +---------- Size: 0x0757 (1879)
         +------------- Version: 0x01
```

Note: The size field does not directly correspond to block size. Its exact meaning is unclear but may indicate payload size or entry count.

## Preamble Region

Following the 8-byte header, each block has a preamble region that extends until the first TABLE_REF (0x0803) pattern. The preamble contains:

- Object descriptors
- Type references (including PropertyReference 0x0984415E)
- Initial value definitions

### Block 3 Preamble (70 bytes, 0x08-0x4E)

```
0008: 00 3d 64 0f e1 20 22 6c 9f 0e 00 c0 00 b6 6c a5
0018: 72 00 a1 00 24 0b 01 11 cd de 4c 09 b8 f2 00 00
0028: 11 c1 05 e3 a9 bf ce 90 00 6a 07 11 01 00 08 0b
0038: 50 79 1e 32 56 07 2a 4e 03 61 2e 41 6f 6a 5b ef
0048: 01 87 d8 ad b1 60
```

### Block 5 Preamble (267 bytes, 0x08-0x113)

Contains PropertyReference hash (0x0984415E) at offset 0x002D, along with multiple VARINT_1405 and VALUE prefixes.

## Compact Format Prefixes

The data region uses 2-byte prefixes to indicate data types:

### Primary Prefixes

| Prefix | Name | Description | Block 3 Count | Block 5 Count |
|--------|------|-------------|---------------|---------------|
| 0x0803 | TABLE_REF | Table ID + Property Index reference | 80 | 10 |
| 0x1405 | VARINT | Variable-length integer prefix | 83 | 58 |
| 0x0502 | FIXED32 | 32-bit fixed value | 75 | 66 |
| 0x1500 | VALUE_15 | 32-bit value (6 bytes total) | 44 | 11 |
| 0x1200 | VALUE_12 | 32-bit value (6 bytes total) | 47 | 34 |

### Secondary Prefixes

| Prefix | Name | Block 3 Count | Block 5 Count |
|--------|------|---------------|---------------|
| 0x1C04 | PREFIX_1C04 | 62 | 1 |
| 0x173C | PREFIX_173C | 32 | 32 |
| 0x1907 | PREFIX_1907 | 31 | 34 |
| 0x16E1 | PREFIX_16E1 | 22 | 21 |
| 0x1809 | PREFIX_1809 | 19 | 0 |
| 0x0C18 | EXTENDED | 14 | 1 |
| 0x1006 | PREFIX_1006 | 11 | 2 |

## TABLE_REF Format (0x0803)

The most important prefix for understanding the compact format:

```
08 03 [table_id] [prop_id]

08 03 = Prefix (field 1, varint + value 3)
table_id = 1-byte table ID (maps to type hash)
prop_id = 1-byte property index within the type
```

### Example

```
08 03 5E B6 = TABLE_REF(table=0x5E, prop=0xB6)
```

This references property 0xB6 (182) of the type mapped to table ID 0x5E (94).

## Table ID Catalog

### Block 3 Table IDs

| Table ID | Decimal | References | Property Range | Unique Props |
|----------|---------|------------|----------------|--------------|
| 0x08 | 8 | 1 | 0x00 | 1 |
| 0x14 | 20 | 3 | 0x05-0xC2 | 2 |
| 0x17 | 23 | 2 | 0x3C | 1 |
| 0x19 | 25 | 2 | 0x07 | 1 |
| 0x3B | 59 | 1 | 0xC9 | 1 |
| 0x5B | 91 | 4 | 0x03-0xB6 | 4 |
| 0x5D | 93 | 1 | 0xAA | 1 |
| 0x5E | 94 | 63 | 0x01-0xD9 | 42 |
| 0xDB | 219 | 2 | 0x17 | 1 |
| 0xFB | 251 | 1 | 0x0B | 1 |

### Block 5 Table IDs

| Table ID | Decimal | References | Property Range | Unique Props |
|----------|---------|------------|----------------|--------------|
| 0x14 | 20 | 3 | 0x05 | 1 |
| 0x17 | 23 | 2 | 0x3C | 1 |
| 0x19 | 25 | 2 | 0x07 | 1 |
| 0x95 | 149 | 1 | 0x14 | 1 |
| 0xDB | 219 | 1 | 0x17 | 1 |
| 0xE1 | 225 | 1 | 0x19 | 1 |

### Known Table ID Mappings

From binary analysis of ACBSP.exe (see type_table_analysis.json):

| Table ID | Type Hash | Type Name | Props |
|----------|-----------|-----------|-------|
| 0x08 (8) | 0xC9A5839D | CompactType_08 | 22 |
| 0x0B (11) | 0x82A2AEE0 | CompactType_0B | 22 |
| 0x16 (22) | 0x2DAD13E3 | PlayerOptionsElement | - |
| 0x20 (32) | 0xFBB63E47 | World | 14 |
| 0x38 (56) | 0xFA1AA549 | CompactType_38 | 22 |
| 0x3B (59) | 0xFC6EDE2A | CompactType_3B | 22 |
| 0x4F (79) | 0xF49BFD86 | CompactType_4F | 22 |
| 0x5B (91) | 0xC8761736 | CompactType_5B | 22 |
| **0x5E (94)** | **0x0DEBED19** | **CompactType_5E** | **22** |
| 0x5F (95) | 0x938F78BA | CompactType_5F | 22 |

Note: Compact types all inherit from CommonParent (0x7E42F87F) and have 22 properties each.

## Marker Bytes

Single-byte markers appear between TABLE_REF sequences to indicate values or flags:

| Marker | Block 3 Count | Block 5 Count | Likely Meaning |
|--------|---------------|---------------|----------------|
| 0x6D | 41 | 32 | Boolean TRUE or value 1 |
| 0xDB | 35 | 28 | Boolean FALSE or value 0 |
| 0xCD | 19 | 11 | Unknown flag/separator |

### Marker Pattern

Markers typically follow immediately after a TABLE_REF:

```
08 03 5E C1 DB 08 03 5E CA
           ^^ MARKER_DB after prop 0xC1

08 03 5E 96 6D 08 03 5E BB
           ^^ MARKER_6D after prop 0x96
```

## Table 0x5E Deep Analysis

Table 0x5E is the dominant type in Block 3 with 63 references across 42 unique properties:

### Property Groups

| Range | Count | Description |
|-------|-------|-------------|
| 0x01, 0x05 | 2 | Early properties |
| 0x34-0x35 | 2 | Mid-range group 1 |
| 0x37-0x38, 0x3A | 3 | Mid-range group 2 |
| 0x6C | 1 | Isolated property |
| 0x90, 0x96 | 2 | High-range start |
| 0x9D-0x9E | 2 | Status group |
| 0xA0-0xAD | 12 | Primary data block |
| 0xAF | 1 | Gap property |
| 0xB2-0xB8 | 7 | Secondary data block |
| 0xBB, 0xBE, 0xC1, 0xC4, 0xCA | 5 | Flags/config |
| 0xD0, 0xD3, 0xD6, 0xD9 | 4 | End group |

## Value Prefixes

### VALUE_1500 Format

```
15 00 [4 bytes little-endian value]

Example: 15 00 08 A5 10 A6 = value 0xA610A508
```

Total: 6 bytes

### VALUE_1200 Format

```
12 00 [4 bytes little-endian value]

Example: 12 00 05 E9 EA E2 = value 0xE2EAE905
```

Total: 6 bytes

Note: The first byte after prefix (0x08 or 0x05) appears to be part of the encoding, not a separate field.

## Data Stream Structure

After the preamble, the data region consists of interleaved:

1. **Property References**: TABLE_REF patterns pointing to specific type properties
2. **Value Markers**: Single bytes indicating boolean/flag values
3. **Prefixed Values**: 2-byte prefix + data for typed values
4. **Raw Data Bytes**: Additional value data between structured entries

### Example Trace (Block 3, offset 0x4E)

```
004E: TABLE_REF(table=0x5B, prop=0x8A)
0052: TABLE_REF(table=0x5E, prop=0xB6)
0056: BYTE(0x8D)
0057: TABLE_REF(table=0x5E, prop=0x90)
005B: TABLE_REF(table=0x5E, prop=0x96)
005F: MARKER_6D
0060: TABLE_REF(table=0x5E, prop=0xBB)
0064: TABLE_REF(table=0x5E, prop=0xBE)
0068: TABLE_REF(table=0x5E, prop=0xC1)
006C: MARKER_DB
006D: TABLE_REF(table=0x5E, prop=0xCA)
```

## Block Content Hypothesis

Based on structural analysis:

### Block 3 (7,972 bytes)

- Heavy use of Table 0x5E suggests a large game object with many properties
- High TABLE_REF density indicates complex nested object structure
- PREFIX_1C04 prevalence (62 occurrences) suggests specific data type handling
- Likely contains: Mission state, inventory, or world object data

### Block 5 (6,266 bytes)

- Fewer TABLE_REFs suggests more direct value storage
- Larger preamble (267 bytes) contains initialization data
- Balanced VARINT/FIXED32 usage suggests numeric data
- Likely contains: Player stats, game progress, or configuration data

## Comparison to Blocks 2/4

| Aspect | Blocks 2/4 | Blocks 3/5 |
|--------|------------|------------|
| Compression | LZSS compressed | Uncompressed |
| Type encoding | Raw 4-byte hashes | 1-byte table IDs |
| Property encoding | Offset-based | Index-based |
| Size | 32KB each (decompressed) | 7.9KB / 6.3KB |

## Implementation Notes

### Reading TABLE_REF

```python
def read_table_ref(data, pos):
    if data[pos] == 0x08 and data[pos+1] == 0x03:
        table_id = data[pos+2]
        prop_id = data[pos+3]
        return (table_id, prop_id), pos+4
    return None, pos
```

### Reading VALUE_1500

```python
def read_value_1500(data, pos):
    if data[pos] == 0x15 and data[pos+1] == 0x00:
        value = struct.unpack('<I', data[pos+2:pos+6])[0]
        return value, pos+6
    return None, pos
```

## Known Type Hashes (Reference)

From `sav_parser.py` TYPE_HASHES dictionary:

| Hash | Type Name |
|------|-----------|
| 0xFBB63E47 | World |
| 0x2DAD13E3 | PlayerOptionsElement |
| 0x0984415E | PropertyReference |
| 0xA1A85298 | PhysicalInventoryItem |
| 0xBDBE3B52 | SaveGame |
| 0x5FDACBA0 | SaveGameDataObject |

## Future Research

1. **Table ID Resolution**: Map remaining table IDs (0x5E, 0x5B, etc.) to type hashes via Ghidra analysis
2. **Prefix Semantics**: Determine exact meaning of PREFIX_1C04, PREFIX_173C, etc.
3. **Preamble Structure**: Decode the preamble format for object initialization
4. **Value Encoding**: Understand the full protobuf-like wire format being used
5. **Cross-Block References**: Investigate how Blocks 3/5 relate to Blocks 2/4

## File Locations

- Block 3 test file: `/tmp/compact_analysis/sav_block3_raw.bin`
- Block 5 test file: `/tmp/compact_analysis/sav_block5_raw.bin`
- Parser implementation: `/mnt/f/ClaudeHole/assassinscreedsave/sav_parser.py`
