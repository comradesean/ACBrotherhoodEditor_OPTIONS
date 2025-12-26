# Assassin's Creed Brotherhood - Language System Analysis

## Executive Summary

This document details the reverse engineering analysis of the language configuration system in Assassin's Creed Brotherhood. The research identified the structure, storage, and usage of language data including a unique hash-based identification system used for save file persistence.

---

## Table of Contents

1. [Language Table Structure](#language-table-structure)
2. [Memory Layout](#memory-layout)
3. [Function Analysis](#function-analysis)
4. [Workflow Diagrams](#workflow-diagrams)
5. [Registry System](#registry-system)
6. [Save File Integration](#save-file-integration)
7. [Localization File Loading](#localization-file-loading)

---

## Language Table Structure

### Base Structure Definition

```c
// Each language entry is 8 bytes
struct LanguageEntry {
    uint32_t language_index;    // Language ID (1-21)
    uint32_t language_hash;     // Unique hash identifier for persistence
};
```

### Complete Language Table

**Base Address:** `0x0298a780`  
**Entry Size:** 8 bytes  
**Total Entries:** 22 (including header and reserved entries)

| Offset       | Index (Dec) | Index (Hex) | Hash Value   | Language              |
|--------------|-------------|-------------|--------------|-----------------------|
| 0x0298a780   | 0           | 0x00000000  | 0x480ED55E   | Header/Unknown        |
| 0x0298a788   | 1           | 0x01000000  | 0xB597CC50   | English               |
| 0x0298a790   | 2           | 0x02000000  | 0x90CC0F3C   | French                |
| 0x0298a798   | 3           | 0x03000000  | 0x81605748   | Spanish               |
| 0x0298a7a0   | 4           | 0x04000000  | 0x7B357543   | Polish                |
| 0x0298a7a8   | 5           | 0x05000000  | 0x6F424E31   | German                |
| 0x0298a7b0   | 6           | 0x06000000  | 0xA1B2D787   | (Reserved/Unused)     |
| 0x0298a7b8   | 7           | 0x07000000  | 0x393123C6   | Hungarian             |
| 0x0298a7c0   | 8           | 0x08000000  | 0x7AFCF62B   | Italian               |
| 0x0298a7c8   | 9           | 0x09000000  | 0xF849E0B1   | Japanese              |
| 0x0298a7d0   | 10          | 0x0A000000  | 0x30316A2C   | Czech                 |
| 0x0298a7d8   | 11          | 0x0B000000  | 0x0DCB2F02   | Korean                |
| 0x0298a7e0   | 12          | 0x0C000000  | 0xC0642997   | Russian               |
| 0x0298a7e8   | 13          | 0x0D000000  | 0x3134CDDB   | Dutch                 |
| 0x0298a7f0   | 14          | 0x0E000000  | 0x1C030BCE   | Danish                |
| 0x0298a7f8   | 15          | 0x0F000000  | 0x1C90AD69   | Norwegian             |
| 0x0298a800   | 16          | 0x10000000  | 0x9D166FCF   | Swedish               |
| 0x0298a808   | 17          | 0x11000000  | 0x3F0E4112   | Portuguese            |
| 0x0298a810   | 18          | 0x12000000  | 0xDCD2A3CD   | Turkish               |
| 0x0298a818   | 19          | 0x13000000  | 0x4409CD43   | SimplifiedChinese     |
| 0x0298a820   | 20          | 0x14000000  | 0x87DA38CF   | TraditionalChinese    |
| 0x0298a828   | 21          | 0x15000000  | 0x85B73887   | Unknown/Extra         |

**Note:** Values shown in little-endian format as they appear in binary.

---

## Memory Layout

### Language Table Pointer Structure

**Address:** `0x0298a830`

```
Offset    | Content                    | Description
----------|----------------------------|----------------------------------
0x0298a830| 80 a7 98 02               | Pointer to DAT_0298a780 (language table)
0x0298a834| e3 13 ad 2d               | Language System Registry ID (0x2DAD13E3)
0x0298a838| 16 00 00 00               | Unknown (possibly table size)
```

### Global Language Storage

Three global variables store the current language index:

| Address      | Variable Name  | Purpose                           |
|--------------|----------------|-----------------------------------|
| 0x0298a840   | DAT_0298a840   | Primary language index            |
| 0x0298a844   | DAT_0298a844   | Secondary language index          |
| 0x0298a848   | DAT_0298a848   | Tertiary language index           |

---

## Function Analysis

### 1. Language Initialization Chain

#### FUN_01ae38b0 - Language Table Registration
**Address:** `0x01ae38b0`

```c
void FUN_01ae38b0(void)
{
  FUN_01b005e0(&PTR_DAT_0298a830, 1);
  return;
}
```

**Purpose:** Entry point for language system initialization  
**Called From:** `FUN_01b7edf0` (Engine::Init::RegisterSystemClasses)  
**Parameters:** 
- Pointer to language table pointer structure
- Flag: 1 (enable registration)

---

#### FUN_01b005e0 - Language System Setup
**Address:** `0x01b005e0`

```c
int FUN_01b005e0(int param_1, char param_2)
{
  int iVar1;
  
  if (param_2 != '\0') {
    FUN_01b015b0(&param_1, 0);
  }
  iVar1 = param_1;
  FUN_01b01f00(*(undefined4 *)(param_1 + 4), param_1, DAT_02a622a8);
  return iVar1;
}
```

**Purpose:** Initializes language table and registers with global system  
**Key Actions:**
1. Calls `FUN_01b015b0` if param_2 is non-zero (array management)
2. Calls `FUN_01b01f00` with:
   - Registry ID: `0x2DAD13E3` (from offset +4)
   - Table pointer: `param_1`
   - Memory context: `DAT_02a622a8`

---

#### FUN_01b01f00 - Registry Registration
**Address:** `0x01b01f00`

```c
void FUN_01b01f00(undefined4 param_1, undefined4 param_2, undefined4 param_3)
{
  undefined4 *puVar1;
  void *local_10;
  undefined1 *puStack_c;
  undefined4 local_8;
  
  local_8 = 0xffffffff;
  puStack_c = &LAB_023c18f8;
  local_10 = ExceptionList;
  ExceptionList = &local_10;
  FUN_01b1d7c0(param_3);
  local_8 = 0;
  puVar1 = (undefined4 *)FUN_0056ce70(&param_1);
  *puVar1 = param_2;
  local_8 = 0xffffffff;
  FUN_01b1d7c0(0);
  ExceptionList = local_10;
  return;
}
```

**Purpose:** Registers language table in global registry  
**Registry ID:** `0x2DAD13E3`  
**Key Actions:**
1. Sets up exception handling
2. Calls `FUN_0056ce70` to get/create registry entry
3. Stores language table pointer in registry

---

### 2. Language Detection and Configuration

#### FUN_0040ad40 - Registry Language Detection
**Address:** `0x0040ad40`

```c
int FUN_0040ad40(void)
{
  LSTATUS LVar1;
  int iVar2;
  int iVar3;
  BYTE local_10c [256];
  DWORD local_c;
  HKEY local_8;
  
  local_c = 0x100;
  iVar3 = 1;
  LVar1 = RegOpenKeyExA((HKEY)0x80000002,
                        "SOFTWARE\\Ubisoft\\Assassin's Creed Brotherhood",
                        0, 0x20019, &local_8);
  if (LVar1 == 0) {
    LVar1 = RegQueryValueExA(local_8, "Language", 
                             (LPDWORD)0x0, (LPDWORD)0x0, 
                             local_10c, &local_c);
    if (LVar1 == 0) {
      // String comparisons for each language...
      // Returns corresponding index (1-20)
    }
    RegCloseKey(local_8);
  }
  return iVar3;
}
```

**Purpose:** Reads language setting from Windows Registry  
**Registry Key:** `HKEY_LOCAL_MACHINE\SOFTWARE\Ubisoft\Assassin's Creed Brotherhood`  
**Registry Value:** `"Language"`  
**Returns:** Language index (1-20), defaults to 1 (English)

**Language String Mappings:**
```c
"English"            → 1  (0x01)
"French"             → 2  (0x02)
"Spanish"            → 3  (0x03)
"Polish"             → 4  (0x04)
"German"             → 5  (0x05)
"Hungarian"          → 7  (0x07)
"Italian"            → 8  (0x08)
"Japanese"           → 9  (0x09)
"Czech"              → 10 (0x0A)
"Korean"             → 11 (0x0B)
"Russian"            → 12 (0x0C)
"Dutch"              → 13 (0x0D)
"Danish"             → 14 (0x0E)
"Norwegian"          → 15 (0x0F)
"Swedish"            → 16 (0x10)
"Portuguese"         → 17 (0x11)
"Turkish"            → 18 (0x12)
"Chinese"            → 19 (0x13) // SimplifiedChinese
"SimplifiedChinese"  → 19 (0x13)
"TraditionalChinese" → 20 (0x14)
```

---

#### FUN_0040b120 - Language Index Distribution
**Address:** `0x0040b120`

```c
void FUN_0040b120(void)
{
  undefined4 uVar1;
  
  uVar1 = FUN_0040ad40();
  FUN_01ae3b10(uVar1);
  FUN_01ae3b20(uVar1);
  FUN_01ae3b00(uVar1);
  return;
}
```

**Purpose:** Retrieves language from registry and stores in global variables  
**Called From:** `FUN_0040bfd0` (early in game initialization)

---

#### FUN_01ae3b10, FUN_01ae3b20, FUN_01ae3b00 - Global Storage
**Addresses:** `0x01ae3b10`, `0x01ae3b20`, `0x01ae3b00`

```c
void FUN_01ae3b10(undefined4 param_1)
{
  DAT_0298a844 = param_1;
  return;
}

void FUN_01ae3b20(undefined4 param_1)
{
  DAT_0298a848 = param_1;
  return;
}

void FUN_01ae3b00(undefined4 param_1)
{
  DAT_0298a840 = param_1;
  return;
}
```

**Purpose:** Store language index in three global variables  
**Global Addresses:**
- `DAT_0298a844` - Primary language storage
- `DAT_0298a848` - Secondary language storage
- `DAT_0298a840` - Tertiary language storage

**Note:** Multiple storage locations likely used for different subsystems (UI, audio, subtitles, etc.)

---

### 3. Localization File Loading

#### FUN_0043d740 - Localization File Loader
**Address:** `0x0043d740`

```c
void FUN_0043d740(void)
{
  bool bVar1;
  char cVar2;
  undefined4 uVar3;
  uint uVar4;
  uint uVar5;
  char *_Src;
  char local_224 [256];
  char local_124 [256];
  uint *local_24;
  uint local_20;
  uint local_1c [2];
  byte local_12;
  byte local_11;
  
  _strncpy_s(local_224, 0x100, "localization.lang", 0xffffffff);
  _strncpy_s(local_124, 0x100, "localization.lang", 0xffffffff);
  
  uVar3 = FUN_01ae3ae0();
  switch(uVar3) {
  case 4:  // Russian
    _Src = "_rus";
    break;
  case 0xb:  // Korean
    _Src = "_kor";
    break;
  case 0x13:  // Simplified Chinese
    _Src = "_chs";
    break;
  case 0x14:  // Traditional Chinese
    _Src = "_chn";
    break;
  default:
    goto switchD_0043d7a9_caseD_5;
  }
  _strncat_s(local_124, 0x100, _Src, 0xffffffff);
  
switchD_0043d7a9_caseD_5:
  // Try to load language-specific file
  cVar2 = FUN_01b2bdf0(local_124, 1, 0);
  if ((cVar2 != '\0') || (cVar2 = FUN_01b2bdf0(local_224, 1, 0), cVar2 != '\0')) {
    FUN_01b2c050(&local_20);
    local_1c[0] = local_20 >> 0x18 | (local_20 & 0xff0000) >> 8 | 
                  (local_20 & 0xff00) << 8 | local_20 << 0x18;
    
    // Check magic header "LANG" (0x4c414e47)
    if (local_1c[0] == 0x4c414e47) {
      FUN_01b2c0b0(&local_11, 1);
      FUN_01b2c050(&local_20);
      local_24 = local_1c;
      DAT_027deef0 = local_20 >> 0x18 | (local_20 & 0xff0000) >> 8 | 
                     (local_20 & 0xff00) << 8 | local_20 << 0x18;
      DAT_027deef4 = (uint)local_11;
      // ... more file parsing ...
    }
  }
  // ... validation and fallback logic ...
}
```

**Purpose:** Loads localization file based on current language  
**Base Filename:** `"localization.lang"`  
**Language-Specific Suffixes:**
- Russian (4): `"localization.lang_rus"`
- Korean (11): `"localization.lang_kor"`
- Simplified Chinese (19): `"localization.lang_chs"`
- Traditional Chinese (20): `"localization.lang_chn"`

**File Format:**
```
Offset | Size | Description
-------|------|----------------------------------
0x00   | 4    | Magic header: "LANG" (0x4c414e47)
0x04   | 1    | Unknown byte
0x05   | 4    | Version/flags (big-endian)
0x09   | 1    | Language index
...    | ...  | Additional localization data
```

---

### 4. Save File Integration

#### FUN_01b09c10 - Save/Load Language Data
**Address:** `0x01b09c10`

```c
undefined4 __thiscall FUN_01b09c10(int param_1, uint param_2, 
                                   uint *param_3, byte *param_4)
{
  int *piVar1;
  byte *pbVar2;
  char cVar3;
  int iVar4;
  int *piVar5;
  uint uVar6;
  undefined1 *local_c;
  undefined4 local_8;
  
  pbVar2 = param_4;
  cVar3 = FUN_01b07940(param_4, 0, 0);
  if (cVar3 == '\0') {
    return 0;
  }
  
  iVar4 = FUN_01aff5e0(*(undefined4 *)(param_1 + 0xc));
  if (iVar4 == 0) {
    piVar5 = (int *)0x0;
  } else {
    piVar5 = (int *)FUN_01b003e0(param_2);
  }
  
  cVar3 = FUN_01b0d140(pbVar2);
  if (cVar3 == '\0') {
    return 0;
  }
  
  local_8 = 0;
  local_c = (undefined1 *)0x0;
  param_2 = *param_3;
  
  if (*(char *)(*(int *)(param_1 + 4) + 4) == '\0') {
    // SAVE MODE: Look up hash by index
    iVar4 = FUN_01b82560(param_2);  // Find index in table
    if (iVar4 == -1) {
      local_8 = 0xffffffff;
      param_2 = 0xffffffff;
    } else {
      // Access: table_base + (index * 8) + 4
      // This reads the HASH VALUE from the language table!
      local_8 = *(undefined4 *)(*piVar5 + 4 + iVar4 * 8);
      local_c = &DAT_025f9b50;
    }
  }
  
  // ... serialization code ...
  
  piVar1 = *(int **)(param_1 + 4);
  (**(code **)(*piVar1 + 8))("EnumValue");
  (**(code **)(*piVar1 + 0x84))(&param_2);
  (**(code **)(*piVar1 + 0x10))("EnumValue");
  
  if (*(int *)(param_1 + 0x58) == 0) {
    FUN_01b0e680("EnumName", local_c, &local_8);
  }
  
  if (*(char *)(*(int *)(param_1 + 4) + 4) != '\0') {
    // LOAD MODE: Look up index by hash
    if (piVar5 != (int *)0x0) {
      iVar4 = FUN_01b82590(local_8);  // Find by hash
      if (iVar4 == -1) {
        iVar4 = FUN_01b82560(param_2);
        if (iVar4 == -1) {
          if ((short)piVar5[2] == 0) {
            param_2 = 0;
          } else {
            param_2 = *(uint *)*piVar5;
          }
        }
      } else {
        // Access: table_base + (index * 8) + 0
        // This reads the INDEX from the language table!
        param_2 = *(uint *)(*piVar5 + iVar4 * 8);
      }
    }
    *param_3 = param_2;
  }
  
  // ... cleanup ...
  return 1;
}
```

**Purpose:** Serializes/deserializes language settings to/from save files  
**Registry ID Used:** `0x2DAD13E3`  
**Key Operations:**

**Save Mode:**
1. Takes language index as input
2. Looks up index in language table: `FUN_01b82560(index)`
3. Retrieves hash from table: `*(table_base + index*8 + 4)`
4. Writes hash to save file as "EnumName"

**Load Mode:**
1. Reads hash from save file
2. Looks up hash in table: `FUN_01b82590(hash)`
3. Retrieves language index from table: `*(table_base + found_index*8 + 0)`
4. Sets current language to that index

**Table Access Pattern:**
```c
// Language table entry structure (8 bytes)
struct LanguageEntry {
    uint32_t index;  // Offset +0
    uint32_t hash;   // Offset +4
};

// Access hash by index:
hash = *(table_base + (index * 8) + 4);

// Access index by position:
index = *(table_base + (position * 8) + 0);
```

---

#### FUN_00bc8b00 - Player Options Save Data
**Address:** `0x00bc8b00`

```c
void __thiscall FUN_00bc8b00(int param_1, int param_2)
{
  // ... setup code ...
  
  FUN_01b09c10(0x2dad13e3, param_1 + 8,  PTR_DAT_02841f14);
  FUN_01b09c10(0x2dad13e3, param_1 + 0xc, PTR_DAT_02841f18);
  FUN_01b09c10(0x2dad13e3, param_1 + 0x10, PTR_DAT_02841f1c);
  
  // ... many more save data operations ...
}
```

**Purpose:** Saves/loads player options including language settings  
**Registry ID:** `0x2DAD13E3` (used to access language table)  
**Language Data Offsets:**
- `param_1 + 8` - First language setting
- `param_1 + 0xc` - Second language setting
- `param_1 + 0x10` - Third language setting

**Note:** Three separate language settings stored, likely for:
1. UI/Menu language
2. Subtitle language
3. Audio/Voice language

---

### 5. Registry System Functions

#### FUN_0056ce70 - Registry Lookup/Create
**Address:** `0x0056ce70`

```c
int FUN_0056ce70(undefined4 *param_1)
{
  char cVar1;
  undefined1 local_88 [28];
  int local_6c;
  undefined1 local_4c [4];
  undefined1 local_48 [4];
  undefined1 local_44 [20];
  int local_30;
  undefined4 local_c;
  undefined4 local_8;
  
  FUN_0056a3d0(local_88, param_1);
  FUN_00569d80(local_48);
  cVar1 = FUN_00564750(local_44);
  if (cVar1 == '\0') {
    return local_6c + 4;
  }
  local_c = *param_1;
  local_8 = 0;
  FUN_0056c9b0(1, 0);
  FUN_00568fc0(local_4c, &local_c);
  return local_30 + 4;
}
```

**Purpose:** Global registry system for looking up registered objects by ID  
**Used By:** Language system, save system, and many other game systems  
**Key ID:** `0x2DAD13E3` - Language System Registry ID

---

#### FUN_01b003e0 - Language Table Retrieval
**Address:** `0x01b003e0`

**Purpose:** Retrieves language table pointer from registry using ID `0x2DAD13E3`  
**Returns:** Pointer to language table base (`0x0298a780`)

---

#### FUN_01b82560 - Index Lookup by Value
**Address:** `0x01b82560`

**Purpose:** Searches language table for entry matching given index/value  
**Returns:** Table position (-1 if not found)

---

#### FUN_01b82590 - Hash Lookup
**Address:** `0x01b82590`

**Purpose:** Searches language table for entry matching given hash  
**Returns:** Table position (-1 if not found)

---

## Workflow Diagrams

### 1. Game Startup Language Initialization

```
┌─────────────────────────────────────────────────────────────┐
│ Game Startup (FUN_0040bfd0)                                 │
└───────────────┬─────────────────────────────────────────────┘
                │
                ├─> FUN_0040b120() - Language Detection
                │   │
                │   ├─> FUN_0040ad40() - Read Windows Registry
                │   │   │
                │   │   └─> HKLM\SOFTWARE\Ubisoft\AC Brotherhood\Language
                │   │       Returns: Language Index (1-20)
                │   │
                │   ├─> FUN_01ae3b10(index) → DAT_0298a844
                │   ├─> FUN_01ae3b20(index) → DAT_0298a848
                │   └─> FUN_01ae3b00(index) → DAT_0298a840
                │
                ├─> Engine::Init::RegisterSystemClasses
                │   │
                │   └─> FUN_01ae38b0() - Language Table Registration
                │       │
                │       └─> FUN_01b005e0(&PTR_DAT_0298a830, 1)
                │           │
                │           └─> FUN_01b01f00(0x2DAD13E3, table_ptr, context)
                │               │
                │               └─> FUN_0056ce70(0x2DAD13E3)
                │                   Registers language table in global registry
                │
                └─> FUN_0043d740() - Load Localization Files
                    │
                    ├─> Determine filename based on language
                    │   • Base: "localization.lang"
                    │   • Russian: "localization.lang_rus"
                    │   • Korean: "localization.lang_kor"
                    │   • Chinese: "localization.lang_chs/chn"
                    │
                    ├─> FUN_01b2bdf0() - Open file
                    │
                    ├─> Verify magic header: "LANG" (0x4c414e47)
                    │
                    └─> Parse localization data
```

---

### 2. Save File Language Persistence

```
┌──────────────────────────────────────────────────────────────┐
│ SAVE OPERATION                                               │
└─────────────────┬────────────────────────────────────────────┘
                  │
                  ├─> FUN_00bc8b00() - PlayerOptionsSaveData
                  │   │
                  │   └─> FUN_01b09c10(0x2DAD13E3, offset, data)
                  │       │
                  │       ├─> Get current language index (e.g., 2 for French)
                  │       │
                  │       ├─> FUN_01b003e0(0x2DAD13E3)
                  │       │   Returns: Language table pointer (0x0298a780)
                  │       │
                  │       ├─> FUN_01b82560(index=2)
                  │       │   Searches table for index 2
                  │       │   Returns: Table position (1 for French)
                  │       │
                  │       ├─> Read hash from table:
                  │       │   hash = *(0x0298a780 + position*8 + 4)
                  │       │   hash = *(0x0298a790 + 4)
                  │       │   hash = 0x90CC0F3C (French hash)
                  │       │
                  │       └─> Write to save file:
                  │           <EnumName>0x90CC0F3C</EnumName>
                  │           <EnumValue>2</EnumValue>
                  │
                  └─> Save file written with language hash


┌──────────────────────────────────────────────────────────────┐
│ LOAD OPERATION                                               │
└─────────────────┬────────────────────────────────────────────┘
                  │
                  ├─> FUN_00bc8b00() - PlayerOptionsSaveData
                  │   │
                  │   └─> FUN_01b09c10(0x2DAD13E3, offset, data)
                  │       │
                  │       ├─> Read from save file:
                  │       │   hash = 0x90CC0F3C (French)
                  │       │
                  │       ├─> FUN_01b003e0(0x2DAD13E3)
                  │       │   Returns: Language table pointer (0x0298a780)
                  │       │
                  │       ├─> FUN_01b82590(hash=0x90CC0F3C)
                  │       │   Searches table for hash 0x90CC0F3C
                  │       │   Returns: Table position (1 for French)
                  │       │
                  │       ├─> Read index from table:
                  │       │   index = *(0x0298a780 + position*8 + 0)
                  │       │   index = *(0x0298a790)
                  │       │   index = 2 (French)
                  │       │
                  │       └─> Set language to index 2
                  │           FUN_01ae3b10(2)
                  │           FUN_01ae3b20(2)
                  │           FUN_01ae3b00(2)
                  │
                  └─> Language restored from save file
```

---

### 3. Language Table Access Patterns

```
┌─────────────────────────────────────────────────────────────┐
│ Language Table Structure (0x0298a780)                       │
│                                                              │
│  Entry 0: [00 00 00 00][48 0E D5 5E]  ← Header              │
│  Entry 1: [01 00 00 00][B5 97 CC 50]  ← English             │
│  Entry 2: [02 00 00 00][90 CC 0F 3C]  ← French              │
│  Entry 3: [03 00 00 00][81 60 57 48]  ← Spanish             │
│  ...                                                         │
└─────────────────────────────────────────────────────────────┘
         ↓                      ↓
    Index Field           Hash Field
    (Offset +0)          (Offset +4)


ACCESS PATTERN 1: Get hash by index
─────────────────────────────────────
Input:  Language index = 2 (French)
Step 1: Find table position with index 2
        FUN_01b82560(2) → returns position 1
Step 2: Calculate offset
        offset = 0x0298a780 + (position * 8) + 4
        offset = 0x0298a780 + (1 * 8) + 4
        offset = 0x0298a790 + 4 = 0x0298a794
Step 3: Read hash
        hash = *(0x0298a794) = 0x90CC0F3C
Output: Hash = 0x90CC0F3C


ACCESS PATTERN 2: Get index by hash
─────────────────────────────────────
Input:  Hash = 0x90CC0F3C
Step 1: Find table position with hash
        FUN_01b82590(0x90CC0F3C) → returns position 1
Step 2: Calculate offset
        offset = 0x0298a780 + (position * 8) + 0
        offset = 0x0298a780 + (1 * 8)
        offset = 0x0298a790
Step 3: Read index
        index = *(0x0298a790) = 0x02000000
        (Little-endian: 2)
Output: Index = 2 (French)
```

---

## Registry System

### Language System Registry ID

**ID:** `0x2DAD13E3`  
**Purpose:** Unique identifier for the language system in the global registry  
**Type:** 32-bit hash/constant

### Registry Usage Locations

The registry ID `0x2DAD13E3` appears in multiple locations throughout the codebase:

| Address      | Context                           | Purpose                           |
|--------------|-----------------------------------|-----------------------------------|
| 0x0298a834   | Language table pointer structure  | Table registration                |
| 0x027e1a40   | Data structure                    | System reference                  |
| 0x027e1a60   | Data structure                    | System reference                  |
| 0x027e1a80   | Data structure                    | System reference                  |
| 0x027e3ee4   | Data structure                    | System reference                  |
| 0x027e1544   | Data structure                    | System reference                  |
| 0x027ea79c   | Data structure                    | System reference                  |
| 0x02801cf4   | Data structure                    | System reference                  |
| 0x0281cecc   | Data structure                    | System reference                  |
| 0x028419f8   | Player options save data          | Save/load language settings       |
| 0x02841a18   | Player options save data          | Save/load language settings       |
| 0x02841a38   | Player options save data          | Save/load language settings       |
| 0x02842100   | Data structure                    | System reference                  |
| 0x02842120   | Data structure                    | System reference                  |

### Registry Access Functions

```c
// Register object with ID
FUN_01b01f00(0x2DAD13E3, object_pointer, context);

// Retrieve object by ID
object_pointer = FUN_01b003e0(0x2DAD13E3);

// Used throughout for language table access
FUN_01b09c10(0x2DAD13E3, offset, data_pointer);
```

---

## Save File Integration

### Language Data Storage in Save Files

The game stores language settings in save files using XML-like format:

```xml
<EnumValue>2</EnumValue>           <!-- Language index -->
<EnumName>0x90CC0F3C</EnumName>    <!-- Language hash for persistence -->
```

### Why Use Hashes?

The hash-based system provides several advantages:

1. **Version Independence:** If language indices change between game versions, hashes remain constant
2. **Validation:** Detect if a save file's language is still supported
3. **Corruption Detection:** Invalid hashes indicate corrupted save data
4. **Forward Compatibility:** New languages can be added without breaking old saves

### Example Save/Load Scenario

**Scenario:** Player saves game with French language, then game is updated with new language list

**Without Hashes:**
```
Save: Language index = 2 (French)
After update: Index 2 now = Spanish (languages reordered)
Load: Game incorrectly sets Spanish language
```

**With Hashes:**
```
Save: Language index = 2, Hash = 0x90CC0F3C (French)
After update: French now at index 5, but hash still 0x90CC0F3C
Load: Game searches for hash 0x90CC0F3C, finds French at new index 5
Result: Correct language restored
```

---

## Localization File Loading

### File Naming Convention

**Base filename:** `localization.lang`

**Language-specific variants:**

| Language             | Index | Filename                  |
|----------------------|-------|---------------------------|
| Most languages       | *     | `localization.lang`       |
| Russian              | 4     | `localization.lang_rus`   |
| Korean               | 11    | `localization.lang_kor`   |
| Simplified Chinese   | 19    | `localization.lang_chs`   |
| Traditional Chinese  | 20    | `localization.lang_chn`   |

### File Format

```
Offset | Type    | Description
-------|---------|----------------------------------------
0x00   | char[4] | Magic header: "LANG" (0x4c414e47)
0x04   | byte    | Unknown byte value
0x05   | uint32  | Version or flags (big-endian)
0x09   | byte    | Language index
0x0A   | uint32  | Additional metadata
...    | ...     | String table and localization data
```

### Loading Process

1. Determine target filename based on current language
2. Attempt to open language-specific file (e.g., `localization.lang_rus`)
3. If specific file not found, fall back to base file (`localization.lang`)
4. Verify magic header ("LANG")
5. Parse language metadata
6. Load string tables into memory
7. Register with localization system

### Endianness Handling

The localization files use **big-endian** format for multi-byte values, requiring byte-swapping:

```c
// Read 4-byte value and convert to little-endian
value = read_uint32();
value = (value >> 24) | 
        ((value & 0xFF0000) >> 8) | 
        ((value & 0xFF00) << 8) | 
        (value << 24);
```

---

## Key Findings Summary

### 1. Language Hash Purpose

The 4-byte hash values serve as **persistent identifiers** for language settings:

- **NOT** CRC-32 checksums of files
- **NOT** validation hashes for localization data
- **ARE** unique identifiers for save file persistence
- **ENABLE** version-independent language storage

### 2. Multiple Language Storage

The game maintains **three separate language indices**:

- `DAT_0298a840` - Likely UI/menu language
- `DAT_0298a844` - Likely subtitle language  
- `DAT_0298a848` - Likely audio/voice language

This allows different languages for different aspects (e.g., English UI with French subtitles).

### 3. Registry System Integration

The language system is part of a larger **global registry system** (`0x2DAD13E3`) that manages game objects and systems. This architecture allows:

- Centralized system management
- Save/load system integration
- Inter-system communication

### 4. Unused Language Slot

Index 6 (`0xA1B2D787`) appears unused/reserved, suggesting:

- Removed language from final release
- Planned language that was cut
- Reserved slot for future DLC language

---

## Technical Notes

### Memory Addresses are Virtual

All addresses listed are **virtual addresses** in the game's memory space when loaded. Physical file offsets will differ.

### Little-Endian Format

The game uses **little-endian** byte order for most data structures (x86 architecture). The language table values are shown as they appear in memory:

- `0x01000000` in memory = integer value 1
- `0xB597CC50` in memory = hash value 0xB597CC50

### Pointer Structure

```c
struct LanguageTablePointer {
    void*    table_address;     // 0x0298a780
    uint32_t registry_id;       // 0x2DAD13E3
    uint32_t metadata;          // 0x00000016
};
```

Located at: `0x0298a830`

---

## Conclusion

This analysis reveals a sophisticated language management system in Assassin's Creed Brotherhood that uses:

1. **Hash-based persistence** for save file compatibility across game versions
2. **Registry architecture** for system-wide language access
3. **Multi-tier language support** (UI, subtitles, audio)
4. **Fallback mechanisms** for missing localization files
5. **Runtime detection** from Windows Registry

The hash values (`0xB597CC50` for English, etc.) are **not checksums** but rather **unique persistent identifiers** that ensure player language preferences survive game updates and language list reorganizations.

---

## Appendix: Quick Reference

### Critical Addresses

| Address      | Description                          |
|--------------|--------------------------------------|
| 0x0298a780   | Language table base                  |
| 0x0298a830   | Language table pointer structure     |
| 0x0298a840   | Global language index storage #1     |
| 0x0298a844   | Global language index storage #2     |
| 0x0298a848   | Global language index storage #3     |

### Critical Constants

| Value        | Description                          |
|--------------|--------------------------------------|
| 0x2DAD13E3   | Language system registry ID          |
| 0x4C414E47   | Localization file magic ("LANG")     |

### Critical Functions

| Address      | Name/Purpose                         |
|--------------|--------------------------------------|
| 0x01ae38b0   | Language table registration          |
| 0x0040ad40   | Read language from Windows Registry  |
| 0x0040b120   | Language detection and storage       |
| 0x0043d740   | Localization file loader             |
| 0x01b09c10   | Save/load language data              |
| 0x0056ce70   | Global registry lookup               |
| 0x01b82560   | Find table entry by index            |
| 0x01b82590   | Find table entry by hash             |

---

**Document Version:** 1.0  
**Analysis Date:** December 2024  
**Game:** Assassin's Creed Brotherhood (PC)  
**Tools Used:** Ghidra
