# AC Brotherhood OPTIONS - Bitfield Reference

**Document Version:** 1.0
**Date:** 2025-12-27
**Status:** Complete Bitfield Documentation

This document provides complete documentation of all bitfields, flag bytes, and multi-bit encoded fields found in the AC Brotherhood OPTIONS file format.

---

## Table of Contents

1. [Section 1 Bitfields](#section-1-bitfields)
   - [Platform Flags (0x0E-0x0F)](#platform-flags-0x0e-0x0f)
2. [Section 2 Bitfields](#section-2-bitfields)
   - [Action Camera Frequency (0x183)](#action-camera-frequency-0x183)
   - [Costume Bitfield (0x369)](#costume-bitfield-0x369)
   - [DLC/Update Flags (0x516-0x519)](#dlcupdate-flags-0x516-0x519)
3. [Section 3 Bitfields](#section-3-bitfields)
   - [Achievement Bitfield (0x84-0x8A)](#achievement-bitfield-0x84-0x8a)
4. [Bitwise Operations Guide](#bitwise-operations-guide)
5. [Ghidra Function References](#ghidra-function-references)

---

## Section 1 Bitfields

### Platform Flags (0x0E-0x0F)

**Location:** Section 1, Offset 0x0E-0x0F (also present in Sections 2 and 3)
**Size:** 2 bytes (16 bits)
**Confidence:** [H] High - Platform differential analysis

The platform flags field identifies the target platform and may contain additional system configuration bits.

| Offset | Bit | Mask | Name | Values | Description |
|--------|-----|------|------|--------|-------------|
| 0x0E | 0-7 | 0x00FF | Platform Low Byte | 0x0C (PC), 0x08 (PS3) | Primary platform identifier |
| 0x0F | 0-7 | 0xFF00 | Platform High Byte | 0x05 | Version/revision indicator |

#### Known Platform Values

| Platform | Bytes (LE) | Combined Value | Description |
|----------|------------|----------------|-------------|
| PC | `0C 05` | 0x050C | Windows PC version |
| PS3 | `08 05` | 0x0508 | PlayStation 3 version |

**Bit Breakdown (0x050C for PC):**

| Bit Position | Hex | Meaning |
|--------------|-----|---------|
| Bits 0-1 | 0x0C & 0x03 = 0x00 | Reserved/unused |
| Bits 2-3 | 0x0C & 0x0C = 0x0C | Platform type (0x03 = PC, 0x02 = PS3) |
| Bits 4-7 | 0x0C & 0xF0 = 0x00 | Reserved |
| Bits 8-11 | 0x05 & 0x0F = 0x05 | Format version |
| Bits 12-15 | 0x05 & 0xF0 = 0x00 | Reserved |

**Note:** The exact bit-level semantics are inferred from PC/PS3 differences. Only bits 2-3 differ between platforms.

---

## Section 2 Bitfields

### Action Camera Frequency (0x183)

**Location:** Section 2, Offset 0x183
**Size:** 1 byte (8 bits, but only 2 bits used)
**Confidence:** [M] Medium - Menu mapping inference

The Action Camera Frequency setting uses a 2-bit field to encode 4 possible values.

| Offset | Bit | Mask | Name | Values | Description |
|--------|-----|------|------|--------|-------------|
| 0x183 | 0-1 | 0x03 | Action Camera Level | 0-3 | Frequency setting |
| 0x183 | 2-7 | 0xFC | (Unused) | 0x00 | Reserved bits |

#### Value Encoding

| Binary | Hex | Level | In-Game Setting |
|--------|-----|-------|-----------------|
| `00` | 0x00 | 0 | Off (Never) |
| `01` | 0x01 | 1 | Low (Rare) |
| `10` | 0x02 | 2 | Medium (Default) |
| `11` | 0x03 | 3 | High (Frequent) |

**Bitwise Operations:**
```c
// Read action camera level
uint8_t level = data[0x183] & 0x03;

// Set action camera level (preserving other bits)
data[0x183] = (data[0x183] & 0xFC) | (new_level & 0x03);
```

---

### Costume Bitfield (0x369)

**Location:** Section 2, Offset 0x369 (within 18-byte record starting at 0x368)
**Size:** 1 byte (8 bits, 6 bits used)
**Confidence:** [P] Proven - Ghidra: FUN_00acf240, Binary verification

**IMPORTANT:** The costume "bitfield" at 0x369 is NOT a standalone byte. It is the VALUE byte (+0x01) within an 18-byte property record that starts at offset 0x368. This record uses **Type 0x00** (bitfield/complex value), not Type 0x0E (boolean).

**Record Structure (binary verified):**
```
0x368: 0B 3F 00 00 00 00 00 00 3D 00 00 00 C2 EA 86 02 96 CE
       ^  ^  ^
       |  |  +-- Type 0x00 (bitfield/complex record, NOT 0x0E boolean)
       |  +-- Value byte (costume bitfield): 0x3F = all unlocked
       +-- Marker 0x0B (record start)
```

The costume bitfield tracks unlocked alternate costumes/outfits for Ezio.

| Offset | Bit | Mask | Name | Values | Description |
|--------|-----|------|------|--------|-------------|
| 0x369 | 0 | 0x01 | florentine_noble | 0=locked, 1=unlocked | Florentine Noble Attire |
| 0x369 | 1 | 0x02 | armor_of_altair | 0=locked, 1=unlocked | Armor of Altair |
| 0x369 | 2 | 0x04 | altairs_robes | 0=locked, 1=unlocked | Altair's Robes |
| 0x369 | 3 | 0x08 | drachen_armor | 0=locked, 1=unlocked | Drachen Armor (Pre-order DLC) |
| 0x369 | 4 | 0x10 | desmond | 0=locked, 1=unlocked | Desmond's Outfit (In-game unlock) |
| 0x369 | 5 | 0x20 | raiden | 0=locked, 1=unlocked | Raiden Outfit (100% sync bonus) |
| 0x369 | 6-7 | 0xC0 | (Unused) | 0x00 | Reserved bits |

#### Common Values

| Binary | Hex | Description |
|--------|-----|-------------|
| `000000` | 0x00 | No costumes unlocked (base game) |
| `000111` | 0x07 | All Uplay costumes |
| `001111` | 0x0F | Uplay + Drachen |
| `111111` | 0x3F | All costumes unlocked |

**Bitwise Operations:**
```c
// Check if Altair's Robes unlocked
bool has_altair = (data[0x369] & 0x04) != 0;

// Unlock all costumes
data[0x369] = 0x3F;

// Unlock specific costume (Desmond)
data[0x369] |= 0x10;

// Lock specific costume (Raiden)
data[0x369] &= ~0x20;
```

#### Costume Unlock Mechanism

The costume bitfield at 0x369 is the **authoritative control** for costume unlocks. Setting the appropriate bit unlocks the corresponding costume.

**Note:** The unlock records at offsets 0x2D9, 0x2EB, 0x2FD, and 0x30F are Uplay-related but their specific purpose is **UNKNOWN**. They were observed to flip in Uplay test files. They do NOT directly control costume unlocks - the costume bitfield at 0x369 is the mechanism for that.

---

### DLC/Update Flags (0x516-0x519)

**Location:** Section 2, Offset 0x516-0x519
**Size:** 4 bytes (4 individual boolean flags)
**Confidence:** [M] Medium - Differential analysis

These flags indicate installed DLC and free content updates. Each byte functions as an independent boolean.

| Offset | Bit | Mask | Name | Values | Description |
|--------|-----|------|------|--------|-------------|
| 0x516 | 0-7 | 0xFF | apu_1_0 | 0x00=no, 0x01=yes | Animus Project Update 1.0 |
| 0x517 | 0-7 | 0xFF | apu_2_0 | 0x00=no, 0x01=yes | Animus Project Update 2.0 |
| 0x518 | 0-7 | 0xFF | apu_3_0 | 0x00=no, 0x01=yes | Animus Project Update 3.0 |
| 0x519 | 0-7 | 0xFF | da_vinci_dlc | 0x00=no, 0x01=yes | Da Vinci Disappearance DLC |

#### DLC Content Reference

| Flag | Content Included |
|------|------------------|
| APU 1.0 (0x516) | Mont Saint-Michel multiplayer map |
| APU 2.0 (0x517) | Pienza multiplayer map |
| APU 3.0 (0x518) | Alhambra map + Dama Rossa, Knight, Marquis, Pariah characters |
| Da Vinci DLC (0x519) | The Da Vinci Disappearance story expansion |

**Note:** These are stored as individual bytes, not as a true bitfield. Each flag is either 0x00 (disabled) or 0x01 (enabled), though the game may accept any non-zero value as "enabled".

---

## Section 3 Bitfields

### Achievement Bitfield (0x84-0x8A)

**Location:** Section 3, Offset 0x84-0x8A (PC only)
**Size:** 7 bytes (56 bits total, 53 used)
**Confidence:** [P] Proven - 24-file differential analysis

**IMPORTANT:** This bitfield is **PC-only**. PS3 uses the PlayStation Network Trophy API for achievement tracking, so Section 3 on PS3 is 43 bytes smaller and lacks this embedded bitfield.

The achievement bitfield stores the unlock status of all 53 in-game achievements.

#### Structure Header

| Offset | Size | Value | Description |
|--------|------|-------|-------------|
| 0x80 | 4 | `00 09 00 0B` | Achievement header marker |
| 0x84 | 7 | Variable | Achievement bitfield (53 bits) |
| 0x8B | 1 | `00` | Padding |
| 0x8C | 4 | `0E 00 00 00` | Structure marker |
| 0x90 | 4 | `5B B0 88 6F` | Progress hash (0x6F88B05B) |

#### Byte 0x84: Achievements 1-8 (Story Progression)

| Offset | Bit | Mask | Name | Values | Description |
|--------|-----|------|------|--------|-------------|
| 0x84 | 0 | 0x01 | technical_difficulties | 0=locked, 1=unlocked | TECHNICAL DIFFICULTIES |
| 0x84 | 1 | 0x02 | battle_wounds | 0=locked, 1=unlocked | BATTLE WOUNDS |
| 0x84 | 2 | 0x04 | sanctuary_sanctuary | 0=locked, 1=unlocked | SANCTUARY! SANCTUARY! |
| 0x84 | 3 | 0x08 | rome_in_ruins | 0=locked, 1=unlocked | ROME IN RUINS |
| 0x84 | 4 | 0x10 | fixer_upper | 0=locked, 1=unlocked | FIXER-UPPER |
| 0x84 | 5 | 0x20 | principessa_in_another_castello | 0=locked, 1=unlocked | PRINCIPESSA IN ANOTHER CASTELLO |
| 0x84 | 6 | 0x40 | fundraiser | 0=locked, 1=unlocked | FUNDRAISER |
| 0x84 | 7 | 0x80 | forget_paris | 0=locked, 1=unlocked | FORGET PARIS |

#### Byte 0x85: Achievements 9-16 (Story + Shrines)

| Offset | Bit | Mask | Name | Values | Description |
|--------|-----|------|------|--------|-------------|
| 0x85 | 0 | 0x01 | bloody_sunday | 0=locked, 1=unlocked | BLOODY SUNDAY |
| 0x85 | 1 | 0x02 | vittoria_agli_assassini | 0=locked, 1=unlocked | VITTORIA AGLI ASSASSINI |
| 0x85 | 2 | 0x04 | requiescat_in_pace | 0=locked, 1=unlocked | REQUIESCAT IN PACE |
| 0x85 | 3 | 0x08 | knife_to_the_heart | 0=locked, 1=unlocked | A KNIFE TO THE HEART |
| 0x85 | 4 | 0x10 | perfect_recall | 0=locked, 1=unlocked | PERFECT RECALL |
| 0x85 | 5 | 0x20 | deja_vu | 0=locked, 1=unlocked | DEJA VU |
| 0x85 | 6 | 0x40 | undertaker_2_0 | 0=locked, 1=unlocked | UNDERTAKER 2.0 |
| 0x85 | 7 | 0x80 | golden_boy | 0=locked, 1=unlocked | GOLDEN BOY |

#### Byte 0x86: Achievements 17-24 (Shrines + Da Vinci Machines)

| Offset | Bit | Mask | Name | Values | Description |
|--------|-----|------|------|--------|-------------|
| 0x86 | 0 | 0x01 | gladiator | 0=locked, 1=unlocked | GLADIATOR |
| 0x86 | 1 | 0x02 | plumber | 0=locked, 1=unlocked | PLUMBER |
| 0x86 | 2 | 0x04 | one_man_wrecking_crew | 0=locked, 1=unlocked | ONE-MAN WRECKING CREW |
| 0x86 | 3 | 0x08 | amen | 0=locked, 1=unlocked | AMEN |
| 0x86 | 4 | 0x10 | bang | 0=locked, 1=unlocked | BANG! |
| 0x86 | 5 | 0x20 | splash | 0=locked, 1=unlocked | SPLASH! |
| 0x86 | 6 | 0x40 | boom | 0=locked, 1=unlocked | BOOM! |
| 0x86 | 7 | 0x80 | kaboom | 0=locked, 1=unlocked | KABOOM! |

#### Byte 0x87: Achievements 25-32 (Side Activities)

| Offset | Bit | Mask | Name | Values | Description |
|--------|-----|------|------|--------|-------------|
| 0x87 | 0 | 0x01 | home_improvement | 0=locked, 1=unlocked | HOME IMPROVEMENT |
| 0x87 | 1 | 0x02 | tower_defense | 0=locked, 1=unlocked | TOWER DEFENSE |
| 0x87 | 2 | 0x04 | show_off | 0=locked, 1=unlocked | SHOW OFF |
| 0x87 | 3 | 0x08 | iamalive | 0=locked, 1=unlocked | .. .- -- .- .-.. .. ...- . (Morse: IAMALIVE) |
| 0x87 | 4 | 0x10 | perfectionist | 0=locked, 1=unlocked | PERFECTIONIST |
| 0x87 | 5 | 0x20 | brotherhood | 0=locked, 1=unlocked | BROTHERHOOD |
| 0x87 | 6 | 0x40 | welcome_to_brotherhood | 0=locked, 1=unlocked | WELCOME TO THE BROTHERHOOD |
| 0x87 | 7 | 0x80 | capture_the_flag | 0=locked, 1=unlocked | CAPTURE THE FLAG |

#### Byte 0x88: Achievements 33-40 (Miscellaneous)

| Offset | Bit | Mask | Name | Values | Description |
|--------|-----|------|------|--------|-------------|
| 0x88 | 0 | 0x01 | in_memoriam | 0=locked, 1=unlocked | IN MEMORIAM |
| 0x88 | 1 | 0x02 | dust_to_dust | 0=locked, 1=unlocked | DUST TO DUST |
| 0x88 | 2 | 0x04 | serial_killer | 0=locked, 1=unlocked | SERIAL KILLER |
| 0x88 | 3 | 0x08 | spring_cleaning | 0=locked, 1=unlocked | SPRING CLEANING |
| 0x88 | 4 | 0x10 | your_wish_granted | 0=locked, 1=unlocked | YOUR WISH IS GRANTED |
| 0x88 | 5 | 0x20 | fly_like_eagle | 0=locked, 1=unlocked | FLY LIKE AN EAGLE |
| 0x88 | 6 | 0x40 | gloves_come_off | 0=locked, 1=unlocked | THE GLOVES COME OFF |
| 0x88 | 7 | 0x80 | mailer_daemon | 0=locked, 1=unlocked | MAILER DAEMON |

#### Byte 0x89: Achievements 41-48 (Multiplayer)

| Offset | Bit | Mask | Name | Values | Description |
|--------|-----|------|------|--------|-------------|
| 0x89 | 0 | 0x01 | rome_bronze | 0=locked, 1=unlocked | ROME GLOBAL ECONOMY BRONZE MEDAL |
| 0x89 | 1 | 0x02 | rome_silver | 0=locked, 1=unlocked | ROME GLOBAL ECONOMY SILVER MEDAL |
| 0x89 | 2 | 0x04 | rome_gold | 0=locked, 1=unlocked | ROME GLOBAL ECONOMY GOLD MEDAL |
| 0x89 | 3 | 0x08 | strong_arm | 0=locked, 1=unlocked | STRONG-ARM |
| 0x89 | 4 | 0x10 | high_roller | 0=locked, 1=unlocked | HIGH ROLLER |
| 0x89 | 5 | 0x20 | il_principe | 0=locked, 1=unlocked | IL PRINCIPE |
| 0x89 | 6 | 0x40 | airstrike | 0=locked, 1=unlocked | AIRSTRIKE |
| 0x89 | 7 | 0x80 | gps | 0=locked, 1=unlocked | GPS |

#### Byte 0x8A: Achievements 49-53 (MP + DLC)

| Offset | Bit | Mask | Name | Values | Description |
|--------|-----|------|------|--------|-------------|
| 0x8A | 0 | 0x01 | clowning_around | 0=locked, 1=unlocked | CLOWNING AROUND |
| 0x8A | 1 | 0x02 | special_delivery | 0=locked, 1=unlocked | SPECIAL DELIVERY |
| 0x8A | 2 | 0x04 | grand_theft_dressage | 0=locked, 1=unlocked | GRAND THEFT DRESSAGE |
| 0x8A | 3 | 0x08 | going_up | 0=locked, 1=unlocked | GOING UP |
| 0x8A | 4 | 0x10 | easy_come_easy_go | 0=locked, 1=unlocked | EASY COME, EASY GO |
| 0x8A | 5-7 | 0xE0 | (Unused) | 0x00 | Reserved bits (always 0) |

#### Common Achievement Values

| Hex Value | Binary (all 7 bytes) | Description |
|-----------|----------------------|-------------|
| `00 00 00 00 00 00 00` | All zeros | No achievements unlocked |
| `FF FF FF FF FF FF 1F` | All ones (53 bits) | All achievements unlocked |

**Bitwise Operations:**
```c
// Check if "ROME IN RUINS" (bit 3 of byte 0x84) is unlocked
bool has_rome_in_ruins = (data[0x84] & 0x08) != 0;

// Unlock all story achievements (byte 0x84)
data[0x84] = 0xFF;

// Unlock all achievements (all 53 bits)
memset(&data[0x84], 0xFF, 6);  // Bytes 0x84-0x89 = 0xFF
data[0x8A] = 0x1F;             // Byte 0x8A = 0x1F (bits 0-4 only)

// Count unlocked achievements
int count = 0;
for (int byte_idx = 0; byte_idx < 7; byte_idx++) {
    uint8_t byte = data[0x84 + byte_idx];
    while (byte) {
        count += byte & 1;
        byte >>= 1;
    }
}
// Subtract 3 unused bits from count if using all bytes
count -= __builtin_popcount(data[0x8A] & 0xE0);
```

---

## Bitwise Operations Guide

### Understanding Bitwise Flags

Each byte can store 8 separate on/off flags using individual bits:

```
Bit Position:  7  6  5  4  3  2  1  0
Binary:        0  0  0  0  0  0  0  0
Hex Values:   80 40 20 10 08 04 02 01
```

### Common Operations

#### Reading a Single Bit
```c
// Check if bit N is set
bool is_set = (byte & (1 << N)) != 0;

// Example: Check bit 3
bool bit3_set = (data[offset] & 0x08) != 0;
```

#### Setting a Single Bit
```c
// Set bit N to 1
byte |= (1 << N);

// Example: Set bit 5
data[offset] |= 0x20;
```

#### Clearing a Single Bit
```c
// Clear bit N to 0
byte &= ~(1 << N);

// Example: Clear bit 2
data[offset] &= ~0x04;  // or: data[offset] &= 0xFB;
```

#### Toggling a Single Bit
```c
// Toggle bit N
byte ^= (1 << N);

// Example: Toggle bit 0
data[offset] ^= 0x01;
```

#### Multi-Bit Fields
```c
// Read 2-bit field at bits 0-1
uint8_t value = byte & 0x03;

// Write 2-bit field at bits 0-1 (preserving other bits)
byte = (byte & 0xFC) | (new_value & 0x03);

// Read 4-bit field at bits 4-7
uint8_t value = (byte >> 4) & 0x0F;

// Write 4-bit field at bits 4-7
byte = (byte & 0x0F) | ((new_value & 0x0F) << 4);
```

### Practical Examples

**Unlock specific outfits at 0x369:**
```c
// Only Desmond
data[0x369] = 0x10;

// Altair's Robes + Raiden
data[0x369] = 0x04 | 0x20;  // = 0x24

// Everything except Raiden
data[0x369] = 0x3F & ~0x20;  // = 0x1F

// Add Florentine Noble to existing unlocks
data[0x369] |= 0x01;
```

**Unlock specific achievements at 0x84:**
```c
// First 4 story achievements
data[0x84] = 0x01 | 0x02 | 0x04 | 0x08;  // = 0x0F

// All story achievements in byte 0x84
data[0x84] = 0xFF;

// Check if player has beaten the game (REQUIESCAT IN PACE)
bool beat_game = (data[0x85] & 0x04) != 0;
```

---

## Ghidra Function References

### Bitfield Access Functions

| Address | Function | Bitfield Accessed | Operation |
|---------|----------|-------------------|-----------|
| 0x00ACF240 | FUN_00acf240 | Costume (0x369) | Settings constructor, initializes costume state |
| 0x00ACF240 | FUN_00acf240 | Brightness (0x195) | Full settings initialization |
| 0x004391F0 | FUN_004391f0 | Subtitles (0x63) | Toggle handler |
| 0x00439250 | FUN_00439250 | Subtitles (0x63) | State reader |
| 0x0084CA20 | FUN_0084ca20 | DLC Sync (0x9D) | DLC flag constructor |
| 0x0084CB60 | FUN_0084cb60 | DLC Sync (0x9D) | DLC sync handler |

### Bitwise Operation Patterns in Ghidra

**Common patterns found in decompiled code:**

```c
// Pattern 1: Single bit check (FUN_00ACF240)
if ((data[0x369] & 0x01) != 0) {
    // Florentine Noble unlocked
}

// Pattern 2: Setting multiple bits
data[0x369] = data[0x369] | 0x07;  // Unlock all Uplay costumes

// Pattern 3: 2-bit field access (Action Camera)
action_level = data[0x183] & 0x03;

// Pattern 4: Boolean conversion
bool enabled = (data[offset] & mask) != 0;
```

### Section Parser Functions

| Address | Function | Section | Bitfields Parsed |
|---------|----------|---------|------------------|
| 0x0046D710 | FUN_0046d710 | Section 1 | Platform flags at 0x0E |
| 0x01712CA0 | FUN_01712ca0 | Section 2 | Costume, DLC flags |
| 0x017108E0 | FUN_017108e0 | Section 3 | Achievement bitfield |
| 0x01B024F0 | FUN_01b024f0 | Section 2 | Settings parsing |
| 0x01BDE7C0 | FUN_01bde7c0 | Section 2/3 | Large structure deserializer |

---

## Summary Tables

### All Bitfields Quick Reference

| Section | Offset | Size | Bits Used | Name | Confidence |
|---------|--------|------|-----------|------|------------|
| 1, 2, 3 | 0x0E-0x0F | 2 bytes | 16 | Platform Flags | [H] |
| 2 | 0x183 | 1 byte | 2 | Action Camera Frequency | [M] |
| 2 | 0x369* | 1 byte | 6 | Costume Bitfield (VALUE byte within 18-byte record at 0x368) | [P] |
| 2 | 0x516-0x519 | 4 bytes | 4x8 | DLC/Update Flags | [M] |
| 3 | 0x84-0x8A | 7 bytes | 53 | Achievement Bitfield (PC) | [P] |

*Note: The costume bitfield at 0x369 is the VALUE byte within an 18-byte property record starting at 0x368. It uses Type 0x00 (bitfield/complex), not Type 0x0E (boolean).

### Mask Quick Reference

| Bitfield | All Bits Set | Description |
|----------|--------------|-------------|
| Platform Flags | 0x050C (PC) / 0x0508 (PS3) | Platform-specific |
| Action Camera | 0x03 | Maximum frequency |
| Costume | 0x3F | All costumes unlocked |
| Achievement | `FF FF FF FF FF FF 1F` | All 53 achievements |

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-27 | Initial complete bitfield documentation |

---

## Source Documents

This reference consolidates bitfield information from:

1. `/docs/OPTIONS_FIELD_REFERENCE.md` - Field definitions and evidence
2. `/docs/SECTION_DATA_STRUCTURES.md` - C structure definitions
3. `/docs/ACB_OPTIONS_Mapping_Reference.md` - Bitwise operations guide
4. `/docs/ACB_OPTIONS_Menu_Mapping_Reference.md` - Menu value mappings
5. `/docs/ACB_Functions_Reference.md` - Ghidra function analysis

---

**End of Document**
