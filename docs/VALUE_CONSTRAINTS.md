# AC Brotherhood OPTIONS - Value Constraints and Validation Rules

**Document Version:** 1.0
**Date:** 2025-12-27
**Status:** Comprehensive Value Constraints Reference

This document specifies valid value ranges, defaults, and validation behaviors for all editable fields in the AC Brotherhood OPTIONS file format.

---

## Table of Contents

1. [Overview](#overview)
2. [Audio Settings](#audio-settings)
3. [Control Settings](#control-settings)
4. [Display Settings](#display-settings)
5. [Language Settings](#language-settings)
6. [HUD Settings](#hud-settings)
7. [Unlock and Progress Fields](#unlock-and-progress-fields)
8. [Platform-Specific Fields](#platform-specific-fields)
9. [Enum Value Reference](#enum-value-reference)
10. [Validation Behavior Summary](#validation-behavior-summary)
11. [Default Values Summary](#default-values-summary)

---

## Overview

### Validation Methodology

Value constraints were determined through:

1. **Ghidra Decompilation:** Analysis of validation code in parser/writer functions
2. **Differential Analysis:** Comparison of 24 OPTIONS files with varying settings
3. **In-Game Testing:** Observation of menu slider/toggle ranges
4. **Float Pattern Analysis:** IEEE 754 float value tables extracted from memory

### Confidence Levels

| Level | Symbol | Description |
|-------|--------|-------------|
| **PROVEN** | [P] | Confirmed via Ghidra decompilation or exhaustive testing |
| **HIGH** | [H] | Strong evidence from differential analysis |
| **MEDIUM** | [M] | Inferred from patterns or partial evidence |
| **LOW** | [L] | Speculation based on field type |

---

## Audio Settings

### Volume Fields

All volume fields use IEEE 754 float format with a logarithmic decibel (dB) scale.

| Field | Section | Offset | Type | Range | Default | Conf |
|-------|---------|--------|------|-------|---------|------|
| Music Volume | S2 | 0xC0-0xC3 | float32 | 0.0 to -96.0 dB | -6.020 dB (Level 5) | [P] |
| Voice Volume | S2 | 0xD5-0xD8 | float32 | 0.0 to -96.0 dB | -6.020 dB (Level 5) | [P] |
| SFX Volume | S2 | 0xEA-0xED | float32 | 0.0 to -96.0 dB | -6.020 dB (Level 5) | [H] |

#### Volume Level Discrete Values (11 Levels)

The game uses 11 discrete volume levels corresponding to a non-linear logarithmic scale:

| UI Level | Slider | Hex Value (LE) | Float dB | Description |
|----------|--------|----------------|----------|-------------|
| 10 | Max | `0x00000000` | 0.0 | Maximum volume |
| 9 | | `0xBF6A4744` | -0.916 | |
| 8 | | `0xBFF816F0` | -1.938 | |
| 7 | | `0xC0464646` | -3.098 | |
| 6 | | `0xC08DFBB2` | -4.437 | |
| 5 | Default | `0xC0C0A8C0` | -6.020 | Factory default |
| 4 | | `0xC0FEAE7C` | -7.958 | |
| 3 | | `0xC1275239` | -10.457 | |
| 2 | | `0xC15FAB9E` | -13.979 | |
| 1 | | `0xC19FFFFF` | -19.999 | |
| 0 | Mute | `0xC2C00000` | -96.0 | Effective silence |

**Technical Notes:**
- dB scale follows industry standard: 0 dB = maximum, negative values = quieter
- -96 dB represents effective silence (16-bit audio floor)
- Steps are non-linear for perceptual consistency (Weber-Fechner law)
- Game validates values by clamping to nearest discrete level

**Validation Behavior:** Values outside the 11-level table are **clamped** to the nearest valid level. The game does not reject intermediate float values but rounds them during menu display.

**Ghidra Reference:** `FUN_00acf240` (Settings constructor)

### Vibration Toggle

| Field | Section | Offset | Type | Valid Values | Default | Conf |
|-------|---------|--------|------|--------------|---------|------|
| Vibration | S2 | 0xFF | bool | 0x00=Off, 0x01=On | 0x01 (On) | [P] |

---

## Control Settings

### Sensitivity Fields

| Field | Section | Offset | Type | Range | Default | Conf |
|-------|---------|--------|------|-------|---------|------|
| X Look Sensitivity | S2 | 0x111-0x114 | float32 | 0.5x to 2.0x | 1.0x (Level 5) | [H] |
| Y Look Sensitivity | S2 | 0x126-0x129 | float32 | 0.5x to 2.0x | 1.0x (Level 5) | [P] |

#### Sensitivity Level Discrete Values (10 Levels)

| UI Level | Hex Value (LE) | Multiplier | Description |
|----------|----------------|------------|-------------|
| 10 | `0x40000000` | 2.0x | Maximum |
| 9 | `0x3FE66666` | 1.8x | |
| 8 | `0x3FCCCCCD` | 1.6x | |
| 7 | `0x3FB33333` | 1.4x | |
| 6 | `0x3F99999A` | 1.2x | |
| 5 | `0x3F800000` | 1.0x | Default (baseline) |
| 4 | `0x3F4CCCCD` | 0.8x | |
| 3 | `0x3F333333` | 0.7x | |
| 2 | `0x3F19999A` | 0.6x | |
| 1 | `0x3F000000` | 0.5x | Minimum |

**Progression Pattern:**
- Levels 1-4: Increment by 0.1x (0.5, 0.6, 0.7, 0.8)
- Level 5: 1.0x baseline (0.2 jump from 0.8)
- Levels 6-10: Increment by 0.2x (1.2, 1.4, 1.6, 1.8, 2.0)

**Validation Behavior:** Similar to volume - values are **clamped** to nearest discrete level.

**Ghidra Reference:** `FUN_00417fc0` (X sensitivity), 10+ instruction references (Y sensitivity)

### Inversion Toggles

| Field | Section | Offset | Type | Valid Values | Default | Conf |
|-------|---------|--------|------|--------------|---------|------|
| 3rd Person Invert X | S2 | 0x13B | bool | 0x00=Normal, 0x01=Inverted | 0x00 | [H] |
| 3rd Person Invert Y | S2 | 0x14D | bool | 0x00=Normal, 0x01=Inverted | 0x00 | [P] |
| 1st Person Invert X | S2 | 0x15F | bool | 0x00=Normal, 0x01=Inverted | 0x00 | [M] |
| 1st Person Invert Y | S2 | 0x171 | bool | 0x00=Normal, 0x01=Inverted | 0x00 | [P] |
| Flying Machine Invert | S2 | 0x1B9 | bool | 0x00=Normal, 0x01=Inverted | 0x00 | [P] |
| Cannon Invert X | S2 | 0x1CB | bool | 0x00=Normal, 0x01=Inverted | 0x00 | [P] |
| Cannon Invert Y | S2 | 0x1DD | bool | 0x00=Normal, 0x01=Inverted | 0x00 | [P] |

**Validation Behavior:** Boolean fields accept only 0x00 or 0x01. Non-zero values are typically treated as "true" (0x01).

**Ghidra Reference:** `FUN_00a82210` (3P Invert X), `FUN_00acf240` (Cannon Invert Y)

---

## Display Settings

### Brightness

| Field | Section | Offset | Type | Range | Default | Conf |
|-------|---------|--------|------|-------|---------|------|
| Brightness | S2 | 0x195 | uint8 | 1-16 (0x01-0x10) | 8 (0x08) | [P] |

**Discrete Values:** 16 levels (1 through 16)

| Value | Hex | Description |
|-------|-----|-------------|
| 1 | 0x01 | Darkest |
| 8 | 0x08 | Default (mid-point) |
| 16 | 0x10 | Brightest |

**Validation Behavior:** Values outside 1-16 range are **clamped**:
- Values < 1 are set to 1
- Values > 16 are set to 16
- Value 0 is treated as invalid and likely clamped to 1

**Ghidra Reference:** `FUN_00acf240` (Settings constructor)

### Action Camera Frequency

| Field | Section | Offset | Type | Range | Default | Conf |
|-------|---------|--------|------|-------|---------|------|
| Action Camera Frequency | S2 | 0x183 | uint8 | 0-3 | 1 or 2 | [M] |

**Enum Values:**

| Value | Hex | Meaning |
|-------|-----|---------|
| 0 | 0x00 | Off/Never |
| 1 | 0x01 | Low frequency |
| 2 | 0x02 | Medium frequency |
| 3 | 0x03 | High frequency |

**Validation Behavior:** Values > 3 are likely **clamped** to 3.

### Blood Toggle

| Field | Section | Offset | Type | Valid Values | Default | Conf |
|-------|---------|--------|------|--------------|---------|------|
| Blood Toggle | S2 | 0x1A7 | bool | 0x00=Off, 0x01=On | 0x01 (On) | [P] |

**Ghidra Reference:** 5 function references

### Subtitles Toggle

| Field | Section | Offset | Type | Valid Values | Default | Conf |
|-------|---------|--------|------|--------------|---------|------|
| Subtitles | S2 | 0x63 | bool | 0x00=Off, 0x01=On | 0x00 (Off) | [P] |

**Ghidra Reference:** `FUN_004391f0`, `FUN_00439250`

---

## Language Settings

### Language Index Fields

| Field | Section | Offset | Type | Range | Default | Conf |
|-------|---------|--------|------|-------|---------|------|
| Audio Language Index | S2 | 0x8E-0x91 | uint32 | 1-20 | System default | [H] |
| Subtitle Language Index | S2 | 0xA7-0xAA | uint32 | 1-20 | System default | [M] |

### Language Hash Fields

| Field | Section | Offset | Type | Valid Values | Conf |
|-------|---------|--------|------|--------------|------|
| Audio Language Hash | S2 | 0x92-0x95 | hash32 | See language table | [H] |
| Subtitle Language Hash | S2 | 0xAB-0xAE | hash32 | See language table | [M] |

**Language Index to Hash Mapping:**

| Index | Language | Hash (LE) |
|-------|----------|-----------|
| 1 | English | 0x50CC97B5 |
| 2 | French | 0x3C0FCC90 |
| 3 | Spanish | 0x48576081 |
| 4 | Polish | 0x4375357B |
| 5 | German | 0x314E426F |
| 6 | (Reserved) | 0x87D7B2A1 |
| 7 | Hungarian | 0xC6233139 |
| 8 | Italian | 0x2BF6FC7A |
| 9 | Japanese | 0xB1E049F8 |
| 10 | Czech | 0x2C6A3130 |
| 11 | Korean | 0x022FCB0D |
| 12 | Russian | 0x972964C0 |
| 13 | Dutch | 0xDBCD3431 |
| 14 | Danish | 0xCE0B031C |
| 15 | Norwegian | 0x69AD901C |
| 16 | Swedish | 0xCF6F169D |
| 17 | Portuguese | 0x12410E3F |
| 18 | Turkish | 0xCDA3D2DC |
| 19 | Simplified Chinese | 0x43CD0944 |
| 20 | Traditional Chinese | 0xCF38DA87 |

**Validation Behavior:**
- Index values outside 1-20 may cause fallback to English (index 1)
- Hash values must match index; mismatched pairs trigger hash-based lookup
- Invalid hashes fall back to index, then to default language

**Ghidra Reference:** Language table at 0x0298a780, lookup functions `FUN_01b82560` (by index), `FUN_01b82590` (by hash)

### Default Language Flag

| Field | Section | Offset | Type | Valid Values | Conf |
|-------|---------|--------|------|--------------|------|
| Default Language Flag | S2 | 0x75 | bool | 0x00/0x01 | [H] |

---

## HUD Settings

All HUD toggles follow the same boolean pattern:

| Field | Section | Offset | Type | Valid Values | Default | Conf |
|-------|---------|--------|------|--------------|---------|------|
| Health Meter | S2 | 0x1EF | bool | 0x00=Off, 0x01=On | 0x01 | [P] |
| Controls | S2 | 0x201 | bool | 0x00=Off, 0x01=On | 0x01 | [M] |
| Updates | S2 | 0x213 | bool | 0x00=Off, 0x01=On | 0x01 | [M] |
| Weapon | S2 | 0x225 | bool | 0x00=Off, 0x01=On | 0x01 | [P] |
| Mini-Map | S2 | 0x237 | bool | 0x00=Off, 0x01=On | 0x01 | [P] |
| Money | S2 | 0x249 | bool | 0x00=Off, 0x01=On | 0x01 | [P] |
| SSI | S2 | 0x26D | bool | 0x00=Off, 0x01=On | 0x01 | [P] |
| Tutorial | S2 | 0x27F | bool | 0x00=Off, 0x01=On | 0x01 | [M] |

**Structure Note:** HUD toggles use 18-byte record spacing with the boolean value at offset +0x00 of each record.

**Ghidra Reference:** `FUN_00acf240` (Mini-Map), various other functions

---

## Unlock and Progress Fields

### Costume Bitfield

| Field | Section | Offset | Type | Valid Range | Default | Conf |
|-------|---------|--------|------|-------------|---------|------|
| Costume Bitfield | S2 | 0x369 | bitfield | 0x00-0x3F | 0x00 | [P] |

**Bit Definitions:**

| Bit | Mask | Costume | Source |
|-----|------|---------|--------|
| 0 | 0x01 | Florentine Noble Attire | Uplay (20 pts) |
| 1 | 0x02 | Armor of Altair | Uplay (20 pts) |
| 2 | 0x04 | Altair's Robes | Uplay (20 pts) |
| 3 | 0x08 | Drachen Armor | Preorder bonus |
| 4 | 0x10 | Desmond | In-game unlock |
| 5 | 0x20 | Raiden | In-game unlock |
| 6-7 | 0xC0 | (Unused) | - |

**Valid Combinations:**
- 0x00: No costumes unlocked
- 0x3F: All 6 costumes unlocked
- Any combination of bits 0-5

**Validation Behavior:** Bits 6-7 are ignored; values with these bits set are masked to 0x3F.

### Unlock Record Flags

| Field | Section | Offset | Type | Valid Values | Default | Conf |
|-------|---------|--------|------|--------------|---------|------|
| Templar Lair 1 (Trajan's Market) | S2 | 0x291 | bool | 0x00/0x01 | 0x00 | [P] |
| Templar Lair 2 (Aqueduct) | S2 | 0x2A3 | bool | 0x00/0x01 | 0x00 | [P] |
| Unknown Unlock #1 | S2 | 0x2B5 | bool | 0x00/0x01 | 0x00 | [M] |
| Unknown Unlock #2 | S2 | 0x2C7 | bool | 0x00/0x01 | 0x00 | [M] |
| Possibly Uplay (unknown) | S2 | 0x2D9 | bool | 0x00/0x01 | 0x00 | [M] |
| Possibly Uplay (unknown) | S2 | 0x2EB | bool | 0x00/0x01 | 0x00 | [M] |
| Possibly Uplay (unknown) | S2 | 0x2FD | bool | 0x00/0x01 | 0x00 | [M] |
| Possibly Uplay (unknown) | S2 | 0x30F | bool | 0x00/0x01 | 0x00 | [M] |

### DLC/Update Flags

| Field | Section | Offset | Type | Valid Values | Default | Conf |
|-------|---------|--------|------|--------------|---------|------|
| Animus Project Update 1.0 | S2 | 0x516 | bool | 0x00/0x01 | 0x00 | [M] |
| Animus Project Update 2.0 | S2 | 0x517 | bool | 0x00/0x01 | 0x00 | [M] |
| Animus Project Update 3.0 | S2 | 0x518 | bool | 0x00/0x01 | 0x00 | [M] |
| Da Vinci Disappearance DLC | S2 | 0x519 | bool | 0x00/0x01 | 0x00 | [M] |

### Achievement Bitfield (PC Only)

| Field | Section | Offset | Type | Valid Range | Default | Conf |
|-------|---------|--------|------|-------------|---------|------|
| Achievement Bitfield | S3 | 0x84-0x8A | 7 bytes | See below | All zeros | [P] |

**Valid Values:**
- 53 achievement bits (bits 0-52)
- Bits 53-55 (byte 0x8A, bits 5-7) must be 0
- Maximum valid value: `FF FF FF FF FF FF 1F`

**Achievement Categories by Byte:**

| Offset | Bits Used | Category |
|--------|-----------|----------|
| 0x84 | 8/8 | Story Progression (1-8) |
| 0x85 | 8/8 | Story + Shrines (9-16) |
| 0x86 | 8/8 | Shrines + Da Vinci Machines (17-24) |
| 0x87 | 8/8 | Side Activities (25-32) |
| 0x88 | 8/8 | Miscellaneous (33-40) |
| 0x89 | 8/8 | Multiplayer (41-48) |
| 0x8A | 5/8 | MP + DLC (49-53), bits 5-7 unused |

### Uplay Gun Capacity Upgrade (30 Upoints)

| Field | Section | Offset | Type | Valid Values | Default | Conf |
|-------|---------|--------|------|--------------|---------|------|
| Gun Capacity Upgrade | S3 | 0x4E | bool | 0x00/0x01 | 0x00 | [P] |

**Note:** This is the ONLY Uplay equipment upgrade stored in Section 3. The upgrade increases Ezio's pistol ammunition capacity. Unlike costume Uplay rewards (which are stored in Section 2's bitfield at 0x369), this gameplay upgrade is tracked separately in the game progress section.

### DLC Sync Flag

| Field | Section | Offset (PC) | Offset (PS3) | Type | Valid Values | Default | Conf |
|-------|---------|-------------|--------------|------|--------------|---------|------|
| DLC Sync Flag | S3 | 0x9D | 0x5A | bool | 0x00/0x01 | 0x00 | [P] |

**Ghidra Reference:** `FUN_0084cb60` (DLC sync handler)

### Profile State Flag

| Field | Section | Offset | Type | Valid Values | Default | Conf |
|-------|---------|--------|------|--------------|---------|------|
| Profile State Flag | S1 | 0x51 | uint8 | 0x02, 0x06 | 0x02 | [H] |

**Known States:**
- 0x02: Base game state
- 0x06: All rewards unlocked state

**Note:** Other values may exist but have not been observed in 24-file analysis.

---

## Platform-Specific Fields

### Platform Flags

| Field | Section | Offset | Type | Valid Values | Conf |
|-------|---------|--------|------|--------------|------|
| Platform Flags | All | 0x0E-0x0F | uint16 | PC=0x050C, PS3=0x0508 | [H] |

**Validation Behavior:** Must match across all sections within a file. Mismatched platform flags may cause load failure.

### PS3-Specific Toggles

| Field | Section | Offset | Type | Valid Values | Conf |
|-------|---------|--------|------|--------------|------|
| PS3 Toggle A | S2 | 0x4A5 | bool | 0x00/0x01 | [L] |
| PS3 Toggle B | S2 | 0x4B7 | bool | 0x00/0x01 | [L] |
| PS3 Toggle C | S2 | 0x4DB | bool | 0x00/0x01 | [L] |
| PS3 Toggle D | S2 | 0x4ED | bool | 0x00/0x01 | [L] |
| PS3 Toggle E | S2 | 0x4FF | bool | 0x00/0x01 | [L] |
| Platform ID | S2 | 0x500 | uint8 | PC=0x16, PS3=0x12 | [M] |

---

## Enum Value Reference

### Complete Enum Tables

#### Action Camera Frequency Enum

```c
typedef enum {
    ACTION_CAM_OFF     = 0,  /* Never trigger action camera */
    ACTION_CAM_LOW     = 1,  /* Low frequency */
    ACTION_CAM_MEDIUM  = 2,  /* Medium frequency */
    ACTION_CAM_HIGH    = 3   /* High frequency */
} ActionCameraFrequency;
```

#### Volume Level Enum

```c
typedef enum {
    VOLUME_MUTE    = 0,   /* -96.0 dB */
    VOLUME_LVL_1   = 1,   /* -19.999 dB */
    VOLUME_LVL_2   = 2,   /* -13.979 dB */
    VOLUME_LVL_3   = 3,   /* -10.457 dB */
    VOLUME_LVL_4   = 4,   /* -7.958 dB */
    VOLUME_DEFAULT = 5,   /* -6.020 dB */
    VOLUME_LVL_6   = 6,   /* -4.437 dB */
    VOLUME_LVL_7   = 7,   /* -3.098 dB */
    VOLUME_LVL_8   = 8,   /* -1.938 dB */
    VOLUME_LVL_9   = 9,   /* -0.916 dB */
    VOLUME_MAX     = 10   /* 0.0 dB */
} VolumeLevel;
```

#### Sensitivity Level Enum

```c
typedef enum {
    SENS_MIN     = 1,   /* 0.5x */
    SENS_LVL_2   = 2,   /* 0.6x */
    SENS_LVL_3   = 3,   /* 0.7x */
    SENS_LVL_4   = 4,   /* 0.8x */
    SENS_DEFAULT = 5,   /* 1.0x */
    SENS_LVL_6   = 6,   /* 1.2x */
    SENS_LVL_7   = 7,   /* 1.4x */
    SENS_LVL_8   = 8,   /* 1.6x */
    SENS_LVL_9   = 9,   /* 1.8x */
    SENS_MAX     = 10   /* 2.0x */
} SensitivityLevel;
```

#### Language Index Enum

```c
typedef enum {
    LANG_ENGLISH              = 1,
    LANG_FRENCH               = 2,
    LANG_SPANISH              = 3,
    LANG_POLISH               = 4,
    LANG_GERMAN               = 5,
    LANG_RESERVED             = 6,   /* Unused */
    LANG_HUNGARIAN            = 7,
    LANG_ITALIAN              = 8,
    LANG_JAPANESE             = 9,
    LANG_CZECH                = 10,
    LANG_KOREAN               = 11,
    LANG_RUSSIAN              = 12,
    LANG_DUTCH                = 13,
    LANG_DANISH               = 14,
    LANG_NORWEGIAN            = 15,
    LANG_SWEDISH              = 16,
    LANG_PORTUGUESE           = 17,
    LANG_TURKISH              = 18,
    LANG_SIMPLIFIED_CHINESE   = 19,
    LANG_TRADITIONAL_CHINESE  = 20
} LanguageIndex;
```

#### Profile State Enum

```c
typedef enum {
    PROFILE_BASE        = 0x02,  /* Base game state */
    PROFILE_ALL_REWARDS = 0x06   /* All rewards unlocked */
} ProfileState;
```

---

## Validation Behavior Summary

### General Validation Behaviors

| Behavior | Description | Fields Affected |
|----------|-------------|-----------------|
| **Clamp** | Values outside range are adjusted to nearest valid value | Volume, Sensitivity, Brightness |
| **Nearest Discrete** | Float values rounded to nearest discrete level | Volume, Sensitivity |
| **Boolean Normalize** | Non-zero values treated as 0x01 | All boolean fields |
| **Mask** | Invalid bits are masked off | Costume bitfield, Achievement bitfield |
| **Fallback** | Invalid values trigger fallback to default | Language index/hash |
| **Reject** | Invalid values cause load failure | Platform flags mismatch |

### Validation Function References

| Function | Address | Purpose |
|----------|---------|---------|
| `FUN_00acf240` | 0x00acf240 | Settings constructor - initializes defaults and validates ranges |
| `FUN_0046d430` | 0x0046d430 | Section 1 reader - validates Field1=0x16, Field2=0xFEDBAC |
| `FUN_01712db0` | 0x01712db0 | Section 2 reader - validates 0x11FACE11 marker |
| `FUN_017109e0` | 0x017109e0 | Section 3 reader - validates 0x21EFFE22 marker |
| `FUN_01b7a1d0` | 0x01b7a1d0 | Magic bytes validator - checks 0x57FBAA33, 0x1004FA99 |
| `FUN_01cdba20` | 0x01cdba20 | Checksum validator - zero-seed Adler-32 |

---

## Default Values Summary

### Section 2 Default Values (New OPTIONS File)

| Category | Field | Default Value | Notes |
|----------|-------|---------------|-------|
| **Audio** | Music Volume | -6.020 dB (Level 5) | Mid-range |
| | Voice Volume | -6.020 dB (Level 5) | Mid-range |
| | SFX Volume | -6.020 dB (Level 5) | Mid-range |
| | Vibration | On (0x01) | Enabled by default |
| **Controls** | X Sensitivity | 1.0x (Level 5) | Baseline |
| | Y Sensitivity | 1.0x (Level 5) | Baseline |
| | All Inversion | Normal (0x00) | Not inverted |
| **Display** | Brightness | 8 | Mid-range (1-16 scale) |
| | Action Camera | 1 or 2 | Low/Medium |
| | Blood | On (0x01) | Enabled |
| | Subtitles | Off (0x00) | Disabled |
| **Language** | Audio/Subtitle | System language | From Windows Registry |
| **HUD** | All toggles | On (0x01) | All HUD elements visible |
| **Unlocks** | All unlocks | Locked (0x00) | Nothing unlocked |
| | Costumes | None (0x00) | No costumes |
| **DLC** | All flags | Off (0x00) | No DLC installed |

### Section 3 Default Values

| Field | Default Value | Notes |
|-------|---------------|-------|
| Uplay Gun Upgrade | 0x00 | Not redeemed |
| DLC Sync Flag | 0x00 | Not synced |
| Achievements (PC) | All zeros | No achievements |

### Section 1 Default Values

| Field | Default Value | Notes |
|-------|---------------|-------|
| Profile State Flag | 0x02 | Base state |

---

## Cross-Field Constraints

### Correlated Fields

Certain fields must be consistent with each other:

1. **Costume Bitfield (0x369) controls costume unlocks:**
   - Bit 0 (0x01) = Florentine Noble Attire
   - Bit 1 (0x02) = Armor of Altair
   - Bit 2 (0x04) = Altair's Robes
   - Note: The unlock records at 0x2D9, 0x2EB, 0x2FD, 0x30F are Uplay-related but their specific purpose is UNKNOWN. They flip in Uplay test files but do NOT directly control costume unlocks.

2. **Profile State vs Progress State:**
   - If S1:0x51 = 0x06 (All rewards), then:
     - S3:0x4E (Gun Upgrade) should = 0x01
     - S3:0x9D/0x5A (DLC Sync) should = 0x01
     - S3:0x84-0x8A (Achievements, PC) should = FF FF FF FF FF FF 1F

3. **Language Index vs Hash:**
   - Audio language index at 0x8E must match hash at 0x92
   - Subtitle language index at 0xA7 must match hash at 0xAB

4. **Platform Consistency:**
   - All sections must have matching platform flags (0x0E-0x0F)
   - Platform ID at 0x500 must match platform flags

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-27 | Initial comprehensive value constraints documentation |

---

## References

- `/docs/OPTIONS_FIELD_REFERENCE.md` - Complete field offset reference
- `/docs/SECTION_DATA_STRUCTURES.md` - C structure definitions
- `/docs/ACB_OPTIONS_Menu_Mapping_Reference.md` - Menu setting mappings
- `/docs/ACB_OPTIONS_Language_Struct_Analysis.md` - Language system analysis
- `/docs/CROSS_SECTION_RELATIONSHIPS.md` - Field correlation documentation
- `/docs/ACB_Functions_Reference.md` - Ghidra function references

---

**End of Document**
