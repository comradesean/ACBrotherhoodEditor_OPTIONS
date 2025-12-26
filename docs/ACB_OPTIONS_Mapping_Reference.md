# Assassin's Creed Brotherhood OPTIONS Mapping Reference

## Table of Contents
- [Section 1: Unknown](#section-1-unknown)
- [Section 2: Templar Lairs & Costumes](#section-2-templar-lairs--costumes)
- [Section 3: Misc & Achievements](#section-3-misc--achievements)
- [Bitwise Operations Guide](#bitwise-operations-guide)

---

## Section 1: Unknown

### Offset 0x51
| Address | Value Change | Description |
|---------|-------------|-------------|
| `0x51` | `0x02` → `0x06` | #UNKNOWN |

---

## Section 2: Templar Lairs & Costumes

### Display Settings

#### Subtitles Toggle
| Address | Value Change | Description |
|---------|-------------|-------------|
| `0x63` | `0x00` → `0x01` | Subtitles OFF → ON |

#### Language Configuration
| Address Range | Type | Description |
|---------|------|-------------|
| `0x8e`–`0x95` | Audio | Language selection (8 bytes) |
| `0xa7`–`0xae` | Subtitle | Language selection (8 bytes) |

*Refer to language_table for specific language codes*

### Unlockable Content

#### Templar Lair Unlocks
| Address | Value Change | Description |
|---------|-------------|-------------|
| `0x291` | `0x00` → `0x01` | Mercati di Traiano (Trajan's Market) - "Shopaholic" |
| `0x2a3` | `0x00` → `0x01` | Tivoli Aqueducts - "Liquid Gold" |

#### Costume Unlocks
**Address:** `0x369` (Bitwise Operator)

| Binary | Hex Value | Outfit Name |
|--------|-----|--------|
| `000001` | `0x01` | Florentine Noble Attire |
| `000010` | `0x02` | Armor of Altair |
| `000100` | `0x04` | Altair's Robes |
| `001000` | `0x08` | Drachen Armor |
| `010000` | `0x10` | Desmond |
| `100000` | `0x20` | Raiden |
| `111111` | `0x3f` | **ALL OUTFITS** |

#### Unknown Toggles
| Address | Value Change | Description |
|---------|-------------|-------------|
| `0x2d9` | `0x00` → `0x01` | UNKNOWN |
| `0x2eb` | `0x00` → `0x01` | UNKNOWN |
| `0x2fd` | `0x00` → `0x01` | UNKNOWN |
| `0x30f` | `0x00` → `0x01` | UNKNOWN |
| `0x516` | `0x00` → `0x01` | UNKNOWN |
| `0x517` | `0x00` → `0x01` | UNKNOWN |
| `0x518` | `0x00` → `0x01` | UNKNOWN |
| `0x519` | `0x00` → `0x01` | UNKNOWN |

*Note: Multiplayer characters (Harlequin, Hellequin, or Officer) are all UNKNOWN.*

---

## Section 3: Misc & Achievements

### Equipment Upgrade & DLC
| Address | Value Change | Description |
|---------|-------------|-------------|
| `0x4e` | `0x00` → `0x01` | Gun Capacity Upgrade |
| `0x9D` | `0x00` → `0x01` | UNKNOWN DLC (Prevents load when disabled - possibly Copernicus Conspiracy?)  (probably not: Da Vinci Disappearance?) |

### Achievement Unlocks (Bitwise)
**Address Range:** `0x84` → `0x8a` (7 bytes) 

#### Address `0x84`
| Binary | Hex Value | Achievement Name |
|--------|-----|-------------|
| `00000001` | `0x01` | TECHNICAL DIFFICULTIES |
| `00000010` | `0x02` | BATTLE WOUNDS |
| `00000100` | `0x04` | SANCTUARY! SANCTUARY |
| `00001000` | `0x08` | ROME IN RUINS |
| `00010000` | `0x10` | FIXER-UPPER |
| `00100000` | `0x20` | PRINCIPESSA IN ANOTHER CASTELLO |
| `01000000` | `0x40` | FUNDRAISER |
| `10000000` | `0x80` | FORGET PARIS |

#### Address `0x85`
| Binary | Hex Value | Achievement Name |
|--------|-----|-------------|
| `00000001` | `0x01` | BLOODY SUNDAY |
| `00000010` | `0x02` | VITTORIA AGLI ASSASSINI |
| `00000100` | `0x04` | REQUIESCAT IN PACE |
| `00001000` | `0x08` | A KNIFE TO THE HEART |
| `00010000` | `0x10` | PERFECT RECALL |
| `00100000` | `0x20` | DEJA VU |
| `01000000` | `0x40` | UNDERTAKER 2.0 |
| `10000000` | `0x80` | GOLDEN BOY |

#### Address `0x86`
| Binary | Hex Value | Achievement Name |
|--------|-----|-------------|
| `00000001` | `0x01` | GLADIATOR |
| `00000010` | `0x02` | PLUMBER |
| `00000100` | `0x04` | ONE-MAN WRECKING CREW |
| `00001000` | `0x08` | AMEN |
| `00010000` | `0x10` | BANG! |
| `00100000` | `0x20` | SPLASH! |
| `01000000` | `0x40` | BOOM! |
| `10000000` | `0x80` | KABOOM! |

#### Address `0x87`
| Binary | Hex Value | Achievement Name |
|--------|-----|-------------|
| `00000001` | `0x01` | HOME IMPROVEMENT |
| `00000010` | `0x02` | TOWER DEFENSE |
| `00000100` | `0x04` | SHOW OFF |
| `00001000` | `0x08` | .. .- -- .- .-.. .. ...- . |
| `00010000` | `0x10` | PERFECTIONIST |
| `00100000` | `0x20` | BROTHERHOOD |
| `01000000` | `0x40` | WELCOME TO THE BROTHERHOOD |
| `10000000` | `0x80` | CAPTURE THE FLAG |

#### Address `0x88`
| Binary | Hex Value | Achievement Name |
|--------|-----|-------------|
| `00000001` | `0x01` | IN MEMORIAM |
| `00000010` | `0x02` | DUST TO DUST |
| `00000100` | `0x04` | SERIAL KILLER |
| `00001000` | `0x08` | SPRING CLEANING |
| `00010000` | `0x10` | YOUR WISH IS GRANTED |
| `00100000` | `0x20` | FLY LIKE AN EAGLE |
| `01000000` | `0x40` | THE GLOVES COME OFF |
| `10000000` | `0x80` | MAILER DAEMON |

#### Address `0x89`
| Binary | Hex Value | Achievement Name |
|--------|-----|-------------|
| `00000001` | `0x01` | ROME GLOBAL ECONOMY BRONZE MEDAL |
| `00000010` | `0x02` | ROME GLOBAL ECONOMY SILVER MEDAL |
| `00000100` | `0x04` | ROME GLOBAL ECONOMY GOLD MEDAL |
| `00001000` | `0x08` | STRONG-ARM |
| `00010000` | `0x10` | HIGH ROLLER |
| `00100000` | `0x20` | IL PRINCIPE |
| `01000000` | `0x40` | AIRSTRIKE |
| `10000000` | `0x80` | GPS |

#### Address `0x8A`
| Binary | Hex Value | Achievement Name |
|--------|-----|-------------|
| `00000001` | `0x01` | CLOWNING AROUND |
| `00000010` | `0x02` | SPECIAL DELIVERY |
| `00000100` | `0x04` | GRAND THEFT DRESSAGE |
| `00001000` | `0x08` | GOING UP |
| `00010000` | `0x10` | EASY COME, EASY GO |

---

## Bitwise Operations Guide

### Understanding Bitwise Flags

Each byte can store 8 separate on/off flags using bits:
```
Bit Position:  7  6  5  4  3  2  1  0
Binary:        0  0  0  0  0  0  0  0
Hex Values:   80 40 20 10 08 04 02 01
```

### How to Calculate Values

**To enable multiple flags:** Add their hex values together
- Example: Enable bits 0, 2, and 4 → `0x01 + 0x04 + 0x10 = 0x15`

**To enable all flags in a byte:** Set to `0xFF` (binary: 11111111)

**To disable a specific flag:** Subtract its value or use bitwise AND with inverse

### Practical Examples

**Unlock specific outfits at 0x369:**
- Only Desmond: `0x10`
- Altair's Robes + Raiden: `0x04 + 0x20 = 0x24`
- Everything except Raiden: `0x3F - 0x20 = 0x1F`

**Unlock specific achievements at 0x84:**
- First 4 achievements: `0x01 + 0x02 + 0x04 + 0x08 = 0x0F`
- All achievements: `0xFF`

---

*Last updated: 12/25/2025  
*Game: Assassin's Creed Brotherhood*  
*All addresses are hexadecimal offsets from their section's base*