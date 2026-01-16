# Section 2 Serialization Reference

**Status**: Standalone Reference Document for Section 2 ("PlayerOptionsSaveData")
**Last Updated**: 2026-01-07
**Section Hash**: 0x305AE1A8

This document is a focused reference for Section 2 serialization in Assassin's Creed Brotherhood's OPTIONS save files, derived from Ghidra decompilation and WinDbg time-travel debugging.

---

## Table of Contents

1. [Section 2 Overview](#section-2-overview)
2. [Runtime Parameters (Confirmed via Debugging)](#runtime-parameters-confirmed-via-debugging)
3. [Serializer Context Structure](#serializer-context-structure)
4. [Section 2 Serializer Functions](#section-2-serializer-functions)
5. [ObjectCloser (FUN_01b0d0c0)](#objectcloser-fun_01b0d0c0---link-to-typedispatcher)
6. [ContainerSerializer (FUN_01b0a460)](#containerserializer-fun_01b0a460---nested-object-creation)
7. [Complete Serialization Call Flow](#complete-serialization-call-flow)
8. [TypeDispatcher (FUN_01b0c2e0)](#typedispatcher-fun_01b0c2e0---complete-type-mapping)
9. [Property Descriptor Structure](#property-descriptor-structure)
10. [Vtable Reference](#vtable-reference)
11. [Object Header Structure (FUN_01b08ce0)](#object-header-structure)
12. [Block System](#block-system)
13. [Mode-Based Serialization](#mode-based-serialization)
14. [Record Structures](#record-structures)
15. [Section 2 Complete Call Flow](#section-2-complete-call-flow)
16. [Binary Layout Analysis](#binary-layout-analysis)
17. [Known Property Hashes](#known-property-hashes)
18. [Key Formulas](#key-formulas)

---

## Section 2 Overview

Section 2 contains player settings/options data serialized under root name "AssassinGlobalProfileData" with hash **0x305AE1A8**.

### Section Identification

| Field | Value | Description |
|-------|-------|-------------|
| Root Hash | 0x305AE1A8 | "AssassinGlobalProfileData" |
| Nested Hash | 0xB7806F86 | "SaveGameDataObject" |
| Header Field2 | 0x00000003 | Section 2 identifier |
| Header Field3 | 0x11FACE11 | Section 2 magic marker |

---

## Runtime Parameters (Confirmed via Debugging)

**Confirmed via WinDbg breakpoint on FUN_01b08ce0:**

| Parameter | Offset | Value | Description |
|-----------|--------|-------|-------------|
| Serializer Version | context+0x24 | **0x10 (16)** | Determines header format |
| Mode | context+0x58 | **0x00 (0)** | Standard serialization mode |
| Write-Enabled | context+0x20 | **0x02 (2)** | Special write mode |

### Version 16 Implications

- Version >= 8: SerializerVersion field is NOT written
- Version >= 13: Uses NbClassVersionsInfo format (not ClassVersion)
- Version >= 14: Uses InstancingMode format (not InstanceOf)

### Mode 0 Implications

- Full ObjectInfo header is written
- PropertyIterator stores object but doesn't iterate (mode != 3)
- ObjectCloser writes Dynamic Properties block
- Standard property records use 13-byte header + value

---

## Serializer Context Structure

The serializer context object (passed as `this`/param_1 to most functions):

```
Offset  Size  Field              Description
------  ----  -----              -----------
+0x04   4     Writer             Pointer to writer object (has vtable)
+0x08   76    State              Saved state array (19 x 4 bytes)
+0x0C   4     CurrentHash        Current object hash
+0x10   4     CurrentObjectID    Current object ID
+0x18   4     ???                Unknown
+0x1C   4     ObjectPtr          Current object pointer
+0x20   4     WriteEnabled       0=disabled, 1=normal, 2=special
+0x24   4     Version            Serializer version (16 for Section 2)
+0x28   4     StoredObject       Object for PropertyIterator
+0x2C   4     Descriptor         Current property descriptor
+0x30   4     ParentObject       Parent object pointer
+0x40   4     ???                Unknown
+0x4C   2     ClassVersion       Class version info
+0x4E   1     Flags              Bit flags for serialization state
+0x4F   1     Flags2             Additional flags
+0x58   4     Mode               0=standard, 1/2/3=mode-based
+0x6C   4     ModeStack          Mode stack pointer
+0x79   1     ArrayFlag          Array serialization flag
+0x7A   1     ValidationFlag     Property validation flag
```

---

## Section 2 Serializer Functions

### Core Pipeline

| Address | Name | Purpose |
|---------|------|---------|
| 0x01712930 | ProfileSerializer | Main Section 2 entry, registers root 0x305AE1A8 |
| 0x005e3700 | SaveGameDataObject | Nested object serializer (hash 0xB7806F86) |
| 0x01b09e20 | RootRegistration | Registers object, calls FUN_01b08ce0 |
| 0x01b08ce0 | ObjectHeaderWriter | Writes ObjectInfo header based on version/mode |
| 0x01b0d0c0 | ObjectCloser | Closes object, handles Dynamic Properties |

### Property Serializers (FROM DECOMPILE FUN_01b0c2e0)

| Address | Name | Type Code | Header | Value | Total |
|---------|------|-----------|--------|-------|-------|
| 0x01b09650 | BooleanSerializer | 0x00 | 13 bytes | 1 byte | 14 bytes |
| 0x01b12120 | ByteSerializer | 0x03 | 13 bytes | 1 byte | 14 bytes |
| 0x01b12420 | FloatSerializer | 0x06 | 13 bytes | 4 bytes | 17 bytes |
| 0x01b12fa0 | ComplexSerializer | 0x07 | 13 bytes | 4 bytes | 17 bytes |
| 0x01b12640 | FloatAltSerializer | 0x0A | 13 bytes | 4 bytes | 17 bytes |
| 0x01b09880 | NumericSerializer | 0x11 | 13 bytes | 4 bytes | 17 bytes |
| 0x01b099a0 | ClassIDSerializer | 0x12/0x1E | 13 bytes | 4 bytes | 17 bytes |
| 0x01b0a460 | ContainerSerializer | 0x13 | 13 bytes | Variable | Variable |
| 0x01b0b8a0 | EnumSmallSerializer | 0x15 | 13 bytes | 4 bytes | 17 bytes |
| 0x01b0b710 | NestedObjectSerializer | 0x16 | 13 bytes | Variable | Variable |
| 0x01b07be0 | VectorSerializer | 0x17 | 13 bytes | Variable | Variable |
| 0x01b0bcf0 | ArraySerializer | 0x18/0x1D | 13 bytes | Variable | Variable |
| 0x01b09c10 | EnumVariantSerializer | 0x19 | 13 bytes | 8 bytes | 21 bytes |

### Header Writers

| Address | Name | Purpose | Bytes |
|---------|------|---------|-------|
| 0x01b0d140 | PropertyHeaderWriter | Writes N/T/PackedInfo | 13 |
| 0x01b0e680 | NBlockWriter | PropertyID hash | 4 |
| 0x01b0e980 | TBlockWriter | ClassID + TypeID | 8 |
| 0x01b076f0 | PackedInfoWriter | PackedInfo byte | 1 |
| 0x01b0d420 | VersionFieldWriter | 2-byte version field | 2 |
| 0x01b0d490 | InstanceOfWriter | 4-byte InstanceOf | 4 |
| 0x01b0d500 | ByteFieldWriter | 1-byte named field | 1 |
| 0x01b0e640 | DwordFieldWriter | 4-byte named field | 4 |

### Mode Writers

| Address | Name | Mode | Header Size |
|---------|------|------|-------------|
| 0x01b70450 | Mode1Writer | 1 | 9 bytes |
| 0x01b704f0 | Mode2Writer | 2 | 13 bytes |
| 0x01b709a0 | Mode3Writer | 3 | 13+ bytes |
| 0x01b12b10 | ModePropertyWriter | 1/2/3 | Variable + 4 |

### Iterator/Dispatcher

| Address | Name | Purpose |
|---------|------|---------|
| 0x01b09620 | PropertyIterator | Dispatches to FUN_01b091a0 if mode==3, else stores object |
| 0x01b091a0 | PropertyIteratorCore | Iterates property list, calls TypeDispatcher |
| 0x01b0c2e0 | TypeDispatcher | Routes to serializer by type code |

---

## ObjectCloser (FUN_01b0d0c0) - Link to TypeDispatcher

The ObjectCloser is the bridge between direct serializer calls and the TypeDispatcher. When an object is closed, it triggers PropertyIteratorCore to iterate any stored properties.

### FUN_01b0d0c0 Decompile (Mode 0 path):

```c
else if (*(int *)(param_1 + 0x20) != 0) {  // WriteEnabled != 0
    FUN_01b0d000();
    (**(code **)(**(int **)(param_1 + 4) + 0x14))("Properties");      // EndBlockSized
    (**(code **)(**(int **)(param_1 + 4) + 0xc))("Dynamic Properties"); // BeginBlockSized
    if (*(int *)(param_1 + 0x28) != 0) {  // StoredObject != 0
        FUN_01b091a0(*(int *)(param_1 + 0x28));  // PropertyIteratorCore!
    }
    (**(code **)(**(int **)(param_1 + 4) + 0x14))("Dynamic Properties"); // EndBlockSized
    (**(code **)(**(int **)(param_1 + 4) + 0x14))("Object");           // EndBlockSized
}
```

**Key insight**: ObjectCloser checks `context+0x28` (StoredObject). If set, it calls PropertyIteratorCore (FUN_01b091a0) which iterates properties and calls TypeDispatcher (FUN_01b0c2e0) for each one.

---

## ContainerSerializer (FUN_01b0a460) - Nested Object Creation

ContainerSerializer creates a nested object with its own ObjectInfo header, then delegates property serialization to the object's vtable.

### FUN_01b0a460 Key Operations:

```c
// Write property header (13 bytes)
FUN_01b0d140(puVar1);

// Create nested ObjectInfo
FUN_01b08ce0(0,&param_3,&local_20,&local_18,&local_1c,&local_2c,&local_24);

// Call object's vtable to serialize its properties
(**(code **)(*piVar6 + 4))(param_1);
```

This explains why Container/NestedObject types have variable size - they contain full nested object structures with their own property lists.

---

## Complete Serialization Call Flow

```
FUN_01712930 (ProfileSerializer)
│
├── Direct serializers for known root properties:
│   ├── FUN_01b0a460 (Container) → FUN_01b08ce0 (nested ObjectInfo) → vtable call
│   ├── FUN_01b0b710 (NestedObject) → similar nested structure
│   ├── FUN_01b09650 (Boolean) → direct 1-byte write
│   └── FUN_01b0bcf0 (Array) → ContentCode + Count + Elements
│
└── FUN_01b0d0c0 (ObjectCloser)
        │
        └── If StoredObject (context+0x28) exists:
                FUN_01b091a0 (PropertyIteratorCore)
                    │
                    └── For each property in list:
                            FUN_01b0c2e0 (TypeDispatcher)
                                │
                                └── Switch on type code → appropriate serializer
```

---

## TypeDispatcher (FUN_01b0c2e0) - Complete Type Mapping

The TypeDispatcher routes property serialization based on the type code extracted from the type_id field.

### Type Code Extraction

```c
// Normal property context (param_4 == 0):
type_code = (type_id >> 16) & 0x3F;   // bits 16-21

// Array/Vector element context (param_4 == 1):
element_type = (type_id >> 23) & 0x3F;  // bits 23-28
```

### Complete Switch Table (FROM DECOMPILE)

| Type Code | Handler Address | Handler Name | Value Size |
|-----------|-----------------|--------------|------------|
| 0x00 | 0x01b09650 | BooleanSerializer | 1 byte |
| 0x01 | 0x01b12060 | Unknown | ? |
| 0x02 | 0x01b121e0 | Unknown | ? |
| 0x03 | 0x01b12120 | ByteSerializer | 1 byte |
| 0x04 | 0x01b12360 | Unknown | ? |
| 0x05 | 0x01b122a0 | Unknown | ? |
| 0x06 | 0x01b12420 | FloatSerializer | 4 bytes |
| 0x07 | 0x01b12fa0 | ComplexSerializer | 4 bytes |
| 0x08 | 0x01b12590 | Unknown | ? |
| 0x09 | 0x01b124e0 | Unknown | ? |
| 0x0A | 0x01b12640 | FloatAltSerializer | 4 bytes |
| 0x0B | 0x01b126f0 | Unknown | ? |
| 0x0C | 0x01b127a0 | Unknown | ? |
| 0x0D | 0x01b12850 | Unknown | ? |
| 0x0E | 0x01b12a60 | Unknown | ? |
| 0x0F | 0x01b12900 | Unknown | ? |
| 0x10 | 0x01b129b0 | Unknown | ? |
| 0x11 | 0x01b09880 | NumericSerializer | 4 bytes |
| 0x12 | 0x01b099a0 | ClassIDSerializer | 4 bytes |
| 0x13 | 0x01b0a460 | ContainerSerializer | Variable |
| 0x14 | 0x01b0b2c0 | Unknown | ? |
| 0x15 | 0x01b0b8a0 | EnumSmallSerializer | 4 bytes |
| 0x16 | 0x01b0b710 | NestedObjectSerializer | Variable |
| 0x17 | (inline) | VectorSerializer | Variable |
| 0x18 | 0x01b0bcf0 | ArraySerializer | Variable |
| 0x19 | 0x01b09c10 | EnumVariantSerializer | 8 bytes |
| 0x1A | 0x01b12cf0 | Unknown | ? |
| 0x1B | 0x01b13180 | Unknown | ? |
| 0x1C | 0x01b0ae60 | Unknown | ? |
| 0x1D | 0x01b0bcf0 | ArraySerializer | Variable |
| 0x1E | 0x01b099a0 | ClassIDSerializer | 4 bytes |

### Confirmed Primitive Element Sizes (for Array/Vector)

| Element Type | Handler | Size | Notes |
|--------------|---------|------|-------|
| 0x00 | BooleanSerializer | 1 byte | vtable+0x98 |
| 0x03 | ByteSerializer | 1 byte | vtable+0x98 |
| 0x06 | FloatSerializer | 4 bytes | vtable+0x80 |
| 0x07 | ComplexSerializer | 4 bytes | vtable+0x84 |
| 0x0A | FloatAltSerializer | 4 bytes | vtable+0x84 |
| 0x11 | NumericSerializer | 4 bytes | vtable+0x84 |
| 0x12 | ClassIDSerializer | 4 bytes | vtable+0x84 |
| 0x15 | EnumSmallSerializer | 4 bytes | vtable+0x84 |
| 0x19 | EnumVariantSerializer | 8 bytes | EnumValue(4) + EnumName(4) |
| 0x1E | ClassIDSerializer | 4 bytes | vtable+0x84 |

### Unknown Type Handlers (Not Used in Section 2)

The following type codes have handlers in the TypeDispatcher but are **NOT used in Section 2** (PlayerOptionsSaveData). They are likely used in other sections (e.g., Section 1 game state data).

| Type Code | Handler Address | Notes |
|-----------|-----------------|-------|
| 0x01 | 0x01b12060 | Unknown primitive |
| 0x02 | 0x01b121e0 | Unknown primitive |
| 0x04 | 0x01b12360 | Unknown primitive |
| 0x05 | 0x01b122a0 | Unknown primitive |
| 0x08 | 0x01b12590 | Unknown primitive |
| 0x09 | 0x01b124e0 | Unknown primitive |
| 0x0B | 0x01b126f0 | Unknown primitive |
| 0x0C | 0x01b127a0 | Unknown primitive |
| 0x0D | 0x01b12850 | Unknown primitive |
| 0x0E | 0x01b12a60 | Unknown primitive |
| 0x0F | 0x01b12900 | Unknown primitive |
| 0x10 | 0x01b129b0 | Unknown primitive |
| 0x14 | 0x01b0b2c0 | Unknown complex |
| 0x1A | 0x01b12cf0 | Unknown |
| 0x1B | 0x01b13180 | Unknown |
| 0x1C | 0x01b0ae60 | Unknown |

**Section 2 Type Distribution (Verified):**
```
0x00 (Boolean):     41 properties
0x03 (Byte):         2 properties
0x06 (Float):        1 property
0x07 (Complex):      5 properties
0x0A (FloatAlt):     5 properties
0x13 (Container):    1 property
0x16 (NestedObject): 2 properties
0x17 (Vector):       1 property
0x19 (EnumVariant):  3 properties
0x1D (Array):        2 properties
─────────────────────────────────
Total:              63 properties
```

---

## Property Descriptor Structure

32-byte descriptor located at static addresses (e.g., DAT_02973808):

```
Offset  Size  Field         Description
------  ----  -----         -----------
0x00    4     Header        Flags, bit 17 = PackedInfo variant
0x04    4     PropertyID    Property hash
0x08    4     ClassID       Class identifier (0 for simple types)
0x0C    4     TypeField     Bits 16-21 = type code via (value >> 16) & 0x3F
0x10    4     Extra1        Additional flags/data
0x14    12    Padding       Reserved
```

### Confirmed Descriptors (Section 2)

| Address | PropertyID | ClassID | Type | Used By |
|---------|------------|---------|------|---------|
| DAT_027ecf90 | 0xBF4C2013 | 0x00000000 | 0x07 | SaveGameDataObject ComplexSerializer |
| DAT_02973808 | 0x7879288E | 0x7879288E | 0x13 | ContainerSerializer |
| DAT_02973828 | 0x0286EAC2 | 0x5713CE96 | 0x16 | NestedObjectSerializer |
| DAT_02973848 | 0x8AC7DD90 | 0x1F9AF76D | 0x16 | NestedObjectSerializer |
| DAT_02973868 | 0x52894752 | 0x00000000 | 0x00 | BooleanSerializer |
| DAT_02973888 | 0x886B92CC | 0x00000000 | 0x00 | BooleanSerializer |
| DAT_029738A8 | 0x49F3B683 | 0x00000000 | 0x00 | BooleanSerializer |
| DAT_029738C8 | 0x707E8A46 | 0x00000000 | 0x00 | BooleanSerializer |
| DAT_029738E8 | 0x6705059E | 0x00000000 | 0x00 | BooleanSerializer |
| DAT_02973908 | 0x0364F3CC | 0x00000000 | 0x00 | BooleanSerializer |
| DAT_02973928 | 0xD9E10623 | 0x00000000 | 0x1D | ArraySerializer |

---

## Vtable Reference

### Serializer Writer Vtable (0x02555c60)

| Offset | Address | Name | Bytes Written |
|--------|---------|------|---------------|
| +0x08 | 01b48770 | BeginBlock | 0 |
| +0x0c | 01b48890 | BeginBlockSized | 4 (size placeholder) |
| +0x10 | 01b487a0 | EndBlock | 0 |
| +0x14 | 01b48920 | EndBlockSized | 0 (fills placeholder) |
| +0x34 | 01b48760 | Write4Byte | 4 |
| +0x40 | 01b48a30 | WriteRawData | Variable |
| +0x48 | 01b492f0 | StringWriter | 4 + len + 1 (with null) |
| +0x4c | 01b49020 | TBlockData | 8 |
| +0x50 | 01b48fb0 | NBlockData | 4 |
| +0x54 | 01b48e90 | StringWriterAlt | 4 + len (no null) |
| +0x58 | 01b48e80 | FlagWriter | 1 |
| +0x84 | 01b48bc0 | Write4ByteAlt | 4 |
| +0x8c | 01b48b90 | Write2Byte | 2 |
| +0x98 | 01b48b70 | Write1Byte | 1 |
| +0x9c | 01b48e70 | Write4ByteAlt2 | 4 |

### Key Distinction

- **vtable+0x08/0x10**: Simple begin/end blocks (0 bytes)
- **vtable+0x0c/0x14**: Sized blocks with 4-byte size placeholder

---

## Object Header Structure

### FUN_01b08ce0 - ObjectHeaderWriter

Writes object header based on mode and version:

**Mode 1 or 2:** No header written, just internal registration via FUN_01b70d10.

**Mode 0 or 3:** Full ObjectInfo header:

```c
// Version 16, Mode 0, WriteEnabled 2:
BeginBlock("ObjectInfo");                    // 0 bytes

// SerializerVersion - SKIPPED (version >= 8 OR writeEnabled == 2)

// ClassVersion/NbClassVersionsInfo (version >= 13 uses NbClassVersionsInfo)
if (mode != 3) {
    FUN_01b0d500("NbClassVersionsInfo", &count);  // 1 byte
    for (i = 0; i < count; i++) {
        vtable+0x84: VersionClassID;              // 4 bytes
        vtable+0x8c: Version;                     // 2 bytes
    }

    // ObjectName
    vtable+0x54: ObjectName string;               // 4 + len bytes
}

// ObjectID
vtable+0x9c: ObjectID;                            // 4 bytes

// InstancingMode (version >= 14)
if (mode != 3) {
    FUN_01b0d500("InstancingMode", &mode_byte);   // 1 byte
    if (mode_byte == 1) {
        FUN_01b0e640("FatherID", &father_id);     // 4 bytes
    }
}

// T-hash
vtable+0x50: T-hash;                              // 4 bytes

EndBlock("ObjectInfo");                           // 0 bytes

// Open Object and Properties blocks
if (mode != 3) {
    BeginBlockSized("Object");                    // 4 bytes (vtable+0x0c)
    BeginBlockSized("Properties");                // 4 bytes (vtable+0x0c)
}
```

---

## Block System

### Sized Blocks (vtable+0x0c / vtable+0x14)

Used for "Object", "Properties", and "Dynamic Properties" blocks:

**FUN_01b48890 (BeginBlockSized):**
- Saves current buffer position
- Writes 4-byte placeholder (will contain block size)
- Increments nesting level

**FUN_01b48920 (EndBlockSized):**
- Calculates actual block size
- Writes size back to placeholder position
- Decrements nesting level

### Simple Blocks (vtable+0x08 / vtable+0x10)

Used for "ObjectInfo", "N", "T", "Value", etc.:
- Write 0 bytes (purely structural)

---

## Mode-Based Serialization

### FUN_01b12b10 - ModePropertyWriter

Called for version-incompatible properties:

```c
// Determine mode via FUN_01b70790
mode = FUN_01b70790(descriptor, ...);

// Write mode byte in T block
vtable+0x98: mode_byte;                          // 1 byte

switch (mode) {
    case 1:
        FUN_01b70450();                          // 9 bytes header
        break;
    case 2:
        FUN_01b704f0();                          // 13 bytes header
        break;
    case 3:
        FUN_01b709a0();                          // 13+ bytes header
        break;
}

// Write PropertyData
vtable+0x84: value;                              // 4 bytes
```

### Mode 1 Header (FUN_01b70450) - 9 bytes

```
Offset  Size  Field
------  ----  -----
0x00    1     PackedInfo (vtable+0x98)
0x01    4     ObjectID (vtable+0x9c)
0x05    4     PropertyID (vtable+0x84)
```

### Mode 2 Header (FUN_01b704f0) - 13 bytes

```
Offset  Size  Field
------  ----  -----
0x00    1     PackedInfo (vtable+0x98)
0x01    4     ObjectID (vtable+0x9c)
0x05    4     ClassID (vtable+0x84)
0x09    4     PropertyID (vtable+0x84)
```

---

## Record Structures

### Standard Property Header - 13 bytes

Written by FUN_01b0d140 (PropertyHeaderWriter):

```
Offset  Size  Field         Writer Function
------  ----  -----         ---------------
0x00    4     PropertyID    FUN_01b0e680 (NBlockWriter)
0x04    4     ClassID       FUN_01b0e980 (TBlockWriter)
0x08    4     TypeID        FUN_01b0e980 (TBlockWriter)
0x0C    1     PackedInfo    FUN_01b076f0 (PackedInfoWriter)
```

### ComplexSerializer Record - 17 bytes

```
Offset  Size  Field         Source
------  ----  -----         ------
0x00    4     PropertyID    descriptor+0x04
0x04    4     ClassID       descriptor+0x08
0x08    4     TypeID        descriptor+0x0C (contains type in bits 16-21)
0x0C    1     PackedInfo    0x0B or 0x0F
0x0D    4     Value         4-byte value
```

**Confirmed at offset 0x1A in game_uncompressed_2.bin:**
```
1A: 13 20 4c bf    PropertyID: 0xBF4C2013 ✓
1E: 00 00 00 00    ClassID: 0x00000000 ✓
22: 00 00 07 00    TypeID (type 0x07): 0x00070000 ✓
26: 0b             PackedInfo: 0x0B ✓
27: 00 00 00 00    Value: 0 ✓
```

### PropertyIteratorCore Record Format (FUN_01b091a0) - FROM DECOMPILE

Records written by PropertyIteratorCore use sized blocks with standard header:

```c
// From FUN_01b091a0 decompilation (Mode 0):
if (cVar2 == '\0') {
    (**(code **)(**(int **)(param_1 + 4) + 0xc))("Property");  // BeginBlockSized
}
// LAB_01b093f7:
local_18 = local_40;                              // PropertyID from descriptor+0x04
(**(code **)(*piVar1 + 8))(&DAT_02554cb8);        // BeginBlock "N"
(**(code **)(*piVar1 + 0x84))(&local_18);         // Write PropertyID (4 bytes)
(**(code **)(*piVar1 + 0x10))(&DAT_02554cb8);     // EndBlock "N"
FUN_01b0e980(&local_48);                          // TBlockWriter: ClassID + TypeID (8 bytes)
FUN_01b076f0(&local_11);                          // PackedInfoWriter (1 byte)
FUN_01b0c2e0(uVar5, puVar10, uVar11);             // TypeDispatcher writes value
```

**Record Structure:**
```
Offset  Size  Field
------  ----  -----
0x00    4     Block Size (from BeginBlockSized, = content size)
0x04    4     PropertyID (vtable+0x84)
0x08    4     ClassID (FUN_01b0e980)
0x0C    4     TypeID (FUN_01b0e980, type code in bits 16-21)
0x10    1     PackedInfo (FUN_01b076f0, typically 0x0B)
0x11    N     Value (TypeDispatcher, size = BlockSize - 13)
```

**Value Sizes by Type Code (FROM DECOMPILE):**
| Type Code | Type Name | Value Size | Handler |
|-----------|-----------|------------|---------|
| 0x00 | Boolean | 1 byte | FUN_01b09650 |
| 0x03 | Byte | 1 byte | FUN_01b12120 |
| 0x06 | Float | 4 bytes | FUN_01b12420 |
| 0x07 | Complex | 4 bytes | FUN_01b12fa0 |
| 0x0A | FloatAlt | 4 bytes | FUN_01b12640 |
| 0x11 | Numeric | 4 bytes | FUN_01b09880 |
| 0x12 | ClassID | 4 bytes | FUN_01b099a0 |
| 0x13 | Container | Variable | FUN_01b0a460 |
| 0x15 | EnumSmall | 4 bytes | FUN_01b0b8a0 |
| 0x16 | NestedObject | Variable | FUN_01b0b710 |
| 0x17 | Vector | Variable | FUN_01b07be0 |
| 0x18/0x1D | Array | Variable | FUN_01b0bcf0 |
| 0x19 | EnumVariant | 8 bytes | FUN_01b09c10 |
| 0x1E | ClassIDAlt | 4 bytes | FUN_01b099a0 |

**Verified at Container's Properties (0x52-0x36D) - 42 records:**
```
Rec  1 @ 0x052: size=14, PropID=0x7BDDD016, type= 0, val=01
Rec  2 @ 0x064: size=21, PropID=0xB3AB00A8, type=25, val=01000000b597cc50
Rec  5 @ 0x0AF: size=17, PropID=0xD51BD06B, type=10, val=00000000
Rec 42 @ 0x358: size=17, PropID=0x9C81BB39, type= 7, val=3f000000
Final offset: 0x36D ✓ (matches Properties end)
```

### ContainerSerializer Record (Type 0x13) - FROM DECOMPILE

FUN_01b0a460 creates a FULL NESTED OBJECT structure. The record itself has a 13-byte header followed by nested object content:

```
Offset  Size  Field
------  ----  -----
0x00    4     PropertyID
0x04    4     ClassID (same as PropertyID for Container)
0x08    4     TypeID (type 0x13 in bits 16-21)
0x0C    1     PackedInfo (0x0B)
--- Nested ObjectInfo starts (FUN_01b08ce0) ---
0x0D    1     NbClassVersionsInfo (0)
0x0E    4     ObjectName length (0)
0x12    4     ObjectID (0)
0x16    1     InstancingMode (0)
0x17    4     T-hash (same as PropertyID/ClassID)
0x1B    4     Object size
0x1F    4     Properties size
0x23    N     Properties content
...     4     DynProps size (usually 0)
...     M     DynProps content
```

**Verified at offset 0x2F in game_uncompressed_2.bin:**
```
0x2F: Header (13 bytes) - PropertyID 0x7879288E
0x3C: ObjectInfo (10 bytes) - zeros
0x46: T-hash 0x7879288E
0x4A: Object size = 803
0x4E: Properties size = 795
0x52: Properties content (795 bytes)
0x36D: DynProps size = 0
Container total = 13 + 10 + 4 + 4 + 803 = 834 bytes (fills entire DynProps)
```

### NestedObjectSerializer Record (Type 0x16) - FROM DECOMPILE

FUN_01b0b710 creates a nested object structure similar to Container.

**IMPORTANT**: When called from root Properties, the parent wraps the record in a sized block (BeginBlockSized/EndBlockSized "Property"), adding a 4-byte size prefix. When called from DynProps, there may be no size prefix.

```
Offset  Size  Field
------  ----  -----
[0x00   4     Block size - IF parent uses sized block]
---     4     PropertyID
+0x04   4     ClassID
+0x08   4     TypeID (type 0x16 in bits 16-21)
+0x0C   1     PackedInfo (0x0B)
--- Nested ObjectInfo starts (FUN_01b0aba0 or FUN_01b0a210) ---
+0x0D   1     NbClassVersionsInfo (0)
+0x0E   4     ObjectName length (0)
+0x12   4     ObjectID (0)
+0x16   1     InstancingMode (0)
+0x17   4     T-hash (same as ClassID)
+0x1B   4     Object size
+0x1F   4     Properties size
+0x23   N     Properties content
...     4     DynProps size (usually 0)
...     M     DynProps content
```

**Verified at offset 0x371 in game_uncompressed_2.bin (in root Properties):**
```
0x371: Block size = 61 (sized block wrapper from parent)
0x375: Header (13 bytes) - PropertyID 0x0286EAC2, ClassID 0x5713CE96
0x382: ObjectInfo (10 bytes) - zeros
0x38C: T-hash 0x5713CE96 (same as ClassID)
0x390: Object size = 30
0x394: Properties size = 22
0x398: Properties content (22 bytes)
0x3AE: DynProps size = 0
Record total: 13 + 10 + 4 + 4 + 30 = 61 ✓ (matches block size)
```

**NestedObject2 at offset 0x3B2:**
```
0x3B2: Block size = 222
0x3B6: Header - PropertyID 0x8AC7DD90, ClassID 0x1F9AF76D
```

### ArraySerializer Record (Type 0x18/0x1D) - FROM DECOMPILE FUN_01b0bcf0

Array records use PropertyIteratorCore format with array-specific value. Elements are serialized recursively via TypeDispatcher.

**Record Structure:**
```
Offset  Size  Field
------  ----  -----
0x00    4     Block Size
0x04    4     PropertyID
0x08    4     ClassID
0x0C    4     TypeID (type 0x1D in bits 16-21, element type in bits 23-28)
0x10    1     PackedInfo (0x0B)
0x11    1     ContentCode
0x12    4     Count (number of elements)
0x16    N     Elements (count * element_size based on element_type)
```

**Element Type Extraction (FROM DECOMPILE FUN_01b0c2e0):**
```c
// Array elements use bits 23-28 for element type (param_4=1 context)
element_type = (type_id >> 23) & 0x3F;
```

**Element Sizes:**
| Element Type | Size | Example |
|--------------|------|---------|
| 0x00 (Boolean) | 1 byte | [0, 1, 1, 0] |
| 0x03 (Byte) | 1 byte | [5, 10, 15] |
| 0x06 (Float) | 4 bytes | [1.0, 2.5, 3.14] |
| 0x07 (Complex) | 4 bytes | [100, 200, 300] |
| 0x15 (EnumSmall) | 4 bytes | [1, 2, 3] |
| 0x19 (EnumVariant) | 8 bytes | [{value, class_id}, ...] |
| 0x16 (NestedObject) | Variable | Recursive parsing |

**Verified Arrays:**
```
Root Array @ 0x500:
  TypeID=0x001D0000, element_type=0x00 (Boolean)
  ContentCode=0x01, Count=4, Elements=[1,1,1,1]

NestedObj1 Array @ 0x398:
  TypeID=0x0B1D0000, element_type=0x16 (NestedObject)
  ContentCode=0x01, Count=0 (empty array)
```

### VectorSerializer Record (Type 0x17) - FROM DECOMPILE FUN_01b07be0 + FUN_01b0c2e0

Vector records are similar to Arrays but without ContentCode. Elements are serialized recursively via TypeDispatcher.

**Record Structure:**
```
Offset  Size  Field
------  ----  -----
0x00    4     Block Size
0x04    4     PropertyID
0x08    4     ClassID
0x0C    4     TypeID (type 0x17 in bits 16-21, element type in bits 23-28)
0x10    1     PackedInfo (0x0B)
0x11    4     Count (number of elements) - written by FUN_01b0d490
0x15    N     Elements (count * element_size based on element_type)
```

**Element Type Extraction (same as Array):**
```c
element_type = (type_id >> 23) & 0x3F;
```

**FUN_01b07be0 Decompile:**
```c
// Write count (4 bytes)
if (*(int *)(param_1 + 0x58) != 3) {
    FUN_01b0d490(&DAT_02554ce8, param_2);  // 4-byte count
}
// Begin Values block
(**(code **)(**(int **)(param_1 + 4) + 8))("Values");
```

**Verified Vector:**
```
NestedObj2 Vector @ properties[4]:
  TypeID=0x00170006, element_type=0x00 (Boolean)
  Count=6, Elements=[0,0,0,0,0,0]
  value_size=10 bytes (4 for count + 6 × 1 byte elements)
```

---

## Section 2 Complete Call Flow

```
FUN_01712930 (ProfileSerializer) - Mode 0, Version 16, WriteEnabled 2
│
├── FUN_01b09e20("AssassinGlobalProfileData", 0x305AE1A8)
│   └── FUN_01b08ce0 (ObjectHeaderWriter)
│       ├── ObjectInfo content (NbClassVersionsInfo, ObjectName, ObjectID, InstancingMode, T-hash)
│       ├── BeginBlockSized("Object")      [4 bytes - size placeholder]
│       └── BeginBlockSized("Properties")  [4 bytes - size placeholder]
│
├── FUN_005e3700 (SaveGameDataObject, hash 0xB7806F86)
│   ├── FUN_01b09e20 - Nested object header
│   │   └── FUN_01b08ce0 (nested ObjectInfo + Object/Properties blocks)
│   ├── FUN_01b0a1f0 (ComplexSerializer, PropertyID 0xBF4C2013) [17 bytes]
│   ├── FUN_01b09620 (PropertyIterator) - stores object, writes nothing
│   └── FUN_01b0d0c0 (ObjectCloser)
│       ├── FUN_01b0d000 (no-op in write mode)
│       ├── EndBlockSized("Properties")
│       ├── BeginBlockSized("Dynamic Properties") [4 bytes]
│       ├── FUN_01b091a0 (if stored object) - iterates properties
│       ├── EndBlockSized("Dynamic Properties")
│       └── EndBlockSized("Object")
│
├── FUN_01b0a460 (ContainerSerializer, type 0x13) [Variable]
├── FUN_01b0b710 × 2 (NestedObjectSerializer, type 0x16) [Variable]
├── FUN_01b09650 × 6 (BooleanSerializer, type 0x00) [14 bytes each]
├── FUN_01b0bcf0 (ArraySerializer, type 0x1D) [Variable]
├── FUN_01b074a0 (PlainOldDataBlock) [4 + data bytes]
├── FUN_01b08030 (Close Values block)
│
└── FUN_01b0d0c0 (Final ObjectCloser)
    ├── EndBlockSized("Properties")
    ├── BeginBlockSized("Dynamic Properties")
    ├── EndBlockSized("Dynamic Properties")
    └── EndBlockSized("Object")
```

---

## Binary Layout Analysis

### Decompressed Section 2 Structure (VERIFIED)

```
Offset  Size    Content
------  ----    -------
0x000   10      ObjectInfo (NbClassVersionsInfo=0, ObjName len=0, ObjID=0, InstMode=0)
0x00A   4       T-hash: 0x305AE1A8
0x00E   4       Object size: 1292
0x012   4       Properties size: 1284
0x016   1284    Properties content (11 records)
0x51A   4       DynProps size: 0
0x51E   END     Total: 1310 bytes
```

### Root Properties Records (0x016-0x519) - VERIFIED

All records use PropertyIteratorCore format (4-byte size + 13-byte header + value):

```
Rec  1 @ 0x016: size=  17, type=07 Complex   , PropID=0xBF4C2013
Rec  2 @ 0x02B: size= 834, type=13 Container , PropID=0x7879288E
Rec  3 @ 0x371: size=  61, type=16 NestedObj , PropID=0x0286EAC2
Rec  4 @ 0x3B2: size= 222, type=16 NestedObj , PropID=0x8AC7DD90
Rec  5 @ 0x494: size=  14, type=00 Boolean   , PropID=0x528947F4
Rec  6 @ 0x4A6: size=  14, type=00 Boolean   , PropID=0x886B92CC
Rec  7 @ 0x4B8: size=  14, type=00 Boolean   , PropID=0x49F3B683
Rec  8 @ 0x4CA: size=  14, type=00 Boolean   , PropID=0x707E8A46
Rec  9 @ 0x4DC: size=  14, type=00 Boolean   , PropID=0x67059E05
Rec 10 @ 0x4EE: size=  14, type=00 Boolean   , PropID=0x0364F3CC
Rec 11 @ 0x500: size=  22, type=1D Array     , PropID=0xD9E10623
```

### Container Content (0x02F-0x370) - 42 nested records

Container creates nested object with its own Properties block (795 bytes) containing 42 PropertyIteratorCore records.

### NestedObject1 Content (0x375-0x3B1) - 1 nested record

NestedObject with Properties (22 bytes) containing 1 Array record.

### NestedObject2 Content (0x3B6-0x493) - 9 nested records

NestedObject with Properties (183 bytes) containing 9 records (Bool, Complex, Vector types).

---

## Known Property Hashes

### Section 2 Hashes

| Hash | Name | Type |
|------|------|------|
| 0x305AE1A8 | AssassinGlobalProfileData | Root |
| 0xB7806F86 | SaveGameDataObject | Nested Object |
| 0xBF4C2013 | SaveGameDataObject Property | Complex (0x07) |
| 0x7879288E | Container Property | Container (0x13) |
| 0x5713CE96 | Nested Object 1 ClassID | Type 0x16 |
| 0x1F9AF76D | Nested Object 2 ClassID | Type 0x16 |
| 0xB3AB00A8 | Subtitles | Enum (0x15) |
| 0x2DAD13E3 | PlayerOptionsSaveData | ClassID |
| 0xD9E10623 | Array Property | Array (0x1D) |

---

## Key Formulas

### PackedInfo Calculation

```c
// Standard properties
PackedInfo = ((descriptor[0] >> 17) & 1) * 4 | 0x0B
// Result: 0x0B (bit 17 = 0) or 0x0F (bit 17 = 1)

// Mode-based properties
PackedInfo = (param << 2) | mode
```

### Type Code Extraction

```c
type = (descriptor[3] >> 16) & 0x3F  // 6-bit type from offset 0x0C
```

### Block Size

Block sizes at offsets 0x0E and 0x12 contain total content size in bytes. The EndBlockSized function calculates and writes this value when the block is closed.

---

## Revision History

| Date | Version | Changes |
|------|---------|---------|
| 2026-01-07 | 1.0 | Initial Section 2 extraction |
| 2026-01-07 | 2.0 | Major update: Runtime debugging confirmed version=16, mode=0, writeEnabled=2. Added complete call flow, vtable block system (sized vs simple), mode header structures, property descriptor table, binary layout analysis with confirmed ComplexSerializer record at 0x1A. |
| 2026-01-07 | 3.0 | Decompilation analysis: ContainerSerializer (FUN_01b0a460) and NestedObjectSerializer (FUN_01b0b710) both create FULL nested object structures with ObjectInfo + Object/Properties blocks. Container at 0x2F verified: 13-byte header + 10-byte ObjectInfo + T-hash + Object(803) + Properties(795) = 834 bytes total. NestedObject at 0x371 has 4-byte size prefix (61), followed by nested object structure. |
| 2026-01-07 | 4.0 | PropertyIteratorCore (FUN_01b091a0) decompilation: ALL property records use sized blocks (4-byte size prefix + 13-byte header + value). Verified complete file structure: Root Properties has 11 records, Container has 42 nested records, NestedObject1 has 1 record, NestedObject2 has 9 records. Value sizes vary by type: Bool=1, Complex=4, Float=4, EnumVariant=8. Total 1310 bytes parses exactly. |
| 2026-01-07 | 5.0 | TypeDispatcher (FUN_01b0c2e0) decompilation: Complete type code switch table (0x00-0x1E) with handler addresses. Array/Vector element type extraction from bits 23-28 of type_id (param_4=1 context). Added VectorSerializer (Type 0x17, FUN_01b07be0) documentation: Count(4) + Elements format. Fixed EnumSmall (0x15) size from 1 to 4 bytes per FUN_01b0b8a0. Added ByteSerializer (0x03, FUN_01b12120) and FloatSerializer (0x06, FUN_01b12420) confirmations. |
| 2026-01-07 | 6.0 | Call flow completion: Added ObjectCloser (FUN_01b0d0c0) decompile showing link to PropertyIteratorCore via context+0x28 (StoredObject). Added ContainerSerializer (FUN_01b0a460) decompile showing nested ObjectInfo creation via FUN_01b08ce0 and vtable-based property serialization. Added complete serialization call flow diagram. Documented unknown type handlers (0x01, 0x02, 0x04, 0x05, 0x08-0x10, 0x14, 0x1A-0x1C) with note that they are not used in Section 2 but likely used in Section 1. Added Section 2 type distribution statistics. |
| 2026-01-14 | 6.1 | Terminology update: Renamed "Padding" field to "TypeID" throughout document to better reflect its purpose (contains type_code in bits 16-21 and element_type in bits 23-28). Updated all code examples, record structures, and comments to use consistent naming with section2_parser.py. |
