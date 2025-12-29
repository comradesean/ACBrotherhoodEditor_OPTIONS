# SAV Blocks Overview

Quick reference for the 5-block structure of AC Brotherhood SAV files.

---

## Block Summary

| Block | Format | Compressed | Decompressed | Primary Content |
|-------|--------|------------|--------------|-----------------|
| 1 | LZSS + Header | ~173 bytes | 283 bytes | SaveGame root object |
| 2 | LZSS + Header | ~1,854 bytes | 32,768 bytes | Game state, missions, rewards |
| 3 | Raw | 7,972 bytes | 7,972 bytes | World compact data |
| 4 | LZSS (no header) | ~2,150 bytes | 32,768 bytes | Inventory (364 items) |
| 5 | Raw | 6,266 bytes | 6,266 bytes | Additional compact data |

---

## Cross-Block Relationship Diagram

```
+------------------+
|     Block 1      |
|   SaveGame Root  |
| (0xBDBE3B52)     |
+--------+---------+
         |
         | World reference (Object ID 0x8DAC4763)
         v
+------------------+          +------------------+
|     Block 2      |          |     Block 3      |
| Game State       |<-------->| World Compact    |
| (0x94D6F8F1)     |  World   | (0xFBB63E47)     |
| - MissionSaveData|  type    | TABLE_REF 0x5E   |
| - RewardFault    |  hash    +------------------+
| - PropertyRefs   |
+--------+---------+
         |
         | PhysicalInventoryItem type hash
         v
+------------------+          +------------------+
|     Block 4      |          |     Block 5      |
| Inventory Items  |          | Compact Data     |
| (0xA1A85298)     |          | TABLE_REF 0x4F   |
| 364 items total  |          |                  |
+------------------+          +------------------+
```

---

## Type Hash Cross-Reference

| Hash | Type Name | Block 1 | Block 2 | Block 3 | Block 4 | Block 5 |
|------|-----------|:-------:|:-------:|:-------:|:-------:|:-------:|
| 0xBDBE3B52 | SaveGame | ROOT | - | - | - | - |
| 0x94D6F8F1 | AssassinSaveGameData | - | ROOT | - | - | - |
| 0xFBB63E47 | World | ref | x2 | PRIMARY | - | - |
| 0x5FDACBA0 | SaveGameDataObject | ref | x2 | - | - | - |
| 0xA1A85298 | PhysicalInventoryItem | - | - | - | x364 | - |
| 0x0984415E | PropertyReference | - | x21 | - | x364 | - |
| 0x5ED7B213 | MissionSaveData | - | x3 | - | - | - |
| 0x12DE6C4C | RewardFault | - | x2 | - | - | - |

---

## Data Flow

```
SAVE OPERATION:

  SaveGame (Block 1)
      |
      +-- World ref -----> World object (Block 2, offset 0x021F)
      |                        |
      +-- DataObject ref       +-- Compact serialization --> Block 3
                               |
  Game State (Block 2)         |
      |                        |
      +-- MissionSaveData      |
      +-- RewardFault          |
      +-- PropertyRefs --------+
      +-- Entity arrays

  Inventory (Block 4) <-- 364 PhysicalInventoryItem entries
      |
      +-- Each item has PropertyReference

  Compact Data (Block 5) <-- Additional serialized state
```

---

## Compression Summary

| Block | Has Header | Header Marker | Compressed Size Field |
|-------|------------|---------------|----------------------|
| 1 | Yes (44 bytes) | 0x000000CD | Offset 0x20 |
| 2 | Yes (44 bytes) | 0x00CAFE00 | Offset 0x20 |
| 3 | No | N/A | Raw data |
| 4 | No | N/A | Calculated |
| 5 | No | N/A | Fixed 6,266 bytes |

---

## Compact Format Table IDs (Blocks 3 & 5)

| Table ID | Block 3 Refs | Block 5 Refs | Resolved Type |
|----------|--------------|--------------|---------------|
| 0x5E | 63 | - | CompactType_5E (0x0DEBED19) |
| 0x5B | 4 | - | CompactType_5B (0xC8761736) |
| 0x20 | - | - | World (0xFBB63E47) |
| 0x4F | - | 61 | CompactType_4F (0xF49BFD86) |
| 0x3B | 1 | - | CompactType_3B (0xFC6EDE2A) |

---

## Key Object IDs

| Object | ID | Found In |
|--------|-----|----------|
| World instance | 0x8DAC4763 | Block 1 (ref), Block 2 (data) |
| SaveGameDataObject | 0x00000000 | Block 1 (null ref) |

---

## Quick Navigation

| Topic | Document |
|-------|----------|
| SaveGame root structure | [BLOCK1_SAVEGAME_STRUCTURE.md](BLOCK1_SAVEGAME_STRUCTURE.md) |
| Game state and missions | [BLOCK2_GAME_STATE_STRUCTURE.md](BLOCK2_GAME_STATE_STRUCTURE.md) |
| Inventory items | [BLOCK4_INVENTORY_STRUCTURE.md](BLOCK4_INVENTORY_STRUCTURE.md) |
| Compact format spec | [BLOCKS_3_5_COMPACT_FORMAT.md](BLOCKS_3_5_COMPACT_FORMAT.md) |
| Complete SAV specification | [SAV_FILE_FORMAT_SPECIFICATION.md](SAV_FILE_FORMAT_SPECIFICATION.md) |
| Type system reference | [TYPE_SYSTEM_REFERENCE.md](TYPE_SYSTEM_REFERENCE.md) |

---

## File Layout (Example: 18,503 bytes)

```
Offset      Size        Block
--------    --------    ---------------------------
0x0000      44 + 173    Block 1: SaveGame header + LZSS
0x00D9      44 + 1854   Block 2: GameState header + LZSS
[dynamic]   7,972       Block 3: World compact (raw)
[dynamic]   2,150       Block 4: Inventory LZSS (no header)
[end-6266]  6,266       Block 5: Compact data (raw)
```

---

*Generated from block-specific documentation. See individual files for complete details.*
