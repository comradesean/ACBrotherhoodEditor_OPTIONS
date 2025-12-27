# Hex Mapping Configuration

## General Settings

| Setting | Address | Value Range | Notes |
|---------|---------|-------------|-------|
| **Action Camera Frequency** | `0x183` | `0x00` → `0x03` | |
| **SFX Volume** | `0xEA` - `0xED` | See volume table below | 4-byte float |
| **Voice Volume** | `0xD5` - `0xD8` | Same pattern as SFX | 4-byte float |
| **Music Volume** | `0xC0` - `0xC3` | Same pattern as SFX | 4-byte float |
| **Brightness** | `0x195` | `0x01` → `0x10` | 10 levels |
| **Blood Toggle** | `0x1A7` | Boolean | On/Off |
| **Subtitles Toggle** | `0x63` | Boolean | On/Off |

### Volume Mapping (SFX/Voice/Music)
**4-byte float, little-endian**

| Level | Hex Value | Decimal (dB) |
|-------|-----------|--------------|
| 10 | `0x00 00 00 00` | 0.0 (Max) |
| 9 | `0x44 47 6A BF` | -0.916 |
| 8 | `0xF0 16 F8 BF` | -1.938 |
| 7 | `0x46 46 46 C0` | -3.098 |
| 6 | `0xB2 FB 8D C0` | -4.437 |
| 5 | `0xC0 A8 C0 C0` | -6.020 |
| 4 | `0x7C AE FE C0` | -7.958 |
| 3 | `0x39 52 27 C1` | -10.457 |
| 2 | `0x9E AB 5F C1` | -13.979 |
| 1 | `0xFF FF 9F C1` | -19.999 |
| 0 | `0x00 00 C0 C2` | -96.0 (Mute) |

## Controls

### Camera Inversion

| Setting | Address | Type |
|---------|---------|------|
| **3rd Person - Invert Y Look** | `0x14D` | Boolean |
| **3rd Person - Invert X Look** | `0x13B` | Boolean |
| **1st Person - Invert Y Look** | `0x171` | Boolean |
| **1st Person - Invert X Look** | `0x15F` | Boolean |
| **Invert Cannon X** | `0x1CB` | Boolean |
| **Invert Cannon Y** | `0x1DD` | Boolean |

### Look Sensitivity

| Setting | Address | Notes |
|---------|---------|-------|
| **Y Look Sensitivity** | `0x126` - `0x129` | 4-byte float (see table below) |
| **X Look Sensitivity** | `0x111` - `0x114` | Same pattern as Y sensitivity |

#### Sensitivity Mapping
**4-byte float, little-endian**

| Level | Hex Value | Multiplier |
|-------|-----------|------------|
| 10 (Max) | `0x00 00 00 40` | 2.0x |
| 9 | `0x66 66 E6 3F` | 1.8x |
| 8 | `0xCD CC CC 3F` | 1.6x |
| 7 | `0x33 33 B3 3F` | 1.4x |
| 6 | `0x9A 99 99 3F` | 1.2x |
| 5 (Default) | `0x00 00 80 3F` | 1.0x |
| 4 | `0xCD CC 4C 3F` | 0.8x |
| 3 | `0x33 33 33 3F` | 0.7x |
| 2 | `0x9A 99 19 3F` | 0.6x |
| 1 (Min) | `0x00 00 00 3F` | 0.5x |

**Pattern:**
- Levels 1-4: Increment by 0.1x (0.5 → 0.8)
- Level 5: 1.0x baseline (jump of 0.2)
- Levels 6-10: Increment by 0.2x (1.2 → 2.0)
- **Range:** 0.5x to 2.0x (50% to 200% of base sensitivity)

### Other Controls

| Setting | Address | Values | Notes |
|---------|---------|--------|-------|
| **Flying Machine** | `0x1B9` | `0x00` = Normal<br>`0x01` = Inverted | |
| **Vibration** | `0xFF` | Boolean | On/Off |

## HUD Settings

| Setting | Address | Type |
|---------|---------|------|
| **Health Meter** | `0x1EF` | Boolean |
| **Controls** | `0x201` | Boolean |
| **Updates** | `0x213` | Boolean |
| **Weapon** | `0x225` | Boolean |
| **Tutorial** | `0x27F` | Boolean |
| **SSI** | `0x26D` | Boolean |
| **Money** | `0x249` | Boolean |
| **Mini-Map** | `0x237` | Boolean |

---

## Unlock Records (18-byte Structure)

Section 2 contains 18-byte records for unlockable content. Each record follows this structure:

| Offset | Field | Size | Description |
|--------|-------|------|-------------|
| +0x00 | Unlock Flag | 1 byte | `0x00` = locked, `0x01` = unlocked |
| +0x01 | Type | 1 byte | Category identifier (e.g., `0x0E` for rewards) |
| +0x02 | Reserved/Hash Prefix | 4 bytes | First 3 bytes zeros, 4th byte contains hash-related data (values like 0xCC, 0x8F, 0x9F observed) |
| +0x06 | Content Hash | 4 bytes | Little-endian hash identifying the content |
| +0x0A | Padding | 8 bytes | Zeros |

### Known Unlock Records

| Name | Address | Hash | Status |
|------|---------|------|--------|
| **Templar Lair 1** (Trajan Market) | `0x291` | `0x00788F42` | Documented |
| **Templar Lair 2** (Aqueduct) | `0x2A3` | `0x006FF456` | Documented |
| **Uplay Reward #1** | `0x2D9` | `0x0021D9D0` | Likely Florentine Noble Attire |
| **Uplay Reward #2** | `0x2EB` | `0x0036A2C4` | Likely Armor of Altair |
| **Uplay Reward #3** | `0x2FD` | `0x0052C3A9` | Likely Altair's Robes |
| **Uplay Reward #4** | `0x30F` | `0x000E8D04` | Likely Hellequin MP Character |
| **Costume Bitfield** | `0x369` | N/A | Multiple costume flags |

### Uplay Rewards Context

The following Uplay rewards exist for AC Brotherhood:
- Theme (10 pts)
- Florentine Noble Attire (20 pts) - Costume
- Armor of Altair (20 pts) - Armor
- Altair's Robes (20 pts) - Costume
- Gun Capacity Upgrade (30 pts) - Upgrade (in Section 3)
- Hellequin MP Character (40 pts) - Multiplayer

---

## DLC/Update Flags

| Setting | Address | Type | Description |
|---------|---------|------|-------------|
| **Update Flag #1** | `0x516` | Boolean | Likely Animus Project Update 1.0 |
| **Update Flag #2** | `0x517` | Boolean | Likely Animus Project Update 2.0 |
| **Update Flag #3** | `0x518` | Boolean | Likely Animus Project Update 3.0 |
| **Update Flag #4** | `0x519` | Boolean | Likely Da Vinci Disappearance DLC |

These 4 consecutive bytes are located at the end of Section 2 data and are set to `0x01` when the corresponding content is available.

### Free Content Updates (Animus Project Updates)

- **APU 1.0**: Added Mont Saint-Michel map
- **APU 2.0**: Added Pienza map
- **APU 3.0**: Added Alhambra map + Dama Rossa, Knight, Marquis, Pariah characters

---

## Technical Notes

### Data Types
- **Boolean**: Single byte (`0x00` = Off, `0x01` = On)
- **Float**: 4-byte IEEE 754 floating point, little-endian format
- **Range**: Single byte with specified min/max values

### Byte Order
All multi-byte values use **little-endian** byte order (least significant byte first).

### Volume Scale
Audio volumes use a logarithmic decibel (dB) scale:
- **0 dB** = Maximum volume (100%)
- **-96 dB** = Effective silence (mute)
- Each step reduces volume non-linearly for perceptual consistency
