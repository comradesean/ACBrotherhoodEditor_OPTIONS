# Section 3 JSON Format

## type_info

8-byte field (16 hex chars). Type code at byte index 6.

| Type    | type_info          | Confirmed |
|---------|--------------------|-----------|
| bool    | `0000000000000000` | Yes       |
| int8    | `0000000000000100` | No        |
| uint8   | `0000000000000200` | No        |
| int16   | `0000000000000300` | No        |
| uint16  | `0000000000000400` | No        |
| int32   | `0000000000000500` | No        |
| uint32  | `0000000000000700` | Yes       |
| int64   | `0000000000000800` | No        |
| uint64  | `0000000000000900` | Yes       |
| float32 | `0000000000000a00` | No        |
| float64 | `0000000000000b00` | No        |
| vec2    | `0000000000000c00` | No        |
| vec3    | `0000000000000d00` | No        |
| vec4    | `0000000000000e00` | No        |
| quat    | `0000000000000f00` | No        |
| mat3x3  | `0000000000001000` | No        |
| mat4x4  | `0000000000001100` | No        |

## flags

Always `0x0b` in traced files. Meaning:
- Bit 0 (Final) = 1
- Bit 1 (Owned) = 1
- Bit 3 = 1

## Computed Fields (not in JSON)

These are calculated during serialization:
- Section sizes (object, properties, base_class)
- Property sizes
- File offsets

## Value Encoding

- `bool`: JSON boolean
- Integers: JSON number
- Floats: JSON number
- Vectors: JSON array of numbers
- Matrices: JSON array of arrays
