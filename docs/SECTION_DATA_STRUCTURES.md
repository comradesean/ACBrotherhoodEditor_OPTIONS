# AC Brotherhood OPTIONS - Section Data Structures

**Document Version:** 1.2
**Date:** 2025-12-27
**Status:** Complete C Structure Definitions (Phase 1 + Phase 2 Updates)

This document provides complete C structure definitions for all decompressed section data in the AC Brotherhood OPTIONS file format.

---

## Common Types

```c
#include <stdint.h>
#include <stdbool.h>

/* Boolean type - single byte */
typedef uint8_t OPTIONS_Bool;  /* 0x00 = False, 0x01 = True */

/* 4-byte hash type - little-endian */
typedef uint32_t OPTIONS_Hash;

/* Float type - IEEE 754, little-endian */
typedef float OPTIONS_Float;
```

---

## Section 1: System/Profile Data

**Uncompressed Size:** 283 bytes (PC) / 289 bytes (PS3)

### Common Header Structure

All sections share a common header pattern at offset 0x00-0x17:

```c
/* Common Section Header - 24 bytes */
typedef struct {
    uint8_t      zero_padding[10];    /* 0x00-0x09: Always zeros */
    OPTIONS_Hash section_hash;        /* 0x0A-0x0D: Section type identifier */
    uint16_t     platform_flags;      /* 0x0E-0x0F: PC=0x050C, PS3=0x0508 */
    uint32_t     unknown;             /* 0x10-0x13: Variable */
    uint32_t     type_indicator;      /* 0x14-0x17: Usually 0x00010000 */
} SectionHeader_Common;
```

### Property Record Structure (18 bytes)

Section 1 uses 12 property records following the header:

```c
/* Property Record - 18 bytes */
typedef struct {
    uint32_t value;           /* +0x00: Property value (little-endian) */
    uint8_t  unknown1;        /* +0x04: Usually 0x00 */
    uint8_t  type_marker;     /* +0x05: 0x0B = property marker */
    uint32_t unknown2;        /* +0x06: Variable data */
    OPTIONS_Hash hash;        /* +0x0A: Content identifier hash */
    uint32_t padding;         /* +0x0E: Usually zeros */
} PropertyRecord;

_Static_assert(sizeof(PropertyRecord) == 18, "PropertyRecord must be 18 bytes");
```

### Complete Section 1 Structure

```c
/* Section 1: System/Profile Data - 283 bytes (PC) */
typedef struct {
    /* Common header */
    uint8_t      zero_padding[10];    /* 0x00-0x09 */
    OPTIONS_Hash section_hash;        /* 0x0A-0x0D: 0xBDBE3B52 */
    uint16_t     platform_flags;      /* 0x0E-0x0F: PC=0x050C */
    uint32_t     unknown1;            /* 0x10-0x13 */
    uint32_t     type_indicator;      /* 0x14-0x17: 0x00010000 */

    /* Property records (12 x 18 bytes = 216 bytes) */
    PropertyRecord records[12];       /* 0x18-0xF7 */

    /* Record 1 (0x18): value = 0x16 (self-ref to header Field0) */
    /* Record 2 (0x2A): value = 0xFEDBAC (self-ref to header Field1) */

    /* Profile state */
    uint8_t  reserved1[89];           /* 0xF8-0x50 (overlaps with records) */
    uint8_t  profile_state_flag;      /* 0x51: 0x02 (base) or 0x06 (all rewards) */
    uint8_t  reserved2[84];           /* 0x52-0xA5 */

    /* ASCII identifier */
    char     options_string[8];       /* 0xA6-0xAD: "Options\0" */

    /* Remaining data */
    uint8_t  trailing_data[109];      /* 0xAE-0x11A */
} Section1_SystemProfile;

/* PS3 Section 1 Prefix - 6 bytes at offset 0x00 before main structure */
typedef struct {
    uint8_t      marker;          /* 0x00: 0x01 - Version/type marker */
    OPTIONS_Hash section_hash;    /* 0x01-0x04: 0xBDBE3B52 (duplicate of main hash) */
    uint8_t      unknown;         /* 0x05: 0x03 - Unknown field */
} PS3_Section1_Prefix;

_Static_assert(sizeof(PS3_Section1_Prefix) == 6, "PS3_Section1_Prefix must be 6 bytes");

/* PS3 Section 1: 6-byte prefix + 283-byte main structure = 289 bytes total
 * After the prefix, PS3 data aligns perfectly with PC data.
 * The section hash appears twice: once in prefix (0x01) and again at main offset 0x0A.
 */
```

---

## Section 2: Game Settings

**Uncompressed Size:** 1310 bytes (PC) / 1306 bytes (PS3)

### Property Record Structure (18 bytes) - Phase 2 Discovery

Section 2 uses 18-byte property records for ALL settings. The "17-byte reserved" gaps between settings are actually the trailing portion of these records:

```c
/* Section 2 Property Record - 18 bytes
 * Each setting in Section 2 follows this structure.
 * The value byte is at the START, followed by type and hash.
 */
typedef struct {
    uint8_t      value;           /* +0x00: Setting value (bool, byte, or float LSB) */
    uint8_t      type_marker;     /* +0x01: 0x0E=standard, 0x11=alt, 0x15=special */
    uint8_t      padding[3];      /* +0x02-0x04: Always zeros */
    OPTIONS_Hash property_hash;   /* +0x05-0x08: Property identifier hash (LE) */
    uint8_t      zero_pad[8];     /* +0x09-0x10: Zero padding */
    uint8_t      next_marker;     /* +0x11: 0x0B = next record start marker */
} Section2_PropertyRecord;

_Static_assert(sizeof(Section2_PropertyRecord) == 18, "Section2_PropertyRecord must be 18 bytes");

/* Type Markers:
 * 0x0E (14): Standard property/setting (most common)
 * 0x11 (17): Alternative type (floats, nested structures)
 * 0x15 (21): Special records (language-related)
 * 0x17 (23): Unique structure (possibly keyboard bindings)
 */
```

### Known Property Hashes (Section 2)

| Offset | Hash | Purpose |
|--------|------|---------|
| 0x13B | 0xA15FACF2 | Invert 3P X axis |
| 0x14D | 0xC36B150F | Invert 3P Y axis |
| 0x15F | 0x9CCE0247 | Invert 1P X axis |
| 0x171 | 0x56932719 | Invert 1P Y axis |
| 0x183 | 0x962BD533 | Action Camera Frequency |
| 0x195 | 0x7ED0EABB | Brightness |
| 0x1A7 | 0xDE6CD4AB | Blood toggle |
| 0x1EF | 0x039BEE69 | HUD: Health Meter |
| 0x237 | 0x761E3CE0 | HUD: Mini-Map |
| 0x291 | 0x788F42CC | Templar Lair: Trajan Market |

### Unlock Record Structure (18 bytes)

```c
/* Unlock Record - 18 bytes (variant of Property Record for unlock tracking) */
typedef struct {
    uint8_t      marker;          /* +0x00: 0x0B (structure marker) */
    OPTIONS_Bool unlock_flag;     /* +0x01: 0x00=locked, 0x01=unlocked */
    uint8_t      type;            /* +0x02: Category (0x0E for rewards) */
    uint8_t      reserved[3];     /* +0x03-0x05: Zeros */
    uint8_t      hash_prefix;     /* +0x06: Encoding byte (0xCC, 0x8F, etc.) */
    OPTIONS_Hash content_hash;    /* +0x07-0x0A: Content identifier */
    uint8_t      padding[7];      /* +0x0B-0x11: Zeros */
} UnlockRecord;

_Static_assert(sizeof(UnlockRecord) == 18, "UnlockRecord must be 18 bytes");
```

### Costume Bitfield

```c
/* Costume Bitfield - 1 byte at offset 0x369 */
typedef struct {
    uint8_t florentine_noble : 1;  /* Bit 0 (0x01) - Uplay */
    uint8_t armor_of_altair  : 1;  /* Bit 1 (0x02) - Uplay */
    uint8_t altairs_robes    : 1;  /* Bit 2 (0x04) - Uplay */
    uint8_t drachen_armor    : 1;  /* Bit 3 (0x08) - Preorder */
    uint8_t desmond          : 1;  /* Bit 4 (0x10) - Unlockable */
    uint8_t raiden           : 1;  /* Bit 5 (0x20) - Unlockable */
    uint8_t unused           : 2;  /* Bits 6-7 */
} CostumeBitfield;

/* All costumes unlocked: 0x3F */
```

### Complete Section 2 Structure

```c
/* Section 2: Game Settings - 1310 bytes (PC) */
typedef struct {
    /* Common header (0x00-0x17) */
    uint8_t      zero_padding[10];        /* 0x00-0x09 */
    OPTIONS_Hash section_hash;            /* 0x0A-0x0D: 0x305AE1A8 */
    uint16_t     platform_flags;          /* 0x0E-0x0F: PC=0x050C */
    uint8_t      reserved1[4];            /* 0x10-0x13 */
    uint32_t     type_indicator;          /* 0x14-0x17: 0x00110000 */
    uint8_t      reserved2[75];           /* 0x18-0x62 */

    /* Display settings */
    OPTIONS_Bool subtitles_enabled;       /* 0x63 */
    uint8_t      reserved3[17];           /* 0x64-0x74 */
    OPTIONS_Bool default_language_flag;   /* 0x75 */
    uint8_t      reserved4[24];           /* 0x76-0x8D */

    /* Language settings */
    uint32_t     audio_language_index;    /* 0x8E-0x91: 1-20 */
    OPTIONS_Hash audio_language_hash;     /* 0x92-0x95 */
    uint8_t      reserved5[17];           /* 0x96-0xA6 */
    uint32_t     subtitle_language_index; /* 0xA7-0xAA: 1-20 */
    OPTIONS_Hash subtitle_language_hash;  /* 0xAB-0xAE */
    uint8_t      reserved6[17];           /* 0xAF-0xBF */

    /* Audio settings (dB scale: -96.0 to 0.0) */
    OPTIONS_Float music_volume;           /* 0xC0-0xC3 */
    uint8_t      reserved7[17];           /* 0xC4-0xD4 */
    OPTIONS_Float voice_volume;           /* 0xD5-0xD8 */
    uint8_t      reserved8[17];           /* 0xD9-0xE9 */
    OPTIONS_Float sfx_volume;             /* 0xEA-0xED */
    uint8_t      reserved9[17];           /* 0xEE-0xFE */
    OPTIONS_Bool vibration_enabled;       /* 0xFF */

    /* Control settings */
    uint8_t      reserved10[17];          /* 0x100-0x110 */
    OPTIONS_Float x_look_sensitivity;     /* 0x111-0x114: 0.5x to 2.0x */
    uint8_t      reserved11[17];          /* 0x115-0x125 */
    OPTIONS_Float y_look_sensitivity;     /* 0x126-0x129: 0.5x to 2.0x */
    uint8_t      reserved12[17];          /* 0x12A-0x13A */
    OPTIONS_Bool invert_3p_x;             /* 0x13B */
    uint8_t      reserved13[17];          /* 0x13C-0x14C */
    OPTIONS_Bool invert_3p_y;             /* 0x14D */
    uint8_t      reserved14[17];          /* 0x14E-0x15E */
    OPTIONS_Bool invert_1p_x;             /* 0x15F */
    uint8_t      reserved15[17];          /* 0x160-0x170 */
    OPTIONS_Bool invert_1p_y;             /* 0x171 */
    uint8_t      reserved16[17];          /* 0x172-0x182 */
    uint8_t      action_camera_freq;      /* 0x183: 0-3 */
    uint8_t      reserved17[17];          /* 0x184-0x194 */
    uint8_t      brightness;              /* 0x195: 1-16 */
    uint8_t      reserved18[17];          /* 0x196-0x1A6 */
    OPTIONS_Bool blood_enabled;           /* 0x1A7 */
    uint8_t      reserved19[17];          /* 0x1A8-0x1B8 */
    OPTIONS_Bool flying_machine_invert;   /* 0x1B9 */
    uint8_t      reserved20[17];          /* 0x1BA-0x1CA */
    OPTIONS_Bool cannon_invert_x;         /* 0x1CB */
    uint8_t      reserved21[17];          /* 0x1CC-0x1DC */
    OPTIONS_Bool cannon_invert_y;         /* 0x1DD */
    uint8_t      reserved22[17];          /* 0x1DE-0x1EE */

    /* HUD settings (18-byte record structure) */
    OPTIONS_Bool hud_health_meter;        /* 0x1EF */
    uint8_t      hud_health_data[17];     /* 0x1F0-0x200 */
    OPTIONS_Bool hud_controls;            /* 0x201 */
    uint8_t      hud_controls_data[17];   /* 0x202-0x212 */
    OPTIONS_Bool hud_updates;             /* 0x213 */
    uint8_t      hud_updates_data[17];    /* 0x214-0x224 */
    OPTIONS_Bool hud_weapon;              /* 0x225 */
    uint8_t      hud_weapon_data[17];     /* 0x226-0x236 */
    OPTIONS_Bool hud_minimap;             /* 0x237 */
    uint8_t      hud_minimap_data[17];    /* 0x238-0x248 */
    OPTIONS_Bool hud_money;               /* 0x249 */
    uint8_t      hud_money_data[35];      /* 0x24A-0x26C */
    OPTIONS_Bool hud_ssi;                 /* 0x26D */
    uint8_t      hud_ssi_data[17];        /* 0x26E-0x27E */
    OPTIONS_Bool hud_tutorial;            /* 0x27F */
    uint8_t      hud_tutorial_data[17];   /* 0x280-0x290 */

    /* Unlock records */
    UnlockRecord templar_lair_1;          /* 0x291: hash 0x00788F42 */
    UnlockRecord templar_lair_2;          /* 0x2A3: hash 0x006FF456 */
    UnlockRecord unknown_unlock_1;        /* 0x2B5: hash 0x000B953B */
    UnlockRecord unknown_unlock_2;        /* 0x2C7: hash 0x001854EC */
    UnlockRecord uplay_florentine;        /* 0x2D9: hash 0x0021D9D0 */
    UnlockRecord uplay_altair_armor;      /* 0x2EB: hash 0x0036A2C4 */
    UnlockRecord uplay_altair_robes;      /* 0x2FD: hash 0x0052C3A9 */
    UnlockRecord uplay_hellequin;         /* 0x30F: hash 0x000E8D04 */
    uint8_t      reserved23[72];          /* 0x321-0x368 */

    /* Costume bitfield */
    CostumeBitfield costumes;             /* 0x369 */
    uint8_t      reserved24[428];         /* 0x36A-0x515 */

    /* DLC/Update flags */
    OPTIONS_Bool apu_1_0;                 /* 0x516: Animus Project Update 1.0 */
    OPTIONS_Bool apu_2_0;                 /* 0x517: Animus Project Update 2.0 */
    OPTIONS_Bool apu_3_0;                 /* 0x518: Animus Project Update 3.0 */
    OPTIONS_Bool da_vinci_dlc;            /* 0x519: Da Vinci Disappearance */
    uint8_t      reserved25[4];           /* 0x51A-0x51D */
} Section2_GameSettings;
```

---

## Section 3: Game Progress

**Uncompressed Size:** 162 bytes (PC) / 119 bytes (PS3)

### Achievement Bitfield (PC Only)

```c
/* Achievement Bitfield - 7 bytes (53 achievements) */
typedef struct {
    uint8_t byte0;  /* 0x84: Achievements 1-8 (Story) */
    uint8_t byte1;  /* 0x85: Achievements 9-16 (Story + Shrines) */
    uint8_t byte2;  /* 0x86: Achievements 17-24 (Shrines + Da Vinci) */
    uint8_t byte3;  /* 0x87: Achievements 25-32 (Side Activities) */
    uint8_t byte4;  /* 0x88: Achievements 33-40 (Miscellaneous) */
    uint8_t byte5;  /* 0x89: Achievements 41-48 (Multiplayer) */
    uint8_t byte6;  /* 0x8A: Achievements 49-53 (MP + DLC), bits 5-7 unused */
} AchievementBitfield;

/* All achievements unlocked: FF FF FF FF FF FF 1F */
```

### Section 3 Property Record Structure

Section 3 uses a different property record layout than Section 1:

```c
/* Section 3 Property Record - 18 bytes
 * Note: Hash is at START (+0x00), not at +0x0A like Section 1
 */
typedef struct {
    OPTIONS_Hash hash;            /* +0x00: Content identifier hash */
    uint8_t      padding1[8];     /* +0x04: Zero padding */
    uint8_t      marker;          /* +0x0C: 0x0B structure marker */
    uint8_t      flag;            /* +0x0D: Value/flag byte */
    uint8_t      type;            /* +0x0E: Type marker (0x0E) */
    uint8_t      padding2[3];     /* +0x0F: Zero padding to 18 bytes */
} Section3_PropertyRecord;

_Static_assert(sizeof(Section3_PropertyRecord) == 18, "Section3_PropertyRecord must be 18 bytes");
```

### Complete Section 3 Structure (PC)

```c
/* Section 3: Game Progress - 162 bytes (PC) */
typedef struct {
    /* Common header (0x00-0x17) */
    uint8_t      zero_padding[10];        /* 0x00-0x09 */
    OPTIONS_Hash section_hash;            /* 0x0A-0x0D: 0xC9876D66 */
    uint16_t     platform_flags;          /* 0x0E-0x0F: PC=0x050C */
    uint8_t      reserved1[8];            /* 0x10-0x17 */

    /* Property records region (0x18-0x4C) - 3 records identified */
    /* Record 1: 0x18-0x29 */
    OPTIONS_Hash record1_hash;            /* 0x1A: 0xBF4C2013 */
    uint8_t      record1_data[14];        /* 0x1E-0x2B */

    /* Record 2: 0x2C-0x3D */
    OPTIONS_Hash record2_hash;            /* 0x2F: 0x3B546966 */
    uint8_t      record2_data[14];        /* 0x33-0x40 */

    /* Record 3: 0x3E-0x4F (overlaps with Uplay marker) */
    OPTIONS_Hash record3_hash;            /* 0x41: 0x4DBC7DA7 */
    uint8_t      record3_data[10];        /* 0x45-0x4E */

    uint8_t      marker_0x4d;             /* 0x4D: 0x0B (constant) */
    OPTIONS_Bool uplay_gun_upgrade;       /* 0x4E: 30-point Uplay reward */
    uint8_t      marker_0x4f;             /* 0x4F: 0x0E (constant) */

    /* Pre-achievement region (0x50-0x7F) - 2 more records */
    /* Record 4: 0x50-0x61 */
    OPTIONS_Hash record4_hash;            /* 0x53: 0x5B95F10B (both platforms) */
    uint8_t      record4_data[14];        /* 0x57-0x64 */

    /* Record 5: 0x62-0x73 */
    OPTIONS_Hash record5_hash;            /* 0x65: 0x2A4E8A90 (both platforms) */
    uint8_t      record5_data[14];        /* 0x69-0x76 */

    /* Record 6: 0x74-0x7F (PC only, partial) */
    OPTIONS_Hash record6_hash;            /* 0x77: 0x496F8780 (PC only) */
    uint8_t      record6_data[8];         /* 0x7B-0x7F */

    /* Achievement region - PC ONLY */
    uint8_t      achievement_header[4];   /* 0x80-0x83: 00 09 00 0B */
    AchievementBitfield achievements;     /* 0x84-0x8A: 53-bit bitfield */
    uint8_t      padding_0x8b;            /* 0x8B: 0x00 */
    uint32_t     marker_0x8c;             /* 0x8C-0x8F: 0x0000000E */
    OPTIONS_Hash progress_hash;           /* 0x90-0x93: 0x6F88B05B */
    uint8_t      reserved4[8];            /* 0x94-0x9B */
    uint8_t      marker_0x9c;             /* 0x9C: 0x0B (constant) */
    OPTIONS_Bool dlc_sync_flag;           /* 0x9D */
    uint8_t      reserved5[2];            /* 0x9E-0x9F */
    uint8_t      trailing_data[2];        /* 0xA0-0xA1 */
} Section3_GameProgress_PC;
```

### Section 3 Structure (PS3)

```c
/* Section 3: Game Progress - 119 bytes (PS3)
 *
 * PS3 is 43 bytes smaller because:
 * 1. No embedded achievement bitfield (PSN Trophy API handles this)
 * 2. DLC sync flag at 0x5A instead of 0x9D
 * 3. Record 6 (0x496F8780) and achievement region omitted
 */
typedef struct {
    /* Common header (0x00-0x17) */
    uint8_t      zero_padding[10];        /* 0x00-0x09 */
    OPTIONS_Hash section_hash;            /* 0x0A-0x0D: 0xC9876D66 */
    uint16_t     platform_flags;          /* 0x0E-0x0F: PS3=0x0508 */
    uint8_t      reserved1[8];            /* 0x10-0x17 */

    /* Property records region (0x18-0x4C) - same as PC */
    OPTIONS_Hash record1_hash;            /* 0x1A: 0xBF4C2013 */
    uint8_t      record1_data[14];        /* 0x1E-0x2B */
    OPTIONS_Hash record2_hash;            /* 0x2F: 0x3B546966 */
    uint8_t      record2_data[14];        /* 0x33-0x40 */
    OPTIONS_Hash record3_hash;            /* 0x41: 0x4DBC7DA7 */
    uint8_t      record3_data[10];        /* 0x45-0x4E */

    uint8_t      marker_0x4d;             /* 0x4D: 0x0B (constant) */
    OPTIONS_Bool uplay_gun_upgrade;       /* 0x4E: 30-point Uplay reward */
    uint8_t      marker_0x4f;             /* 0x4F: 0x0E (constant) */

    /* Shared records region (0x50-0x76) */
    OPTIONS_Hash record4_hash;            /* 0x53: 0x5B95F10B (same as PC) */
    uint8_t      record4_data[14];        /* 0x57-0x64 */
    OPTIONS_Hash record5_hash;            /* 0x65: 0x2A4E8A90 (same as PC) */
    uint8_t      record5_data[8];         /* 0x69-0x70 */

    /* Platform-specific differences */
    uint8_t      ps3_flag_0x60;           /* 0x60: 0x01 (PC has 0x00) */
    uint8_t      ps3_type_0x73;           /* 0x73: 0x00 (PC has 0x15) */

    /* DLC sync region - different offset than PC */
    OPTIONS_Bool dlc_sync_flag;           /* 0x5A */
    uint8_t      trailing_data[28];       /* 0x5B-0x76 */
} Section3_GameProgress_PS3;
```

---

## Section 4: Controller Mappings (PS3 Only)

**Uncompressed Size:** 1903 bytes
**Coverage:** 98.8% (Phase 3 analysis)

### Section 4 Header (97 bytes)

```c
/* Section 4 Header - 97 bytes */
typedef struct {
    uint8_t      zero_padding[10];    /* 0x00-0x09: Always zeros */
    OPTIONS_Hash section_hash;        /* 0x0A-0x0D: 0xB4B55039 */
    uint16_t     platform_flags;      /* 0x0E-0x0F: 0x075D */
    uint32_t     unknown;             /* 0x10-0x13: 0x07550000 */
    uint32_t     type_indicator;      /* 0x14-0x17: 0x00110000 */
    uint8_t      extended_header[73]; /* 0x18-0x60: Property records */
} Section4_Header;

_Static_assert(sizeof(Section4_Header) == 97, "Section4_Header must be 97 bytes");
```

### Button Mapping Record (85 bytes)

All records share identical template structure except Button ID at +0x1D.

```c
/* PS3 Button Mapping Property Sub-Record - 18 bytes */
typedef struct {
    uint8_t      padding[3];          /* +0x00: zeros */
    uint8_t      type_marker;         /* +0x03: 0x0F */
    uint32_t     value;               /* +0x04: matches record_size */
    OPTIONS_Hash action_hash;         /* +0x08: binding hash */
    uint8_t      trailing[5];         /* +0x0C: zeros */
    uint8_t      next_marker;         /* +0x11: 0x05 or 0x0B */
} ButtonPropertyRecord;

/* PS3 Button Mapping Record - 85 bytes */
typedef struct {
    uint8_t  signature[5];            /* +0x00: A8 CF 5F F9 43 */
    uint32_t record_size;             /* +0x05: 0x0000003B (59, BE) */
    uint32_t record_count;            /* +0x09: 0x00000011 (17, BE) */
    uint32_t controller_hash;         /* +0x0D: 0x8157B2C0 (DualShock 3) */
    uint8_t  reserved[9];             /* +0x11: zeros */
    uint16_t field_marker;            /* +0x1A: 0x0006 */
    uint8_t  struct_marker;           /* +0x1C: 0x0B */
    uint8_t  button_id;               /* +0x1D: varies (0x02-0x22) */
    /* Property Records Section - 55 bytes */
    ButtonPropertyRecord prop1;       /* +0x1E: hash 0xE717D13B */
    ButtonPropertyRecord prop2;       /* +0x30: hash 0x0043E6D0 */
    uint8_t  prop3_marker;            /* +0x42: 0x05 */
    uint8_t  prop3_padding;           /* +0x43: 0x00 */
    uint8_t  prop3_struct;            /* +0x44: 0x0B */
    uint8_t  prop3_zeros[16];         /* +0x45: zeros to end */
} PS3_ButtonRecord;

_Static_assert(sizeof(PS3_ButtonRecord) == 85, "PS3_ButtonRecord must be 85 bytes");

/* Button ID to DualShock 3 Button Mapping:
 * 0x02 = Cross (X)         0x14 = Select
 * 0x05 = L1                0x15 = Triangle
 * 0x07 = R1                0x16 = Circle
 * 0x08 = L2                0x19 = Square
 * 0x0A = R2                0x1C = Start
 * 0x0E = D-Pad             0x1F = L3 (Left Stick Click)
 * 0x0F = D-Pad Alternate   0x20 = R3 (Right Stick Click)
 * 0x11 = Left Stick        0x22 = PS Button
 * 0x12 = Right Stick
 *
 * Key Finding: Only button_id varies between records.
 * All other fields are constant templates.
 */
```

### Trailer Property Record (18 bytes)

```c
/* Section 4 Trailer Property Record - 18 bytes */
typedef struct {
    uint8_t      marker;              /* +0x00: 0x0B */
    uint8_t      flag;                /* +0x01: 0x00 or 0x01 */
    uint8_t      type;                /* +0x02: 0x0E, 0x15, etc. */
    uint8_t      padding[3];          /* +0x03: zeros */
    OPTIONS_Hash property_hash;       /* +0x06: configuration hash */
    uint8_t      trailing[8];         /* +0x0A: zeros */
} Section4_TrailerRecord;

/* Known Trailer Hashes:
 * 0x9F1438A5, 0xAFBEEA25, 0x221991EF, 0x20AD7434,
 * 0xB6BA16BB, 0x1A361AE1, 0x605F5F37, 0x3B7A5EB8
 */
```

### Complete Section 4 Structure

```c
/* Section 4: PS3 Controller Mappings - 1903 bytes */
typedef struct {
    Section4_Header   header;           /* 0x00-0x60: 97 bytes */
    PS3_ButtonRecord  buttons[17];      /* 0x61-0x605: 1445 bytes */
    uint8_t           trailer[256];     /* 0x606-0x705: property records */
    uint8_t           padding[105];     /* 0x706-0x76E: zero padding */
} Section4_ControllerMappings;

_Static_assert(sizeof(Section4_ControllerMappings) == 1903,
               "Section4_ControllerMappings must be 1903 bytes");
```

---

## Value Tables

### Volume Levels (dB Scale)

```c
/* Volume slider values - IEEE 754 floats */
static const uint32_t VOLUME_VALUES[] = {
    0x00000000,  /* Level 10:   0.0 dB (Maximum) */
    0xBF6A4744,  /* Level  9:  -0.916 dB */
    0xBFF816F0,  /* Level  8:  -1.938 dB */
    0xC0464646,  /* Level  7:  -3.098 dB */
    0xC08DFBB2,  /* Level  6:  -4.437 dB */
    0xC0C0A8C0,  /* Level  5:  -6.020 dB (Default) */
    0xC0FEAE7C,  /* Level  4:  -7.958 dB */
    0xC1275239,  /* Level  3: -10.457 dB */
    0xC15FAB9E,  /* Level  2: -13.979 dB */
    0xC19FFFFF,  /* Level  1: -19.999 dB */
    0xC2C00000,  /* Level  0: -96.0 dB (Mute) */
};
```

### Sensitivity Levels (Multiplier Scale)

```c
/* Sensitivity slider values - IEEE 754 floats */
static const uint32_t SENSITIVITY_VALUES[] = {
    0x40000000,  /* Level 10: 2.0x (Maximum) */
    0x3FE66666,  /* Level  9: 1.8x */
    0x3FCCCCCD,  /* Level  8: 1.6x */
    0x3FB33333,  /* Level  7: 1.4x */
    0x3F99999A,  /* Level  6: 1.2x */
    0x3F800000,  /* Level  5: 1.0x (Default) */
    0x3F4CCCCD,  /* Level  4: 0.8x */
    0x3F333333,  /* Level  3: 0.7x */
    0x3F19999A,  /* Level  2: 0.6x */
    0x3F000000,  /* Level  1: 0.5x (Minimum) */
};
```

---

## Notes

1. **Byte Order:** All multi-byte values are little-endian unless otherwise noted
2. **Reserved Fields:** Marked as `reserved` - purpose unknown, modify at own risk
3. **Platform Flags:** Distinguishes PC (0x050C) from PS3 (0x0508) at decompressed data level
4. **18-byte Records:** Both PropertyRecord and UnlockRecord are 18 bytes - shared serialization format
5. **PS3 Differences:** PS3 uses PSN Trophy API for achievements, hence smaller Section 3

---

**End of Document**
