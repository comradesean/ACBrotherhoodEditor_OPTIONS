# AC Brotherhood OPTIONS File Tools

Reverse-engineered LZSS compression/decompression tools for Assassin's Creed Brotherhood's OPTIONS save files. Achieves **100% byte-for-byte accuracy** with the game's implementation.

## Tools

### Unified Tools (Recommended)
| Tool | Description |
|------|-------------|
| `options_unpack.py` | Extract and decompress sections from OPTIONS files (auto-detects PC/PS3) |
| `options_pack.py` | Rebuild OPTIONS files from decompressed sections (supports PC and PS3) |

## Usage

### Unified Tools (Recommended)

#### Unpack an OPTIONS file
```bash
# Auto-detect format, extract all sections
python options_unpack.py OPTIONS.bin

# Extract specific section (1-4)
python options_unpack.py OPTIONS.bin 2

# Force specific format
python options_unpack.py OPTIONS.bin --pc
python options_unpack.py OPTIONS.PS3 --ps3

# Custom output directory
python options_unpack.py OPTIONS.bin -o ./output/
```
Outputs: `section1.bin`, `section2.bin`, `section3.bin`, and optionally `section4.bin`

#### Pack sections into an OPTIONS file
```bash
# PC format (3 sections)
python options_pack.py section1.bin section2.bin section3.bin -o OPTIONS.bin --pc

# PS3 format (4 sections)
python options_pack.py section1.bin section2.bin section3.bin section4.bin -o OPTIONS.PS3 --ps3

# With validation (decompresses and verifies output)
python options_pack.py section1.bin section2.bin section3.bin -o OPTIONS.bin --pc --validate
```

## Section Structure

Each OPTIONS file contains 3 or 4 compressed sections. Section 4 is optional on both PC and PS3.

| Section | Name | Description |
|---------|------|-------------|
| 1 | SaveGame | Core save game data |
| 2 | AssassinGlobalProfileData | Global profile settings |
| 3 | AssassinSingleProfileData | Single-player profile data |
| 4 | AssassinMultiProfileData | Multiplayer profile data (optional) |

## File Structure

### PC OPTIONS File
```
[Section 1: 44-byte header + LZSS compressed data]
[Section 2: 44-byte header + LZSS compressed data]
[Section 3: 44-byte header + LZSS compressed data]
[8-byte gap marker (if Section 4 present)]
[Section 4: 44-byte header + LZSS compressed data (optional)]
[Footer: 01 00 00 00 XX]
```

### PS3 OPTIONS File
```
[8-byte prefix: size (BE) + CRC32 (BE)]
[Section 1: 44-byte header + LZSS compressed data]
[Section 2: 44-byte header + LZSS compressed data]
[Section 3: 44-byte header + LZSS compressed data]
[8-byte gap marker (if Section 4 present)]
[Section 4: 44-byte header + LZSS compressed data (optional)]
[Zero padding to 51,200 bytes]
```

## Documentation

See `docs/` for detailed reverse engineering notes:
- `LZSS_LOGIC_FLOW_ANALYSIS.md` - Compression algorithm details
- `PS3_OPTIONS_FORMAT.md` - PS3 format specification
- `PS3_vs_PC_STRUCTURE_ANALYSIS.md` - PC/PS3 format differences
- `ACB_OPTIONS_Header_Complete_Specification.md` - Complete header specification

## Requirements

- Python 3.6+
- No external dependencies

## License

This project is for educational and research purposes.
