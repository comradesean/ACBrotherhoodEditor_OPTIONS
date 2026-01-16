# Section 1 Serialization Documentation

**Document Version:** 2.3
**Date:** 2026-01-07
**Status:** Complete (Verified by Working Parser + Deep Ghidra Analysis)

This document provides comprehensive documentation for Section 1 serialization in the AC Brotherhood OPTIONS file format, derived from Ghidra decompilation and WinDbg time-travel debugging.

---

## Table of Contents

1. [Overview and Purpose](#overview-and-purpose)
2. [Call Sequence with Function Addresses](#call-sequence-with-function-addresses)
3. [Binary Layout with Exact Byte Offsets](#binary-layout-with-exact-byte-offsets)
4. [Property Descriptor Structure](#property-descriptor-structure)
5. [Type System and Dispatch](#type-system-and-dispatch)
6. [Type Prefix Mapping (RESOLVED)](#type-prefix-mapping-resolved)
7. [Root vs Child Property Serialization](#root-vs-child-property-serialization)
8. [Serializer Context Structure](#serializer-context-structure)
9. [Block Nesting Mechanism](#block-nesting-mechanism)
10. [Value Encoding by Type](#value-encoding-by-type)
11. [Vtable Methods Used](#vtable-methods-used)
12. [Detailed Function Analysis](#detailed-function-analysis)
13. [Working Parser Reference](#working-parser-reference)
14. [Knowledge Gaps and Further Research](#knowledge-gaps-and-further-research)

---

## Overview and Purpose

Section 1 contains system/profile data for Assassin's Creed Brotherhood save files. It is identified by:

- **Root Hash:** `0xBDBE3B52` ("SaveGame")
- **ManagedObject Wrapper Hash:** `0xBB96607D`
- **Uncompressed Size:** 283 bytes (PC) / 289 bytes (PS3)

### Section 1 Header (Compressed File)

| Offset | Field | Value |
|--------|-------|-------|
| 0x00 | Field1 | `0x00000016` |
| 0x04 | Field2 | `0x00FEDBAC` |
| 0x08 | Field3 | `0x000000C5` |
| 0x0C | UncompSize | uncompressed_size |
| 0x10-0x1F | Magic | `0x57FBAA33`, `0x1004FA99`, `0x00020001`, `0x01000080` |
| 0x20 | CompSize | compressed_size |
| 0x24 | UncompSize2 | uncompressed_size |
| 0x28 | Checksum | Zero-seed Adler-32 |

---

## Call Sequence with Function Addresses

### Entry Point: FUN_005e3560 (Section 1 Serializer)

The Section 1 serializer makes exactly 16 serialization calls in this order:

```c
void __thiscall FUN_005e3560(int param_1, int param_2) {
    // Store context reference
    *(int *)(param_2 + 0x1c) = param_1;

    // 1. Root Registration - "SaveGame" with hash 0xBDBE3B52 (conditional)
    if (*(char *)(*(int *)(param_2 + 4) + 4) == '\0') {
        uVar1 = FUN_01afc2c0(param_1, 0, 1);
        uVar2 = FUN_01afb8a0(param_1);
        FUN_01b09e20("SaveGame", 0, 0xbdbe3b52, uVar1, uVar2);
    }

    // 2. ManagedObject Wrapper - hash 0xBB96607D
    uVar1 = *(undefined4 *)(param_2 + 0x20);
    *(undefined4 *)(param_2 + 0x20) = 0;
    FUN_01b17f90(param_2);
    *(undefined4 *)(param_2 + 0x20) = uVar1;

    // 3-7. Complex Serializers (5 calls) - 4-byte values
    FUN_01b0a1f0(param_1 + 0x10, PTR_DAT_027ecf54);  // hash 0x70A1EA5F
    FUN_01b0a1f0(param_1 + 0x14, PTR_DAT_027ecf58);  // hash 0x2578300E
    FUN_01b0a1f0(param_1 + 0x18, PTR_DAT_027ecf5c);  // hash 0xF5C71F6B
    FUN_01b0a1f0(param_1 + 0x1c, PTR_DAT_027ecf60);  // hash 0xBB6621D2
    FUN_01b0a1f0(param_1 + 0x20, PTR_DAT_027ecf64);  // hash 0x28550876

    // 8. Boolean Serializer - 1-byte value
    FUN_01b09650(param_1 + 0x49, PTR_DAT_027ecf68);  // hash 0x34032BE4

    // 9. Value Serializer - string "Options"
    FUN_01b09980(param_1 + 0x24, PTR_DAT_027ecf6c);  // hash 0x78BD5067

    // 10-11. ClassID Serializers (2 calls) - Pointer types
    FUN_01b099a0(0xfbb63e47, param_1 + 0x28, PTR_DAT_027ecf70);  // hash 0x7111FCC2
    FUN_01b099a0(0x5fdacba0, param_1 + 0x2c, PTR_DAT_027ecf74);  // hash 0x6C448E95

    // 12-14. Complex Serializers (3 more calls)
    FUN_01b0a1f0(param_1 + 0x30, PTR_DAT_027ecf78);  // hash 0xEB76C432
    FUN_01b0a1f0(param_1 + 0x34, PTR_DAT_027ecf7c);  // hash 0x28F5132B
    FUN_01b0a1f0(param_1 + 0x38, PTR_DAT_027ecf80);  // hash 0x8C00191B

    // 15. Property Iterator - remaining properties
    FUN_01b09620(param_1 + 0x4c);

    // 16. Object Closer
    FUN_01b0d0c0();
}
```

### Function Reference Table

| Address | Function Name | Purpose | Output Size |
|---------|---------------|---------|-------------|
| 0x005e3560 | Section1Serializer | Entry point for Section 1 | Variable |
| 0x01b09e20 | RootRegistration | Registers "SaveGame" root object | Variable |
| 0x01b08ce0 | RootObjectHeaderWriter | Writes root object header | Variable |
| 0x01b17f90 | ManagedObjectWrapper | Wraps with hash 0xBB96607D | 0 bytes (wrapper) |
| 0x01b0a1f0 | ComplexSerializer | Wrapper for FUN_01b12fa0 | 21 bytes |
| 0x01b12fa0 | ComplexSerializerCore | Core logic for complex types | 21 bytes |
| 0x01b09650 | BooleanSerializer | Wrapper for FUN_01b11fb0 | 18 bytes |
| 0x01b11fb0 | BooleanSerializerCore | Core logic for booleans | 18 bytes |
| 0x01b09880 | NumericSerializer | Numeric value serializer | 21 bytes |
| 0x01b09980 | ValueSerializer | Serializes strings/enums | 25+ bytes |
| 0x01b12cf0 | ValueSerializerCore | Core logic for strings | Variable |
| 0x01b099a0 | ClassIDSerializer | Serializes pointers with ClassID | 21 bytes |
| 0x01b09620 | PropertyIterator | Iterates sub-properties | Variable |
| 0x01b0d0c0 | ObjectCloser | Closes Property/Object blocks | 0 bytes |
| 0x01b07940 | PropertyValidator | Validates property before serialization | 0 bytes |
| 0x01b0d140 | PropertyHeaderWriter | Writes property header (N+T+PackedInfo) | 13-17 bytes |
| 0x01b0e680 | NBlockWriter | Writes PropertyID hash | 4 bytes |
| 0x01b0e980 | TBlockWriter | Writes ClassID + type_id | 8 bytes |
| 0x01b496d0 | TBlockDataWriter | Writes T-block content via vtable | 8 bytes |
| 0x01b076f0 | PackedInfoWriter | Writes PackedInfo byte | 1 byte |
| 0x01b0c2e0 | TypeDispatcher | Routes to appropriate serializer | - |
| 0x01b48700 | FlushPendingAndWrite | Flush pending queue, write value | Variable |
| 0x01b487b0 | AddToPendingQueue | Queue Type prefix from TBlockData | 0 bytes |
| 0x01b48890 | BeginBlock | Opens block, reserves Type prefix space | 4 bytes |
| 0x01b48920 | EndBlock | Closes block, writes accumulated Type | 0 bytes |
| 0x01b489b0 | PopBlock | Decrement nesting, adjust offsets | 0 bytes |
| 0x01b49020 | TBlockData | Get current T-block data | 0 bytes |
| 0x01b49090 | ContextCleanup | Flush pending, cleanup stream | 0 bytes |
| 0x01b49b10 | Destructor | Cleanup and free context | 0 bytes |
| 0x01b48e90 | WriteString | String serialization with length | Variable |
| 0x01b48a10 | HasMore | Check if more items in block (size > 0) | 0 bytes |
| 0x01b0d000 | PropertyReader | Deserializer loop for properties | 0 bytes |
| 0x01b0d420 | VersionWriter | Write version fields (2 bytes via vtable+0x8c) | 2 bytes |

### Master Call Flow Diagram

```
FUN_005e3560 (Section1Serializer)
│
├─► FUN_01b09e20 (RootRegistration) ──► Mode 1/2/3 (skips Type prefix)
│   └─► FUN_01b08ce0 (RootObjectHeaderWriter)
│       ├─► vtable+0x8c ("SerializerVersion") - 2 bytes
│       ├─► vtable+0x8c ("ClassVersion") - 2 bytes
│       ├─► vtable+0x54 ("ObjectName") - string
│       ├─► vtable+0x9c ("ObjectID") - 4 bytes
│       ├─► vtable+0x84 ("InstanceOf") - 4 bytes
│       └─► vtable+0x50 ("T" block) - root hash
│
├─► FUN_01b17f90 (ManagedObjectWrapper)
│   ├─► vtable+0x18 (RegisterNestedObject)
│   └─► FUN_01b0d0c0 (ObjectCloser) - closes immediately
│
├─► FUN_01b0a1f0 x8 (ComplexSerializer) ──► Mode 0 (writes Type prefix 0x11)
│   └─► FUN_01b12fa0 (ComplexSerializerCore)
│       ├─► FUN_01b07940 (PropertyValidator)
│       ├─► FUN_01b0d140 (PropertyHeaderWriter)
│       │   ├─► vtable+0x0c ("Property") ──► FUN_01b48890 (reserves 4 bytes)
│       │   ├─► FUN_01b0e680 (N-block: Hash)
│       │   │   ├─► vtable+0x08 (BeginBlock "N")
│       │   │   ├─► vtable+0x50 (Write hash)
│       │   │   └─► vtable+0x10 (EndBlock "N")
│       │   ├─► FUN_01b0e980 (T-block: ClassID + type_id)
│       │   │   ├─► vtable+0x08 (BeginBlock "T")
│       │   │   ├─► vtable+0x4c ──► FUN_01b496d0 (Write 8 bytes)
│       │   │   └─► vtable+0x10 (EndBlock "T")
│       │   └─► FUN_01b076f0 (PackedInfo: 0x0B/0x0F)
│       ├─► vtable+0x08 ("Value")
│       ├─► vtable+0x84 (Write 4-byte value)
│       ├─► vtable+0x10 ("Value")
│       └─► vtable+0x14 ("Property") ──► FUN_01b48920 (writes Type prefix)
│
├─► FUN_01b09650 (BooleanSerializer) ──► Mode 0 (writes Type prefix 0x0E)
│   └─► FUN_01b11fb0 (BooleanSerializerCore)
│       ├─► FUN_01b07940 (PropertyValidator)
│       ├─► FUN_01b0d140 (PropertyHeaderWriter) - same as above
│       ├─► vtable+0x08 ("Value")
│       ├─► vtable+0x58 (Write 1-byte value)
│       ├─► vtable+0x10 ("Value")
│       └─► vtable+0x14 ("Property")
│
├─► FUN_01b09980 (ValueSerializer/Enum) ──► Mode 0 (writes Type prefix 0x19)
│   └─► FUN_01b12cf0 (ValueSerializerCore)
│       ├─► FUN_01b07940 (PropertyValidator)
│       ├─► FUN_01b0d140 (PropertyHeaderWriter)
│       ├─► vtable+0x08 ("Value")
│       ├─► vtable+0x48 (Write string: len + chars + null)
│       ├─► vtable+0x10 ("Value")
│       └─► vtable+0x14 ("Property")
│
├─► FUN_01b099a0 x2 (ClassIDSerializer) ──► Mode 0 (writes Type prefix 0x11)
│   ├─► FUN_01b07940 (PropertyValidator)
│   ├─► FUN_01b0d140 (PropertyHeaderWriter)
│   ├─► vtable+0x08 ("Value")
│   ├─► vtable+0x9c (Write 4-byte pointer value)
│   ├─► vtable+0x10 ("Value")
│   └─► vtable+0x14 ("Property")
│
├─► FUN_01b09620 (PropertyIterator)
│   └─► FUN_01b0c2e0 (TypeDispatcher) - for each sub-property
│
└─► FUN_01b0d0c0 (ObjectCloser)
    ├─► EndBlock("Properties")
    └─► EndBlock("Object")
```

---

## Binary Layout with Exact Byte Offsets

### Decompressed Section 1 Structure

```
Offset   Size  Field                  Description
------   ----  -----                  -----------
0x00     10    Zero Prefix            Leading zeros (from LZSS compression layer)
0x0A     4     Container Hash         0xBDBE3B52 ("SaveGame")
0x0E     4     Object Block Size      265 = size from 0x12 to EOF (BeginBlock "Object")
0x12     4     Properties Block Size  257 = size from 0x16 to 0x117 (BeginBlock "Properties")
0x16     4     Root Block Size        17 = root property content size (BeginBlock "Property")
0x1A     17    Root Property          First property content (NO Type prefix, HAS block size)
0x2B     21+   Child Properties       Variable-size records (WITH Type prefix, NO block size)
...      4     End Marker             0x00000000 (Dynamic Properties block size = 0)
```

### Block Structure (RE Verified via WinDbg)

The container uses nested BeginBlock calls from FUN_01b08ce0 and FUN_01b0d140:

```
Object Block (size=265, offset 0x0E)
└── Properties Block (size=257, offset 0x12)
    └── Root Property Block (size=17, offset 0x16)
        └── Root content: Hash+ClassID+type_id+PackedInfo+Value (17 bytes)
    └── Child properties (NO individual blocks, just Type prefix each)
    └── End marker (0x00000000)
└── Dynamic Properties Block (size=0, empty)
```

**Key Finding:** Mode is always 0, but:
- **Root property:** Gets BeginBlock("Property") → block size at 0x16, but NO Type prefix
- **Child properties:** Skip BeginBlock (flag at ctx+0x4e & 1), but WRITE Type prefix

### Root Property Record Structure (17 bytes content + 4 bytes block size)

The root property:
- **HAS** a 4-byte block size prefix (BeginBlock "Property" is called)
- Does **NOT** have a Type prefix (special handling for first property)

```
Offset  Size  Field           Description
------  ----  -----           -----------
-0x04   4     Block Size      17 (from BeginBlock, at offset 0x16 in file)
+0x00   4     Hash            PropertyID hash (e.g., 0x70A1EA5F)
+0x04   4     ClassID         Class identifier (0 for most properties)
+0x08   4     type_id        Type/flags field (type extracted via formula)
+0x0C   1     PackedInfo      0x0B or 0x0F
+0x0D   4     Value           4-byte value
------
Content: 17 bytes (matches block size)
```

### Child Property Record Structure (with Type prefix, NO block size)

Child properties:
- Do **NOT** have a block size prefix (BeginBlock skipped via ctx+0x4e flag)
- **HAVE** a 4-byte Type prefix

```
Offset  Size  Field           Description
------  ----  -----           -----------
+0x00   4     Type            Type prefix (0x11=Numeric, 0x0E=BoolAlt, 0x19=Enum)
+0x04   4     Hash            PropertyID hash
+0x08   4     ClassID         Class identifier (0 or specific class hash)
+0x0C   4     type_id        Type/flags field
+0x10   1     PackedInfo      0x0B or 0x0F
+0x11   var   Value           Value (size depends on type)
------
Total: 21 bytes (4-byte values), 18 bytes (1-byte bool), 25+ bytes (strings)
```

### Binary Layout Example (First 48 bytes)

```
Offset  Hex                                 Description
------  ---                                 -----------
0x00    00 00 00 00 00 00 00 00 00 00      Zero Prefix (10 bytes)
0x0A    52 3B BE BD                        Container Hash: 0xBDBE3B52
0x0E    09 01 00 00                        Object Block Size: 265
0x12    01 01 00 00                        Properties Block Size: 257
0x16    11 00 00 00                        Root Block Size: 17 (BeginBlock "Property")
0x1A    5F EA A1 70                        Root Hash: 0x70A1EA5F (NO Type prefix!)
0x1E    00 00 00 00                        Root ClassID: 0
0x22    00 00 07 00                        Root type_id: 0x00070000 (Type = Complex)
0x26    0B                                 Root PackedInfo: 0x0B
0x27    16 00 00 00                        Root Value: 22
--- Root property ends at 0x2A (17 bytes from 0x1A) ---
0x2B    11 00 00 00                        Child #1 Type prefix: 0x11 (NO block size!)
0x2F    0E 30 78 25                        Child #1 Hash: 0x2578300E
0x33    00 00 00 00                        Child #1 ClassID: 0
0x37    00 00 07 00                        Child #1 type_id: 0x00070000
0x3B    0B                                 Child #1 PackedInfo: 0x0B
0x3C    AC DB FE 00                        Child #1 Value: 16702380
...
```

---

## Property Descriptor Structure

Property descriptors are stored in memory and contain metadata about each property.

### Descriptor Layout (32 bytes)

```
Offset  Size  Field           Description
------  ----  -----           -----------
+0x00   4     Flags           Control flags; bit 17 used for PackedInfo calculation
+0x04   4     PropertyID      Property hash (e.g., 0x70A1EA5F)
+0x08   4     ClassID         Class identifier (e.g., 0xFBB63E47)
+0x0C   4     type_id        Type/flags; type = (type_id >> 16) & 0x3F
+0x10   4     Unknown1        Additional metadata (observed: 0x00400000, 0x00500000, etc.)
+0x14   12    Unknown2-4      Reserved/padding
```

### Complete Descriptor Table (Section 1)

| Address | Flags | PropertyID | ClassID | type_id | Type Code | Type Name |
|---------|-------|------------|---------|----------|-----------|-----------|
| 027ecd98 | 0x02000001 | 0x70A1EA5F | 0x00000000 | 0x00070000 | 0x07 | Complex |
| 027ecdb8 | 0x02000001 | 0x2578300E | 0x00000000 | 0x00070000 | 0x07 | Complex |
| 027ecdd8 | 0x02000001 | 0xF5C71F6B | 0x00000000 | 0x00070000 | 0x07 | Complex |
| 027ecdf8 | 0x02000001 | 0xBB6621D2 | 0x00000000 | 0x00070000 | 0x07 | Complex |
| 027ece18 | 0x02000001 | 0x28550876 | 0x00000000 | 0x00070000 | 0x07 | Complex |
| 027ece38 | 0x02000001 | 0x34032BE4 | 0x00000000 | 0x00000000 | 0x00 | Bool |
| 027ece58 | 0x02000001 | 0x78BD5067 | 0x00000000 | 0x001A0000 | 0x1A | String |
| 027ece78 | 0x02000001 | 0x7111FCC2 | 0xFBB63E47 | 0x00120000 | 0x12 | Pointer |
| 027ece98 | 0x02000001 | 0x6C448E95 | 0x5FDACBA0 | 0x00120000 | 0x12 | Pointer |
| 027eceb8 | 0x02000001 | 0xEB76C432 | 0x00000000 | 0x00070000 | 0x07 | Complex |
| 027eced8 | 0x02000001 | 0x28F5132B | 0x00000000 | 0x00070000 | 0x07 | Complex |
| 027ecef8 | 0x02000001 | 0x8C00191B | 0x00000000 | 0x00070000 | 0x07 | Complex |

### Descriptor Pointer Table

| Pointer Address | Target Descriptor | PropertyID |
|-----------------|-------------------|------------|
| 027ecf54 | DAT_027ecd98 | 0x70A1EA5F |
| 027ecf58 | DAT_027ecdb8 | 0x2578300E |
| 027ecf5c | DAT_027ecdd8 | 0xF5C71F6B |
| 027ecf60 | DAT_027ecdf8 | 0xBB6621D2 |
| 027ecf64 | DAT_027ece18 | 0x28550876 |
| 027ecf68 | DAT_027ece38 | 0x34032BE4 |
| 027ecf6c | DAT_027ece58 | 0x78BD5067 |
| 027ecf70 | DAT_027ece78 | 0x7111FCC2 |
| 027ecf74 | DAT_027ece98 | 0x6C448E95 |
| 027ecf78 | DAT_027eceb8 | 0xEB76C432 |
| 027ecf7c | DAT_027eced8 | 0x28F5132B |
| 027ecf80 | DAT_027ecef8 | 0x8C00191B |

### PackedInfo Calculation (VERIFIED)

**Assembly trace from FUN_01b0d140 @ 01b0d269-01b0d2ac:**

```asm
01b0d269 8b 03           MOV  EAX,[EBX]        ; EAX = descriptor[0] = Flags
01b0d26b c1 e8 11        SHR  EAX,0x11         ; >> 17
01b0d26e 24 01           AND  AL,0x1           ; & 1
01b0d270 02 c0           ADD  AL,AL            ; * 2
01b0d272 02 c0           ADD  AL,AL            ; * 4
; ... then at LAB_01b0d2a4 (common path when EDI == 0):
01b0d2a4 24 ef           AND  AL,0xef          ; clear bit 4
01b0d2a6 0c 0b           OR   AL,0xb           ; | 0x0B
01b0d2ac e8 3f a4        CALL FUN_01b076f0     ; write PackedInfo
```

**Formula:**
```c
temp = ((Flags >> 17) & 1) * 4
PackedInfo = (temp & 0xEF) | 0x0B
```

**Verified trace for Section 1:**
```
FUN_005e3560 passes PTR_DAT_027ecf54
    → PTR_DAT_027ecf54 (@ 027ecf54) contains address 027ecd98
        → DAT_027ecd98[0x00] = 0x02000001 (Flags)
            → bit 17 of 0x02000001 = 0
                → temp = 0 * 4 = 0
                    → PackedInfo = (0 & 0xEF) | 0x0B = 0x0B
```

**Result:** PackedInfo = **0x0B** (computed, not preserved)

### String Length Computation (VERIFIED)

**Traced from FUN_01b12cf0 → vtable+0x48 → FUN_01b492f0 → FUN_01b49920:**

```c
// FUN_01b49920 - strlen computation
pcVar4 = (char *)*param_2;  // Get string pointer
if (pcVar4 == (char *)0x0) {
    local_8 = 0;
}
else {
    pcVar1 = pcVar4 + 1;
    do {
        cVar2 = *pcVar4;
        pcVar4 = pcVar4 + 1;
    } while (cVar2 != '\0');
    local_8 = (int)pcVar4 - (int)pcVar1;  // strlen!
}
(**(code **)(*param_1 + 0x84))(&local_8);  // Write length (4 bytes)
// Then writes string + null via vtable+0x40
```

**Result:** string_length = **strlen(string)** (computed, not preserved)

---

## Type System and Dispatch

### Type Extraction Formula

From FUN_01b0c2e0:

```c
// Standard mode (param_4 == 0): shift by 16
// Array element mode (param_4 != 0): shift by 23
int shift = (param_4 == '\0') ? 0x10 : 0x17;
int type_code = (type_id >> shift) & 0x3F;
```

### Complete Type Dispatch Table (FUN_01b0c2e0)

| Case | Hex | Function | Type Name | Value Size |
|------|-----|----------|-----------|------------|
| 0 | 0x00 | FUN_01b09650 | Bool | 1 byte |
| 1 | 0x01 | FUN_01b12060 | Unknown | - |
| 2 | 0x02 | FUN_01b121e0 | Unknown | - |
| 3 | 0x03 | FUN_01b12120 | Unknown | - |
| 4 | 0x04 | FUN_01b12360 | Unknown | - |
| 5 | 0x05 | FUN_01b122a0 | Unknown | - |
| 6 | 0x06 | FUN_01b12420 | Unknown | - |
| 7 | 0x07 | FUN_01b12fa0 | Complex | 4 bytes |
| 8 | 0x08 | FUN_01b12590 | Unknown | - |
| 9 | 0x09 | FUN_01b124e0 | Unknown | - |
| 10 | 0x0A | FUN_01b12640 | Unknown | - |
| 11 | 0x0B | FUN_01b126f0 | Unknown | - |
| 12 | 0x0C | FUN_01b127a0 | Unknown | - |
| 13 | 0x0D | FUN_01b12850 | Unknown | - |
| 14 | 0x0E | FUN_01b12a60 | BoolAlt | 1 byte |
| 15 | 0x0F | FUN_01b12900 | Unknown | - |
| 16 | 0x10 | FUN_01b129b0 | Unknown | - |
| 17 | 0x11 | FUN_01b09880 | Numeric | 4 bytes |
| 18 | 0x12 | FUN_01b099a0 | Pointer | 4 bytes |
| 19 | 0x13 | FUN_01b0a460 | Unknown | - |
| 20 | 0x14 | FUN_01b0b2c0 | Unknown | - |
| 21 | 0x15 | FUN_01b0b8a0 | Unknown | Variable |
| 22 | 0x16 | FUN_01b0b710 | Unknown | Variable |
| 23 | 0x17 | (inline) | Array | Variable |
| 24 | 0x18 | (inline) | Container | Variable |
| 25 | 0x19 | FUN_01b09c10 | Enum | Variable |
| 26 | 0x1A | FUN_01b12cf0 | String | Variable |
| 27 | 0x1B | FUN_01b13180 | Unknown | - |
| 28 | 0x1C | FUN_01b0ae60 | Unknown | - |
| 29 | 0x1D | (inline) | Container | Variable |
| 30 | 0x1E | FUN_01b099a0 | PointerAlt | 4 bytes |

---

## Type Prefix Mapping (RESOLVED)

### Critical Discovery

The **Type prefix** written to the binary is **NOT** the same as the descriptor type code. The Type prefix indicates which **deserialization handler** to use when reading the file.

### Serializer → Type Prefix Mapping

| Serializer Function | Descriptor Type | Binary Type Prefix | Purpose |
|---------------------|-----------------|-------------------|---------|
| FUN_01b0a1f0 (Complex) | 0x07 | **0x11** | 4-byte numeric format |
| FUN_01b09650 (Boolean) | 0x00 | **0x0E** | 1-byte boolean format |
| FUN_01b09980 (Enum) | 0x1A | **0x19** | String format |
| FUN_01b099a0 (Pointer) | 0x12 | **0x11** | 4-byte numeric format |

### Mapping Logic

```
Descriptor Type → Serializer → Binary Type Prefix → Deserializer

0x07 (Complex)  → FUN_01b12fa0 → 0x11 → FUN_01b09880 (Numeric)
0x00 (Bool)     → FUN_01b11fb0 → 0x0E → FUN_01b12a60 (BoolAlt)
0x1A (String)   → FUN_01b12cf0 → 0x19 → FUN_01b09c10 (Enum)
0x12 (Pointer)  → FUN_01b099a0 → 0x11 → FUN_01b09880 (Numeric)
```

### Type Prefix Diagram

```
SERIALIZATION:                          DESERIALIZATION:

Descriptor          Serializer          Binary      Deserializer
type_id            Function            Type        Switch Case
───────────         ──────────          ────        ───────────

0x00070000 ──┬──► FUN_01b12fa0 ────► 0x11 ────► case 0x11 (FUN_01b09880)
(Complex)    │    (Complex)           │          (Numeric)
             │                        │
0x00120000 ──┘                        │
(Pointer)  ──────► FUN_01b099a0 ──────┘
                   (ClassID)

0x00000000 ──────► FUN_01b11fb0 ────► 0x0E ────► case 0x0E (FUN_01b12a60)
(Bool)             (Boolean)                     (BoolAlt)

0x001A0000 ──────► FUN_01b12cf0 ────► 0x19 ────► case 0x19 (FUN_01b09c10)
(String)           (Value)                       (Enum)
```

---

## Root vs Child Property Serialization

### Mode-Based Header Skip (RESOLVED)

The key to understanding why root properties lack Type prefixes is in FUN_01b0d140:

```c
undefined4 __thiscall FUN_01b0d140(int param_1, uint *param_2) {
    int iVar3 = *(int *)(param_1 + 0x58);  // Get serialization mode

    // SKIP header writing for modes 1, 2, 3 or flag 0x01
    if ((((iVar3 == 1) || (iVar3 == 2)) || (iVar3 == 3)) ||
        ((*(byte *)(param_1 + 0x4e) & 1) != 0)) {
        return 1;  // Return early - NO header written!
    }

    // Mode 0: Write full property header including Type prefix
    (**(code **)(**(int **)(param_1 + 4) + 0xc))("Property");  // BeginBlock
    // ... write N-block, T-block, PackedInfo ...
}
```

### Serialization Modes

| Mode | Value at ctx+0x58 | Header Written | Type Prefix | Used For |
|------|-------------------|----------------|-------------|----------|
| 0 | Normal | Full header | YES | Child properties |
| 1 | Root | Skipped | NO | Root registration |
| 2 | Nested | Skipped | NO | Nested objects |
| 3 | Special | Skipped | NO | Special cases |

### Root vs Child Comparison

```
ROOT PROPERTY (Mode 1/2/3):
┌─────────────────────────────────────────────────────┐
│ FUN_01b09e20 (RootRegistration)                     │
│   ↓                                                 │
│ FUN_01b12fa0 (ComplexSerializerCore)               │
│   ↓                                                 │
│ FUN_01b0d140 checks mode → mode != 0 → RETURN 1    │
│   ↓                                                 │
│ NO PropertyHeaderWriter execution                   │
│   ↓                                                 │
│ Binary: [Hash][ClassID][type_id][PackedInfo][Value] │
│         (17 bytes - no Type prefix)                 │
└─────────────────────────────────────────────────────┘

CHILD PROPERTY (Mode 0):
┌─────────────────────────────────────────────────────┐
│ FUN_01b0a1f0 (ComplexSerializer)                   │
│   ↓                                                 │
│ FUN_01b12fa0 (ComplexSerializerCore)               │
│   ↓                                                 │
│ FUN_01b0d140 checks mode → mode == 0 → CONTINUE    │
│   ↓                                                 │
│ vtable+0x0c ("Property") → reserves 4 bytes        │
│ FUN_01b0e680 (N-block) → writes Hash               │
│ FUN_01b0e980 (T-block) → writes ClassID + type_id   │
│ FUN_01b076f0 → writes PackedInfo                   │
│   ↓                                                 │
│ vtable+0x14 ("Property") → writes Type prefix      │
│   ↓                                                 │
│ Binary: [Type][Hash][ClassID][type_id][PackedInfo]  │
│         [Value] (21 bytes - has Type prefix)       │
└─────────────────────────────────────────────────────┘
```

---

## Serializer Context Structure

### Context Layout (param_1 in serializer functions)

The serializer context contains state for the serialization process:

```
Offset    Size  Field              Description
------    ----  -----              -----------
+0x04     4     write_mode         0 = write mode, non-zero = read mode
+0x08     4     stream_ptr         Pointer to underlying stream/writer vtable
+0x0c     76    block_stack        Stack for nested blocks (entries at +0x10, +0x14 per level)
+0x1c     4     object_ptr         Current object being serialized
+0x24     4     version            Serializer version
+0x2c     4     descriptor_ptr     Current property descriptor
+0x4e     1     flags              Control flags (bit 0 = skip header, etc.)
+0x4f     1     flags2             Additional flags (bit 1 = special mode)
+0x58     4     mode               Serialization mode (0=normal, 1/2/3=skip header)
+0x79     1     validator_flag1    Set by FUN_01b07940
+0x7a     1     validator_flag2    Set by FUN_01b07940
+0x7c     4     mode2              Secondary mode
+0x1010   2     stack_counter      Block nesting counter (ushort)
+0x1012   1     tblock_flag        T-block write flag
+0x1014   64    pending_queue      Queue of pending 4-byte values (16 entries max)
+0x1054   4     pending_count      Number of items in pending queue
```

### Pending Queue Mechanism

The pending queue at ctx+0x1014 buffers Type prefix values during nested serialization:

```
┌─────────────────────────────────────────────────────────────────┐
│ FUN_01b487b0 (AddToPendingQueue / vtable+0x24)                  │
│   ├─► Calls vtable+0x4c (TBlockData) to get Type prefix value  │
│   ├─► Stores at ctx+0x1014[pending_count]                      │
│   └─► Increments ctx+0x1054                                    │
├─────────────────────────────────────────────────────────────────┤
│                    ... serialization continues ...              │
├─────────────────────────────────────────────────────────────────┤
│ FUN_01b48700 (FlushPendingAndWrite / vtable+0x30)               │
│   ├─► Loops through ctx+0x1014 array                           │
│   │   └─► Calls vtable+0x54 for each pending item              │
│   ├─► Resets ctx+0x1054 to 0                                   │
│   └─► Calls vtable+0x04 to write final value                   │
└─────────────────────────────────────────────────────────────────┘
```

### Mode and Flag Interactions

```c
// FUN_01b0d140 - PropertyHeaderWriter
if (mode == 1 || mode == 2 || mode == 3 || (flags & 0x01)) {
    return 1;  // Skip header
}

// FUN_01b12fa0/FUN_01b11fb0 - End of serialization
if (mode != 1 && mode != 2 && mode != 3 && !(flags & 0x01)) {
    vtable+0x14("Property");  // End block, write Type prefix
}
```

---

## Block Nesting Mechanism

### Stack-Based Block Tracking

The serializer uses a stack to track nested blocks. Each block level has:
- **Size accumulator** (offset +8 from base)
- **Type value** (offset +0x10 from base)
- **Position** (offset +0x14 from base)

### Block Stack Structure

```
Base + 0x08 + counter*8 : Size accumulator for this level
Base + 0x10 + counter*8 : Block value (becomes Type prefix)
Base + 0x14 + counter*8 : Write position
```

### BeginBlock Flow (FUN_01b48890)

```c
uint __fastcall FUN_01b48890(int param_1) {
    if (*(char *)(param_1 + 4) == '\0') {  // Write mode
        // Get current write position
        uVar2 = (**(code **)(**(int **)(param_1 + 8) + 0x4c))();

        // Store position for later backpatching
        *(uint *)(param_1 + 0x14 + counter * 8) = uVar2;

        // Initialize block value to 0
        *(uint *)(param_1 + 0x10 + counter * 8) = 0;

        // Reserve 4 bytes for Type prefix
        uVar3 = (**(code **)(**(int **)(param_1 + 8) + 0x44))(4);

        // Increment counter
        *(short *)(param_1 + 0x1010) = counter + 1;

        return uVar3;
    }
    // ... read mode handling
}
```

### EndBlock Flow (FUN_01b48920)

```c
void __fastcall FUN_01b48920(int *param_1) {
    if ((char)param_1[1] == '\0') {  // Write mode
        // Decrement counter
        uVar2 = *(ushort *)(param_1 + 0x404) - 1;

        // Read accumulated Type value from stack
        iVar1 = param_1[counter * 2 + 2];

        *(ushort *)(param_1 + 0x404) = uVar2;

        // Seek to reserved position
        (**(code **)(*(int *)param_1[2] + 0x50))(param_1[uVar2 * 2 + 5]);

        // Write Type prefix at reserved position
        (**(code **)(*(int *)param_1[2] + 0x34))(iVar1);

        // Restore position
        (**(code **)(*(int *)param_1[2] + 0x54))(param_1[counter * 2 + 5]);
        (**(code **)(*(int *)param_1[2] + 0x58))();
    }
}
```

### Block Nesting Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ BeginBlock("Property")                                           │
│   counter: 0 → 1                                                 │
│   stack[0].value = 0                                             │
│   stack[0].position = current_pos                                │
│   RESERVE 4 bytes for Type prefix                                │
├─────────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ BeginBlock("N")                                             │ │
│ │   counter: 1 → 2                                            │ │
│ │   Write PropertyID hash (4 bytes)                           │ │
│ │ EndBlock("N")                                               │ │
│ │   counter: 2 → 1                                            │ │
│ └─────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ BeginBlock("T")                                             │ │
│ │   counter: 1 → 2                                            │ │
│ │   FUN_01b496d0: stack[1].size += 8                          │ │
│ │   Write ClassID + type_id (8 bytes)                        │ │
│ │ EndBlock("T")                                               │ │
│ │   counter: 2 → 1                                            │ │
│ └─────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│ Write PackedInfo (1 byte)                                        │
├─────────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ BeginBlock("Value")                                         │ │
│ │   Write value (1/4/variable bytes)                          │ │
│ │ EndBlock("Value")                                           │ │
│ └─────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│ EndBlock("Property")                                             │
│   counter: 1 → 0                                                 │
│   SEEK to stack[0].position                                      │
│   WRITE stack[0].value as Type prefix                            │
│   (value accumulated during block processing)                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Value Encoding by Type

### Type 0x07/0x11 - Complex/Numeric (4-byte value)

Standard 21-byte child record (17-byte root record):

```
Child:  [Type:4][Hash:4][ClassID:4][type_id:4][PackedInfo:1][Value:4]
Root:   [Hash:4][ClassID:4][type_id:4][PackedInfo:1][Value:4]
```

Example (hash 0x2578300E, value 16702380):
```
11 00 00 00    Type: 0x11 (Numeric)
0E 30 78 25    Hash: 0x2578300E
00 00 00 00    ClassID: 0
00 00 07 00    type_id: 0x00070000 (Complex)
0B             PackedInfo: 0x0B
AC DB FE 00    Value: 16702380 (0x00FEDBAC)
```

### Type 0x0E - BoolAlt (1-byte value)

18-byte child record:

```
Child:  [Type:4][Hash:4][ClassID:4][type_id:4][PackedInfo:1][Value:1]
```

Example (hash 0x34032BE4, value 1):
```
0E 00 00 00    Type: 0x0E (BoolAlt)
E4 2B 03 34    Hash: 0x34032BE4
00 00 00 00    ClassID: 0
00 00 00 00    type_id: 0x00000000 (Bool)
0B             PackedInfo: 0x0B
01             Value: 1 (true)
```

### Type 0x19 - Enum (String value)

Variable-size child record:

```
Child:  [Type:4][Hash:4][ClassID:4][type_id:4][PackedInfo:1][Length:4][String:N][Null:1]
```

Example (hash 0x78BD5067, value "Options"):
```
19 00 00 00    Type: 0x19 (Enum)
67 50 BD 78    Hash: 0x78BD5067
00 00 00 00    ClassID: 0
00 00 1A 00    type_id: 0x001A0000 (String)
0B             PackedInfo: 0x0B
07 00 00 00    String length: 7
4F 70 74 69    "Opti"
6F 6E 73 00    "ons" + null
```

Total size: 4 + 4 + 4 + 4 + 1 + 4 + 7 + 1 = 29 bytes

### Type 0x12 - Pointer (4-byte value with ClassID)

21-byte child record with non-zero ClassID:

```
Child:  [Type:4][Hash:4][ClassID:4][type_id:4][PackedInfo:1][Value:4]
```

Example (hash 0x7111FCC2, ClassID 0xFBB63E47, value 0):
```
11 00 00 00    Type: 0x11 (Numeric format for Pointer)
C2 FC 11 71    Hash: 0x7111FCC2
47 3E B6 FB    ClassID: 0xFBB63E47 (non-zero!)
00 00 12 00    type_id: 0x00120000 (Pointer)
0B             PackedInfo: 0x0B
00 00 00 00    Value: 0 (null pointer)
```

---

## Vtable Methods Used

### Serializer Writer Class (vtable @ 0x02555c60)

Complete vtable mapping with 40 entries:

| Offset | Address | Function | Purpose |
|--------|---------|----------|---------|
| +0x00 | 01b49b10 | Destructor | Cleanup and optionally free context |
| +0x04 | 01b48830 | Write4Bytes | Write 4-byte value to stream |
| +0x08 | 01b48770 | BeginBlockNoop | No-op stub (RET 0x4) |
| +0x0c | 01b48890 | BeginBlockReserve | Begin block, reserve 4 bytes for Type |
| +0x10 | 01b487a0 | EndBlockNoop | No-op stub (RET 0x4) |
| +0x14 | 01b48920 | EndBlockWrite | End block, backpatch Type prefix |
| +0x18 | 01b489b0 | PopBlock | Decrement nesting, adjust offsets |
| +0x1c | 01b48a10 | CheckNested | Check if block is nested |
| +0x20 | 01b48780 | GetStackCounter | Get current nesting level |
| +0x24 | 01b487b0 | **AddToPendingQueue** | Queue Type prefix from TBlockData |
| +0x28 | 01b487e0 | WritePendingItem | Write queued item via vtable+0x50 |
| +0x2c | 01b48800 | WritePendingItemAlt | Write queued item via vtable+0x5c |
| +0x30 | 01b48700 | **FlushPendingAndWrite** | Flush queue, then write value |
| +0x34 | 01b48760 | CallVtable8 | Indirect call to vtable+0x08 |
| +0x38 | 01b48820 | Unknown | - |
| +0x3c | 01b48b10 | Unknown | - |
| +0x40 | 01b48a30 | WriteRaw | Write raw bytes |
| +0x44 | 01b49300 | Reserve | Reserve N bytes in stream |
| +0x48 | 01b492f0 | StringWriter | Write strlen(4) + string + null (computes length) |
| +0x4c | 01b49020 | TBlockData | Get/write T-block via FUN_01b496d0 |
| +0x50 | 01b48fb0 | NBlockData | Write PropertyID hash |
| +0x54 | 01b48e90 | WriteString | String serialization with length calc |
| +0x58 | 01b48e80 | WriteByte | Write 1-byte value |
| +0x5c | 01b48e00 | Unknown | - |
| +0x60 | 01b48d60 | Unknown | - |
| +0x64 | 01b49140 | Unknown | - |
| +0x68 | 01b48cf0 | Unknown | - |
| +0x6c | 01b48c80 | Unknown | - |
| +0x70 | 01b48c10 | Unknown | - |
| +0x74 | 01b48c00 | Unknown | - |
| +0x78 | 01b48bf0 | Unknown | - |
| +0x7c | 01b48be0 | Unknown | - |
| +0x80 | 01b48bd0 | Unknown | - |
| +0x84 | 01b48bc0 | Write4ByteValue | 4-byte value via FUN_01b49610 |
| +0x88 | 01b48bb0 | Unknown | - |
| +0x8c | 01b48ba0 | Write2Byte | 2-byte value (version fields) |
| +0x90 | 01b48b90 | Unknown | - |
| +0x94 | 01b48b80 | Unknown | - |
| +0x98 | 01b48b70 | Write1Byte | Direct single byte write |
| +0x9c | 01b48e70 | Write4ByteAlt | 4-byte value (alternate) |

### Key Vtable Functions

**FUN_01b487b0 (vtable+0x24) - AddToPendingQueue:**
```c
int __fastcall FUN_01b487b0(int ctx) {
    // Get Type prefix value from TBlockData
    uVar1 = (**(code **)(**(int **)(ctx + 8) + 0x4c))();

    // Store in pending queue
    *(undefined4 *)(ctx + 0x1014 + *(int *)(ctx + 0x1054) * 4) = uVar1;

    // Increment count and return index
    *(int *)(ctx + 0x1054) = *(int *)(ctx + 0x1054) + 1;
    return *(int *)(ctx + 0x1054) - 1;
}
```

**FUN_01b48700 (vtable+0x30) - FlushPendingAndWrite:**
```c
void __thiscall FUN_01b48700(int ctx, undefined4 param_2, undefined4 param_3) {
    // Flush all pending items
    if (*(int *)(ctx + 0x1054) != 0) {
        puVar1 = (undefined4 *)(ctx + 0x1014);
        do {
            (**(code **)(**(int **)(ctx + 8) + 0x54))(*puVar1);  // Write each
            puVar1 = puVar1 + 1;
        } while (++count < *(uint *)(ctx + 0x1054));
    }

    // Reset queue and write final value
    *(undefined4 *)(ctx + 0x1054) = 0;
    (**(code **)(**(int **)(ctx + 8) + 4))(param_2, param_3);
}
```

**FUN_01b489b0 (vtable+0x18) - PopBlock:**
```c
uint __fastcall FUN_01b489b0(int ctx) {
    // Decrement nesting counter
    *(short *)(ctx + 0x1010) -= 1;

    // Get value from block stack
    iVar3 = *(int *)(ctx + 0x10 + counter * 8);
    if (iVar3 != 0) {
        (**(code **)(**(int **)(ctx + 8) + 0x44))(iVar3);  // Reserve
    }

    // Adjust stack offset based on write mode
    if (*(char *)(ctx + 4) != '\0') {
        *(int *)(ctx + 8 + counter * 8) -= 4;  // Read mode
    } else {
        *(int *)(ctx + 8 + counter * 8) += 4;  // Write mode
    }
    return ctx + 8 + counter * 8;
}
```

---

## Detailed Function Analysis

### FUN_01b0c2e0 - Type Dispatcher

**Purpose:** Routes serialization to the appropriate handler based on type code.

**Key Logic:**
```c
void __thiscall FUN_01b0c2e0(int param_1, uint *param_2, uint *param_3, char param_4) {
    // Type extraction with mode-dependent shift
    int shift = (param_4 == '\0') ? 0x10 : 0x17;  // 16 or 23 bits
    int type_code = (param_3[3] >> shift) & 0x3F;

    switch(type_code) {
        case 0x00: FUN_01b09650(param_2, param_3); break;  // Bool
        case 0x07: FUN_01b12fa0(param_3, param_2); break;  // Complex
        case 0x0E: FUN_01b12a60(param_3, param_2); break;  // BoolAlt
        case 0x11: FUN_01b09880(param_2, param_3); break;  // Numeric
        case 0x12:
        case 0x1E: FUN_01b099a0(classid, param_2, param_3); break;  // Pointer
        case 0x17: /* inline array handling */ break;
        case 0x19: FUN_01b09c10(classid, param_2, param_3); break;  // Enum
        case 0x1A: FUN_01b12cf0(param_3, param_2); break;  // String
        // ... more cases
    }

    // End Property block if mode 0
    if (*(int *)(param_1 + 0x58) == 0 && param_4 == '\0') {
        vtable+0x14("Property");
    }
}
```

### FUN_01b0d140 - PropertyHeaderWriter

**Purpose:** Writes the property header (N-block, T-block, PackedInfo).

**Key Logic:**
```c
undefined4 __thiscall FUN_01b0d140(int param_1, uint *param_2) {
    int mode = *(int *)(param_1 + 0x58);

    // CRITICAL: Skip header for modes 1/2/3 (root properties)
    if (mode == 1 || mode == 2 || mode == 3 || (*(byte *)(param_1 + 0x4e) & 1)) {
        return 1;
    }

    // Check for nested object
    if (vtable+0x1c() != 0) return 0;

    // Begin Property block (reserves 4 bytes for Type prefix)
    vtable+0x0c("Property");

    // Write N-block (PropertyID hash)
    uint hash = param_2[1];
    FUN_01b0e680(&"N", 0, &hash);

    // Write T-block (ClassID + type_id)
    uint classid = param_2[2];
    uint type_id = param_2[3];
    FUN_01b0e980(&classid);  // Writes 8 bytes

    // Write PackedInfo
    byte packed = ((param_2[0] >> 17) & 1) * 4 | 0x0B;
    FUN_01b076f0(&packed);

    return 1;
}
```

### FUN_01b12fa0 - ComplexSerializerCore

**Purpose:** Core serialization for Complex (4-byte) values.

**Key Logic:**
```c
undefined4 __thiscall FUN_01b12fa0(int param_1, byte *param_2, undefined4 param_3) {
    // Validate property
    if (FUN_01b07940(param_2, 0, 0) == 0) return 0;

    // Write property header (or skip if mode != 0)
    if (FUN_01b0d140(param_2) == 0) return 0;

    // Optional: handle mode 2 special case
    if (*(int *)(param_1 + 0x58) == 2 && ...) {
        FUN_01b12b10(param_2, param_3);
    }

    // Write Value block
    vtable+0x08("Value");
    vtable+0x84(param_3);  // Write 4-byte value
    vtable+0x10("Value");

    // Clear flag
    *(byte *)(param_1 + 0x4e) &= 0x7f;

    // End Property block if mode 0
    int mode = *(int *)(param_1 + 0x58);
    if (mode != 1 && mode != 2 && mode != 3 && !(*(byte *)(param_1 + 0x4e) & 1)) {
        vtable+0x14("Property");
    }

    return 1;
}
```

### FUN_01b11fb0 - BooleanSerializerCore

**Purpose:** Core serialization for Boolean (1-byte) values.

**Key Logic:**
```c
undefined4 __thiscall FUN_01b11fb0(int param_1, byte *param_2, undefined4 param_3) {
    // Validate property
    if (FUN_01b07940(param_2, 0, 0) == 0) return 0;

    // Write property header
    if (FUN_01b0d140(param_2) == 0) return 0;

    // Write Value block
    vtable+0x08("Value");
    vtable+0x58(param_3);  // Write 1-byte value (different from Complex!)
    vtable+0x10("Value");

    // End Property block if mode 0
    // ... same as ComplexSerializerCore

    return 1;
}
```

### FUN_01b07940 - PropertyValidator

**Purpose:** Validates property before serialization, sets up context.

**Key Logic:**
```c
undefined1 __thiscall FUN_01b07940(int param_1, byte *param_2) {
    int mode = *(int *)(param_1 + 0x58);

    // Set validator flags
    *(undefined1 *)(param_1 + 0x79) = 1;
    *(undefined1 *)(param_1 + 0x7a) = 0;

    // Store descriptor pointer
    *(byte **)(param_1 + 0x2c) = param_2;

    // Check if serialization should proceed
    if (mode != 3 && ((*param_2 & 1) == 0) && mode != 2) {
        return 0;  // Skip this property
    }

    // Additional validation...
    return 1;
}
```

### FUN_01b496d0 - TBlockDataWriter

**Purpose:** Writes T-block content (ClassID + type_id) and updates size accumulator.

**Key Logic:**
```c
void __thiscall FUN_01b496d0(int param_1, undefined4 *param_2) {
    // Update parent block's size accumulator
    if (*(short *)(param_1 + 0x1010) != 0) {
        int *size_ptr = (int *)(param_1 + 8 + counter * 8);
        if (write_mode) {
            *size_ptr += 8;  // Add T-block size
        } else {
            *size_ptr -= 8;
        }
    }

    // Write ClassID and type_id
    if (write_mode) {
        vtable+0x30(*param_2, param_2[1]);  // Write 8 bytes
    } else {
        vtable+0x18();  // Read mode
    }
}
```

---

## Implementation Notes

### JSON Serializer Simplification

The game's serializer uses a complex pending queue mechanism for streaming/nested serialization. **Our JSON serializer does NOT need this complexity** because:

| Game's Approach | Our Approach |
|-----------------|--------------|
| Stream-based, nested blocks | Flat structure, all data known upfront |
| Queue Type prefixes, flush later | Write Type prefix directly |
| Complex state machine with modes | Simple loop through properties |
| Block nesting with deferred writes | Sequential property output |

**For 1:1 round-trip, we need:**
1. Root property → no Type prefix (17 bytes)
2. Child properties → 4-byte Type prefix + data (21+ bytes)
3. Compute Type prefix from descriptor type (extracted from type_id)

**Type Prefix Computation (from RE):**
```
type_id → descriptor_type → type_prefix
         (>> 16) & 0x3F    compute_type_prefix()

0x00070000 → 0x07 (Complex) → 0x11 (Numeric)
0x00000000 → 0x00 (Bool)    → 0x0E (BoolAlt)
0x001A0000 → 0x1A (String)  → 0x19 (Enum)
0x00120000 → 0x12 (Pointer) → 0x11 (Numeric)
```

The pending queue (ctx+0x1014), flush mechanism (FUN_01b48700), and queue function (FUN_01b487b0) are implementation details for the game's streaming serializer that we can safely ignore.

---

## Working Parser Reference

### section1_parser.py

A fully working parser that achieves **1:1 byte-for-byte match** with the original binary.

**Key Constants:**

```python
# Type codes from FUN_01b0c2e0 type dispatcher
TYPE_BOOL = 0x00
TYPE_COMPLEX = 0x07
TYPE_BOOLEAN_ALT = 0x0E
TYPE_NUMERIC = 0x11
TYPE_POINTER = 0x12
TYPE_ARRAY = 0x17
TYPE_ENUM = 0x19
TYPE_STRING = 0x1A
TYPE_POINTER_ALT = 0x1E

# Type prefix mapping (descriptor type → binary type prefix)
TYPE_PREFIX_MAP = {
    0x07: 0x11,  # Complex → Numeric format
    0x00: 0x0E,  # Bool → BoolAlt format
    0x1A: 0x19,  # String → Enum format
    0x12: 0x11,  # Pointer → Numeric format
}

# Constants
ZERO_PREFIX_SIZE = 10
CONTAINER_HASH = 0xBDBE3B52  # "SaveGame"
END_MARKER = 0x00000000
```

**Key Functions:**

```python
def extract_descriptor_type(type_id: int) -> int:
    """
    Extract descriptor type from type_id field.
    From FUN_01b0c2e0: (type_id >> 16) & 0x3F
    """
    return (type_id >> 16) & 0x3F

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
        0x00: 0x0E,  # Bool → BoolAlt format
        0x07: 0x11,  # Complex → Numeric format
        0x12: 0x11,  # Pointer → Numeric format
        0x1A: 0x19,  # String → Enum format
    }
    return TYPE_PREFIX_MAP.get(descriptor_type, 0x11)  # Default to Numeric
```

---

## Knowledge Gaps and Further Research

### RE-Verified Items

| Element | Source Function | Verification |
|---------|-----------------|--------------|
| Type extraction formula | FUN_01b0c2e0 | `(type_id >> 16) & 0x3F` ✓ |
| Type prefix computation | FUN_01b11fb0/12fa0/099a0/12cf0 | Descriptor type → Type prefix mapping ✓ |
| PackedInfo computation | FUN_01b0d140 @ 01b0d269 | DAT Flags=0x02000001, bit 17=0 → 0x0B ✓ |
| String length computation | FUN_01b12cf0 → FUN_01b49920 | strlen loop, no max limit ✓ |
| Root no Type prefix | FUN_01b0d140 | Mode 1/2/3 skips header ✓ |
| Child Type prefix | FUN_01b0d140 | Mode 0 writes full header ✓ |
| Container hash write | FUN_01b08ce0 | vtable+0x50 writes hash ✓ |
| Version fields | FUN_01b0d420 | vtable+0x8c writes 2-byte values ✓ |
| Property serialization | FUN_005e3560 | Full call sequence documented ✓ |
| Block mechanism | FUN_01b48890/920 | BeginBlock reserves, EndBlock writes ✓ |
| Pending queue | FUN_01b487b0/700 | Queue at ctx+0x1014, flush mechanism ✓ |
| ObjectCloser | FUN_01b0d0c0 | Ends Properties/Object blocks ✓ |
| HasMore check | LAB_01b48a10 | Size-based block tracking for read termination ✓ |
| Property reader | FUN_01b0d000 | Deserializer loop using HasMore ✓ |
| Version writer | FUN_01b0d420 | Writes 2-byte versions via vtable+0x8c ✓ |

### Empirically Verified (Preserve for Round-Trip)

| Element | Size | Value/Notes | Status |
|---------|------|-------------|--------|
| Zero prefix | 10 bytes | All zeros, from compression layer | Preserve |
| Container hash | 4 bytes | 0xBDBE3B52 ("SaveGame") | RE verified |
| Container header | 12 bytes | field1=265, field2=257 (Properties size), field3=17 | RE verified |
| End marker | 4 bytes | 0x00000000 | RE verified (see below) |

### Container Header Fields (RE Verified via WinDbg)

All three fields are block sizes from nested BeginBlock calls:

| Field | Offset | Value | Meaning | Verification |
|-------|--------|-------|---------|--------------|
| field1 | 0x0E | 265 | Object block size | 283 - 18 = 265 ✓ (0x12 to EOF) |
| field2 | 0x12 | 257 | Properties block size | 283 - 26 = 257 ✓ (0x16 to 0x117) |
| field3 | 0x16 | 17 | Root property block size | Root = Hash(4)+ClassID(4)+type_id(4)+Packed(1)+Value(4) = 17 ✓ |

**Block Nesting (from FUN_01b08ce0 + FUN_01b0d140):**
1. BeginBlock("Object") → writes field1 at 0x0E
2. BeginBlock("Properties") → writes field2 at 0x12
3. BeginBlock("Property") for root → writes field3 at 0x16
4. Root property content (17 bytes)
5. Child properties (each has Type prefix, NO block size)
6. EndBlock sequence backpatches sizes

### End Marker Mechanism (RE Verified)

The "end marker" is **not an explicit terminator** but rather the result of size-based block tracking.

**LAB_01b48a10 (vtable+0x1c) - HasMore Check:**
```asm
CMP byte ptr [ECX + 0x4], 0x0      ; Check write mode
JZ  LAB_01b48a26                    ; Jump if write mode

; Read mode - check remaining size:
MOVZX EAX, word ptr [ECX + 0x1010] ; EAX = stack_counter
CMP dword ptr [ECX + EAX*0x8 + 0x8], 0x0  ; block_stack[counter].size <= 0?
SETBE AL                            ; Return 1 if no more, 0 if has more
RET
```

**How it works:**
1. BeginBlock reads a **size value** from the binary
2. As properties are read, remaining size **decrements**
3. When size reaches 0, `HasMore` returns 1 (done)
4. The 0x00000000 at end is block metadata, not a sentinel

**For our parser:**
- We check if Type prefix == 0x00000000 to terminate
- This works because no valid Type prefix is 0 (valid: 0x0E, 0x11, 0x19)
- The game uses size tracking; we use Type prefix check - both achieve same result

### Remaining To Verify (Low Priority)

| Area | Question | Priority |
|------|----------|----------|
| Property hash meanings | What do hashes like 0x70A1EA5F represent? | Low |
| ManagedObject wrapper | Why FUN_01b17f90 opens and immediately closes | Low |

### Confirmed Knowledge

| Area | Finding | Source |
|------|---------|--------|
| Root hash | 0xBDBE3B52 = "SaveGame" | FUN_005e3560 |
| ManagedObject hash | 0xBB96607D | FUN_01b17f90 |
| Property header size | 13 bytes (N:4 + T:8 + PackedInfo:1) | FUN_01b0d140 |
| Type extraction | `(type_id >> 16) & 0x3F` | FUN_01b0c2e0 |
| Mode shift | Standard=16 bits, Array=23 bits | FUN_01b0c2e0 |
| PackedInfo formula | `((Flags >> 17) & 1) * 4 \| 0x0B` → 0x0B | FUN_01b0d140 @ 01b0d269, DAT_027ecd98 |
| String length | strlen(value) computed, no max limit | FUN_01b12cf0 → FUN_01b49920 |
| Block nesting | Stack at ctx+0x08 with 8-byte entries | FUN_01b48890, FUN_01b48920 |
| Context mode offset | ctx+0x58 contains serialization mode | FUN_01b0d140 |

---

## Appendix: Known Property Hashes

### Section 1 Properties (Complete)

| Hash | Descriptor Type | Binary Type | ClassID | Serializer | Sample Value |
|------|-----------------|-------------|---------|------------|--------------|
| 0x70A1EA5F | 0x07 (Complex) | N/A (root) | 0 | FUN_01b0a1f0 | 22 |
| 0x2578300E | 0x07 (Complex) | 0x11 | 0 | FUN_01b0a1f0 | 16702380 |
| 0xF5C71F6B | 0x07 (Complex) | 0x11 | 0 | FUN_01b0a1f0 | 6 |
| 0xBB6621D2 | 0x07 (Complex) | 0x11 | 0 | FUN_01b0a1f0 | 351759 |
| 0x28550876 | 0x07 (Complex) | 0x11 | 0 | FUN_01b0a1f0 | 3 |
| 0x34032BE4 | 0x00 (Bool) | 0x0E | 0 | FUN_01b09650 | 1 |
| 0x78BD5067 | 0x1A (String) | 0x19 | 0 | FUN_01b09980 | "Options" |
| 0x7111FCC2 | 0x12 (Pointer) | 0x11 | 0xFBB63E47 | FUN_01b099a0 | 0 |
| 0x6C448E95 | 0x12 (Pointer) | 0x11 | 0x5FDACBA0 | FUN_01b099a0 | 0 |
| 0xEB76C432 | 0x07 (Complex) | 0x11 | 0 | FUN_01b0a1f0 | 0 |
| 0x28F5132B | 0x07 (Complex) | 0x11 | 0 | FUN_01b0a1f0 | 0 |
| 0x8C00191B | 0x07 (Complex) | 0x11 | 0 | FUN_01b0a1f0 | 0 |

### Class Identifiers

| ClassID | Context | Notes |
|---------|---------|-------|
| 0xBDBE3B52 | SaveGame | Section 1 root |
| 0xBB96607D | ManagedObject | Wrapper class |
| 0xFBB63E47 | Unknown | Pointer target class #1 |
| 0x5FDACBA0 | Unknown | Pointer target class #2 |

---

**End of Document**
