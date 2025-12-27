# AC Brotherhood OPTIONS - Function Call Tree

**Document Version:** 1.0
**Date:** 2025-12-27
**Status:** Complete Ghidra Function Reference with Call Hierarchy

This document maps all reverse-engineered functions from ACBSP.exe that handle OPTIONS file parsing, serialization, and compression. Functions are organized by section with full call hierarchy.

---

## Table of Contents

1. [Function Summary](#function-summary)
2. [Section 1 Functions](#section-1-functions)
3. [Section 2 Functions](#section-2-functions)
4. [Section 3 Functions](#section-3-functions)
5. [Compression Functions](#compression-functions)
6. [Header and Magic Byte Functions](#header-and-magic-byte-functions)
7. [File I/O Functions](#file-io-functions)
8. [Save System Orchestration](#save-system-orchestration)
9. [Language System Functions](#language-system-functions)
10. [Complete Call Hierarchy](#complete-call-hierarchy)
11. [Function-to-Field Mapping](#function-to-field-mapping)

---

## Function Summary

### Quick Reference Table

| Address | Function | Section | Purpose |
|---------|----------|---------|---------|
| 0x0046D430 | FUN_0046d430 | Section 1 | Reader/Validator (checks 0xFEDBAC) |
| 0x0046D710 | FUN_0046d710 | Section 1 | Header writer |
| 0x0046D7B0 | FUN_0046d7b0 | Section 1 | Loader |
| 0x00ACF240 | FUN_00acf240 | Section 2 | Settings constructor (5,379 bytes) |
| 0x01712CA0 | FUN_01712ca0 | Section 2 | Header writer |
| 0x01712DB0 | FUN_01712db0 | Section 2 | Validation (checks 0x11FACE11) |
| 0x01B024F0 | FUN_01b024f0 | Section 2 | Data parsing |
| 0x01B02990 | FUN_01b02990 | Section 2 | Data parsing |
| 0x01B020E0 | FUN_01b020e0 | Section 2 | Data parsing |
| 0x017106E0 | FUN_017106e0 | Section 3 | Constructor (91 bytes) |
| 0x017108E0 | FUN_017108e0 | Section 3 | Writer (sets 0x21EFFE22) |
| 0x017109E0 | FUN_017109e0 | Section 3 | Reader (validates 0x21EFFE22) |
| 0x01710540 | FUN_01710540 | Section 3 | Destructor (11 bytes) |
| 0x0084CA20 | FUN_0084ca20 | Section 3 | DLC flag constructor |
| 0x0084CB60 | FUN_0084cb60 | Section 3 | DLC sync handler |
| 0x0223E140 | Compression | Compression | Main entry point |
| 0x0223E0A0 | Match Finder | Compression | Find best match at position |
| 0x01CDBA20 | FUN_01cdba20 | Checksum | Zero-seed Adler-32 |
| 0x01B7A310 | FUN_01b7a310 | Header | Magic bytes writer |
| 0x01B7A1D0 | FUN_01b7a1d0 | Header | Magic bytes validator |

---

## Section 1 Functions

### Primary Section 1 Functions

#### FUN_0046d710 - Section 1 Header Writer

**Address:** `0x0046D710`
**Purpose:** Initializes Section 1 header with magic values

**Key Operations:**
```c
*(uint32_t*)(param_2 + 0x10) = 0x16;      // Field1 = 0x16
*(uint32_t*)(param_2 + 0x14) = 0xFEDBAC;  // Field2 = 0xFEDBAC
```

**Writes:**
- Field1: `0x00000016` (Section 1 signature)
- Field2: `0x00FEDBAC` (Validation marker)

**Calls:** `FUN_0046d160`

---

#### FUN_0046d160 - Section 1 Writer/Serializer

**Address:** `0x0046D160`
**Purpose:** Builds and writes Section 1 of the OPTIONS file

**Process:**
1. Debug logging: "::Engine::SaveGame::SaveToFile"
2. Allocates initial 12-byte buffer
3. Writes header (Field1: 0x16, Field2: 0xFEDBAC)
4. Compresses section data via `FUN_01afe160`
5. Appends compressed data after header
6. Calls vtable write function for output

**Calls:**
- `FUN_01afe160` (compression)
- Vtable write function

---

#### FUN_0046d430 - Section 1 Reader and Validator

**Address:** `0x0046D430`
**Purpose:** Reads and validates Section 1 from OPTIONS file

**Validation Logic:**
```c
if ((*buffer == 0x16) && (buffer[1] == 0xFEDBAC)) {
    // Valid Section 1 header
    size_t decompressed_size = buffer[2];  // Field3
    decompress(buffer + 3, decompressed_size, ...);
} else {
    // Invalid header - set error flag
    *(uint8_t*)(param_2 + 0x46) = 1;
    return 0;
}
```

**Calls:**
- `FUN_00425360` (decompression)
- Vtable deserialize function at offset 0x28

---

#### FUN_0046d7b0 - Section 1 Loader

**Address:** `0x0046D7B0`
**Purpose:** Loads Section 1 data after validation

**Calls:**
- `FUN_0046d430` (validation)
- Post-load processing functions

---

## Section 2 Functions

### Primary Section 2 Functions

#### FUN_00acf240 - Settings Constructor

**Address:** `0x00ACF240`
**Size:** 5,379 bytes (large function)
**Purpose:** Initializes all Section 2 settings fields

**Fields Initialized:**
| Offset | Field | Evidence |
|--------|-------|----------|
| 0xC0 | Music Volume | Direct write |
| 0xFF | Vibration | Direct write |
| 0x195 | Brightness | Direct write |
| 0x1DD | Cannon Invert Y | Direct write |
| 0x237 | Mini-Map | Direct write |
| 0x369 | Costume Bitfield | Direct write |

---

#### FUN_01712ca0 - Section 2 Header Writer

**Address:** `0x01712CA0`
**Purpose:** Writes Section 2 header to buffer

**Key Operations:**
```asm
01712cd8  MOV EBX, 0x3          ; Field2 = Type ID
01712ceb  MOV ECX, 0x11FACE11   ; Field3 = Magic
```

**Header Written:**
- Field1: `compressed_size + 40`
- Field2: `0x00000003` (Type ID)
- Field3: `0x11FACE11` (Section 2 magic)

**Calls:**
- `FUN_01afe160` (compression)
- `FUN_0046eb90` (buffer resize)

---

#### FUN_01712db0 - Section 2 Reader/Validator

**Address:** `0x01712DB0`
**Purpose:** Validates Section 2 magic and processes data

**Validation:**
```c
if (buffer[0] != 0x3) return false;        // Type ID check
if (buffer[1] != 0x11FACE11) return false;  // Magic check
```

**Calls:**
- `FUN_00425360` (decompression)
- `FUN_01afd600` (header processing)
- Vtable function at offset 0x0C

---

#### FUN_01712930 - Profile Data Serializer

**Address:** `0x01712930`
**Purpose:** Serializes/deserializes "AssassinGlobalProfileData" structure

**Process:**
1. Links back-pointer: `param_2 + 0x1c = param_1`
2. Initializes context if first-time
3. Serializes multiple fields with hash keys
4. Handles arrays and dynamic data

---

#### FUN_01b024f0, FUN_01b02990, FUN_01b020e0 - Section 2 Data Parsers

**Addresses:** `0x01B024F0`, `0x01B02990`, `0x01B020E0`
**Purpose:** Parse individual field groups within Section 2

---

### Section 2 Field-Specific Functions

| Address | Function | Field Accessed |
|---------|----------|----------------|
| 0x004391F0 | FUN_004391f0 | Subtitles Toggle (0x63) |
| 0x00439250 | FUN_00439250 | Subtitles Toggle (0x63) |
| 0x0040CFC0 | FUN_0040cfc0 | Default Language Flag (0x75) |
| 0x0040D880 | FUN_0040d880 | Default Language Flag (0x75) |
| 0x00504240 | FUN_00504240 | Voice Volume (0xD5) |
| 0x0084E720 | FUN_0084e720 | Voice Volume (0xD5) |
| 0x007A1320 | FUN_007a1320 | SFX Volume (0xEA) |
| 0x00417FC0 | FUN_00417fc0 | X Look Sensitivity (0x111) |
| 0x00A82210 | FUN_00a82210 | 3rd Person Invert X (0x13B) |

---

## Section 3 Functions

### Primary Section 3 Functions

#### FUN_017106e0 - Section 3 Constructor

**Address:** `0x017106E0`
**Size:** 91 bytes
**Purpose:** Constructs Section 3 object

**Process:**
- Sets vtable to `PTR_FUN_0253de0c`
- Initializes fields

---

#### FUN_017108e0 - Section 3 Writer

**Address:** `0x017108E0`
**Purpose:** Writes Section 3 to buffer

**Key Operations:**
```asm
0171090d  XOR EBX, EBX          ; Field2 = 0x00 (Type ID)
01710927  MOV ECX, 0x21EFFE22   ; Field3 = Magic
```

**Header Written:**
- Field1: `compressed_size + 40`
- Field2: `0x00000000` (Type ID)
- Field3: `0x21EFFE22` (Section 3 magic)

**Calls:**
- `FUN_01afe160` (compression)

---

#### FUN_017109e0 - Section 3 Reader/Validator

**Address:** `0x017109E0`
**Purpose:** Reads and validates Section 3

**Validation:**
```c
if (buffer[0] != 0x0) return false;         // Type ID check
if (buffer[1] != 0x21EFFE22) return false;  // Magic check
```

**Special Handling:**
- If flag at offset 0x24 is set, calls `FUN_004d1c00`

**Calls:**
- `FUN_00425360` (decompression)
- `FUN_01afd600` (header processing)

---

#### FUN_01710540 - Section 3 Destructor

**Address:** `0x01710540`
**Size:** 11 bytes
**Purpose:** Destructs Section 3 object

---

#### FUN_0084ca20 - DLC Flag Constructor

**Address:** `0x0084CA20`
**Purpose:** Initializes DLC sync flag at offset 0x9D

---

#### FUN_0084cb60 - DLC Sync Handler

**Address:** `0x0084CB60`
**Purpose:** Sets DLC sync flag (offset 0x9D in PC, 0x5A in PS3)

**Field Written:** Section 3 DLC Sync Flag

---

## Compression Functions

### Main Compression Entry Points

#### Compression Entry Point (0x0223E140)

**Address:** `0x0223E140` (ACBSP+0x178e140)
**Purpose:** Primary compression entry point

**Key Operations:**
- Initializes 2-byte zero prefix buffer
- Main compression loop
- Lazy matching orchestration

---

#### Match Finder (0x0223E0A0)

**Address:** `0x0223E0A0` (ACBSP+0x178e0a0)
**Purpose:** Find best match at given position

**Returns:**
- Match length and offset
- Uses hash table or binary tree structure

---

### Compression Wrapper Functions

#### FUN_01afe160 - Compression Wrapper

**Address:** `0x01AFE160`
**Purpose:** Wrapper with standard 4KB buffer sizes

**Calls:** `FUN_01afdba0` with 0x1000 buffer size

---

#### FUN_01afdba0 - Main Compression with Verification

**Address:** `0x01AFDBA0`
**Purpose:** Primary compression with optional round-trip validation

**Process:**
1. Initializes compression buffers
2. Calls `FUN_01b7b050` (LZSS compressor) with 0x8000 buffer
3. If `param_6` set, decompresses via `FUN_00425360` to validate
4. Releases allocated buffers

---

#### FUN_01b7b050 - Low-Level Compression

**Address:** `0x01B7B050`
**Purpose:** Core LZSS compression

**Output:**
- Returns compressed buffer size in `param_4`
- Returns compression result in `param_5`

---

#### FUN_01b8e140 - LZSS Compression Engine

**Address:** `0x01B8E140`
**Purpose:** Core LZSS compression algorithm (lazy-matching variant)

**Encoding Types:**
- Short matches (2-5 bytes, offset 1-256): 12 bits
- Long matches (3+ bytes, offset 0-8191): 18+ bits
- Literals: 9 bits

---

### Decompression Functions

#### FUN_00425360 - Decompression Function

**Address:** `0x00425360`
**Purpose:** Decompresses LZSS-compressed data

**Signature:**
```c
void decompress_data(
    uint8_t* input_data,
    uint32_t compressed_size,
    uint32_t decompressed_size,
    bool verify_checksum,
    void* output_buffer,
    uint32_t output_buffer_size,
    void* allocator
);
```

---

## Header and Magic Byte Functions

#### FUN_01b7a310 - Magic Bytes Writer

**Address:** `0x01B7A310`
**Purpose:** Writes universal 16-byte magic pattern to section headers

**Pattern Written:**
```
0x10: 0x57FBAA33  (Magic1 - Format signature)
0x14: 0x1004FA99  (Magic2 - Version identifier)
0x18: 0x00020001  (Magic3 - Compression params)
0x1C: 0x01000080  (Magic4 - Version flags)
```

**Implementation:**
- Magic1 & Magic2: Written via `vtable[0x30](0x57fbaa33, 0x1004fa99)`
- Magic3: Written via `vtable[0x38](1)` + `vtable[0x3c](2)`
- Magic4: Written via `vtable[0x34](param+0x40 | 0x80000000)`

---

#### FUN_01b7a1d0 - Magic Bytes Validator

**Address:** `0x01B7A1D0`
**Purpose:** Validates section header magic bytes

**Validation:**
1. Size check: buffer >= 12 bytes
2. Magic1: `buffer[0x04] == 0x57FBAA33`
3. Magic2: `buffer[0x08] == 0x1004FA99`

**Returns:** `0x1004FA01` if valid

---

#### FUN_01afd600 - Header Processor with Validation

**Address:** `0x01AFD600`
**Purpose:** Validates and processes section header data

**Calls:**
- `FUN_01b7a1d0` (magic validation)
- `FUN_01b7b190` (processing)

---

## Checksum Functions

#### FUN_01cdba20 - Zero-Seed Adler-32

**Address:** `0x01CDBA20` (ACBSP+0x178ba20)
**Purpose:** Custom Adler-32 checksum with zero seed

**Parameters:**
- Standard Adler-32 initial: s1=1, s2=0
- ACB variant initial: s1=0, s2=0

**Called by:** `FUN_01ccac5d` during serialization

---

## File I/O Functions

#### FUN_005e4860 - Low-Level File Writer

**Address:** `0x005E4860`
**Purpose:** Writes data buffer to file in SAVES directory

**Process:**
1. Builds path: `[game_dir]\SAVES\[filename]`
2. Creates SAVES directory if needed
3. Opens file with `CreateFileW`
4. Writes buffer with `WriteFile`

---

#### FUN_005e4970 - OPTIONS File Writer

**Address:** `0x005E4970`
**Purpose:** Writes OPTIONS file to disk

**Calls:** `FUN_005e4860` with path "OPTIONS"

---

#### FUN_005e4c40 - OPTIONS File Reader

**Address:** `0x005E4C40`
**Purpose:** Reads OPTIONS file from disk

**Calls:** `FUN_005e4b10` to load file

---

#### FUN_005e4b10 - Generic File Reader

**Address:** `0x005E4B10`
**Purpose:** Reads any file from SAVES directory

**Process:**
1. Builds path
2. Opens file with `CreateFileW`
3. Gets size with `GetFileSize`
4. Allocates buffer via `FUN_01ae48f0`
5. Reads with `ReadFile`

---

## Save System Orchestration

#### FUN_0046d980 - Save Orchestrator

**Address:** `0x0046D980`
**Purpose:** Main save coordinator with dirty flag processing

**Flag Dispatch:**
| Flag | Action |
|------|--------|
| 0x01/0x02 | Calls `FUN_005e3960()` (Section 1 save) |
| 0x04 | Calls `FUN_005e39a0()` (Section 2 save) |
| 0x08 | Calls `FUN_0046d7b0` (Section 1 reload) |
| 0x10 | Appends via `FUN_0046d8b0` with flag 0x10 |
| 0x40 | Appends via `FUN_0046d8b0` with flag 0x40 |
| 0x80 | Loads Section 1 + saves via `FUN_005e39a0()` |

---

#### FUN_0046e0a0 - Dirty Flag Manager

**Address:** `0x0046E0A0`
**Purpose:** Manages dirty/modified flags and triggers saves

**Calls:** `FUN_0046d980()` if save trigger conditions met

---

## Language System Functions

### Language Table Functions

| Address | Function | Purpose |
|---------|----------|---------|
| 0x01AE38B0 | FUN_01ae38b0 | Language table registration |
| 0x01B005E0 | FUN_01b005e0 | Language system setup |
| 0x01B01F00 | FUN_01b01f00 | Registry registration |
| 0x0040AD40 | FUN_0040ad40 | Registry language detection |
| 0x0040B120 | FUN_0040b120 | Language index distribution |
| 0x01AE3B10 | FUN_01ae3b10 | Global storage (DAT_0298a844) |
| 0x01AE3B20 | FUN_01ae3b20 | Global storage (DAT_0298a848) |
| 0x01AE3B00 | FUN_01ae3b00 | Global storage (DAT_0298a840) |
| 0x01B09C10 | FUN_01b09c10 | Save/Load language data |
| 0x01B82560 | FUN_01b82560 | Index lookup by value |
| 0x01B82590 | FUN_01b82590 | Hash lookup |

---

## Complete Call Hierarchy

### Save Game Flow

```
Game Save Trigger
    |
    v
FUN_0046d980 (Save Orchestrator)
    |
    +-- Section 1 Save Path:
    |   |
    |   v
    |   FUN_0046d710 (Initialize Section 1)
    |       |-- Set Field1 = 0x16
    |       |-- Set Field2 = 0xFEDBAC
    |       |
    |       v
    |   FUN_0046d160 (Write Section 1)
    |       |
    |       +-- FUN_01afe160 (Compression Wrapper)
    |       |       |
    |       |       v
    |       |   FUN_01afdba0 (Main Compression)
    |       |       |
    |       |       v
    |       |   FUN_01b7b050 (Low-Level Compression)
    |       |
    |       +-- FUN_01b7a310 (Write Magic Bytes)
    |       |       |-- Write 0x57FBAA33 @ 0x10
    |       |       |-- Write 0x1004FA99 @ 0x14
    |       |       |-- Write 0x00020001 @ 0x18
    |       |       |-- Write 0x01000080 @ 0x1C
    |       |
    |       +-- FUN_01cdba20 (Compute Adler-32)
    |
    +-- Section 2 Save Path:
    |   |
    |   v
    |   FUN_01712ca0 (Write Section 2)
    |       |-- Set Field2 = 0x03
    |       |-- Set Field3 = 0x11FACE11
    |       |
    |       +-- FUN_01afe160 (Compression)
    |       +-- FUN_0046eb90 (Buffer Resize)
    |       +-- FUN_01b7a310 (Magic Bytes)
    |       +-- FUN_01cdba20 (Checksum)
    |
    +-- Section 3 Save Path:
        |
        v
    FUN_017108e0 (Write Section 3)
        |-- Set Field2 = 0x00
        |-- Set Field3 = 0x21EFFE22
        |
        +-- FUN_01afe160 (Compression)
        +-- FUN_01b7a310 (Magic Bytes)
        +-- FUN_01cdba20 (Checksum)
        |
        v
    FUN_005e4970 (Write OPTIONS File)
        |
        v
    FUN_005e4860 (Write to Disk)
```

### Load Game Flow

```
Game Load Request
    |
    v
FUN_005e4c40 (Read OPTIONS File)
    |
    v
FUN_005e4b10 (Read from Disk)
    |
    +-- Section 1 Load Path:
    |   |
    |   v
    |   FUN_0046d7b0 (Load Section 1)
    |       |
    |       v
    |   FUN_0046d430 (Validate Section 1)
    |       |-- Check Field1 == 0x16
    |       |-- Check Field2 == 0xFEDBAC
    |       |
    |       +-- FUN_01b7a1d0 (Validate Magic)
    |       |       |-- Check 0x57FBAA33 @ buffer+0x04
    |       |       |-- Check 0x1004FA99 @ buffer+0x08
    |       |
    |       +-- FUN_00425360 (Decompress)
    |
    +-- Section 2 Load Path:
    |   |
    |   v
    |   FUN_01712db0 (Validate Section 2)
    |       |-- Check Field2 == 0x03
    |       |-- Check Field3 == 0x11FACE11
    |       |
    |       +-- FUN_00425360 (Decompress)
    |       +-- FUN_01afd600 (Header Processing)
    |
    +-- Section 3 Load Path:
        |
        v
    FUN_017109e0 (Validate Section 3)
        |-- Check Field2 == 0x00
        |-- Check Field3 == 0x21EFFE22
        |
        +-- FUN_00425360 (Decompress)
        +-- FUN_01afd600 (Header Processing)
```

---

## Function-to-Field Mapping

### Section 1 Field Access

| Offset | Field | Writing Function | Reading Function |
|--------|-------|------------------|------------------|
| 0x00 | Field1 (0x16) | FUN_0046d710 | FUN_0046d430 |
| 0x04 | Field2 (0xFEDBAC) | FUN_0046d710 | FUN_0046d430 |
| 0x51 | Profile State Flag | (Unknown) | (Unknown) |

### Section 2 Field Access

| Offset | Field | Function Reference |
|--------|-------|-------------------|
| 0x63 | Subtitles Toggle | FUN_004391f0, FUN_00439250 |
| 0x75 | Default Language Flag | FUN_0040cfc0, FUN_0040d880 |
| 0xC0-0xC3 | Music Volume | FUN_00acf240 |
| 0xD5-0xD8 | Voice Volume | FUN_00504240, FUN_0084e720 |
| 0xEA-0xED | SFX Volume | FUN_007a1320 |
| 0xFF | Vibration | FUN_00acf240 |
| 0x111-0x114 | X Look Sensitivity | FUN_00417fc0 |
| 0x13B | 3rd Person Invert X | FUN_00a82210 |
| 0x195 | Brightness | FUN_00acf240 |
| 0x1DD | Cannon Invert Y | FUN_00acf240 |
| 0x237 | Mini-Map | FUN_00acf240 |
| 0x369 | Costume Bitfield | FUN_00acf240 |

### Section 3 Field Access

| Offset | Field | Function Reference |
|--------|-------|-------------------|
| 0x4E | Uplay Gun Upgrade | (Unknown) |
| 0x9D (PC) / 0x5A (PS3) | DLC Sync Flag | FUN_0084ca20, FUN_0084cb60 |

---

## Virtual Function Tables

### PTR_FUN_02411ef0 - I/O Handler Vtable

**Address:** `0x02411EF0`

| Offset | Function | Purpose |
|--------|----------|---------|
| 0x00 | FUN_009ca4c0 | Destructor |
| 0x04 | FUN_005e4950 | Write "assassin.sav" |
| 0x08 | FUN_005e4c20 | Read "assassin.sav" |
| 0x0C | FUN_005e4970 | Write "OPTIONS" |
| 0x10 | FUN_005e4c40 | Read "OPTIONS" |

### PTR_FUN_0253df30 - AssassinGlobalProfileData Vtable

**Address:** `0x0253DF30`

| Offset | Function | Purpose |
|--------|----------|---------|
| 0x04 | FUN_01712930 | Serializer |
| 0x24 | FUN_01712ca0 | Section 2 Writer |

### PTR_FUN_0253de0c - Section 3 Vtable

**Address:** `0x0253DE0C`

| Offset | Function | Purpose |
|--------|----------|---------|
| 0x24 | FUN_017108e0 | Section 3 Writer |

---

## Key Memory Addresses

### Compression Engine

| Address | Purpose |
|---------|---------|
| 0x0223E140 | Compression entry point |
| 0x0223E0A0 | Match finder function |
| 0x0223E1EB | Offset loading for encoding |
| 0x0223E463 | Long match encoding start |
| 0x0223E463-0x0223E47A | Long match encoding sequence |

### Language System

| Address | Purpose |
|---------|---------|
| 0x0298A780 | Language hash table |
| 0x0298A830 | Language table pointer |
| 0x0298A840 | Global language storage 1 |
| 0x0298A844 | Global language storage 2 |
| 0x0298A848 | Global language storage 3 |

---

## Notes

1. **Function Naming:** All functions use Ghidra's auto-generated names (FUN_XXXXXXXX format)
2. **Address Format:** Addresses are given as file offsets in ACBSP.exe
3. **Runtime Calculation:** Runtime address = Base Address + File Offset
4. **Common Base:** Runtime base observed at 0x00AB0000 in debug sessions
5. **Compression Addresses:** Compression functions at 0x0223XXXX are within the main module

---

**End of Document**
