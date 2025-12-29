# Block 2 Game State Structure

## Overview

Block 2 is the main game state block in Assassin's Creed Brotherhood SAV files. It is LZSS compressed and decompresses to exactly 32,768 bytes (32 KB).

**SAV File Location:**
- Header offset: 0x00D9 (44 bytes)
- Compressed data offset: 0x0105
- Typical compressed size: ~1,854 bytes

**Header Markers:**
- Field2: 0x00000001
- Field3: 0x00CAFE00 (distinguishes from Block 1's 0x000000CD)

---

## Type Hash Summary

Block 2 contains the following serialized types:

| Type | Hash | Count | Offset Range |
|------|------|-------|--------------|
| PropertyReference | 0x0984415E | 21 | 0x40E1 - 0x45F5 |
| MissionSaveData | 0x5ED7B213 | 3 | 0x00B1 - 0x00CE |
| SaveGameDataObject | 0x5FDACBA0 | 2 | 0x00DE - 0x00E2 |
| RewardFault | 0x12DE6C4C | 2 | 0x0196 - 0x019A |
| World | 0xFBB63E47 | 2 | 0x0212 - 0x0216 |

---

## Block Layout

```
0x0000 - 0x0015  Header (22 bytes)
0x0016 - 0x0097  Root object intro section
0x0098 - 0x00B0  Pre-MissionSaveData section
0x00B1 - 0x00CD  MissionSaveData entries (3 instances)
0x00CE - 0x00D9  Bridge section
0x00DA - 0x0127  SaveGameDataObject region
0x0128 - 0x0191  Intermediate region
0x0192 - 0x01B3  RewardFault region
0x01B4 - 0x020D  Post RewardFault section
0x020E - 0x03E7  World data (2 World instances)
0x03E8 - 0x40D7  Large data array (repeating entries)
0x40D8 - 0x460F  PropertyReference array (21 entries)
0x4610 - 0x4B85  Intermediate data region
0x4B86 - 0x7FFF  Large repeating entries region
```

---

## Header Section (0x0000 - 0x0015)

| Offset | Size | Value | Description |
|--------|------|-------|-------------|
| 0x00 | 10 | `00 00 00 00 00 00 00 00 00 00` | Leading zeros (padding) |
| 0x0A | 4 | `0x94D6F8F1` | Root type hash |
| 0x0E | 4 | `0x0003F208` | Size/offset value 1 (258,568) |
| 0x12 | 4 | `0x0003F1B8` | Size/offset value 2 (258,488) |

---

## Serialization Pattern

Type entries follow a consistent pattern:

```
[prefix] 00 00 00 [type_hash] [type_hash] 00 00 [flags] [data...]
```

**Prefix values:**
- `0x11`: Type reference (most common)
- `0x12`: Secondary type reference
- `0x0E`: Property value
- `0x0B`: Property marker
- `0x17`: Extended property

**Double-hash pattern:**
Types are serialized with the hash appearing twice:
```
11 00 00 00 [hash4] [hash4] 00 00 [flags2] ...
```

This pattern allows the deserializer to verify type consistency.

---

## MissionSaveData (0x5ED7B213)

**Purpose:** Stores mission-specific save data, including checkpoint information and mission state.

**Locations:**
- 0x00B1 (first occurrence, hash repeated at 0x00B5)
- 0x00CE (third occurrence)

**Entry Structure:**
```
Offset  Content
0x00    13 b2 d7 5e  - MissionSaveData hash (LE)
0x04    13 b2 d7 5e  - MissionSaveData hash repeated
0x08    00 00        - Flags
0x0A    1d 0a        - Entry type marker
0x0C    0b           - Subtype marker
0x0D    01           - Boolean/count
0x0E    01 00 00 00  - Data field
        ...          - Additional mission data (zeros in fresh save)
```

**Sample (0x00B1):**
```
0x00B1: 13 b2 d7 5e 13 b2 d7 5e 00 00 1d 0a 0b 01 01 00
0x00C1: 00 00 00 00 00 00 00 00 00 00 00 00 00 13 b2 d7
```

---

## SaveGameDataObject (0x5FDACBA0)

**Purpose:** Container for save game data objects, wrapping mission data and player state.

**Locations:**
- 0x00DE (first occurrence)
- 0x00E2 (second occurrence, hash repeated)

**Entry Structure:**
```
Offset  Content
0x00    a0 cb da 5f  - SaveGameDataObject hash (LE)
0x04    a0 cb da 5f  - Hash repeated
0x08    00 00        - Flags
0x0A    12 00        - Entry type marker
0x0C    0b           - Property marker
0x0D    27 ec 79 8a  - Reference ID
        ...          - Referenced data
```

**Sample (0x00DE):**
```
0x00DE: a0 cb da 5f a0 cb da 5f 00 00 12 00 0b 27 ec 79
0x00EE: 8a 11 00 00 00 4c b5 e5 44 00 00 00 00 00 00 07
```

---

## RewardFault (0x12DE6C4C)

**Purpose:** Tracks Ubisoft Connect / Uplay reward status and fault states.

**Locations:**
- 0x0196 (first occurrence)
- 0x019A (second occurrence, hash repeated)

**Entry Structure:**
```
Offset  Content
0x00    4c 6c de 12  - RewardFault hash (LE)
0x04    4c 6c de 12  - Hash repeated
0x08    00 00        - Flags
0x0A    9d 0a        - Entry type marker
0x0C    0b 01        - Property marker with count
0x0E    00 00 00 00  - Fault state (zeros = no faults)
        ...          - Additional fault tracking data
```

**Sample (0x0196):**
```
0x0196: 4c 6c de 12 4c 6c de 12 00 00 9d 0a 0b 01 00 00
0x01A6: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 56 00
```

---

## World (0xFBB63E47)

**Purpose:** Main world object containing map state, player position references, and world properties.

**Locations:**
- 0x0212 (first occurrence)
- 0x0216 (second occurrence, hash repeated)

**Entry Structure:**
```
Offset  Content
0x00    47 3e b6 fb  - World hash (LE)
0x04    47 3e b6 fb  - Hash repeated
0x08    00 00        - Flags
0x0A    12 00        - Entry type marker
0x0C    0b           - Property marker
0x0D    63 47 ac 8d  - World instance ID
        ...          - World properties
```

**World Data Region (0x020E - 0x03E7):**
The World entries span approximately 474 bytes and contain nested property references including:
- Property hash 0x11854ADA
- Property hash 0x7ACF45C6
- Property hash 0xF44B5195
- Property hash 0x5DEBF8DE
- Property hash 0xD92D49F7
- Property hash 0xD4C878C7

**Sample (0x0212):**
```
0x0212: 47 3e b6 fb 47 3e b6 fb 00 00 12 00 0b 63 47 ac
0x0222: 8d de 00 00 00 90 dd c7 8a 6d f7 9a 1f 00 00 16
```

---

## PropertyReference Array (0x0984415E)

**Purpose:** Array of property references used for binding game values.

**Location:** 0x40D8 - 0x460F
**Count:** 21 entries
**Entry Size:** 65 bytes (0x41)

**Pattern:**
Each entry has identical structure with PropertyReference hash at offset +9:
```
Offset  Content
0x00    00           - Padding
0x01    11 00 00 00  - Prefix marker
0x05    1f 5f 60 af  - Unknown hash
0x09    5e 41 84 09  - PropertyReference hash (LE)
0x0D    00 00        - Flags
0x0F    12 00        - Type marker
0x11    0b           - Property marker
0x12    00 00 00 00  - Reference ID (zeros)
        ...          - 18 bytes of zeros
0x28    62 1c 6a 63  - Second reference
0x2C    2f 00 00 00  - Size/count
0x30    27 00 00 00  - Data value
```

**Spacing:** Exactly 65 bytes between each PropertyReference hash occurrence.

---

## Large Data Array (0x03E8 - 0x40D7)

**Purpose:** Array of identical slot entries, likely representing game object states or inventory slots.

**Size:** 15,600 bytes (15.2 KB)
**Entry Pattern:** Repeating 98-byte entries

**Common Property Hashes in Array:**
- 0x9BD7FCBE (appears at start of each entry)
- 0xF977547D
- 0x75758A0E
- 0x768CAE23
- 0x309E9CEF

**Entry Structure (98 bytes):**
```
0x00    [5 bytes]  - Entry header
0x05    be fc d7 9b 50  - Hash prefix + size
0x0A    00 00 00       - Padding
0x0D    48 00 00 00    - Size (72)
0x11    0e 00 00 00    - Property count
0x15    7d 54 77 f9    - Property hash 1
0x19    00 00 00 00    - Value (zeros)
0x1D    00 00          - Padding
0x1F    43 24          - Marker
0x21    0b 00          - Property marker
0x23    0e 00 00 00    - Next property
0x27    0e 8a 75 75    - Property hash 2
        ...            - Additional properties
```

Most entries contain zeros, indicating uninitialized/empty slots.

---

## Large Repeating Entries (0x4B86 - 0x7FFF)

**Purpose:** Array of game entity entries with consistent structure.

**Size:** 13,433 bytes (13.1 KB)
**Entry Spacing:** Alternating 57/47 bytes (104 bytes per pair)

**Common Hashes:**
- 0x5B6A6F41 (130 occurrences) - Entity type
- 0xCEBFA9E3 (129 occurrences) - Property type
- 0x72A56CB6 (129 occurrences) - Additional property

**Entry Structure:**
```
11 00 00 00 41 6f 6a 5b  - Type marker + hash
00 00 00 00 00 00 07 00  - Flags + property count
0b [id]                  - Property marker + ID
0e 00 00 00 b6 6c a5 72  - Property entry
00 00 00 00 00 00 00 00  - Value
0b 01                    - Property marker
0e 00 00 00 cd de 09 b8  - Second property
00 00 00 00 00 00 00 00  - Value
0b 00                    - Property marker
11 00 00 00 e3 a9 bf ce  - Nested type
00 00 00 00 00 00 07 00  - Flags
0b 00 00 00 00           - Empty property
...                      - Padding zeros
```

---

## Hash Catalog

### Type Hashes (Prefix 0x11)

| Hash | Count | Description |
|------|-------|-------------|
| 0x5B6A6F41 | 130 | Entity type |
| 0xCEBFA9E3 | 129 | Property container |
| 0xAF605F1F | 21 | PropertyReference related |
| 0x7ACF45C6 | 2 | World property |
| 0xF44B5195 | 2 | World property |
| 0x5DEBF8DE | 2 | World property |
| 0xD4C878C7 | 2 | World property |
| 0xFBB63E47 | 1 | World |
| 0x5FDACBA0 | 1 | SaveGameDataObject |
| 0x44E5B54C | 1 | Unknown |
| 0xBF4C2013 | 1 | Unknown |
| 0xAC016BC1 | 1 | Unknown |
| 0xE38B5102 | 1 | Unknown |
| 0x2179DAE4 | 1 | Unknown |

### Property Hashes (Prefix 0x0E)

| Hash | Count | Description |
|------|-------|-------------|
| 0x309E9CEF | 157 | Array element property |
| 0x75758A0E | 157 | Array element property |
| 0x768CAE23 | 157 | Array element property |
| 0x72A56CB6 | 129 | Entity property |
| 0x11854ADA | 2 | World-related |
| 0x11A757F6 | 2 | World-related |
| 0x000C0C40 | 2 | Value property |
| 0x2F4ACE81 | 2 | Value property |

---

## Identified Game Values

### Potential Value Locations

Block 2 contains mostly structured data with type hashes rather than raw game values. Game progress values are likely encoded within:

1. **World Section (0x020E - 0x03E7):** May contain player position and map state
2. **Large Data Array (0x03E8 - 0x40D7):** 157 slot entries for collectibles/objectives
3. **Entity Array (0x4B86 - 0x7FFF):** ~130 entity entries for NPCs/objects

### Note on Value Editing

Direct editing of Block 2 values is complex due to:
- Hash-based type system requiring correct type markers
- Nested structure with cross-references
- Variable-length encodings

For simple value editing (money, health), check Block 4 which may contain more accessible game state data.

---

## Comparison with Other Blocks

| Block | Purpose | Format | Size |
|-------|---------|--------|------|
| Block 1 | Player Profile | LZSS compressed | 283 bytes |
| **Block 2** | **Game State** | **LZSS compressed** | **32,768 bytes** |
| Block 3 | Compact data | Uncompressed | 7,972 bytes |
| Block 4 | Extended state | LZSS compressed | 32,768 bytes |
| Block 5 | Compact data | Uncompressed | 6,266 bytes |

---

## Technical Notes

1. **Double-hash verification:** All type entries use a double-hash pattern where the same 4-byte hash appears twice consecutively, followed by 2 bytes of flags.

2. **Little-endian encoding:** All multi-byte values use little-endian byte order.

3. **Property nesting:** Objects contain nested properties, each prefixed with type/count markers.

4. **Sparse arrays:** Most array slots contain zeros, indicating uninitialized state (early game save).

5. **Fixed entry sizes:** PropertyReference entries are exactly 65 bytes; entity entries alternate between 57/47 bytes.

---

## File Generation

This document was generated by analyzing:
- File: `/tmp/block2_analysis/sav_block2_decompressed.bin`
- Original: `ACBROTHERHOODSAVEGAME0.SAV`
- Block 2 compressed size: 1,854 bytes
- Block 2 decompressed size: 32,768 bytes
