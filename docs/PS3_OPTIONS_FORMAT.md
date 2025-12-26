# PS3 OPTIONS File Format Specification

Complete technical documentation for the Assassin's Creed Brotherhood PS3 OPTIONS save file format.

## 1. Overview

The PS3 OPTIONS file stores game settings, configuration, and DualShock 3 controller mappings for Assassin's Creed Brotherhood. The file uses LZSS compression for data storage.

**Key Characteristics:**
- **Fixed file size**: 51,200 bytes (0xC800)
- **Number of sections**: 4 compressed sections
- **8-byte prefix**: Contains data size and CRC32 checksum
- **Zero-padded**: File is padded with null bytes to reach the fixed size

## 2. Tool Usage

### Decompressor

```bash
# Decompress all 4 sections
python lzss_decompressor_ps3.py OPTIONS.PS3

# Decompress specific section (1, 2, 3, or 4)
python lzss_decompressor_ps3.py OPTIONS.PS3 2

# Section 4 only (controller mappings)
python lzss_decompressor_ps3.py OPTIONS.PS3 4
```

**Output files**: `section1.bin`, `section2.bin`, `section3.bin`, `section4.bin`

### Serializer

```bash
# Rebuild with all 4 sections
python options_serializer_ps3.py section1.bin section2.bin section3.bin section4.bin -o OPTIONS.PS3

# Rebuild with 3 sections only (no controller mappings)
python options_serializer_ps3.py section1.bin section2.bin section3.bin -o OPTIONS.PS3

# Rebuild with validation (decompresses output and compares to inputs)
python options_serializer_ps3.py sec1.bin sec2.bin sec3.bin sec4.bin -o OPTIONS.PS3 --validate
```

## 3. File Layout

Complete byte-by-byte layout of a PS3 OPTIONS file:

```
Offset     Size        Description
---------- ----------- --------------------------------------------------
0x0000     8 bytes     PS3 Prefix (data size + CRC32, big-endian)
0x0008     44 bytes    Section 1 Header
0x0034     variable    Section 1 Compressed Data (ends with 0x20 0x00)
...        44 bytes    Section 2 Header
...        variable    Section 2 Compressed Data (ends with 0x20 0x00)
...        44 bytes    Section 3 Header
...        variable    Section 3 Compressed Data (ends with 0x20 0x00)
...        8 bytes     Gap Marker (before Section 4)
...        44 bytes    Section 4 Header
...        variable    Section 4 Compressed Data (ends with 0x20 0x00)
...        variable    Zero Padding (to reach 51,200 bytes)
---------- ----------- --------------------------------------------------
Total:     51,200 bytes (fixed)
```

### Example Layout (Typical File)

```
Offset     Size        Description
---------- ----------- --------------------------------------------------
0x0000     8 bytes     PS3 Prefix
0x0008     44 bytes    Section 1 Header (Field2=0xC6)
0x0034     166 bytes   Section 1 Compressed Data
0x00DA     44 bytes    Section 2 Header (Field2=0x11FACE11)
0x0106     627 bytes   Section 2 Compressed Data
0x0379     44 bytes    Section 3 Header (Field2=0x21EFFE22)
0x03A5     66 bytes    Section 3 Compressed Data
0x03E7     8 bytes     Gap Marker [00 00 01 7B 00 00 00 08]
0x03EF     44 bytes    Section 4 Header (Field2=0x07)
0x041B     331 bytes   Section 4 Compressed Data
0x0566     49,818 bytes Zero Padding
---------- ----------- --------------------------------------------------
Total:     51,200 bytes
```

## 4. 8-Byte Prefix Structure

The file begins with an 8-byte prefix containing the payload size and CRC32 checksum.

| Offset | Size | Endianness | Field | Description |
|--------|------|------------|-------|-------------|
| 0x00 | 4 bytes | Big-endian | Data Size | Size of all section data (excludes prefix and padding) |
| 0x04 | 4 bytes | Big-endian | CRC32 | Checksum of section data |

### Example

```
Bytes:  00 00 05 5E 20 EC E5 EA
        |---------|  |---------|
        Size         CRC32

Size:   0x055E = 1374 bytes
CRC32:  0x20ECE5EA
```

### CRC32 Algorithm Parameters

The PS3 uses a custom CRC32 configuration (not the standard CRC32):

| Parameter | Value | Description |
|-----------|-------|-------------|
| Polynomial | `0x04C11DB7` | CRC-32 polynomial |
| Initial Value | `0xBAE23CD0` | Non-standard initial seed |
| XOR Output | `0xFFFFFFFF` | Final XOR value |
| Reflect Input | `true` | Reflect each input byte |
| Reflect Output | `true` | Reflect the final CRC value |

### CRC32 Coverage

The CRC32 is calculated over **all section data** starting at offset 0x08, which includes:
- Section 1 header and compressed data
- Section 2 header and compressed data
- Section 3 header and compressed data
- Gap marker (8 bytes)
- Section 4 header and compressed data

The CRC32 does **not** include:
- The 8-byte prefix itself
- Zero padding at the end of the file

### Reference Implementation

```python
def crc32_ps3(data: bytes) -> int:
    crc = 0xBAE23CD0  # Custom initial value

    for byte in data:
        # Reflect input byte (reverse bits)
        byte = int('{:08b}'.format(byte)[::-1], 2)
        crc ^= (byte << 24)

        for _ in range(8):
            if crc & 0x80000000:
                crc = ((crc << 1) ^ 0x04C11DB7) & 0xFFFFFFFF
            else:
                crc = (crc << 1) & 0xFFFFFFFF

    # Reflect output (reverse all 32 bits)
    crc = int('{:032b}'.format(crc)[::-1], 2)
    # XOR with final value
    return (crc ^ 0xFFFFFFFF) & 0xFFFFFFFF
```

## 5. Section Header Structure (44 bytes)

Each section begins with a 44-byte header containing 11 fields. The first 3 fields use big-endian byte order, while fields 3-10 use little-endian byte order.

| Offset | Size | Field | Endian | Description |
|--------|------|-------|--------|-------------|
| 0x00 | 4 bytes | Field0 | BE | Varies by section (see Section 6) |
| 0x04 | 4 bytes | Field1 | BE | Varies by section (see Section 6) |
| 0x08 | 4 bytes | Field2 | BE | Section identifier marker |
| 0x0C | 4 bytes | Field3 | LE | Uncompressed data size |
| 0x10 | 4 bytes | Magic1 | LE | Magic constant: `0x57FBAA33` |
| 0x14 | 4 bytes | Magic2 | LE | Magic constant: `0x1004FA99` |
| 0x18 | 4 bytes | Magic3 | LE | Magic constant: `0x00020001` |
| 0x1C | 4 bytes | Magic4 | LE | Magic constant: `0x01000080` |
| 0x20 | 4 bytes | Field5 | LE | Compressed data size |
| 0x24 | 4 bytes | Field6 | LE | Uncompressed data size (duplicate of Field3) |
| 0x28 | 4 bytes | Field7 | LE | Checksum (zero-seed Adler-32 of compressed data) |

### Field Details

**Field0 (offset 0x00):**
- Section 1: Fixed value `0x00000016`
- Sections 2-4: `compressed_size + 40`

**Field1 (offset 0x04):**
- Section 1: `0x00FEDBAC`
- Section 2: `0x00000003`
- Section 3: `0x00000000`
- Section 4: `0x00000004`

**Field2 (offset 0x08):**
- Section identifier (see Section 6 for values)

**Magic Bytes (offsets 0x10-0x1F):**
- These 16 bytes are constant across all sections
- Used to locate section headers during parsing

### Example Header (Section 1)

```
Offset  Raw Bytes           Interpretation
------  ------------------  --------------------------
0x00    00 00 00 16         Field0 = 0x00000016 (BE)
0x04    00 FE DB AC         Field1 = 0x00FEDBAC (BE)
0x08    00 00 00 C6         Field2 = 0x000000C6 (BE)
0x0C    21 01 00 00         Field3 = 289 bytes (LE)
0x10    33 AA FB 57         Magic1 = 0x57FBAA33 (LE)
0x14    99 FA 04 10         Magic2 = 0x1004FA99 (LE)
0x18    01 00 02 00         Magic3 = 0x00020001 (LE)
0x1C    80 00 00 01         Magic4 = 0x01000080 (LE)
0x20    A6 00 00 00         Field5 = 166 bytes compressed (LE)
0x24    21 01 00 00         Field6 = 289 bytes uncompressed (LE)
0x28    XX XX XX XX         Field7 = Adler-32 checksum (LE)
```

## 6. Section-Specific Values

| Field | Section 1 | Section 2 | Section 3 | Section 4 |
|-------|-----------|-----------|-----------|-----------|
| Field0 | `0x00000016` | compressed_size + 40 | compressed_size + 40 | `0x22FEEF21` |
| Field1 | `0x00FEDBAC` | `0x00000003` | `0x00000000` | `0x00000004` |
| Field2 | `0x000000C6` | `0x11FACE11` | `0x21EFFE22` | `0x00000007` |

### Section 4 Field0 Note

Section 4's Field0 value (`0x22FEEF21`) is derived from Section 3's identifier (`0x21EFFE22`) with its bytes reversed (byte-swapped as big-endian).

## 7. 8-Byte Gap Marker (Before Section 4)

Between Section 3's compressed data and Section 4's header, there is an 8-byte gap marker.

| Offset | Size | Endianness | Field | Description |
|--------|------|------------|-------|-------------|
| 0x00 | 4 bytes | Big-endian | Size | Section 4 total size + 4 |
| 0x04 | 4 bytes | Big-endian | Type | Type marker: `0x00000008` |

### Size Calculation

```
Gap marker size field = Section 4 header (44 bytes) + Section 4 compressed data size + 4
```

### Example

```
Bytes:  00 00 01 7B 00 00 00 08
        |---------|  |---------|
        Size         Type

Size:   0x017B = 379 bytes
        = 44 (header) + 331 (compressed data) + 4
Type:   0x08
```

## 8. Section Checksums

Each section header contains an Adler-32 checksum in Field7 (offset 0x28).

### Zero-Seed Adler-32 Algorithm

The game uses a non-standard Adler-32 variant with zero seed:

| Parameter | Standard Adler-32 | AC Brotherhood Variant |
|-----------|-------------------|------------------------|
| Initial s1 | 1 | **0** |
| Initial s2 | 0 | 0 |

### Algorithm

```python
def adler32_zero_seed(data: bytes) -> int:
    MOD_ADLER = 65521
    s1 = 0  # NON-STANDARD: standard uses s1=1
    s2 = 0

    for byte in data:
        s1 = (s1 + byte) % MOD_ADLER
        s2 = (s2 + s1) % MOD_ADLER

    return (s2 << 16) | s1
```

### Checksum Coverage

The checksum is calculated over the **compressed LZSS data** for that section, not the decompressed data.

## 9. LZSS Compression Format

The compressed data uses an LZSS variant with three encoding types:

| Type | Total Bits | Condition | Format |
|------|------------|-----------|--------|
| Literal | 9 | Always valid | Flag 0 + 8-bit byte |
| Short match | 12 | Length 2-5, offset 1-256 | Flag 1, type 0, 2-bit length, 8-bit offset |
| Long match | 18+ | Length 3+, offset 1-8192 | Flag 1, type 1, 16-bit encoding, optional extension bytes |

### Terminator

Each compressed section ends with a terminator sequence:
- Two flag bits set to 1
- Followed by bytes `0x20 0x00`

### Compression Details

For complete LZSS compression implementation details, see `docs/LZSS_LOGIC_FLOW_ANALYSIS.md`.

## 10. Section Contents Overview

| Section | Uncompressed Size | Description |
|---------|-------------------|-------------|
| Section 1 | 289 bytes | General game settings |
| Section 2 | 1306 bytes | Game settings and options |
| Section 3 | 119 bytes | Additional settings |
| Section 4 | 1903 bytes | DualShock 3 controller mappings |

### Section 4 Controller Mapping Structure

Section 4 contains controller button mapping data specific to the DualShock 3:

| Offset | Size | Description |
|--------|------|-------------|
| 0x00 | 97 bytes | Header (general controller settings) |
| 0x61 | 1445 bytes | Button mapping records (17 records x 85 bytes) |
| 0x5EC | 361 bytes | Trailer (additional settings + padding) |

**Button Mapping Record Structure (85 bytes):**

| Offset | Size | Description |
|--------|------|-------------|
| 0x00 | 5 bytes | Signature: `A8 CF 5F F9 43` |
| 0x05 | 4 bytes | Value 1: `0x0000003B` (constant) |
| 0x09 | 4 bytes | Value 2: `0x00000011` (constant) |
| 0x0D | 4 bytes | Controller ID: `C0 B2 57 81` |
| 0x11 | 10 bytes | Reserved (zeros) |
| 0x1B | 2 bytes | Field marker: `06 00` |
| 0x1D | 1 byte | Button/Action ID |
| 0x1E | 67 bytes | Additional mapping data |

**Known Button/Action IDs:**

| ID | Hex | Mapping |
|----|-----|---------|
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
| 31 | 0x1F | L3 (left stick click) |
| 32 | 0x20 | R3 (right stick click) |
| 34 | 0x22 | PS button |

## 11. Zero Padding

The file is padded with null bytes (0x00) to reach exactly 51,200 bytes (0xC800).

### Padding Calculation

```
padding_size = 51200 - (8 + section_data_size)

Where:
  8 = PS3 prefix size
  section_data_size = Sum of all section headers and compressed data, including gap marker
```

### Important Notes

- The padding consists entirely of `0x00` bytes
- Padding immediately follows Section 4's LZSS terminator (`0x20 0x00`)
- There is **no footer** before the padding (unlike the PC version)
- The file must be exactly 51,200 bytes for the PS3 to accept it

## Appendix A: Complete File Structure Diagram

```
+--------------------------------+ 0x0000
|         PS3 Prefix             |
|   Data Size (4 bytes BE)       |
|   CRC32 (4 bytes BE)           |
+--------------------------------+ 0x0008
|      Section 1 Header          |
|   Field0-2 (12 bytes BE)       |
|   Field3-10 (32 bytes LE)      |
+--------------------------------+ 0x0034
|   Section 1 Compressed Data    |
|   (ends with 0x20 0x00)        |
+--------------------------------+
|      Section 2 Header          |
|   (44 bytes)                   |
+--------------------------------+
|   Section 2 Compressed Data    |
|   (ends with 0x20 0x00)        |
+--------------------------------+
|      Section 3 Header          |
|   (44 bytes)                   |
+--------------------------------+
|   Section 3 Compressed Data    |
|   (ends with 0x20 0x00)        |
+--------------------------------+
|        Gap Marker              |
|   Size (4 bytes BE)            |
|   Type=0x08 (4 bytes BE)       |
+--------------------------------+
|      Section 4 Header          |
|   (44 bytes)                   |
+--------------------------------+
|   Section 4 Compressed Data    |
|   (ends with 0x20 0x00)        |
+--------------------------------+
|       Zero Padding             |
|   (0x00 bytes to reach 51200)  |
+--------------------------------+ 0xC800
```

## Appendix B: Parsing Algorithm

Pseudocode for parsing a PS3 OPTIONS file:

```
1. Read 8-byte prefix
   - Extract data_size (bytes 0-3, big-endian)
   - Extract expected_crc32 (bytes 4-7, big-endian)

2. Extract section data
   - section_data = file[8 : 8 + data_size]

3. Verify CRC32
   - calculated_crc32 = crc32_ps3(section_data)
   - Validate: calculated_crc32 == expected_crc32

4. Find section headers by searching for magic pattern
   - Pattern: 33 AA FB 57 99 FA 04 10 01 00 02 00 80 00 00 01
   - This pattern appears at offset 0x10 within each header
   - Header start = pattern_position - 0x10

5. For each section header found:
   - Parse fields 0-2 as big-endian
   - Parse fields 3-10 as little-endian
   - Extract compressed data starting at header + 44 bytes
   - Compressed data ends at header.compressed_size bytes

6. Handle gap marker before Section 4
   - 8 bytes immediately before Section 4 header
   - Parse size and type as big-endian

7. Decompress each section using LZSS
   - Verify decompressed size matches header.uncompressed_size
   - Verify checksum matches header.checksum
```

## Appendix C: Serialization Algorithm

Pseudocode for creating a PS3 OPTIONS file:

```
1. For each section (1-4):
   - Compress section data using LZSS
   - Calculate Adler-32 checksum of compressed data
   - Build 44-byte header with appropriate field values
   - For Section 4: prepend 8-byte gap marker

2. Concatenate all sections
   - section_data = section1 + section2 + section3 + gap_marker + section4

3. Calculate CRC32
   - crc32_value = crc32_ps3(section_data)

4. Build prefix
   - prefix = data_size (BE) + crc32_value (BE)

5. Calculate padding
   - padding_size = 51200 - 8 - len(section_data)
   - padding = bytes(padding_size)

6. Write file
   - output = prefix + section_data + padding
```
