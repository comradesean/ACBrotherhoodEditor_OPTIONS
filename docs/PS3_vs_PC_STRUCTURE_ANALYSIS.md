# PS3 vs PC OPTIONS File Structure Analysis

## Executive Summary

**Key Finding**: PS3 OPTIONS files have **4 sections** while PC has **3 sections**.

The 4th section in PS3 files contains controller mapping data specific to the DualShock 3 controller. This section is absent from PC files which use a different input handling system.

## Tool Usage

### Decompress PS3 OPTIONS files
```bash
# Decompress all 4 sections
python lzss_decompressor_ps3.py OPTIONS.PS3

# Decompress specific section (1, 2, 3, or 4)
python lzss_decompressor_ps3.py OPTIONS.PS3 2

# Section 4 only (controller mappings)
python lzss_decompressor_ps3.py OPTIONS.PS3 4
```
Outputs: `section1.bin`, `section2.bin`, `section3.bin`, `section4.bin`

### Rebuild PS3 OPTIONS files
```bash
# With all 4 sections
python options_serializer_ps3.py section1.bin section2.bin section3.bin section4.bin -o OPTIONS.PS3

# With 3 sections only (no controller mappings)
python options_serializer_ps3.py section1.bin section2.bin section3.bin -o OPTIONS.PS3

# With validation (decompresses output and compares to inputs)
python options_serializer_ps3.py sec1.bin sec2.bin sec3.bin sec4.bin -o OPTIONS.PS3 --validate
```

## File Structure Comparison

### PC OPTIONS File (3 Sections)

```
Offset   Size        Description
------   ----        -----------
0x0000   44 bytes    Section 1 Header (Field3=0xC5)
0x002C   165 bytes   Section 1 Compressed Data
0x00D1   44 bytes    Section 2 Header (Field3=0x11FACE11)
0x00FD   634 bytes   Section 2 Compressed Data
0x0377   44 bytes    Section 3 Header (Field3=0x21EFFE22)
0x03A3   92 bytes    Section 3 Compressed Data
0x03FF   5 bytes     Footer [01 00 00 00 0C]
------
Total:   1028 bytes
```

### PS3 OPTIONS File (4 Sections)

```
Offset   Size        Description
------   ----        -----------
0x0000   8 bytes     PS3 Prefix (size + CRC32, big-endian)
0x0008   44 bytes    Section 1 Header (Field3=0xC6)
0x0034   166 bytes   Section 1 Compressed Data
0x00DA   44 bytes    Section 2 Header (Field3=0x11FACE11)
0x0106   627 bytes   Section 2 Compressed Data
0x0379   44 bytes    Section 3 Header (Field3=0x21EFFE22)
0x03A5   66 bytes    Section 3 Compressed Data
0x03E7   8 bytes     **Section 4 Marker** [00 00 01 7B 00 00 00 08]
0x03EF   44 bytes    Section 4 Header (Field3=0x07)
0x041B   331 bytes   Section 4 Compressed Data
0x0566   ~49KB       Zero padding (to reach 50KB fixed size)
------
Total:   51200 bytes (fixed size PS3 save)
```

## Section Details

### Section Markers (Field3 Values)

| Section | PC Marker | PS3 Marker | Notes |
|---------|-----------|------------|-------|
| 1 | 0x000000C5 | 0x000000C6 | PS3 is +1 |
| 2 | 0x11FACE11 | 0x11FACE11 | Identical |
| 3 | 0x21EFFE22 | 0x21EFFE22 | Identical |
| 4 | N/A | 0x00000007 | PS3 only |

### Section Sizes (Uncompressed)

| Section | PC Size | PS3 Size | Difference |
|---------|---------|----------|------------|
| 1 | 283 bytes | 289 bytes | +6 |
| 2 | 1310 bytes | 1306 bytes | -4 |
| 3 | 162 bytes | 119 bytes | -43 |
| 4 | N/A | 1903 bytes | PS3 only |
| **Total** | **1755 bytes** | **3617 bytes** | **+1862** |

## PS3 8-Byte Prefix

The PS3 file starts with an 8-byte wrapper (big-endian):

```
Bytes:  00 00 05 5E 20 EC E5 EA
        ├──────────┼───────────┤
        Size       CRC32

Size:   0x055E = 1374 bytes (payload size after prefix)
CRC32:  0x20ECE5EA (checksum of payload)
```

## Section 4 Marker (8-Byte Gap)

Between Section 3 and Section 4, there's an 8-byte marker:

```
Bytes:  00 00 01 7B 00 00 00 08 (big-endian)
        ├──────────┼───────────┤
        Size       Type

Size:   0x17B = 379 bytes (Section 4 header + compressed data + 4)
Type:   0x08 = Section 4 type identifier
```

This marker acts as a subsection boundary indicator.

### Section 4 Header Fields

Section 4's header has unique values in fields 0-2:

| Offset | Field | Value | Description |
|--------|-------|-------|-------------|
| 0x00 | Field0 | `0x22FEEF21` | Previous section ID (0x21EFFE22) byte-swapped as BE |
| 0x04 | Field1 | `0x00000004` | Section number |
| 0x08 | Field2 | `0x00000007` | Section 4 identifier (PS3 controller mappings) |

Fields 3-10 follow the same pattern as other sections (uncompressed size, magic bytes, compressed size, checksum).

## Section 4 Content Analysis

Section 4 contains **controller mapping data** with the following structure:

### Overall Layout
- **Header**: 97 bytes (general controller settings)
- **Records**: 17 records x 85 bytes = 1445 bytes
- **Trailer**: 361 bytes (additional settings + padding)
- **Total**: 1903 bytes

### Record Structure

Each 85-byte record contains a controller button mapping:

```
Offset  Size  Description
------  ----  -----------
0x00    5     Signature: A8 CF 5F F9 43 (controller identifier)
0x05    4     Value 1: 0x0000003B (59) - constant
0x09    4     Value 2: 0x00000011 (17) - constant
0x0D    4     Controller ID: C0 B2 57 81
0x11    10    Zeros
0x1B    2     06 00 - field marker
0x1D    1     **Button/Action ID** (varies: 02, 15, 16, 05, 0A, etc.)
0x1E    67    Additional mapping data with sub-patterns
```

### Button/Action IDs Found

| ID | Hex | Possible Mapping |
|----|-----|------------------|
| 2 | 0x02 | Cross (X) button |
| 5 | 0x05 | L1 trigger |
| 7 | 0x07 | R1 trigger |
| 8 | 0x08 | L2 trigger |
| 10 | 0x0A | R2 trigger |
| 14 | 0x0E | D-pad |
| 17 | 0x11 | Left stick |
| 18 | 0x12 | Right stick |
| 20 | 0x14 | Select |
| 21 | 0x15 | Triangle |
| 22 | 0x16 | Circle |
| 25 | 0x19 | Square |
| 28 | 0x1C | Start |
| 31 | 0x1F | L3 (stick click) |
| 32 | 0x20 | R3 (stick click) |
| 34 | 0x22 | PS button |

## PC Section 3 Extra Data

PC Section 3 is larger (162 vs 119 bytes) and contains extra data at the end:

```
0x77: 80 87 6f 49 00 00 00 00 00 00 09 00 0b ff ff ff
0x87: ff ff ff 1f 00 0e 00 00 00 5b b0 88 6f 00 00 00
0x97: 00 00 00 00 00 0b 01 00 00 00 00
```

This appears to be PC-specific settings (possibly keyboard/mouse mappings or video settings).

## Footer Comparison

**Important**: PS3 OPTIONS files have **no footer**. The file ends immediately after Section 4's LZSS terminator (`0x20 0x00`), followed by zero padding to reach 51,200 bytes.

PC files have a 5-byte footer:
```
01 00 00 00 0C
```
- Field1: `0x00000001`
- Field2: `0x0C` (12)

## Why PS3 Has 4 Sections

1. **DualShock 3 Complexity**: The PS3 controller has:
   - Pressure-sensitive face buttons (not just on/off)
   - Sixaxis motion controls
   - Rumble motors with variable intensity
   - Unique button layout vs Xbox/PC controllers

2. **Platform Separation**: Sony requires games to store controller configs separately to support:
   - Multiple controller profiles
   - Custom remapping through XMB
   - Accessibility options

3. **Save Size Requirements**: PS3 saves have fixed size requirements (51200 bytes here), requiring padding.

## Conversion Implications

When converting PS3 saves to PC:
1. Remove the 8-byte prefix
2. Field2 in Section 1 header changes from 0xC6 to 0xC5
3. Remove the 8-byte gap marker before Section 4
4. Section 4 can be included (likely ignored by PC) or removed
5. Add PC footer (`01 00 00 00 0C`)
6. Remove zero padding

When converting PC saves to PS3:
1. Add 8-byte prefix with size and CRC32 (big-endian)
2. Update Field2 in Section 1 header to 0xC6
3. Add 8-byte gap marker before Section 4
4. Either include Section 4 from original PS3 file or generate from defaults
5. Remove PC footer (PS3 has no footer)
6. Pad to 51,200 bytes with zeros