# OPTIONS File Serializer

A complete, self-sufficient tool for recreating Assassin's Creed Brotherhood OPTIONS files from decompressed sections.

## Quick Start

```bash
# Basic usage
python3 options_serializer_pc.py section1.bin section2.bin section3.bin -o OUTPUT.bin

# With validation
python3 options_serializer_pc.py section1.bin section2.bin section3.bin -o OUTPUT.bin --validate

# Using wildcards
python3 options_serializer_pc.py game_uncompressed_*.bin -o OPTIONS.bin --validate
```

## Features

- **Self-contained**: All code embedded in one file, no external dependencies except Python 3
- **LZSS Compression**: Uses the exact lazy-matching LZSS algorithm from the game
- **Proper Headers**: Generates correct section headers with IDs, checksums, and metadata
- **Adler-32 Checksums**: Implements the game's non-standard zero-seed variant
- **Validation**: Built-in decompression and comparison to verify output
- **Round-trip Safe**: Decompress → Recompress → Decompress produces identical data

## File Structure

The script recreates OPTIONS files with this structure:

```
┌─────────────────────────────────────────┐
│ Section 1 Header (44 bytes)             │
│  - Section ID (16 bytes)                │
│  - Common pattern (16 bytes)            │
│  - Compressed length (4 bytes)          │
│  - Uncompressed length (4 bytes)        │
│  - Adler-32 checksum (4 bytes)          │
├─────────────────────────────────────────┤
│ Section 1 Data (LZSS compressed)        │
├─────────────────────────────────────────┤
│ Section 2 Header (44 bytes)             │
├─────────────────────────────────────────┤
│ Section 2 Data (LZSS compressed)        │
├─────────────────────────────────────────┤
│ Section 3 Header (44 bytes)             │
├─────────────────────────────────────────┤
│ Section 3 Data (LZSS compressed)        │
└─────────────────────────────────────────┘
```

## Section IDs

The script uses hardcoded section IDs that are constant across all AC Brotherhood OPTIONS files:

**Section 1** (283 bytes uncompressed):
```
16 00 00 00 AC DB FE 00 C5 00 00 00 1B 01 00 00
```

**Section 2** (1310 bytes uncompressed):
```
AB 02 00 00 03 00 00 00 11 CE FA 11 1E 05 00 00
```

**Section 3** (162 bytes uncompressed):
```
84 00 00 00 00 00 00 00 22 FE EF 21 A2 00 00 00
```

Note: The last 4 bytes of each ID contain the uncompressed size in little-endian format.

## Common Pattern

All sections share this 16-byte pattern:
```
33 AA FB 57 99 FA 04 10 01 00 02 00 80 00 00 01
```

## Examples

### Example 1: Create OPTIONS from existing decompressed sections
```bash
python3 options_serializer_pc.py \
  references/OPTIONS.WINDBGTRACE/game_uncompressed_1.bin \
  references/OPTIONS.WINDBGTRACE/game_uncompressed_2.bin \
  references/OPTIONS.WINDBGTRACE/game_uncompressed_3.bin \
  -o my_OPTIONS.bin
```

### Example 2: Create and validate
```bash
python3 options_serializer_pc.py \
  section1.bin section2.bin section3.bin \
  -o OPTIONS.bin \
  --validate
```

### Example 3: Full workflow (decompress → modify → recompress)
```bash
# 1. Decompress original
python3 lzss_decompressor_pc.py original_OPTIONS.bin

# 2. Modify the decompressed sections (edit game_uncompressed_*.bin)
# ... make your changes ...

# 3. Recompress into new OPTIONS file
python3 options_serializer_pc.py \
  game_uncompressed_1.bin \
  game_uncompressed_2.bin \
  game_uncompressed_3.bin \
  -o modified_OPTIONS.bin \
  --validate
```

## Output

The script provides detailed output:

```
======================================================================
OPTIONS File Serializer for AC Brotherhood
======================================================================

Processing Section 1:
  Input file: game_uncompressed_1.bin
  Uncompressed size: 283 bytes
  Compressed size: 165 bytes (58.3%)
  Header size: 44 bytes
  Checksum: 0xF47135C9

Processing Section 2:
  Input file: game_uncompressed_2.bin
  Uncompressed size: 1310 bytes
  Compressed size: 643 bytes (49.1%)
  Header size: 44 bytes
  Checksum: 0x47F0C2A3

Processing Section 3:
  Input file: game_uncompressed_3.bin
  Uncompressed size: 162 bytes
  Compressed size: 92 bytes (56.8%)
  Header size: 44 bytes
  Checksum: 0x28401B93

======================================================================
SERIALIZATION COMPLETE
======================================================================

Output file: OPTIONS.bin
Total size: 1032 bytes
  Headers: 132 bytes
  Compressed data: 900 bytes
  Uncompressed data: 1755 bytes
  Overall compression ratio: 1.95x
```

## Validation Output

With `--validate`, the script also shows:

```
======================================================================
VALIDATION: Decompressing and Comparing
======================================================================

Validating Section 1:
  Decompressed size: 283 bytes
  Original size: 283 bytes
  Match: YES
  Header validation:
    Compressed size: 165 bytes (expected: 165)
    Uncompressed size: 283 bytes (expected: 283)
    Checksum: 0xF47135C9

[... sections 2 and 3 ...]

======================================================================
VALIDATION PASSED: All sections match original data!
======================================================================
```

## Technical Details

### LZSS Compression
- Uses lazy matching for optimal compression
- 2-byte zero prefix buffer
- Supports short matches (2-5 bytes, offset 1-256)
- Supports long matches (3+ bytes, offset 0-8191)
- Variable-length encoding for very long matches

### Adler-32 Checksum
- **Non-standard zero-seed variant**: s1=0, s2=0
- Standard Adler-32 uses s1=1, s2=0
- Calculated over compressed data only
- Stored in little-endian format

### Compression Differences
The serializer's compression may differ byte-for-byte from the original game compression, but:
- ✓ Decompressed output is **identical**
- ✓ Checksums are valid for the generated compression
- ✓ Files work correctly in-game

This is expected - LZSS allows multiple valid compressed representations of the same data.

## Testing

Run the round-trip test to verify everything works:

```bash
bash test_roundtrip.sh
```

This will:
1. Decompress an original OPTIONS file
2. Recompress it using the serializer
3. Decompress the result
4. Compare to ensure perfect data reconstruction

## Requirements

- Python 3.6+
- No external dependencies

## Files

- `options_serializer_pc.py` - The main serializer script (self-contained)
- `lzss_decompressor_pc.py` - Decompressor (needed for validation)
- `test_roundtrip.sh` - Comprehensive round-trip test
- `SERIALIZER_ANALYSIS.md` - Detailed technical analysis

## License

This tool is for educational and modding purposes.
Assassin's Creed Brotherhood © Ubisoft.
