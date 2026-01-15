# Section 3 Serialization - WinDbg TTD Trace Results

## Overview

This document records all findings from WinDbg Time Travel Debugging (TTD) trace of the Assassin's Creed Brotherhood save file serialization for the OPTIONS file.

**TTD Trace File:** OPTIONS.WINDBGTRACE
**File Being Read:** game_uncompressed_3.bin (162 bytes, Section 3)
**Module Base:** ACBSP = 0x00ae0000
**Ghidra Base:** 0x00400000
**Address Conversion:** WinDbg = Ghidra + 0x6e0000

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

## Traced Functions (READ Path)

### 1. FUN_01710580 - AssassinSingleProfileData::Serialize

**WinDbg Address:** ACBSP+0x1310580 (0x01df0580)
**TTD Position:** B1F2B:920

**Registers on Entry:**
- ECX (param_1/this) = 0xf74c0a50 (AssassinSingleProfileData object)
- [esp+4] (param_2) = 0x03cff870 (serializer context)

**Serializer Context Structure:**
```
03cff870: 00000000 0a3a06b0 03053330 c9876d66
          +0x00    +0x04    +0x08    +0x0C (type hash)
03cff880: 00000000 00000000 00000000 f74c0a50
          +0x10    +0x14    +0x18    +0x1C (object ptr)
03cff890: 00000001 00000010 f74c0a58 ...
          +0x20    +0x24    +0x28
```

**Key Offsets in Serializer Context:**
- +0x04: Mode structure pointer (0x0a3a06b0)
- +0x08: Buffer/stream pointer (0x03053330)
- +0x0C: Type hash (0xc9876d66)
- +0x1C: Object pointer
- +0x20: Saved/restored during base class call
- +0x58: Mode value (0 = default)

**Mode Check:**
```
cmp byte ptr [eax+4], 0    ; [0x0a3a06b4] = 0x01
jne (skip header write)    ; 0x01 != 0, so READ mode
```
- Mode 0x00 = WRITE mode (writes headers)
- Mode 0x01 = READ mode (skips header write)

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

**WinDbg Address:** ACBSP+0x170a1f0 (0x021ea1f0)

This is a thin wrapper that calls FUN_01b12fa0:
```asm
mov eax, [ebp+8]     ; field pointer
mov edx, [ebp+0Ch]   ; property metadata
push eax
push edx
call FUN_01b12fa0
```

---

### 4. FUN_01b12fa0 - Property Serialization Core

**WinDbg Address:** ACBSP+0x1712fa0 (0x021f2fa0)

**Parameters:**
- ECX = serializer context
- [esp+4] = property metadata (0x02eccf90)
- [esp+8] = field pointer (0xf74c0a54)

**Property Metadata at 0x02eccf90:**
```
02eccf90: 02000001 bf4c2013 00000000 00070000
          flags    hash
02eccfa0: 00100007 ...
```
- Hash 0xbf4c2013 = SaveGameDataObject base class field

**Traced Flow:**
1. FUN_01b07940 - Validation (checks mode, property flags)
2. FUN_01b0d140 - More validation
3. vtable[2]("Value") - Start XML element
4. **vtable[0x84](field_ptr)** - Actual serialize!
5. vtable[4]("Value") - End XML element

---

### 5. FUN_01b49610 - Stream Read/Write (4 bytes - uint32)

> **Related:** See [FUN_01b49610 - 4-Byte Write Dispatcher (DETAILED TRACE)](#fun_01b49610---4-byte-write-dispatcher-detailed-trace) for the complete WRITE path analysis with disassembly.

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

> **Related:** See [FUN_01b6fea0 - Core 4-Byte Write to Buffer](#fun_01b6fea0---core-4-byte-write-to-buffer) for the WRITE path equivalent.

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

**Traced Execution:**
- Stream object (ECX) = 0xf6c302d8
- Buffer pointer at [ECX+0x18] = 0x0a3a0627
- Data at buffer: 0x00000000
- Field pointer = 0xf74c0a54
- Result: Field set to 0x00000000

**Buffer Position = 0x0a3a0627:**
This is offset 0x27 from header start (0x0a3a0600), which is:
- Offset 0x26: base_class_flags = 0x0b (property flags byte)
- Offset 0x27-0x2a: 00 00 00 00 (base class field value)

---

### 7. FUN_01b09650 - Bool Property Serializer

> **Related:** See [FUN_01b09650 - Bool Property Serializer (WRITE Mode Entry)](#fun_01b09650---bool-property-serializer-write-mode-entry) for the WRITE path analysis.

**WinDbg Address:** ACBSP+0x1709650 (0x021e9650)
**TTD Position:** B1F2B:BE9

**Parameters:**
- ECX = serializer context (0x03cff870)
- [esp+4] = field pointer (0xf74c0a70 for bool_field_0x20)
- [esp+8] = property metadata (0x03053250)

**Property Metadata at 0x03053250:**
```
03053250: 02000001 3b546966 00000000 00000000
          flags    hash=0x3b546966 (bool_field_0x20)
```

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

> **Related:** See [FUN_01b497f0 - 1-Byte Read/Write Dispatcher](#20-fun_01b497f0---1-byte-readwrite-dispatcher) for the complete WRITE path trace with call chain.

**WinDbg Address:** ACBSP+0x1749610 (0x02229610)

```c
// Adjust position by ±1 (bool is 1 byte)
if (mode == read) {
  vtable[0x24]();  // Read 1 byte
} else {
  vtable[0x3c](*param_2);  // Write 1 byte
}
```

**Traced Result:**
- Buffer position: 0x0a3a063c
- Data at buffer: 0x01
- Field before: 0x00
- Field after: 0x01 (true) ✓

---

### 10. FUN_01b09760 - uint64 Property Serializer

**WinDbg Address:** ACBSP+0x1709760 (0x021e9760)
**TTD Position:** B1F2B:1643

**Parameters:**
- [esp+4] = field pointer (0xf74c0a68 for uint64_field_0x18)
- [esp+8] = property metadata (0x030532d0)

**Property Metadata at 0x030532d0:**
```
030532d0: 02000001 496f8780 00000000 00090000
          flags    hash=0x496f8780 (uint64_field_0x18)
```

Uses **vtable[0x7c]** for uint64 serialization.

---

### 11. FUN_01b124e0 - uint64 Serialization Core

**WinDbg Address:** ACBSP+0x17124e0 (0x021f24e0)
**TTD Position:** B1F2B:1644

**Disassembly Flow:**
```asm
021f24ef  call FUN_01b07940      ; Validation #1
021f24ff  call FUN_01b0d140      ; Validation #2
021f2527  mov esi, [edi+4]       ; Get mode structure
021f252a  mov eax, [esi]         ; Get vtable
021f252c  mov edx, [eax+8]       ; vtable[2] - StartElement
021f252f  push "Value"
021f2536  call edx               ; vtable[2]("Value")
021f253a  mov edx, [eax+7Ch]     ; vtable[0x7c] - uint64 serialize
021f253d  push ebx               ; field pointer
021f2540  call edx               ; vtable[0x7c](field_ptr) ← ACTUAL READ
021f2544  mov edx, [eax+10h]     ; vtable[4] - EndElement
021f2547  push "Value"
021f254e  call edx               ; vtable[4]("Value")
```

Similar structure to FUN_01b11fb0 (bool) but uses **vtable[0x7c]** instead of vtable[0x58].

---

### 12. FUN_01b48be0 - uint64 VTable Thunk

**WinDbg Address:** ACBSP+0x1748be0 (0x02228be0)
**TTD Position:** B1F2B:1863

Thin wrapper that immediately jumps to FUN_01b496d0:
```asm
02228be0  push ebp
02228be1  mov ebp, esp
02228be3  pop ebp
02228be4  jmp FUN_01b496d0 (022296d0)
```

---

### 13. FUN_01b496d0 - Stream Read/Write (8 bytes - uint64)

**WinDbg Address:** ACBSP+0x17496d0 (0x022296d0)
**TTD Position:** B1F2B:1867

**Traced Execution:**
```
B1F2B:186A  cmp [ecx+1010h], 0     ; [0x0a3a16c0] = 0x0003 (not zero)
B1F2B:186C  cmp byte [ecx+4], 0    ; [0x0a3a06b4] = 0x01 (READ mode)
B1F2B:186F  add [ecx+eax*8+8], -8  ; Position pre-decremented by 8
B1F2B:1873  mov ecx, [ecx+8]       ; Get stream object = 0xf6c302d8
B1F2B:1876  mov eax, [eax+18h]     ; vtable[6] = 0x0224f490 (FUN_01b6f490)
B1F2B:1878  jmp eax                ; Jump to actual 8-byte read
```

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

> **Related:** See [FUN_01b496d0 - 8-Byte Read/Write Dispatcher (WRITE Mode Traced)](#22-fun_01b496d0---8-byte-readwrite-dispatcher-write-mode-traced) for the WRITE path equivalent via inner_vtable[0x30].

**WinDbg Address:** ACBSP+0x176f490 (0x0224f490)
**TTD Position:** B1F2B:1878

**Traced Execution:**
```
B1F2B:187D  mov eax, [esi+18h]     ; Buffer pointer = 0x0a3a0684
B1F2B:187E  mov edx, [eax]         ; Read LOW dword from buffer
B1F2B:187F  mov ecx, [ebp+8]       ; Field pointer = 0xf74c0a68
B1F2B:1880  mov [ecx], edx         ; Write low dword to field
B1F2B:1881  mov eax, [eax+4]       ; Read HIGH dword from buffer
B1F2B:1882  mov [ecx+4], eax       ; Write high dword to field
B1F2B:1883  test [esi+4], 1        ; Endianness check = 0 (no swap needed)
B1F2B:1885  add [esi+18h], 8       ; Advance buffer position by 8
```

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

### uint64 Read Complete Call Chain

```
FUN_01b09760 (uint64 property serializer)
  └─→ FUN_01b124e0 (uint64 serialization core)
        ├─→ FUN_01b07940 (validation)
        ├─→ FUN_01b0d140 (validation)
        ├─→ vtable[2]("Value") - start element
        ├─→ vtable[0x7c] = FUN_01b48be0 (thunk)
        │     └─→ FUN_01b496d0 (8-byte handler)
        │           └─→ vtable[6] = FUN_01b6f490 (actual 8-byte read)
        └─→ vtable[4]("Value") - end element
```

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

> **See Also:** [Important Correction](#important-correction) below for the correct interpretation of fields 0x0e-0x19 as three uint32 section sizes (not mixed uint16/uint32 fields).

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
--- Base class field property (shortened format, no size field) ---
0x1a    13 20 4c bf                    base_class_hash        0xbf4c2013
0x1e    00 00 00 00 00 00 07 00        base_class_type_info   (8 bytes)
0x26    0b                             base_class_flags       0x0b (property flags byte!)
0x27    00 00 00 00                    base_class_value       0x00000000
--- End base class field property (17 bytes total) ---

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

**CloseSection (FUN_01b48920) at 0x02228920**

Traced at TTD position E68A19:CBB for CloseSection("Property"):

```
CloseSection("Property") - backpatches base class section size at 0x16

Entry: counter = 3, section name = "Property" (0x02c34c40)

Inside FUN_01b48920:
CBF: movzx eax, [esi+1010h]     ; load counter = 3
CC0: movzx ecx, ax              ; ecx = 3 (for size lookup)
CC1: dec eax                    ; eax = 2 (new counter value)
CC3: mov edi, [esi+ecx*8+8]     ; edi = [esi+0x20] = 0x11 (SIZE = 17 bytes!)
CC5: mov [esi+1010h], ax        ; update counter: 3 → 2
CC7: mov edx, [edx+50h]         ; inner_vtable[0x50] = 0x0224f090 (seek function)
CC9: mov eax, [esi+eax*8+14h]   ; eax = [esi+0x24] = 0xf08d02f8 (saved POSITION token)
CCA: push eax                   ; push position token
CCB: call inner_vtable[0x50]    ; SEEK back to saved position → 0x04660016

After seek, stream position is 0x04660016 (offset 0x16):
CD8: mov ecx, [esi+8]           ; load stream object
CDA: mov edx, [eax+34h]         ; inner_vtable[0x34] = 0x0224f4d0 (4-byte write)
CDB: push edi                   ; push size value (0x11 = 17)
CDC: call inner_vtable[0x34]    ; write 4 bytes

Core write at E68A19:CF6:
CF4: mov ecx, [esi+18h]         ; ecx = 0x04660016 (write position)
CF5: mov edx, [eax]             ; edx = 0x00000011 (size value)
CF6: mov [ecx], edx             ; WRITE: [0x04660016] = 0x00000011
CF7: add [esi+18h], 4           ; advance position (but will be restored)
```

**Serializer Counter Arrays:**
- `[serializer + n*8 + 0x08]`: Accumulated size for nesting level n
- `[serializer + n*8 + 0x14]`: Saved position token for nesting level n
- `[serializer + 0x1010]`: Current nesting depth (counter)

**Position Token:** The saved position (e.g., 0xf08d02f8) is an abstract token, not a direct buffer address. The seek function (inner_vtable[0x50]) translates it to the actual buffer position (0x04660016 = offset 0x16).

**All Backpatches Verified:**

| Offset | Size (hex) | Size (dec) | Section | TTD Position | Write Instruction |
|--------|------------|------------|---------|--------------|-------------------|
| 0x0e | 0x90 | 144 | "Object" | E68A1F:D0 | mov [0x0466000e], 0x90 |
| 0x12 | 0x88 | 136 | "Properties" | E68A1D:B86 | mov [0x04660012], 0x88 |
| 0x16 | 0x11 | 17 | "Property" | E68A19:CF6 | mov [0x04660016], 0x11 |

**Core Write Function:** FUN_01b6fea0 (0x0224fea0 WinDbg / 0x01b6fea0 Ghidra)
```c
// Simplified logic:
if (buffer_capacity_check) { ... }
if (endian_swap_flag) { byte_swap_4_bytes(); }
**(stream + 0x18) = *value;      // Write 4 bytes at current position
*(stream + 0x18) += 4;           // Advance position
```

**IMPORTANT**: The 0x0b at offset 0x26 is NOT NbClassVersionsInfo!
It is the **property flags byte** for the base class field, written by FUN_01b076f0.

Confirmed via memory breakpoint at READ B1F2B:B38 and WRITE E68A19:C3E:
- The 0x0b is read/written as part of SaveGameDataObject::Serialize base class handling
- Call chain: FUN_01b0a1f0 → FUN_01b12fa0 → FUN_01b076f0 → FUN_01b6f150/FUN_01b6f370

---

## VTable Reference (Complete)

> **See Also:** For detailed trace analysis of specific vtable entries, see:
> - [FUN_01b48fb0 - TypeInfo Serializer (vtable[0x50])](#fun_01b48fb0---typeinfo-serializer-vtable0x50---complete-trace) for type hash serialization
> - [FUN_01b48e80 - Bool Serializer (vtable[0x58])](#19-fun_01b48e80---bool-serializer-vtable0x58---write-mode) for boolean value handling
> - [FUN_01b48be0 - uint64 Serializer (vtable[0x7c])](#21-fun_01b48be0---uint64-serializer-vtable0x7c---write-mode) for 64-bit integer handling
> - [FUN_01b48bc0 - uint32 Serializer (vtable[0x84])](#vtable0x84---uint32-serializer-write-path) for 32-bit integer handling

### Serializer Mode VTable at PTR_FUN_02555c60 (Ghidra) / 0x02c35c60 (WinDbg)

Accessed via: `mov eax, [edi+4]; mov eax, [eax]; call [eax+offset]`

| Offset | Ghidra Addr | Function | Purpose | Status |
|--------|-------------|----------|---------|--------|
| 0x00 | 02555c60 | FUN_01b49b10 | Destructor | Ghidra |
| 0x04 | 02555c64 | FUN_01b48830 | Get buffer bounds → inner[0x10] | Ghidra |
| 0x08 | 02555c68 | LAB_01b48770 | StartElement (NO-OP WRITE) | TTD ✓ |
| 0x0c | 02555c6c | FUN_01b48890 | OpenSection | TTD ✓ |
| 0x10 | 02555c70 | LAB_01b487a0 | EndElement (NO-OP WRITE) | TTD ✓ |
| 0x14 | 02555c74 | FUN_01b48920 | CloseSection | TTD ✓ |
| 0x18 | 02555c78 | FUN_01b489b0 | Pop section (counter--, skip) | Ghidra |
| 0x1c | 02555c7c | LAB_01b48a10 | Check section counter ≤ 0 | Ghidra |
| 0x20 | 02555c80 | LAB_01b48780 | Get section counter | Ghidra |
| 0x24 | 02555c84 | FUN_01b487b0 | Push position → inner[0x4c] | Ghidra |
| 0x28 | 02555c88 | FUN_01b487e0 | Seek to saved position → inner[0x50] | Ghidra |
| 0x2c | 02555c8c | FUN_01b48800 | Calc remaining → inner[0x5c] | Ghidra |
| 0x30 | 02555c90 | FUN_01b48700 | Restore all + get bounds | Ghidra |
| 0x34 | 02555c94 | FUN_01b48760 | Reset stream → inner[0x08] | Ghidra |
| 0x38 | 02555c98 | LAB_01b48820 | Flush → inner[0x68] | Ghidra |
| 0x3c | 02555c9c | FUN_01b48b10 | Position stack read/write | Ghidra |
| 0x40 | 02555ca0 | FUN_01b48a30 | Array/block serializer (N-byte + swap) | Ghidra |
| 0x44 | 02555ca4 | FUN_01b49300 | wstring serializer → FUN_01b49b40 | Ghidra |
| 0x48 | 02555ca8 | FUN_01b492f0 | string serializer → FUN_01b49920 | Ghidra |
| 0x4c | 02555cac | FUN_01b49020 | 8-byte + optional type name → FUN_01b496d0 | Ghidra |
| 0x50 | 02555cb0 | FUN_01b48fb0 | TypeInfo serializer | TTD ✓ |
| 0x54 | 02555cb4 | FUN_01b48e90 | String serializer | Ghidra |
| 0x58 | 02555cb8 | FUN_01b48e80 | Bool serializer → FUN_01b49430 | TTD ✓ |
| 0x5c | 02555cbc | FUN_01b48e00 | vec4/float4 (16 bytes) → 4× inner[0x34] | Ghidra |
| 0x60 | 02555cc0 | FUN_01b48d60 | mat4x4 (64 bytes) → 16× inner[0x34] | Ghidra |
| 0x64 | 02555cc4 | FUN_01b49140 | mat3x3 (36 bytes) → 9× inner[0x34] | Ghidra |
| 0x68 | 02555cc8 | FUN_01b48cf0 | quat/vec4 (16 bytes) → 4× inner[0x34] | Ghidra |
| 0x6c | 02555ccc | FUN_01b48c80 | vec3 (12 bytes) → 3× inner[0x34] | Ghidra |
| 0x70 | 02555cd0 | FUN_01b48c10 | vec2 (8 bytes) → 2× inner[0x34] | Ghidra |
| 0x74 | 02555cd4 | FUN_01b48c00 | float32 (4 bytes) → FUN_01b49790 | Ghidra |
| 0x78 | 02555cd8 | FUN_01b48bf0 | float64/double (8 bytes) → FUN_01b49730 | Ghidra |
| 0x7c | 02555cdc | FUN_01b48be0 | uint64 (8 bytes) → FUN_01b496d0 | TTD ✓ |
| 0x80 | 02555ce0 | FUN_01b48bd0 | int32 (4 bytes) → FUN_01b49670 | Ghidra |
| 0x84 | 02555ce4 | FUN_01b48bc0 | uint32 (4 bytes) → FUN_01b49610 | Ghidra |
| 0x88 | 02555ce8 | FUN_01b48bb0 | uint16 (2 bytes) → FUN_01b495b0 | Ghidra |
| 0x8c | 02555cec | FUN_01b48ba0 | int16 (2 bytes) → FUN_01b49550 | Ghidra |
| 0x90 | 02555cf0 | FUN_01b48b90 | uint8 (1 byte) → FUN_01b494f0 | Ghidra |
| 0x94 | 02555cf4 | FUN_01b48b80 | int8 (1 byte) → FUN_01b49490 | Ghidra |
| 0x98 | 02555cf8 | FUN_01b48b70 | WriteByte → FUN_01b49430 | TTD ✓ |
| 0x9c | 02555cfc | FUN_01b48e70 | uint32 serializer (ObjectID) → FUN_01b49610 | TTD ✓ |

### Header Field Serializers (used by FUN_01b08ce0)

| Field | VTable Offset | Function | Bytes |
|-------|---------------|----------|-------|
| NbClassVersionsInfo | 0x98 | FUN_01b48b70 → FUN_01b49430 | 1 byte |
| ObjectName | 0x54 | FUN_01b48e90 | 4 bytes (length) + N bytes (string) |
| ObjectID | 0x9c | FUN_01b48e70 → FUN_01b49610 | 4 bytes |
| InstancingMode | 0x98 | FUN_01b48b70 → FUN_01b49430 | 1 byte |
| TypeInfo | 0x50 | FUN_01b48fb0 | variable |

### Property Type VTable (for value serialization)

| Offset | Type | Ghidra Function | Thunk Target | Bytes |
|--------|------|-----------------|--------------|-------|
| 0x58 | bool | FUN_01b48e80 | ? | 1 byte |
| 0x7c | uint64 | FUN_01b48be0 | FUN_01b496d0 | 8 bytes |
| 0x84 | uint32 | FUN_01b48bc0 | ? | 4 bytes |
| 0x98 | byte | FUN_01b48b70 | FUN_01b49430 | 1 byte |

### Stream Inner VTable at PTR_FUN_02556168 (Ghidra) / 0x02c36168 (WinDbg)

> **See Also:** For core I/O function details, see:
> - [FUN_01b6f440 - Actual 4-Byte Read](#6-fun_01b6f440---actual-4-byte-read) (inner_vtable[7])
> - [FUN_01b6f490 - Actual 8-Byte Read](#14-fun_01b6f490---actual-8-byte-read) (inner_vtable[6])
> - [FUN_01b6fea0 - Core 4-Byte Write](#fun_01b6fea0---core-4-byte-write-to-buffer) (inner_vtable[13])
> - [FUN_01b6f370 - Core Byte Write](#fun_01b6f370---core-byte-write-to-buffer) (inner_vtable[15])

Accessed via: `mov ecx, [param_1+8]; mov eax, [ecx]; call [eax+offset]`

**VTable Address Discovery (WRITE path trace at E68A19:270):**
```
esi = 0x04660698 (stream object)
[esi] = 0x02c36168 (inner vtable pointer)
[0x02c36168+0x34] = 0x0224f4d0 (WinDbg) = FUN_01b6f4d0 (Ghidra)
```

| Offset | Index | Purpose | READ Function | WRITE Function | Notes |
|--------|-------|---------|---------------|----------------|-------|
| 0x00 | [0] | Destructor | FUN_01b701c0 | FUN_01b701c0 | Ghidra verified |
| 0x04 | [1] | Stub (return false) | LAB_01b6efe0 | LAB_01b6efe0 | Ghidra verified |
| 0x08 | [2] | Reset state | FUN_01b6eff0 | FUN_01b6eff0 | Ghidra verified |
| 0x0c | [3] | IsAtEnd | LAB_01b6f010 | LAB_01b6f010 | Ghidra verified |
| 0x10 | [4] | Get buffer bounds | FUN_01b8a020 | FUN_01b8a020 | Ghidra verified |
| 0x14 | [5] | Alloc + read ptr | FUN_01b6f300 | - | Ghidra verified |
| 0x18 | [6] | 8-byte read/write | FUN_01b6f490 | - | TTD ✓ |
| 0x1c | [7] | 4-byte read/write | FUN_01b6f440 | - | TTD ✓ |
| 0x20 | [8] | 2-byte read | FUN_01b6f400 | - | Ghidra verified |
| 0x24 | [9] | 1-byte read | FUN_01b6f150 | - | Ghidra verified |
| 0x28 | [10] | N-byte read | FUN_01b6f030 | - | Ghidra verified |
| 0x2c | [11] | Thunk to [13] | FUN_01b6f100 | - | Ghidra verified |
| 0x30 | [12] | 8-byte write | - | FUN_01b6f4e0 → FUN_01b6ff10 | TTD ✓ |
| 0x34 | [13] | 4-byte write | - | FUN_01b6f4d0 → FUN_01b6fea0 | TTD ✓ |
| 0x38 | [14] | 2-byte write | - | FUN_01b6f4c0 → FUN_01b6fe40 | Ghidra verified |
| 0x3c | [15] | 1-byte write | - | FUN_01b6f370 | TTD ✓ |
| 0x40 | [16] | N-byte write | - | FUN_01b6f3b0 | Ghidra verified |
| 0x44 | [17] | Skip N bytes | FUN_01b6f2b0 | FUN_01b6f2b0 | Ghidra verified |
| 0x48 | [18] | Rewind N bytes | FUN_01b6f080 | FUN_01b6f080 | Ghidra verified |
| 0x4c | [19] | Tell (get pos) | LAB_01b6f4f0 | LAB_01b6f4f0 | Ghidra verified |
| 0x50 | [20] | Seek + Save | FUN_01b6f090 | FUN_01b6f090 | Ghidra verified |
| 0x54 | [21] | Finalize | FUN_01b6f880 | FUN_01b6f880 | Ghidra verified |
| 0x58 | [22] | Restore Position | LAB_01b6f0b0 | LAB_01b6f0b0 | Ghidra verified |
| 0x5c | [23] | Calc remaining | FUN_01b6f0c0 | FUN_01b6f0c0 | Ghidra verified |
| 0x60 | [24] | NOP | LAB_01b6f0e0 | LAB_01b6f0e0 | Ghidra verified |
| 0x64 | [25] | NOP | LAB_01b6f0f0 | LAB_01b6f0f0 | Ghidra verified |
| 0x68 | [26] | Flush buffer | LAB_01b6f6e0 | LAB_01b6f6e0 | Ghidra verified |
| 0x6c | [27] | Get flag & 1 | LAB_01b6f120 | LAB_01b6f120 | Ghidra verified |

**FUN_01b6f4d0 (vtable[0x34]) - Thunk to FUN_01b6fea0:**
```c
void FUN_01b6f4d0(void)
{
    FUN_01b6fea0(&stack0x00000004);
    return;
}
```
This is a simple thunk that passes the stack parameter to the actual 4-byte write function.

### VTable Call Chain Example (uint64 READ)

```
FUN_01b09760 (property serializer)
  └─→ FUN_01b124e0 (serialization core)
        └─→ vtable[0x7c] = FUN_01b48be0 (thunk)
              └─→ FUN_01b496d0 (8-byte handler)
                    └─→ inner_vtable[6] = FUN_01b6f490 (actual read)
```

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

**Raw Hex Dumps (from Ghidra):**
```
DAT_027ecf90 (0xbf4c2013 - SaveGameDataObject base class uint32):
  027ecf90: 01 00 00 02  13 20 4c bf  00 00 00 00  00 00 07 00
  027ecfa0: 00 00 10 00  00 00 00 00  00 00 00 00  00 00 00 00

DAT_02973250 (0x3b546966 - bool_field_0x20):
  02973250: 01 00 00 02  66 69 54 3b  00 00 00 00  00 00 00 00
  02973260: 00 00 80 00  00 00 00 00  00 00 00 00  00 00 00 00

DAT_02973270 (0x4dbc7da7 - bool_field_0x21):
  02973270: 01 00 00 02  a7 7d bc 4d  00 00 00 00  00 00 00 00
  02973280: 00 00 84 00  00 00 00 00  00 00 00 00  00 00 00 00

DAT_02973290 (0x5b95f10b - bool_field_0x22):
  02973290: 01 00 00 02  0b f1 95 5b  00 00 00 00  00 00 00 00
  029732a0: 00 00 88 00  00 00 00 00  00 00 00 00  00 00 00 00

DAT_029732b0 (0x2a4e8a90 - bool_field_0x23):
  029732b0: 01 00 00 02  90 8a 4e 2a  00 00 00 00  00 00 00 00
  029732c0: 00 00 8c 00  00 00 00 00  00 00 00 00  00 00 00 00

DAT_029732d0 (0x496f8780 - uint64_field_0x18):
  029732d0: 01 00 00 02  80 87 6f 49  00 00 00 00  00 00 09 00
  029732e0: 00 00 60 00  00 00 00 00  00 00 00 00  00 00 00 00

DAT_029732f0 (0x6f88b05b - bool_field_0x24):
  029732f0: 01 00 00 02  5b b0 88 6f  00 00 00 00  00 00 00 00
  02973300: 00 00 90 00  00 00 00 00  00 00 00 00  00 00 00 00
```

**Key Observations:**
- flags bit 0 set (0x01) = "serialize this property"
- type_info at offset 0x0e matches type codes: 0x00=bool, 0x07=uint32, 0x09=uint64
- scaled_offset formula: `object_field_offset × 4` (purpose unknown, possibly vtable indexing)

### 4. Base Class Field Property at 0x1a-0x2a
- Shortened property format: [hash 4][type_info 8][flags 1][value 4] = 17 bytes
- No size field (unlike regular properties)
- Hash 0xbf4c2013 = SaveGameDataObject field hash
- Flags byte 0x0b at offset 0x26 (property flags, NOT NbClassVersionsInfo!)
- Value at 0x27-0x2a = base class field value

> **See Also:**
> - [FUN_01b0d140 - Property Header Writer](#fun_01b0d140---property-header-writer-complete-trace) documents how property headers are written (hash, type_info, flags)
> - [Property Format in File](#property-format-in-file) shows the complete property structure diagram

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

## WRITE Path Trace (Complete)

> **Related:** The READ path functions are documented in [Traced Functions (READ Path)](#traced-functions-read-path) above. Each WRITE function has a corresponding READ implementation that uses symmetric vtable offsets.

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

### FUN_01b09e20 - Header Writer Wrapper

**WinDbg Address:** 0x021e9e20
**TTD Position:** E68A19:CC

**Parameters on stack:**
- `[esp+4]` = 0x02c1ddec (metadata pointer)
- `[esp+c]` = 0xC9876D66 (type hash)
- `[esp+18]` = 0xf74c0898 (object pointer)

This wrapper calls **FUN_01b08ce0** at address `021e9ed5`.

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

**WinDbg Address:** 0x021ed500 (Ghidra: 0x01b0d500)
**TTD Position:** E68A19:1A2

**Traced Disassembly:**
```asm
021ed505  mov edi, [ebp+8]       ; param_2 = string name (e.g., "NbClassVersionsInfo" - misleading name!)
021ed508  mov esi, ecx           ; param_1 = serializer (this)
021ed50a  mov eax, [esi]         ; vtable
021ed50c  mov edx, [eax+8]       ; vtable[2] = StartElement
021ed510  call edx               ; StartElement(name) ← NO-OP in WRITE!
021ed512  mov ecx, [ebp+0Ch]     ; param_3 = byte value to write
021ed517  mov edx, [eax+98h]     ; vtable[0x98] = WriteByte
021ed520  call edx               ; WriteByte(value) ← ACTUAL WRITE
021ed524  mov edx, [eax+10h]     ; vtable[4] = EndElement
021ed52a  call edx               ; EndElement(name) ← NO-OP in WRITE!
021ed52f  ret 8
```

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

> **Related:** See [FUN_01b6f440 - Actual 4-Byte Read](#6-fun_01b6f440---actual-4-byte-read) for the READ path equivalent.

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

### FUN_01b6f030 - N-byte Read (inner_vtable[0x28])

> **Called From:** [FUN_01b48e90 - String Serializer](#fun_01b48e90---string-serializer) for reading string character data.

**Ghidra Address:** 0x01b6f030 (WinDbg: 0x0224f030)
**Status:** Ghidra static analysis (not exercised in current trace)

```c
void __thiscall FUN_01b6f030(int param_1, void *param_2, size_t param_3) {
    // Copy N bytes from buffer to destination
    _memcpy(param_2, *(void **)(param_1 + 0x18), param_3);

    // Advance buffer pointer by N bytes
    *(int *)(param_1 + 0x18) = *(int *)(param_1 + 0x18) + param_3;
}
```

**Parameters:**
- `param_1` = stream object
- `param_2` = destination buffer (where to copy data)
- `param_3` = number of bytes to read

**Memory Layout:**
- `[param_1 + 0x18]` = current buffer pointer (source)

**Pattern:** Same as fixed-size readers but with variable length parameter.

---

### FUN_01b6f3b0 - N-byte Write (inner_vtable[0x40])

> **Called From:** [FUN_01b48e90 - String Serializer](#fun_01b48e90---string-serializer) for writing string character data.

**Ghidra Address:** 0x01b6f3b0 (WinDbg: 0x0224f3b0)
**Status:** Ghidra static analysis (not exercised in current trace)

```c
void __thiscall FUN_01b6f3b0(int param_1, void *param_2, size_t param_3) {
    // 1. Buffer expansion check (same pattern as fixed-size writers)
    if (*(int *)(param_1 + 0x30) != 0) {
        uint space_remaining = *(uint *)(param_1 + 0x1c);
        uint space_used = *(int *)(param_1 + 0x18) - *(int *)(param_1 + 0x14);
        if (space_remaining < space_used + param_3) {
            FUN_01b6f1b0(...);  // Expand buffer
        }
    }

    // 2. Copy N bytes from source to buffer
    _memcpy(*(void **)(param_1 + 0x18), param_2, param_3);

    // 3. Advance buffer pointer by N bytes
    *(int *)(param_1 + 0x18) = *(int *)(param_1 + 0x18) + param_3;
}
```

**Parameters:**
- `param_1` = stream object
- `param_2` = source buffer (data to write)
- `param_3` = number of bytes to write

**Memory Layout:**
- `[param_1 + 0x14]` = buffer start
- `[param_1 + 0x18]` = current buffer pointer (destination)
- `[param_1 + 0x1c]` = buffer capacity
- `[param_1 + 0x30]` = expansion enabled flag

**Pattern:** Same as fixed-size writers (FUN_01b6fea0, FUN_01b6ff10) but with variable length.

---

### FUN_01b6f150 - 1-byte Read (inner_vtable[0x24])

**Ghidra Address:** 0x01b6f150 (WinDbg: 0x0224f150)
**Status:** Ghidra static analysis (not exercised in current trace - WRITE mode only)

```c
void __thiscall FUN_01b6f150(int param_1, undefined1 *param_2) {
    // Read 1 byte from buffer to destination
    *param_2 = **(undefined1 **)(param_1 + 0x18);

    // Advance buffer pointer by 1 byte
    *(int *)(param_1 + 0x18) = *(int *)(param_1 + 0x18) + 1;
}
```

**Parameters:**
- `param_1` = stream object
- `param_2` = destination (where to store the byte)

**Memory Layout:**
- `[param_1 + 0x18]` = current buffer pointer (source)

**Pattern:** Identical to 1-byte write (FUN_01b6f370) but reads instead of writes.
No buffer expansion check needed for reads.

---

### FUN_01b6f090 - Seek + Save Position (inner_vtable[0x50])

> **Called From:** [CloseSection (FUN_01b48920)](#closesection-fun_01b48920---size-patching) for seeking back to section size placeholders during backpatching.

**Ghidra Address:** 0x01b6f090 (WinDbg: 0x0224f090)
**Status:** Ghidra static analysis (used by CloseSection for backpatching)

```c
void __thiscall FUN_01b6f090(int param_1, int *param_2) {
    // 1. Save current position as relative offset
    //    saved_offset = current_pos - buffer_base
    *(int *)(param_1 + 0x2c) = *(int *)(param_1 + 0x18) - *(int *)(param_1 + 0x14);

    // 2. Seek to new position (token is relative offset)
    //    current_pos = token + buffer_base
    *(int *)(param_1 + 0x18) = *param_2 + *(int *)(param_1 + 0x14);
}
```

**Parameters:**
- `param_1` = stream object
- `param_2` = pointer to position token (relative offset)

**Memory Layout:**
- `[param_1 + 0x14]` = buffer base address
- `[param_1 + 0x18]` = current position (absolute)
- `[param_1 + 0x2c]` = saved offset (relative, for restore)

**Usage in CloseSection:**
1. Save current write position
2. Seek back to section size placeholder
3. Write the calculated size (4 bytes)
4. Restore position (via LAB_01b6f0b0)

---

### LAB_01b6f0b0 - Restore Position (inner_vtable[0x58])

**Ghidra Address:** 0x01b6f0b0 (WinDbg: 0x0224f0b0)
**Status:** Ghidra static analysis (used by CloseSection after backpatching)

```asm
LAB_01b6f0b0:
    MOV  EAX, [ECX + 0x2c]    ; Get saved offset (relative)
    ADD  EAX, [ECX + 0x14]    ; Add buffer base
    MOV  [ECX + 0x18], EAX    ; Set current position (absolute)
    RET
```

**Equivalent C:**
```c
void __thiscall LAB_01b6f0b0(int param_1) {
    // Restore position from saved offset
    // current_pos = saved_offset + buffer_base
    *(int *)(param_1 + 0x18) = *(int *)(param_1 + 0x2c) + *(int *)(param_1 + 0x14);
}
```

**Memory Layout:**
- `[param_1 + 0x14]` = buffer base address
- `[param_1 + 0x18]` = current position (absolute)
- `[param_1 + 0x2c]` = saved offset (set by FUN_01b6f090)

**Pattern:** Paired with FUN_01b6f090 for seek-write-restore operations.

---

### FUN_01b6f880 - Finalize (inner_vtable[0x54])

**Ghidra Address:** 0x01b6f880 (WinDbg: 0x0224f880)
**Status:** Ghidra static analysis (cleanup/finalization function)

```c
void FUN_01b6f880(int param_1) {
    int iVar1;
    undefined4 uVar2;

    iVar1 = param_1;
    FUN_01b700b0(&param_1);  // Some cleanup operation

    if (iVar1 != 0) {
        uVar2 = FUN_01abc2c0(iVar1);
        // Call through global function pointer - likely deallocation
        (**(code **)(*(int *)*DAT_02a5e0f4 + 0x14))(5, iVar1, uVar2, 0, 0);
    }
}
```

**Purpose:** Appears to be a cleanup/finalization function, possibly for buffer deallocation
or stream finalization. Not directly related to seek operations despite being in the
same vtable region.

---

### FUN_01b6f400 - 2-byte Read (inner_vtable[0x20])

**Ghidra Address:** 0x01b6f400 (WinDbg: 0x0224f400)
**Status:** Ghidra static analysis

```c
void __thiscall FUN_01b6f400(int param_1, undefined2 *param_2) {
    // Read 2 bytes from buffer
    *param_2 = **(undefined2 **)(param_1 + 0x18);

    // Byte swap if flag set (endianness conversion)
    if ((*(byte *)(param_1 + 4) & 1) != 0) {
        // Swap bytes: AB -> BA
        char temp = *(char *)param_2;
        *(char *)param_2 = *((char *)param_2 + 1);
        *((char *)param_2 + 1) = temp;
    }

    // Advance buffer pointer by 2
    *(int *)(param_1 + 0x18) += 2;
}
```

---

### FUN_01b6f4c0 / FUN_01b6fe40 - 2-byte Write (inner_vtable[0x38])

**Ghidra Address:** 0x01b6f4c0 → 0x01b6fe40 (WinDbg: 0x0224f4c0 → 0x0224fe40)
**Status:** Ghidra static analysis

```c
void __thiscall FUN_01b6fe40(int param_1, undefined2 *param_2) {
    // 1. Buffer expansion check
    if (*(int *)(param_1 + 0x30) != 0) {
        if (capacity < used + 2) {
            FUN_01b6f1b0(...);  // Expand buffer
        }
    }

    // 2. Byte swap if flag set (endianness conversion)
    if ((*(byte *)(param_1 + 4) & 1) != 0) {
        // Swap bytes before writing
    }

    // 3. Write 2 bytes to buffer
    **(undefined2 **)(param_1 + 0x18) = *param_2;

    // 4. Advance buffer pointer by 2
    *(int *)(param_1 + 0x18) += 2;
}
```

---

### FUN_01b6f2b0 - Skip N Bytes (inner_vtable[0x44])

**Ghidra Address:** 0x01b6f2b0 (WinDbg: 0x0224f2b0)
**Status:** Ghidra static analysis

```c
void __thiscall FUN_01b6f2b0(int param_1, int param_2) {
    // Buffer expansion check (WRITE mode)
    if (*(int *)(param_1 + 0x30) != 0) {
        if (capacity < used + param_2) {
            FUN_01b6f1b0(...);  // Expand buffer
        }
    }

    // Advance buffer pointer by N bytes (skip without reading/writing)
    *(int *)(param_1 + 0x18) += param_2;
}
```

**Purpose:** Skip over N bytes without reading or writing. Used for padding or reserved fields.

---

### FUN_01b6f080 - Rewind N Bytes (inner_vtable[0x48])

**Ghidra Address:** 0x01b6f080 (WinDbg: 0x0224f080)
**Status:** Ghidra static analysis

```c
void __thiscall FUN_01b6f080(int param_1, int param_2) {
    // Move buffer pointer back by N bytes
    *(int *)(param_1 + 0x18) -= param_2;
}
```

**Purpose:** Move backward in buffer. Used for re-reading or overwriting previous data.

---

### LAB_01b6f010 - IsAtEnd (inner_vtable[0x0c])

**Ghidra Address:** 0x01b6f010 (WinDbg: 0x0224f010)
**Status:** Ghidra static analysis

```asm
LAB_01b6f010:
    MOV  EAX, [ECX + 0x18]    ; current position
    SUB  EAX, [ECX + 0x14]    ; - buffer base = bytes used
    XOR  EDX, EDX
    CMP  EAX, [ECX + 0x1c]    ; compare to capacity
    SETZ DL                    ; DL = 1 if used == capacity
    MOV  AL, DL
    RET
```

**Equivalent C:**
```c
bool __thiscall LAB_01b6f010(int param_1) {
    int used = *(int *)(param_1 + 0x18) - *(int *)(param_1 + 0x14);
    int capacity = *(int *)(param_1 + 0x1c);
    return (used == capacity);  // true if buffer is full/at end
}
```

---

### FUN_01b6f0c0 - Calculate Remaining (inner_vtable[0x5c])

**Ghidra Address:** 0x01b6f0c0 (WinDbg: 0x0224f0c0)
**Status:** Ghidra static analysis

```c
int __thiscall FUN_01b6f0c0(int param_1, int *param_2) {
    // Returns: current_offset - *param_2
    return (*(int *)(param_1 + 0x18) - *(int *)(param_1 + 0x14)) - *param_2;
}
```

**Purpose:** Calculate bytes remaining or offset difference.

---

### FUN_01b48fb0 - TypeInfo Serializer (vtable[0x50]) - COMPLETE TRACE

**WinDbg Address:** 0x02228fb0 (Ghidra: 0x01b48fb0)
**TTD Position:** E68A19:2FA (entry)

**Parameters:**
- ECX (this) = 0x24d476e0 (serializer context)
- [ebp+8] = param_2 = 0x02c1ddec (metadata pointer)
- [ebp+0xC] = param_3 = 0x07a8f6cc → **0xc9876d66** (type hash)

**Disassembly with Annotations:**
```asm
02228fb0  push    ebp
02228fb1  mov     ebp, esp
02228fb3  push    ecx
02228fb4  push    esi
02228fb5  mov     esi, ecx                    ; esi = serializer context

; FLAG CHECK: Controls whether type NAME string is serialized
02228fb7  cmp     byte ptr [esi+1012h], 0     ; [24d486f2] = 0x00
02228fbe  je      02229008                    ; TAKEN! (flag=0, skip string)

; --- STRING PATH (not taken in this trace) ---
02228fc0  cmp     byte ptr [esi+4], 0         ; Mode check
02228fc4  mov     eax, [esi]                  ; Get vtable
02228fc6  jne     02228fe5                    ; If READ mode, jump

; WRITE mode with string:
02228fc8  mov     edx, [eax+54h]              ; vtable[0x54] = String serializer
02228fcb  lea     ecx, [ebp+8]
02228fce  push    ecx
02228fcf  mov     ecx, esi
02228fd1  call    edx                         ; Serialize type name string
02228fd3  mov     ecx, [ebp+0Ch]
02228fd6  push    ecx
02228fd7  mov     ecx, esi
02228fd9  call    FUN_01b49610                ; Write type hash (4 bytes)
02228fde  pop     esi
02228fdf  mov     esp, ebp
02228fe1  pop     ebp
02228fe2  ret     8

; READ mode with string:
02228fe5  mov     edx, [eax+84h]              ; vtable[0x84]
02228feb  lea     ecx, [ebp-4]
02228fee  push    ecx
02228fef  mov     ecx, esi
02228ff1  mov     [ebp-4], 0
02228ff8  call    edx
02228ffa  mov     ecx, [esi+8]
02228ffd  mov     eax, [ecx]
02228fff  mov     edx, [ebp-4]
02229002  mov     eax, [eax+44h]              ; inner_vtable[0x44]
02229005  push    edx
02229006  call    eax

; --- SIMPLE PATH (taken in this trace) ---
; Just write the type hash, no string
02229008  mov     ecx, [ebp+0Ch]              ; param_3 = &type_hash
0222900b  push    ecx                         ; Push pointer to hash
0222900c  mov     ecx, esi                    ; this = serializer
0222900e  call    FUN_01b49610                ; Write 4-byte type hash
02229013  pop     esi
02229014  mov     esp, ebp
02229016  pop     ebp
02229017  ret     8
```

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

**Traced Flow:**
```
E68A19:2FA  Entry (ECX=0x24d476e0)
E68A19:2FF  cmp [esi+1012h], 0 → ZF=1 (flag is 0)
E68A19:300  je 02229008 → TAKEN
E68A19:301  At 02229008: mov ecx, [ebp+0Ch] → ECX = 0x07a8f6cc
E68A19:302  push ecx (pointer to type hash)
E68A19:304  call FUN_01b49610
```

---

### FUN_01b49610 - 4-Byte Write Dispatcher (DETAILED TRACE)

**WinDbg Address:** 0x02229610 (Ghidra: 0x01b49610)
**TTD Position:** E68A19:305 (called from FUN_01b48fb0)

**Parameters:**
- ECX = 0x24d476e0 (serializer context)
- [ebp+8] = 0x07a8f6cc → **0xc9876d66** (type hash value)

**Disassembly with Annotations:**
```asm
02229610  push    ebp
02229611  mov     ebp, esp

; COUNTER TRACKING CHECK
02229613  cmp     word ptr [ecx+1010h], 0     ; [24d486f0] = 0x0000
0222961b  je      02229645                    ; TAKEN! (counter disabled)

; --- Counter update (skipped) ---
0222961d  cmp     byte ptr [ecx+4], 0         ; Mode check
02229621  je      02229635                    ; WRITE path
; READ: counter -= 4
02229623  movzx   eax, word ptr [ecx+1010h]
0222962a  add     dword ptr [ecx+eax*8+8], -4
0222962f  lea     eax, [ecx+eax*8+8]
02229633  jmp     02229645
; WRITE: counter += 4
02229635  movzx   edx, word ptr [ecx+1010h]
0222963c  add     dword ptr [ecx+edx*8+8], 4
02229641  lea     eax, [ecx+edx*8+8]

; --- ACTUAL I/O OPERATION ---
02229645  cmp     byte ptr [ecx+4], 0         ; [24d476e4] = 0x00 (WRITE)
02229649  mov     ecx, [ecx+8]                ; Get stream object
0222964c  je      02229656                    ; TAKEN (WRITE mode)

; READ path: inner_vtable[0x1c]
0222964e  mov     eax, [ecx]
02229650  mov     eax, [eax+1Ch]              ; inner_vtable[7] = 4-byte read
02229653  pop     ebp
02229654  jmp     eax

; WRITE path: inner_vtable[0x34]
02229656  mov     eax, [ebp+8]                ; param = &value
02229659  mov     edx, [ecx]                  ; Get inner vtable
0222965b  mov     eax, [eax]                  ; Dereference: EAX = actual value
0222965d  mov     edx, [edx+34h]              ; inner_vtable[0x34] = 4-byte write
02229660  push    eax                         ; Push VALUE (not pointer!)
02229661  call    edx                         ; Call FUN_01b6f4d0 → FUN_01b6fea0
02229663  pop     ebp
02229664  ret     4
```

**Key Observations:**
1. Counter at `[ecx+0x1010]` = 0x0000 → counter tracking disabled, skip to I/O
2. Mode at `[ecx+0x4]` = 0x00 → WRITE mode
3. Stream object at `[ecx+0x8]` used for actual I/O
4. WRITE path dereferences the pointer to get actual value before calling write function
5. Calls `inner_vtable[0x34]` = FUN_01b6f4d0 (thunk) → FUN_01b6fea0 (core write)

**Serializer Context Structure (confirmed):**
| Offset | Value | Purpose |
|--------|-------|---------|
| +0x00 | vtable | Serializer mode vtable |
| +0x04 | 0x00 | Mode (0=WRITE, 1=READ) |
| +0x08 | stream_obj | Stream object pointer |
| +0x1010 | 0x0000 | Counter tracking flag |
| +0x1012 | 0x00 | TypeInfo string flag |

---

### FUN_01b09650 - Bool Property Serializer (WRITE Mode Entry)

**WinDbg Address:** 0x021e9650 (Ghidra: 0x01b09650)
**TTD Position:** E68A1B:BD

Now in property serialization phase. Calls FUN_01b11fb0 which:
1. Calls FUN_01b0d140 to write property header
2. Calls vtable[0x58] to write bool value
3. Calls vtable[5] CloseSection("Property")

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

> **See Also:** [Detailed Layout](#detailed-layout) shows the complete file structure with these corrected field boundaries.

**Backpatching observed:**
- Position E68A1F:D0: `mov dword ptr [0466000e], 0x00000090`
- This happens AFTER all properties are serialized
- Fields 0x12-0x15 and 0x16-0x19 are written earlier during serialization

---

## Section Nesting (OpenSection/CloseSection)

> **Visual Diagrams:** See [Visual: Stack State During Serialization](#visual-stack-state-during-serialization-lifo-model), [Visual: File Layout with Section Boundaries](#visual-file-layout-with-section-boundaries), and [Visual: Backpatching Mechanism](#visual-backpatching-mechanism) below for graphical representations of the section nesting system.

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

<a id="visual-stack-state-during-serialization-lifo-model"></a>
### Visual: Stack State During Serialization (LIFO Model)

> **Related:** See [Section Stack Model](#section-stack-model) above for the textual explanation, and [CloseSection Backpatch Mechanism](#closesection-backpatch-mechanism-traced) for the traced implementation.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SECTION STACK EVOLUTION (WRITE PATH)                     │
└─────────────────────────────────────────────────────────────────────────────┘

Step 1: OpenSection("Object")           Step 2: OpenSection("Properties")
┌───────────────────┐                   ┌───────────────────┐
│   SECTION STACK   │                   │   SECTION STACK   │
├───────────────────┤                   ├───────────────────┤
│ [0] pos=0x0e      │ ← top             │ [1] pos=0x12      │ ← top
│     "Object"      │                   │     "Properties"  │
│                   │                   ├───────────────────┤
│                   │                   │ [0] pos=0x0e      │
│                   │                   │     "Object"      │
└───────────────────┘                   └───────────────────┘
   stack_ptr = 1                           stack_ptr = 2


Step 3: OpenSection(BaseClass)          Step 4: Write base class (17 bytes)
┌───────────────────┐                   ┌───────────────────┐
│   SECTION STACK   │                   │   SECTION STACK   │
├───────────────────┤                   ├───────────────────┤
│ [2] pos=0x16      │ ← top             │ [2] pos=0x16      │ ← top (unchanged)
│     "BaseClass"   │                   │     "BaseClass"   │
├───────────────────┤                   ├───────────────────┤
│ [1] pos=0x12      │                   │ [1] pos=0x12      │
│     "Properties"  │                   │     "Properties"  │
├───────────────────┤                   ├───────────────────┤
│ [0] pos=0x0e      │                   │ [0] pos=0x0e      │
│     "Object"      │                   │     "Object"      │
└───────────────────┘                   └───────────────────┘
   stack_ptr = 3                           (data written 0x1a-0x2a)


Step 5: CloseSection (BaseClass)        Step 6: Write properties (0x2b-0x9d)
┌───────────────────┐                   ┌───────────────────┐
│   SECTION STACK   │                   │   SECTION STACK   │
├───────────────────┤                   ├───────────────────┤
│ [1] pos=0x12      │ ← top             │ [1] pos=0x12      │ ← top (unchanged)
│     "Properties"  │                   │     "Properties"  │
├───────────────────┤                   ├───────────────────┤
│ [0] pos=0x0e      │                   │ [0] pos=0x0e      │
│     "Object"      │                   │     "Object"      │
└───────────────────┘                   └───────────────────┘
   POP! Patches 0x16 with size=17          (properties written)
   stack_ptr = 2


Step 7: CloseSection (Properties)       Step 8: CloseSection (Object)
┌───────────────────┐                   ┌───────────────────┐
│   SECTION STACK   │                   │   SECTION STACK   │
├───────────────────┤                   ├───────────────────┤
│ [0] pos=0x0e      │ ← top             │     (empty)       │
│     "Object"      │                   │                   │
└───────────────────┘                   └───────────────────┘
   POP! Patches 0x12 with size=136         POP! Patches 0x0e with size=144
   stack_ptr = 1                           stack_ptr = 0
```

<a id="visual-file-layout-with-section-boundaries"></a>
### Visual: File Layout with Section Boundaries

> **Related:** See [Detailed Layout](#detailed-layout) for the byte-by-byte field breakdown.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SECTION 3 FILE LAYOUT                               │
│                    (TypeInfo Block with Nested Sections)                    │
└─────────────────────────────────────────────────────────────────────────────┘

Offset    Content                              Section Hierarchy
──────────────────────────────────────────────────────────────────────────────
0x00 ┌──────────────────────────────────┐
     │  Section 3 header (magic, etc)   │
0x0e ├──────────────────────────────────┤    ┌─── OBJECT SECTION ────────────┐
     │  [SIZE: 0x90 = 144 bytes]        │◄───┤   Spans 0x12 to 0xa2 (EOF)    │
     │  (backpatched at step 8)         │    │   Size written LAST           │
0x12 ├──────────────────────────────────┤    │  ┌─ PROPERTIES SECTION ──────┐│
     │  [SIZE: 0x88 = 136 bytes]        │◄───┼──┤  Spans 0x1a to 0xa2 (EOF)  ││
     │  (backpatched at step 7)         │    │  │  Size written 2nd-to-last  ││
0x16 ├──────────────────────────────────┤    │  │ ┌─ BASECLASS SECTION ────┐││
     │  [SIZE: 0x11 = 17 bytes]         │◄───┼──┼─┤ Spans 0x1a to 0x2a     │││
     │  (backpatched at step 5)         │    │  │ │ Size written FIRST     │││
0x1a ├──────────────────────────────────┤    │  │ │                        │││
     │  Base Class Property:            │    │  │ │ hash: 0xbf4c2013       │││
     │    hash     (4 bytes)            │    │  │ │ type_info (8 bytes)    │││
     │    type_info (8 bytes)           │    │  │ │ flags: 0x0b            │││
     │    flags   (1 byte)              │    │  │ │ value: 0x00000000      │││
     │    value   (4 bytes)             │    │  │ │                        │││
0x2b ├──────────────────────────────────┤    │  │ └────────────────────────┘││
     │                                  │    │  │                            ││
     │  Property 1 (bool_field_0x20)    │    │  │  Individual properties     ││
     │  Property 2 (bool_field_0x21)    │    │  │  each with own section     ││
     │  Property 3 (ulong_field_0x28)   │    │  │  (OpenSection/CloseSection)││
     │  Property 4 (ushort_field_0x30)  │    │  │                            ││
     │  Property 5 (ushort_field_0x32)  │    │  │                            ││
     │  ...                             │    │  │                            ││
0x9d │                                  │    │  │                            ││
0xa2 └──────────────────────────────────┘    │  └────────────────────────────┘│
     EOF                                     └────────────────────────────────┘
```

<a id="visual-backpatching-mechanism"></a>
### Visual: Backpatching Mechanism

> **Related:** See [CloseSection (FUN_01b48920) - Size Patching](#closesection-fun_01b48920---size-patching) for the traced implementation details.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    HOW BACKPATCHING WORKS (WRITE MODE)                      │
└─────────────────────────────────────────────────────────────────────────────┘

                        FORWARD PASS (OpenSection)
                        ──────────────────────────

File Position:     0x0e        0x12        0x16        0x1a
                    │           │           │           │
                    ▼           ▼           ▼           ▼
              ┌─────────┬─────────┬─────────┬─────────────────────┐
              │ reserve │ reserve │ reserve │   write content...  │
              │ 4 bytes │ 4 bytes │ 4 bytes │                     │
              │ (????)  │ (????)  │ (????)  │                     │
              └─────────┴─────────┴─────────┴─────────────────────┘
                    │           │           │
                    ▼           ▼           ▼
              Stack Push   Stack Push   Stack Push
              pos=0x0e     pos=0x12     pos=0x16


                        BACKWARD PASS (CloseSection)
                        ───────────────────────────

  After writing base class (cursor at 0x2b):
  ┌─────────────────────────────────────────────────────────────┐
  │  CloseSection #1:                                           │
  │    1. Pop stack → get saved_pos = 0x16                      │
  │    2. Calculate: size = current_pos - saved_pos - 4         │
  │                  size = 0x2b - 0x16 - 4 = 0x11 (17)         │
  │    3. Seek to 0x16                                          │
  │    4. Write size (0x00000011)     ─────────┐                │
  │    5. Seek back to 0x2b                    │                │
  └────────────────────────────────────────────│────────────────┘
                                               │
              ┌─────────┬─────────┬─────────┬──▼──────────────────┐
              │ (????)  │ (????)  │   17    │   base class data   │
              └─────────┴─────────┴─────────┴─────────────────────┘
                                       ▲
                                       │
                              BACKPATCH! (TTD: E68A19:CF7)


  After writing properties (cursor at 0xa2):
  ┌─────────────────────────────────────────────────────────────┐
  │  CloseSection #2:                                           │
  │    1. Pop stack → get saved_pos = 0x12                      │
  │    2. Calculate: size = 0xa2 - 0x12 - 4 = 0x88 (136)        │
  │    3. Seek to 0x12, Write 136, Seek back                    │
  └─────────────────────────────────────────────────────────────┘
                         │
              ┌─────────┬▼────────┬─────────┬─────────────────────┐
              │ (????)  │   136   │   17    │   all content...    │
              └─────────┴─────────┴─────────┴─────────────────────┘
                              ▲
                              │
                     BACKPATCH! (TTD: E68A1D:B87)


  Final CloseSection (cursor still at 0xa2):
  ┌─────────────────────────────────────────────────────────────┐
  │  CloseSection #3:                                           │
  │    1. Pop stack → get saved_pos = 0x0e                      │
  │    2. Calculate: size = 0xa2 - 0x0e - 4 = 0x90 (144)        │
  │    3. Seek to 0x0e, Write 144, Seek back                    │
  └─────────────────────────────────────────────────────────────┘
                │
              ┌─▼───────┬─────────┬─────────┬─────────────────────┐
              │   144   │   136   │   17    │   all content...    │
              └─────────┴─────────┴─────────┴─────────────────────┘
                   ▲
                   │
          BACKPATCH! (TTD: E68A1F:D0)


                    FINAL FILE STATE
                    ─────────────────
              ┌─────────┬─────────┬─────────┬─────────────────────┐
              │ 144     │ 136     │ 17      │   serialized data   │
              │ Object  │ Props   │ Base    │   (base + props)    │
              │ section │ section │ class   │                     │
              │ size    │ size    │ size    │                     │
              └─────────┴─────────┴─────────┴─────────────────────┘
              0x0e      0x12      0x16      0x1a              0xa2
```

### Visual: Single Property Section Nesting

```
┌─────────────────────────────────────────────────────────────────────────────┐
│              PROPERTY SECTION (Each Property Has Its Own Section)           │
└─────────────────────────────────────────────────────────────────────────────┘

For each property, the same OpenSection/CloseSection pattern is used:

  FUN_01b0d140 (Property Header Writer):
  ┌──────────────────────────────────────────────────────────────────────────┐
  │                                                                          │
  │   1. OpenSection("Property")                                             │
  │      ├─ Reserve 4 bytes for size at current position                     │
  │      └─ Push position to section stack                                   │
  │                                                                          │
  │   2. Write hash (4 bytes)          ─┐                                    │
  │   3. Write type_info (8 bytes)      │  Property header                   │
  │   4. Write flags (1 byte)          ─┘  (13 bytes fixed)                  │
  │                                                                          │
  │   [Return to caller - caller writes value]                               │
  │                                                                          │
  │   5. Write value (variable size depending on type)                       │
  │                                                                          │
  │   6. CloseSection("Property")                                            │
  │      ├─ Pop position from stack                                          │
  │      ├─ Calculate size = current_pos - saved_pos - 4                     │
  │      └─ Backpatch size at saved position                                 │
  │                                                                          │
  └──────────────────────────────────────────────────────────────────────────┘


  Example: bool_field_0x20 (first property after base class)

  Before CloseSection:
  ┌────────────┬────────────┬──────────────┬───────┬───────┐
  │ size(????) │ hash       │ type_info    │ flags │ value │
  │ 4 bytes    │ 0x3b546966 │ 8 bytes      │ 0x0b  │ 0x01  │
  └────────────┴────────────┴──────────────┴───────┴───────┘
  │            │◄───────────── 14 bytes ─────────────────►│
  ▲
  saved_pos

  After CloseSection:
  ┌────────────┬────────────┬──────────────┬───────┬───────┐
  │ size = 14  │ hash       │ type_info    │ flags │ value │
  │ 0x0000000e │ 0x3b546966 │ 8 bytes      │ 0x0b  │ 0x01  │
  └────────────┴────────────┴──────────────┴───────┴───────┘
       ▲
       │
       └─── Backpatched with calculated size
```

### Section Size Values (TRACED)

| Field | Offset | Value | Decimal | Meaning | Written At |
|-------|--------|-------|---------|---------|------------|
| field_0x16 | 0x16-0x19 | 0x00000011 | 17 | Base class property size | E68A19:CF7 |
| field_0x12 | 0x12-0x15 | 0x00000088 | 136 | 0xa2 - 0x1a = bytes from base class to EOF | E68A1D:B87 |
| field_0x0e | 0x0e-0x11 | 0x00000090 | 144 | 0xa2 - 0x12 = bytes from Properties to EOF | E68A1F:D0 |

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

---

Then the base class property is written by SaveGameDataObject::Serialize → FUN_01b0a1f0:
```
0x1a-0x1d: base_class_hash (0xbf4c2013)
0x1e-0x25: base_class_type_info (8 bytes)
0x26: base_class_flags (0x0b) - written by FUN_01b076f0
0x27-0x2a: base_class_value (0x00000000)
```

---

<a id="fun_01b0d140---property-header-writer-complete-trace"></a>
### FUN_01b0d140 - Property Header Writer (COMPLETE TRACE)

> **Called From:** Property serializers like [FUN_01b09650 (Bool)](#7-fun_01b09650---bool-property-serializer) and [FUN_01b09760 (uint64)](#10-fun_01b09760---uint64-property-serializer) via their core functions.
> **Calls:** [FUN_01b0e680](#16-fun_01b0e680---property-hash-writer) for hash, [FUN_01b0e980](#17-fun_01b0e980---type-info-writer) for type_info, [FUN_01b076f0](#fun_01b076f0---property-flags-writer) for flags byte.

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

**Key Assembly Points:**
```asm
021ed190  push    offset "Property"    ; String for section name
021ed196  call    edx                  ; vtable[0x0c] = OpenSection
          ; → Reserves 4 bytes at current position for size

021ed19b  mov     eax, [ebx+4]         ; Get property hash from metadata
021ed1af  call    FUN_01b0e680         ; Write property hash (4 bytes)
          ; → Writes hash to buffer

021ed1c7  mov     edx, [ebx+8]         ; type_info low
021ed1ca  mov     eax, [ebx+0Ch]       ; type_info high
021ed1da  call    FUN_01b0e980         ; Write type_info (8 bytes)
          ; → Writes 8-byte type descriptor

021ed2a4  and     al, 0EFh             ; Clear bit 4
021ed2a6  or      al, 0Bh              ; Set flags to 0x0b
021ed2ac  call    FUN_01b076f0         ; Write flags byte
          ; → Writes single byte 0x0b to buffer
```

**Property Metadata Structure (param_2):**
```
+0x00: flags (bit 17 checked for alternative path)
+0x04: property hash (4 bytes) - e.g., 0x3b546966 for bool_field_0x20
+0x08: type_info low (4 bytes)
+0x0C: type_info high (4 bytes)
```

<a id="property-format-in-file"></a>
**Property Format in File:**
```
[size 4][hash 4][type_info 8][flags 1][value N]
   ↑       ↑         ↑          ↑        ↑
   │       │         │          │        └── Written by caller (vtable[0x58/0x7c/0x84])
   │       │         │          └── FUN_01b076f0 (always 0x0b in this trace)
   │       │         └── FUN_01b0e980 (8 bytes from metadata +8/+C)
   │       └── FUN_01b0e680 (4 bytes from metadata +4)
   └── OpenSection (backpatched by CloseSection with total size)
```

**Traced Example (bool_field_0x20 at offset 0x2B):**
```
Position E68A1B:25B - In FUN_01b0d140
  Buffer before: 0x0466002B (offset 0x2B)
  Property metadata at 0x03053250:
    +4: 0x3b546966 (hash)
    +8: 0x00000000 (type_info low)
    +C: 0x00000000 (type_info high)

After FUN_01b0d140 + value write:
  0x2B-0x2E: 0e 00 00 00  (size = 14 bytes, backpatched)
  0x2F-0x32: 66 69 54 3b  (hash 0x3b546966 LE)
  0x33-0x3A: 00 00 00 00 00 00 00 00  (type_info)
  0x3B:      0b           (flags)
  0x3C:      01           (bool value = true)
```

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

**Traced Call (first bool property):**
```
Parameters:
  ECX (this) = 0x24d476e0 (serializer context)
  param_2 = 0x02c34cbc → "Name" (tag string)
  param_3 = 0x00000000 (unused)
  param_4 = 0x07a8f698 → 0x3b546966 (property hash)

Call chain:
  E68A1B:26D  vtable[0x08] = 0x02228770 (FUN_01b48770) - StartElement("Name") [NO-OP]
  E68A1B:276  vtable[0x50] = 0x02228fb0 (FUN_01b48fb0) - Write hash
              └─→ FUN_01b49610 → FUN_01b6fea0 (core 4-byte write)
  E68A1B:2BF  vtable[0x10] = 0x022287a0 (FUN_01b487a0) - EndElement("Name") [NO-OP]

Buffer: 0x0466002b → 0x0466002f (4 bytes written)
```

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

**Traced Call (first bool property):**
```
Parameters:
  ECX (this) = 0x07a8f7d4 (serialization context)
  param_2 = 0x07a8f690 → [0x00000000, 0x00000000] (type_info for bool)

Version check:
  [ECX + 0x24] = 0x10 (16 decimal) - >= 9, takes CURRENT PATH

Call chain:
  E68A1B:2E1  vtable[0x08] = 0x02228770 (FUN_01b48770) - StartElement("Type") [NO-OP]
  E68A1B:2E9  vtable[0x4c] = 0x02229020 (FUN_01b49020) - 8-byte handler
              └─→ Checks [serializer+0x1012] = 0 → simple path
              └─→ FUN_01b496d0 → FUN_01b6f4e0 → FUN_01b6ff10 (core 8-byte write)
  E68A1B:338  vtable[0x10] = 0x022287a0 (FUN_01b487a0) - EndElement("Type") [NO-OP]

Tag strings:
  0x02c34cb0 → "Type"
  0x02cd9b50 → format specifier (appears empty/null)
```

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

**Disassembly:**
```asm
02228e80  push    ebp
02228e81  mov     ebp, esp
02228e83  pop     ebp
02228e84  jmp     FUN_01b497f0 (022297f0)
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

**Traced Call (first bool property value):**
```
Parameters:
  ECX (this) = 0x24d476e0 (serializer context)
  param_2 = 0xf74c08b8 → 0x01 (bool value = true)

Key checks:
  [ECX + 0x1010] = 0x0003 (counter enabled, index 3)
  [ECX + 0x4] = 0x00 (WRITE mode)

Counter update:
  [ECX + 3*8 + 8] = [0x24d47700] incremented (tracks bytes written)

Stream object:
  [ECX + 0x8] = 0x07a8f854

Inner vtable:
  [0x07a8f854] = 0x02c36168 (Stream Inner VTable)
  [0x02c36168 + 0x3c] = 0x0224f370 (FUN_01b6f370 - core 1-byte write)

Call:
  E68A1B:426  call FUN_01b6f370 with EAX = 0x01 (bool value)

Buffer:
  Before: 0x0466003b
  After:  0x0466003c (advanced by 1 byte)
```

**Complete Bool WRITE Call Chain:**
```
FUN_01b48e80 (vtable[0x58]) - thin wrapper
  └─→ FUN_01b497f0 (1-byte dispatcher)
        ├─→ Counter: [serializer+0x1010] = 3, increments [serializer+0x20]
        ├─→ Mode: [serializer+4] = 0 (WRITE)
        ├─→ Stream: [serializer+8] = 0x07a8f854
        └─→ inner_vtable[0x3c] = FUN_01b6f370 (core 1-byte write)
              └─→ *buffer++ = 0x01
```

**READ vs WRITE Comparison:**
| Mode | Inner VTable Offset | Function | Action |
|------|---------------------|----------|--------|
| READ | 0x24 (index 9) | FUN_01b6f3b0 | `*param_2 = *buffer++` |
| WRITE | 0x3c (index 15) | FUN_01b6f370 | `*buffer++ = *param_2` |

---

### 21. FUN_01b48be0 - uint64 Serializer (vtable[0x7c]) - WRITE Mode

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

**Disassembly:**
```asm
02228be0  push    ebp
02228be1  mov     ebp, esp
02228be3  pop     ebp
02228be4  jmp     FUN_01b496d0 (022296d0)
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

**Traced Call (uint64 property value):**
```
Parameters:
  ECX (this) = 0x24d476e0 (serializer context)
  param_2 = 0xf74c08b0 → [0x00000000, 0x00000000] (uint64 = 0)

Key checks:
  [ECX + 0x1010] = 0x0003 (counter enabled, index 3)
  [ECX + 0x4] = 0x00 (WRITE mode)

Counter update:
  [ECX + 3*8 + 8] = [0x24d47700] += 8 (was 0x0d, now 0x15)

Stream object:
  [ECX + 0x8] = 0x07a8f854

Inner vtable:
  [0x07a8f854] = 0x02c36168 (Stream Inner VTable)
  [0x02c36168 + 0x30] = 0x0224f4e0 (FUN_01b6f4e0 - core 8-byte write)

Value decomposition:
  Low dword:  [0xf74c08b0] = 0x00000000
  High dword: [0xf74c08b4] = 0x00000000

Call:
  E68A1D:406  push high (0), push low (0), call FUN_01b6f4e0

Buffer:
  After: 0x04660084 (advanced by 8 bytes)
```

**Complete uint64 WRITE Call Chain:**
```
FUN_01b48be0 (vtable[0x7c]) - thin wrapper
  └─→ FUN_01b496d0 (8-byte dispatcher)
        ├─→ Counter: [serializer+0x1010] = 3, adds 8 to [serializer+0x20]
        ├─→ Mode: [serializer+4] = 0 (WRITE)
        ├─→ Stream: [serializer+8] = 0x07a8f854
        ├─→ Load value as two dwords: low=[param], high=[param+4]
        └─→ inner_vtable[0x30] = FUN_01b6f4e0 (core 8-byte write)
              └─→ Writes 8 bytes to buffer
```

**READ vs WRITE Comparison (8-byte):**
| Mode | Inner VTable Offset | Function | Parameters |
|------|---------------------|----------|------------|
| READ | 0x18 (index 6) | FUN_01b6f490 | output_ptr |
| WRITE | 0x30 (index 12) | FUN_01b6f4e0 | low_dword, high_dword |

---

### vtable[0x84] - uint32 Serializer (WRITE Path)

**TTD Position:** E68A19:C6B → E68A19:CA2
**Value Written:** 0x00000000 (base class field value at offset 0x27)

**Call Chain:**
```
FUN_01b48bc0 (vtable[0x84]) @ 0x02228bc0
  │ Thin wrapper - just jmp to dispatcher
  └─→ jmp FUN_01b49610 @ 0x02229610 (4-byte dispatcher)
        │
        ├─→ Counter check: [ecx+0x1010] = 3 (active)
        ├─→ Counter increment: [ecx+3*8+8] += 4 (0x0D → 0x11)
        ├─→ Mode check: [ecx+4] = 0 (WRITE)
        ├─→ Stream: [ecx+8] = 0x07a8f854
        ├─→ Load value: [param] = 0x00000000
        └─→ inner_vtable[0x34] = FUN_01b6f4d0 @ 0x0224f4d0
              │
              └─→ call FUN_01b6fea0 @ 0x0224fea0 (core 4-byte write)
                    │
                    ├─→ Stream: esi = 0x07a8f854
                    ├─→ [esi+0x14] = 0x04660000 (buffer base)
                    ├─→ [esi+0x18] = 0x04660027 (write position)
                    ├─→ [esi+0x1C] = 0x00001000 (buffer size)
                    ├─→ Bounds check: (0x27 + 4 = 0x2B) <= 0x1000 ✓
                    ├─→ WRITE: mov dword ptr [0x04660027], 0x00000000
                    └─→ Update position: [esi+0x18] += 4 → 0x0466002B
```

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

**TTD Position:** E68A1D:CE1 → E68A1D:F9D
**Purpose:** Writes Dynamic Properties section (trailing 4 zeros at offset 0x9e)

**Call Chain:**
```
FUN_01b0d0c0 @ 0x021ed0c0 (finalization)
  │
  ├─→ Early exit check: [context+0x58] and [context+0x20]
  │   (First call at E68A1B:A5 took early exit - NO-OP)
  │
  └─→ Main path (second invocation):
        │
        ├─→ E68A1D:CE1: call vtable[0x0c] = OpenSection("Dynamic Properties")
        │   push 0x02c34e58  ; "Dynamic Properties" string
        │   call 0x02228890  ; FUN_01b48890 (OpenSection)
        │
        ├─→ E68A1D:E26: call FUN_01b091a0 (process dynamic properties)
        │   (No properties to write in this save)
        │
        └─→ E68A1D:F5F: call vtable[0x14] = CloseSection("Dynamic Properties")
              push 0x02c34e58  ; "Dynamic Properties" string
              call 0x02228920  ; FUN_01b48920 (CloseSection)
                    │
                    ├─→ Mode check: [esi+4] = 0 (WRITE)
                    ├─→ Counter: [esi+0x1010] = 2, decremented to 1
                    ├─→ Size value: [esi+2*8+8] = 0x00000000
                    └─→ inner_vtable[0x34] → FUN_01b6fea0
                          │
                          └─→ WRITE: mov dword ptr [0x0466009e], 0x00000000
                              Position update: 0x9e → 0xa2
```

**Key Insight:** The trailing 4 zeros at offset 0x9e-0xa1 are the **Dynamic Properties section size** (zero because this save has no dynamic properties). They are written by CloseSection backpatching the size reserved by OpenSection.

**Ghidra References:**
- FUN_01b0d0c0: Finalization entry point
- FUN_01b48890: OpenSection (vtable[0x0c])
- FUN_01b48920: CloseSection (vtable[0x14])
- FUN_01b091a0: Dynamic properties processor

**String at 0x02c34e58:** "Dynamic Properties"

---

### What Remains to Trace (WRITE Path)

1. ~~**FUN_01b0d500** - How bytes are written~~ ✓ Complete
2. ~~**Core byte/uint32 write functions**~~ ✓ Complete
3. ~~**FUN_01b0d140** - Property header writer~~ ✓ Complete
4. ~~**FUN_01b0e680** - Property hash writer~~ ✓ Complete
5. ~~**FUN_01b0e980** - Type info writer~~ ✓ Complete
6. ~~**vtable[0x58] Bool writer**~~ ✓ Complete
7. ~~**vtable[0x7c] uint64 writer**~~ ✓ Complete
8. ~~**vtable[0x84] uint32 writer**~~ ✓ Complete
9. ~~**FUN_01b0d0c0** - Finalization in WRITE mode (writes trailing 4 zeros)~~ ✓ Complete

---

## Parser Verification Checklist

> **See Also:** The parser implementation is in [`section3_parser.py`](section3_parser.py) in the same directory. The parser implements all traced serialization behavior and has been verified to produce byte-for-byte identical output.

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
| Bool property format | ✓ [size 4][hash 4][type_info 8][flags 1][value 1] | ✓ |
| uint64 property format | ✓ [size 4][hash 4][type_info 8][flags 1][value 8] | ✓ |
| Property flags byte (0x0b) | ✓ | ✓ |
| Trailing bytes (4 zeros) | ✓ | ✓ (Dynamic Properties CloseSection) |

---

## Parser Verification Results

> **See Also:** The parser source code is in [`section3_parser.py`](section3_parser.py). Line numbers referenced below correspond to that file.

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

**Bool Property (traced at B1F2B:BE9):**
```
Parser format: [size 4][hash 4][type_info 8][flags 1][value 1]
Traced format: [size 4][hash 4][type_info 8][flags 1][value 1]
Status: ✓ MATCH
```

**UInt64 Property (traced at B1F2B:1643):**
```
Parser format: [size 4][hash 4][type_info 8][flags 1][value 8]
Traced format: [size 4][hash 4][type_info 8][flags 1][value 8]
Status: ✓ MATCH
```

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

## Functions Traced (Complete List)

### Main Serialization Functions

| Ghidra | WinDbg | Function | Purpose | Traced |
|--------|--------|----------|---------|--------|
| FUN_01710580 | 0x01df0580 | AssassinSingleProfileData::Serialize | Main entry point | ✓ READ ✓ WRITE |
| FUN_005e3700 | 0x00cc3700 | SaveGameDataObject::Serialize | Base class serializer | ✓ |
| FUN_01b09e20 | 0x021e9e20 | Header writer wrapper | Calls FUN_01b08ce0 | ✓ |
| FUN_01b08ce0 | 0x021e8ce0 | Header writer (ObjectInfo) | Writes 0x00-0x19 | ✓ |
| FUN_01b0d0c0 | 0x021ed0c0 | Finalization | Writes trailing zeros | ✓ |

### Property Serialization Functions

| Ghidra | WinDbg | Function | Purpose | Traced |
|--------|--------|----------|---------|--------|
| FUN_01b09650 | 0x021e9650 | Bool property serializer | Entry for bool props | ✓ |
| FUN_01b09760 | 0x021e9760 | uint64 property serializer | Entry for uint64 props | ✓ |
| FUN_01b11fb0 | 0x021f1fb0 | Bool serialization core | vtable[0x58] dispatch | ✓ |
| FUN_01b124e0 | 0x021f24e0 | uint64 serialization core | vtable[0x7c] dispatch | ✓ |
| FUN_01b12fa0 | 0x021f2fa0 | Property serialization core | Base class field | ✓ |
| FUN_01b0a1f0 | 0x021ea1f0 | Base class field wrapper | Calls FUN_01b12fa0 | ✓ |
| FUN_01b076f0 | 0x021e76f0 | Property flags writer | Writes 0x0b byte | ✓ |
| FUN_01b0d140 | 0x021ed140 | Property header writer | Hash/type_info/flags | ✓ |
| FUN_01b0e680 | 0x021ee680 | Property hash writer | vtable wrapper | ✓ |
| FUN_01b0e980 | 0x021ee980 | Type info writer | Version-aware 8-byte | ✓ |
| FUN_01b49020 | 0x02229020 | 8-byte serializer | Optional type name | ✓ |
| FUN_01b48e80 | 0x02228e80 | Bool serializer | vtable[0x58] wrapper | ✓ |
| FUN_01b497f0 | 0x022297f0 | 1-byte dispatcher | Bool/byte read/write | ✓ |
| FUN_01b48be0 | 0x02228be0 | uint64 serializer | vtable[0x7c] wrapper | ✓ |
| FUN_01b496d0 | 0x022296d0 | 8-byte dispatcher | uint64 read/write | ✓ |
| FUN_01b6f4e0 | 0x0224f4e0 | Core 8-byte write | inner_vtable[0x30] | ✓ |
| FUN_01b48bc0 | 0x02228bc0 | uint32 serializer | vtable[0x84] wrapper | ✓ |
| FUN_01b49610 | 0x02229610 | 4-byte dispatcher | counter + mode dispatch | ✓ |
| FUN_01b6f4d0 | 0x0224f4d0 | Core 4-byte write wrapper | inner_vtable[0x34] | ✓ |
| FUN_01b091a0 | 0x021e91a0 | Dynamic properties processor | Called by finalization | ✓ |

### VTable Serializer Thunks (at 0x02555c60)

| Offset | Ghidra | WinDbg | Purpose | Traced |
|--------|--------|--------|---------|--------|
| 0x08 | LAB_01b48770 | 0x02228770 | StartElement (NO-OP WRITE) | ✓ |
| 0x0c | FUN_01b48890 | 0x02228890 | OpenSection | ✓ |
| 0x10 | LAB_01b487a0 | 0x022287a0 | EndElement (NO-OP WRITE) | ✓ |
| 0x14 | FUN_01b48920 | 0x02228920 | CloseSection | ✓ |
| 0x40 | FUN_01b48a30 | 0x02228a30 | Array/block serializer | Ghidra |
| 0x44 | FUN_01b49300 | 0x02229300 | wstring serializer | Ghidra |
| 0x48 | FUN_01b492f0 | 0x022292f0 | string serializer | Ghidra |
| 0x4c | FUN_01b49020 | 0x02229020 | 8-byte + type name | ✓ |
| 0x50 | FUN_01b48fb0 | 0x02228fb0 | TypeInfo serializer | ✓ |
| 0x54 | FUN_01b48e90 | 0x02228e90 | String serializer | ✓ |
| 0x58 | FUN_01b48e80 | 0x02228e80 | Bool serializer | ✓ |
| 0x5c | FUN_01b48e00 | 0x02228e00 | vec4/float4 (16 bytes) | Ghidra |
| 0x60 | FUN_01b48d60 | 0x02228d60 | mat4x4 (64 bytes) | Ghidra |
| 0x64 | FUN_01b49140 | 0x02229140 | mat3x3 (36 bytes) | Ghidra |
| 0x68 | FUN_01b48cf0 | 0x02228cf0 | quat/vec4 (16 bytes) | Ghidra |
| 0x6c | FUN_01b48c80 | 0x02228c80 | vec3 (12 bytes) | Ghidra |
| 0x70 | FUN_01b48c10 | 0x02228c10 | vec2 (8 bytes) | Ghidra |
| 0x74 | FUN_01b48c00 | 0x02228c00 | float32 (4 bytes) | Ghidra |
| 0x78 | FUN_01b48bf0 | 0x02228bf0 | float64/double (8 bytes) | Ghidra |
| 0x7c | FUN_01b48be0 | 0x02228be0 | uint64 (8 bytes) | ✓ |
| 0x80 | FUN_01b48bd0 | 0x02228bd0 | int32 (4 bytes) | Ghidra |
| 0x84 | FUN_01b48bc0 | 0x02228bc0 | uint32 (4 bytes) | ✓ |
| 0x88 | FUN_01b48bb0 | 0x02228bb0 | uint16 (2 bytes) | Ghidra |
| 0x8c | FUN_01b48ba0 | 0x02228ba0 | int16 (2 bytes) | Ghidra |
| 0x90 | FUN_01b48b90 | 0x02228b90 | uint8 (1 byte) | Ghidra |
| 0x94 | FUN_01b48b80 | 0x02228b80 | int8 (1 byte) | Ghidra |
| 0x98 | FUN_01b48b70 | 0x02228b70 | WriteByte | ✓ |
| 0x9c | FUN_01b48e70 | 0x02228e70 | uint32 (ObjectID) | ✓ |

### Core I/O Dispatcher Functions

| Ghidra | WinDbg | Function | Purpose | Traced |
|--------|--------|----------|---------|--------|
| FUN_01b49430 | 0x02229430 | 1-byte dispatcher | Mode check + vtable call | ✓ |
| FUN_01b49610 | 0x02229610 | 4-byte dispatcher | Mode check + vtable call | ✓ |
| FUN_01b496d0 | 0x022296d0 | 8-byte dispatcher | Mode check + vtable call | ✓ |

### Core Stream I/O Functions

| Ghidra | WinDbg | Function | Purpose | Traced |
|--------|--------|----------|---------|--------|
| FUN_01b6f370 | 0x0224f370 | Core 1-byte write | `*buffer++ = byte` | ✓ |
| FUN_01b6f150 | 0x0224f150 | Core 1-byte read | `byte = *buffer++` | Ghidra verified |
| FUN_01b6f400 | 0x0224f400 | Core 2-byte read | `val = *(uint16*)buffer` | Ghidra verified |
| FUN_01b6fe40 | 0x0224fe40 | Core 2-byte write | `*(uint16*)buffer = val` | Ghidra verified |
| FUN_01b6f440 | 0x0224f440 | Core 4-byte read | `val = *(uint32*)buffer` | ✓ |
| FUN_01b6f490 | 0x0224f490 | Core 8-byte read | `val = *(uint64*)buffer` | ✓ |
| FUN_01b6fea0 | 0x0224fea0 | Core 4-byte write | `*(uint32*)buffer = val` | ✓ |
| FUN_01b6f4e0 | 0x0224f4e0 | Core 8-byte write | `*(uint64*)buffer = val` via FUN_01b6ff10 | ✓ |
| FUN_01b6f030 | 0x0224f030 | Core N-byte read | `memcpy(dest, buffer, n)` | Ghidra verified |
| FUN_01b6f3b0 | 0x0224f3b0 | Core N-byte write | `memcpy(buffer, src, n)` | Ghidra verified |

### Seek/Position Functions

| Ghidra | WinDbg | Function | Purpose | Traced |
|--------|--------|----------|---------|--------|
| FUN_01b6f090 | 0x0224f090 | Seek + Save | Save pos, seek to token | Ghidra verified |
| LAB_01b6f0b0 | 0x0224f0b0 | Restore Position | Restore saved position | Ghidra verified |
| FUN_01b6f2b0 | 0x0224f2b0 | Skip N bytes | `buffer += n` | Ghidra verified |
| FUN_01b6f080 | 0x0224f080 | Rewind N bytes | `buffer -= n` | Ghidra verified |
| FUN_01b6f880 | 0x0224f880 | Finalize | Cleanup/deallocation | Ghidra verified |

### Stream Utility Functions

| Ghidra | WinDbg | Function | Purpose | Traced |
|--------|--------|----------|---------|--------|
| FUN_01b701c0 | 0x0225f1c0 | Destructor | Cleanup + optional free | Ghidra verified |
| LAB_01b6efe0 | 0x0224efe0 | Stub | Return false | Ghidra verified |
| FUN_01b6eff0 | 0x0224eff0 | Reset state | Clear flags | Ghidra verified |
| LAB_01b6f010 | 0x0224f010 | IsAtEnd | Check if buffer full | Ghidra verified |
| FUN_01b8a020 | 0x0226a020 | Get bounds | Get buffer base/limit | Ghidra verified |
| FUN_01b6f0c0 | 0x0224f0c0 | Calc remaining | offset - param | Ghidra verified |
| LAB_01b6f120 | 0x0224f120 | Get flag | Return flags & 1 | Ghidra verified |

### Functions NOT Yet Traced

| Ghidra | Purpose | Priority |
|--------|---------|----------|
| FUN_01b0d500 | Single byte writer wrapper | Low (understood) |
| FUN_01b48e00 | Unknown vtable[0x5c] | Low |
| FUN_01b48d60 | Unknown vtable[0x60] | Low |
| FUN_01b49140 | Unknown vtable[0x64] | Low |

---

## Complete WRITE Path Flow (Summary)

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

**WRITE Path Status:** ✓ COMPLETE
All WRITE path serialization has been traced:
- Header (0x00-0x19)
- Base class property (0x1a-0x2a)
- 5 bool properties (0x2b-0x95)
- 1 uint64 property (0x96-0x9d)
- Dynamic Properties section (0x9e-0xa1) - trailing 4 zeros

**Key addresses for WRITE path:**
- FUN_01b08ce0 (header writer): 0x021e8ce0
- FUN_01b0d500 (byte writer): 0x021ed500
- FUN_01b09650 (bool property serializer): 0x021e9650
- FUN_01b11fb0 (property value writer): 0x021f1fb0
- FUN_01b0d140 (property header writer): 0x021ed140
- FUN_01b0e680 (property hash writer): 0x021ee680
- FUN_01b0e980 (type info writer): 0x021ee980
- FUN_01b49020 (8-byte serializer): 0x02229020
- FUN_01b48e80 (bool serializer vtable[0x58]): 0x02228e80
- FUN_01b497f0 (1-byte dispatcher): 0x022297f0
- FUN_01b48be0 (uint64 serializer vtable[0x7c]): 0x02228be0
- FUN_01b496d0 (8-byte dispatcher): 0x022296d0
- FUN_01b6f370 (core byte write): 0x0224f370
- FUN_01b6fea0 (core 4-byte write): 0x0224fea0
- FUN_01b6f4e0 (core 8-byte write): 0x0224f4e0
- FUN_01b48bc0 (uint32 serializer vtable[0x84]): 0x02228bc0
- FUN_01b49610 (4-byte dispatcher): 0x02229610
- FUN_01b6f4d0 (4-byte write wrapper): 0x0224f4d0
- FUN_01b0d0c0 (finalization): 0x021ed0c0
- FUN_01b48890 (OpenSection): 0x02228890
- FUN_01b48920 (CloseSection): 0x02228920

**Key Discoveries from WRITE Path Trace:**
- WRITE mode byte: `[serializer+4]+4 = 0x00`
- StartElement/EndElement are NO-OPs in WRITE mode (just `RET 4`)
- Serializer version: `[context+0x24] = 0x10` (16) - determines legacy vs current format

**Stream Inner VTable Summary (at 0x02c36168):**
| Size | READ Offset | READ Function | WRITE Offset | WRITE Function |
|------|-------------|---------------|--------------|----------------|
| 1 byte | 0x24 | FUN_01b6f150 | 0x3c | FUN_01b6f370 |
| 2 bytes | 0x20 | FUN_01b6f400 | 0x38 | FUN_01b6fe40 |
| 4 bytes | 0x1c | FUN_01b6f440 | 0x34 | FUN_01b6fea0 |
| 8 bytes | 0x18 | FUN_01b6f490 | 0x30 | FUN_01b6f4e0 |
| N bytes | 0x28 | FUN_01b6f030 | 0x40 | FUN_01b6f3b0 |
- Core byte write: FUN_01b6f370 - `*buffer_ptr++ = byte`
- Core 4-byte write: FUN_01b6fea0 - `*buffer_ptr = value; buffer_ptr += 4`
- Endianness swap supported in 4-byte write
- String serializer: length (4 bytes) + data (N bytes)
- Structured header at 0x00-0x09: NOT padding, but NbClassVersionsInfo + ObjectName + ObjectID + InstancingMode
- The 0x0b at offset 0x26 is the base class property FLAGS BYTE, written by FUN_01b076f0
