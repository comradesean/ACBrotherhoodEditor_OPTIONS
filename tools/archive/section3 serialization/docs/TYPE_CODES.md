# Type Codes Reference

Type codes are stored at byte index 6 of the 8-byte `type_info` field.

## Confirmed Types (Traced)

| Type | Code | type_info | Value Size | Traced |
|------|------|-----------|------------|--------|
| bool | 0x00 | `0000000000000000` | 1 byte | Yes |
| uint32 | 0x07 | `0000000000000700` | 4 bytes | Yes |
| uint64 | 0x09 | `0000000000000900` | 8 bytes | Yes |

## Speculative Types (From Ghidra Analysis)

| Type | Code | type_info | Value Size |
|------|------|-----------|------------|
| int8 | 0x01 | `0000000000000100` | 1 byte |
| uint8 | 0x02 | `0000000000000200` | 1 byte |
| int16 | 0x03 | `0000000000000300` | 2 bytes |
| uint16 | 0x04 | `0000000000000400` | 2 bytes |
| int32 | 0x05 | `0000000000000500` | 4 bytes |
| int64 | 0x08 | `0000000000000800` | 8 bytes |
| float32 | 0x0A | `0000000000000a00` | 4 bytes |
| float64 | 0x0B | `0000000000000b00` | 8 bytes |
| vec2 | 0x0C | `0000000000000c00` | 8 bytes (2x float32) |
| vec3 | 0x0D | `0000000000000d00` | 12 bytes (3x float32) |
| vec4 | 0x0E | `0000000000000e00` | 16 bytes (4x float32) |
| quat | 0x0F | `0000000000000f00` | 16 bytes (4x float32) |
| mat3x3 | 0x10 | `0000000000001000` | 36 bytes (9x float32) |
| mat4x4 | 0x11 | `0000000000001100` | 64 bytes (16x float32) |

## type_info Structure

```
Bytes:  [0] [1] [2] [3] [4] [5] [6] [7]
         00  00  00  00  00  00  XX  00
                                 ^
                                 Type code at byte index 6
```

**Extraction:** `type_code = type_info[6] & 0x3F`

## VTable Dispatch (Property Serializers)

| Type | vtable offset | Function |
|------|---------------|----------|
| bool | 0x58 | FUN_01b48e80 |
| uint32 | 0x84 | (thunk to FUN_01b49610) |
| uint64 | 0x7c | FUN_01b48be0 |

## Source

Type codes derived from:
- WinDbg TTD traces (bool, uint32, uint64 confirmed)
- Ghidra vtable analysis at 0x02555c60
- PropertyDescriptor structures (DAT_02973250, etc.)

See [PROPERTY_DESCRIPTORS.md](PROPERTY_DESCRIPTORS.md) for raw hex dumps of property descriptors containing type_info values.
