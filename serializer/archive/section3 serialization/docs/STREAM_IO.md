# Stream I/O Functions

**Extracted from:** [SECTION3_SERIALIZATION.md](SECTION3_SERIALIZATION.md)

These functions implement low-level stream read/write operations for the serialization system. All functions operate on a stream object with the following memory layout:

**Stream Object Memory Layout:**
- `[stream + 0x04]` = flags (bit 0: endianness swap)
- `[stream + 0x14]` = buffer base address
- `[stream + 0x18]` = current position (absolute pointer)
- `[stream + 0x1c]` = buffer capacity
- `[stream + 0x2c]` = saved offset (for position restore)
- `[stream + 0x30]` = expansion enabled flag

**Core pattern:** All functions read/write at `[stream+0x18]` and advance position by N bytes.

---

## FUN_01b6f030 - N-byte Read (inner_vtable[0x28])

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

## FUN_01b6f3b0 - N-byte Write (inner_vtable[0x40])

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

## FUN_01b6f150 - 1-byte Read (inner_vtable[0x24])

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

## FUN_01b6f090 - Seek + Save Position (inner_vtable[0x50])

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

## LAB_01b6f0b0 - Restore Position (inner_vtable[0x58])

> Assembly: See DISASSEMBLY.md - LAB_01b6f0b0 - Restore Position

**Ghidra Address:** 0x01b6f0b0 (WinDbg: 0x0224f0b0)
**Status:** Ghidra static analysis (used by CloseSection after backpatching)

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

## FUN_01b6f880 - Finalize (inner_vtable[0x54])

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

## FUN_01b6f400 - 2-byte Read (inner_vtable[0x20])

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

## FUN_01b6f4c0 / FUN_01b6fe40 - 2-byte Write (inner_vtable[0x38])

**Ghidra Address:** 0x01b6f4c0 -> 0x01b6fe40 (WinDbg: 0x0224f4c0 -> 0x0224fe40)
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

## FUN_01b6f2b0 - Skip N Bytes (inner_vtable[0x44])

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

## FUN_01b6f080 - Rewind N Bytes (inner_vtable[0x48])

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

## LAB_01b6f010 - IsAtEnd (inner_vtable[0x0c])

> Assembly: See DISASSEMBLY.md - LAB_01b6f010 - IsAtEnd

**Ghidra Address:** 0x01b6f010 (WinDbg: 0x0224f010)
**Status:** Ghidra static analysis

**Equivalent C:**
```c
bool __thiscall LAB_01b6f010(int param_1) {
    int used = *(int *)(param_1 + 0x18) - *(int *)(param_1 + 0x14);
    int capacity = *(int *)(param_1 + 0x1c);
    return (used == capacity);  // true if buffer is full/at end
}
```

---

## FUN_01b6f0c0 - Calculate Remaining (inner_vtable[0x5c])

**Ghidra Address:** 0x01b6f0c0 (WinDbg: 0x0224f0c0)
**Status:** Ghidra static analysis

```c
int __thiscall FUN_01b6f0c0(int param_1, int *param_2) {
    // Returns: current_offset - *param_2
    return (*(int *)(param_1 + 0x18) - *(int *)(param_1 + 0x14)) - *param_2;
}
```

**Purpose:** Calculate bytes remaining or offset difference.
