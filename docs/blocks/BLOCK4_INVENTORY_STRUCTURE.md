# Block 4 Inventory Structure Analysis

## Overview

Block 4 contains the player's physical inventory items. It is LZSS compressed (no header) and decompresses to exactly 32,768 bytes (32 KB).

**Key Statistics:**
- Total size: 32,768 bytes
- Header: 10 bytes (all zeros)
- PhysicalInventoryItem entries: 364
- PropertyReference entries: 364
- Format 1 (Simple) items: 182
- Format 2 (Complex) items: 182

## Block Structure

```
Offset    | Size    | Description
----------|---------|------------------------------------------
0x0000    | 10      | Header (all zeros - no count field)
0x000A    | varies  | PhysicalInventoryItem array (364 entries)
          |         | Items end at 0x7FFF (block boundary)
```

## Item Formats

Block 4 contains two distinct item formats, identified by bytes 4-5 after the type hash:

### Format 1: Simple Items (0x32 prefix)

Used for stackable items with PropertyReference. Fixed size of 66 or 69 bytes.

```
Offset | Size | Description
-------|------|-----------------------------------------------------
+0x00  | 4    | Type Hash: 0xA1A85298 (PhysicalInventoryItem)
+0x04  | 2    | Format marker: 0x0032 (50 decimal)
+0x06  | 2    | Padding: 0x0000
+0x08  | 4    | Quantity (e.g., 0x2A = 42)
+0x0C  | 4    | Field marker: 0x00000011
+0x10  | 4    | Property hash 1: 0xBF298A20
+0x14  | 4    | Property hash 2: 0xC69075AB
+0x18  | 2    | Unknown: 0x0000
+0x1A  | 3    | Prefix: 0x12 0x00 0x0B
+0x1D  | 4    | Item ID Hash (VARIES - identifies specific item)
+0x21  | 4    | Field marker: 0x00000011
+0x25  | 4    | PropertyReference hash: 0x0984415E
+0x29  | 4    | PropertyReference hash (repeated): 0x0984415E
+0x2D  | 2    | Unknown: 0x0000
+0x2F  | 3    | Prefix: 0x12 0x00 0x0B
+0x32  | 19   | Padding/reserved (zeros) [for 69-byte variant]
```

**Size Distribution:**
- 69 bytes: 145 items
- 66 bytes: 36 items

### Format 2: Complex Items (0x00 prefix)

Used for items with embedded sub-object data. Variable size.

```
Offset | Size | Description
-------|------|-----------------------------------------------------
+0x00  | 4    | Type Hash: 0xA1A85298 (PhysicalInventoryItem)
+0x04  | 2    | Format marker: 0x0000
+0x06  | 2    | Length indicator: 0x0A1D (2589 decimal)
+0x08  | 2    | Flags/version: 0x0B 0x01
+0x0A  | var  | Embedded object data (variable length)
```

**Size Distribution:**
| Size | Count | Description |
|------|-------|-------------|
| 22   | 55    | Minimal/null entry |
| 25   | 36    | Simple reference |
| 158  | 84    | Complex item with sub-objects |
| 479  | 1     | Extended complex item |
| 531  | 1     | Extended complex item |
| 587  | 1     | Extended complex item |
| 595  | 2     | Extended complex item |
| 901  | 1     | Extended complex item |
| 1236 | 1     | Extended complex item (largest) |

## Item ID Hashes (Format 1)

These hashes identify specific game items. All Format 1 items have quantity=42.

### By Category (Hash Prefix)

| Prefix | Item IDs | Likely Category |
|--------|----------|-----------------|
| 0x1B | 0x1BE2AFD6, 0x1BE2AFD7, 0x1BE2AFD8 | 3 related variants |
| 0x2E | 0x2E0957F8, 0x2E095807, 0x2E095821, 0x2E095837 | Sequential - ammunition? |
| 0x55 | 0x55308E7F-0x55308EA9 (10 items) | Consumables |
| 0x61 | 0x61D961DE, 0x61D961DF | Related pair |
| 0x66 | 0x6621BE50, 0x6621BE58 | Related pair |
| 0x77 | 0x77AB5B4C | Weapon/armor |
| 0x78 | 0x784EC410, 0x784ECD82 | Weapons/armor |
| 0x7F | 0x7F3D48A7 | Special item |
| 0x9F | 0x9F836382, 0x9F836387 | Related pair |
| 0xAF | 0xAFD4F6F3 | Most common (68 occurrences) - currency? |
| 0xBF | 0xBF4D4478 | Special item |

### Most Common Item IDs

| Item ID | Count | Notes |
|---------|-------|-------|
| 0xAFD4F6F3 | 68 | Most common - possibly florins/currency |
| 0x9F836382 | 6 | |
| 0x1BE2AFD7 | 6 | |
| 0x1BE2AFD6 | 6 | |
| 0x1BE2AFD8 | 6 | |
| 0x6621BE58 | 6 | |
| 0x6621BE50 | 6 | |
| 0x55308E83 | 6 | |

## Item Interleaving Pattern

Format 1 and Format 2 items are interleaved throughout the block, not stored in separate regions. Analysis shows 72 format transitions with varying run lengths:

- Format 1 runs: 1-20 items
- Format 2 runs: 2-18 items

## Type Hashes Used

| Hash | Type Name | Usage |
|------|-----------|-------|
| 0xA1A85298 | PhysicalInventoryItem | Item entry marker (364 total) |
| 0x0984415E | PropertyReference | Property binding (364 total, Format 1 only) |

## Hex Dump Examples

### Format 1 Item (69 bytes)
```
000a: 98 52 a8 a1 32 00 00 00 2a 00 00 00 11 00 00 00
001a: 20 8a 29 bf ab 75 90 c6 00 00 12 00 0b f3 f6 d4
002a: af 11 00 00 00 5e 41 84 09 5e 41 84 09 00 00 12
003a: 00 0b 00 00 00 00 00 00 00 00 00 00 00 00 00 00
004a: 00 00 00 00 00
```

### Format 2 Item (22 bytes - minimal)
```
02b2: 98 52 a8 a1 00 00 1d 0a 0b 01 00 00 00 00 12 00
02c2: 00 00 67 48 00 41
```

### Format 2 Item (158 bytes - complex)
```
00d6: 98 52 a8 a1 00 00 1d 0a 0b 01 00 00 00 00 11 00
00e6: 00 00 bf 6b 77 90 00 00 00 00 00 00 07 00 0b 00
00f6: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
0106: 00 00 91 75 8b 6d 2b 01 00 00 23 01 00 00 15 00
0116: 00 00 97 7b 3a ff af cc 99 25 00 00 19 00 0b 02
0126: 00 00 00 a8 6a 4b 04 11 00 00 00 4f d4 f7 6a 00
0136: 00 00 00 00 00 07 00 0b 00 00 00 00 11 00 00 00
0146: 12 99 7b f7 00 00 00 00 00 00 07 00 0b 00 00 00
0156: 00 11 00 00 00 24 c9 7e c8 00 00 00 00 00 00 07
0166: 00 0b d7 71 d6 5f 9c 00 00 00 b8 57 f2 b7
```

## Notes

1. **1:1 Correspondence**: Each PhysicalInventoryItem has exactly one PropertyReference in Format 1 items.

2. **Block Boundary**: The last item ends exactly at the 32KB boundary. The final bytes `98 52` are the start of what would be another PhysicalInventoryItem hash, but the block is truncated.

3. **No Array Header**: Unlike other serialization formats, Block 4 has no count field or array length prefix. The 10-byte header is all zeros.

4. **Quantity Field**: All Format 1 items have quantity=42, suggesting either a maximum stack size or a default/placeholder value.

5. **Format 2 Embedded Data**: Complex items contain embedded hash values and sub-object data. The 158-byte format appears to use 0x11 field markers and contains multiple embedded property references.

6. **Field Markers**: The value 0x11 (17 decimal) appears frequently as a field marker/delimiter in both formats.

## Related Files

- Source: `ACBROTHERHOODSAVEGAME0.SAV` (Block 4)
- Decompressed: `/tmp/block4_analysis/sav_block4_decompressed.bin`
- Parser: `/mnt/f/ClaudeHole/assassinscreedsave/sav_parser.py`

## Future Research

1. Map Item ID hashes to actual AC Brotherhood inventory items
2. Decode Format 2 embedded object structure
3. Understand the relationship between quantity and item stacking
4. Investigate continuation in Block 5 (contains 1 PhysicalInventoryItem)
