# Execution Traces - Section 3 Serialization

This file contains verbose execution traces extracted from SECTION3_SERIALIZATION.md for reference.
These traces include TTD positions, memory addresses, register states, and WinDbg command output
from Time Travel Debugging analysis of Assassin's Creed Brotherhood save file serialization.

**Source File:** SECTION3_SERIALIZATION.md
**TTD Trace File:** OPTIONS.WINDBGTRACE
**Module Base:** ACBSP = 0x00ae0000

---

## Table of Contents

- [FUN_01710580 Entry Traces](#fun_01710580---assassinsingleprofiledataserialize)
- [FUN_01b6f440 Stream Read Trace](#fun_01b6f440---actual-4-byte-read-trace)
- [Bool Property Read Trace](#bool-property-read-trace)
- [CloseSection Backpatch Traces](#closesection-backpatch-traces)
- [VTable Discovery Trace](#vtable-address-discovery)
- [Property Header Write Traces](#property-header-write-traces)
- [Bool Value Write Trace](#bool-value-write-trace)
- [uint64 Value Write Trace](#uint64-value-write-trace)
- [uint32 Write Trace (Base Class Field)](#uint32-write-trace-base-class-field)
- [Dynamic Properties Finalization Trace](#dynamic-properties-finalization-trace)

---

## FUN_01710580 - AssassinSingleProfileData::Serialize

### Entry Point Context

**TTD Position:** B1F2B:920

**Registers on Entry:**
- ECX (param_1/this) = 0xf74c0a50 (AssassinSingleProfileData object)
- [esp+4] (param_2) = 0x03cff870 (serializer context)

**Serializer Context Structure at 0x03cff870:**
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

**Mode Check Trace:**
```
cmp byte ptr [eax+4], 0    ; [0x0a3a06b4] = 0x01
jne (skip header write)    ; 0x01 != 0, so READ mode
```
- Mode 0x00 = WRITE mode (writes headers)
- Mode 0x01 = READ mode (skips header write)

---

## FUN_01b12fa0 - Property Serialization Core Trace

**TTD Position:** B1F2B (during property read)

**Property Metadata at 0x02eccf90:**
```
02eccf90: 02000001 bf4c2013 00000000 00070000
          flags    hash
02eccfa0: 00100007 ...
```
- Hash 0xbf4c2013 = SaveGameDataObject base class field

---

## FUN_01b6f440 - Actual 4-Byte Read Trace

**TTD Position:** B1F2B:B7B

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

## Bool Property Read Trace

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

**Traced Result (FUN_01b497f0):**
- Buffer position: 0x0a3a063c
- Data at buffer: 0x01
- Field before: 0x00
- Field after: 0x01 (true)

---

## uint64 Property Read Trace

**TTD Position:** B1F2B:1643

**Parameters:**
- [esp+4] = field pointer (0xf74c0a68 for uint64_field_0x18)
- [esp+8] = property metadata (0x030532d0)

**Property Metadata at 0x030532d0:**
```
030532d0: 02000001 496f8780 00000000 00090000
          flags    hash=0x496f8780 (uint64_field_0x18)
```

---

## CloseSection Backpatch Traces

**FUN_01b48920 - CloseSection Mechanism**
**TTD Position:** E68A19:CBB (for CloseSection("Property"))

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

**Confirmed via memory breakpoint at READ B1F2B:B38 and WRITE E68A19:C3E:**
- The 0x0b is read/written as part of SaveGameDataObject::Serialize base class handling
- Call chain: FUN_01b0a1f0 -> FUN_01b12fa0 -> FUN_01b076f0 -> FUN_01b6f150/FUN_01b6f370

---

## VTable Address Discovery

**WRITE path trace at E68A19:270:**
```
esi = 0x04660698 (stream object)
[esi] = 0x02c36168 (inner vtable pointer)
[0x02c36168+0x34] = 0x0224f4d0 (WinDbg) = FUN_01b6f4d0 (Ghidra)
```

---

## Property Header Write Traces

### FUN_01b0e680 - Property Hash Writer Trace

**TTD Position:** E68A1B:264

**Traced Call (first bool property):**
```
Parameters:
  ECX (this) = 0x24d476e0 (serializer context)
  param_2 = 0x02c34cbc -> "Name" (tag string)
  param_3 = 0x00000000 (unused)
  param_4 = 0x07a8f698 -> 0x3b546966 (property hash)

Call chain:
  E68A1B:26D  vtable[0x08] = 0x02228770 (FUN_01b48770) - StartElement("Name") [NO-OP]
  E68A1B:276  vtable[0x50] = 0x02228fb0 (FUN_01b48fb0) - Write hash
              --> FUN_01b49610 -> FUN_01b6fea0 (core 4-byte write)
  E68A1B:2BF  vtable[0x10] = 0x022287a0 (FUN_01b487a0) - EndElement("Name") [NO-OP]

Buffer: 0x0466002b -> 0x0466002f (4 bytes written)
```

### FUN_01b0e980 - Type Info Writer Trace

**TTD Position:** E68A1B:2D0

**Traced Call (first bool property):**
```
Parameters:
  ECX (this) = 0x07a8f7d4 (serialization context)
  param_2 = 0x07a8f690 -> [0x00000000, 0x00000000] (type_info for bool)

Version check:
  [ECX + 0x24] = 0x10 (16 decimal) - >= 9, takes CURRENT PATH

Call chain:
  E68A1B:2E1  vtable[0x08] = 0x02228770 (FUN_01b48770) - StartElement("Type") [NO-OP]
  E68A1B:2E9  vtable[0x4c] = 0x02229020 (FUN_01b49020) - 8-byte handler
              --> Checks [serializer+0x1012] = 0 -> simple path
              --> FUN_01b496d0 -> FUN_01b6f4e0 -> FUN_01b6ff10 (core 8-byte write)
  E68A1B:338  vtable[0x10] = 0x022287a0 (FUN_01b487a0) - EndElement("Type") [NO-OP]

Tag strings:
  0x02c34cb0 -> "Type"
  0x02cd9b50 -> format specifier (appears empty/null)
```

### FUN_01b48fb0 - TypeInfo Serializer Trace

**TTD Position:** E68A19:2FA (entry)

**Parameters:**
- ECX (this) = 0x24d476e0 (serializer context)
- [ebp+8] = param_2 = 0x02c1ddec (metadata pointer)
- [ebp+0xC] = param_3 = 0x07a8f6cc -> **0xc9876d66** (type hash)

**Key Finding:**
- Flag at `[serializer+0x1012]` = **0x00** means NO type name string is written
- Only the 4-byte type hash (0xc9876d66) is written at offset 0x0a

### FUN_01b49610 - 4-Byte Write Dispatcher Trace

**TTD Position:** E68A19:305 (called from FUN_01b48fb0)

**Parameters:**
- ECX = 0x24d476e0 (serializer context)
- [ebp+8] = 0x07a8f6cc -> **0xc9876d66** (type hash value)

**Key Observations:**
1. Counter at `[ecx+0x1010]` = 0x0000 -> counter tracking disabled, skip to I/O
2. Mode at `[ecx+0x4]` = 0x00 -> WRITE mode
3. Stream object at `[ecx+0x8]` used for actual I/O
4. WRITE path dereferences the pointer to get actual value before calling write function
5. Calls `inner_vtable[0x34]` = FUN_01b6f4d0 (thunk) -> FUN_01b6fea0 (core write)

**Serializer Context Structure (confirmed):**
| Offset | Value | Purpose |
|--------|-------|---------|
| +0x00 | vtable | Serializer mode vtable |
| +0x04 | 0x00 | Mode (0=WRITE, 1=READ) |
| +0x08 | stream_obj | Stream object pointer |
| +0x1010 | 0x0000 | Counter tracking flag |
| +0x1012 | 0x00 | TypeInfo string flag |

---

## Bool Value Write Trace

### FUN_01b497f0 - 1-Byte Dispatcher

**TTD Position:** E68A1B:415

**Traced Call (first bool property value):**
```
Parameters:
  ECX (this) = 0x24d476e0 (serializer context)
  param_2 = 0xf74c08b8 -> 0x01 (bool value = true)

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
  --> FUN_01b497f0 (1-byte dispatcher)
        |--> Counter: [serializer+0x1010] = 3, increments [serializer+0x20]
        |--> Mode: [serializer+4] = 0 (WRITE)
        |--> Stream: [serializer+8] = 0x07a8f854
        --> inner_vtable[0x3c] = FUN_01b6f370 (core 1-byte write)
              --> *buffer++ = 0x01
```

---

## uint64 Value Write Trace

### FUN_01b496d0 - 8-Byte Dispatcher

**TTD Position:** E68A1D:3F2

**Traced Call (uint64 property value):**
```
Parameters:
  ECX (this) = 0x24d476e0 (serializer context)
  param_2 = 0xf74c08b0 -> [0x00000000, 0x00000000] (uint64 = 0)

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
  --> FUN_01b496d0 (8-byte dispatcher)
        |--> Counter: [serializer+0x1010] = 3, adds 8 to [serializer+0x20]
        |--> Mode: [serializer+4] = 0 (WRITE)
        |--> Stream: [serializer+8] = 0x07a8f854
        |--> Load value as two dwords: low=[param], high=[param+4]
        --> inner_vtable[0x30] = FUN_01b6f4e0 (core 8-byte write)
              --> Writes 8 bytes to buffer
```

---

## uint32 Write Trace (Base Class Field)

### vtable[0x84] - uint32 Serializer

**TTD Position:** E68A19:C6B -> E68A19:CA2
**Value Written:** 0x00000000 (base class field value at offset 0x27)

**Call Chain:**
```
FUN_01b48bc0 (vtable[0x84]) @ 0x02228bc0
  | Thin wrapper - just jmp to dispatcher
  --> jmp FUN_01b49610 @ 0x02229610 (4-byte dispatcher)
        |
        |--> Counter check: [ecx+0x1010] = 3 (active)
        |--> Counter increment: [ecx+3*8+8] += 4 (0x0D -> 0x11)
        |--> Mode check: [ecx+4] = 0 (WRITE)
        |--> Stream: [ecx+8] = 0x07a8f854
        |--> Load value: [param] = 0x00000000
        --> inner_vtable[0x34] = FUN_01b6f4d0 @ 0x0224f4d0
              |
              --> call FUN_01b6fea0 @ 0x0224fea0 (core 4-byte write)
                    |
                    |--> Stream: esi = 0x07a8f854
                    |--> [esi+0x14] = 0x04660000 (buffer base)
                    |--> [esi+0x18] = 0x04660027 (write position)
                    |--> [esi+0x1C] = 0x00001000 (buffer size)
                    |--> Bounds check: (0x27 + 4 = 0x2B) <= 0x1000
                    |--> WRITE: mov dword ptr [0x04660027], 0x00000000
                    --> Update position: [esi+0x18] += 4 -> 0x0466002B
```

---

## Dynamic Properties Finalization Trace

### FUN_01b0d0c0 - Finalization

**TTD Position:** E68A1D:CE1 -> E68A1D:F9D
**Purpose:** Writes Dynamic Properties section (trailing 4 zeros at offset 0x9e)

**Call Chain:**
```
FUN_01b0d0c0 @ 0x021ed0c0 (finalization)
  |
  |--> Early exit check: [context+0x58] and [context+0x20]
  |   (First call at E68A1B:A5 took early exit - NO-OP)
  |
  --> Main path (second invocation):
        |
        |--> E68A1D:CE1: call vtable[0x0c] = OpenSection("Dynamic Properties")
        |   push 0x02c34e58  ; "Dynamic Properties" string
        |   call 0x02228890  ; FUN_01b48890 (OpenSection)
        |
        |--> E68A1D:E26: call FUN_01b091a0 (process dynamic properties)
        |   (No properties to write in this save)
        |
        --> E68A1D:F5F: call vtable[0x14] = CloseSection("Dynamic Properties")
              push 0x02c34e58  ; "Dynamic Properties" string
              call 0x02228920  ; FUN_01b48920 (CloseSection)
                    |
                    |--> Mode check: [esi+4] = 0 (WRITE)
                    |--> Counter: [esi+0x1010] = 2, decremented to 1
                    |--> Size value: [esi+2*8+8] = 0x00000000
                    --> inner_vtable[0x34] -> FUN_01b6fea0
                          |
                          --> WRITE: mov dword ptr [0x0466009e], 0x00000000
                              Position update: 0x9e -> 0xa2
```

**String at 0x02c34e58:** "Dynamic Properties"

---

## Property Descriptor Raw Hex Dumps

**From Ghidra static analysis:**

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

---

## Traced Property Example (bool_field_0x20)

**TTD Position:** E68A1B:25B

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

## Session Information

**Last TTD Position:** E68A1D:F9D
**Location:** Completed FUN_01b0d0c0 finalization

**WRITE Path Verified Offsets:**
- Header (0x00-0x19)
- Base class property (0x1a-0x2a)
- 5 bool properties (0x2b-0x95)
- 1 uint64 property (0x96-0x9d)
- Dynamic Properties section (0x9e-0xa1) - trailing 4 zeros
