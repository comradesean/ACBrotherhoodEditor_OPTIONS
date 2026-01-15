# Function Documentation

This document contains detailed function documentation extracted from [SECTION3_SERIALIZATION.md](SECTION3_SERIALIZATION.md).

For the overall file format, section nesting concepts, and key findings, see the main document.

---

## Table of Contents

- [READ Path Functions](#read-path)
  - [FUN_01710580 - AssassinSingleProfileData::Serialize](#1-fun_01710580---assassinsingleprofiledataserialize)
  - [FUN_005e3700 - SaveGameDataObject::Serialize](#2-fun_005e3700---savegamedataobjectserialize-base-class)
  - [FUN_01b0a1f0 - Base Class Field Serializer Wrapper](#3-fun_01b0a1f0---base-class-field-serializer-wrapper)
  - [FUN_01b12fa0 - Property Serialization Core](#4-fun_01b12fa0---property-serialization-core)
  - [FUN_01b49610 - Stream Read/Write (4 bytes)](#5-fun_01b49610---stream-readwrite-4-bytes---uint32)
  - [FUN_01b6f440 - Actual 4-Byte Read](#6-fun_01b6f440---actual-4-byte-read)
  - [FUN_01b09650 - Bool Property Serializer](#7-fun_01b09650---bool-property-serializer)
  - [FUN_01b11fb0 - Bool Serialization Core](#8-fun_01b11fb0---bool-serialization-core)
  - [FUN_01b497f0 - Stream Read/Write (1 byte)](#9-fun_01b497f0---stream-readwrite-1-byte---bool)
  - [FUN_01b09760 - uint64 Property Serializer](#10-fun_01b09760---uint64-property-serializer)
  - [FUN_01b124e0 - uint64 Serialization Core](#11-fun_01b124e0---uint64-serialization-core)
  - [FUN_01b48be0 - uint64 VTable Thunk](#12-fun_01b48be0---uint64-vtable-thunk)
  - [FUN_01b496d0 - Stream Read/Write (8 bytes)](#13-fun_01b496d0---stream-readwrite-8-bytes---uint64)
  - [FUN_01b6f490 - Actual 8-Byte Read](#14-fun_01b6f490---actual-8-byte-read)
  - [uint64 Read Complete Call Chain](#uint64-read-complete-call-chain)
  - [FUN_01b0d0c0 - Finalization](#15-fun_01b0d0c0---finalization)
- [WRITE Path Functions](#write-path)
  - [Entry Point - FUN_01710580 WRITE Mode](#entry-point---fun_01710580-write-mode)
  - [FUN_01b09e20 - Header Writer Wrapper](#fun_01b09e20---header-writer-wrapper)
  - [FUN_01b08ce0 - Actual Header Writer](#fun_01b08ce0---actual-header-writer)
  - [FUN_01b0d500 - Single Byte Writer](#fun_01b0d500---single-byte-writer-write-mode-traced)
  - [WRITE Mode VTable Functions - NO-OPs](#write-mode-vtable-functions---no-ops-confirmed)
  - [FUN_01b48b70 - WriteByte Dispatcher](#fun_01b48b70---writebyte-dispatcher-vtable0x98)
  - [FUN_01b6f370 - Core Byte Write to Buffer](#fun_01b6f370---core-byte-write-to-buffer)
  - [FUN_01b49610 - 4-Byte Write Dispatcher](#fun_01b49610---4-byte-write-dispatcher)
  - [FUN_01b6fea0 - Core 4-Byte Write to Buffer](#fun_01b6fea0---core-4-byte-write-to-buffer)
  - [FUN_01b48e90 - String Serializer](#fun_01b48e90---string-serializer)
  - [FUN_01b08ce0 - Type Info Block Writer](#fun_01b08ce0---type-info-block-writer-continuation)
- [Property Serializers](#property-serializers)
  - [FUN_01b48fb0 - TypeInfo Serializer](#fun_01b48fb0---typeinfo-serializer-vtable0x50---complete-trace)
  - [FUN_01b0d140 - Property Header Writer](#fun_01b0d140---property-header-writer-complete-trace)
  - [FUN_01b0e680 - Property Hash Writer](#16-fun_01b0e680---property-hash-writer)
  - [FUN_01b0e980 - Type Info Writer](#17-fun_01b0e980---type-info-writer)
  - [FUN_01b49020 - 8-Byte Serializer with Optional Type Name](#18-fun_01b49020---8-byte-serializer-with-optional-type-name)
  - [FUN_01b48e80 - Bool Serializer (vtable[0x58])](#19-fun_01b48e80---bool-serializer-vtable0x58---write-mode)
  - [FUN_01b497f0 - 1-Byte Read/Write Dispatcher](#20-fun_01b497f0---1-byte-readwrite-dispatcher)
  - [FUN_01b48be0 - uint64 Serializer (vtable[0x7c])](#21-fun_01b48be0---uint64-serializer-vtable0x7c---write-mode)
  - [FUN_01b496d0 - 8-Byte Read/Write Dispatcher (WRITE)](#22-fun_01b496d0---8-byte-readwrite-dispatcher-write-mode-traced)
  - [vtable[0x84] - uint32 Serializer](#vtable0x84---uint32-serializer-write-path)
  - [FUN_01b0d0c0 - Finalization (Dynamic Properties)](#fun_01b0d0c0---finalization-dynamic-properties)
- [Utility Functions](#utility-functions)

---

<a id="read-path"></a>
## READ Path Functions

### 1. FUN_01710580 - AssassinSingleProfileData::Serialize

**WinDbg Address:** ACBSP+0x1310580 (0x01df0580)
**TTD Position:** B1F2B:920

> Trace: See TRACES.md - FUN_01710580 Entry Point Context (serializer context structure, registers, mode check)

**Call Sequence (traced):**
1. Store object ptr: `[esi+1ch] = edi`
2. Mode check → Skip header write (READ mode)
3. Save `[esi+20h]` to EBX (value = 0x01)
4. Set `[esi+20h] = 0`
5. Call FUN_005e3700 (base class)
6. Restore `[esi+20h]` from EBX
7. Call FUN_01b09650 for bool_field_0x20
8. Call FUN_01b09650 for bool_field_0x21
9. Call FUN_01b09650 for bool_field_0x22
10. Call FUN_01b09650 for bool_field_0x23
11. Call FUN_01b09760 for uint64_field_0x18
12. Call FUN_01b09650 for bool_field_0x24
13. Call FUN_01b0d0c0 (finalize)

---

### 2. FUN_005e3700 - SaveGameDataObject::Serialize (Base Class)

**WinDbg Address:** ACBSP+0x1e3700 (0x00cc3700)
**TTD Position:** B1F2B:930

**Traced Flow:**
1. Same prologue pattern as derived class
2. Mode check → Skip header write (READ mode)
3. Call FUN_01b0a1f0(param_1 + 4, property_metadata)
4. Call FUN_01b09620(param_1 + 8)
5. Call FUN_01b0d0c0()

---

### 3. FUN_01b0a1f0 - Base Class Field Serializer Wrapper

> Assembly: See DISASSEMBLY.md - FUN_01b0a1f0 - Base Class Field Serializer Wrapper

**WinDbg Address:** ACBSP+0x170a1f0 (0x021ea1f0)

This is a thin wrapper that calls FUN_01b12fa0.

---

### 4. FUN_01b12fa0 - Property Serialization Core

**WinDbg Address:** ACBSP+0x1712fa0 (0x021f2fa0)

**Parameters:**
- ECX = serializer context
- [esp+4] = property metadata (0x02eccf90)
- [esp+8] = field pointer (0xf74c0a54)

> Trace: See TRACES.md - FUN_01b12fa0 Property Serialization Core Trace (property metadata dump)

- Hash 0xbf4c2013 = SaveGameDataObject base class field

**Traced Flow:**
1. FUN_01b07940 - Validation (checks mode, property flags)
2. FUN_01b0d140 - More validation
3. vtable[2]("Value") - Start XML element
4. **vtable[0x84](field_ptr)** - Actual serialize!
5. vtable[4]("Value") - End XML element

---

### 5. FUN_01b49610 - Stream Read/Write (4 bytes - uint32)

**WinDbg Address:** ACBSP+0x1749610 (0x02229610)

**Decompilation:**
```c
void __thiscall FUN_01b49610(int param_1, undefined4 *param_2)
{
  // Adjust position by ±4
  if (*(short *)(param_1 + 0x1010) != 0) {
    if (*(char *)(param_1 + 4) == '\0') {  // Write
      *piVar1 = *piVar1 + 4;
    } else {  // Read
      *piVar1 = *piVar1 + -4;
    }
  }

  if (*(char *)(param_1 + 4) != '\0') {  // Read mode
    (**(code **)(**(int **)(param_1 + 8) + 0x1c))();  // vtable[7]
  } else {  // Write mode
    (**(code **)(**(int **)(param_1 + 8) + 0x34))(*param_2);  // vtable[13]
  }
}
```

---

### 6. FUN_01b6f440 - Actual 4-Byte Read

**WinDbg Address:** ACBSP+0x176f440 (0x0224f440)
**TTD Position:** B1F2B:B7B

**Decompilation:**
```c
void __thiscall FUN_01b6f440(int param_1, undefined4 *param_2)
{
  // Read 4 bytes from stream buffer
  *param_2 = **(undefined4 **)(param_1 + 0x18);

  // Optional byte-swap for endianness
  if ((*(byte *)(param_1 + 4) & 1) != 0) {
    // Swap bytes 0↔3 and 1↔2
  }

  // Advance stream position
  *(int *)(param_1 + 0x18) = *(int *)(param_1 + 0x18) + 4;
}
```

> Trace: See TRACES.md - FUN_01b6f440 Actual 4-Byte Read Trace (stream object, buffer position, field value)

---

### 7. FUN_01b09650 - Bool Property Serializer

**WinDbg Address:** ACBSP+0x1709650 (0x021e9650)
**TTD Position:** B1F2B:BE9

> Trace: See TRACES.md - Bool Property Read Trace (parameters, property metadata at 0x03053250)

**Traced Flow:**
1. Mode check
2. Call FUN_01b11fb0 (actual serialize)
3. Normalize bool to 0/1

---

### 8. FUN_01b11fb0 - Bool Serialization Core

**WinDbg Address:** ACBSP+0x1711fb0 (0x021f1fb0)

Similar structure to FUN_01b12fa0 but uses **vtable[0x58]** instead of vtable[0x84]:
1. FUN_01b07940 - Validation
2. FUN_01b0d140 - Validation
3. vtable[2]("Value")
4. **vtable[0x58](field_ptr)** - Bool serialize
5. vtable[4]("Value")

---

### 9. FUN_01b497f0 - Stream Read/Write (1 byte - bool)

**WinDbg Address:** ACBSP+0x1749610 (0x02229610)

```c
// Adjust position by ±1 (bool is 1 byte)
if (mode == read) {
  vtable[0x24]();  // Read 1 byte
} else {
  vtable[0x3c](*param_2);  // Write 1 byte
}
```

> Trace: See TRACES.md - Bool Property Read Trace (buffer position 0x0a3a063c, value read)

---

### 10. FUN_01b09760 - uint64 Property Serializer

**WinDbg Address:** ACBSP+0x1709760 (0x021e9760)
**TTD Position:** B1F2B:1643

> Trace: See TRACES.md - uint64 Property Read Trace (parameters, property metadata at 0x030532d0)

Uses **vtable[0x7c]** for uint64 serialization.

---

### 11. FUN_01b124e0 - uint64 Serialization Core

> Assembly: See DISASSEMBLY.md - FUN_01b124e0 - uint64 Serialization Core

**WinDbg Address:** ACBSP+0x17124e0 (0x021f24e0)
**TTD Position:** B1F2B:1644

Similar structure to FUN_01b11fb0 (bool) but uses **vtable[0x7c]** instead of vtable[0x58].

---

### 12. FUN_01b48be0 - uint64 VTable Thunk

> Assembly: See DISASSEMBLY.md - FUN_01b48be0 - uint64 VTable Thunk

**WinDbg Address:** ACBSP+0x1748be0 (0x02228be0)
**TTD Position:** B1F2B:1863

Thin wrapper that immediately jumps to FUN_01b496d0.

---

### 13. FUN_01b496d0 - Stream Read/Write (8 bytes - uint64)

> Assembly: See DISASSEMBLY.md - FUN_01b496d0 - Stream Read/Write (8 bytes - uint64)

**WinDbg Address:** ACBSP+0x17496d0 (0x022296d0)
**TTD Position:** B1F2B:1867

**Decompilation:**
```c
void __thiscall FUN_01b496d0(int param_1, undefined4 *param_2)
{
  // Adjust position by ±8 (for uint64)
  if (*(short *)(param_1 + 0x1010) != 0) {
    if (*(char *)(param_1 + 4) == '\0') {  // Write
      *piVar1 = *piVar1 + 8;
    } else {  // Read
      *piVar1 = *piVar1 + -8;  // Pre-decrement
    }
  }

  if (*(char *)(param_1 + 4) != '\0') {  // Read mode
    (**(code **)(**(int **)(param_1 + 8) + 0x18))();  // vtable[6]
  } else {  // Write mode
    (**(code **)(**(int **)(param_1 + 8) + 0x30))(*param_2, param_2[1]);  // vtable[12]
  }
}
```

---

### 14. FUN_01b6f490 - Actual 8-Byte Read

> Assembly: See DISASSEMBLY.md - FUN_01b6f490 - Actual 8-Byte Read

**WinDbg Address:** ACBSP+0x176f490 (0x0224f490)
**TTD Position:** B1F2B:1878

**Decompilation:**
```c
void __thiscall FUN_01b6f490(int param_1, undefined4 *param_2)
{
  undefined4 *buffer_ptr = *(undefined4 **)(param_1 + 0x18);

  // Read 8 bytes as two 4-byte values (little-endian)
  *param_2 = *buffer_ptr;           // Low dword
  param_2[1] = buffer_ptr[1];       // High dword

  // Optional byte-swap for endianness
  if ((*(byte *)(param_1 + 4) & 1) != 0) {
    // Swap bytes within each dword
  }

  // Advance stream position by 8
  *(int *)(param_1 + 0x18) = *(int *)(param_1 + 0x18) + 8;
}
```

**Key Observations:**
- Reads 8 bytes as two separate 4-byte reads (low then high)
- Same pattern as FUN_01b6f440 (4-byte read) but doubled
- Endianness swap optional based on stream flags
- Buffer position advanced by 8 after read

---

<a id="canonical-uint64-read-call-chain"></a>
### uint64 Read Complete Call Chain

```
FUN_01b09760 (uint64 property serializer)
  └─→ FUN_01b124e0 (uint64 serialization core)
        ├─→ FUN_01b07940 (validation)
        ├─→ FUN_01b0d140 (validation)
        ├─→ vtable[2]("Value") - start element
        ├─→ vtable[0x7c] = FUN_01b48be0 (thunk)
        │     └─→ FUN_01b496d0 (8-byte handler)
        │           └─→ inner_vtable[6] = FUN_01b6f490 (actual 8-byte read)
        └─→ vtable[4]("Value") - end element
```

**Note:** `vtable[N]` refers to the outer serializer mode vtable at PTR_FUN_02555c60.
`inner_vtable[N]` refers to the stream I/O vtable at PTR_FUN_02556168.

---

### 15. FUN_01b0d0c0 - Finalization

**WinDbg Address:** ACBSP+0x170d0c0 (0x021ed0c0)
**TTD Position:** B1F2B:1B59

**Traced Flow (READ mode):**
1. Check `[esi+58h]` - mode value (not 1, 2, or 3)
2. Check `[esi+20h]` - must be non-zero to proceed
3. Call FUN_01b0d000 (pre-finalization)
4. **vtable[5]("Properties")** - CloseSection at B1F2B:1B84
5. **vtable[3]("Dynamic Properties")** - OpenSection at B1F2B:1BA5 (reserves 4 bytes)
6. Check `[esi+28h]` - dynamic properties pointer (0xf74c0a58)
7. Call FUN_01b091a0 - Dynamic properties serialization at B1F2B:1BD5
8. **vtable[5]("Dynamic Properties")** - CloseSection at B1F2B:1CB2 → **WRITES TRAILING 4 ZEROS!**
9. **vtable[5]("Object")** - CloseSection (implicit in step to B1F2B:1CEB)

**Key VTable Calls:**
- vtable[3] (offset 0x0c) = FUN_01b48890 (OpenSection)
- vtable[5] (offset 0x14) = FUN_01b48920 (CloseSection)

**Decompilation:**
```c
void __fastcall FUN_01b0d0c0(int param_1)
{
  if ([param_1+0x58] is 1, 2, or 3) {
    // Alternative path via FUN_01b70d50
  }
  else if (*(int *)(param_1 + 0x20) != 0) {
    FUN_01b0d000();
    vtable[5]("Properties");           // CloseSection
    vtable[3]("Dynamic Properties");   // OpenSection - reserves 4 bytes
    if (*(int *)(param_1 + 0x28) != 0) {
      FUN_01b091a0(*(int *)(param_1 + 0x28));  // Serialize dynamic props
    }
    vtable[5]("Dynamic Properties");   // CloseSection - writes size (0)
    vtable[5]("Object");               // CloseSection
  }
}
```

**Trailing 4 Zeros Confirmed:**
The "Dynamic Properties" section has:
- OpenSection reserves 4 bytes for size field
- No dynamic properties written in this file
- CloseSection patches size to 0x00000000

---

<a id="write-path"></a>
## WRITE Path Functions

### Entry Point - FUN_01710580 WRITE Mode

**TTD Position:** E68A12:1BD8
**Mode byte:** `[0x24d476e4] = 0x00` (WRITE mode confirmed)

**WRITE Path Flow:**
```
01df0591  cmp byte ptr [eax+4], 0    ; Mode check
01df0595  jne 01df05c8               ; NOT taken (mode=0, WRITE)
01df05a1  call FUN_021dc2c0          ; Setup #1
01df05ae  call FUN_021db8a0          ; Setup #2
01df05b5  push 0C9876D66h            ; Type hash pushed!
01df05c3  call FUN_021e9e20          ; Header writer wrapper
```

---

### FUN_01b09e20 - Header Writer Wrapper

**WinDbg Address:** 0x021e9e20
**TTD Position:** E68A19:CC

**Parameters on stack:**
- `[esp+4]` = 0x02c1ddec (metadata pointer)
- `[esp+c]` = 0xC9876D66 (type hash)
- `[esp+18]` = 0xf74c0898 (object pointer)

This wrapper calls **FUN_01b08ce0** at address `021e9ed5`.

---

### FUN_01b08ce0 - Actual Header Writer

**WinDbg Address:** 0x021e8ce0 (Ghidra: 0x01b08ce0)
**TTD Position:** E68A19:178 (entry)

**Decompilation shows key operations:**
```c
// Start header section
vtable[2]("ObjectInfo");

// Write a byte with "NbClassVersionsInfo" label - version >= 13 path
// NOTE: Despite the string name, this writes to offset 0 (padding bytes),
// NOT to offset 0x26. The actual 0x0b at offset 0x26 is the base class
// property flags byte, written by FUN_01b076f0 during SaveGameDataObject::Serialize.
if (serializer_version >= 0xd) {
    local_5 = *(byte*)(param_7 + 6);  // Gets value from object (was 0x00 in trace)
    FUN_01b0d500("NbClassVersionsInfo", &local_5);  // Writes to offset 0
}

// Write object metadata
vtable[2]("ObjectName"); vtable[0x54](...); vtable[4]("ObjectName");
vtable[2]("ObjectID"); vtable[0x9c](...); vtable[4]("ObjectID");

// Write instancing mode
FUN_01b0d500("InstancingMode", ...);

// Write type info block
vtable[2](DAT); vtable[0x50](param_2, param_4); vtable[4](DAT);

// End header, start object/properties sections
vtable[4]("ObjectInfo");
vtable[3]("Object");      // OpenSection
vtable[3]("Properties");  // OpenSection
```

---

### FUN_01b0d500 - Single Byte Writer (WRITE Mode Traced)

> Assembly: See DISASSEMBLY.md - FUN_01b0d500 - Single Byte Writer (WRITE Mode Traced)

**WinDbg Address:** 0x021ed500 (Ghidra: 0x01b0d500)
**TTD Position:** E68A19:1A2

**Key Finding:** In WRITE mode, StartElement and EndElement are NO-OPs (just `RET 4`).
The actual work happens via vtable[0x98] → FUN_01b48b70 → FUN_01b49430 → inner_vtable[0x0f].

---

### WRITE Mode VTable Functions - NO-OPs Confirmed

| Function | WinDbg | Ghidra | WRITE Mode Behavior |
|----------|--------|--------|---------------------|
| vtable[2] StartElement | 0x02228770 | 0x01b48770 | `RET 4` (NO-OP) |
| vtable[4] EndElement | 0x022287a0 | 0x01b487a0 | `RET 4` (NO-OP) |

In WRITE mode, element markers are not needed - we just write bytes directly to the buffer.

---

### FUN_01b48b70 - WriteByte Dispatcher (vtable[0x98])

**WinDbg Address:** 0x02228b70 (Ghidra: 0x01b48b70)
**TTD Position:** E68A19:1B3

Thunk that jumps to FUN_01b49430:
```c
void FUN_01b49430(int param_1, undefined1 *param_2) {
    // Counter tracking
    if (*(short *)(param_1 + 0x1010) != 0) {
        if (*(char *)(param_1 + 4) == '\0') {  // WRITE mode
            *counter = *counter + 1;
        } else {  // READ mode
            *counter = *counter - 1;
        }
    }

    if (*(char *)(param_1 + 4) != '\0') {  // READ mode
        inner_vtable[9]();  // offset 0x24 - ReadByte
    } else {  // WRITE mode
        inner_vtable[0x0f](*param_2);  // offset 0x3c - WriteByte
    }
}
```

---

### FUN_01b6f370 - Core Byte Write to Buffer

**WinDbg Address:** 0x0224f370 (Ghidra: 0x01b6f370)
**TTD Position:** E68A19:1C4

```c
void FUN_01b6f370(int param_1, undefined1 param_2) {
    // Buffer expansion check
    if (*(int *)(param_1 + 0x30) != 0) {
        if (buffer_needs_expansion) {
            FUN_01b6f1b0(...);  // Expand buffer
        }
    }

    // CORE WRITE:
    **(undefined1 **)(param_1 + 0x18) = param_2;  // Write byte at buffer position
    *(int *)(param_1 + 0x18) += 1;                // Increment buffer pointer
}
```

---

### FUN_01b49610 - 4-Byte Write Dispatcher

**WinDbg Address:** 0x02229610 (Ghidra: 0x01b49610)
**TTD Position:** E68A19:25E

```c
void FUN_01b49610(int param_1, undefined4 *param_2) {
    // Counter tracking (adds 4 bytes)
    if (*(short *)(param_1 + 0x1010) != 0) {
        if (*(char *)(param_1 + 4) == '\0') {  // WRITE mode
            *counter = *counter + 4;
        } else {  // READ mode
            *counter = *counter - 4;
        }
    }

    if (*(char *)(param_1 + 4) != '\0') {  // READ mode
        inner_vtable[7]();  // offset 0x1c - Read 4 bytes
    } else {  // WRITE mode
        inner_vtable[0x0d](*param_2);  // offset 0x34 - Write 4 bytes
    }
}
```

---

### FUN_01b6fea0 - Core 4-Byte Write to Buffer

**WinDbg Address:** 0x0224fea0 (Ghidra: 0x01b6fea0)
**TTD Position:** E68A19:270

```c
void FUN_01b6fea0(int param_1, undefined4 *param_2) {
    // Buffer expansion check
    if (*(int *)(param_1 + 0x30) != 0) {
        if (buffer_needs_expansion) {
            FUN_01b6f1b0(...);  // Expand buffer
        }
    }

    // ENDIANNESS SWAP (if flag & 1)
    if ((*(byte *)(param_1 + 4) & 1) != 0) {
        // Swap bytes 0↔3, 1↔2 (big↔little endian)
    }

    // CORE WRITE:
    **(undefined4 **)(param_1 + 0x18) = *param_2;  // Write 4 bytes at buffer position
    *(int *)(param_1 + 0x18) += 4;                 // Increment buffer pointer
}
```

---

### FUN_01b48e90 - String Serializer

**WinDbg Address:** 0x02228e90 (Ghidra: 0x01b48e90)
**TTD Position:** E68A19:1FA (called for ObjectName, but string was empty)
**Status:** Ghidra static analysis (N-byte paths not exercised in current trace)

**Serializer Layout:**
```
param_1 + 0x04   = mode byte (0x00 = WRITE, 0x01 = READ)
param_1 + 0x08   = stream pointer
param_1 + 0x1010 = counter (section nesting depth)
param_1 + counter*8 + 0x08 = accumulated size for current section
```

**WRITE Path (mode == 0):**
```c
int FUN_01b48e90(int param_1, int *param_2) {
    int local_8 = 0;

    // 1. Calculate string length (strlen)
    if (mode == 0 && *param_2 != NULL) {
        local_8 = strlen(*param_2);
    }

    // 2. Write 4-byte length prefix
    FUN_01b49610(&local_8);  // Uses inner_vtable[0x34] for 4-byte write

    // 3. Update counter accumulator (if inside a section)
    if (counter != 0) {
        [param_1 + counter*8 + 0x08] += local_8;  // Add string length to section size
    }

    // 4. Write string data (N bytes)
    if (*param_2 != NULL) {
        inner_vtable[0x40](*param_2, local_8);  // N-byte write at offset 0x40
    }
    return 0;
}
```

**READ Path (mode == 1):**
```c
int FUN_01b48e90(int param_1, int *param_2) {
    int local_8 = 0;

    // 1. Read 4-byte length prefix
    FUN_01b49610(&local_8);  // Uses inner_vtable[0x1c] for 4-byte read

    // 2. Update counter accumulator (if inside a section)
    if (counter != 0) {
        [param_1 + counter*8 + 0x08] -= local_8;  // Subtract for remaining size tracking
    }

    // 3. Handle empty string case
    if (local_8 == 0) {
        *param_2 = NULL;
        return iVar6;
    }

    // 4. Allocate buffer (length + 1 for null terminator)
    *param_2 = malloc(local_8 + 1);

    // 5. Read string data (N bytes)
    inner_vtable[0x28](*param_2, local_8);  // N-byte read at offset 0x28

    // 6. Null-terminate the string
    (*param_2)[local_8] = '\0';

    return iVar6;
}
```

**Inner VTable Usage (confirmed via Ghidra):**
| Offset | Index | Function | Purpose |
|--------|-------|----------|---------|
| 0x28 | [10] | FUN_01b6f030 | N-byte read (string characters) |
| 0x40 | [16] | FUN_01b6f3b0 | N-byte write (string characters) |

**Note:** The N-byte read/write functions at inner_vtable[0x28] and [0x40] are not exercised
in the current trace because AssassinSingleProfileData has no string properties. The
ObjectName field is empty (length=0) so the N-byte path is skipped.

---

### FUN_01b08ce0 - Type Info Block Writer (Continuation)

**TTD Position:** E68A19:2F0 (buffer at offset 0x0a)
**Buffer Address:** 0x04660000 + 0x0a = 0x0466000a

After writing the structured header fields (0x00-0x09), the buffer position is at offset 0x0a.
The next writes are handled by FUN_01b08ce0 type info block:

**Header Value Sources (TRACED - values are NOT hardcoded!):**

| Field | Source | Traced Value | Notes |
|-------|--------|--------------|-------|
| NbClassVersionsInfo | [param_7+6] = [07a8f6a2] | 0x00 | Could be non-zero for versioned classes |
| ObjectName | [param_3] = [07a8f6c8] | NULL (0x00000000) | NULL → writes length=0, no string data |
| ObjectID | [param_5] = [07a8f6a4] | 0x00000000 | Could be non-zero for named objects |
| InstancingMode | [param_8] high byte | 0x00 | Could be 1 for instanced objects |

**Write Sequence (offsets 0x0a onwards) - TRACED:**
```
0x0a-0x0d: Type hash (0xc9876d66) - FUN_01b48fb0 → FUN_01b49610
0x0e-0x11: field_0x0e (0x00000090) - BACKPATCHED by FUN_01b6fea0 at E68A1F:D0
0x12-0x15: field_0x12 (0x00000088) - Written during initial serialization
0x16-0x19: field_0x16 (0x00000011) - Written during initial serialization
```

<a id="important-correction"></a>
**IMPORTANT CORRECTION:** Header fields 0x0e-0x19 are THREE uint32s, NOT uint16+uint32+uint32+2bytes!
- Old (wrong): 0x0e-0x0f=uint16, 0x10-0x13=uint32, 0x14-0x17=uint32, 0x18-0x19=2bytes
- New (correct): 0x0e-0x11=uint32, 0x12-0x15=uint32, 0x16-0x19=uint32

**Backpatching observed:**
- Position E68A1F:D0: `mov dword ptr [0466000e], 0x00000090`
- This happens AFTER all properties are serialized
- Fields 0x12-0x15 and 0x16-0x19 are written earlier during serialization

---

### FUN_01b09650 - Bool Property Serializer (WRITE Mode Entry)

**WinDbg Address:** 0x021e9650 (Ghidra: 0x01b09650)
**TTD Position:** E68A1B:BD

Now in property serialization phase. Calls FUN_01b11fb0 which:
1. Calls FUN_01b0d140 to write property header
2. Calls vtable[0x58] to write bool value
3. Calls vtable[5] CloseSection("Property")

---

<a id="property-serializers"></a>
## Property Serializers

### FUN_01b48fb0 - TypeInfo Serializer (vtable[0x50]) - COMPLETE TRACE

> Assembly: See DISASSEMBLY.md - FUN_01b48fb0 - TypeInfo Serializer (vtable[0x50])

**WinDbg Address:** 0x02228fb0 (Ghidra: 0x01b48fb0)
**TTD Position:** E68A19:2FA (entry)

> Trace: See TRACES.md - FUN_01b48fb0 TypeInfo Serializer Trace (parameters, type hash 0xc9876d66)

**Decompilation:**
```c
void __thiscall FUN_01b48fb0(int *param_1, undefined4 param_2, undefined4 param_3)
{
    // Flag at offset 0x1012 controls whether type NAME is serialized
    if (*(char *)(param_1 + 0x1012) != '\0') {
        if ((char)param_1[1] == '\0') {  // WRITE mode
            vtable[0x54](&param_2);       // Serialize type name string
            FUN_01b49610(param_3);        // Write type hash
            return;
        }
        // READ mode with string
        local_8 = 0;
        vtable[0x84](&local_8);
        inner_vtable[0x44](local_8);
    }
    // Simple path: just write type hash
    FUN_01b49610(param_3);
}
```

**Key Finding:**
- Flag at `[serializer+0x1012]` = **0x00** means NO type name string is written
- Only the 4-byte type hash (0xc9876d66) is written at offset 0x0a
- This explains why the file has just the hash, not a string like "AssassinSingleProfileData"

---

### FUN_01b49610 - 4-Byte Write Dispatcher (DETAILED TRACE)

> Assembly: See DISASSEMBLY.md - FUN_01b49610 - 4-Byte Write Dispatcher

**WinDbg Address:** 0x02229610 (Ghidra: 0x01b49610)
**TTD Position:** E68A19:305 (called from FUN_01b48fb0)

> Trace: See TRACES.md - FUN_01b49610 4-Byte Write Dispatcher Trace (parameters, serializer context structure)

---

<a id="fun_01b0d140---property-header-writer-complete-trace"></a>
### FUN_01b0d140 - Property Header Writer (COMPLETE TRACE)

> Assembly: See DISASSEMBLY.md - FUN_01b0d140 - Property Header Writer

**WinDbg Address:** 0x021ed140 (Ghidra: 0x01b0d140)
**TTD Position:** E68A1B:25B (first property write)

**Decompilation:**
```c
undefined4 __thiscall FUN_01b0d140(int param_1, uint *param_2)
{
  // Early exit checks for mode 1, 2, 3 or flag 0x4e bit 0
  iVar3 = *(int *)(param_1 + 0x58);
  if ((iVar3 == 1) || (iVar3 == 2) || (iVar3 == 3) || ((*(byte *)(param_1 + 0x4e) & 1) != 0)) {
    return 1;
  }

  // Check if we should skip (vtable[0x1c] returns non-zero)
  cVar2 = (**(code **)(**(int **)(param_1 + 4) + 0x1c))();
  if (cVar2 != '\0') return 0;

  // 1. OpenSection("Property") - reserves 4 bytes for size
  (**(code **)(**(int **)(param_1 + 4) + 0xc))("Property");

  // 2. Write property hash (4 bytes)
  local_8 = param_2[1];  // Get hash from metadata at offset +4
  FUN_01b0e680(&DAT_02554cbc, 0, &local_8);

  // 3. Write type_info (8 bytes)
  local_10 = puVar1[2];  // type_info low (offset +8)
  local_c = puVar1[3];   // type_info high (offset +C)
  FUN_01b0e980(&local_10);

  // 4. Write flags byte (0x0b)
  if (iVar3 == 0) {
    // Default path: flags = 0x0b
    param_2 = ... | 0xb000000;
    FUN_01b076f0((int)&param_2 + 3);  // Write single byte 0x0b
  } else {
    // Alternative path with version info
    FUN_01b0e7e0(...);
    FUN_01b076f0(...);
    FUN_01b0e7e0(...);
  }

  return 1;
  // Note: Caller writes value and calls CloseSection
}
```

**Property Metadata Structure (param_2):**
```
+0x00: flags (bit 17 checked for alternative path)
+0x04: property hash (4 bytes) - e.g., 0x3b546966 for bool_field_0x20
+0x08: type_info low (4 bytes)
+0x0C: type_info high (4 bytes)
```

> Trace: See TRACES.md - Traced Property Example bool_field_0x20 (E68A1B:25B, buffer layout 0x2B-0x3C)

---

### 16. FUN_01b0e680 - Property Hash Writer

**WinDbg Address:** 0x021ee680 (Ghidra: 0x01b0e680)
**TTD Position:** E68A1B:264

**Decompilation:**
```c
void __thiscall FUN_01b0e680(int *param_1, char *param_2, undefined4 param_3, undefined4 *param_4)
{
  vtable[0x08](param_2);           // StartElement(tag_name) - NO-OP in WRITE
  vtable[0x50](param_3, param_4);  // Serialize 4-byte value (FUN_01b48fb0)
  vtable[0x10](param_2);           // EndElement(tag_name) - NO-OP in WRITE
}
```

> Trace: See TRACES.md - FUN_01b0e680 Property Hash Writer Trace (call chain E68A1B:26D-2BF)

**Purpose:** Wrapper that writes a 4-byte property hash with XML-style element markers (which are NO-OPs in binary WRITE mode).

---

### 17. FUN_01b0e980 - Type Info Writer

**WinDbg Address:** 0x021ee980 (Ghidra: 0x01b0e980)
**TTD Position:** E68A1B:2D0

**Decompilation:**
```c
void __thiscall FUN_01b0e980(int param_1, undefined4 *param_2)
{
  piVar1 = *(int **)(param_1 + 4);           // Get mode vtable

  if (*(int *)(param_1 + 0x24) < 9) {        // Version check
    // LEGACY PATH (version < 9):
    vtable[0x08]("Type");                    // StartElement
    vtable[0x4c](format, &local_c);          // Read via 8-byte handler
    vtable[0x10]("Type");                    // EndElement
    FUN_01b0e3d0(&local_14);                 // Convert legacy format
    *param_2 = result[0];
    param_2[1] = result[1];
    return;
  }

  // CURRENT PATH (version >= 9):
  local_c = *param_2;                        // Copy low dword
  local_8 = param_2[1];                      // Copy high dword
  vtable[0x08]("Type");                      // StartElement - NO-OP
  vtable[0x4c](format, &local_c);            // Write 8 bytes (FUN_01b49020)
  vtable[0x10]("Type");                      // EndElement - NO-OP
  *param_2 = local_c;                        // Copy back (for READ)
  param_2[1] = local_8;
}
```

> Trace: See TRACES.md - FUN_01b0e980 Type Info Writer Trace (call chain E68A1B:2E1-338, version check)

**Version Behavior:**
- **Version < 9:** Legacy format, uses FUN_01b0e3d0 for bit-field conversion
- **Version >= 9:** Direct 8-byte read/write (our file uses this)

**Serializer Version:** 0x10 (16) - stored at [context + 0x24]

---

### 18. FUN_01b49020 - 8-Byte Serializer with Optional Type Name

**WinDbg Address:** 0x02229020 (Ghidra: 0x01b49020)
**TTD Position:** E68A1B:2E9 (called from FUN_01b0e980)

**Decompilation:**
```c
void __thiscall FUN_01b49020(int param_1, char *param_2, undefined4 *param_3)
{
  if ([param_1 + 0x1012] != 0) {             // Type name string flag
    if ([param_1 + 0x4] == 0) {              // WRITE mode
      vtable[0x54](param_2);                 // Write type name string
      FUN_01b496d0(param_3);                 // Write 8-byte value
      return;
    }
    // READ mode with string
    vtable[0x84](&local);
    inner_vtable[0x44](local);
  }

  // Simple path (flag == 0):
  FUN_01b496d0(param_3);                     // Just write/read 8 bytes
}
```

**Key Flag:** [serializer + 0x1012] = 0x00 in our trace, so takes simple path directly to FUN_01b496d0.

**Called Function:** FUN_01b496d0 (8-byte read/write dispatcher) - already documented.

---

### 19. FUN_01b48e80 - Bool Serializer (vtable[0x58]) - WRITE Mode

> Assembly: See DISASSEMBLY.md - FUN_01b48e80 - Bool Serializer (vtable[0x58])

**WinDbg Address:** 0x02228e80 (Ghidra: 0x01b48e80)
**TTD Position:** E68A1B:411

**Decompilation:**
```c
void FUN_01b48e80(void)
{
  FUN_01b497f0();  // Thin wrapper, just jumps to dispatcher
  return;
}
```

---

### 20. FUN_01b497f0 - 1-Byte Read/Write Dispatcher

**WinDbg Address:** 0x022297f0 (Ghidra: 0x01b497f0)
**TTD Position:** E68A1B:415

**Decompilation:**
```c
void __thiscall FUN_01b497f0(int param_1, undefined1 *param_2)
{
  // Counter tracking (±1 byte)
  if (*(short *)(param_1 + 0x1010) != 0) {
    if (*(char *)(param_1 + 4) == '\0') {  // WRITE mode
      counter[index]++;                     // Increment byte count
    } else {                                // READ mode
      counter[index]--;                     // Decrement byte count
    }
  }

  // Get stream object
  stream = *(int **)(param_1 + 8);

  if (*(char *)(param_1 + 4) != '\0') {    // READ mode
    inner_vtable[0x24]();                   // 1-byte read (index 9)
  } else {                                  // WRITE mode
    inner_vtable[0x3c](*param_2);           // 1-byte write (index 15)
  }
}
```

> Trace: See TRACES.md - Bool Value Write Trace (FUN_01b497f0 1-byte dispatcher, call chain E68A1B:426)

**READ vs WRITE Comparison:**
| Mode | Inner VTable Offset | Function | Action |
|------|---------------------|----------|--------|
| READ | 0x24 (index 9) | FUN_01b6f3b0 | `*param_2 = *buffer++` |
| WRITE | 0x3c (index 15) | FUN_01b6f370 | `*buffer++ = *param_2` |

---

### 21. FUN_01b48be0 - uint64 Serializer (vtable[0x7c]) - WRITE Mode

> Assembly: See DISASSEMBLY.md - FUN_01b48be0 - uint64 Serializer (vtable[0x7c]) - WRITE Mode

**WinDbg Address:** 0x02228be0 (Ghidra: 0x01b48be0)
**TTD Position:** E68A1D:3EE

**Decompilation:**
```c
void FUN_01b48be0(void)
{
  FUN_01b496d0();  // Thin wrapper, just jumps to 8-byte dispatcher
  return;
}
```

---

### 22. FUN_01b496d0 - 8-Byte Read/Write Dispatcher (WRITE Mode Traced)

**WinDbg Address:** 0x022296d0 (Ghidra: 0x01b496d0)
**TTD Position:** E68A1D:3F2

**Decompilation:**
```c
void __thiscall FUN_01b496d0(int param_1, undefined4 *param_2)
{
  // Counter tracking (±8 bytes)
  if (*(short *)(param_1 + 0x1010) != 0) {
    if (*(char *)(param_1 + 4) == '\0') {  // WRITE mode
      counter[index] += 8;
    } else {                                // READ mode
      counter[index] -= 8;
    }
  }

  // Get stream object
  stream = *(int **)(param_1 + 8);

  if (*(char *)(param_1 + 4) != '\0') {    // READ mode
    inner_vtable[0x18](param_2);            // 8-byte read
  } else {                                  // WRITE mode
    low = *param_2;
    high = param_2[1];
    inner_vtable[0x30](low, high);          // 8-byte write
  }
}
```

> Trace: See TRACES.md - uint64 Value Write Trace (FUN_01b496d0 8-byte dispatcher, call chain E68A1D:406)

**READ vs WRITE Comparison (8-byte):**
| Mode | Inner VTable Offset | Function | Parameters |
|------|---------------------|----------|------------|
| READ | 0x18 (index 6) | FUN_01b6f490 | output_ptr |
| WRITE | 0x30 (index 12) | FUN_01b6f4e0 | low_dword, high_dword |

---

### vtable[0x84] - uint32 Serializer (WRITE Path)

**TTD Position:** E68A19:C6B -> E68A19:CA2
**Value Written:** 0x00000000 (base class field value at offset 0x27)

> Trace: See TRACES.md - uint32 Write Trace Base Class Field (full call chain E68A19:C6B-CA2)

**Key Insight:** File offset 0x27 is the base class field uint32 value (within the 17-byte base class property block at 0x1a-0x2a).

**READ vs WRITE Comparison (4-byte):**
| Mode | Inner VTable Offset | Function | Parameters |
|------|---------------------|----------|------------|
| READ | 0x1c (index 7) | FUN_01b6f440 | output_ptr |
| WRITE | 0x34 (index 13) | FUN_01b6f4d0→FUN_01b6fea0 | value |

**Ghidra References:**
- FUN_01b48bc0: vtable[0x84] thin wrapper
- FUN_01b49610: 4-byte dispatcher (counter tracking + mode dispatch)
- FUN_01b6f4d0: inner_vtable[0x34] wrapper
- FUN_01b6fea0: Core 4-byte stream write

---

### FUN_01b0d0c0 - Finalization (Dynamic Properties)

**TTD Position:** E68A1D:CE1 -> E68A1D:F9D
**Purpose:** Writes Dynamic Properties section (trailing 4 zeros at offset 0x9e)

> Trace: See TRACES.md - Dynamic Properties Finalization Trace (full call chain E68A1D:CE1-F9D)

**Key Insight:** The trailing 4 zeros at offset 0x9e-0xa1 are the **Dynamic Properties section size** (zero because this save has no dynamic properties). They are written by CloseSection backpatching the size reserved by OpenSection.

**Ghidra References:**
- FUN_01b0d0c0: Finalization entry point
- FUN_01b48890: OpenSection (vtable[0x0c])
- FUN_01b48920: CloseSection (vtable[0x14])
- FUN_01b091a0: Dynamic properties processor

---

<a id="utility-functions"></a>
## Utility Functions

### Stream I/O Functions

See [STREAM_IO.md](STREAM_IO.md) for detailed documentation of all stream read/write functions including:
- N-byte read/write (FUN_01b6f030, FUN_01b6f3b0)
- Fixed-size readers (1/2/4/8 byte variants)
- Position management (seek, save, restore)
- Buffer management functions

**Core pattern:** All functions read/write at `[stream+0x18]` and advance position by N bytes.

### CloseSection (FUN_01b48920) - Size Patching

```c
void __fastcall FUN_01b48920(int *param_1)
{
  if ((char)param_1[1] != '\0') {  // READ mode
    (**(code **)(*param_1 + 0x18))();
    return;
  }
  // WRITE mode:
  uVar2 = *(ushort *)(param_1 + 0x404) - 1;  // Pop section stack
  iVar1 = param_1[... * 2 + 2];               // Get saved position
  *(ushort *)(param_1 + 0x404) = uVar2;       // Update stack pointer

  (**(code **)(*(int *)param_1[2] + 0x50))(...);  // Seek to saved position
  (**(code **)(*(int *)param_1[2] + 0x34))(iVar1); // WRITE SIZE via inner_vtable[0x34]
  (**(code **)(*(int *)param_1[2] + 0x54))(...);  // Seek back to current position
  (**(code **)(*(int *)param_1[2] + 0x58))();     // Finalize
  ...
}
```

The key call is `inner_vtable[0x34]` which is FUN_01b6fea0 (core 4-byte write).
