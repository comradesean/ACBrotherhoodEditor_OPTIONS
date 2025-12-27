# AC Brotherhood OPTIONS - Cross-Section Relationships

**Document Version:** 1.0
**Date:** 2025-12-27
**Status:** Comprehensive Analysis of Inter-Section Dependencies

This document details the relationships and dependencies between the four sections (PC: 3 sections, PS3: 4 sections) of the OPTIONS file format.

---

## Section Identification System

All sections share a common header pattern that enables identification and validation:

### Section Type Hashes (Offset 0x0A-0x0D)

| Section | Hash at 0x0A | Purpose |
|---------|--------------|---------|
| Section 1 | `0xBDBE3B52` | System/Profile type identifier |
| Section 2 | `0x305AE1A8` | Game Settings type identifier |
| Section 3 | `0xC9876D66` | Game Progress type identifier |

These hashes serve as internal type markers, complementing the header's Field2 magic numbers (0xC5, 0x11FACE11, 0x21EFFE22).

### Platform Flags (Offset 0x0E-0x0F)

| Platform | Flags Value | Byte Order |
|----------|-------------|------------|
| PC | `0x050C` (bytes: 0C 05) | Little-endian |
| PS3 | `0x0508` (bytes: 08 05) | Little-endian |

All three sections use identical platform flags within the same file.

---

## Section Dependency Graph

```
┌─────────────────────────────────────────────────────────────────────┐
│                    OPTIONS File Structure                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────┐                                                │
│  │    Section 1     │                                                │
│  │  System/Profile  │                                                │
│  │                  │                                                │
│  │ • 0x51: Profile  │─────────────────────────────────────────┐      │
│  │   State Flag     │                                         │      │
│  │   (0x02 → 0x06)  │                                         │      │
│  └──────────────────┘                                         │      │
│                                                               │      │
│  ┌──────────────────┐                                         │      │
│  │    Section 2     │                                         │      │
│  │  Game Settings   │                                         │      │
│  │                  │                                         │      │
│  │ Unlock Records:  │                                         │      │
│  │ • 0x2D9 ─────────┼──→ Florentine Noble ──┐                 │      │
│  │ • 0x2EB ─────────┼──→ Armor of Altair ───┼─→ Costume      │      │
│  │ • 0x2FD ─────────┼──→ Altair's Robes ────┘   Bitfield     │      │
│  │ • 0x30F: Hellequin (MP, no costume)         @ 0x369       │      │
│  │                  │                                         │      │
│  │ Costume Bitfield │                                         │      │
│  │ @ 0x369         │                                         │      │
│  └──────────────────┘                                         │      │
│           │                                                   │      │
│           │ Uplay rewards link                                │      │
│           ▼                                                   │      │
│  ┌──────────────────┐                                         │      │
│  │    Section 3     │                                         │      │
│  │  Game Progress   │                                         │      │
│  │                  │                                         │      │
│  │ • 0x4E: Gun      │◄── 30-point Uplay reward                │      │
│  │   Capacity       │                                         │      │
│  │   Upgrade        │                                         │      │
│  │                  │                                         │      │
│  │ • 0x84-0x8A:     │                                         │      │
│  │   Achievements   │    (PC only)                            │      │
│  │   (53 bits)      │                                         │      │
│  │                  │                                         │      │
│  │ • 0x9D: DLC      │◄────────────────────────────────────────┘      │
│  │   Sync Flag      │    Correlates with S1:0x51                     │
│  └──────────────────┘                                                │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Detailed Relationships

### 1. Section 2 → Section 3: Uplay Reward Flow

The Uplay reward system spans both sections:

| Section 2 Unlock | Hash | Section 3 Effect | Section 2 Effect |
|------------------|------|------------------|------------------|
| 0x2D9: Florentine Noble | `0x0021D9D0` | None | 0x369 bit 0 |
| 0x2EB: Armor of Altair | `0x0036A2C4` | None | 0x369 bit 1 |
| 0x2FD: Altair's Robes | `0x0052C3A9` | None | 0x369 bit 2 |
| 0x30F: Hellequin MP | `0x000E8D04` | None | (MP character) |
| (Gun Capacity) | N/A | 0x4E = 0x01 | N/A (in S3) |

**Flow:**
1. User redeems Uplay reward
2. Game sets unlock record flag in Section 2
3. For costume rewards, costume bitfield at 0x369 is also set
4. Gun Capacity Upgrade (30-point reward) sets flag in Section 3

### 2. Section 2 Costume Bitfield → Uplay Unlock Records

Direct correlation between costume bits and unlock records:

| Bit | Costume | Corresponding Unlock Record |
|-----|---------|----------------------------|
| 0 (0x01) | Florentine Noble Attire | 0x2D9 |
| 1 (0x02) | Armor of Altair | 0x2EB |
| 2 (0x04) | Altair's Robes | 0x2FD |
| 3 (0x08) | Drachen Armor | (Preorder, no unlock record) |
| 4 (0x10) | Desmond | (In-game unlock, no record) |
| 5 (0x20) | Raiden | (In-game unlock, no record) |

### 3. Section 1 ↔ Section 3: Profile State Correlation

The Profile State Flag in Section 1 correlates with Section 3's DLC Sync Flag:

| State | S1:0x51 | S3:0x9D | S3:0x4E | S3:0x84-0x8A |
|-------|---------|---------|---------|--------------|
| Base game | 0x02 | 0x00 | 0x00 | All zeros |
| All rewards unlocked | 0x06 | 0x01 | 0x01 | All 0xFF...1F |

**Observation:** When any field shows the "all rewards" state, all related fields are also in that state. This suggests a synchronized unlock mechanism.

---

## 24-File Validation Results

Analysis of 24 reference OPTIONS files (21 language variants + 3 reward states):

### Section 1 Invariance

All 21 language files are **byte-for-byte identical** for Section 1, with only one exception:
- Offset 0x51 varies between 0x02 (base) and 0x06 (all rewards)

This proves Section 1 does NOT contain language-dependent data.

### Section 2 Variation Points

Only **11 bytes** vary across all 21 language files:

| Offset | Purpose | Variation |
|--------|---------|-----------|
| 0x8E-0x91 | Audio Language Index | 1-20 based on language |
| 0x92-0x95 | Audio Language Hash | Per-language hash |
| 0xA7-0xAA | Subtitle Language Index | 1-20 based on language |
| 0xAB-0xAE | Subtitle Language Hash | Per-language hash |

All other 1299 bytes are identical across languages.

### Section 3 Binary States

Section 3 shows only two distinct states across all 24 files:

| State | Count | 0x4E | 0x84-0x8A | 0x9D |
|-------|-------|------|-----------|------|
| Base | 21 | 0x00 | 00 00 00 00 00 00 00 | 0x00 |
| All Rewards | 3 | 0x01 | FF FF FF FF FF FF 1F | 0x01 |

This perfect binary correlation proves these three fields are part of the same "rewards/progress unlocked" system.

---

## Section Independence

Despite the relationships documented above, sections are largely independent:

### Checksum Independence

Each section has its own checksum at header offset 0x28:
- No cross-section checksums exist
- Modifying one section does not require updating another section's checksum

### Parsing Order

Sections are parsed sequentially:
1. Section 1 (System/Profile)
2. Section 2 (Game Settings)
3. Section 3 (Game Progress)
4. Section 4 (PS3 Controller Mappings) - PS3 only

No section's parsing depends on another section's content.

### Independent Modification

Each section can theoretically be modified independently:
1. Decompress target section
2. Modify decompressed data
3. Recompress section
4. Update section checksum
5. Rebuild file

However, maintaining logical consistency (e.g., unlock records matching costume bits) requires coordinated changes.

---

## PS3-Specific Considerations

### Section 3 Size Difference

| Platform | Size | Achievement Storage |
|----------|------|---------------------|
| PC | 162 bytes | Embedded 7-byte bitfield |
| PS3 | 119 bytes | External (PSN Trophy API) |

The 43-byte difference is entirely due to PC embedding achievement data while PS3 relies on external trophy system.

### DLC Sync Flag Offset

| Platform | DLC Sync Flag Offset |
|----------|---------------------|
| PC | 0x9D |
| PS3 | 0x5A |

This offset difference is a consequence of the PS3's smaller Section 3 (no achievement region).

### Section 4 (PS3 Only)

Section 4 is completely independent:
- Contains DualShock 3 button mappings
- No references to/from other sections
- 1903 bytes of controller configuration

---

## Cross-Section Validation Recommendations

When modifying OPTIONS files, validate:

1. **Costume Consistency:** If modifying unlock record at 0x2D9/0x2EB/0x2FD, also update costume bitfield at 0x369
2. **Uplay Gun Upgrade:** Section 3 offset 0x4E should reflect 30-point Uplay reward status
3. **Profile State:** If setting Section 3 to "all rewards," consider updating Section 1:0x51 to 0x06
4. **Platform Flags:** All sections should have matching platform flags (0x050C or 0x0508)
5. **Checksums:** Update each modified section's checksum independently

---

## Summary Table

| Relationship | Source | Target | Type |
|--------------|--------|--------|------|
| Uplay Costume → Bitfield | S2:0x2D9/2EB/2FD | S2:0x369 | Redundant state |
| Uplay Gun → Progress | (Uplay) | S3:0x4E | Direct flag |
| Profile State ↔ DLC Sync | S1:0x51 | S3:0x9D | Correlated state |
| Language Index → Hash | S2:0x8E/0xA7 | S2:0x92/0xAB | Lookup pair |
| Platform Flags | All sections | Header 0x0E | Consistent value |
| Section Hashes | All sections | Header 0x0A | Type identifier |

---

**End of Document**
