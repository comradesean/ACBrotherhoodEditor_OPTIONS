# Property Descriptor Hex Dumps

This file contains property descriptor memory dumps extracted from reverse engineering analysis of Assassin's Creed Brotherhood save file serialization. These PropertyDescriptor structures are stored in static memory and define how each property is serialized.

**Source:** SECTION3_SERIALIZATION.md, TRACES.md
**Analysis Tool:** Ghidra static analysis + WinDbg TTD trace

---

## PropertyDescriptor Structure Layout

Each PropertyDescriptor is a 32-byte (0x20) structure:

```
Offset  Size  Field
0x00    4     flags (always 0x02000001)
0x04    4     property_hash (little-endian)
0x08    6     padding (zeros)
0x0e    2     type_info (type code at byte 0: 0x00=bool, 0x07=uint32, 0x09=uint64)
0x10    4     scaled_offset (object_field_offset x 4)
0x14    12    padding (zeros)
```

---

## DAT_027ecf90 - SaveGameDataObject Base Class Field

**Property Hash:** 0xbf4c2013
**Type:** uint32 (0x07)
**Object Offset:** +0x04 (scaled: 0x10)

```
027ecf90: 01 00 00 02  13 20 4c bf  00 00 00 00  00 00 07 00
027ecfa0: 00 00 10 00  00 00 00 00  00 00 00 00  00 00 00 00
```

**Field Breakdown:**
- `01 00 00 02` - flags (0x02000001)
- `13 20 4c bf` - hash 0xbf4c2013 (little-endian)
- `00 00 00 00 00 00` - padding
- `07 00` - type_info (0x07 = uint32)
- `00 00 10 00` - scaled_offset 0x10 (object offset +0x04 x 4)
- remaining: padding

---

## DAT_02973250 - bool_field_0x20

**Property Hash:** 0x3b546966
**Type:** bool (0x00)
**Object Offset:** +0x20 (scaled: 0x80)

```
02973250: 01 00 00 02  66 69 54 3b  00 00 00 00  00 00 00 00
02973260: 00 00 80 00  00 00 00 00  00 00 00 00  00 00 00 00
```

**Field Breakdown:**
- `01 00 00 02` - flags (0x02000001)
- `66 69 54 3b` - hash 0x3b546966 (little-endian)
- `00 00 00 00 00 00` - padding
- `00 00` - type_info (0x00 = bool)
- `00 00 80 00` - scaled_offset 0x80 (object offset +0x20 x 4)
- remaining: padding

---

## DAT_02973270 - bool_field_0x21

**Property Hash:** 0x4dbc7da7
**Type:** bool (0x00)
**Object Offset:** +0x21 (scaled: 0x84)

```
02973270: 01 00 00 02  a7 7d bc 4d  00 00 00 00  00 00 00 00
02973280: 00 00 84 00  00 00 00 00  00 00 00 00  00 00 00 00
```

**Field Breakdown:**
- `01 00 00 02` - flags (0x02000001)
- `a7 7d bc 4d` - hash 0x4dbc7da7 (little-endian)
- `00 00 00 00 00 00` - padding
- `00 00` - type_info (0x00 = bool)
- `00 00 84 00` - scaled_offset 0x84 (object offset +0x21 x 4)
- remaining: padding

---

## DAT_02973290 - bool_field_0x22

**Property Hash:** 0x5b95f10b
**Type:** bool (0x00)
**Object Offset:** +0x22 (scaled: 0x88)

```
02973290: 01 00 00 02  0b f1 95 5b  00 00 00 00  00 00 00 00
029732a0: 00 00 88 00  00 00 00 00  00 00 00 00  00 00 00 00
```

**Field Breakdown:**
- `01 00 00 02` - flags (0x02000001)
- `0b f1 95 5b` - hash 0x5b95f10b (little-endian)
- `00 00 00 00 00 00` - padding
- `00 00` - type_info (0x00 = bool)
- `00 00 88 00` - scaled_offset 0x88 (object offset +0x22 x 4)
- remaining: padding

---

## DAT_029732b0 - bool_field_0x23

**Property Hash:** 0x2a4e8a90
**Type:** bool (0x00)
**Object Offset:** +0x23 (scaled: 0x8c)

```
029732b0: 01 00 00 02  90 8a 4e 2a  00 00 00 00  00 00 00 00
029732c0: 00 00 8c 00  00 00 00 00  00 00 00 00  00 00 00 00
```

**Field Breakdown:**
- `01 00 00 02` - flags (0x02000001)
- `90 8a 4e 2a` - hash 0x2a4e8a90 (little-endian)
- `00 00 00 00 00 00` - padding
- `00 00` - type_info (0x00 = bool)
- `00 00 8c 00` - scaled_offset 0x8c (object offset +0x23 x 4)
- remaining: padding

---

## DAT_029732d0 - uint64_field_0x18

**Property Hash:** 0x496f8780
**Type:** uint64 (0x09)
**Object Offset:** +0x18 (scaled: 0x60)

```
029732d0: 01 00 00 02  80 87 6f 49  00 00 00 00  00 00 09 00
029732e0: 00 00 60 00  00 00 00 00  00 00 00 00  00 00 00 00
```

**Field Breakdown:**
- `01 00 00 02` - flags (0x02000001)
- `80 87 6f 49` - hash 0x496f8780 (little-endian)
- `00 00 00 00 00 00` - padding
- `09 00` - type_info (0x09 = uint64)
- `00 00 60 00` - scaled_offset 0x60 (object offset +0x18 x 4)
- remaining: padding

---

## DAT_029732f0 - bool_field_0x24

**Property Hash:** 0x6f88b05b
**Type:** bool (0x00)
**Object Offset:** +0x24 (scaled: 0x90)

```
029732f0: 01 00 00 02  5b b0 88 6f  00 00 00 00  00 00 00 00
02973300: 00 00 90 00  00 00 00 00  00 00 00 00  00 00 00 00
```

**Field Breakdown:**
- `01 00 00 02` - flags (0x02000001)
- `5b b0 88 6f` - hash 0x6f88b05b (little-endian)
- `00 00 00 00 00 00` - padding
- `00 00` - type_info (0x00 = bool)
- `00 00 90 00` - scaled_offset 0x90 (object offset +0x24 x 4)
- remaining: padding

---

## Summary Table

| DAT Address | Property Hash | Type | Type Code | Object Offset | Scaled Offset | Field Name |
|-------------|---------------|------|-----------|---------------|---------------|------------|
| DAT_027ecf90 | 0xbf4c2013 | uint32 | 0x07 | +0x04 | 0x10 | SaveGameDataObject base field |
| DAT_02973250 | 0x3b546966 | bool | 0x00 | +0x20 | 0x80 | bool_field_0x20 |
| DAT_02973270 | 0x4dbc7da7 | bool | 0x00 | +0x21 | 0x84 | bool_field_0x21 |
| DAT_02973290 | 0x5b95f10b | bool | 0x00 | +0x22 | 0x88 | bool_field_0x22 |
| DAT_029732b0 | 0x2a4e8a90 | bool | 0x00 | +0x23 | 0x8c | bool_field_0x23 |
| DAT_029732d0 | 0x496f8780 | uint64 | 0x09 | +0x18 | 0x60 | uint64_field_0x18 |
| DAT_029732f0 | 0x6f88b05b | bool | 0x00 | +0x24 | 0x90 | bool_field_0x24 |

---

## PTR_DAT References (Accessor Pointers)

These are the pointer tables used by serialization functions to access PropertyDescriptors:

**SaveGameDataObject::Serialize (FUN_005e3700):**
- PTR_DAT_027ecf8c -> DAT_027ecf90 (base class uint32)

**AssassinSingleProfileData::Serialize (FUN_01710580):**
- PTR_DAT_02973310 -> DAT_02973250 (bool_field_0x20)
- PTR_DAT_02973314 -> DAT_02973270 (bool_field_0x21)
- PTR_DAT_02973318 -> DAT_02973290 (bool_field_0x22)
- PTR_DAT_0297331c -> DAT_029732b0 (bool_field_0x23)
- PTR_DAT_02973320 -> DAT_029732d0 (uint64_field_0x18)
- PTR_DAT_02973324 -> DAT_029732f0 (bool_field_0x24)

---

## Type Code Reference

| Code | Type | Size |
|------|------|------|
| 0x00 | bool | 1 byte |
| 0x07 | uint32 | 4 bytes |
| 0x09 | uint64 | 8 bytes |

**Note:** These are the only type codes used in the OPTIONS save file Section 3.
