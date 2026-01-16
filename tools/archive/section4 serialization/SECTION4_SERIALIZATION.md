# Section 4 Serialization - Trace Documentation

**Started**: January 2026
**Goal**: Trace serialization code from entry point, serialize to JSON and back

---

## HANDOFF SUMMARY (Read This First!)

### Current State
- **Tracing**: Write path of AssassinMultiProfileData serialization
- **TTD Position**: A380F9:A4 (header copy operation)
- **Last Action**: Traced header structure and array element serialization
- **Mode**: 0 (text-like mode with markers - NOT binary mode 1/2/3)

### What We've Learned This Session

1. **Header Structure** (22 bytes) - **FULLY TRACED via FUN_01af6b80 + FUN_01b404c0**:
   ```
   Offset 0x00: [1 byte]   NbClassVersionsInfo = 0x00 (class version count)
   Offset 0x01: [4 bytes]  ObjectName = 0x00000000 (null string hash)
   Offset 0x05: [4 bytes]  ObjectID = 0x00000000
   Offset 0x09: [1 byte]   InstancingMode = 0x00
   Offset 0x0A: [4 bytes]  Type hash = 0xb4b55039 ("AssassinMultiProfileData")
   Offset 0x0E: [4 bytes]  Size field 1 = 0x1836 (content + size fields)
   Offset 0x12: [4 bytes]  Size field 2 = 0x182e (content only)
   ```
   - The 10 "zero" bytes are NOT padding - they are traced ObjectInfo fields
   - Header is built in temporary buffer (0x02bd0000) then copied to output (0x02c40000)
   - Size fields written at END of serialization by FUN_01b404c0 (Property finalization)
   - Size difference: 8 bytes = size of both size fields (4+4)

2. **Array Element Serialization (FUN_01aff250)** - TRACED:
   - Writes "Value" marker (vtable+0x08)
   - Saves context state (19 dwords)
   - Calls FUN_01afd270 (element dispatcher)
   - FUN_01afd270 calls the type-specific serializer (e.g., FUN_00d32140)
   - Restores context state
   - Writes "Value" end marker (vtable+0x10)
   - Mode check: only mode 0 writes "Property" marker (vtable+0x14)

3. **MultiplayerUserData** (type 0xC292F31F) - Complex nested structure:
   | Offset | Type | Element Hash | Notes |
   |--------|------|--------------|-------|
   | +0x4c | Array | 0x94DAAEE6 | 5 elements |
   | +0x54 | Array | 0xF95FCFA8 | - |
   | +0x10 | Array | (4-byte) | PlainOldDataBlock |
   | +0x18 | Array | (4-byte) | PlainOldDataBlock |
   | +0x5c | Byte | - | FUN_01af9930 |
   | +0x5d | Byte | - | FUN_01af9930 |
   | +0x00 | Float | - | FUN_01af9a40 |
   | +0x08 | Float | - | FUN_01af9a40 |
   | +0x20 | Array | (4-byte) | - |
   | +0x28 | Array | - | - |
   | +0x34 | Array | - | - |
   | +0x40 | Array | - | - |

4. **Float Serializer** (FUN_01af9a40 → FUN_01b2cc00):
   - Uses vtable+0x7c for actual float write
   - Same pattern: "Value" marker, write value, end marker, mode check for "Property"

5. **PlainOldDataBlock** (FUN_01ae5710):
   - For raw data arrays
   - Uses vtable+0x40 for bulk write
   - Only writes if flag (context+0x4e & 1) is set

### Key Addresses
| What | Address |
|------|---------|
| Output buffer | 0x02c40000 |
| Source buffer (header) | 0x02bd0000 |
| Context | 0x05ebfa44 |
| Data object | 0xfb630888 |
| Serializer | 0x2b37bf90 |
| VTable (Ghidra) | 0x022C7FA8 |
| Item 0 (MultiplayerUserData) | 0x266494b0 |
| Item 1 (MultiplayerUserData) | 0x26649510 |

### Remaining Gaps
1. ~~**Type 0x039d value length**~~ - **TRACED**: ContentCode byte + count (uint32) + hash array
2. ~~**Type 0x0b1d array serialization**~~ - **TRACED**: Array with typed elements, nested objects have full headers

### Nested Object Delimiters - TRACED
**No explicit delimiter bytes between array elements.** Framing is done through:
1. **"Value" markers** - vtable+0x08 (begin) and vtable+0x10 (end) wrap each element
2. **"Property" marker** - vtable+0x14, written in mode 0 only after each element
3. **Size tracking** - FUN_01b404c0 writes size fields at finalization
4. **Context save/restore** - FUN_01aff250 saves 19 dwords of context state around each element

### Type 0x039d (ContentCode + Hash Array) - FULLY TRACED
- Type descriptor: `00 00 00 00 00 00 9d 03`

**Traced Structure:**
| Component | Bytes | Written By | TTD Position |
|-----------|-------|------------|--------------|
| Type descriptor | 8 | FUN_01b88850 | A38021:17A |
| Marker (0x0b) | 1 | (inline) | - |
| ContentCode | 1 | FUN_01b147e0 via vtable+0x98 | A38021:29B |
| Count | 4 | FUN_01aebab0 via vtable+0x84 | A37E9B:2F6 |
| Elements | count × 4 | FUN_01ae5710 via vtable+0x40 | A37EA3:884 |

**Traced Call Chain:**
```
FUN_01b0b3b0 (Array handler)
  → FUN_01b04800 (element type handler)
    → FUN_01b147e0 (writes ContentCode byte via vtable+0x98)
  → FUN_01aebab0 (writes count via vtable+0x84 → FUN_01b887e0)
  → FUN_01ae5710 (PlainOldDataBlock - bulk memcpy via vtable+0x40)
```

**FUN_01ae5710 (PlainOldDataBlock) Decompiled:**
```c
if ((*(byte *)(param_1 + 0x4e) & 1) != 0) {
    (*vtable+0x08)("PlainOldDataBlock");  // begin marker
    (*vtable+0x40)(data, size, ...);       // bulk memcpy of elements
    (*vtable+0x10)("PlainOldDataBlock");  // end marker
}
```

- Elements are 4-byte hashes copied as raw PlainOldData (not individually serialized)
- Variable length: 5 bytes minimum (ContentCode + zero count), grows by 4 per element
- Length formula: 18 + (count × 4) bytes total

### Type 0x0b1d (Array with Typed Elements) - FULLY TRACED

- Type descriptor: `[inner_hash:4] [00 00 1d 0b]` (type code stored as dword 0x0b1d0000)

**Traced Structure:**
| Component | Bytes | Written By | TTD Position |
|-----------|-------|------------|--------------|
| Type descriptor | 8 | FUN_01688850 via vtable | A37E9B:177-17A |
| Marker (0x0b) | 1 | FUN_01646870 (WriteByte) | A37E9B:237 |
| ContentCode | 1 | FUN_01646870 (WriteByte) | A37E9B:29C |
| Count | 4 | FUN_01688830 (WriteUInt32) | A37E9B:2F6 |
| **Nested elements** | variable | Full object serialization | A37E9D:2B8+ |

**Type Descriptor Write (A37E9B:176-17A):**
```asm
mov ecx, [edi]      ; ecx = inner_hash (0xc292f31f)
mov [eax], ecx      ; write 4 bytes to buffer
mov edx, [edi+4]    ; edx = type_code_dword (0x0b1d0000)
mov [eax+4], edx    ; write 4 bytes to buffer
add [esi+18h], 8    ; advance position by 8
```

**Nested Element Structure:**
Each element is a **full object** with 22-byte header:
```
[1 byte]   NbClassVersionsInfo (usually 0x00)
[4 bytes]  ObjectName hash (usually 0x00000000)
[4 bytes]  ObjectID (usually 0x00000000)
[1 byte]   InstancingMode (usually 0x00)
[4 bytes]  Type hash (e.g., 0xc292f31f for MultiplayerUserData)
[4 bytes]  Size field 1 (content + size fields)
[4 bytes]  Size field 2 (content only)
[variable] Object properties
```

**Key Finding:** Type code is 0x0b1d (2845 decimal), NOT 0x1d (29 decimal).
The 0x0b prefix may indicate "array/collection" category, correlating with the 0x0b marker byte.

---

## Address Translation

| Base | Address |
|------|---------|
| Ghidra | 0x400000 |
| WinDbg (ACBMP) | 0x4f0000 |
| **Offset** | WinDbg = Ghidra + 0xf0000 |

---

## Function Index

| Ghidra | WinDbg | Name | Status |
|--------|--------|------|--------|
| FUN_00d39a60 | ACBMP+0x939a60 | Entry - AssassinMultiProfileData::Serialize | TRACED |
| FUN_00d32140 | ACBMP+0x932140 | MultiplayerUserData::Serialize | TRACED |
| FUN_01afcb30 | ACBMP+0x16fcb30 | Type registration (write mode only) | TRACED |
| FUN_01b0b3b0 | ACBMP+0x170b3b0 | Array/list serialization handler | TRACED |
| FUN_01b147e0 | ACBMP+0x17147e0 | Type 0x039d handler - ContentCode + markers | **TRACED** |
| FUN_01aebab0 | ACBMP+0x16ebab0 | Write array count | TRACED |
| FUN_01aff250 | ACBMP+0x16ff250 | Serialize array element | **TRACED** |
| FUN_01afd270 | ACBMP+0x16fd270 | Element dispatcher | **TRACED** |
| FUN_01af9930 | ACBMP+0x16f9930 | Bool/Byte field serializer | **TRACED** |
| FUN_01b2c6d0 | ACBMP+0x172c6d0 | Property value writer (writes 0x0B marker + value) | **TRACED** |
| FUN_01b0d530 | ACBMP+0x170d530 | Property header writer (writes 0x0B PropertyHeaderFlag) | **TRACED** |
| FUN_01aeb860 | ACBMP+0x16eb860 | Property validation check | **TRACED** |
| FUN_01b45640 | ACBMP+0x1745640 | vtable+0x58: Write byte | TRACED |
| FUN_01b80e70 | ACBMP+0x1780e70 | Actual byte write impl | TRACED |
| FUN_01af9a40 | ACBMP+0x16f9a40 | Float field serializer (wrapper) | TRACED |
| FUN_01b2cc00 | ACBMP+0x172cc00 | Float property writer (vtable+0x7c) | TRACED |
| FUN_01ae5710 | ACBMP+0x16e5710 | PlainOldDataBlock handler (vtable+0x40 memcpy) | **TRACED** |
| FUN_01af9b80 | ACBMP+0x16f9b80 | Enum field serializer | **TRACED** |
| FUN_01af6b80 | ACBMP+0x16f6b80 | ObjectInfo header writer | **TRACED** |
| FUN_01b45760 | ACBMP+0x1745760 | vtable+0x50: Write "Type" field | **TRACED** |
| FUN_01b887e0 | ACBMP+0x1787e0 | WriteUInt32 to stream | **TRACED** |
| FUN_01b80c90 | ACBMP+0x1780c90 | Write dispatcher (vtable+0x34/0x1c) | **TRACED** |
| FUN_01b404c0 | ACBMP+0x17404c0 | Property finalization (vtable+0x14), writes size fields | **TRACED** |
| FUN_01b88850 | ACBMP+0x1788850 | Write 8-byte type descriptor | **TRACED** |
| FUN_01b46870 | ACBMP+0x1746870 | WriteByte to stream | **TRACED** |
| FUN_01b04800 | ACBMP+0x1714800 | Type 0x039d - count/hash array writer | **TRACED** |
| FUN_01b38d90 | ACBMP+0x1738d90 | OpenSection (vtable+0x0c), reserves 4 bytes for size | **TRACED** |
| FUN_01b0d4b0 | ACBMP+0x170d4b0 | Finalization - writes Dynamic Properties footer | **TRACED** |

---

## Binary Format

### File Header (22 bytes) - FULLY TRACED via FUN_01af6b80 + FUN_01b404c0
```
Offset 0x00: [1 byte]   NbClassVersionsInfo = 0x00 (class version count)
Offset 0x01: [4 bytes]  ObjectName = 0x00000000 (null string hash, vtable+0x54)
Offset 0x05: [4 bytes]  ObjectID = 0x00000000 (vtable+0x84)
Offset 0x09: [1 byte]   InstancingMode = 0x00 (FUN_01b147e0)
Offset 0x0A: [4 bytes]  Type hash = 0xb4b55039 (FUN_01b80c90 → WriteUInt32)
Offset 0x0E: [4 bytes]  Size field 1 = 0x1836 (FUN_01b887e0, content + size fields)
Offset 0x12: [4 bytes]  Size field 2 = 0x182e (FUN_01b887e0, content only)
```
- Header built in temp buffer (0x02bd0000) then copied to output (0x02c40000)
- ObjectInfo fields (0x00-0x0D) written by FUN_01af6b80 in mode 0
- Size fields (0x0E-0x15) written at END by FUN_01b404c0 (Property finalization)
- Size difference: 8 bytes = size of both size fields (4+4)
- The 10 "zero" bytes before type hash are NOT padding - they are traced fields

### Dynamic Properties Section (4 bytes) - FULLY TRACED via FUN_01b0d4b0

The file ends with a "Dynamic Properties" section written during finalization.

**FUN_01b0d4b0 (Finalization) - TRACED via WinDbg:**
```c
void __fastcall FUN_01b0d4b0(int param_1)
{
  int iVar1 = *(int *)(param_1 + 0x58);  // Mode check

  if (((iVar1 == 1) || (iVar1 == 2)) || (iVar1 == 3)) {
    // Binary mode (1/2/3) - different path
    if (*(int *)(param_1 + 0x6c) != 0) {
      FUN_01b49c90();
      return;
    }
  }
  else if (*(int *)(param_1 + 0x20) != 0) {
    // Mode 0 - text-like mode with section markers
    FUN_01b0d3f0();
    (*vtable+0x14)("Properties");          // CloseSection - backpatch properties size
    (*vtable+0x0c)("Dynamic Properties");  // OpenSection - reserves 4 bytes
    if (*(int *)(param_1 + 0x28) != 0) {
      FUN_01af9d90(...);                   // Write dynamic properties (if any)
    }
    (*vtable+0x14)("Dynamic Properties");  // CloseSection - WRITES FOOTER!
    (*vtable+0x14)("Object");              // CloseSection - backpatch root object
  }
}
```

**Finalization Sequence (Mode 0):**
| Step | VTable | Call | Action |
|------|--------|------|--------|
| 1 | +0x14 | CloseSection("Properties") | Backpatch properties size in header |
| 2 | +0x0c | OpenSection("Dynamic Properties") | Reserve 4 bytes for size |
| 3 | - | FUN_01af9d90 | Write dynamic properties (if any exist) |
| 4 | +0x14 | **CloseSection("Dynamic Properties")** | **Write footer (size=0 if empty)** |
| 5 | +0x14 | CloseSection("Object") | Backpatch root object size |

**FUN_01b38d90 (OpenSection, vtable+0x0c) - WRITE mode:**
```c
if (mode == 0) {  // WRITE
    position = (*inner_vtable[0x4c])();           // Get current stream position
    section_stack[index].start = position;         // Store in section stack
    section_stack[index].size = 0;                 // Initial size = 0
    (*inner_vtable[0x44])(4);                      // Reserve 4 bytes for size
    counter++;                                      // Increment section counter
}
```

**FUN_01b404c0 (CloseSection, vtable+0x14) - WRITE mode:**
```c
if (mode == 0) {  // WRITE
    counter--;
    size = calculated_size;
    (*inner_vtable[0x50])(stored_position);        // Seek to reserved spot
    (*inner_vtable[0x34])(size);                   // Write actual size (4 bytes)
    (*inner_vtable[0x54])(current_position);       // Seek back
    if (counter > 0) {
        FUN_01b79f90(size + 4);                    // Update parent section size
    }
}
```

**File Structure:**
```
Offset [end of properties]: [4 bytes] Dynamic Properties size = 0x00000000
```

**Key Points:**
- Footer written by `CloseSection("Dynamic Properties")` during finalization
- Size = 0 when no dynamic properties exist (most saves)
- These 4 bytes are NOT included in the header size fields
- Confirmed via WinDbg TTD trace at position A37AE6:95

### FUN_01af9d90 - Dynamic Properties Writer (TRACED)

**What are Dynamic Properties?**
Dynamic properties are complex-type properties that have non-null values at runtime. They are written separately from regular properties.

**Complex Types that qualify as Dynamic (bits 16-21 of type_info):**
| Type Code | Enum | Description |
|-----------|------|-------------|
| 0x12 | 18 | ENUM |
| 0x13 | 19 | OBJECT |
| 0x14 | 20 | STRUCT |
| 0x15 | 21 | ARRAY |
| 0x16 | 22 | CLASS |
| 0x1c | 28 | MAP |
| 0x1e | 30 | SET |

**Counting Logic:**
```c
// Iterate through object's property list
local_10 = *(undefined4 **)(iVar8 + 8);                         // Property list start
local_18 = local_10 + (*(ushort *)(iVar8 + 0xe) & 0x3fff) * 8;  // Property list end

local_14 = 0;  // Count of dynamic properties
do {
    uVar4 = (uint)puVar5[1] >> 0x10 & 0x3f;  // Extract type from bits 16-21
    local_5 = '\x01';  // Assume included

    // Check if type is one of the complex types
    if (uVar4 == 0x16 || uVar4 == 0x13 || uVar4 == 0x15 ||
        uVar4 == 0x14 || uVar4 == 0x12 || uVar4 == 0x1e || uVar4 == 0x1c) {
        iVar8 = FUN_01b5a3b0(*puVar5);  // Check if property has value
        if (iVar8 == 0) {
            local_5 = '\0';  // NULL - exclude from count
        }
    }

    if (local_5 != '\0') {
        local_14 = local_14 + 1;  // Increment count
    }
} while (local_10 != local_18);
```

**Mode 3 Binary Format:**
```c
if (*(int *)(param_1 + 0x58) == 3) {
    // Write count first
    (*vtable+0x08)("NbDynamicProperties");   // OpenSection
    (*vtable+0x84)(&local_14);               // Write UINT32 count
    (*vtable+0x10)("NbDynamicProperties");   // CloseSection
}

// Then for each property with a value:
if (*local_2c != '\0') {
    (*vtable+0x08)(&DAT_022c4de4);    // OpenSection
    (*vtable+0x84)(&local_c);          // Write property ID (4 bytes)
    (*vtable+0x10)(&DAT_022c4de4);    // CloseSection

    FUN_01b182b0(&local_3c);           // Write type descriptor (8 bytes)
    FUN_01b0b9a0(...);                 // Write property value
}
```

**Dynamic Properties Structure (Mode 3):**
```
[4 bytes]   NbDynamicProperties - count of dynamic properties
For each dynamic property:
  [4 bytes]   Property ID
  [8 bytes]   Type descriptor
  [N bytes]   Property value (format depends on type)
```

**Why footer is usually 0:**
Primitive types (BOOL, INT8, INT32, FLOAT, etc.) are NOT dynamic properties. Only complex types (CLASS, OBJECT, ARRAY, STRUCT, ENUM, SET, MAP) with non-null values get written here. Most simple objects have no qualifying properties, so `NbDynamicProperties = 0` and nothing is written, resulting in `dynamic_properties_size = 0`.

### Property Structure
```
[4 bytes]   Length - size of following data
[4 bytes]   Property hash - identifies the property
[8 bytes]   Type descriptor - determines value format
[1 byte]    0x0b - marker indicating value follows
[variable]  Value - format depends on type descriptor
```

### Property Metadata Structure (Static Data) - TRACED
Each property has a 32-byte metadata record in the game binary:
```
Offset 0x00: [4 bytes]  Flags = 0x02000001
Offset 0x04: [4 bytes]  Property hash (identifies property)
Offset 0x08: [8 bytes]  Type descriptor
Offset 0x10: [4 bytes]  Field offset info
Offset 0x14: [12 bytes] Additional metadata
```
- Found at addresses like 0x0241da70, 0x0241db50, etc.
- Passed to serializer functions as the last parameter (PTR_DAT_*)
- Type code is in bytes 14-15 of the type descriptor (offset 0x0E-0x0F)

### Known Type Descriptors (8 bytes, little-endian)
| Type Bytes | Type Code | Value Format |
|------------|-----------|--------------|
| 00 00 00 00 00 00 00 00 | 0x00 | Bool - marker (0x0B) + 1 byte value |
| 00 00 00 00 00 00 05 00 | 0x05 | Int16/UInt16 - 2 bytes (TRACED) |
| 00 00 00 00 00 00 06 00 | 0x06 | Int32 - 4 bytes, vtable+0x80 (TRACED) |
| 00 00 00 00 00 00 07 00 | 0x07 | UInt32 - 4 bytes, vtable+0x84 |
| 00 00 00 00 00 00 09 00 | 0x09 | Float - 4 bytes IEEE 754 (TRACED) |
| 00 00 00 00 00 00 0a 00 | 0x0a | Float variant (seen in property metadata) |
| 51 c8 d0 a7 00 00 19 00 | 0x19 | Enum - 4 byte value + 4 byte name hash |
| TT TT TT TT 00 00 1d 0b | 0x0b1d | Array with typed elements (TRACED) |
| 00 00 00 00 00 00 9d 03 | 0x039d | ContentCode + Hash Array (TRACED) |

### Type Code Reference (Complete)

Type code is extracted from `type_info`: `(type_info >> 16) & 0x3F`

For container types (MAP, ARRAY), element type is: `(type_info >> 23) & 0x3F`

| Code | Hex | Name | Size | VTable | Notes |
|------|-----|------|------|--------|-------|
| 0 | 0x00 | BOOL | 1 | +0x58 | Boolean |
| 1 | 0x01 | BOOL_ALT | 1 | | Boolean variant |
| 2 | 0x02 | UINT8 | 1 | +0x90 | Unsigned byte |
| 3 | 0x03 | INT8 | 1 | +0x94 | Signed byte |
| 4 | 0x04 | UINT16 | 2 | +0x88 | Unsigned 16-bit |
| 5 | 0x05 | INT16 | 2 | +0x8c | Signed 16-bit |
| 6 | 0x06 | INT32_V2 | 4 | +0x74 | Signed 32-bit (binary data confirms integer) |
| 7 | 0x07 | UINT32 | 4 | +0x84 | Unsigned 32-bit |
| 8 | 0x08 | INT32 | 4 | +0x80 | Signed 32-bit |
| 9 | 0x09 | UINT64 | 8 | +0x7c | Unsigned 64-bit |
| 10 | 0x0A | FLOAT_ALT | 4 | | Float variant (4-byte IEEE 754) |
| 11 | 0x0B | FLOAT64 | 8 | +0x78 | Double precision |
| 12 | 0x0C | VECTOR2 | 8 | +0x70 | 2x float32 |
| 13 | 0x0D | VECTOR3 | 12 | | 3x float32 |
| 14 | 0x0E | VECTOR4 | 16 | | 4x float32 |
| 15 | 0x0F | MATRIX3X3 | 36 | | 9x float32 |
| 16 | 0x10 | MATRIX4X4 | 64 | | 16x float32 |
| 17 | 0x11 | STRING | 4 | +0x54 | 4-byte hash in binary mode |
| 18 | 0x12 | OBJECTREF | var | | Object reference |
| 19 | 0x13 | OBJECTREF_EMB | var | | Embedded object reference |
| 20 | 0x14 | ENUM | var | | Enumeration |
| 21 | 0x15 | STRUCT | var | | Structure |
| 22 | 0x16 | CLASS | var | | Nested object (ObjectInfo header) |
| 23 | 0x17 | ARRAY | var | | Array container |
| 24 | 0x18 | MAP | var | | Map container |
| 25 | 0x19 | ENUM_ALT | 8 | | 4-byte value + 4-byte name hash |
| 26 | 0x1A | GUID | 16 | | 16-byte GUID |
| 27 | 0x1B | VARSTRING | var | | UTF-16LE: count(4) + chars + null(2) |
| 28 | 0x1C | POINTER | var | | Pointer reference |
| 29 | 0x1D | MAP_ALT | var | | Map variant |
| 30 | 0x1E | SET | var | | Set container |

**Size column**: Fixed byte count (excluding 0x0B marker), or "var" for variable-length types.

**Dynamic property types** (written by FUN_01af9d90 when non-null):
- 0x12 OBJECTREF, 0x13 OBJECTREF_EMB, 0x14 ENUM, 0x15 STRUCT, 0x16 CLASS, 0x1C POINTER, 0x1E SET

### Type Descriptor Format Variants
**Simple types (0x00-0x19, 0x039d):**
```
[6 bytes]  Zeros or type-specific data
[2 bytes]  Type code (little-endian)
```

**Array with element type (0x0b1d) - TRACED:**
```
[4 bytes]  Inner element type hash (e.g., 0xc292f31f for MultiplayerUserData)
[4 bytes]  Type code dword 0x0b1d0000 (writes as 00 00 1d 0b in memory)
```
- Type code is 0x0b1d stored as full dword, NOT 0x1d with padding
- Followed by marker (0x0b), ContentCode, count, then nested element data
- Elements are full objects with their own 22-byte headers (ObjectInfo + type hash + sizes + properties)

### Bool/Byte Property Structure (FUN_01af9930 → FUN_01b2c6d0 → FUN_01b0d530) - FULLY TRACED
```
[4 bytes]   Length (14 for bool)
[4 bytes]   Property hash
[8 bytes]   Type descriptor (00 00 00 00 00 00 00 00 for type 0)
[1 byte]    0x0b marker (PropertyHeaderFlag)
[1 byte]    Bool value (0x00 = false, 0x01 = true)
```

**FUN_01af9930** (Bool/Byte field serializer):
```c
void __thiscall FUN_01af9930(int param_1, char *param_2, undefined4 param_3)
{
  if (*(char *)(*(int *)(param_1 + 4) + 4) == '\0') {
    *param_2 = *param_2 != '\0';  // Normalize to 0 or 1
  }
  cVar1 = FUN_01b2c6d0(param_3, param_2);  // Call property value writer
  if ((cVar1 != '\0') && (*(char *)(*(int *)(param_1 + 4) + 4) != '\0')) {
    *param_2 = *param_2 != '\0';  // Normalize again on read
  }
}
```

**FUN_01b2c6d0** (Property value writer):
```c
// After validation via FUN_01aeb860 and FUN_01b0d530...
piVar1 = *(int **)(param_1 + 4);
(**(code **)(*piVar1 + 8))("Value");      // BeginElement - NO-OP in binary mode
(**(code **)(*piVar1 + 0x58))(param_3);   // Write byte via vtable+0x58
(**(code **)(*piVar1 + 0x10))("Value");   // EndElement - NO-OP in binary mode

// Mode check for "Property" marker (skipped in modes 1/2/3)
iVar2 = *(int *)(param_1 + 0x58);
if ((((iVar2 != 1) && (iVar2 != 2)) && (iVar2 != 3)) && ((*(byte *)(param_1 + 0x4e) & 1) == 0)) {
  (**(code **)(**(int **)(param_1 + 4) + 0x14))("Property");
}
```

**FUN_01b0d530** (Property header writer - writes 0x0B marker):
```c
// In mode 0, after property validation...
if (iVar3 == 0) {
  param_2 = (uint *)(CONCAT13(cVar2, param_2._0_3_) | 0xb000000);  // Set 0x0B flag
  FUN_01aeb610((int)&param_2 + 3);  // Write PropertyHeaderFlag
}
```

**Key insight**: The 0x0B marker is the PropertyHeaderFlag written by FUN_01b0d530 for ALL property values, not just bool/byte types.

### Float Property Structure (FUN_01af9a40 → FUN_01b2cc00) - TRACED
```
[4 bytes]   Length (17 for float)
[4 bytes]   Property hash
[8 bytes]   Type descriptor (contains 0x09 = float type)
[1 byte]    0x0b marker
[4 bytes]   Float value (IEEE 754 little-endian)
```
- Written by FUN_01b2cc00 via vtable+0x7c
- Mode 0 writes "Value" marker, float value, end marker, then "Property"
- Examples: 0.0f = `00 00 00 00`, 1.0f = `00 00 80 3f`

### Enum Property Structure (FUN_01af9b80) - TRACED
```
[4 bytes]   Length (21 for enum)
[4 bytes]   Property hash
[8 bytes]   Type descriptor (contains 0x19 = enum type)
[1 byte]    0x0b marker
[4 bytes]   Enum value (uint32)
[4 bytes]   Enum name hash (for validation/version compat)
```
- Written by FUN_01af9b80 via vtable+0x84 (WriteUInt32)
- Name hash allows reader to validate/remap if enum values change between versions
- Mode 0 writes "EnumValue" marker, value, end marker, then "EnumName"

### ContentCode + Hash Array Property Structure (Type 0x039d) - FULLY TRACED
```
[4 bytes]   Length (18 minimum, varies with count)
[4 bytes]   Property hash
[8 bytes]   Type descriptor (00 00 00 00 00 00 9d 03)
[1 byte]    0x0b marker
[1 byte]    ContentCode value
[4 bytes]   Count (uint32, number of elements)
[count*4]   Element array (each element is 4 bytes, copied as PlainOldData)
```

**Traced Write Sequence:**
1. FUN_01b147e0 writes ContentCode byte via vtable+0x98 (position A38021:29B)
2. FUN_01aebab0 writes Count via vtable+0x84 → FUN_01b887e0 (position A37E9B:2F6)
3. FUN_01ae5710 writes Elements via vtable+0x40 as PlainOldDataBlock (position A37EA3:884)

**Key Insight:** Elements are NOT individually serialized - they are bulk copied via memcpy in FUN_01ae5710.

- Length formula: 4 (hash) + 8 (type) + 1 (marker) + 1 (code) + 4 (count) + (count × 4) = 18 + (count × 4)

**Examples from game_uncompressed_4.bin:**
```
Offset 0x5FC: Length=18, Code=0x01, Count=0, Hashes=[]
Offset 0x612: Length=30, Code=0x01, Count=3, Hashes=[0x57554DCF, 0x57554DDF, 0x57554DDA]
```

**Traced buffer example (game_uncompressed_4.windbgtraced.bin at 0x90):**
```
9d 03 0b 01 02 00 00 00 55 02 ee 8c ...
[typ] [m][c][count=2   ][elem 0x8cee0255]
```

---

## BinarySerializer VTable (Ghidra: 0x022C7FA8)

| Offset | Ghidra Func | Purpose | Traced |
|--------|-------------|---------|--------|
| +0x08 | FUN_01b38d80 | Begin marker ("Value") | Yes |
| +0x0C | ? | ? | No |
| +0x10 | FUN_01b38e60 | End marker | Yes |
| +0x14 | FUN_01b404c0 | Write "Property" (mode 0 only) | Yes |
| +0x1C | FUN_01b38e40 | Check at end (returns 0 in write mode) | Yes |
| +0x3C | (stream) | Write byte to output buffer | Yes |
| +0x40 | ? | PlainOldDataBlock bulk write | Yes |
| +0x58 | FUN_01b45640 | Write byte/bool value | Yes |
| +0x7C | ? | Write float value | Yes |
| +0x84 | ? | Write int32 | No |
| +0x98 | ? | Read ContentCode | Yes |

---

## Serialization Context (0x05ebfa44)

| Offset | Value | Purpose |
|--------|-------|---------|
| +0x04 | 0x2b37bf90 | Serializer object |
| +0x08 | (varies) | Type info pointer |
| +0x0c | (varies) | Current type hash |
| +0x10 | (varies) | Type-related |
| +0x1c | 0xfb630888 | Data object being serialized |
| +0x20 | (varies) | Set to 1 during element serialization |
| +0x2c | (varies) | Element type info |
| +0x30 | (varies) | Override type info |
| +0x4e | 0x20 | Flags (bit 0 = PlainOldDataBlock enable) |
| +0x4f | (varies) | More flags |
| +0x58 | 0x00 | Mode (0=text-like, 1/2/3=binary) |
| +0x79 | 0x01 | ContentCode flag |
| +0x7a | (varies) | Array-related flag |

### Mode Behavior
- **Mode 0**: Writes "Value" markers AND "Property" markers
- **Mode 1/2/3**: Skips "Property" markers (pure binary)

---

## Type Hashes Discovered

| Hash | Name | Serializer | Notes |
|------|------|------------|-------|
| 0xb4b55039 | "AssassinMultiProfileData" | FUN_00d39a60 | Root type |
| 0xc292f31f | "MultiplayerUserData" | FUN_00d32140 | Array element type |
| 0x94daaee6 | **"AbilityProfileData"** | FUN_00cddd60 | Nested in MultiplayerUserData |
| 0xf95fcfa8 | **"OutfitData"** | FUN_00ccd3d0 | Nested in MultiplayerUserData |
| 0xbf4c2013 | (unknown) | Appears in header area |
| 0x096ba47c | (unknown) | Enum property hash (+0x1c) |
| 0xed9fe0d4 | (unknown) | Enum name hash (value=0) |
| 0xafbeea25 | (unknown) | Byte property (+0x28) |
| 0x221991ef | (unknown) | Byte property (+0x29) |
| 0x20ad7434 | (unknown) | Byte property (+0x2a) |
| 0xb6ba16bb | (unknown) | Byte property (+0x2b) |
| 0x1a361ae1 | (unknown) | Byte property (+0x2c) |
| 0xac36ddcb | (unknown) | Byte property (+0x2d) |
| 0xcf74fe85 | (unknown) | Float property (+0x18) |
| 0xfae20de8 | (unknown) | Byte property (+0x2e) |
| 0xc7f33a0d | (unknown) | Byte property (+0x2f) |

### Inner Type Structures (from Ghidra static analysis)

**OutfitData (0xf95fcfa8)** - FUN_00ccd3d0:
| Offset | Property Hash | Type Code | Serializer | Notes |
|--------|---------------|-----------|------------|-------|
| +0x00 | 0x8157b2c0 | 0x06 | FUN_01af9a20 | Unknown type |
| +0x04 | 0xe717d13b | 0x05 | FUN_01af99e0 | Unknown type |
| +0x06 | 0x00d0e643 | 0x05 | FUN_01af99e0 | Unknown type |

**AbilityProfileData (0x94daaee6)** - FUN_00cddd60:
| Offset | Property Hash | Type Code | Serializer | Notes |
|--------|---------------|-----------|------------|-------|
| +0x00 | (via PTR_DAT_0241dc78) | array | FUN_01b0b3b0 | Hash array |
| +0x08 | (via PTR_DAT_0241dc7c) | array | FUN_01b0b3b0 | Hash array |
| +0x10 | (via PTR_DAT_0241dc80) | array | FUN_01b0b3b0 | Hash array |
| +0x18 | (via PTR_DAT_0241dc84) | array | FUN_01b0b3b0 | Hash array |
| +0x24 | 0x3fdeb65c | 0x00 | FUN_01af9930 | Byte |
| +0x20 | 0x9b44ee2a | 0x1b | FUN_01ae5600 | Unknown type |

### Type 0x05 (Int16/UInt16) - TRACED
- Serializer: FUN_01af99e0 → FUN_01b2c9c0
- VTable offset: +0x8c
- Value size: **2 bytes**
- Total property: 19 bytes (4 length + 4 hash + 8 type + 1 marker + 2 value)
- TTD Position: A37F0F:2F0 (value write)

### Type 0x06 (Int32) - TRACED
- Serializer: FUN_01af9a20 → FUN_01b2cb40
- VTable offset: +0x80
- Value size: **4 bytes**
- Total property: 21 bytes (4 length + 4 hash + 8 type + 1 marker + 4 value)
- TTD Position: A37F09:294 (value write)

### Type 0x1b - TRACED
- Serializer: FUN_01ae5600 → FUN_01b33c40
- VTable offset: +0x44
- Value size: **4 bytes**
- Total property: 21 bytes (4 length + 4 hash + 8 type + 1 marker + 4 value)
- TTD Position: A37EA9:468 (value write)
- Property hash example: 0x9b44ee2a (AbilityProfileData+0x20)

**FUN_01b33c40 (inner handler):**
```c
(**(code **)(*piVar1 + 0x44))(param_3);   // Write value via vtable+0x44
```

Note: vtable+0x44 is adjacent to +0x40 (PlainOldDataBlock). May be a variant of Int32.

### Undocumented Type Codes
| Type Code | Serializer | Notes |
|-----------|------------|-------|
| 0x0198 | ? | Not present in test binary - may be used in other save files |

---

## Data Structures

### AssassinMultiProfileData (0xfb630888)
| Offset | Value | Type | Serializer |
|--------|-------|------|------------|
| +0x18 | 0x3f800000 | float (1.0f) | FUN_01af9a40 |
| +0x1c | 0x00000000 | enum (value=0, hash=0xed9fe0d4) | FUN_01af9b80 |
| +0x20 | 0x266494b0 | array ptr (2 items) | FUN_01b0b3b0 |
| +0x28 | 0x00 | byte | FUN_01af9930 |
| +0x29 | 0x01 | byte | FUN_01af9930 |
| +0x2a | 0x01 | byte | FUN_01af9930 |
| +0x2b | 0x01 | byte | FUN_01af9930 |
| +0x2c | 0x01 | byte | FUN_01af9930 |
| +0x2d | 0x01 | byte | FUN_01af9930 |
| +0x2e | 0x01 | byte | FUN_01af9930 |
| +0x2f | 0x00 | byte | FUN_01af9930 |

### MultiplayerUserData Array
- **Count**: 2 items
- **Item 0**: 0x266494b0
- **Item 1**: 0x26649510 (96 bytes apart)
- **Element type hash**: 0xC292F31F

---

## Tracing Session Log

| Position | Action |
|----------|--------|
| A37E80:2CB | Entry point FUN_00d39a60 |
| A37E88:4F | Type registration |
| A37E99:D1 | Array handler entry |
| A37E9B:34B | Item 0 - entered FUN_01aff250 |
| A37E9B:3E9 | Item 0 - entered FUN_01afd270 |
| A37E9B:4E4 | Item 0 - entered FUN_00d32140 (MultiplayerUserData) |
| A37E9F:45F | Nested array handler for +0x4c |
| A3804D:CF | Item 1 serialized |
| A38271:3EF | Byte 0x00 written to buffer |
| A380F9:42 | Buffer allocation (02c40000) |
| A380F9:A4 | Header copy from 02bd0000 to 02c40000 |
| A3828A:4AF | Size field 2 write (0x182e to 02c40012) |
| A3828E:D0 | Size field 1 write (0x1836 to 02c4000e) |
| A38282:9E | Enum serializer FUN_01af9b80 entry (field +0x1c) |
| A38286:97 | Enum serializer return (wrote 21 bytes at 02c41807) |
| A38031:A3 | Float serializer FUN_01af9a40 entry (MultiplayerUserData+0x00) |
| A38035:95 | Float serializer return (wrote 17 bytes, IEEE 754 0.0f) |
| A37E9B:34C | Item 0 array element (FUN_01aff250) |
| A3804D:FD | Item 1 array element (FUN_01aff250) - no delimiter between items |
| A38021:17A | Type 0x039d descriptor write (FUN_01b88850) |
| A38021:29B | Type 0x039d ContentCode write (FUN_01b147e0 via vtable+0x98) |
| A37E9B:2F6 | Type 0x039d count write (count=2, FUN_01aebab0) |
| A37EA3:884 | Type 0x039d element write (PlainOldDataBlock memcpy, FUN_01ae5710) |

---

## WinDbg Commands Reference

```
# Output buffer
db 02c40000 L200

# Source buffer (header)
db 02bd0000 L20

# Context structure
dd 05ebfa44 L20

# Data object
dd fb630888 L20

# Serializer object
dd 2b37bf90 L10

# Stream object
dd 05ebfac4 L10

# Go to entry point
!tt A37E80:2CB

# Go to header copy
!tt A380F9:A4
```

---

## Next Steps

1. [x] Trace FUN_01aff250 (array element format)
2. [x] Trace header structure (FUN_01af6b80 - ObjectInfo writer) - **COMPLETE**
3. [x] Trace size fields (FUN_01b404c0 → FUN_01b887e0) - **COMPLETE**
4. [x] Trace enum serializer FUN_01af9b80 - **COMPLETE** (was misnamed object/null)
5. [x] Trace float serializer FUN_01af9a40 → FUN_01b2cc00 - **COMPLETE** (IEEE 754 confirmed)
6. [x] Document nested object delimiters - **COMPLETE** (no explicit delimiters, uses Value/Property markers)
7. [x] Trace type 0x039d value length - **COMPLETE** (ContentCode + count + hash array)
8. [ ] Build parser based on traced format
