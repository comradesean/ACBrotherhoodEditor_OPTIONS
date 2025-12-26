# Assassin's Creed Brotherhood - Function Reference Map
**Complete Documentation of Reverse-Engineered Functions**

Date: December 25, 2024  
Status: Work in Progress - Footer Logic Still Missing

---

## Table of Contents

1. [File I/O Functions](#file-io-functions)
2. [Section Writers (Serialization)](#section-writers-serialization)
3. [Section Readers (Deserialization)](#section-readers-deserialization)
4. [Compression Functions](#compression-functions)
5. [Header & Magic Byte Functions](#header--magic-byte-functions)
6. [Save System Orchestration](#save-system-orchestration)
7. [Memory Management](#memory-management)
8. [Serialization Framework](#serialization-framework)
9. [Game State & Objects](#game-state--objects)
10. [Utility Functions](#utility-functions)
11. [Unrelated Functions](#unrelated-functions)

---

## File I/O Functions

### `FUN_005e4860` - Low-Level File Writer
**Address:** 0x005e4860  
**Purpose:** Writes data buffer to a file in the SAVES directory

**Process:**
1. Builds path: `[game_dir]\SAVES\[filename]`
2. Creates SAVES directory if needed
3. Opens/creates file with `CreateFileW`
4. Writes buffer with `WriteFile`
5. Closes handle

**Parameters:**
- `param_1`: Path prefix
- `param_2`: Filename
- `param_3`: Data buffer
- `param_4`: Size in bytes

---

### `FUN_005e4b10` - Generic File Reader
**Address:** 0x005e4b10  
**Purpose:** Reads any file from the SAVES directory into a buffer

**Process:**
1. Builds full path: `[game_dir]\SAVES\[filename]`
2. Opens file with `CreateFileW`
3. Gets file size with `GetFileSize`
4. Allocates buffer via `FUN_01ae48f0`
5. Reads entire file with `ReadFile`
6. Returns buffer and size in `param_3`

**Returns:** 1 on success, 0 on failure

---

### `FUN_005e4970` - OPTIONS File Writer
**Address:** 0x005e4970  
**Purpose:** Writes the OPTIONS file to disk (thin wrapper)

**Process:**
- Calls `FUN_005e4860` with:
  - Path: `PTR_s_save:SAVES_027ed058`
  - Filename: `"OPTIONS"`
  - Buffer: `param_2` (complete file data)
  - Size: `param_3` (total bytes)

**Key Detail:** Receives an already-complete buffer with all sections AND footer

---

### `FUN_005e4950` - Assassin.sav File Writer
**Address:** 0x005e4950  
**Purpose:** Writes Section 1 savegame data to "assassin.sav"

**Process:** Calls `FUN_005e4860` to write to "assassin.sav" file

---

### `FUN_005e4c20` - Assassin.sav Reader
**Address:** 0x005e4c20  
**Purpose:** Reads the "assassin.sav" file

**Process:** Calls `FUN_005e4b10` to load from "assassin.sav"

---

### `FUN_005e4c40` - OPTIONS File Reader
**Address:** 0x005e4c40  
**Purpose:** Reads the OPTIONS file from disk

**Process:** Calls `FUN_005e4b10` to load "OPTIONS" file

---

## Section Writers (Serialization)

### `FUN_0046d160` - Section 1 Writer/Serializer
**Address:** 0x0046d160  
**Purpose:** Builds and writes Section 1 of the OPTIONS file (primary savegame data)

**Process:**
1. Debug logging: "::Engine::SaveGame::SaveToFile"
2. Allocates initial 12-byte buffer
3. Writes header (Field1: 0x16, Field2: 0xFEDBAC)
4. Compresses section data via `FUN_01afe160`
5. Appends compressed data after header
6. Optionally serializes sub-objects
7. Calls vtable write function to output

**Key Detail:** Delegates to vtable function - does not write final file directly

---

### `FUN_01712ca0` - Section 2 Writer
**Address:** 0x01712ca0  
**Purpose:** Writes Section 2 (AssassinGlobalProfileData) to buffer

**Process:**
1. Allocates 8-byte header: `0x00000003` and `0x11FACE11`
2. Sets offset: `param_2[1] = 8`
3. Compresses section data via `FUN_01afe160`
4. Expands buffer with `FUN_0046eb90`
5. Appends compressed data after header
6. Updates offset tracking

**Buffer Structure:** `param_2[0]` = buffer, `param_2[1]` = offset, `param_2[2]` = flags

---

### `FUN_017108e0` - Section 3 Writer
**Address:** 0x017108e0  
**Purpose:** Writes Section 3 to buffer

**Process:**
1. Allocates 8-byte header: `0x00000000` and `0x21EFFE22`
2. Sets offset: `param_2[1] = 8`
3. Compresses data via `FUN_01afe160`
4. Expands buffer
5. Appends compressed data
6. Updates offset

**Note:** Identical structure to Section 2 writer, different magic values

---

### `FUN_01712930` - Profile Data Serializer/Deserializer
**Address:** 0x01712930  
**Purpose:** Serializes/deserializes "AssassinGlobalProfileData" structure

**Process:**
1. Links back-pointer: `param_2 + 0x1c = param_1`
2. Initializes context if first-time
3. Temporary state swap for `param_2 + 0x20`
4. Serializes multiple fields with hash keys
5. Handles arrays and dynamic data
6. Calls finalization functions

**Related:** Section 2/3 configuration data serialization

---

## Section Readers (Deserialization)

### `FUN_0046d430` - Section 1 Reader and Validator
**Address:** 0x0046d430  
**Purpose:** Reads and validates Section 1 from OPTIONS file during load

**Process:**
1. Reads section via vtable function
2. Validates Field1 == `0x16` (Section 1 signature)
3. Validates Field2 == `0xFEDBAC` (validation marker)
4. Returns 0 with error flag if invalid
5. Decompresses data via `FUN_00425360`
6. Processes sub-objects if present
7. Deserializes via vtable function at offset 0x28
8. Returns decompressed data pointer

**Error Handling:** Sets `param_2 + 0x46` flag on validation failure

---

### `FUN_01712db0` - Section 2 Reader/Validator
**Address:** 0x01712db0  
**Purpose:** Reads and validates Section 2 (AssassinGlobalProfileData)

**Process:**
1. Validates header: `0x00000003` and `0x11FACE11`
2. Decompresses via `FUN_00425360`
3. Processes data via `FUN_01afd600`
4. Deserializes via vtable function at offset 0x0C
5. Returns 1 on success, 0 on failure

**Related:** Counterpart to `FUN_01712ca0` (Section 2 writer)

---

### `FUN_017109e0` - Section 3 Reader/Validator
**Address:** 0x017109e0  
**Purpose:** Reads and validates Section 3 from buffer

**Process:**
1. Validates header: `0x00000000` and `0x21EFFE22`
2. Decompresses data
3. Processes via `FUN_01afd600`
4. Deserializes via vtable at offset 0x0C
5. Special handling: If flag at offset 0x24 is set, calls `FUN_004d1c00`
6. Returns 1 on success, 0 on failure

**Related:** Counterpart to `FUN_017108e0` (Section 3 writer)

---

### `FUN_01bde7c0` - Massive Structure Deserializer
**Address:** 0x01bde7c0  
**Purpose:** Deserializes very large structure (400+ bytes) from binary buffer

**Process:**
1. Reads buffer pointer from `param_2 + 0x14`
2. Sequentially reads ~130+ fields
3. Reads mix of 1-byte, 4-byte values
4. Calls helper deserializers for complex sub-structures
5. Advances read pointer after each field

**Key Detail:** Reads decompressed OPTIONS data (Section 2/3 content)

---

### `FUN_01be02f0` - Deserialization Wrapper
**Address:** 0x01be02f0  
**Purpose:** Wrapper for massive structure deserializer

**Process:**
1. Calls no-op stub `FUN_01b17ea0`
2. Uses dispatcher `FUN_01af6920` with hash `0x1c0637ab`
3. Invokes `FUN_01bde7c0` for structure at `param_1 + 8`

---

### `FUN_01af6920` - Polymorphic Deserialization Dispatcher
**Address:** 0x01af6920  
**Purpose:** Reads type byte and dispatches to appropriate handler

**Process:**
1. Reads type byte from buffer
2. **Type 0x00:** Full object - allocates, sets ID, calls callback
3. **Type 0x02:** Reference/pointer deserialization
4. **Type 0x03:** Null object marker
5. Calls user-provided callback to populate object

---

## Compression Functions

### `FUN_01b8e140` - LZSS Compression Engine
**Address:** 0x01b8e140  
**Purpose:** Core LZSS compression algorithm (lazy-matching variant)

**Process:**
1. Initializes compression state, bit buffer, output pointer
2. Main loop processes input looking for matches:
   - Short matches (2-5 bytes, offset 1-256): 1-bit flag + 2-bit length + 8-bit offset
   - Long matches (3+ bytes, offset 0-8191): 2-bit flag + 13-bit offset + variable length
   - Literals: 1-bit flag + raw byte
3. Lazy matching: Evaluates current vs next position
4. Bit packing: Efficient bit-level encoding
5. Terminator: Writes end-of-stream marker (0x20, 0x00)
6. Returns compressed size in `param_4`

**Features:**
- Variable-length encoding for very long matches (9+ bytes)
- Statistics tracking (literals, short/long matches)
- Callback support for progress monitoring

---

### `FUN_01b8e5a0` - Compression Wrapper
**Address:** 0x01b8e5a0  
**Purpose:** Simple wrapper for main compression

**Process:** Calls `FUN_01b8e140` with default parameters (last two = 0)

---

### `FUN_01afe160` - Compression Wrapper with Fixed Buffers
**Address:** 0x01afe160  
**Purpose:** Wrapper with standard 4KB buffer sizes

**Process:** Calls `FUN_01afdba0` with fixed parameters (0x1000 = 4096 bytes)

---

### `FUN_01afdba0` - Main Compression with Verification
**Address:** 0x01afdba0  
**Purpose:** Primary compression with optional round-trip validation

**Process:**
1. Initializes compression buffers and reference-counted objects
2. Calls `FUN_01b7b050` (LZSS compressor) with 0x8000 buffer
3. If `param_6` flag set, decompresses via `FUN_00425360` to validate
4. Releases all allocated buffers and objects

---

### `FUN_01b7a200` - Compression Dispatcher with Callback
**Address:** 0x01b7a200  
**Purpose:** Routes compression through function table with optional two-pass

**Process:**
1. If `param_7` provided AND table entry exists:
   - First pass: Get size estimate via `PTR_FUN_0298d168[param_1 * 5]`
   - Store size to `*param_5`
   - Second pass: Finalize via `PTR_FUN_0298d170[param_1 * 5]`
2. No callback: Single-pass via `PTR_FUN_0298d168[param_1 * 5]`

**Key Detail:** `param_1` selects compression algorithm (stride of 5 entries)

---

### `FUN_01b7b000` - Compression with Checksum
**Address:** 0x01b7b000  
**Purpose:** Compresses data and calculates checksum

**Process:**
1. Calls `FUN_01b7a200` (compression dispatcher)
2. Calls `FUN_01b7ac10` with result (calculates Adler-32 checksum)

**Related:** Section header creation - compression + checksum

---

## Header & Magic Byte Functions

### `FUN_01b7a1d0` - Magic Bytes Validator
**Address:** 0x01b7a1d0  
**Purpose:** Validates section header magic bytes

**Process:**
1. Size check: Verifies buffer ≥ 12 bytes (`param_2 > 0xB`)
2. Magic1: Checks `param_1 + 0x04` == `0x57FBAA33`
3. Magic2: Checks `param_1 + 0x08` == `0x1004FA99`
4. Success: Returns `0x1004FA01`
5. Failure: Returns EAX with lower byte zeroed

**Related:** Universal header validator from documentation

---

### `FUN_01b7a310` - Magic Bytes Writer
**Address:** 0x01b7a310  
**Purpose:** Writes universal 16-byte magic pattern to section headers

**Process:**
1. Writes Magic1 & Magic2: `0x57FBAA33` and `0x1004FA99` (vtable[0x30])
2. Writes Magic3 low word: `1` (vtable[0x38])
3. Writes Magic3 high byte: From `param_1 + 0x48` = `2` (vtable[0x3C])
   - Forms `0x00020001` (compression parameters)
4. Writes Magic4: Base value from `param_1 + 0x40`
   - ORs with `0x80000000` if flag set
   - Forms `0x01000080` (version/flags)

**Pattern Written:**
```
0x10: 0x57FBAA33  (Magic1)
0x14: 0x1004FA99  (Magic2)
0x18: 0x00020001  (Magic3)
0x1C: 0x01000080  (Magic4)
```

---

### `FUN_01afd600` - Header Processor with Validation
**Address:** 0x01afd600  
**Purpose:** Validates and processes section header data

**Process:**
1. Validates magic bytes via `FUN_01b7a1d0`
2. If valid: Calls `FUN_01b7b190` to process/transform
3. Updates pointers with processed results
4. Creates buffer structures
5. Manages reference-counted objects with atomic ops
6. Calls initialization functions
7. Releases temporary buffers
8. Returns processed data handle

**Related:** Called during deserialization after header validation

---

### `FUN_01b08ce0` - Object Metadata Serializer
**Address:** 0x01b08ce0  
**Purpose:** Serializes object metadata (version info, class IDs, names)

**Process:** Writes extensive metadata including version numbers, class IDs, object relationships

---

## Save System Orchestration

### `FUN_0046d980` - Save Orchestrator / Dirty Flag Processor
**Address:** 0x0046d980  
**Purpose:** Main save coordinator - processes dirty flags and dispatches save operations

**Process:**
1. Pre-save callbacks: Iterates list at `param_1 + 0x1dc`
2. Flag-based dispatch checks bits in `param_1 + 0x298`:
   - **Bit 0x01/0x02:** Calls `FUN_005e3960()` (Section 1 save)
   - **Bit 0x04:** Calls `FUN_005e39a0()` (Section 2 save)
   - **Bit 0x08:** Calls `FUN_0046d7b0` (Section 1 reload)
   - **Bit 0x10:** Appends via `FUN_0046d8b0` with flag 0x10
   - **Bit 0x40:** Appends via `FUN_0046d8b0` with flag 0x40
   - **Bit 0x80:** Loads Section 1 + saves via `FUN_005e39a0()`
   - **Bit 0x100/0x400/0x800:** Various cleanup operations
3. Clears flags after each operation
4. Post-save callbacks: Iterates list at `param_1 + 0x1f0`

**Key Detail:** THE save orchestrator - triggers all save operations

---

### `FUN_0046e0a0` - Dirty Flag Manager with Save Trigger
**Address:** 0x0046e0a0  
**Purpose:** Manages dirty/modified flags and triggers saves

**Process:**
1. Check active: Only if `param_1 + 0x185` is set
2. Optional reset: If `param_4` true, clears flags to 0
3. Set primary flags: ORs `param_2` into `param_1 + 0x298`
4. Conditional secondary: If bits 0-1 set, ORs `param_3` into `param_1 + 0x29c`
5. Trigger save: If `param_4` true, calls `FUN_0046d980()`

**Related:** Dirty-flag tracking - sets flags when data changes

---

### `FUN_005e3960` - Object Pre-Save Callback Iterator
**Address:** 0x005e3960  
**Purpose:** Calls vtable function 0x20 on all registered objects

**Process:** Iterates object array at `param_1 + 0x3c`, calling save preparation

---

### `FUN_005e39a0` - Object Save Callback Iterator
**Address:** 0x005e39a0  
**Purpose:** Calls vtable function 0x1C on registered objects if flag set

**Process:** If `param_1 + 0x45` set, iterates array calling finalization handlers

---

### `FUN_0046e1e0` - Event Handler / Game Loop
**Address:** 0x0046e1e0  
**Purpose:** Game event handler that triggers saves at different points

**Process:** Checks various flags and calls section functions at appropriate times (not the file serializer itself)

---

## Memory Management

### `FUN_01ab97a0` - Binary Tree/Heap Insertion
**Address:** 0x01ab97a0  
**Purpose:** Inserts memory block into segregated free list

**Process:**
1. Calculates bucket index from size (bit-scan for highest bit)
2. Stores at `param_2 + 0x1c`
3. If bucket empty: Sets flag, initializes circular doubly-linked list
4. If occupied: Traverses binary tree, finds insertion point
5. Inserts into circular list at found position

**Block Structure:**
- +0x08: previous pointer
- +0x0C: next pointer
- +0x10/0x14: child pointers
- +0x18: parent/bucket pointer
- +0x1C: bucket index

**Key Detail:** Segregated fit allocator - blocks organized by size class

---

### `FUN_0046eb90` - Buffer Resize/Reallocate
**Address:** (referenced in section writers)  
**Purpose:** Resizes buffers to accommodate additional data

---

### `FUN_01ae48f0` - Buffer Allocation
**Address:** (referenced throughout)  
**Purpose:** Allocates buffers for serialization/deserialization

---

## Serialization Framework

### `FUN_01b0a740` - Complex Object Serialization Dispatcher
**Address:** 0x01b0a740  
**Purpose:** Generic serialization framework with type checking

**Process:** Extensive type validation, buffer management, conditional paths based on metadata

---

### `FUN_01b0a460` - Complex Value Serialization
**Address:** 0x01b0a460  
**Purpose:** Serializes values with extensive type checking

**Process:** Complex serialization with state management, type validation, multiple paths

---

### `FUN_01b074a0` - Plain Data Block Writer
**Address:** 0x01b074a0  
**Purpose:** Writes plain data block if flag set

**Process:** If `param_1 + 0x4e & 0x01`, writes via vtable at offset 0x40

---

### `FUN_01b49610` - Serialization Stack Manager
**Address:** 0x01b49610  
**Purpose:** Manages serialization depth tracking

**Process:** Adjusts stack pointers, calls finalization handlers based on mode

---

## Game State & Objects

### `FUN_0046dcc0` - Game State Object Constructor
**Address:** 0x0046dcc0  
**Purpose:** Constructs and initializes main game state/save system

**Process:**
1. Sets up 3 vtable pointers
2. Initializes subsystems repeatedly
3. Creates I/O handler via `FUN_005e49d0`, stores at `param_1[0xa3]` (offset 0x28C)
4. Zeros state fields
5. Enables save system: Sets flag at offset 0x185

**Key Field:** `param_1[0xa3]` (offset 0x28C) = I/O handler object

---

### `FUN_005e49d0` - I/O Handler Object Creator
**Address:** 0x005e49d0  
**Purpose:** Creates I/O handler object with vtable `PTR_FUN_02411ef0`

**Returns:** I/O handler object pointer

---

### `FUN_009ca3e0` - I/O Handler Constructor
**Address:** 0x009ca3e0  
**Purpose:** Sets vtable for I/O handler

**Process:** Sets `*param_1 = &PTR_FUN_02411ef0`

---

### `FUN_009ca4c0` - I/O Handler Destructor
**Address:** 0x009ca4c0  
**Purpose:** Destructs I/O handler object

---

### `FUN_009ca500` - I/O Handler Destructor (alt)
**Address:** 0x009ca500  
**Purpose:** Alternate destructor

---

### `FUN_009ca550` - I/O Handler Destructor (with dealloc)
**Address:** 0x009ca550  
**Purpose:** Destructor with deallocation

---

### `FUN_01712ec0` - AssassinGlobalProfileData Constructor
**Address:** 0x01712ec0  
**Purpose:** Constructs AssassinGlobalProfileData object

**Process:** Sets vtable to `PTR_FUN_0253df30`, initializes subsystems

---

### `FUN_017130a0` - AssassinGlobalProfileData Destructor
**Address:** 0x017130a0  
**Purpose:** Destructs AssassinGlobalProfileData object

---

### `FUN_017106e0` - Section 3 Constructor
**Address:** 0x017106e0  
**Purpose:** Constructs Section 3 object

**Process:** Sets vtable to `PTR_FUN_0253de0c`, initializes fields

---

### `FUN_01710540` - Section 3 Destructor
**Address:** 0x01710540  
**Purpose:** Destructs Section 3 object

---

### `FUN_01710b90` - Section 3 Destructor (with dealloc)
**Address:** 0x01710b90  
**Purpose:** Destructor with deallocation

---

### `FUN_0046d8b0` - Dynamic Array Append
**Address:** 0x0046d8b0  
**Purpose:** Appends 8-byte entry to dynamic array

**Process:**
1. Checks capacity vs count (packed in `param_1 + 0x360`)
2. Auto-grows via `FUN_0046ef60` if full
3. Calculates position: `base + (index + 1) * 8 - 8`
4. Copies 8 bytes from `param_2`
5. Updates index

**Field Format (`param_1 + 0x360`):**
- Bits 0-13: capacity (max 16383)
- Bits 16-29: count (max 16383)

---

### `FUN_01b2e130` - Structure Initializer with Parent Tracking
**Address:** 0x01b2e130  
**Purpose:** Initializes structure with parent relationship

**Process:**
1. Ensures capacity
2. Populates multiple fields
3. Depth tracking: If parent exists, depth = parent_depth + 1, else 0

**Related:** Tree/hierarchy node initialization

---

## Utility Functions

### `FUN_01b17ea0` - No-Op Callback Stub
**Address:** 0x01b17ea0  
**Purpose:** Empty placeholder function

**Details:** Returns immediately with `RET 0x4`, used as default callback in 20+ locations

---

### `FUN_01b09620` - Conditional Field Setter
**Address:** 0x01b09620  
**Purpose:** Sets field based on state flag

**Process:**
- If `param_1 + 0x58 == 3`: Calls `FUN_01b091a0` if param_2 non-null
- Otherwise: Sets `param_1 + 0x28 = param_2`

---

### `FUN_01c48fa0` - Indexed Vtable Function Call
**Address:** 0x01c48fa0  
**Purpose:** Calls vtable function with indexed offset

**Process:**
1. Gets function from `DAT_02a5e0f4` vtable at offset 4
2. Calculates target: `param_9 + (param_2 * 0x14)` (20-byte stride)
3. Invokes with all parameters

---

### `FUN_01b48fb0` - Conditional Vtable Dispatcher
**Address:** 0x01b48fb0  
**Purpose:** Conditionally calls vtable functions based on flags

**Process:**
1. If `param_1 + 0x1012` set:
   - If `param_1[1]` false: Call vtable[0x54], then cleanup
   - Otherwise: Call vtable[0x84] and [0x44]
2. Always calls `FUN_01b49610` for cleanup

---

## Unrelated Functions

### `FUN_01baa240` - AES Decryption
**Address:** 0x01baa240  
**Purpose:** AES block cipher decryption rounds

**Process:** Performs AES decryption with inverse operations

**Related:** Cryptography, unrelated to OPTIONS format

---

### `FUN_004b41b0` - Player Stats Manager
**Address:** 0x004b41b0  
**Purpose:** Initializes player statistics and online services

**Related:** Multiplayer infrastructure, unrelated to OPTIONS

---

### `FUN_00a20600` - Reward Code Handler
**Address:** 0x00a20600  
**Purpose:** Processes reward/unlock codes (ACBREWARD02-07)

**Related:** Game progression, unrelated to OPTIONS format

---

## Important Vtables

### PTR_FUN_02411ef0 - I/O Handler Vtable
**Address:** 0x02411ef0  
**Functions:**
- Offset 0x00: `FUN_009ca4c0` (Destructor)
- Offset 0x04: `FUN_005e4950` (Write "assassin.sav")
- Offset 0x08: `FUN_005e4c20` (Read "assassin.sav")
- Offset 0x0C: `FUN_005e4970` (Write "OPTIONS") ← **CRITICAL**
- Offset 0x10: `FUN_005e4c40` (Read "OPTIONS")

**Usage:** Set at offset 0x28C in main game state object

---

### PTR_FUN_0253df30 - AssassinGlobalProfileData Vtable
**Address:** 0x0253df30  
**Functions:**
- Offset 0x04: `FUN_01712930` (Serializer)
- Offset 0x24: `FUN_01712ca0` (Section 2 Writer) ← **CRITICAL**

**Related String:** "AssassinGlobalProfileData"

---

### PTR_FUN_0253de0c - Section 3 Vtable
**Address:** 0x0253de0c  
**Functions:**
- Offset 0x24: `FUN_017108e0` (Section 3 Writer) ← **CRITICAL**

---

## Key Findings

### File Structure
- **Section 1** → "assassin.sav" (via vtable offset 0x04)
- **Sections 2+3** → "OPTIONS" (via vtable offset 0x0C)

### Section Format
All sections use 8-byte headers:
- **Section 2:** `0x00000003` + `0x11FACE11`
- **Section 3:** `0x00000000` + `0x21EFFE22`

### Buffer Management
- Both section writers set `param_2[1] = 8` at start
- Suggests separate buffers later combined
- Footer added during "global options construction"

---

## Missing Piece: Footer Logic

**Status:** NOT YET FOUND

**What we know:**
- Footer is 5 bytes: `01 00 00 00 [XX]`
- Observed values: `0x54` (84) and `0x0C` (12)
- Added "after Section 3 during global options construction"
- Must occur before calling `FUN_005e4970`

**Where to look next:**
1. Function that calls BOTH `FUN_01712ca0` AND `FUN_017108e0`
2. Function that invokes vtable offset 0x0C to call `FUN_005e4970`
3. Buffer finalization/completion functions
4. Any code writing sequential bytes: `01 00 00 00 XX`

---

## Document Metadata

**Created:** December 25, 2024  
**Functions Analyzed:** 80+  
**Status:** Work in Progress  
**Next Steps:** Find footer calculation logic

---

**End of Function Reference**
