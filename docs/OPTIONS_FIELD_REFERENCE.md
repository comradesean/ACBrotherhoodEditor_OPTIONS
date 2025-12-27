# AC Brotherhood OPTIONS File - Complete Field Reference

**Last Updated:** 2025-12-27
**Document Version:** 2.0
**Status:** Authoritative Reference (Consolidated from 13 Source Documents)

---

## Document Info

### Coverage Summary

| Section | Platform | Total Size | Bytes Mapped | Coverage |
|---------|----------|------------|--------------|----------|
| Section 1 | PC | 283 bytes | 19 bytes | 7% |
| Section 1 | PS3 | 289 bytes | 19 bytes | 7% |
| Section 2 | PC | 1310 bytes | 176 bytes | 13% |
| Section 2 | PS3 | 1306 bytes | 176 bytes | 13% |
| Section 3 | PC | 162 bytes | 25 bytes | 15% |
| Section 3 | PS3 | 119 bytes | 25 bytes | 21% |
| Section 4 | PS3 only | 1903 bytes | 16 bytes | 1% |

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

### Known Fields

| Offset | Size | Type | Field Name | Value Range | Conf | Evidence |
|--------|------|------|------------|-------------|------|----------|
| 0x00-0x09 | 10 | padding | Zero Padding | Always 0x00 | [P] | Structure analysis |
| 0x51 | 1 | byte | Unknown System Flag | 0x02-0x06 | [M] | Observed in diffs |
| 0xA6-0xAD | 8 | string | "Options" ASCII | Fixed | [P] | Hex dump |

### Unknown Regions (Section 1)

| Offset Range | Size | Notes |
|--------------|------|-------|
| 0x0A-0x50 | 71 bytes | Likely property entries, platform identification |
| 0x52-0xA5 | 84 bytes | Unknown structure |
| 0xAE-0x11A | 109 bytes | Remaining section data |

**Mapped:** 19 bytes | **Unmapped:** 264 bytes | **Coverage:** 7%

**Note:** Section 1 content is largely unmapped. Ghidra analysis shows this section is handled by `FUN_0046d7b0` and `FUN_0046d430`.

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
| 0x2D9 | Uplay: Florentine Noble Attire | 0x0021D9D0 | [H] | Differential + Context |
| 0x2EB | Uplay: Armor of Altair | 0x0036A2C4 | [H] | Differential + Context |
| 0x2FD | Uplay: Altair's Robes | 0x0052C3A9 | [H] | Differential + Context |
| 0x30F | Uplay: Hellequin MP Character | 0x000E8D04 | [H] | Differential + Context |

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

### Unmapped Regions (Section 2)

| Offset Range | Size | Notes |
|--------------|------|-------|
| 0x10-0x13 | 4 bytes | Between platform flags and type |
| 0x18-0x62 | 75 bytes | Pre-subtitle region |
| 0x64-0x74 | 17 bytes | Between subtitle toggle and language flag |
| 0x76-0x8D | 24 bytes | Between language flag and audio hash |
| 0x96-0xA6 | 17 bytes | Between audio and subtitle language |
| 0xAF-0xBF | 17 bytes | Between language and audio volume |
| 0xC4-0xD4 | 17 bytes | Between music and voice volume |
| 0xD9-0xE9 | 17 bytes | Between voice and SFX volume |
| 0xEE-0xFE | 17 bytes | Between SFX and vibration |
| 0x100-0x110 | 17 bytes | Pre-sensitivity region |
| 0x115-0x125 | 17 bytes | Between X and Y sensitivity |
| 0x12A-0x13A | 17 bytes | Pre-3P invert X region |
| 0x13C-0x14C | 17 bytes | Between 3P invert X and Y |
| 0x14E-0x15E | 17 bytes | Between 3P invert Y and 1P invert X |
| 0x160-0x170 | 17 bytes | Between 1P invert X and Y |
| 0x172-0x182 | 17 bytes | Pre-action camera region |
| 0x184-0x194 | 17 bytes | Between action camera and brightness |
| 0x196-0x1A6 | 17 bytes | Between brightness and blood |
| 0x1A8-0x1B8 | 17 bytes | Between blood and flying machine |
| 0x1BA-0x1CA | 17 bytes | Between flying machine and cannon X |
| 0x1CC-0x1DC | 17 bytes | Between cannon X and Y |
| 0x1DE-0x1EE | 17 bytes | Pre-HUD region |
| 0x280-0x290 | 17 bytes | Between tutorial and templar lairs |
| 0x2A4-0x2D8 | 53 bytes | Between templar lair 2 and uplay reward 1 |
| 0x321-0x368 | 72 bytes | Between hellequin and costume bitfield |
| 0x36A-0x515 | 428 bytes | Post-costume, pre-DLC flags |
| 0x51A-0x51D | 4 bytes | Post-DLC flags padding |

**Mapped:** 176 bytes | **Unmapped:** 1134 bytes | **Coverage:** 13%

---

## Section 3: Game Progress

**PC Size:** 162 bytes | **PS3 Size:** 119 bytes
**Class Name:** `AssassinSingleProfileData` (found at string address 0x0253ddec)
**Section Marker:** Field3 = 0x21EFFE22

### Known Fields

| Offset | Size | Type | Field Name | Value Range | Conf | Evidence |
|--------|------|------|------------|-------------|------|----------|
| 0x00-0x09 | 10 | padding | Zero Padding | 0x00 | [P] | Structure analysis |
| 0x4D | 1 | marker | Structure Marker | 0x0B | [P] | Constant value |
| 0x4E | 1 | bool | Uplay Gun Capacity Upgrade | 0=No, 1=Yes | [P] | 24-file differential |
| 0x4F | 1 | marker | Structure Marker | 0x0E | [P] | Constant value |
| 0x80-0x83 | 4 | header | Achievement Header | 0x00 09 00 0B | [P] | Constant; 0x0B is structure type marker, 0x09 may indicate following data size |
| 0x84-0x8A | 7 | bitfield | Achievement Bitfield | 53 bits used | [P] | Differential + Bit count |
| 0x8B | 1 | padding | Reserved | 0x00 | [P] | Structure |
| 0x8C-0x8F | 4 | marker | Structure Marker | 0x0E 00 00 00 | [P] | Constant |
| 0x90-0x93 | 4 | hash | Hash Constant | 0x6F88B05B | [P] | Constant |
| 0x9C | 1 | marker | Structure Marker | 0x0B | [P] | Constant |
| 0x9D | 1 | bool | DLC Sync Flag | 0=No, 1=Yes | [P] | Ghidra: FUN_0084cb60 |
| 0x9E-0x9F | 2 | padding | Reserved | 0x00 | [P] | Structure |

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
| 0x0A-0x4C | 67 bytes | Pre-Uplay reward region |
| 0x50-0x7F | 48 bytes | Between Uplay flag and achievement header |
| 0x94-0x9B | 8 bytes | Between hash and DLC sync region |
| 0xA0-0xA1 | 2 bytes (PC) | Post-DLC sync (PC has 43 more bytes than PS3) |

**Mapped:** 25 bytes | **Unmapped:** 137 bytes (PC) / 94 bytes (PS3) | **Coverage:** 15% (PC) / 21% (PS3)

---

## Section 4: PS3 Controller Mappings (PS3 Only)

**Size:** 1903 bytes
**Section Marker:** Field2 = 0x00000004, Field3 = 0x00000007

Section 4 is PS3-exclusive and contains DualShock 3 controller mapping data.

### Structure Overview

| Component | Offset | Size | Description |
|-----------|--------|------|-------------|
| Header | 0x00-0x60 | 97 bytes | General controller settings |
| Records | 0x61-0x5EB | 1445 bytes | 17 button mapping records (85 bytes each) |
| Trailer | 0x5EC-0x76E | 361 bytes | Additional settings + padding |

### Button Mapping Record Structure (85 bytes)

| Record Offset | Size | Description |
|---------------|------|-------------|
| +0x00 | 5 | Signature: `A8 CF 5F F9 43` |
| +0x05 | 4 | Value 1: `0x0000003B` (constant) |
| +0x09 | 4 | Value 2: `0x00000011` (constant) |
| +0x0D | 4 | Controller ID: `C0 B2 57 81` |
| +0x11 | 10 | Reserved (zeros) |
| +0x1B | 2 | Field marker: `06 00` |
| +0x1D | 1 | Button/Action ID |
| +0x1E | 67 | Additional mapping data |

### Known Button/Action IDs

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
| 31 | 0x1F | L3 (Left Stick Click) |
| 32 | 0x20 | R3 (Right Stick Click) |
| 34 | 0x22 | PS Button |

**Mapped:** 16 bytes (button IDs) | **Unmapped:** 1887 bytes | **Coverage:** 1%

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

## Cross-Reference Notes

### Section 2 Uplay Rewards -> Section 3 Uplay Flag

- Section 2 unlock records at 0x2D9, 0x2EB, 0x2FD, 0x30F track individual Uplay rewards
- Section 3 offset 0x4E (Gun Capacity Upgrade) is the 30-point Uplay reward
- When all Uplay rewards are unlocked, Section 3 offset 0x9D (DLC Sync Flag) is also set

### Section 2 Costume Bitfield -> Uplay Costumes

- Costume bitfield at 0x369 includes Uplay-unlocked costumes
- Bit 0 (Florentine Noble Attire) corresponds to 0x2D9 unlock
- Bit 1 (Armor of Altair) corresponds to 0x2EB unlock
- Bit 2 (Altair's Robes) corresponds to 0x2FD unlock

### 24-File Validation (Section 3)

All 24 reference OPTIONS files show consistent behavior:
- **21 files:** 0x4E=0x00, 0x84-0x8A=all zeros, 0x9D=0x00 (Base state)
- **3 files:** 0x4E=0x01, 0x84-0x8A=all achievements, 0x9D=0x01 (All rewards state)

This perfect binary correlation proves these three fields are part of the same "rewards/progress unlocked" system.

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
