# Reverse Engineering Task: Assassin's Creed Brotherhood OPTIONS File Format

## Context

You are continuing reverse engineering work on the Assassin's Creed Brotherhood OPTIONS binary save file format. A comprehensive specification has been completed documenting the file structure, compression, headers, and platform differences. See `OPTIONS_FORMAT_SPECIFICATION.md` for current progress.

**What's Complete:**
- File layout and section structure (3 sections PC, 4 sections PS3)
- 44-byte section header format fully decoded
- LZSS compression algorithm reverse-engineered
- Platform differences (PC vs PS3) documented
- Checksums, magic numbers, and validation patterns identified
- Compression/decompression fully understood

**What's Missing:**
- Internal structure of decompressed section data (what's in those 283/1310/162/1903 bytes)
- Hash resolution (what do `0x305AE1A8` and `0x6F88B05B` represent?)
- Bitfield/flag meanings within section data
- Field offset → game setting mappings
- Value ranges, defaults, and validation rules
- String tables or lookup tables (if any)
- Cross-section reference relationships

---

## Your Task

Using **Ghidra decompilation** and **WinDBG time-travel tracing**, complete the documentation by reverse engineering the internal structure of each decompressed section. Your goal is to create detailed field-level specifications for all section payloads.

---

## Available Tools & Resources

1. **Ghidra Project**
   - ACBSP.exe already loaded and analyzed
   - Known parser functions identified:
     - `FUN_0046d710` - Section 1 parser
     - `FUN_01712ca0` - Section 2 parser  
     - `FUN_017108e0` - Section 3 parser
   - Section header struct already defined

2. **WinDBG Time-Travel Traces**
   - Save file load/write operations captured
   - Memory snapshots of decompressed sections available
   - Call stacks linking file offsets to UI/game features

3. **Sample Files**
   - 24 different OPTIONS files with varying settings
   - Both PC and PS3 versions available
   - Differential analysis partially completed

---

## Step-by-Step Instructions

### Phase 1: Decompressed Section Data Structure Extraction

**For Each Section (1, 2, 3, and PS3 Section 4):**

1. **Decompile the parser function in Ghidra:**
   - Open the function (e.g., `FUN_0046d710` for Section 1)
   - Generate C pseudocode
   - Export decompilation to text file

2. **Identify all field accesses:**
   - Search for patterns: `*(data + 0xNN)`, `data[offset]`, structure member accesses
   - Document every unique offset accessed
   - Note data type of each access (uint32_t, uint8_t, float, etc.)

3. **Create C structure definitions:**
   - Build a struct template with all discovered fields
   - Name fields based on usage context (e.g., `audio_volume`, `graphics_quality`)
   - Add comments with Ghidra function references

4. **Validate field boundaries:**
   - Ensure all offsets are accounted for
   - Identify padding bytes (unused regions)
   - Verify struct size matches decompressed section size

**Deliverable:** `SECTION_DATA_STRUCTURES.md` with complete C structs for each section

---

### Phase 2: Hash Resolution

**Objective:** Determine what `0x305AE1A8` and `0x6F88B05B` represent

1. **Find hash computation function:**
   - Search Ghidra for these constants
   - Identify the hashing algorithm used (likely FNV, Murmur, CityHash, or custom)
   - Decompile the hash function

2. **Extract all hash values:**
   - Search binary for hash comparison operations
   - Build list of all hashes used in validation/lookup

3. **Resolve hashes to strings:**
   - If algorithm is known: brute-force common strings (achievement names, setting IDs, etc.)
   - If lookup table exists: extract hash → string mappings directly
   - Use WinDBG traces to see what triggers hash matches

4. **Build hash dictionary:**
   - Create mapping table: `hash_value → identifier_string`

**Deliverable:** `HASH_RESOLUTION_TABLE.md` with hash → string mappings

---

### Phase 3: Field → Game Setting Mapping

**Objective:** Map each byte offset to its in-game meaning

**Method A: Static Analysis (Ghidra)**

1. For each field access in parser functions:
   - Trace forward to UI update functions
   - Identify game feature controlled by field
   - Example: `FUN_SetMasterVolume(section2_data[0x20])` → offset 0x20 = master volume

2. Search for string references near field accesses:
   - Look for debug strings, error messages, UI labels
   - These often directly name the setting

**Method B: Dynamic Analysis (WinDBG)**

1. Set memory watchpoints on decompressed section buffers:
   ```
   ba r4 <section2_base>+0x20
   ```

2. When breakpoint hits:
   - Examine call stack to identify caller
   - Trace to UI or gameplay system
   - Map offset → feature name

3. Repeat for all significant offsets

**Deliverable:** `FIELD_MAPPING_TABLE.md` listing offset → setting → data type → range

---

### Phase 4: Bitfield Documentation

**Objective:** Identify and document all boolean flags and multi-bit enums

1. **Find bitwise operations in code:**
   - Search for `&`, `|`, `<<`, `>>` operations on section data
   - Example: `if (data[0x5C] & 0x01)` → bit 0 at offset 0x5C is a flag

2. **Document each bit:**
   - Offset, bit position, meaning
   - Example: "Section 2, offset 0x5C, bit 0: Subtitles enabled"

3. **Identify multi-bit fields:**
   - Look for masks like `& 0x0F` (4-bit field), `& 0x03` (2-bit field)
   - Document possible values and meanings

**Deliverable:** `BITFIELD_REFERENCE.md` with complete flag tables

---

### Phase 5: Value Constraints & Validation

**Objective:** Document valid ranges, defaults, and boundary checks

1. **Find validation code:**
   - Search for comparison operations (`<`, `>`, `==`, `!=`) on field values
   - Identify clamping logic (min/max enforcement)

2. **Extract default values:**
   - Look for initialization code when creating new save files
   - Document factory defaults for each setting

3. **Document ranges:**
   - Min/max values for numeric fields
   - Enum values for categorical fields
   - String length limits (if applicable)

**Deliverable:** `VALUE_CONSTRAINTS.md` with validation rules

---

### Phase 6: Cross-Section References

**Objective:** Identify relationships between sections

1. **Trace data flow between sections:**
   - Does Section 1 data influence Section 2 parsing?
   - Are there offset pointers between sections?

2. **Document dependencies:**
   - Which sections must be parsed in order?
   - Conditional parsing based on flags in other sections?

**Deliverable:** `SECTION_RELATIONSHIPS.md` describing inter-section dependencies

---

## Output Format Requirements

For each deliverable, use this structure:

### C Structure Definitions
```c
/* Section N Decompressed Data - XXX bytes */
typedef struct {
    uint32_t field_0x00;      /* Description, function ref */
    uint8_t  flags_0x04;      /* Bitfield, see BITFIELD_REFERENCE */
    float    setting_0x08;    /* Range: min-max, default: value */
    // ...
} SectionN_Data;
```

### Field Tables
| Offset | Name | Type | Size | Range | Default | Description | Function Ref |
|--------|------|------|------|-------|---------|-------------|--------------|
| 0x00 | field_name | uint32_t | 4 | 0-100 | 50 | Purpose | FUN_XXXXXXXX |

### Bitfield Tables
| Offset | Bit | Mask | Name | Values | Description |
|--------|-----|------|------|--------|-------------|
| 0x5C | 0 | 0x01 | subtitles_enabled | 0=off, 1=on | Enable subtitles |
| 0x5C | 1 | 0x02 | hud_enabled | 0=off, 1=on | Enable HUD |

---

## Success Criteria

Your work is complete when:

1. ✅ Every byte in each decompressed section is accounted for
2. ✅ All hashes are resolved or marked as unresolved with reasoning
3. ✅ Field → setting mappings cover all major game features
4. ✅ All bitfields are documented with meanings
5. ✅ Value constraints documented for editable fields
6. ✅ C structures compile and match actual data layout

---

## Methodology Guidelines

- **Cite function references:** Always include Ghidra function addresses (e.g., `FUN_01712ca0`)
- **Show evidence:** Include hex dumps, decompiled code snippets as proof
- **Handle unknowns:** If you can't determine a field's purpose, mark it as `unknown_0xNN` and document why
- **Validate with samples:** Test structures against all 24 sample files
- **Document assumptions:** Note any educated guesses vs confirmed facts

---

## Priority Order

1. **Section 2 (Game Settings)** - Highest value, contains most user-visible settings
2. **Section 1 (System/Profile)** - Platform identification, critical for save validation  
3. **Section 3 (Progress)** - Achievement/unlock tracking
4. **Section 4 (PS3 Controller)** - PS3-specific, lower priority

---

## Expected Timeline

- Phase 1-3: High priority, maximum detail required
- Phase 4-6: Medium priority, document what's discoverable
- Total estimated effort: Thorough reverse engineering of 4 sections

---

## Questions to Answer

As you work, try to answer these:

1. What is the hash algorithm used for constants like `0x305AE1A8`?
2. Are there embedded string tables or are all strings externalized?
3. Do sections reference each other via offsets or are they independent?
4. What happens if a field value is outside valid range? (Is it clamped? Rejected?)
5. Are there version fields indicating save file format revisions?
6. What fields differ between PC and PS3 beyond section count?
7. Are there any encrypted or obfuscated fields?

---

## Final Deliverables

Submit the following documents:

1. `SECTION_DATA_STRUCTURES.md` - Complete C struct definitions
2. `HASH_RESOLUTION_TABLE.md` - Hash → identifier mappings  
3. `FIELD_MAPPING_TABLE.md` - Offset → setting mappings
4. `BITFIELD_REFERENCE.md` - Flag and enum documentation
5. `VALUE_CONSTRAINTS.md` - Validation rules and ranges
6. `SECTION_RELATIONSHIPS.md` - Cross-section dependencies
7. `FUNCTION_CALL_TREE.md` - Which functions parse which sections

Additionally, update the main `OPTIONS_FORMAT_SPECIFICATION.md` with new sections incorporating all findings.

---

## Notes

- The existing specification is authoritative for file structure, headers, and compression
- Focus on the **decompressed data payload** - that's the gap
- Use differential analysis: compare OPTIONS files with different settings to isolate field changes
- WinDBG traces are your ground truth - when in doubt, trust runtime behavior

---

**Good luck! This will complete the most comprehensive AC Brotherhood OPTIONS format documentation ever created.**
