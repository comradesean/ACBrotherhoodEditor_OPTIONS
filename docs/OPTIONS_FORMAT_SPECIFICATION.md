# Assassin's Creed Brotherhood OPTIONS File Format Specification

**Document Version:** 2.2
**Date:** 2026-01-06
**Status:** Formal Technical Specification (Section 1 Record Structure Updated)
**Research Method:** WinDbg Time-Travel Debugging + Ghidra Decompilation + 24-File Differential Analysis

---

## Table of Contents

1. [Overview and Scope](#1-overview-and-scope)
2. [File Layout Diagram](#2-file-layout-diagram)
3. [Section Header Structure](#3-section-header-structure)
4. [Section-by-Section Breakdown](#4-section-by-section-breakdown)
5. [Data Type Definitions](#5-data-type-definitions)
6. [Hash Reference Table](#6-hash-reference-table)
7. [Validation and Checksums](#7-validation-and-checksums)
8. [Compression Format Summary](#8-compression-format-summary)
9. [Platform Differences (PC vs PS3)](#9-platform-differences-pc-vs-ps3)
10. [Annotated Hex Dump Examples](#10-annotated-hex-dump-examples)
11. [Appendix: Complete Magic Number Reference](#11-appendix-complete-magic-number-reference)

---

## 1. Overview and Scope

### 1.1 Purpose

This document provides a complete, formal technical specification for the Assassin's Creed Brotherhood OPTIONS binary save file format. The specification is intended to enable:

- Implementation of parsers and serializers
- Modification of game settings and save data
- Cross-platform save conversion (PC to PS3 and vice versa)
- Research and documentation purposes

### 1.2 Format Summary

| Property | PC Version | PS3 Version |
|----------|------------|-------------|
| File Extension | `.bin` or no extension | `.PS3` or no extension |
| Number of Sections | 3 | 4 |
| Fixed Size | No (variable, ~1028 bytes) | Yes (51,200 bytes) |
| Endianness | Little-endian | Mixed (header fields BE, data LE) |
| Compression | LZSS variant | LZSS variant (identical) |
| Checksum | Zero-seed Adler-32 | Zero-seed Adler-32 + CRC32 prefix |

### 1.3 Section Purposes

| Section | Name | Purpose | PC Size | PS3 Size |
|---------|------|---------|---------|----------|
| 1 | System/Profile | Platform identification, profile metadata | 283 bytes | 289 bytes |
| 2 | Game Settings | Audio, video, control settings, unlocks | 1310 bytes | 1306 bytes |
| 3 | Game Progress | Achievements, Uplay rewards, DLC flags | 162 bytes | 119 bytes |
| 4 | Controller Mappings | DualShock 3 button mappings (PS3 only) | N/A | 1903 bytes |

---

## 2. File Layout Diagram

### 2.1 PC OPTIONS File Layout

```
+===============================================+ 0x0000
|              SECTION 1                        |
|   +---------------------------------------+   |
|   | Header (44 bytes)                     |   |
|   |   Field0: 0x00000016                  |   |
|   |   Field1: 0x00FEDBAC                  |   |
|   |   Field2: 0x000000C5                  |   |
|   |   Field3: uncompressed_size           |   |
|   |   Magic1-4: format signatures         |   |
|   |   Field5: compressed_size             |   |
|   |   Field6: uncompressed_size           |   |
|   |   Field7: checksum                    |   |
|   +---------------------------------------+   |
|   | Compressed Data                       |   |
|   |   Prefix: 06 00 E1 00                 |   |
|   |   LZSS data...                        |   |
|   |   Terminator: 20 00                   |   |
|   +---------------------------------------+   |
+===============================================+
|              SECTION 2                        |
|   +---------------------------------------+   |
|   | Header (44 bytes)                     |   |
|   |   Field0: compressed_size + 40        |   |
|   |   Field1: 0x00000003                  |   |
|   |   Field2: 0x11FACE11                  |   |
|   |   ...                                 |   |
|   +---------------------------------------+   |
|   | Compressed Data                       |   |
|   +---------------------------------------+   |
+===============================================+
|              SECTION 3                        |
|   +---------------------------------------+   |
|   | Header (44 bytes)                     |   |
|   |   Field0: compressed_size + 40        |   |
|   |   Field1: 0x00000000                  |   |
|   |   Field2: 0x21EFFE22                  |   |
|   |   ...                                 |   |
|   +---------------------------------------+   |
|   | Compressed Data                       |   |
|   +---------------------------------------+   |
+===============================================+
|              FOOTER (5 bytes)                 |
|   01 00 00 00 XX                              |
|   XX = Network interface count (telemetry)    |
+===============================================+
```

### 2.2 PS3 OPTIONS File Layout

```
+===============================================+ 0x0000
|        8-BYTE PREFIX (Big-Endian)             |
|   Bytes 0-3: Data size (sections total)       |
|   Bytes 4-7: CRC32 of section data            |
+===============================================+ 0x0008
|              SECTION 1                        |
|   Header (44 bytes) - Fields 0-2 are BE       |
|   Compressed Data                             |
+===============================================+
|              SECTION 2                        |
|   Header (44 bytes)                           |
|   Compressed Data                             |
+===============================================+
|              SECTION 3                        |
|   Header (44 bytes)                           |
|   Compressed Data                             |
+===============================================+
|        8-BYTE GAP MARKER (Big-Endian)         |
|   Bytes 0-3: Section 4 size + 4               |
|   Bytes 4-7: 0x00000008 (type marker)         |
+===============================================+
|              SECTION 4 (PS3 Only)             |
|   Header (44 bytes)                           |
|   Compressed Data                             |
+===============================================+
|              ZERO PADDING                     |
|   (to reach exactly 51,200 bytes)             |
+===============================================+ 0xC800
```

---

## 3. Section Header Structure

### 3.1 C Structure Definition

```c
/* OPTIONS Section Header - 44 bytes (0x2C) */
typedef struct {
    /* First 3 fields vary by section and platform */
    uint32_t field0;          /* 0x00: Section-specific (see table) */
    uint32_t field1;          /* 0x04: Section type identifier */
    uint32_t field2;          /* 0x08: Section magic marker */

    /* Uncompressed size */
    uint32_t uncompressed_size_1;  /* 0x0C: Uncompressed data size */

    /* Universal magic bytes - constant across all sections */
    uint32_t magic1;          /* 0x10: 0x57FBAA33 - Format signature */
    uint32_t magic2;          /* 0x14: 0x1004FA99 - Version identifier */
    uint32_t magic3;          /* 0x18: 0x00020001 - Compression params */
    uint32_t magic4;          /* 0x1C: 0x01000080 - Version flags */

    /* Size and checksum fields */
    uint32_t compressed_size;      /* 0x20: Compressed data size */
    uint32_t uncompressed_size_2;  /* 0x24: Duplicate of field at 0x0C */
    uint32_t checksum;             /* 0x28: Zero-seed Adler-32 */
} OPTIONS_SectionHeader;

_Static_assert(sizeof(OPTIONS_SectionHeader) == 44, "Header must be 44 bytes");
```

### 3.2 Field Values by Section

| Offset | Field | Section 1 (PC) | Section 1 (PS3) | Section 2 | Section 3 | Section 4 (PS3) |
|--------|-------|----------------|-----------------|-----------|-----------|-----------------|
| 0x00 | Field0 | `0x00000016` | `0x00000016` | `comp_sz + 40` | `comp_sz + 40` | `0x22FEEF21` |
| 0x04 | Field1 | `0x00FEDBAC` | `0x00FEDBAC` | `0x00000003` | `0x00000000` | `0x00000004` |
| 0x08 | Field2 | `0x000000C5` | `0x000000C6` | `0x11FACE11` | `0x21EFFE22` | `0x00000007` |
| 0x0C | Field3 | uncompressed | uncompressed | uncompressed | uncompressed | uncompressed |
| 0x10 | Magic1 | `0x57FBAA33` | `0x57FBAA33` | `0x57FBAA33` | `0x57FBAA33` | `0x57FBAA33` |
| 0x14 | Magic2 | `0x1004FA99` | `0x1004FA99` | `0x1004FA99` | `0x1004FA99` | `0x1004FA99` |
| 0x18 | Magic3 | `0x00020001` | `0x00020001` | `0x00020001` | `0x00020001` | `0x00020001` |
| 0x1C | Magic4 | `0x01000080` | `0x01000080` | `0x01000080` | `0x01000080` | `0x01000080` |
| 0x20 | Field5 | compressed_sz | compressed_sz | compressed_sz | compressed_sz | compressed_sz |
| 0x24 | Field6 | uncompressed | uncompressed | uncompressed | uncompressed | uncompressed |
| 0x28 | Field7 | checksum | checksum | checksum | checksum | checksum |

### 3.3 PS3 Header Byte Order

For PS3 files, fields 0-2 (bytes 0x00-0x0B) are stored in **big-endian** byte order. All other fields (0x0C onwards) remain **little-endian**.

```c
/* Reading PS3 header */
header.field0 = read_uint32_be(buffer + 0x00);  /* Big-endian */
header.field1 = read_uint32_be(buffer + 0x04);  /* Big-endian */
header.field2 = read_uint32_be(buffer + 0x08);  /* Big-endian */
header.uncompressed_size_1 = read_uint32_le(buffer + 0x0C);  /* Little-endian */
/* ... remaining fields little-endian ... */
```

---

## 4. Section-by-Section Breakdown

### 4.1 Section 1: System/Profile Data

**Identification:**
- Field0: `0x00000016` (magic number, value 22 decimal)
- Field1: `0x00FEDBAC` (validation marker)
- Field2: `0x000000C5` (PC) or `0x000000C6` (PS3)

**Uncompressed Size:** 283 bytes (PC) / 289 bytes (PS3)

**Class Name:** Unknown (minimal Ghidra coverage)

#### 4.1.1 Header Region (0x00-0x17)

| Offset | Size | Type | Field Name | Value | Confidence |
|--------|------|------|------------|-------|------------|
| 0x00-0x09 | 10 | bytes | Zero Padding | `0x00` | PROVEN |
| 0x0A-0x0D | 4 | hash | Section Hash | `0xBDBE3B52` | PROVEN |
| 0x0E-0x0F | 2 | flags | Version Flags | v1.0=`0x0508`, v1.05=`0x050C` | HIGH |
| 0x10-0x13 | 4 | value | Unknown | Varies | LOW |
| 0x14-0x17 | 4 | type | Type Indicator | `0x00010000` | MEDIUM |

#### 4.1.2 Property Record Structure

**IMPORTANT:** Section 1 uses **21-byte records**, NOT 18-byte records like Sections 2 and 3.

Section 1 contains **12 records** with 0x0B markers at the following PC offsets:
`0x26, 0x3B, 0x50, 0x65, 0x7A, 0x8F, 0xA1, 0xBE, 0xD3, 0xE8, 0xFD, 0x112`

**Record Distance Analysis:**
- Most records: 21 bytes (0x15 spacing)
- Record 6 @ 0x8F: 18 bytes (exception)
- Record 7 @ 0xA1: 29 bytes (exception - contains "Options" ASCII string)

```c
/* Section 1 Property Record - 21 bytes (standard)
 * NOTE: Section 1 uses 21-byte records, unlike Sections 2/3 which use 18-byte records.
 * Two exceptions exist: Record 6 (18 bytes) and Record 7 (29 bytes with "Options" string).
 */
typedef struct {
    uint8_t      marker;          /* +0x00: 0x0B = record start marker */
    uint8_t      value[4];        /* +0x01-0x04: Value (4 bytes) */
    uint8_t      type;            /* +0x05: Type field (0x11, 0x0E, or 0x4F) */
    uint8_t      padding1[3];     /* +0x06-0x08: Padding (00 00 00) */
    uint32_t     hash;            /* +0x09-0x0C: Hash/ID (4 bytes) */
    uint8_t      trailer[8];      /* +0x0D-0x14: Padding/trailer (8 bytes) */
} Section1_PropertyRecord;
```

**Type Field Values:**
- 0x11: Most common type
- 0x0E: Boolean-style type (same as Sections 2/3)
- 0x4F: Special type (Record 7 with "Options" string)

**PS3 Confirmation:** PS3 Section 1 follows the same record distance pattern, with offsets shifted by 6 bytes due to PS3 header prefix.

**Purpose:** Unknown. The specific purpose of Section 1 records has not been determined.

#### 4.1.3 Profile State Flag

| Offset | Size | Type | Field Name | Value | Confidence |
|--------|------|------|------------|-------|------------|
| 0x51 | 1 | byte | Profile State Flag | 0x02 (base), 0x06 (all rewards) | HIGH |

This is the **only byte that differs** between base game and all-rewards-unlocked OPTIONS files for the same platform/language.

#### 4.1.4 "Options" String Location

The ASCII string "Options" appears at offset 0xA6-0xAD in the decompressed Section 1 data:

```
0xA6: 4F 70 74 69 6F 6E 73 00  "Options\0"
```

#### 4.1.5 PC vs PS3 Size Difference

| Platform | Size | Field2 | Notes |
|----------|------|--------|-------|
| PC | 283 bytes | 0xC5 | Standard |
| PS3 | 289 bytes | 0xC6 | +6 bytes (unknown purpose) |

### 4.2 Section 2: Game Settings

**Identification:**
- Field0: `compressed_size + 40`
- Field1: `0x00000003` (type ID: Configuration)
- Field2: `0x11FACE11` (section magic)

**Uncompressed Size:** 1310 bytes (PC) / 1306 bytes (PS3)

#### 4.2.1 C Structure Definition

```c
/* Section 2 Game Settings Structure */
typedef struct {
    /* Header region */
    uint8_t  zero_padding[10];       /* 0x00-0x09: Zero padding */
    uint32_t section_hash;           /* 0x0A-0x0D: 0x305AE1A8 */
    uint16_t version_flags;          /* 0x0E-0x0F: v1.0=0x0508, v1.05=0x050C */
    uint8_t  reserved1[4];           /* 0x10-0x13 */
    uint32_t type_indicator;         /* 0x14-0x17: 0x00110000 */
    uint8_t  reserved2[75];          /* 0x18-0x62 */

    /* Display settings */
    uint8_t  subtitles_enabled;      /* 0x63: Boolean (0/1) */
    uint8_t  reserved3[17];          /* 0x64-0x74 */
    uint8_t  default_language_flag;  /* 0x75: Boolean (0/1) */
    uint8_t  reserved4[24];          /* 0x76-0x8D */

    /* Language settings */
    uint32_t audio_language_index;   /* 0x8E-0x91: 1-20 */
    uint32_t audio_language_hash;    /* 0x92-0x95: Language hash */
    uint8_t  reserved5[17];          /* 0x96-0xA6 */
    uint32_t subtitle_language_index;/* 0xA7-0xAA: 1-20 */
    uint32_t subtitle_language_hash; /* 0xAB-0xAE: Language hash */
    uint8_t  reserved6[17];          /* 0xAF-0xBF */

    /* Audio settings */
    float    music_volume;           /* 0xC0-0xC3: dB scale (-96.0 to 0.0) */
    uint8_t  reserved7[17];          /* 0xC4-0xD4 */
    float    voice_volume;           /* 0xD5-0xD8: dB scale */
    uint8_t  reserved8[17];          /* 0xD9-0xE9 */
    float    sfx_volume;             /* 0xEA-0xED: dB scale */
    uint8_t  reserved9[17];          /* 0xEE-0xFE */
    uint8_t  vibration_enabled;      /* 0xFF: Boolean (0/1) */

    /* Control settings */
    uint8_t  reserved10[17];         /* 0x100-0x110 */
    float    x_look_sensitivity;     /* 0x111-0x114: 0.5x to 2.0x */
    uint8_t  reserved11[17];         /* 0x115-0x125 */
    float    y_look_sensitivity;     /* 0x126-0x129: 0.5x to 2.0x */
    uint8_t  reserved12[17];         /* 0x12A-0x13A */
    uint8_t  invert_3p_x;            /* 0x13B: Boolean (0/1) */
    uint8_t  reserved13[17];         /* 0x13C-0x14C */
    uint8_t  invert_3p_y;            /* 0x14D: Boolean (0/1) */
    uint8_t  reserved14[17];         /* 0x14E-0x15E */
    uint8_t  invert_1p_x;            /* 0x15F: Boolean (0/1) */
    uint8_t  reserved15[17];         /* 0x160-0x170 */
    uint8_t  invert_1p_y;            /* 0x171: Boolean (0/1) */
    uint8_t  reserved16[17];         /* 0x172-0x182 */
    uint8_t  action_camera_freq;     /* 0x183: 0-3 */
    uint8_t  reserved17[17];         /* 0x184-0x194 */
    uint8_t  brightness;             /* 0x195: 1-16 */
    uint8_t  reserved18[17];         /* 0x196-0x1A6 */
    uint8_t  blood_enabled;          /* 0x1A7: Boolean (0/1) */
    uint8_t  reserved19[17];         /* 0x1A8-0x1B8 */
    uint8_t  flying_machine_invert;  /* 0x1B9: Boolean (0/1) */
    uint8_t  reserved20[17];         /* 0x1BA-0x1CA */
    uint8_t  cannon_invert_x;        /* 0x1CB: Boolean (0/1) */
    uint8_t  reserved21[17];         /* 0x1CC-0x1DC */
    uint8_t  cannon_invert_y;        /* 0x1DD: Boolean (0/1) */
    uint8_t  reserved22[17];         /* 0x1DE-0x1EE */

    /* HUD settings - 18-byte record structure */
    uint8_t  hud_health_meter;       /* 0x1EF: Boolean (0/1) */
    uint8_t  hud_health_data[17];    /* 0x1F0-0x200 */
    uint8_t  hud_controls;           /* 0x201: Boolean (0/1) */
    uint8_t  hud_controls_data[17];  /* 0x202-0x212 */
    uint8_t  hud_updates;            /* 0x213: Boolean (0/1) */
    uint8_t  hud_updates_data[17];   /* 0x214-0x224 */
    uint8_t  hud_weapon;             /* 0x225: Boolean (0/1) */
    uint8_t  hud_weapon_data[17];    /* 0x226-0x236 */
    uint8_t  hud_minimap;            /* 0x237: Boolean (0/1) */
    uint8_t  hud_minimap_data[17];   /* 0x238-0x248 */
    uint8_t  hud_money;              /* 0x249: Boolean (0/1) */
    uint8_t  hud_money_data[35];     /* 0x24A-0x26C */
    uint8_t  hud_ssi;                /* 0x26D: Boolean (0/1) */
    uint8_t  hud_ssi_data[17];       /* 0x26E-0x27E */
    uint8_t  hud_tutorial;           /* 0x27F: Boolean (0/1) */
    uint8_t  hud_tutorial_data[17];  /* 0x280-0x290 */

    /* Unlock records - see UnlockRecord structure */
    /* 0x291+: Array of 18-byte unlock records */

    /* Costume bitfield at 0x369 */
    /* DLC flags at 0x516-0x519 */

} Section2_GameSettings;
```

#### 4.2.2 Unlock Record Structure (18 bytes)

```c
typedef struct {
    uint8_t  marker;          /* +0x00: 0x0B (structure marker) */
    uint8_t  unlock_flag;     /* +0x01: 0x00=locked, 0x01=unlocked */
    uint8_t  type;            /* +0x02: Category (0x0E for rewards) */
    uint8_t  reserved[3];     /* +0x03-0x05: Zeros */
    uint8_t  hash_prefix;     /* +0x06: High byte related to content hash encoding */
    uint32_t content_hash;    /* +0x07-0x0A: Content identifier (LE) */
    uint8_t  padding[7];      /* +0x0B-0x11: Zeros */
} UnlockRecord;

_Static_assert(sizeof(UnlockRecord) == 18, "UnlockRecord must be 18 bytes");

/* Note: Records start at offset 0x290, NOT 0x291. The documented offsets
   (0x291, 0x2A3, etc.) point to the unlock_flag byte within each record.
   The hash_prefix byte (+0x06) contains values like 0xCC, 0x8F, 0x9F, etc.
   which appear related to the content hash encoding but are not part of
   the hash value itself. */
```

#### 4.2.3 Known Unlock Records

| Offset | Name | Hash | Description |
|--------|------|------|-------------|
| 0x291 | Templar Lair 1 | `0x00788F42` | Trajan's Market |
| 0x2A3 | Templar Lair 2 | `0x006FF456` | Tivoli Aqueduct |
| 0x2B5 | Unknown #1 | `0x000B953B` | Discovered via differential analysis |
| 0x2C7 | Unknown #2 | `0x001854EC` | Discovered via differential analysis |
| 0x2D9 | Possibly Uplay | `0x0021D9D0` | Purpose unknown (flips in Uplay test files) |
| 0x2EB | Possibly Uplay | `0x0036A2C4` | Purpose unknown (flips in Uplay test files) |
| 0x2FD | Possibly Uplay | `0x0052C3A9` | Purpose unknown (flips in Uplay test files) |
| 0x30F | Possibly Uplay | `0x000E8D04` | Purpose unknown (flips in Uplay test files) |

**Note:** Unknown records #1 and #2 were discovered through 21-file language differential analysis. Hashes do not match known Uplay or DLC content - possibly beta/cut content or region-specific unlocks.

#### 4.2.4 Costume Record (18 bytes starting at 0x368)

**IMPORTANT:** The costume bitfield at 0x369 is NOT a standalone byte. It is the VALUE byte within an 18-byte property record starting at offset 0x368. This record uses **Type 0x00** (bitfield/complex), not Type 0x0E (boolean).

**Binary verified:** `0B 3F 00 00 00 00 00 00 3D 00 00 00 C2 EA 86 02 96 CE`

```c
/* Costume Record - 18 bytes starting at offset 0x368
 * The "bitfield" at 0x369 is the VALUE byte within this record.
 */
typedef struct {
    uint8_t  marker;          /* +0x00 (0x368): 0x0B - record start */
    uint8_t  costume_value;   /* +0x01 (0x369): costume bitfield (0x00-0x3F) */
    uint8_t  type;            /* +0x02 (0x36A): 0x00 - Type 0x00 (bitfield/complex) */
    uint8_t  padding[3];      /* +0x03-0x05: zeros */
    uint32_t property_hash;   /* +0x06-0x09: property hash (LE) */
    uint8_t  type_data[8];    /* +0x0A-0x11: type-specific data */
} CostumeRecord;

/* Costume bitfield bit definitions (value at offset 0x369) */
#define COSTUME_FLORENTINE_NOBLE  0x01  /* Bit 0 - Uplay */
#define COSTUME_ARMOR_OF_ALTAIR   0x02  /* Bit 1 - Uplay */
#define COSTUME_ALTAIRS_ROBES     0x04  /* Bit 2 - Uplay */
#define COSTUME_DRACHEN_ARMOR     0x08  /* Bit 3 - Preorder */
#define COSTUME_DESMOND           0x10  /* Bit 4 - In-game */
#define COSTUME_RAIDEN            0x20  /* Bit 5 - In-game */
#define COSTUME_ALL_UNLOCKED      0x3F  /* All 6 costumes */
```

#### 4.2.5 Volume Level Values

| Slider | Hex Value | Float (dB) | Description |
|--------|-----------|------------|-------------|
| 10 | `0x00000000` | 0.0 | Maximum |
| 9 | `0xBF6A4744` | -0.916 | |
| 8 | `0xBFF816F0` | -1.938 | |
| 7 | `0xC0464646` | -3.098 | |
| 6 | `0xC08DFBB2` | -4.437 | |
| 5 | `0xC0C0A8C0` | -6.020 | Default |
| 4 | `0xC0FEAE7C` | -7.958 | |
| 3 | `0xC1275239` | -10.457 | |
| 2 | `0xC15FAB9E` | -13.979 | |
| 1 | `0xC19FFFFF` | -19.999 | |
| 0 | `0xC2C00000` | -96.0 | Mute |

#### 4.2.6 Sensitivity Level Values

| Level | Hex Value | Multiplier |
|-------|-----------|------------|
| 10 | `0x40000000` | 2.0x |
| 9 | `0x3FE66666` | 1.8x |
| 8 | `0x3FCCCCCD` | 1.6x |
| 7 | `0x3FB33333` | 1.4x |
| 6 | `0x3F99999A` | 1.2x |
| 5 | `0x3F800000` | 1.0x (Default) |
| 4 | `0x3F4CCCCD` | 0.8x |
| 3 | `0x3F333333` | 0.7x |
| 2 | `0x3F19999A` | 0.6x |
| 1 | `0x3F000000` | 0.5x |

### 4.3 Section 3: Game Progress

**Identification:**
- Field0: `compressed_size + 40`
- Field1: `0x00000000` (type ID: State)
- Field2: `0x21EFFE22` (section magic)

**Uncompressed Size:** 162 bytes (PC) / 119 bytes (PS3)

**Class Name:** `AssassinSingleProfileData` (address 0x0253ddec in executable)

#### 4.3.1 Header Region (0x00-0x17)

| Offset | Size | Type | Field Name | Value | Confidence |
|--------|------|------|------------|-------|------------|
| 0x00-0x09 | 10 | bytes | Zero Padding | `0x00` | PROVEN |
| 0x0A-0x0D | 4 | hash | Section Hash | `0xC9876D66` | HIGH |
| 0x0E-0x0F | 2 | flags | Version Flags | v1.0=`0x0508`, v1.05=`0x050C` | HIGH |
| 0x10-0x13 | 4 | value | Unknown | Varies | LOW |
| 0x14-0x17 | 4 | type | Type Indicator | `0x00010000` | MEDIUM |

#### 4.3.2 C Structure Definition

```c
typedef struct {
    /* Header region */
    uint8_t  zero_padding[10];       /* 0x00-0x09: Zero padding */
    uint32_t section_hash;           /* 0x0A-0x0D: 0xC9876D66 */
    uint16_t version_flags;          /* 0x0E-0x0F: v1.0=0x0508, v1.05=0x050C */
    uint8_t  reserved0[8];           /* 0x10-0x17: Unknown */

    /* Property records region (uses same 18-byte structure as Sections 1 & 2) */
    uint8_t  reserved1[53];          /* 0x18-0x4C: Unknown */

    /* Gun Capacity Upgrade Record - 18 bytes starting at 0x4D
     * Binary verified: 0B 01 0E 00 00 00 ...
     * This is the VALUE byte within an 18-byte record, NOT a standalone marker.
     */
    uint8_t  gun_record_marker;      /* 0x4D: 0x0B (record start marker) */
    uint8_t  uplay_gun_upgrade;      /* 0x4E: Boolean value - 30-point Uplay reward */
    uint8_t  gun_record_type;        /* 0x4F: 0x0E (Type 0x0E = boolean record) */
    uint8_t  reserved2[48];          /* 0x50-0x7F: Unknown */

    /* Achievement region - PC ONLY */
    uint8_t  achievement_header[4];  /* 0x80-0x83: 00 09 00 0B */
    uint8_t  achievements[7];        /* 0x84-0x8A: 53-bit achievement bitfield */
    uint8_t  padding_0x8b;           /* 0x8B: 0x00 */
    uint32_t marker_0x8c;            /* 0x8C-0x8F: 0x0000000E */
    uint32_t progress_hash;          /* 0x90-0x93: 0x6F88B05B */
    uint8_t  reserved3[8];           /* 0x94-0x9B: Unknown */
    uint8_t  marker_0x9c;            /* 0x9C: 0x0B (constant marker) */
    uint8_t  dlc_sync_flag;          /* 0x9D: Boolean - DLC synchronization */
    uint8_t  reserved4[2];           /* 0x9E-0x9F: Padding */
    /* PC has additional bytes here */
} Section3_GameProgress;
```

#### 4.3.3 PC vs PS3 Size Difference (43 bytes)

| Platform | Size | Achievement Storage | Explanation |
|----------|------|---------------------|-------------|
| PC | 162 bytes | Embedded 7-byte bitfield at 0x84-0x8A | 53 achievements stored locally |
| PS3 | 119 bytes | **No embedded bitfield** | PSN Trophy system handles achievements externally |

The **43-byte difference** is explained by:
1. PC embeds achievement bitfield (7 bytes) plus surrounding structure/markers (~36 bytes overhead)
2. PS3 relies on PlayStation Network Trophy API for achievement tracking
3. PS3 Section 3 stores only cross-platform progress data (Uplay rewards, DLC sync)
4. DLC Sync Flag on PS3 is at offset 0x5A (instead of PC's 0x9D)

#### 4.3.4 Achievement Bitfield (0x84-0x8A, PC Only)

The achievement bitfield uses 53 bits across 7 bytes. All achievements unlocked: `FF FF FF FF FF FF 1F`

**Byte 0x84 (Achievements 1-8):**

| Bit | Hex | Achievement |
|-----|-----|-------------|
| 0 | 0x01 | TECHNICAL DIFFICULTIES |
| 1 | 0x02 | BATTLE WOUNDS |
| 2 | 0x04 | SANCTUARY! SANCTUARY! |
| 3 | 0x08 | ROME IN RUINS |
| 4 | 0x10 | FIXER-UPPER |
| 5 | 0x20 | PRINCIPESSA IN ANOTHER CASTELLO |
| 6 | 0x40 | FUNDRAISER |
| 7 | 0x80 | FORGET PARIS |

**Byte 0x85 (Achievements 9-16):**

| Bit | Hex | Achievement |
|-----|-----|-------------|
| 0 | 0x01 | BLOODY SUNDAY |
| 1 | 0x02 | VITTORIA AGLI ASSASSINI |
| 2 | 0x04 | REQUIESCAT IN PACE |
| 3 | 0x08 | A KNIFE TO THE HEART |
| 4 | 0x10 | PERFECT RECALL |
| 5 | 0x20 | DEJA VU |
| 6 | 0x40 | UNDERTAKER 2.0 |
| 7 | 0x80 | GOLDEN BOY |

**Byte 0x86 (Achievements 17-24):**

| Bit | Hex | Achievement |
|-----|-----|-------------|
| 0 | 0x01 | GLADIATOR |
| 1 | 0x02 | PLUMBER |
| 2 | 0x04 | ONE-MAN WRECKING CREW |
| 3 | 0x08 | AMEN |
| 4 | 0x10 | BANG! |
| 5 | 0x20 | SPLASH! |
| 6 | 0x40 | BOOM! |
| 7 | 0x80 | KABOOM! |

**Byte 0x87 (Achievements 25-32):**

| Bit | Hex | Achievement |
|-----|-----|-------------|
| 0 | 0x01 | HOME IMPROVEMENT |
| 1 | 0x02 | TOWER DEFENSE |
| 2 | 0x04 | SHOW OFF |
| 3 | 0x08 | .. .- -- .- .-.. .. ...- . (IAMALIVE) |
| 4 | 0x10 | PERFECTIONIST |
| 5 | 0x20 | BROTHERHOOD |
| 6 | 0x40 | WELCOME TO THE BROTHERHOOD |
| 7 | 0x80 | CAPTURE THE FLAG |

**Byte 0x88 (Achievements 33-40):**

| Bit | Hex | Achievement |
|-----|-----|-------------|
| 0 | 0x01 | IN MEMORIAM |
| 1 | 0x02 | DUST TO DUST |
| 2 | 0x04 | SERIAL KILLER |
| 3 | 0x08 | SPRING CLEANING |
| 4 | 0x10 | YOUR WISH IS GRANTED |
| 5 | 0x20 | FLY LIKE AN EAGLE |
| 6 | 0x40 | THE GLOVES COME OFF |
| 7 | 0x80 | MAILER DAEMON |

**Byte 0x89 (Achievements 41-48):**

| Bit | Hex | Achievement |
|-----|-----|-------------|
| 0 | 0x01 | ROME GLOBAL ECONOMY BRONZE |
| 1 | 0x02 | ROME GLOBAL ECONOMY SILVER |
| 2 | 0x04 | ROME GLOBAL ECONOMY GOLD |
| 3 | 0x08 | STRONG-ARM |
| 4 | 0x10 | HIGH ROLLER |
| 5 | 0x20 | IL PRINCIPE |
| 6 | 0x40 | AIRSTRIKE |
| 7 | 0x80 | GPS |

**Byte 0x8A (Achievements 49-53):**

| Bit | Hex | Achievement |
|-----|-----|-------------|
| 0 | 0x01 | CLOWNING AROUND |
| 1 | 0x02 | SPECIAL DELIVERY |
| 2 | 0x04 | GRAND THEFT DRESSAGE |
| 3 | 0x08 | GOING UP |
| 4 | 0x10 | EASY COME, EASY GO |
| 5-7 | 0xE0 | (Unused) |

### 4.4 Section 4: Controller Mappings (PS3 Only)

**Identification:**
- Field0: `0x22FEEF21` (previous section ID byte-swapped)
- Field1: `0x00000004` (section number)
- Field2: `0x00000007` (section identifier)

**Uncompressed Size:** 1903 bytes

#### 4.4.1 Overall Structure

| Component | Offset | Size | Description |
|-----------|--------|------|-------------|
| Header | 0x00-0x60 | 97 bytes | General controller settings |
| Button Records | 0x61-0x5EB | 1445 bytes | 17 records x 85 bytes each |
| Trailer | 0x5EC-0x76E | 361 bytes | Additional settings + padding |

#### 4.4.2 Button Mapping Record (85 bytes)

```c
typedef struct {
    uint8_t  signature[5];    /* 0x00-0x04: A8 CF 5F F9 43 */
    uint32_t value1;          /* 0x05-0x08: 0x0000003B (constant) */
    uint32_t value2;          /* 0x09-0x0C: 0x00000011 (constant) */
    uint32_t controller_id;   /* 0x0D-0x10: C0 B2 57 81 */
    uint8_t  reserved[10];    /* 0x11-0x1A: Zeros */
    uint16_t field_marker;    /* 0x1B-0x1C: 0x0006 */
    uint8_t  button_id;       /* 0x1D: Button/action identifier */
    uint8_t  mapping_data[67];/* 0x1E-0x54: Additional mapping data */
} PS3_ButtonRecord;
```

#### 4.4.3 Button IDs

| ID | Hex | DualShock 3 Button |
|----|-----|--------------------|
| 2 | 0x02 | Cross (X) |
| 5 | 0x05 | L1 |
| 7 | 0x07 | R1 |
| 8 | 0x08 | L2 |
| 10 | 0x0A | R2 |
| 14 | 0x0E | D-Pad |
| 17 | 0x11 | Left Stick |
| 18 | 0x12 | Right Stick |
| 20 | 0x14 | Select |
| 21 | 0x15 | Triangle |
| 22 | 0x16 | Circle |
| 25 | 0x19 | Square |
| 28 | 0x1C | Start |
| 31 | 0x1F | L3 |
| 32 | 0x20 | R3 |
| 34 | 0x22 | PS Button |

---

## 5. Data Type Definitions

### 5.1 Boolean Type

```c
typedef uint8_t OPTIONS_Bool;  /* 0x00 = False, 0x01 = True */
```

All boolean fields are single bytes. The game uses `CMP byte ptr [REG + offset], 0x0` pattern in code.

### 5.2 Float Type (IEEE 754)

```c
typedef float OPTIONS_Float;  /* 4 bytes, little-endian */
```

Used for:
- Volume levels (dB scale: -96.0 to 0.0)
- Sensitivity multipliers (0.5x to 2.0x)

### 5.3 Hash Type

```c
typedef uint32_t OPTIONS_Hash;  /* 4 bytes, little-endian */
```

Hashes are precomputed and stored in a static table at address `0x0298a780` in the executable. The hash algorithm is unknown (tested 30+ algorithms without match).

### 5.4 Bitfield Type

```c
/* Achievement bitfield: 7 bytes, 53 bits used */
typedef struct {
    uint8_t bytes[7];  /* LSB-first bit order within each byte */
} AchievementBitfield;

/* Costume Record: 18 bytes, value byte at +0x01 contains 6-bit bitfield
 * Note: The "bitfield" at 0x369 is NOT standalone - it's within an 18-byte record.
 * The record starts at 0x368 with marker 0x0B and uses Type 0x00 (bitfield/complex).
 */
typedef struct {
    uint8_t  marker;          /* +0x00: 0x0B */
    uint8_t  costume_value;   /* +0x01: bitfield (0x00-0x3F) */
    uint8_t  type;            /* +0x02: 0x00 (NOT 0x0E) */
    uint8_t  padding[15];     /* +0x03-0x11: record data */
} CostumeRecord;
```

---

## 6. Hash Reference Table

### 6.1 Language Hashes

| Index | Language | Hash (LE) | Hash (BE Display) |
|-------|----------|-----------|-------------------|
| 0x01 | English | `0x50CC97B5` | `B597CC50` |
| 0x02 | French | `0x3C0FCC90` | `90CC0F3C` |
| 0x03 | Spanish | `0x48576081` | `81605748` |
| 0x04 | Polish | `0x4375357B` | `7B357543` |
| 0x05 | German | `0x314E426F` | `6F424E31` |
| 0x06 | (Reserved) | `0x87D7B2A1` | `A1B2D787` |
| 0x07 | Hungarian | `0xC6233139` | `393123C6` |
| 0x08 | Italian | `0x2BF6FC7A` | `7AFCF62B` |
| 0x09 | Japanese | `0xB1E049F8` | `F849E0B1` |
| 0x0A | Czech | `0x2C6A3130` | `30316A2C` |
| 0x0B | Korean | `0x022FCB0D` | `0DCB2F02` |
| 0x0C | Russian | `0x972964C0` | `C0642997` |
| 0x0D | Dutch | `0xDBCD3431` | `3134CDDB` |
| 0x0E | Danish | `0xCE0B031C` | `1C030BCE` |
| 0x0F | Norwegian | `0x69AD901C` | `1C90AD69` |
| 0x10 | Swedish | `0xCF6F169D` | `9D166FCF` |
| 0x11 | Portuguese | `0x12410E3F` | `3F0E4112` |
| 0x12 | Turkish | `0xCDA3D2DC` | `DCD2A3CD` |
| 0x13 | Simplified Chinese | `0x43CD0944` | `4409CD43` |
| 0x14 | Traditional Chinese | `0xCF38DA87` | `87DA38CF` |

### 6.2 Section Identification Hashes

All sections share a common header pattern with a section-specific hash at offset 0x0A:

| Section | Hash at 0x0A | Version Flags at 0x0E | Purpose |
|---------|--------------|------------------------|---------|
| Section 1 | `0xBDBE3B52` | v1.0=0x0508, v1.05=0x050C | System/Profile type identifier |
| Section 2 | `0x305AE1A8` | v1.0=0x0508, v1.05=0x050C | Game Settings type identifier |
| Section 3 | `0xC9876D66` | v1.0=0x0508, v1.05=0x050C | Game Progress type identifier |

**Version Flag Note:** The flags at offset 0x0E identify the game version, not the platform:
- 0x08 = Version 1.0 (disc/launch version)
- 0x0C = Version 1.05 (latest patch)

PC always uses 0x0C (v1.05). PS3 may have either value depending on patch status.

**Note:** Hash at Section 3 offset 0x90 (`0x6F88B05B`) is part of the progress/achievement structure, not the section header.

### 6.3 Content Hashes

| Hash | Content |
|------|---------|
| `0x00788F42` | Templar Lair: Trajan's Market |
| `0x006FF456` | Templar Lair: Tivoli Aqueduct |
| `0x000B953B` | Unknown Unlock #1 (discovered via differential) |
| `0x001854EC` | Unknown Unlock #2 (discovered via differential) |
| `0x0021D9D0` | Possibly Uplay (purpose unknown) |
| `0x0036A2C4` | Possibly Uplay (purpose unknown) |
| `0x0052C3A9` | Possibly Uplay (purpose unknown) |
| `0x000E8D04` | Possibly Uplay (purpose unknown) |
| `0x6F88B05B` | Section 3 progress/achievement constant |

---

## 7. Validation and Checksums

### 7.1 Zero-Seed Adler-32

Each section header contains an Adler-32 checksum at offset 0x28, calculated over the **compressed data only** (excluding the 4-byte prefix).

```c
#define ADLER32_MODULUS 65521

uint32_t adler32_zero_seed(const uint8_t* data, size_t length) {
    uint32_t s1 = 0;  /* NON-STANDARD: standard uses s1 = 1 */
    uint32_t s2 = 0;

    for (size_t i = 0; i < length; i++) {
        s1 = (s1 + data[i]) % ADLER32_MODULUS;
        s2 = (s2 + s1) % ADLER32_MODULUS;
    }

    return (s2 << 16) | s1;
}
```

**Key Difference:** The game uses seed `0x00000000` instead of the standard `0x00000001`.

### 7.2 PS3 CRC32

The PS3 8-byte prefix contains a CRC32 of all section data.

```c
/* PS3 CRC32 Parameters */
#define CRC32_POLYNOMIAL  0x04C11DB7
#define CRC32_INIT_VALUE  0xBAE23CD0  /* Non-standard! */
#define CRC32_XOR_OUTPUT  0xFFFFFFFF
#define CRC32_REFLECT_IN  true
#define CRC32_REFLECT_OUT true
```

```python
def crc32_ps3(data: bytes) -> int:
    crc = 0xBAE23CD0  # Custom initial value

    for byte in data:
        # Reflect input byte
        byte = int('{:08b}'.format(byte)[::-1], 2)
        crc ^= (byte << 24)

        for _ in range(8):
            if crc & 0x80000000:
                crc = ((crc << 1) ^ 0x04C11DB7) & 0xFFFFFFFF
            else:
                crc = (crc << 1) & 0xFFFFFFFF

    # Reflect output and XOR
    crc = int('{:032b}'.format(crc)[::-1], 2)
    return (crc ^ 0xFFFFFFFF) & 0xFFFFFFFF
```

### 7.3 Magic Number Validation

Section headers are validated by checking:

1. **Section-specific fields (0x00-0x08):** Match expected values for section type
2. **Universal magic bytes (0x10-0x1F):** Must equal `0x57FBAA33`, `0x1004FA99`, `0x00020001`, `0x01000080`
3. **Size consistency:** `field3 == field6` (uncompressed sizes match)
4. **Checksum:** Computed Adler-32 matches stored value at 0x28

---

## 8. Compression Format Summary

### 8.1 LZSS Variant Overview

The game uses a custom LZSS variant with three encoding types:

| Type | Total Bits | Condition | Format |
|------|------------|-----------|--------|
| Literal | 9 | Any byte | Flag 0 + 8-bit byte |
| Short Match | 12 | Length 2-5, offset 1-256 | Flag 1, Type 0, 2-bit length, 8-bit offset |
| Long Match | 18+ | Length 3+, offset 1-8192 | Flag 1, Type 1, 16-bit encoding, optional extension |

### 8.2 Data Prefix

All compressed sections begin with a 4-byte prefix:

```
06 00 E1 00
```

This prefix is part of the LZSS stream and decompresses to the leading zero bytes in section data.

### 8.3 Terminator

Each compressed section ends with:

```
20 00
```

This is signaled by two consecutive 1-bits followed by a long match encoding with distance = 0.

### 8.4 Buffer Initialization

The compressor initializes a 2-byte zero prefix before input data:

```
[00 00] [input data...]
 ^^^^^
 Prefix (positions 0-1, not output)
```

Encoding starts at position 2. This allows matches to reference the prefix for data beginning with zeros.

### 8.5 Critical Implementation Details

1. **First byte forced literal:** The game always encodes the first input byte as a literal
2. **Offset adjustment:** Long matches add +1 to offset during encoding; short matches do not
3. **Minimum offset:** Long matches require offset >= 2; short matches allow offset = 1 (for RLE)
4. **Cost tie-breaking:** When match cost equals literal cost, prefer literals
5. **Backward scanning:** Scan from `pos-1` down, using strict `>` comparison for first match found

---

## 9. Platform Differences (PC vs PS3)

### 9.1 Summary Table

| Feature | PC | PS3 |
|---------|-----|-----|
| Section Count | 3 | 4 |
| File Size | Variable (~1028 bytes) | Fixed (51,200 bytes) |
| File Prefix | None | 8 bytes (size + CRC32, BE) |
| Header Fields 0-2 | Little-endian | Big-endian |
| Section 1 Field2 | 0x000000C5 | 0x000000C6 |
| Gap Marker | None | 8 bytes before Section 4 |
| Footer | 5 bytes | None |
| Padding | None | Zero-fill to 51,200 bytes |

### 9.2 PS3 8-Byte Prefix

```c
typedef struct {
    uint32_t data_size;  /* Big-endian: total size of sections */
    uint32_t crc32;      /* Big-endian: CRC32 of section data */
} PS3_Prefix;
```

### 9.3 PS3 Gap Marker (Before Section 4)

```c
typedef struct {
    uint32_t size;  /* Big-endian: Section 4 total size + 4 */
    uint32_t type;  /* Big-endian: 0x00000008 */
} PS3_GapMarker;
```

### 9.4 PC Footer

```c
typedef struct {
    uint8_t  signature;      /* 0x01 */
    uint8_t  reserved[3];    /* 0x00 0x00 0x00 */
    uint8_t  network_count;  /* Network interface count (telemetry) */
} PC_Footer;
```

The network interface count is collected by Ubisoft's Quazal/NEX infrastructure during save creation and has no impact on game functionality.

---

## 10. Annotated Hex Dump Examples

### 10.1 PC Section 1 Header (Complete)

```
Offset   Raw Bytes                              Interpretation
------   ---------                              --------------
0x0000   16 00 00 00                            Field0: 0x00000016 (magic, value=22)
0x0004   AC DB FE 00                            Field1: 0x00FEDBAC (validation marker)
0x0008   C5 00 00 00                            Field2: 0x000000C5 (section marker, PC)
0x000C   1B 01 00 00                            Field3: 0x0000011B (283 bytes uncompressed)
0x0010   33 AA FB 57                            Magic1: 0x57FBAA33 (format signature)
0x0014   99 FA 04 10                            Magic2: 0x1004FA99 (version identifier)
0x0018   01 00 02 00                            Magic3: 0x00020001 (compression params)
0x001C   80 00 00 01                            Magic4: 0x01000080 (version flags)
0x0020   A5 00 00 00                            Field5: 0x000000A5 (165 bytes compressed)
0x0024   1B 01 00 00                            Field6: 0x0000011B (283 bytes, duplicate)
0x0028   CD 33 69 B8                            Field7: 0xB869CD33 (Adler-32 checksum)
------   ---------                              --------------
0x002C   06 00 E1 00                            Data Prefix (LZSS stream start)
0x0030   52 3B BE BD ...                        Compressed data begins
...      ...
         20 00                                  Terminator (end of LZSS stream)
```

### 10.2 PS3 File Start

```
Offset   Raw Bytes                              Interpretation
------   ---------                              --------------
0x0000   00 00 05 5E                            Data Size: 0x055E (1374 bytes, BE)
0x0004   20 EC E5 EA                            CRC32: 0x20ECE5EA (BE)
------   ---------                              --------------
0x0008   00 00 00 16                            Field0: 0x00000016 (BE)
0x000C   00 FE DB AC                            Field1: 0x00FEDBAC (BE)
0x0010   00 00 00 C6                            Field2: 0x000000C6 (BE, PS3 marker)
0x0014   21 01 00 00                            Field3: 0x00000121 (289 bytes, LE)
0x0018   33 AA FB 57                            Magic1: 0x57FBAA33 (LE)
...      ...                                    (remaining fields little-endian)
```

### 10.3 PC Footer

```
Offset   Raw Bytes                              Interpretation
------   ---------                              --------------
0x03FF   01 00 00 00 0C                         Footer:
         01                                       Signature byte
         00 00 00                                 Reserved (zeros)
         0C                                       Network interface count (12)
```

---

## 11. Appendix: Complete Magic Number Reference

### 11.1 Universal Magic Numbers (All Sections)

| Value | Location | Purpose | Function Reference |
|-------|----------|---------|-------------------|
| `0x57FBAA33` | Header 0x10 | Format signature | FUN_01b7a310 |
| `0x1004FA99` | Header 0x14 | Version identifier | FUN_01b7a310 |
| `0x00020001` | Header 0x18 | Compression params (type=1, mode=2) | FUN_01b7a310 |
| `0x01000080` | Header 0x1C | Version flags (ver=1 | 0x80000000) | FUN_01b7a310 |

### 11.2 Section-Specific Magic Numbers

| Section | Field | Value | Purpose | Function |
|---------|-------|-------|---------|----------|
| 1 | Field0 | `0x00000016` | Section 1 type marker | FUN_0046d710 |
| 1 | Field1 | `0x00FEDBAC` | Validation marker | FUN_0046d710 |
| 1 | Field2 | `0x000000C5` | PC section marker | FUN_01b7b050 |
| 1 | Field2 | `0x000000C6` | PS3 section marker | - |
| 2 | Field1 | `0x00000003` | Type ID: Configuration | FUN_01712ca0 |
| 2 | Field2 | `0x11FACE11` | Section 2 signature | FUN_01712ca0 |
| 3 | Field1 | `0x00000000` | Type ID: State | FUN_017108e0 |
| 3 | Field2 | `0x21EFFE22` | Section 3 signature | FUN_017108e0 |
| 4 | Field0 | `0x22FEEF21` | Prev section ID swapped | - |
| 4 | Field1 | `0x00000004` | Section number | - |
| 4 | Field2 | `0x00000007` | Section 4 identifier | - |

### 11.3 Internal Constants

| Value | Location | Purpose |
|-------|----------|---------|
| `0x305AE1A8` | Section 2 +0x0A | Section 2 hash constant |
| `0x00110000` | Section 2 +0x14 | Type indicator |
| `0x6F88B05B` | Section 3 +0x90 | Section 3 hash constant |
| `0x00000008` | PS3 Gap Marker | Type marker for Section 4 boundary |

### 11.4 Validation Patterns

**Section Header Location:** Search for magic pattern at offset 0x10:
```
33 AA FB 57 99 FA 04 10 01 00 02 00 80 00 00 01
```

Header starts 0x10 bytes before this pattern.

**LZSS Stream Start:** `06 00 E1 00`

**LZSS Stream End:** `20 00`

---

## Document Metadata

**Created:** 2025-12-27
**Last Updated:** 2025-12-27
**Author:** Generated from reverse engineering documentation
**Version History:**
- v1.0: Initial specification
- v2.0: Added Section 1 property record structure (12 records), Section identification hashes (0x0A-0x0D), Version flags (0x0E-0x0F), 2 unknown unlock records in Section 2, PC vs PS3 Section 3 size difference explanation (PSN Trophy system)

**Sources:**
- WinDbg Time-Travel Debugging traces
- Ghidra decompilation of ACBSP.exe
- 24-file differential analysis (21 language variants + 3 reward states)
- Binary comparison of PC and PS3 save files

**Related Documents:**
- `OPTIONS_FIELD_REFERENCE.md` - Consolidated field mappings (v3.0)
- `LZSS_LOGIC_FLOW_ANALYSIS.md` - Compression algorithm details
- `PS3_OPTIONS_FORMAT.md` - PS3-specific documentation
- `ACB_OPTIONS_Header_Complete_Specification.md` - Header structure details

---

**End of Specification**
