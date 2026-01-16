# Section 3 Serialization - WinDbg TTD Trace Results

## Overview

This document records all findings from WinDbg Time Travel Debugging (TTD) trace of the Assassin's Creed Brotherhood save file serialization for the OPTIONS file.

**TTD Trace File:** OPTIONS.WINDBGTRACE
**File Being Read:** game_uncompressed_3.bin (162 bytes, Section 3)
**Module Base:** ACBSP = 0x00ae0000
**Ghidra Base:** 0x00400000
**Address Conversion:** WinDbg = Ghidra + 0x6e0000

---

## Quick Start - Section 3 Binary Format

**To READ Section 3:**
```
1. Parse header (0x00-0x0D): 1B version, 4B name_len, 4B obj_id, 1B mode, 4B type_hash
2. Read section sizes (0x0E-0x19): 3x 4B sizes (object, properties, base_class)
3. Read base class property (0x1A): [hash 4][type_info 8][flags 1][value 4] (no size field)
4. Iterate regular properties until EOF-4:
   - [size 4][hash 4][type_info 8][flags 1][value N]
   - Value size: bool=1, uint32=4, uint64=8 (derived from type_info byte 6)
5. Read trailing 4B (dynamic properties size, always 0)
```

**To WRITE Section 3:**
```
1. Write header (0x00-0x0D)
2. OpenSection() 3x - reserves 4B each for sizes (backpatched later)
3. Write base class property (no size field)
4. CloseSection() - backpatches base_class size
5. For each property: OpenSection(), write content, CloseSection()
6. CloseSection() - backpatches properties size
7. Write 0x00000000 (no dynamic properties)
8. CloseSection() - backpatches object size
```

**Type codes (byte 6 of type_info):** `0x00`=bool, `0x07`=uint32, `0x09`=uint64 — See [TYPE_CODES.md](TYPE_CODES.md) for full reference

**Reference implementation:** [`section3_parser.py`](../section3_parser.py)

---

## Class Hierarchy

```
AssassinSingleProfileData (0xc9876d66) - FUN_01710580
  └── SaveGameDataObject (0xb7806f86) - FUN_005e3700
```

| Class | Type Hash | Serialize Function | Ghidra Address |
|-------|-----------|-------------------|----------------|
| AssassinSingleProfileData | 0xc9876d66 | FUN_01710580 | 0x01710580 |
| SaveGameDataObject (base) | 0xb7806f86 | FUN_005e3700 | 0x005e3700 |

**Note:** The type hash 0xc9876d66 is written to the file at offset 0x0a. The base class type hash 0xb7806f86 is NOT written to the file - only used internally. The base class *field* hash 0xbf4c2013 appears at offset 0x1a as part of the base class property.

---

## Quick Cross-Reference

This document contains detailed traces of serialization functions. Key navigation points:

| Topic | Section |
|-------|---------|
| File byte layout | [Detailed Layout](#detailed-layout) |
| Property format | [Property Format in File](#property-format-in-file) |
| Section nesting visual | [Visual: Section Nesting and Backpatching](#visual-section-nesting-and-backpatching) |
| VTable reference | [VTable Reference (Complete)](#vtable-reference-complete) |
| WRITE path call flow | [Complete WRITE Path Flow (Summary)](#complete-write-path-flow-summary) |
| Parser implementation | [`section3_parser.py`](../section3_parser.py) |

---

## Traced Functions (READ Path)

See [FUNCTIONS.md](FUNCTIONS.md#read-path) for detailed READ path function documentation including:
- FUN_01710580: AssassinSingleProfileData::Serialize (entry point)
- FUN_005e3700: SaveGameDataObject::Serialize (base class)
- FUN_01b12fa0: Property serialization core
- FUN_01b6f440/FUN_01b6f490: Stream read (4/8 bytes)

**Key call chain:** Serialize → Property Serializer → vtable dispatch → Stream read

---

## File Structure (Confirmed via WinDbg WRITE Path Trace)

### Understanding Header vs Section Reservations

The file structure has three distinct regions:

1. **ObjectInfo Header (0x00-0x0D)** - Written by FUN_01b08ce0
   - Object metadata and type identification
   - Written directly, not backpatched

2. **Section Size Reservations (0x0E-0x19)** - Reserved by OpenSection calls
   - NOT part of the semantic "header"
   - Internal bookkeeping for nested section structure
   - Backpatched later by CloseSection in reverse order (LIFO)

3. **Content (0x1A onwards)** - Properties and data

<a id="detailed-layout"></a>
### Detailed Layout

**Note:** Fields 0x0e-0x19 are three uint32 section sizes (not mixed uint16/uint32 fields). See [Important Correction](#important-correction) for details.

```
=== OBJECTINFO HEADER (0x00-0x0D) - Written by FUN_01b08ce0 ===
Offset  Bytes                          Field                  Written By
------  ----------------------------   --------------------   ------------------
0x00    00                             NbClassVersionsInfo    FUN_01b0d500 (vtable[0x98])
0x01    00 00 00 00                    ObjectName length      FUN_01b48e90 (vtable[0x54])
0x05    00 00 00 00                    ObjectID               FUN_01b48e70 (vtable[0x9c])
0x09    00                             InstancingMode         FUN_01b0d500 (vtable[0x98])
0x0a    66 6d 87 c9                    TypeHash               FUN_01b48fb0 (vtable[0x50])
        ↑ 0xc9876d66 little-endian

=== SECTION SIZE RESERVATIONS (0x0E-0x19) - Reserved via OpenSection ===
0x0e    90 00 00 00                    "Object" section size      OpenSection in FUN_01b08ce0
        ↑ 0x00000090 = 144 bytes
        ↑ VERIFIED: backpatched at E68A1F:D0 via mov [0x0466000e], 0x00000090
        ↑ Covers: offset 0x12 to EOF (0xa2 - 0x12 = 0x90)

0x12    88 00 00 00                    "Properties" section size  OpenSection in FUN_01b08ce0
        ↑ 0x00000088 = 136 bytes
        ↑ VERIFIED: backpatched at E68A1D:B86 via mov [0x04660012], 0x00000088
        ↑ Covers: offset 0x1a to EOF (0xa2 - 0x1a = 0x88)

0x16    11 00 00 00                    Base class section size    OpenSection in SaveGameDataObject
        ↑ 0x00000011 = 17 bytes
        ↑ VERIFIED: backpatched at E68A19:CF6 via mov [0x04660016], 0x00000011
        ↑ Covers: base class property only (0x1a-0x2a = 17 bytes)

=== CONTENT (0x1A onwards) ===
--- Base class field property (shortened format: [hash 4][type_info 8][flags 1][value 4], no size field) ---
0x1a    13 20 4c bf                    base_class_hash        0xbf4c2013
0x1e    00 00 00 00 00 00 07 00        base_class_type_info   (8 bytes)
0x26    0b                             base_class_flags       0x0b (property flags byte!)
0x27    00 00 00 00                    base_class_value       0x00000000
--- End base class field property (17 bytes total) ---

--- Regular properties follow standard format (see Property Format in File section below) ---
0x2b    0e 00 00 00                    first prop size        0x0e (14)
0x2f    66 69 54 3b                    first prop hash        0x3b546966
...
```

### Write Order vs File Order

**WRITE order (chronological):**
1. FUN_01b08ce0 writes 0x00-0x0D (header)
2. FUN_01b08ce0 reserves 0x0E-0x11 via OpenSection("Object")
3. FUN_01b08ce0 reserves 0x12-0x15 via OpenSection("Properties")
4. SaveGameDataObject::Serialize reserves 0x16-0x19 via OpenSection
5. SaveGameDataObject::Serialize writes base class property (0x1A-0x2A)
6. CloseSection patches 0x16-0x19 with base class size (17)
7. Properties written (0x2B-0x9D)
8. CloseSection patches 0x12-0x15 with properties size (136)
9. Trailing zeros written (0x9E-0xA1)
10. CloseSection patches 0x0E-0x11 with object size (144)

**Section Stack (LIFO):**
```
Push: OpenSection("Object")     → saves position 0x0e, stack[0]
Push: OpenSection("Properties") → saves position 0x12, stack[1]
Push: OpenSection(base class)   → saves position 0x16, stack[2]
Pop:  CloseSection              → patches 0x16 with size 17
Pop:  CloseSection              → patches 0x12 with size 136
Pop:  CloseSection              → patches 0x0e with size 144
```

### CloseSection Backpatch Mechanism (Traced)

> Assembly: See DISASSEMBLY.md - CloseSection Backpatch Mechanism

**CloseSection (FUN_01b48920) at 0x02228920**

Traced at TTD position E68A19:CBB for CloseSection("Property").

> Trace: See TRACES.md - CloseSection Backpatch Traces (serializer counter arrays, position tokens, all backpatch verification)

**Core Write Function:** FUN_01b6fea0 (0x0224fea0 WinDbg / 0x01b6fea0 Ghidra)

**IMPORTANT**: The 0x0b at offset 0x26 is NOT NbClassVersionsInfo!
It is the **property flags byte** for the base class field, written by FUN_01b076f0.

---

## VTable Reference

See [VTABLES.md](VTABLES.md) for the complete VTable reference including:
- Serializer Mode VTable at PTR_FUN_02555c60 (38 entries)
- Stream Inner VTable at PTR_FUN_02556168 (28 entries)

**Quick lookup:** vtable[0x58]=bool, vtable[0x7c]=uint64, vtable[0x84]=uint32

**Legend:** ✓ = Traced, ○ = Ghidra verified, ? = Inferred

---

## Key Findings

### 1. Mode Detection
- Mode byte at `[serializer+4]+4`
- 0x00 = WRITE mode
- 0x01 = READ mode

### 2. Buffer Position Tracking
- Stream object at `[serializer+8]`
- Current position at `[stream+0x18]`
- Position adjusts by type size (1, 4, or 8 bytes)

### 3. Property Metadata (PropertyDescriptor Structure)

Each property has a 32-byte (0x20) descriptor in static memory that defines how to serialize it.

**Structure Layout (verified from Ghidra):**
```
Offset  Size  Field
0x00    4     flags (always 0x02000001)
0x04    4     property_hash (little-endian)
0x08    6     padding (zeros)
0x0e    2     type_info (type code at byte 0, e.g., 0x00=bool, 0x07=uint32, 0x09=uint64)
0x10    4     scaled_offset (object_field_offset × 4)
0x14    12    padding (zeros)
```

**Property Descriptors (from Ghidra):**

| DAT Address | Hash | Type | Object Offset | Scaled (×4) | Field Name |
|-------------|------|------|---------------|-------------|------------|
| DAT_027ecf90 | 0xbf4c2013 | uint32 (0x07) | +0x04 | 0x10 | SaveGameDataObject base field |
| DAT_02973250 | 0x3b546966 | bool (0x00) | +0x20 | 0x80 | bool_field_0x20 |
| DAT_02973270 | 0x4dbc7da7 | bool (0x00) | +0x21 | 0x84 | bool_field_0x21 |
| DAT_02973290 | 0x5b95f10b | bool (0x00) | +0x22 | 0x88 | bool_field_0x22 |
| DAT_029732b0 | 0x2a4e8a90 | bool (0x00) | +0x23 | 0x8c | bool_field_0x23 |
| DAT_029732d0 | 0x496f8780 | uint64 (0x09) | +0x18 | 0x60 | uint64_field_0x18 |
| DAT_029732f0 | 0x6f88b05b | bool (0x00) | +0x24 | 0x90 | bool_field_0x24 |

> Hex Dump: See [PROPERTY_DESCRIPTORS.md](PROPERTY_DESCRIPTORS.md) for complete hex dumps of all PropertyDescriptor structures (DAT_027ecf90 through DAT_029732f0)

**Key Observations:**
- flags bit 0 set (0x01) = "serialize this property"
- type_info at offset 0x0e matches type codes: 0x00=bool, 0x07=uint32, 0x09=uint64
- scaled_offset formula: `object_field_offset × 4` (purpose unknown, possibly vtable indexing)

**PTR_DAT References (how Serialize functions access PropertyDescriptors):**
```
FUN_005e3700 (SaveGameDataObject::Serialize):
  → Uses PTR_DAT_027ecf8c → DAT_027ecf90 (base class uint32)

FUN_01710580 (AssassinSingleProfileData::Serialize):
  → PTR_DAT_02973310 → DAT_02973250 (bool_field_0x20)
  → PTR_DAT_02973314 → DAT_02973270 (bool_field_0x21)
  → PTR_DAT_02973318 → DAT_02973290 (bool_field_0x22)
  → PTR_DAT_0297331c → DAT_029732b0 (bool_field_0x23)
  → PTR_DAT_02973320 → DAT_029732d0 (uint64_field_0x18)
  → PTR_DAT_02973324 → DAT_029732f0 (bool_field_0x24)
```

**Completeness:** These 7 PropertyDescriptors are the COMPLETE set of types for this file.
The only type codes used are: **0x00 (bool), 0x07 (uint32), 0x09 (uint64)**.

### 4. Base Class Field Property at 0x1a-0x2a

> Uses the **Base Class Property Format** (variant 2) from the [Property Format in File](#property-format-in-file) canonical definition.

- Hash 0xbf4c2013 = SaveGameDataObject field hash
- Flags byte 0x0b at offset 0x26 (property flags, NOT NbClassVersionsInfo!)
- Value at 0x27-0x2a = base class field value (uint32)

---

## WRITE Path Trace

See [FUNCTIONS.md](FUNCTIONS.md#write-path) for detailed WRITE path function documentation including:
- FUN_01b08ce0: Header writer
- FUN_01b0d500: Single byte writer
- FUN_01b49610/FUN_01b6fea0: 4-byte write dispatcher

**Mode check:** `[serializer+4]+4 = 0x00` indicates WRITE mode

---

### Property Serialization Functions

See [FUNCTIONS.md](FUNCTIONS.md#property-serializers) for detailed property serializer documentation including:
- FUN_01b48fb0: TypeInfo serializer (vtable[0x50])
- FUN_01b0d140: Property header writer
- FUN_01b48e80: Bool serializer (vtable[0x58])
- FUN_01b48be0: uint64 serializer (vtable[0x7c])

---

## Section Nesting (OpenSection/CloseSection)

The TypeInfo block fields (0x0e-0x19) are **section size fields** written by CloseSection (FUN_01b48920).

### Section Stack Model

Sections are opened in forward order but closed in reverse (LIFO stack):

```
1. OpenSection("Object") at 0x0e      ← reserves 4 bytes, pushes position
2. OpenSection("Properties") at 0x12   ← reserves 4 bytes, pushes position
3. OpenSection(???) at 0x16            ← reserves 4 bytes, pushes position
4. Write base class property (17 bytes at 0x1a-0x2a)
5. CloseSection(???)                   ← patches 0x16 with size=17 (E68A19:CF7)
6. Write properties (0x2b-0x9d)
7. CloseSection("Properties")          ← patches 0x12 with size=136 (E68A1D:B87)
8. CloseSection("Object")              ← patches 0x0e with size=144 (E68A1F:D0)
```

<a id="visual-section-nesting-and-backpatching"></a>
### Visual: Section Nesting

**LIFO Model (simplified):**
```
OpenSection("Object")      → stack: [0x0E]
  OpenSection("Properties") → stack: [0x0E, 0x12]
    OpenSection("BaseClass") → stack: [0x0E, 0x12, 0x16]
    CloseSection()          → patches 0x16, stack: [0x0E, 0x12]
  CloseSection()            → patches 0x12, stack: [0x0E]
CloseSection()              → patches 0x0E, stack: []
```

**Size formula:** `size = current_position - saved_position - 4`

See [DIAGRAMS.md](DIAGRAMS.md) for detailed visual diagrams including file layout, backpatching sequence, and property nesting.

### Section Size Values (TRACED)

| Field | Offset | Value | Decimal | Meaning | Written At |
|-------|--------|-------|---------|---------|------------|
| field_0x16 | 0x16-0x19 | 0x00000011 | 17 | Base class property size | E68A19:CF7 |
| field_0x12 | 0x12-0x15 | 0x00000088 | 136 | 0xa2 - 0x1a = bytes from base class to EOF | E68A1D:B87 |
| field_0x0e | 0x0e-0x11 | 0x00000090 | 144 | 0xa2 - 0x12 = bytes from Properties to EOF | E68A1F:D0 |

---

<a id="property-format-in-file"></a>
## Property Format in File

**Property Format in File (Canonical Definition):**

There are two property format variants:

**1. Regular Property Format** (used for most properties):
```
[size 4][hash 4][type_info 8][flags 1][value N]
   ↑       ↑         ↑          ↑        ↑
   │       │         │          │        └── Written by caller (vtable[0x58/0x7c/0x84])
   │       │         │          └── FUN_01b076f0 (always 0x0b in this trace)
   │       │         └── FUN_01b0e980 (8 bytes from metadata +8/+C)
   │       └── FUN_01b0e680 (4 bytes from metadata +4)
   └── OpenSection (backpatched by CloseSection with total size)
```

**2. Base Class Property Format** (shortened, no size field):
```
[hash 4][type_info 8][flags 1][value 4] = 17 bytes total
```

**Property Type Sizes:**
| Type | Size Field | Value Size | Total Size |
|------|-----------|------------|------------|
| bool | 0x0e (14) | 1 byte | 18 bytes |
| uint32 | 0x11 (17) | 4 bytes | 21 bytes |
| uint64 | 0x15 (21) | 8 bytes | 25 bytes |

---

## Parser Verification Checklist

> **See Also:** The parser implementation is in [`section3_parser.py`](../section3_parser.py) in the same directory. The parser implements all traced serialization behavior and has been verified to produce byte-for-byte identical output.

| Component | Parser Implementation | Trace Verified |
|-----------|----------------------|----------------|
| Header padding (10 bytes) | ✓ | ✓ |
| Type hash at 0x0a | ✓ | ✓ |
| field_0x0e (2 bytes) | ✓ | ✓ |
| field_0x10 (4 bytes) | ✓ | ✓ |
| field_0x14 (4 bytes) | ✓ | ✓ |
| field_0x18 (6 bytes) | ✓ | ✓ |
| field_0x1e (6 bytes) | ✓ | ✓ |
| field_0x24 (2 bytes) | ✓ | ✓ |
| Base class hash at 0x1a | ✓ | ✓ |
| Base class type_info (8 bytes) | ✓ | ✓ |
| Base class flags at 0x26 | ✓ (was incorrectly named NbClassVersionsInfo) | ✓ |
| Base class value (4 bytes) | ✓ | ✓ |
| Bool property format | ✓ (see [Property Format](#property-format-in-file)) | ✓ |
| uint64 property format | ✓ (see [Property Format](#property-format-in-file)) | ✓ |
| Property flags byte (0x0b) | ✓ | ✓ |
| Trailing bytes (4 zeros) | ✓ | ✓ (Dynamic Properties CloseSection) |

---

## Parser Verification Results

> **See Also:** The parser source code is in [`section3_parser.py`](../section3_parser.py). Line numbers referenced below correspond to that file.

### Header Parsing (section3_parser.py lines 184-216)

| Parser Code | Trace Verified | Notes |
|-------------|----------------|-------|
| `reader.read_bytes(10)` padding | ✓ | Matches 10 bytes at 0x00 |
| `reader.read_uint32()` type_hash | ✓ | 0xc9876d66 at 0x0a |
| `reader.read_uint16()` field_0x0e | ✓ | 0x0090 at 0x0e |
| `reader.read_uint32()` field_0x10 | ✓ | 0x00880000 at 0x10 |
| `reader.read_uint32()` field_0x14 | ✓ | 0x00110000 at 0x14 |
| `reader.read_bytes(6)` field_0x18 | ✓ | Contains 0xbf4c2013 hash |
| `reader.read_bytes(6)` field_0x1e | ✓ | 6 bytes at 0x1e |
| `reader.read_uint16()` field_0x24 | ✓ | 0x0007 at 0x24 |

### Constants Verification (section3_parser.py lines 381-444)

| Constant | Parser Value | Trace Value | Status |
|----------|-------------|-------------|--------|
| BOOL_SIZE_FIELD | 0x0e (14) | 0x0e | ✓ Match |
| UINT64_SIZE_FIELD | 0x15 (21) | 0x15 | ✓ Match |
| PROPERTY_FLAGS_BYTE | 0x0b | 0x0b | ✓ Match |
| BOOL_TYPE_INFO | 8 × 0x00 | 8 × 0x00 | ✓ Match |
| UINT64_TYPE_INFO | `00 00 00 00 00 00 09 00` | `00 00 00 00 00 00 09 00` | ✓ Match |
| NB_CLASS_VERSIONS_INFO | 0x0b | 0x0b at offset 0x26 | ✓ Match |

### Property Format Verification

| Property Type | Traced Position | Value Size | Status |
|--------------|-----------------|------------|--------|
| Bool | B1F2B:BE9 | 1 byte | MATCH |
| UInt64 | B1F2B:1643 | 8 bytes | MATCH |

### Important Semantic Note

**Base Class Field (offset 0x27-0x2a):**
- ~~Parser treats as: `OBJECT_SECTION_PLACEHOLDER` (4 zero bytes)~~ **FIXED**
- Parser now properly parses as `header['base_class_field']` and preserves during roundtrip
- Trace reveals: This is the **base class field value** read by FUN_01b0a1f0
- Traced at: B1F2B:B7B - FUN_01b6f440 reads from buffer 0x0a3a0627
- Field pointer: 0xf74c0a54 (object + 0x04, SaveGameDataObject field)
- Value in OPTIONS file: 0x00000000 (but could theoretically be any uint32)

**Parser Compliance Summary:**
| Component | Parser Constant | Trace Value | Match |
|-----------|-----------------|-------------|-------|
| Bool size | BOOL_SIZE_FIELD = 0x0e | 0x0e | ✓ |
| uint64 size | UINT64_SIZE_FIELD = 0x15 | 0x15 | ✓ |
| Property flags | PROPERTY_FLAGS_BYTE = 0x0b | 0x0b | ✓ |
| Bool type_info | BOOL_TYPE_INFO = 8×0x00 | 8×0x00 | ✓ |
| uint64 type_info | UINT64_TYPE_INFO | `00..00 09 00` | ✓ |
| Base class flags | 0x0b at offset 0x26 | 0x0b | ✓ (property flags byte) |
| Trailing zeros | TRAILING_BYTES = 4×0x00 | Dynamic Props size=0 | ✓ |

### VTable Offsets Verified

| Type | VTable Offset | Read Function | Parser Implementation |
|------|--------------|---------------|----------------------|
| uint32 | 0x84 | FUN_01b6f440 (4 bytes) | `struct.unpack('<I')` ✓ |
| bool | 0x58 | FUN_01b497f0 (1 byte) | `data[value_offset]` ✓ |
| uint64 | 0x7c | FUN_01b6f490 (8 bytes) | `struct.unpack('<q')` ✓ |

### Roundtrip Test Result

```
✓ ROUNDTRIP VERIFIED: Output matches original byte-for-byte
```

The parser correctly implements all traced serialization behavior for the READ path

---

## Complete WRITE Path Flow (Summary)

> **Note:** For detailed function documentation including decompilation and trace data, see [FUNCTIONS.md](FUNCTIONS.md). For VTable references, see [VTable Reference (Complete)](#vtable-reference-complete). For Stream I/O functions, see [Stream Inner VTable](#stream-inner-vtable-at-ptr_fun_02556168-ghidra--0x02c36168-windbg).

```
FUN_01710580 (AssassinSingleProfileData::Serialize)
  │
  ├─ Mode check: [serializer+4]+4 == 0x00 (WRITE mode)
  │
  ├─ FUN_01dc2c0, FUN_01db8a0 (setup)
  │
  ├─ FUN_01b09e20 (header writer wrapper)
  │   └─ FUN_01b08ce0 (actual header writer)
  │       ├─ FUN_01b0d500("NbClassVersionsInfo") → offset 0x00 (1 byte)
  │       ├─ FUN_01b48e90 (string serializer) → offset 0x01-0x04 (ObjectName length)
  │       ├─ FUN_01b48e70 (uint32 serializer) → offset 0x05-0x08 (ObjectID)
  │       ├─ FUN_01b0d500("InstancingMode") → offset 0x09 (1 byte)
  │       └─ vtable[0x50] (type info block) → offset 0x0a-0x19
  │
  ├─ FUN_005e3700 (SaveGameDataObject::Serialize base class)
  │   └─ FUN_01b0a1f0 → FUN_01b12fa0 → FUN_01b076f0
  │       └─ Base class property → offset 0x1a-0x2a (17 bytes)
  │
  ├─ FUN_01b09650 (bool property serializer) × 5
  │   └─ FUN_01b11fb0 → FUN_01b0d140 (property header) + vtable[0x58] (bool value)
  │
  ├─ FUN_01b09760 (uint64 property serializer) × 1
  │   └─ FUN_01b124e0 → FUN_01b0d140 (property header) + vtable[0x7c] (uint64 value)
  │
  └─ FUN_01b0d0c0 (finalization)
      └─ vtable[5]("Dynamic Properties") → offset 0x9e-0xa1 (trailing 4 zeros)
```

**Core I/O Functions (WRITE mode):**
- FUN_01b6f370: Single byte write - `*buffer++ = byte`
- FUN_01b6fea0: 4-byte write - `*buffer = value; buffer += 4`
- FUN_01b6f4e0 → FUN_01b6ff10: 8-byte write (for uint64)

---

## Session Resume Instructions

**Last TTD Position:** E68A1D:F9D
**Location:** Completed FUN_01b0d0c0 finalization - wrote Dynamic Properties size (0x00000000) at offset 0x9e

**WRITE Path Status:** COMPLETE
All WRITE path serialization has been traced:
- Header (0x00-0x19)
- Base class property (0x1a-0x2a)
- 5 bool properties (0x2b-0x95)
- 1 uint64 property (0x96-0x9d)
- Dynamic Properties section (0x9e-0xa1) - trailing 4 zeros

> **Note:** For function addresses and VTable mappings, see:
> - [VTable Reference (Complete)](#vtable-reference-complete) - Serializer mode vtable
> - [Stream Inner VTable](#stream-inner-vtable-at-ptr_fun_02556168-ghidra--0x02c36168-windbg) - Stream I/O functions
> - [FUNCTIONS.md](FUNCTIONS.md) - Individual function documentation with WinDbg addresses and decompilation

**Key Discoveries from WRITE Path Trace:**
- WRITE mode byte: `[serializer+4]+4 = 0x00`
- StartElement/EndElement are NO-OPs in WRITE mode (just `RET 4`)
- Serializer version: `[context+0x24] = 0x10` (16) - determines legacy vs current format
- Structured header at 0x00-0x09: NOT padding, but NbClassVersionsInfo + ObjectName + ObjectID + InstancingMode
- The 0x0b at offset 0x26 is the base class property FLAGS BYTE, written by FUN_01b076f0
