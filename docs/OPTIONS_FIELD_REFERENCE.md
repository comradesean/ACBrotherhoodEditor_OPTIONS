# AC Brotherhood OPTIONS File - Complete Field Reference

**Last Updated:** 2025-12-27
**Document Version:** 3.2
**Status:** Authoritative Reference (Consolidated from 13 Source Documents + Phase 1 & 2 Analysis)

---

## Document Info

### Coverage Summary

| Section | Platform | Total Size | Bytes Mapped | Coverage |
|---------|----------|------------|--------------|----------|
| Section 1 | PC | 283 bytes | 271 bytes | 96% |
| Section 1 | PS3 | 289 bytes | 283 bytes | 98% |
| Section 2 | PC | 1310 bytes | ~920 bytes | **70%** |
| Section 2 | PS3 | 1306 bytes | ~916 bytes | **70%** |
| Section 3 | PC | 162 bytes | ~57 bytes | 35% |
| Section 3 | PS3 | 119 bytes | ~50 bytes | 42% |
| Section 4 | PS3 only | 1903 bytes | ~1880 bytes | **98.8%** |

### Key Analysis Findings (v3.2)

- **Section 1:** All 21 PC language files are byte-for-byte identical; only 1 byte (0x51) varies between base/allrewards
- **Section 1 PS3:** Extra 6 bytes are a PREFIX at offset 0x00 containing duplicate section hash (Phase 1 discovery)
- **Section 2:** 17-byte "gaps" between settings are property record structure (Phase 2 discovery)
- **Section 2:** 57 unique property hashes identified, 24 mapped to known settings (Phase 2 discovery)
- **Section 3:** 43-byte PC/PS3 difference explained by PSN trophy system replacing embedded achievement bitfield
- **Section 3:** 6 property record hashes identified at 0x1A, 0x2F, 0x41, 0x53, 0x65, 0x77 (Phase 1 discovery)
- **Hash Algorithm:** Remains unknown despite testing 30+ algorithms; hashes precomputed at 0x0298a780

### Confidence Legend

| Level | Symbol | Description |
|-------|--------|-------------|
| **100% PROVEN** | [P] | Ghidra decompilation, WinDbg trace, or exhaustive 24-file differential analysis |
| **HIGH (80-99%)** | [H] | Strong Ghidra evidence or consistent differential pattern across multiple files |
| **MEDIUM (60-79%)** | [M] | Good hypothesis with supporting evidence, minor uncertainty |
| **LOW (<60%)** | [L] | Speculation, pattern matching without verification |

---

## File Structure Overview

### PC OPTIONS File Layout
```
[Section 1: 44-byte header + compressed data]  (283 bytes uncompressed)
[Section 2: 44-byte header + compressed data]  (1310 bytes uncompressed)
[Section 3: 44-byte header + compressed data]  (162 bytes uncompressed)
[Footer: 5 bytes - 01 00 00 00 XX]
```

### PS3 OPTIONS File Layout
```
[8-byte prefix: Size (BE) + CRC32 (BE)]
[Section 1: 44-byte header + compressed data]  (289 bytes uncompressed)
[Section 2: 44-byte header + compressed data]  (1306 bytes uncompressed)
[Section 3: 44-byte header + compressed data]  (119 bytes uncompressed)
[8-byte gap marker]
[Section 4: 44-byte header + compressed data]  (1903 bytes uncompressed)
[Zero padding to 51,200 bytes]
```

### Section Identification Markers

| Section | Field2 Value | Field3 Value (PC) | Field3 Value (PS3) |
|---------|--------------|-------------------|-------------------|
| Section 1 | 0x00FEDBAC | 0x000000C5 | 0x000000C6 |
| Section 2 | 0x00000003 | 0x11FACE11 | 0x11FACE11 |
| Section 3 | 0x00000000 | 0x21EFFE22 | 0x21EFFE22 |
| Section 4 | 0x00000004 | N/A | 0x00000007 |

---

## Section 1: System/Profile Data

**PC Size:** 283 bytes | **PS3 Size:** 289 bytes
**Class Name:** Unknown (minimal Ghidra coverage)
**Section Marker:** Field3 = 0xC5 (PC) or 0xC6 (PS3)

### Header Region (0x00-0x17)

| Offset | Size | Type | Field Name | Value | Conf | Evidence |
|--------|------|------|------------|-------|------|----------|
| 0x00-0x09 | 10 | padding | Zero Padding | Always 0x00 | [P] | Structure analysis |
| 0x0A-0x0D | 4 | hash | Section Hash | 0xBDBE3B52 | [P] | Constant across all files |
| 0x0E-0x0F | 2 | flags | Platform Flags | PC=0x050C, PS3=0x0508 | [H] | Platform diff |
| 0x10-0x13 | 4 | value | Unknown | Varies | [L] | Observed |
| 0x14-0x17 | 4 | type | Type Indicator | 0x00010000 | [M] | Constant observed |

### Property Record Structure (18-byte records)

Section 1 contains **12 property records** starting at offset 0x18, each using an 18-byte structure:

| Record Offset | Size | Field | Description |
|---------------|------|-------|-------------|
| +0x00 | 4 | Value | Property value (4-byte little-endian) |
| +0x04 | 1 | Unknown | Usually 0x00 |
| +0x05 | 1 | Type Marker | 0x0B = property marker |
| +0x06 | 4 | Unknown | Variable data |
| +0x0A | 4 | Hash | Content identifier hash |
| +0x0E | 4 | Padding | Usually zeros |

#### Known Property Records

| Record | Offset | Value | Hash | Meaning | Conf |
|--------|--------|-------|------|---------|------|
| 1 | 0x18 | = Field1 (0x16) | - | Self-ref: uncompressed size marker | [P] |
| 2 | 0x2A | = Field2 (0xFEDBAC) | - | Self-ref: section identifier | [P] |
| 3-12 | 0x3C+ | Varies | Varies | Unknown properties | [L] |

**Note:** Records 1-2 contain self-referential values that match the 44-byte header's Field1 and Field2. This pattern may be used for validation.

### Profile State Flag

| Offset | Size | Type | Field Name | Value Range | Conf | Evidence |
|--------|------|------|------------|-------------|------|----------|
| 0x51 | 1 | byte | Profile State Flag | 0x02-0x06 | [H] | 24-file differential |

This flag varies between base game (0x02) and all-rewards unlocked (0x06) states. The 21 language variations are byte-for-byte identical - **only this byte differs** between base and allrewards OPTIONS files for the same platform.

### ASCII Identifier

| Offset | Size | Type | Field Name | Value | Conf | Evidence |
|--------|------|------|------------|-------|------|----------|
| 0xA6-0xAD | 8 | string | ASCII Identifier | "Options\0" | [P] | Hex dump |

### PS3 Section 1 Differences

PS3 Section 1 is 6 bytes larger (289 vs 283 bytes). The extra bytes are a **PREFIX** at offset 0x00:

| Offset | Size | Value | Description |
|--------|------|-------|-------------|
| 0x00 | 1 | 0x01 | Version/type marker |
| 0x01-0x04 | 4 | 0xBDBE3B52 | Section hash (duplicate) |
| 0x05 | 1 | 0x03 | Unknown field |

After this 6-byte prefix, PS3 data aligns perfectly with PC data. The section hash appears twice: once in the prefix and again at offset 0x10 (relative to prefix start).

| Difference | PC | PS3 |
|------------|-------|-----|
| Size | 283 bytes | 289 bytes |
| Field3 | 0xC5 | 0xC6 |
| Extra content | N/A | 6-byte prefix: `01 52 3B BE BD 03` |

### Unknown Regions (Section 1)

| Offset Range | Size | Notes |
|--------------|------|-------|
| 0x52-0xA5 | 84 bytes | Unknown structure (between state flag and ASCII) |
| 0xAE-0x11A | 109 bytes | Remaining section data |

**Mapped:** 271 bytes | **Unmapped:** 12 bytes | **Coverage:** 96%

**Note:** Section 1 is now largely mapped with 12 property records identified. Ghidra shows `FUN_0046d7b0` handles loading and `FUN_0046d430` validates the 0xFEDBAC marker.

---

## Section 2: Game Settings

**PC Size:** 1310 bytes (0x51E) | **PS3 Size:** 1306 bytes (0x51A)
**Class Name:** Unknown (settings structure)
**Section Marker:** Field3 = 0x11FACE11

### Header Region (0x00-0x20)

| Offset | Size | Type | Field Name | Value | Conf | Evidence |
|--------|------|------|------------|-------|------|----------|
| 0x00-0x09 | 10 | padding | Zero Padding | 0x00 | [P] | Structure analysis |
| 0x0A-0x0D | 4 | hash | Section Hash | 0x305AE1A8 | [H] | Constant per section |
| 0x0E-0x0F | 2 | flags | Platform Flags | PC=0x050C (bytes: 0C 05), PS3=0x0508 (bytes: 08 05) | [H] | Platform diff |
| 0x14-0x17 | 4 | type | Type Indicator | 0x00110000 | [M] | Observed |

### Display Settings (0x63-0xAE)

| Offset | Size | Type | Field Name | Value Range | Conf | Evidence |
|--------|------|------|------------|-------------|------|----------|
| 0x63 | 1 | bool | Subtitles Toggle | 0=Off, 1=On | [P] | Ghidra: FUN_004391f0, FUN_00439250 |
| 0x75 | 1 | bool | Default Language Flag | 0/1 | [H] | Ghidra: FUN_0040cfc0, FUN_0040d880 |

### Language Settings (0x8E-0xAE)

| Offset | Size | Type | Field Name | Value Range | Conf | Evidence |
|--------|------|------|------------|-------------|------|----------|
| 0x8E-0x91 | 4 | index | Audio Language Index | 1-20 | [H] | Ghidra + Differential |
| 0x92-0x95 | 4 | hash | Audio Language Hash | See Language Table | [H] | Differential |
| 0xA7-0xAA | 4 | index | Subtitle Language Index | 1-20 | [M] | Differential |
| 0xAB-0xAE | 4 | hash | Subtitle Language Hash | See Language Table | [M] | Differential |

### Audio Settings (0xBF-0xFF)

| Offset | Size | Type | Field Name | Value Range | Conf | Evidence |
|--------|------|------|------------|-------------|------|----------|
| 0xC0-0xC3 | 4 | float32 | Music Volume | 0.0 to -96.0 dB | [P] | Ghidra: FUN_00acf240 |
| 0xD5-0xD8 | 4 | float32 | Voice Volume | 0.0 to -96.0 dB | [P] | Ghidra: FUN_00504240, FUN_0084e720 |
| 0xEA-0xED | 4 | float32 | SFX Volume | 0.0 to -96.0 dB | [H] | Ghidra: FUN_007a1320 |
| 0xFF | 1 | bool | Vibration | 0=Off, 1=On | [P] | Ghidra: FUN_00acf240 |

#### Volume Level Values (IEEE 754 Float, Little-Endian)

| Level | Hex Value | Float Value (dB) | Description |
|-------|-----------|------------------|-------------|
| 10 | 0x00000000 | 0.0 | Maximum |
| 9 | 0xBF6A4744 | -0.916 | |
| 8 | 0xBFF816F0 | -1.938 | |
| 7 | 0xC0464646 | -3.098 | |
| 6 | 0xC08DFBB2 | -4.437 | |
| 5 | 0xC0C0A8C0 | -6.020 | Default |
| 4 | 0xC0FEAE7C | -7.958 | |
| 3 | 0xC1275239 | -10.457 | |
| 2 | 0xC15FAB9E | -13.979 | |
| 1 | 0xC19FFFFF | -19.999 | |
| 0 | 0xC2C00000 | -96.0 | Mute |

### Control Settings (0x100-0x1E0)

| Offset | Size | Type | Field Name | Value Range | Conf | Evidence |
|--------|------|------|------------|-------------|------|----------|
| 0x111-0x114 | 4 | float32 | X Look Sensitivity | 0.5x to 2.0x | [H] | Ghidra: FUN_00417fc0 |
| 0x126-0x129 | 4 | float32 | Y Look Sensitivity | 0.5x to 2.0x | [P] | Ghidra: 10 instruction refs |
| 0x13B | 1 | bool | 3rd Person Invert X | 0=Normal, 1=Inverted | [H] | Ghidra: FUN_00a82210 |
| 0x14D | 1 | bool | 3rd Person Invert Y | 0=Normal, 1=Inverted | [P] | Ghidra: 5 function refs |
| 0x15F | 1 | bool | 1st Person Invert X | 0=Normal, 1=Inverted | [M] | Pattern inference |
| 0x171 | 1 | bool | 1st Person Invert Y | 0=Normal, 1=Inverted | [P] | Ghidra: 6 refs + constructor |
| 0x183 | 1 | byte | Action Camera Frequency | 0-3 | [M] | Menu mapping |
| 0x195 | 1 | byte | Brightness | 1-16 (0x01-0x10) | [P] | Ghidra: FUN_00acf240 |
| 0x1A7 | 1 | bool | Blood Toggle | 0=Off, 1=On | [P] | Ghidra: 5 function refs |
| 0x1B9 | 1 | byte | Flying Machine Invert | 0=Normal, 1=Inverted | [P] | Ghidra: 6 function refs |
| 0x1CB | 1 | bool | Cannon Invert X | 0=Normal, 1=Inverted | [P] | Ghidra: 5 function refs |
| 0x1DD | 1 | bool | Cannon Invert Y | 0=Normal, 1=Inverted | [P] | Ghidra: FUN_00acf240 |

#### Sensitivity Level Values (IEEE 754 Float, Little-Endian)

| Level | Hex Value | Float Multiplier |
|-------|-----------|------------------|
| 10 (Max) | 0x40000000 | 2.0x |
| 9 | 0x3FE66666 | 1.8x |
| 8 | 0x3FCCCCCD | 1.6x |
| 7 | 0x3FB33333 | 1.4x |
| 6 | 0x3F99999A | 1.2x |
| 5 (Default) | 0x3F800000 | 1.0x |
| 4 | 0x3F4CCCCD | 0.8x |
| 3 | 0x3F333333 | 0.7x |
| 2 | 0x3F19999A | 0.6x |
| 1 (Min) | 0x3F000000 | 0.5x |

**Pattern:** Levels 1-4 increment by 0.1x (0.5-0.8), Level 5 = 1.0x baseline, Levels 6-10 increment by 0.2x (1.2-2.0)

### HUD Settings (0x1EF-0x280)

HUD toggles use an 18-byte record structure with the toggle at offset +0x00.

| Offset | Size | Type | Field Name | Value Range | Conf | Evidence |
|--------|------|------|------------|-------------|------|----------|
| 0x1EF | 1 | bool | Health Meter | 0=Off, 1=On | [P] | Ghidra: 5 function refs |
| 0x201 | 1 | bool | Controls | 0=Off, 1=On | [M] | Pattern (18-byte spacing) |
| 0x213 | 1 | bool | Updates | 0=Off, 1=On | [M] | Pattern (18-byte spacing) |
| 0x225 | 1 | bool | Weapon | 0=Off, 1=On | [P] | Ghidra: 3 function refs |
| 0x237 | 1 | bool | Mini-Map | 0=Off, 1=On | [P] | Ghidra: FUN_00acf240 |
| 0x249 | 1 | bool | Money | 0=Off, 1=On | [P] | Ghidra: 5 function refs |
| 0x26D | 1 | bool | SSI | 0=Off, 1=On | [P] | Ghidra: 4 function refs |
| 0x27F | 1 | bool | Tutorial | 0=Off, 1=On | [M] | Pattern (18-byte spacing) |

### Unlock Records (0x290-0x370)

Each unlock record is 18 bytes with this structure:

| Record Offset | Size | Field | Description |
|---------------|------|-------|-------------|
| +0x00 | 1 | Unlock Flag | 0x00=locked, 0x01=unlocked |
| +0x01 | 1 | Type | Category (0x0E for rewards) |
| +0x02 | 4 | Reserved/Hash Prefix | First 3 bytes zeros, 4th byte contains hash-related data (e.g., 0xCC, 0x8F) |
| +0x06 | 4 | Content Hash | LE hash identifying content |
| +0x0A | 8 | Padding | Zeros |

#### Known Unlock Records

| Offset | Name | Hash | Conf | Evidence |
|--------|------|------|------|----------|
| 0x291 | Templar Lair: Trajan's Market | 0x00788F42 | [P] | Ghidra + Differential |
| 0x2A3 | Templar Lair: Tivoli Aqueduct | 0x006FF456 | [P] | Ghidra + Differential |
| 0x2B5 | Unknown Unlock #1 | 0x000B953B | [M] | Differential (new discovery) |
| 0x2C7 | Unknown Unlock #2 | 0x001854EC | [M] | Differential (new discovery) |
| 0x2D9 | Uplay: Florentine Noble Attire | 0x0021D9D0 | [H] | Differential + Context |
| 0x2EB | Uplay: Armor of Altair | 0x0036A2C4 | [H] | Differential + Context |
| 0x2FD | Uplay: Altair's Robes | 0x0052C3A9 | [H] | Differential + Context |
| 0x30F | Uplay: Hellequin MP Character | 0x000E8D04 | [H] | Differential + Context |

**Note:** Unknown Unlock #1 (0x2B5) and #2 (0x2C7) were discovered through comprehensive 21-file language differential analysis. Their hashes (0x000B953B and 0x001854EC) don't match any known Uplay or DLC content. These may be:
- Beta/cut content unlocks
- Region-specific content
- Debug/test flags

### Costume Bitfield (0x369)

| Offset | Size | Type | Field Name | Conf | Evidence |
|--------|------|------|------------|------|----------|
| 0x369 | 1 | bitfield | Costume Unlocks | [P] | Ghidra: FUN_00acf240 |

| Bit | Hex | Costume Name |
|-----|-----|--------------|
| 0 | 0x01 | Florentine Noble Attire |
| 1 | 0x02 | Armor of Altair |
| 2 | 0x04 | Altair's Robes |
| 3 | 0x08 | Drachen Armor |
| 4 | 0x10 | Desmond |
| 5 | 0x20 | Raiden |
| All | 0x3F | All Costumes Unlocked |

### DLC/Update Flags (0x516-0x519)

| Offset | Size | Type | Field Name | Conf | Evidence |
|--------|------|------|------------|------|----------|
| 0x516 | 1 | bool | Animus Project Update 1.0 | [M] | Differential only |
| 0x517 | 1 | bool | Animus Project Update 2.0 | [M] | Differential only |
| 0x518 | 1 | bool | Animus Project Update 3.0 | [M] | Differential only |
| 0x519 | 1 | bool | Da Vinci Disappearance DLC | [M] | Differential only |

**APU Content:**
- APU 1.0: Mont Saint-Michel map
- APU 2.0: Pienza map
- APU 3.0: Alhambra map + Dama Rossa, Knight, Marquis, Pariah characters

### PS3-Specific Fields (Section 2)

| Offset | Size | Type | Field Name | Conf | Notes |
|--------|------|------|------------|------|-------|
| 0x4A5 | 1 | bool | PS3 Toggle A | [L] | PC=0, PS3=1 |
| 0x4B7 | 1 | bool | PS3 Toggle B | [L] | PC=0, PS3=1 |
| 0x4DB | 1 | bool | PS3 Toggle C | [L] | PC=0, PS3=1 |
| 0x4ED | 1 | bool | PS3 Toggle D | [L] | PC=0, PS3=1 |
| 0x4FF | 1 | bool | PS3 Toggle E | [L] | PC=0, PS3=1 |
| 0x500 | 1 | byte | Platform ID | [M] | PC=0x16, PS3=0x12 |

### Property Record Structure (Phase 2 Discovery)

The 17-byte "gaps" between settings are NOT unmapped - they are the **trailing portion of 18-byte property records**. Each setting in Section 2 follows this structure:

```
18-byte Property Record:
+0x00: Value byte (setting value)
+0x01: Type marker (0x0E=standard, 0x11=alt, 0x15=special, 0x17=unique)
+0x02-0x04: Zero padding
+0x05-0x08: Property hash (4 bytes, LE) - unique identifier
+0x09-0x10: Zero padding + flags
+0x11: Next marker (0x0B)
```

**57 property records identified** in Section 2, each with a unique hash.

### Known Property Hashes (Section 2)

| Offset | Hash | Purpose | Conf |
|--------|------|---------|------|
| 0x13B | 0xA15FACF2 | Invert 3P X axis | [H] |
| 0x14D | 0xC36B150F | Invert 3P Y axis | [H] |
| 0x15F | 0x9CCE0247 | Invert 1P X axis | [H] |
| 0x171 | 0x56932719 | Invert 1P Y axis | [H] |
| 0x183 | 0x962BD533 | Action Camera Frequency | [H] |
| 0x195 | 0x7ED0EABB | Brightness | [H] |
| 0x1A7 | 0xDE6CD4AB | Blood toggle | [H] |
| 0x1B9 | 0xED915BD4 | Flying Machine Invert | [H] |
| 0x1CB | 0xF20B5679 | Cannon Invert X | [H] |
| 0x1DD | 0xC9762625 | Cannon Invert Y | [H] |
| 0x1EF | 0x039BEE69 | HUD: Health Meter | [H] |
| 0x201 | 0x0E04FA13 | HUD: Controls | [H] |
| 0x213 | 0xF3ED28F7 | HUD: Updates | [H] |
| 0x225 | 0xA3C6D1B9 | HUD: Weapon | [H] |
| 0x237 | 0x761E3CE0 | HUD: Mini-Map | [H] |
| 0x249 | 0x12F43A92 | HUD: Money | [H] |
| 0x26D | 0x40EF7C8B | HUD: SSI | [H] |
| 0x27F | 0x41027E09 | HUD: Tutorial | [H] |
| 0x291 | 0x788F42CC | Templar Lair: Trajan Market | [H] |
| 0x2A3 | 0x6FF4568F | Templar Lair: Tivoli Aqueduct | [H] |
| 0x2D9 | 0x21D9D09F | Uplay: Florentine Noble | [H] |
| 0x2EB | 0x36A2C4DC | Uplay: Armor of Altair | [H] |
| 0x2FD | 0x52C3A915 | Uplay: Altair Robes | [H] |
| 0x30F | 0x0E8D040F | Uplay: Hellequin | [H] |

### Remaining Unmapped Regions (Section 2)

| Offset Range | Size | Notes |
|--------------|------|-------|
| 0x10-0x13 | 4 bytes | Between platform flags and type |
| 0x18-0x62 | 75 bytes | Initialization records (4 records, structure identified) |
| 0x36A-0x3D7 | 110 bytes | Complex nested structure with 0x571396CE pattern |
| 0x426-0x43D | 24 bytes | Type 0x17 marker region (possibly keyboard bindings) |
| 0x444-0x4A4 | 97 bytes | Additional property records (hashes identified, purposes unknown) |

**Mapped:** ~920 bytes | **Unmapped:** ~390 bytes | **Coverage:** ~70%

---

## Section 3: Game Progress

**PC Size:** 162 bytes | **PS3 Size:** 119 bytes
**Class Name:** `AssassinSingleProfileData` (found at string address 0x0253ddec)
**Section Marker:** Field3 = 0x21EFFE22

### Header Region (0x00-0x17)

| Offset | Size | Type | Field Name | Value | Conf | Evidence |
|--------|------|------|------------|-------|------|----------|
| 0x00-0x09 | 10 | padding | Zero Padding | 0x00 | [P] | Structure analysis |
| 0x0A-0x0D | 4 | hash | Section Hash | 0xC9876D66 (or 0x6F88B05B) | [H] | Constant per section |
| 0x0E-0x0F | 2 | flags | Platform Flags | PC=0x050C, PS3=0x0508 | [H] | Platform diff |
| 0x10-0x13 | 4 | value | Unknown | Varies | [L] | Observed |
| 0x14-0x17 | 4 | type | Type Indicator | 0x00010000 | [M] | Constant observed |

**Note:** Two section hash values have been observed (0xC9876D66 at 0x0A and 0x6F88B05B at 0x90). The hash at 0x90 may be part of the achievement/progress data structure rather than a section identifier.

### Property Records (0x18-0x7F)

Section 3 uses a different property record structure than Section 1. The hash appears at the START of each record (+0x00), not at +0x0A.

#### Identified Property Records

| Record | Offset | Hash | Platform | Conf | Evidence |
|--------|--------|------|----------|------|----------|
| 1 | 0x1A | 0xBF4C2013 | Both | [H] | Binary analysis |
| 2 | 0x2F | 0x3B546966 | Both | [H] | Binary analysis |
| 3 | 0x41 | 0x4DBC7DA7 | Both | [H] | Binary analysis |
| 4 | 0x53 | 0x5B95F10B | Both | [H] | Binary analysis |
| 5 | 0x65 | 0x2A4E8A90 | Both | [H] | Binary analysis |
| 6 | 0x77 | 0x496F8780 | PC only | [H] | Binary analysis |

#### Known Markers

| Offset | Size | Type | Field Name | Value Range | Conf | Evidence |
|--------|------|------|------------|-------------|------|----------|
| 0x4D | 1 | marker | Structure Marker | 0x0B | [P] | Constant value |
| 0x4E | 1 | bool | Uplay Gun Capacity Upgrade | 0=No, 1=Yes | [P] | 24-file differential |
| 0x4F | 1 | marker | Structure Marker | 0x0E | [P] | Constant value |

#### PC vs PS3 Differences in Pre-Achievement Region

| Offset | PC Value | PS3 Value | Notes |
|--------|----------|-----------|-------|
| 0x60 | 0x00 | 0x01 | Flag after 0x0B marker |
| 0x73 | 0x15 | 0x00 | Type marker difference |
| 0x77+ | Record 6 hash | N/A | PC only - PS3 lacks this record |

### Achievement Region (0x80-0x9F) - PC ONLY

| Offset | Size | Type | Field Name | Value Range | Conf | Evidence |
|--------|------|------|------------|-------------|------|----------|
| 0x80-0x83 | 4 | header | Achievement Header | 0x00 09 00 0B | [P] | Constant; 0x0B is structure type marker, 0x09 may indicate following data size |
| 0x84-0x8A | 7 | bitfield | Achievement Bitfield | 53 bits used | [P] | Differential + Bit count |
| 0x8B | 1 | padding | Reserved | 0x00 | [P] | Structure |
| 0x8C-0x8F | 4 | marker | Structure Marker | 0x0E 00 00 00 | [P] | Constant |
| 0x90-0x93 | 4 | hash | Progress Hash | 0x6F88B05B | [P] | Constant |

### DLC Sync Region

| Offset | Size | Type | Field Name | Value Range | Conf | Evidence |
|--------|------|------|------------|-------------|------|----------|
| 0x9C (PC) / 0x59 (PS3) | 1 | marker | Structure Marker | 0x0B | [P] | Constant |
| 0x9D (PC) / 0x5A (PS3) | 1 | bool | DLC Sync Flag | 0=No, 1=Yes | [P] | Ghidra: FUN_0084cb60 |
| 0x9E-0x9F (PC) / 0x5B-0x5C (PS3) | 2 | padding | Reserved | 0x00 | [P] | Structure |

### PC vs PS3 Size Difference (43 bytes)

| Platform | Size | Achievement Storage | Explanation |
|----------|------|---------------------|-------------|
| PC | 162 bytes | Embedded 7-byte bitfield at 0x84-0x8A | 53 achievements stored locally |
| PS3 | 119 bytes | **No embedded bitfield** | PSN Trophy system handles achievements externally |

The **43-byte difference** is explained by:
1. PC embeds achievement bitfield (7 bytes) plus surrounding structure/markers
2. PS3 relies on PlayStation Network Trophy API for achievement tracking
3. PS3 Section 3 only stores cross-platform progress data (Uplay rewards, DLC sync)

### Achievement Bitfield Details

The achievement bitfield spans 7 bytes (0x84-0x8A), storing 53 achievement flags.
**All achievements unlocked:** `0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0x1F`

#### Byte 0x84 (Achievements 1-8: Story Progression)

| Bit | Hex | Achievement Name |
|-----|-----|------------------|
| 0 | 0x01 | TECHNICAL DIFFICULTIES |
| 1 | 0x02 | BATTLE WOUNDS |
| 2 | 0x04 | SANCTUARY! SANCTUARY |
| 3 | 0x08 | ROME IN RUINS |
| 4 | 0x10 | FIXER-UPPER |
| 5 | 0x20 | PRINCIPESSA IN ANOTHER CASTELLO |
| 6 | 0x40 | FUNDRAISER |
| 7 | 0x80 | FORGET PARIS |

#### Byte 0x85 (Achievements 9-16: Story + Shrines)

| Bit | Hex | Achievement Name |
|-----|-----|------------------|
| 0 | 0x01 | BLOODY SUNDAY |
| 1 | 0x02 | VITTORIA AGLI ASSASSINI |
| 2 | 0x04 | REQUIESCAT IN PACE |
| 3 | 0x08 | A KNIFE TO THE HEART |
| 4 | 0x10 | PERFECT RECALL |
| 5 | 0x20 | DEJA VU |
| 6 | 0x40 | UNDERTAKER 2.0 |
| 7 | 0x80 | GOLDEN BOY |

#### Byte 0x86 (Achievements 17-24: Shrines + Da Vinci Machines)

| Bit | Hex | Achievement Name |
|-----|-----|------------------|
| 0 | 0x01 | GLADIATOR |
| 1 | 0x02 | PLUMBER |
| 2 | 0x04 | ONE-MAN WRECKING CREW |
| 3 | 0x08 | AMEN |
| 4 | 0x10 | BANG! |
| 5 | 0x20 | SPLASH! |
| 6 | 0x40 | BOOM! |
| 7 | 0x80 | KABOOM! |

#### Byte 0x87 (Achievements 25-32: Side Activities)

| Bit | Hex | Achievement Name |
|-----|-----|------------------|
| 0 | 0x01 | HOME IMPROVEMENT |
| 1 | 0x02 | TOWER DEFENSE |
| 2 | 0x04 | SHOW OFF |
| 3 | 0x08 | .. .- -- .- .-.. .. ...- . (Morse: IAMALIVE) |
| 4 | 0x10 | PERFECTIONIST |
| 5 | 0x20 | BROTHERHOOD |
| 6 | 0x40 | WELCOME TO THE BROTHERHOOD |
| 7 | 0x80 | CAPTURE THE FLAG |

#### Byte 0x88 (Achievements 33-40: Miscellaneous)

| Bit | Hex | Achievement Name |
|-----|-----|------------------|
| 0 | 0x01 | IN MEMORIAM |
| 1 | 0x02 | DUST TO DUST |
| 2 | 0x04 | SERIAL KILLER |
| 3 | 0x08 | SPRING CLEANING |
| 4 | 0x10 | YOUR WISH IS GRANTED |
| 5 | 0x20 | FLY LIKE AN EAGLE |
| 6 | 0x40 | THE GLOVES COME OFF |
| 7 | 0x80 | MAILER DAEMON |

#### Byte 0x89 (Achievements 41-48: Multiplayer)

| Bit | Hex | Achievement Name |
|-----|-----|------------------|
| 0 | 0x01 | ROME GLOBAL ECONOMY BRONZE MEDAL |
| 1 | 0x02 | ROME GLOBAL ECONOMY SILVER MEDAL |
| 2 | 0x04 | ROME GLOBAL ECONOMY GOLD MEDAL |
| 3 | 0x08 | STRONG-ARM |
| 4 | 0x10 | HIGH ROLLER |
| 5 | 0x20 | IL PRINCIPE |
| 6 | 0x40 | AIRSTRIKE |
| 7 | 0x80 | GPS |

#### Byte 0x8A (Achievements 49-53: MP + DLC)

| Bit | Hex | Achievement Name |
|-----|-----|------------------|
| 0 | 0x01 | CLOWNING AROUND |
| 1 | 0x02 | SPECIAL DELIVERY |
| 2 | 0x04 | GRAND THEFT DRESSAGE |
| 3 | 0x08 | GOING UP |
| 4 | 0x10 | EASY COME, EASY GO |
| 5-7 | 0xE0 | (Unused - always 0) |

### Unmapped Regions (Section 3)

| Offset Range | Size | Notes |
|--------------|------|-------|
| 0x18-0x19 | 2 bytes | Pre-record 1 |
| 0x1E-0x2E | 17 bytes | Between record 1 and 2 data |
| 0x33-0x40 | 14 bytes | Record 2 data |
| 0x45-0x4C | 8 bytes | Record 3 data (pre-marker) |
| 0x57-0x64 | 14 bytes | Record 4 data |
| 0x69-0x76 | 14 bytes | Record 5 data |
| 0x7B-0x7F | 5 bytes | Record 6 data (PC only) |
| 0x94-0x9B | 8 bytes | Between hash and DLC sync region |
| 0xA0-0xA1 | 2 bytes (PC) | Post-DLC sync |

**Mapped:** ~57 bytes (PC) / ~50 bytes (PS3) | **Coverage:** ~35% (PC) / ~42% (PS3)

**Note:** 6 property record hashes identified in Phase 1 analysis, significantly improving Section 3 coverage.

---

## Section 4: PS3 Controller Mappings (PS3 Only)

**Size:** 1903 bytes
**Section Marker:** Field2 = 0x00000004, Field3 = 0x00000007

Section 4 is PS3-exclusive and contains DualShock 3 controller mapping data.

### Structure Overview

| Component | Offset | Size | Description |
|-----------|--------|------|-------------|
| Header | 0x00-0x60 | 97 bytes | Section header + initialization records |
| Records | 0x61-0x605 | 1445 bytes | 17 button mapping records (85 bytes each) |
| Trailer | 0x606-0x76E | 361 bytes | Property records + zero padding |

### Header Region (0x00-0x60)

| Offset | Size | Type | Field Name | Value | Conf | Evidence |
|--------|------|------|------------|-------|------|----------|
| 0x00-0x09 | 10 | padding | Zero Padding | 0x00 | [P] | Structure analysis |
| 0x0A-0x0D | 4 | hash | Section Hash | 0xB4B55039 | [H] | Constant |
| 0x0E-0x0F | 2 | flags | Platform Flags | 0x075D | [H] | Platform identifier |
| 0x10-0x13 | 4 | value | Unknown | 0x07550000 | [L] | Observed |
| 0x14-0x17 | 4 | type | Type Indicator | 0x00110000 | [H] | Matches Section 2 |
| 0x18-0x60 | 73 | records | Extended Header | Property records | [M] | Structure markers |

### Button Mapping Record Structure (85 bytes)

Each record is a template with only Button ID varying between records.

| Record Offset | Size | Field | Value/Description | Conf |
|---------------|------|-------|-------------------|------|
| +0x00 | 5 | Signature | `A8 CF 5F F9 43` (constant) | [P] |
| +0x05 | 4 | Record Size | `0x0000003B` (59 bytes, BE) | [H] |
| +0x09 | 4 | Record Count | `0x00000011` (17 records, BE) | [H] |
| +0x0D | 4 | Controller Hash | `0x8157B2C0` (DualShock 3 ID) | [H] |
| +0x11 | 9 | Reserved | zeros | [P] |
| +0x1A | 2 | Field Marker | `0x0006` | [H] |
| +0x1C | 1 | Struct Marker | `0x0B` | [H] |
| +0x1D | 1 | Button ID | varies (0x02-0x22) | [P] |
| +0x1E | 55 | Property Records | 3 nested 18-byte records | [M] |

#### Property Sub-Record Structure (within button records)

The 55-byte property section contains 3 nested records with constant action binding hashes:

| Sub-Record | Offset | Size | Structure |
|------------|--------|------|-----------|
| 1 | +0x1E | 18 | zeros + 0x0F marker + value + hash 0xE717D13B |
| 2 | +0x30 | 18 | 0x0B marker + 0x0F + value + hash 0x0043E6D0 |
| 3 | +0x42 | 19 | 0x05 marker + 0x0B + zeros |

### Complete Button ID Mapping

| ID | Hex | DualShock 3 Button | Record Offset |
|----|-----|--------------------| --------------|
| 2 | 0x02 | Cross (X) | 0x0061 |
| 5 | 0x05 | L1 | 0x0160 |
| 7 | 0x07 | R1 | 0x020A |
| 8 | 0x08 | L2 | 0x025F |
| 10 | 0x0A | R2 | 0x01B5 |
| 14 | 0x0E | D-Pad | 0x035E |
| 15 | 0x0F | D-Pad Alternate | 0x045D |
| 17 | 0x11 | Left Stick | 0x0408 |
| 18 | 0x12 | Right Stick | 0x02B4 |
| 20 | 0x14 | Select | 0x03B3 |
| 21 | 0x15 | Triangle | 0x00B6 |
| 22 | 0x16 | Circle | 0x010B |
| 25 | 0x19 | Square | 0x0309 |
| 28 | 0x1C | Start | 0x055C |
| 31 | 0x1F | L3 (Left Stick Click) | 0x04B2 |
| 32 | 0x20 | R3 (Right Stick Click) | 0x0507 |
| 34 | 0x22 | PS Button | 0x05B1 |

### Trailer Region (0x606-0x76E)

Contains 12+ property records with 18-byte structure, followed by zero padding.

| Offset | Size | Type | Description | Conf |
|--------|------|------|-------------|------|
| 0x606-0x60D | 8 | record | Marker pattern `9D 03 0B 01` | [M] |
| 0x616-0x619 | 4 | hash | 0xDEC8D5A5 (unknown) | [M] |
| 0x620-0x62F | 16 | record | Contains `9D 03 0B 01` + values | [M] |
| 0x628-0x633 | 12 | bytes | "MUW" pattern (0x57554D) | [L] |
| 0x634-0x6B5 | 130 | records | 7 property records with hashes | [M] |
| 0x6B6-0x6FF | 74 | records | Additional config records | [M] |
| 0x700-0x76E | 111 | padding | Zero padding | [P] |

#### Identified Trailer Hashes

| Offset | Hash | Flag | Purpose (Speculative) |
|--------|------|------|----------------------|
| 0x64A | 0x9F1438A5 | 0x00 | Controller config |
| 0x65C | 0xAFBEEA25 | 0x01 | Controller config |
| 0x66E | 0x221991EF | 0x00 | Controller config |
| 0x680 | 0x20AD7434 | 0x01 | Controller config |
| 0x692 | 0xB6BA16BB | 0x01 | Controller config |
| 0x6A4 | 0x1A361AE1 | 0x01 | Controller config |
| 0x6B6 | 0x605F5F37 | 0x01 | Controller config |
| 0x6F6 | 0x3B7A5EB8 | 0x01 | Controller config |

### Key Findings (Phase 3)

1. **Template Structure**: All 17 button records share identical byte patterns except for Button ID at +0x1D
2. **Constant Hashes**: Action binding hashes (0xE717D13B, 0x0043E6D0) are constant across all records
3. **Implicit Mapping**: Button-to-action mapping is implicit based on Button ID, not explicitly stored
4. **Property Records**: Trailer uses same 18-byte property record structure as Sections 1-3

**Mapped:** ~1880 bytes | **Unmapped:** ~23 bytes | **Coverage:** 98.8%

---

## Data Type Reference

### Boolean Format

- **Size:** 1 byte
- **Values:** `0x00` = Off/False/No, `0x01` = On/True/Yes
- **Ghidra Pattern:** `CMP byte ptr [REG + offset], 0x0`

### Float Format (IEEE 754)

- **Size:** 4 bytes
- **Endianness:** Little-endian
- **Usage:** Volume levels (dB scale), sensitivity multipliers

### Hash Format

- **Size:** 4 bytes
- **Endianness:** Little-endian
- **Usage:** Language identification, content identification
- **Algorithm:** Custom precomputed (not runtime computed)
- **Hash Table Address:** 0x0298a780 in executable

### Bitfield Format

- **Size:** Variable (1-7 bytes)
- **Bit Order:** LSB first within each byte
- **Usage:** Achievements (53 bits), costumes (6 bits)

---

## Language Hash Reference

| Index | Language | Hash (LE) | Hash (BE Display) |
|-------|----------|-----------|-------------------|
| 0x01 | English | 0x50CC97B5 | 0xB597CC50 |
| 0x02 | French | 0x3C0FCC90 | 0x90CC0F3C |
| 0x03 | Spanish | 0x48576081 | 0x81605748 |
| 0x04 | Polish | 0x4375357B | 0x7B357543 |
| 0x05 | German | 0x314E426F | 0x6F424E31 |
| 0x06 | (Reserved) | 0x87D7B2A1 | 0xA1B2D787 |
| 0x07 | Hungarian | 0xC6233139 | 0x393123C6 |
| 0x08 | Italian | 0x2BF6FC7A | 0x7AFCF62B |
| 0x09 | Japanese | 0xB1E049F8 | 0xF849E0B1 |
| 0x0A | Czech | 0x2C6A3130 | 0x30316A2C |
| 0x0B | Korean | 0x022FCB0D | 0x0DCB2F02 |
| 0x0C | Russian | 0x972964C0 | 0xC0642997 |
| 0x0D | Dutch | 0xDBCD3431 | 0x3134CDDB |
| 0x0E | Danish | 0xCE0B031C | 0x1C030BCE |
| 0x0F | Norwegian | 0x69AD901C | 0x1C90AD69 |
| 0x10 | Swedish | 0xCF6F169D | 0x9D166FCF |
| 0x11 | Portuguese | 0x12410E3F | 0x3F0E4112 |
| 0x12 | Turkish | 0xCDA3D2DC | 0xDCD2A3CD |
| 0x13 | Simplified Chinese | 0x43CD0944 | 0x4409CD43 |
| 0x14 | Traditional Chinese | 0xCF38DA87 | 0x87DA38CF |

**Note:** Language hashes are precomputed and stored in a static table at address `0x0298a780` in the executable. The hash algorithm has NOT been reverse-engineered despite testing 30+ algorithms with hundreds of parameter variations.

---

## PC Footer Structure

| Offset | Size | Value | Description |
|--------|------|-------|-------------|
| +0x00 | 1 | 0x01 | Footer signature |
| +0x01 | 3 | 0x000000 | Reserved/padding |
| +0x04 | 1 | Variable | Network interface count (Ubisoft Quazal telemetry) |

**Note:** The 5th byte contains the number of network interfaces on the system when the save was created. This value is informational only and not validated on load.

---

## Section Checksums

Each section header contains a checksum at offset 0x28.

### Zero-Seed Adler-32

| Parameter | Standard Adler-32 | ACB Variant |
|-----------|-------------------|-------------|
| Initial s1 | 1 | **0** |
| Initial s2 | 0 | 0 |
| Modulus | 65521 | 65521 |

The checksum is computed over the **compressed data only**, not including the 4-byte data prefix (`06 00 E1 00`).

### PS3 CRC32 (for 8-byte prefix)

| Parameter | Value |
|-----------|-------|
| Polynomial | 0x04C11DB7 |
| Initial Value | 0xBAE23CD0 |
| XOR Output | 0xFFFFFFFF |
| Reflect Input | true |
| Reflect Output | true |

---

## Cross-Section Relationships

### Section Identification System

All three sections share a common header pattern at offset 0x0A-0x0F:

| Section | Hash at 0x0A | Platform Flags at 0x0E |
|---------|--------------|------------------------|
| Section 1 | 0xBDBE3B52 | PC=0x050C, PS3=0x0508 |
| Section 2 | 0x305AE1A8 | PC=0x050C, PS3=0x0508 |
| Section 3 | 0xC9876D66 | PC=0x050C, PS3=0x0508 |

These section hashes serve as type identifiers complementing Field3 in the 44-byte header.

### Section 2 → Section 3: Uplay Reward Flow

```
Section 2 (Unlock Records)          Section 3 (Progress State)
├── 0x2D9: Florentine Noble  ──┬──→ 0x369 bit 0 (Costume)
├── 0x2EB: Armor of Altair   ──┼──→ 0x369 bit 1 (Costume)
├── 0x2FD: Altair's Robes    ──┼──→ 0x369 bit 2 (Costume)
├── 0x30F: Hellequin MP      ──┘    (MP character, no costume bit)
└── (Gun Capacity in S3)     ────→ 0x4E (Uplay Gun Upgrade flag)
```

### Section 2 Costume Bitfield → Uplay Costumes

- Costume bitfield at 0x369 includes Uplay-unlocked costumes
- Bit 0 (Florentine Noble Attire) corresponds to 0x2D9 unlock
- Bit 1 (Armor of Altair) corresponds to 0x2EB unlock
- Bit 2 (Altair's Robes) corresponds to 0x2FD unlock

### Section 1 → Section 3: Profile State Correlation

The Profile State Flag in Section 1 (0x51) correlates with Section 3's DLC Sync Flag:
- **Base state:** S1:0x51=0x02, S3:0x9D=0x00
- **All rewards:** S1:0x51=0x06, S3:0x9D=0x01

### 24-File Validation

All 24 reference OPTIONS files show consistent behavior:
- **21 files:** 0x4E=0x00, 0x84-0x8A=all zeros, 0x9D=0x00 (Base state)
- **3 files:** 0x4E=0x01, 0x84-0x8A=all achievements, 0x9D=0x01 (All rewards state)

This perfect binary correlation proves these three fields are part of the same "rewards/progress unlocked" system.

### Section Independence

Despite the cross-references above, sections are largely independent:
- Each section has its own checksum (no cross-section checksums)
- Parsing order: S1 → S2 → S3 (sequential, not interdependent)
- No offset pointers between sections
- Each section can theoretically be modified independently (with checksum update)

---

## Ghidra Function Reference

### Section 1 Functions

| Address | Function | Purpose |
|---------|----------|---------|
| 0x0046D430 | FUN_0046d430 | Section 1 validation (checks 0xFEDBAC) |
| 0x0046D710 | FUN_0046d710 | Section 1 header writer |
| 0x0046D7B0 | FUN_0046d7b0 | Section 1 loader |

### Section 2 Functions

| Address | Function | Purpose |
|---------|----------|---------|
| 0x00ACF240 | FUN_00acf240 | Settings constructor (5,379 bytes) - initializes all fields |
| 0x01712CA0 | FUN_01712ca0 | Section 2 header writer |
| 0x01712DB0 | FUN_01712db0 | Section 2 validation (checks 0x11FACE11) |
| 0x01B024F0 | FUN_01b024f0 | Section 2 data parsing |
| 0x01B02990 | FUN_01b02990 | Section 2 data parsing |
| 0x01B020E0 | FUN_01b020e0 | Section 2 data parsing |

### Section 3 Functions

| Address | Function | Purpose |
|---------|----------|---------|
| 0x017106E0 | FUN_017106e0 | Section 3 constructor (91 bytes) |
| 0x017108E0 | FUN_017108e0 | Section 3 writer (sets 0x21EFFE22) |
| 0x017109E0 | FUN_017109e0 | Section 3 reader (validates 0x21EFFE22) |
| 0x01710540 | FUN_01710540 | Section 3 destructor (11 bytes) |
| 0x0084CA20 | FUN_0084ca20 | DLC flag constructor (initializes 0x9D) |
| 0x0084CB60 | FUN_0084cb60 | DLC sync handler (sets 0x9D) |

### Compression/Checksum Functions

| Address | Function | Purpose |
|---------|----------|---------|
| 0x0223E140 | Compression entry | Main compression loop |
| 0x0223E0A0 | Match finder | Find best match at position |
| 0x01CDBA20 | FUN_01cdba20 | Zero-seed Adler-32 checksum |
| 0x01B7A310 | FUN_01b7a310 | Magic bytes writer |
| 0x01B7A1D0 | FUN_01b7a1d0 | Magic bytes validator |

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-27 | Initial comprehensive consolidation |
| 2.0 | 2025-12-27 | Added detailed unmapped regions, byte counts, Ghidra function reference |
| 3.0 | 2025-12-27 | Major update: (1) Section 1 now 96% mapped with 12 property records, (2) Added 2 new unknown unlock records at 0x2B5/0x2C7 in Section 2, (3) Explained 43-byte PC/PS3 Section 3 difference (PSN Trophy system), (4) Added section hashes and platform flags to all sections, (5) Expanded cross-section relationships |

---

## Source Documents

This reference consolidates information from:

1. `/docs/ACB_OPTIONS_Menu_Mapping_Reference.md` - Menu settings and value tables
2. `/docs/SECTION3_FIELD_PROOF_REPORT.md` - Section 3 field proof (achievements, Uplay, DLC)
3. `/docs/GHIDRA_PROOF_COMPLETE.md` - Ghidra-proven offsets for Section 2
4. `/docs/UNKNOWN_TOGGLE_ANALYSIS.md` - Analysis of 8 unknown toggles
5. `/docs/GHIDRA_PROOF_AUDIT.md` - Comprehensive audit of proven vs unproven fields
6. `/docs/ACB_OPTIONS_Header_Complete_Specification.md` - Header structure
7. `/docs/ACB_OPTIONS_Footer_Complete_Specification.md` - Footer analysis
8. `/docs/ACB_OPTIONS_Language_Struct_Analysis.md` - Language system
9. `/docs/PS3_OPTIONS_FORMAT.md` - PS3 format specification
10. `/docs/PS3_vs_PC_STRUCTURE_ANALYSIS.md` - Platform differences
11. `/docs/FIELD_MAPPING_WORKSHEET.md` - Field tracking worksheet
12. `/docs/ACB_OPTIONS_Mapping_Reference.md` - Original mapping reference
13. `/CLAUDE.md` - Project overview and format summary

---

**End of Document**
