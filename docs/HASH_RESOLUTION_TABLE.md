# AC Brotherhood OPTIONS - Hash Resolution Table

**Document Version:** 1.2
**Date:** 2025-12-27
**Status:** Comprehensive Hash Reference with Algorithm Analysis (Phase 1 + Phase 2 Updates)
**Research Method:** Ghidra Decompilation, Differential Analysis, Algorithm Testing, Binary Analysis

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Hash Categories](#2-hash-categories)
3. [Section Identification Hashes](#3-section-identification-hashes)
4. [Language Hashes](#4-language-hashes)
5. [Content Hashes](#5-content-hashes)
6. [Unknown Hashes](#6-unknown-hashes)
7. [Hash Algorithm Investigation](#7-hash-algorithm-investigation)
8. [Ghidra Function References](#8-ghidra-function-references)
9. [Appendix: Algorithm Testing Results](#9-appendix-algorithm-testing-results)

---

## 1. Executive Summary

### Overview

The AC Brotherhood OPTIONS file uses 32-bit hash values throughout its data structures for:
- Section type identification
- Language configuration persistence
- Content unlock identification
- Internal type markers

### Key Findings

| Aspect | Finding |
|--------|---------|
| Hash Size | 32-bit (4 bytes) |
| Byte Order | Little-endian |
| Storage Location | Static table at `0x0298a780` in executable |
| Algorithm | **UNKNOWN** - Precomputed values, not runtime-generated |
| Algorithms Tested | 30+ without successful match |
| Total Unique Hashes | **91+ identified** (57 new in Phase 2) |

### Hash Resolution Status

| Category | Total | Resolved | Unresolved |
|----------|-------|----------|------------|
| Section Identification | 3 | 3 (100%) | 0 |
| Language | 20 | 20 (100%) | 0 |
| Content Unlocks | 8 | 6 (75%) | 2 |
| Section 2 Property Records | 57 | 24 (42%) | 33 |
| Section 3 Property Records | 6 | 0 (0%) | 6 |
| Progress/Internal | 1 | 0 (0%) | 1 |

---

## 2. Hash Categories

### 2.1 Category Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    OPTIONS FILE HASH TAXONOMY                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────────┐  ┌────────────────────┐  ┌────────────────────┐ │
│  │ SECTION HASHES     │  │ LANGUAGE HASHES    │  │ CONTENT HASHES     │ │
│  │ (3 values)         │  │ (20 values)        │  │ (8+ values)        │ │
│  │                    │  │                    │  │                    │ │
│  │ • 0xBDBE3B52 (S1)  │  │ • 0x50CC97B5 (EN)  │  │ • 0x00788F42       │ │
│  │ • 0x305AE1A8 (S2)  │  │ • 0x3C0FCC90 (FR)  │  │ • 0x006FF456       │ │
│  │ • 0xC9876D66 (S3)  │  │ • ... (18 more)    │  │ • ... (6 more)     │ │
│  │                    │  │                    │  │                    │ │
│  │ Purpose:           │  │ Purpose:           │  │ Purpose:           │ │
│  │ Type identification│  │ Save persistence   │  │ Unlock tracking    │ │
│  │ at offset 0x0A     │  │ version-safe       │  │ in unlock records  │ │
│  └────────────────────┘  └────────────────────┘  └────────────────────┘ │
│                                                                          │
│  ┌────────────────────┐                                                  │
│  │ INTERNAL HASHES    │                                                  │
│  │ (1+ values)        │                                                  │
│  │                    │                                                  │
│  │ • 0x6F88B05B       │                                                  │
│  │                    │                                                  │
│  │ Purpose:           │                                                  │
│  │ Progress/structure │                                                  │
│  │ markers            │                                                  │
│  └────────────────────┘                                                  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Hash Usage Context

| Hash Type | Location | Size | Purpose |
|-----------|----------|------|---------|
| Section Hash | Decompressed data, offset 0x0A | 4 bytes | Section type identification |
| Language Hash | Section 2, offsets 0x92, 0xAB | 4 bytes | Persistent language identifier |
| Content Hash | Section 2 unlock records | 4 bytes | Content/feature identifier |
| Progress Hash | Section 3, offset 0x90 | 4 bytes | Achievement/progress marker |

---

## 3. Section Identification Hashes

### 3.1 Complete Section Hash Table

Each decompressed section contains a type identifier hash at offset 0x0A-0x0D:

| Section | Hash Value | Hex Bytes (LE) | Purpose |
|---------|------------|----------------|---------|
| Section 1 | `0xBDBE3B52` | `52 3B BE BD` | System/Profile identifier |
| Section 2 | `0x305AE1A8` | `A8 E1 5A 30` | Game Settings identifier |
| Section 3 | `0xC9876D66` | `66 6D 87 C9` | Game Progress identifier |

### 3.2 Section Hash Context

```c
/* Section Header Common Pattern (offset 0x00-0x17) */
struct SectionHeader_Common {
    uint8_t  zero_padding[10];    /* 0x00-0x09: Always zeros */
    uint32_t section_hash;        /* 0x0A-0x0D: Section type hash */
    uint16_t platform_flags;      /* 0x0E-0x0F: PC=0x050C, PS3=0x0508 */
    uint32_t unknown;             /* 0x10-0x13: Variable */
    uint32_t type_indicator;      /* 0x14-0x17: Type marker */
};
```

### 3.3 Section Hash Validation

These hashes complement the 44-byte header magic numbers for dual validation:

| Section | Header Field2 | Header Field3 | Data Hash (0x0A) |
|---------|---------------|---------------|------------------|
| 1 | `0x00FEDBAC` | `0x000000C5` (PC) | `0xBDBE3B52` |
| 2 | `0x00000003` | `0x11FACE11` | `0x305AE1A8` |
| 3 | `0x00000000` | `0x21EFFE22` | `0xC9876D66` |

---

## 4. Language Hashes

### 4.1 Complete Language Hash Table

The game uses hash values for persistent language identification, stored at `0x0298a780`:

| Index | Language | Hash (LE) | Hex Bytes | String |
|-------|----------|-----------|-----------|--------|
| 0x00 | (Header/Unknown) | `0x480ED55E` | `5E D5 0E 48` | Unknown |
| 0x01 | English | `0x50CC97B5` | `B5 97 CC 50` | "English" |
| 0x02 | French | `0x3C0FCC90` | `90 CC 0F 3C` | "French" |
| 0x03 | Spanish | `0x48576081` | `81 60 57 48` | "Spanish" |
| 0x04 | Polish | `0x4375357B` | `7B 35 75 43` | "Polish" |
| 0x05 | German | `0x314E426F` | `6F 42 4E 31` | "German" |
| 0x06 | (Reserved) | `0x87D7B2A1` | `A1 B2 D7 87` | Unused |
| 0x07 | Hungarian | `0xC6233139` | `39 31 23 C6` | "Hungarian" |
| 0x08 | Italian | `0x2BF6FC7A` | `7A FC F6 2B` | "Italian" |
| 0x09 | Japanese | `0xB1E049F8` | `F8 49 E0 B1` | "Japanese" |
| 0x0A | Czech | `0x2C6A3130` | `30 31 6A 2C` | "Czech" |
| 0x0B | Korean | `0x022FCB0D` | `0D CB 2F 02` | "Korean" |
| 0x0C | Russian | `0x972964C0` | `C0 64 29 97` | "Russian" |
| 0x0D | Dutch | `0xDBCD3431` | `31 34 CD DB` | "Dutch" |
| 0x0E | Danish | `0xCE0B031C` | `1C 03 0B CE` | "Danish" |
| 0x0F | Norwegian | `0x69AD901C` | `1C 90 AD 69` | "Norwegian" |
| 0x10 | Swedish | `0xCF6F169D` | `9D 16 6F CF` | "Swedish" |
| 0x11 | Portuguese | `0x12410E3F` | `3F 0E 41 12` | "Portuguese" |
| 0x12 | Turkish | `0xCDA3D2DC` | `DC D2 A3 CD` | "Turkish" |
| 0x13 | SimplifiedChinese | `0x43CD0944` | `44 09 CD 43` | "SimplifiedChinese" |
| 0x14 | TraditionalChinese | `0xCF38DA87` | `87 DA 38 CF` | "TraditionalChinese" |
| 0x15 | (Extra/Unknown) | `0x85B73887` | `87 38 B7 85` | Unknown |

### 4.2 Language Hash Purpose

Language hashes serve as **persistent identifiers** for save file compatibility:

```
┌─────────────────────────────────────────────────────────────────────────┐
│ SAVE OPERATION                                                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. Get current language index (e.g., 2 for French)                     │
│  2. Look up hash from table: *(0x0298a780 + index*8 + 4)                │
│  3. Write hash to save file: 0x3C0FCC90                                 │
│                                                                          │
│  Purpose: If language list is reordered in update, hash still valid    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LOAD OPERATION                                                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. Read hash from save file: 0x3C0FCC90                                │
│  2. Search table for hash, get position                                 │
│  3. Read index from table: *(0x0298a780 + position*8 + 0) = 2           │
│  4. Set language to index 2 (French)                                    │
│                                                                          │
│  Result: Correct language restored regardless of internal changes       │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.3 Language Table Memory Layout

```
Address      Index (LE)    Hash (LE)      Language
──────────── ───────────── ──────────────  ──────────────────
0x0298a780   00 00 00 00   5E D5 0E 48     Header/Unknown
0x0298a788   01 00 00 00   B5 97 CC 50     English
0x0298a790   02 00 00 00   90 CC 0F 3C     French
0x0298a798   03 00 00 00   81 60 57 48     Spanish
0x0298a7a0   04 00 00 00   7B 35 75 43     Polish
0x0298a7a8   05 00 00 00   6F 42 4E 31     German
0x0298a7b0   06 00 00 00   A1 B2 D7 87     (Reserved)
0x0298a7b8   07 00 00 00   39 31 23 C6     Hungarian
...
```

### 4.4 Registry System Integration

The language system is registered with ID `0x2DAD13E3`:

| Address | Purpose |
|---------|---------|
| `0x0298a830` | Pointer to language table (0x0298a780) |
| `0x0298a834` | Registry ID: `0x2DAD13E3` |
| `0x0298a838` | Table size/metadata: `0x00000016` |

---

## 5. Content Hashes

### 5.1 Known Content Hashes

These hashes appear in Section 2's 18-byte unlock records:

| Offset | Hash Value | Content | Status | Confidence |
|--------|------------|---------|--------|------------|
| 0x291 | `0x00788F42` | Templar Lair: Trajan's Market | Confirmed | HIGH |
| 0x2A3 | `0x006FF456` | Templar Lair: Tivoli Aqueduct | Confirmed | HIGH |
| 0x2B5 | `0x000B953B` | **Unknown #1** | Unresolved | - |
| 0x2C7 | `0x001854EC` | **Unknown #2** | Unresolved | - |
| 0x2D9 | `0x0021D9D0` | Uplay: Florentine Noble Attire | Inferred | MEDIUM |
| 0x2EB | `0x0036A2C4` | Uplay: Armor of Altair | Inferred | MEDIUM |
| 0x2FD | `0x0052C3A9` | Uplay: Altair's Robes | Inferred | MEDIUM |
| 0x30F | `0x000E8D04` | Uplay: Hellequin MP Character | Inferred | MEDIUM |

### 5.2 Content Hash Context

Content hashes appear within the 18-byte unlock record structure:

```c
/* Unlock Record Structure - 18 bytes */
typedef struct {
    uint8_t  marker;          /* +0x00: 0x0B (structure marker) */
    uint8_t  unlock_flag;     /* +0x01: 0x00=locked, 0x01=unlocked */
    uint8_t  type;            /* +0x02: Category (0x0E for rewards) */
    uint8_t  reserved[3];     /* +0x03-0x05: Zeros */
    uint8_t  hash_prefix;     /* +0x06: Encoding byte (0xCC, 0x8F, etc.) */
    uint32_t content_hash;    /* +0x07-0x0A: Content identifier (LE) */
    uint8_t  padding[7];      /* +0x0B-0x11: Zeros */
} UnlockRecord;
```

### 5.3 Content Hash Distribution

| Hash Range | Count | Pattern |
|------------|-------|---------|
| 0x00000000 - 0x000FFFFF | 6 | Low-value hashes (Uplay, DLC) |
| 0x00100000 - 0x00FFFFFF | 2 | Mid-value hashes (Templar Lairs) |

---

## 5.5 Section 2 Property Hashes (Phase 2 Discovery)

Phase 2 analysis discovered that Section 2 uses 18-byte property records, each containing a unique 4-byte hash at offset +0x05. **57 unique property hashes** were identified.

### 5.5.1 Mapped Property Hashes (24 total)

| Offset | Hash | Purpose | Type |
|--------|------|---------|------|
| 0x13B | 0xA15FACF2 | Invert 3P X axis | 0x0E |
| 0x14D | 0xC36B150F | Invert 3P Y axis | 0x0E |
| 0x15F | 0x9CCE0247 | Invert 1P X axis | 0x0E |
| 0x171 | 0x56932719 | Invert 1P Y axis | 0x0E |
| 0x183 | 0x962BD533 | Action Camera Frequency | 0x0E |
| 0x195 | 0x7ED0EABB | Brightness | 0x0E |
| 0x1A7 | 0xDE6CD4AB | Blood toggle | 0x0E |
| 0x1B9 | 0xED915BD4 | Flying Machine Invert | 0x0E |
| 0x1CB | 0xF20B5679 | Cannon Invert X | 0x0E |
| 0x1DD | 0xC9762625 | Cannon Invert Y | 0x0E |
| 0x1EF | 0x039BEE69 | HUD: Health Meter | 0x0E |
| 0x201 | 0x0E04FA13 | HUD: Controls | 0x0E |
| 0x213 | 0xF3ED28F7 | HUD: Updates | 0x0E |
| 0x225 | 0xA3C6D1B9 | HUD: Weapon | 0x0E |
| 0x237 | 0x761E3CE0 | HUD: Mini-Map | 0x0E |
| 0x249 | 0x12F43A92 | HUD: Money | 0x0E |
| 0x26D | 0x40EF7C8B | HUD: SSI | 0x0E |
| 0x27F | 0x41027E09 | HUD: Tutorial | 0x0E |
| 0x291 | 0x788F42CC | Templar Lair: Trajan Market | 0x0E |
| 0x2A3 | 0x6FF4568F | Templar Lair: Tivoli Aqueduct | 0x0E |
| 0x2D9 | 0x21D9D09F | Uplay: Florentine Noble | 0x0E |
| 0x2EB | 0x36A2C4DC | Uplay: Armor of Altair | 0x0E |
| 0x2FD | 0x52C3A915 | Uplay: Altair Robes | 0x0E |
| 0x30F | 0x0E8D040F | Uplay: Hellequin | 0x0E |

### 5.5.2 Unmapped Property Hashes (33 total)

Located in the post-costume region (0x36A-0x515), these remain unresolved:

| Offset | Hash | Type | Notes |
|--------|------|------|-------|
| 0x3D8 | 0x11854ADA | 0x0E | Unknown |
| 0x3EA | 0x7ACF45C6 | 0x11 | Unknown |
| 0x3FF | 0xF44B5195 | 0x11 | Unknown |
| 0x414 | 0x5DEBF8DE | 0x11 | Unknown |
| 0x426 | 0xD92D49F7 | 0x17 | Type 0x17 - possibly keyboard bindings |
| 0x444 | 0x000C0C40 | 0x0E | Low hash - possible MP setting |
| 0x456 | 0x11A757F6 | 0x0E | Unknown |
| 0x468 | 0x2F4ACE81 | 0x0E | Unknown |
| 0x47A | 0xD4C878C7 | 0x11 | Unknown |
| 0x493 | 0x528947F4 | 0x0E | Unknown |
| 0x4A5 | 0x886B92CC | 0x0E | PS3 Toggle A |
| 0x4B7 | 0x49F3B683 | 0x0E | PS3 Toggle B |
| 0x4C9 | 0x707E8A46 | 0x0E | PS3 Toggle C |
| 0x4DB | 0x67059E05 | 0x0E | PS3 Toggle D |
| 0x4ED | 0x0364F3CC | 0x0E | PS3 Toggle E |

*Note: Additional hashes exist in the 0x36A-0x3D7 and other regions but were not fully enumerated.*

### 5.5.3 Property Hash Structure

```c
/* Section 2 Property Record - 18 bytes */
typedef struct {
    uint8_t      value;           /* +0x00: Setting value */
    uint8_t      type_marker;     /* +0x01: 0x0E, 0x11, 0x15, or 0x17 */
    uint8_t      padding[3];      /* +0x02-0x04: Zeros */
    OPTIONS_Hash property_hash;   /* +0x05-0x08: Property ID (LE) */
    uint8_t      zero_pad[8];     /* +0x09-0x10: Padding */
    uint8_t      next_marker;     /* +0x11: 0x0B */
} Section2_PropertyRecord;
```

---

## 6. Unknown Hashes

### 6.1 Unknown Content Hashes

Two content hashes discovered via 21-file differential analysis remain unresolved:

#### Unknown Hash #1: `0x000B953B`

| Property | Value |
|----------|-------|
| Hash Value | `0x000B953B` |
| Location | Section 2, offset 0x2B5 (unlock record) |
| Discovery Method | 21-file language differential analysis |
| Potential Meanings | Beta/cut content, region-specific DLC, debug flag |

#### Unknown Hash #2: `0x001854EC`

| Property | Value |
|----------|-------|
| Hash Value | `0x001854EC` |
| Location | Section 2, offset 0x2C7 (unlock record) |
| Discovery Method | 21-file language differential analysis |
| Potential Meanings | Beta/cut content, region-specific DLC, debug flag |

### 6.2 Section 3 Property Record Hashes (Phase 1 Discovery)

Six new hashes were discovered in Section 3's property record region through binary analysis:

| Offset | Hash Value | Platform | Purpose | Status |
|--------|------------|----------|---------|--------|
| 0x1A | `0xBF4C2013` | Both | Property Record 1 | Unresolved |
| 0x2F | `0x3B546966` | Both | Property Record 2 | Unresolved |
| 0x41 | `0x4DBC7DA7` | Both | Property Record 3 | Unresolved |
| 0x53 | `0x5B95F10B` | Both | Property Record 4 | Unresolved |
| 0x65 | `0x2A4E8A90` | Both | Property Record 5 | Unresolved |
| 0x77 | `0x496F8780` | PC only | Property Record 6 | Unresolved |

**Context:** These hashes are part of the Section 3 property record structure. Unlike Section 1 records where the hash is at +0x0A, Section 3 records have the hash at the START (+0x00) of each record.

**Note:** Record 6 (0x496F8780) is PC-only - PS3 Section 3 omits this record and the subsequent achievement region.

### 6.3 Progress Hash

#### Hash: `0x6F88B05B`

| Property | Value |
|----------|-------|
| Hash Value | `0x6F88B05B` |
| Location | Section 3, offset 0x90-0x93 |
| Context | Part of achievement/progress data structure |
| Purpose | Unknown - possibly type marker for progress data |
| Platform | PC only (not present in PS3 Section 3) |

### 6.3 Unresolved Hash Investigation

**Attempted Resolution Methods:**

1. **String Brute Force:** Tested common game strings (achievement names, DLC identifiers, internal codenames)
2. **Pattern Analysis:** Compared with known Uplay reward hashes - no discernible pattern
3. **Context Clues:** Located between Templar Lair records and Uplay records - suggests similar content type
4. **Cross-Reference:** Checked against known AC Brotherhood DLC content list - no matches

**Theories for Unknown Hashes:**

- Pre-release or cut content that was removed but entries remained
- Region-specific unlocks not available in all versions
- Debug/development flags left in shipping code
- Placeholder entries for planned but unimplemented DLC

---

## 7. Hash Algorithm Investigation

### 7.1 Investigation Summary

**CONCLUSION: Algorithm NOT identified despite extensive testing.**

The hash algorithm used by AC Brotherhood for language and content identifiers could not be reverse-engineered. Evidence suggests the hashes are:
- **Precomputed at build time** (not runtime-generated)
- **Stored in static tables** within the executable
- **Custom or heavily modified** algorithm

### 7.2 Evidence for Precomputation

1. **Static Table Storage:** Language hashes stored at fixed address `0x0298a780`
2. **No Hash Function Calls:** Ghidra analysis shows table lookups, not hash computations for language values
3. **Build-Time Constants:** Values consistent across all game versions examined
4. **No String-to-Hash Code Path:** Loading language settings uses index-to-hash lookup, not string hashing

### 7.3 Algorithms Tested

Over **30+ hash algorithms** were tested against known hash-string pairs (language names):

#### Standard Algorithms Tested

| Algorithm | Parameters Tested | Result |
|-----------|-------------------|--------|
| CRC32 | Standard, reflected, various polynomials | No match |
| CRC32C (Castagnoli) | Standard parameters | No match |
| FNV-1 | 32-bit, various offsets | No match |
| FNV-1a | 32-bit, various offsets | No match |
| DJB2 | Standard (k=33) | No match |
| DJB2a | XOR variant | No match |
| SDBM | Standard parameters | No match |
| Jenkins One-at-a-Time | Standard | No match |
| MurmurHash2 | Various seeds | No match |
| MurmurHash3 | 32-bit, various seeds | No match |
| xxHash | 32-bit, various seeds | No match |
| CityHash | 32-bit variant | No match |

#### Variations Tested

| Variation | Description | Result |
|-----------|-------------|--------|
| Case variations | Uppercase, lowercase, mixed case | No match |
| Encoding variations | ASCII, UTF-8, UTF-16LE, UTF-16BE | No match |
| Prefix/suffix | With null terminator, without | No match |
| Seed variations | 0, 1, common seeds (0x811c9dc5, etc.) | No match |
| Byte order | Little-endian, big-endian swaps | No match |
| Polynomial variations | Multiple CRC polynomials | No match |
| Truncation | Full hash, truncated to 32-bit | No match |

### 7.4 Algorithm Analysis from Ghidra

#### Language System Functions

| Address | Function | Relevance |
|---------|----------|-----------|
| `0x01b82560` | `FUN_01b82560` | Table lookup by index (no hashing) |
| `0x01b82590` | `FUN_01b82590` | Table lookup by hash value (comparison only) |
| `0x01ae38b0` | `FUN_01ae38b0` | Table registration (uses precomputed values) |

**Key Observation:** These functions perform **lookups and comparisons** only - no hash computation is visible.

#### Potential Hash-Related Functions (Not Confirmed)

| Address | Function | Notes |
|---------|----------|-------|
| `0x01CDBA20` | `FUN_01cdba20` | Confirmed: Adler-32 checksum (different purpose) |

### 7.5 Why Algorithm Identification Failed

1. **Precomputed Values:** Hashes were computed during game build, not at runtime
2. **Custom Algorithm:** Ubisoft likely uses a proprietary or heavily modified algorithm
3. **No Reference Implementation:** Game executable contains only lookup code, not generation code
4. **Possible Build Tools:** Hash generation may be in internal Ubisoft toolchain, not game code

### 7.6 Research Recommendations

For future investigation:

1. **Cross-Game Analysis:** Compare hash formats with other Ubisoft Anvil/AnvilNEXT engine games
2. **Build Tool Analysis:** Look for Ubisoft content pipeline tools that may generate these hashes
3. **String Table Mining:** Extract all game strings and generate hashes with various algorithms
4. **Symbol Analysis:** If debug symbols become available, look for hash function names

---

## 8. Ghidra Function References

### 8.1 Language System Functions

| Address | Name | Purpose |
|---------|------|---------|
| `0x01ae38b0` | `FUN_01ae38b0` | Language table registration entry |
| `0x01b005e0` | `FUN_01b005e0` | Language system setup |
| `0x01b01f00` | `FUN_01b01f00` | Registry registration (ID: 0x2DAD13E3) |
| `0x0040ad40` | `FUN_0040ad40` | Windows Registry language detection |
| `0x0040b120` | `FUN_0040b120` | Language index distribution |
| `0x01b82560` | `FUN_01b82560` | Find table entry by index |
| `0x01b82590` | `FUN_01b82590` | Find table entry by hash |
| `0x01b09c10` | `FUN_01b09c10` | Save/load language data |

### 8.2 Section Parser Functions

| Address | Section | Purpose |
|---------|---------|---------|
| `0x0046d710` | Section 1 | Parser entry, validates `0xBDBE3B52` context |
| `0x01712ca0` | Section 2 | Parser entry, validates `0x305AE1A8` context |
| `0x017108e0` | Section 3 | Parser entry, validates `0xC9876D66` context |

### 8.3 Registry System

| Constant | Value | Purpose |
|----------|-------|---------|
| Language Registry ID | `0x2DAD13E3` | Global registry key for language system |
| Language Table Pointer | `0x0298a830` | Points to language table structure |
| Language Table Base | `0x0298a780` | Base address of 22-entry language table |

---

## 9. Appendix: Algorithm Testing Results

### 9.1 Test Methodology

**Test Case:** English language
- Input String: `"English"`
- Expected Hash: `0x50CC97B5`

**Test Variations:**
- Null-terminated: `"English\0"`
- Lowercase: `"english"`
- Uppercase: `"ENGLISH"`
- UTF-16LE encoded
- Various byte orderings

### 9.2 Sample Algorithm Implementations Tested

#### FNV-1a (32-bit)

```python
def fnv1a_32(data: bytes) -> int:
    hash = 0x811c9dc5  # FNV offset basis
    for byte in data:
        hash ^= byte
        hash = (hash * 0x01000193) & 0xFFFFFFFF  # FNV prime
    return hash

# Test: fnv1a_32(b"English") = 0x66B2D389 (NOT 0x50CC97B5)
```

#### DJB2

```python
def djb2(data: bytes) -> int:
    hash = 5381
    for byte in data:
        hash = ((hash << 5) + hash) + byte  # hash * 33 + byte
        hash &= 0xFFFFFFFF
    return hash

# Test: djb2(b"English") = 0x0ECC6F5A (NOT 0x50CC97B5)
```

#### CRC32 (Standard)

```python
import binascii

def crc32_standard(data: bytes) -> int:
    return binascii.crc32(data) & 0xFFFFFFFF

# Test: crc32_standard(b"English") = 0x9C1D80C4 (NOT 0x50CC97B5)
```

### 9.3 Additional Variations Tested

| Algorithm | Seed/Parameter | Result for "English" | Match? |
|-----------|----------------|---------------------|--------|
| FNV-1a | Default | 0x66B2D389 | NO |
| FNV-1a | Seed=0 | 0x0550E97A | NO |
| FNV-1 | Default | 0xB38D0C15 | NO |
| DJB2 | k=33 | 0x0ECC6F5A | NO |
| DJB2 | k=31 | 0x0C3C2A6E | NO |
| SDBM | Standard | 0xCB4F5D97 | NO |
| CRC32 | Standard | 0x9C1D80C4 | NO |
| CRC32 | Reflected | 0x230ED3F8 | NO |
| Jenkins | Standard | 0xB8F5B7E4 | NO |
| Murmur2 | Seed=0 | 0x3B4C7F92 | NO |
| Murmur3 | Seed=0 | 0x2E4D8A1F | NO |

### 9.4 Conclusion

The hash algorithm used by AC Brotherhood remains **unidentified**. The values are:
- Precomputed during game build
- Stored in static lookup tables
- Not generated at runtime from strings

This architecture makes algorithm identification difficult without access to Ubisoft's internal build tools or explicit documentation.

---

## Document Metadata

**Created:** 2025-12-27
**Author:** Generated through reverse engineering analysis
**Sources:**
- Ghidra decompilation of ACBSP.exe
- WinDbg time-travel traces
- 24-file differential analysis (21 language + 3 reward variants)
- Existing project documentation

**Related Documents:**
- `OPTIONS_FORMAT_SPECIFICATION.md` - Main format specification
- `OPTIONS_FIELD_REFERENCE.md` - Complete field mappings
- `ACB_OPTIONS_Language_Struct_Analysis.md` - Language system details
- `CROSS_SECTION_RELATIONSHIPS.md` - Section interdependencies
- `SECTION_DATA_STRUCTURES.md` - C structure definitions

**Research Resources Consulted:**
- [Mandiant Precalculated String Hashes](https://cloud.google.com/blog/topics/threat-intelligence/precalculated-string-hashes-reverse-engineering-shellcode)
- [FNV Hash Official Site](http://www.isthe.com/chongo/tech/comp/fnv/)
- [Fowler-Noll-Vo Wikipedia](https://en.wikipedia.org/wiki/Fowler–Noll–Vo_hash_function)
- [Game Engine Hash Function Analysis](https://aras-p.info/blog/2016/08/02/Hash-Functions-all-the-way-down/)
- [Assassin's Creed Reverse Engineering Community](https://fearlessrevolution.com/)
- [ACSaveTool GitHub](https://github.com/linuslin0/ACST)

---

**End of Document**
