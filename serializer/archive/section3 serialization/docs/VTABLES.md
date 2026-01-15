# VTable Reference

> This file contains the VTable reference extracted from [SECTION3_SERIALIZATION.md](SECTION3_SERIALIZATION.md).
> It documents the serializer mode and stream inner VTables used for binary serialization.

---

## VTable Reference (Complete)

### Serializer Mode VTable at PTR_FUN_02555c60 (Ghidra) / 0x02c35c60 (WinDbg)

Accessed via: `mov eax, [edi+4]; mov eax, [eax]; call [eax+offset]`

**Legend:** ✓ = Traced, ○ = Ghidra verified, ? = Inferred

| Off | Function | Purpose | S |
|-----|----------|---------|---|
| 0x00 | FUN_01b49b10 | Destructor | ○ |
| 0x04 | FUN_01b48830 | Get buffer bounds → inner[0x10] | ○ |
| 0x08 | LAB_01b48770 | StartElement (NO-OP WRITE) | ✓ |
| 0x0c | FUN_01b48890 | OpenSection | ✓ |
| 0x10 | LAB_01b487a0 | EndElement (NO-OP WRITE) | ✓ |
| 0x14 | FUN_01b48920 | CloseSection | ✓ |
| 0x18 | FUN_01b489b0 | Pop section (counter--, skip) | ○ |
| 0x1c | LAB_01b48a10 | Check section counter ≤ 0 | ○ |
| 0x20 | LAB_01b48780 | Get section counter | ○ |
| 0x24 | FUN_01b487b0 | Push position → inner[0x4c] | ○ |
| 0x28 | FUN_01b487e0 | Seek to saved position → inner[0x50] | ○ |
| 0x2c | FUN_01b48800 | Calc remaining → inner[0x5c] | ○ |
| 0x30 | FUN_01b48700 | Restore all + get bounds | ○ |
| 0x34 | FUN_01b48760 | Reset stream → inner[0x08] | ○ |
| 0x38 | LAB_01b48820 | Flush → inner[0x68] | ○ |
| 0x3c | FUN_01b48b10 | Position stack read/write | ○ |
| 0x40 | FUN_01b48a30 | Array/block serializer (N-byte + swap) | ○ |
| 0x44 | FUN_01b49300 | wstring serializer → FUN_01b49b40 | ○ |
| 0x48 | FUN_01b492f0 | string serializer → FUN_01b49920 | ○ |
| 0x4c | FUN_01b49020 | 8-byte + optional type name → FUN_01b496d0 | ○ |
| 0x50 | FUN_01b48fb0 | TypeInfo serializer | ✓ |
| 0x54 | FUN_01b48e90 | String serializer | ○ |
| 0x58 | FUN_01b48e80 | Bool serializer → FUN_01b49430 | ✓ |
| 0x5c | FUN_01b48e00 | vec4/float4 (16B) → 4× inner[0x34] | ○ |
| 0x60 | FUN_01b48d60 | mat4x4 (64B) → 16× inner[0x34] | ○ |
| 0x64 | FUN_01b49140 | mat3x3 (36B) → 9× inner[0x34] | ○ |
| 0x68 | FUN_01b48cf0 | quat/vec4 (16B) → 4× inner[0x34] | ○ |
| 0x6c | FUN_01b48c80 | vec3 (12B) → 3× inner[0x34] | ○ |
| 0x70 | FUN_01b48c10 | vec2 (8B) → 2× inner[0x34] | ○ |
| 0x74 | FUN_01b48c00 | float32 (4B) → FUN_01b49790 | ○ |
| 0x78 | FUN_01b48bf0 | float64/double (8B) → FUN_01b49730 | ○ |
| 0x7c | FUN_01b48be0 | uint64 (8B) → FUN_01b496d0 | ✓ |
| 0x80 | FUN_01b48bd0 | int32 (4B) → FUN_01b49670 | ○ |
| 0x84 | FUN_01b48bc0 | uint32 (4B) → FUN_01b49610 | ○ |
| 0x88 | FUN_01b48bb0 | uint16 (2B) → FUN_01b495b0 | ○ |
| 0x8c | FUN_01b48ba0 | int16 (2B) → FUN_01b49550 | ○ |
| 0x90 | FUN_01b48b90 | uint8 (1B) → FUN_01b494f0 | ○ |
| 0x94 | FUN_01b48b80 | int8 (1B) → FUN_01b49490 | ○ |
| 0x98 | FUN_01b48b70 | WriteByte → FUN_01b49430 | ✓ |
| 0x9c | FUN_01b48e70 | uint32 serializer (ObjectID) → FUN_01b49610 | ✓ |

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

Accessed via: `mov ecx, [param_1+8]; mov eax, [ecx]; call [eax+offset]`

> Trace: See TRACES.md - VTable Address Discovery (stream object 0x04660698, inner vtable 0x02c36168)

| Off | [i] | Purpose | READ | WRITE | S |
|-----|-----|---------|------|-------|---|
| 0x00 | 0 | Destructor | FUN_01b701c0 | FUN_01b701c0 | ○ |
| 0x04 | 1 | Stub (ret false) | LAB_01b6efe0 | LAB_01b6efe0 | ○ |
| 0x08 | 2 | Reset state | FUN_01b6eff0 | FUN_01b6eff0 | ○ |
| 0x0c | 3 | IsAtEnd | LAB_01b6f010 | LAB_01b6f010 | ○ |
| 0x10 | 4 | Get buffer bounds | FUN_01b8a020 | FUN_01b8a020 | ○ |
| 0x14 | 5 | Alloc + read ptr | FUN_01b6f300 | - | ○ |
| 0x18 | 6 | 8-byte r/w | FUN_01b6f490 | - | ✓ |
| 0x1c | 7 | 4-byte r/w | FUN_01b6f440 | - | ✓ |
| 0x20 | 8 | 2-byte read | FUN_01b6f400 | - | ○ |
| 0x24 | 9 | 1-byte read | FUN_01b6f150 | - | ○ |
| 0x28 | 10 | N-byte read | FUN_01b6f030 | - | ○ |
| 0x2c | 11 | Thunk to [13] | FUN_01b6f100 | - | ○ |
| 0x30 | 12 | 8-byte write | - | FUN_01b6f4e0→FUN_01b6ff10 | ✓ |
| 0x34 | 13 | 4-byte write | - | FUN_01b6f4d0→FUN_01b6fea0 | ✓ |
| 0x38 | 14 | 2-byte write | - | FUN_01b6f4c0→FUN_01b6fe40 | ○ |
| 0x3c | 15 | 1-byte write | - | FUN_01b6f370 | ✓ |
| 0x40 | 16 | N-byte write | - | FUN_01b6f3b0 | ○ |
| 0x44 | 17 | Skip N bytes | FUN_01b6f2b0 | FUN_01b6f2b0 | ○ |
| 0x48 | 18 | Rewind N bytes | FUN_01b6f080 | FUN_01b6f080 | ○ |
| 0x4c | 19 | Tell (get pos) | LAB_01b6f4f0 | LAB_01b6f4f0 | ○ |
| 0x50 | 20 | Seek + Save | FUN_01b6f090 | FUN_01b6f090 | ○ |
| 0x54 | 21 | Finalize | FUN_01b6f880 | FUN_01b6f880 | ○ |
| 0x58 | 22 | Restore Position | LAB_01b6f0b0 | LAB_01b6f0b0 | ○ |
| 0x5c | 23 | Calc remaining | FUN_01b6f0c0 | FUN_01b6f0c0 | ○ |
| 0x60 | 24 | NOP | LAB_01b6f0e0 | LAB_01b6f0e0 | ○ |
| 0x64 | 25 | NOP | LAB_01b6f0f0 | LAB_01b6f0f0 | ○ |
| 0x68 | 26 | Flush buffer | LAB_01b6f6e0 | LAB_01b6f6e0 | ○ |
| 0x6c | 27 | Get flag & 1 | LAB_01b6f120 | LAB_01b6f120 | ○ |

**FUN_01b6f4d0 (vtable[0x34]) - Thunk to FUN_01b6fea0:**
```c
void FUN_01b6f4d0(void)
{
    FUN_01b6fea0(&stack0x00000004);
    return;
}
```
This is a simple thunk that passes the stack parameter to the actual 4-byte write function.
