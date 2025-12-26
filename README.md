# AC Brotherhood OPTIONS File Tools

Reverse-engineered LZSS compression/decompression tools for Assassin's Creed Brotherhood's OPTIONS save files. Achieves **100% byte-for-byte accuracy** with the game's implementation.

## Tools

### PC Tools
| Tool | Description |
|------|-------------|
| `lzss_decompressor_pc.py` | Decompress PC OPTIONS files (3 sections) with header/checksum validation |
| `lzss_compressor_pc.py` | Compress data using the exact game LZSS algorithm |
| `options_serializer_pc.py` | Rebuild complete PC OPTIONS files from decompressed sections |

### PS3 Tools
| Tool | Description |
|------|-------------|
| `lzss_decompressor_ps3.py` | Decompress PS3 OPTIONS files (4 sections) with CRC32/header validation |
| `options_serializer_ps3.py` | Rebuild complete PS3 OPTIONS files from decompressed sections |

## Usage

### PC OPTIONS Files

#### Decompress a PC OPTIONS file
```bash
# Decompress all 3 sections
python lzss_decompressor_pc.py OPTIONS.bin

# Decompress specific section (1, 2, or 3)
python lzss_decompressor_pc.py OPTIONS.bin 2
```
Outputs: `section1.bin`, `section2.bin`, `section3.bin`

#### Rebuild a PC OPTIONS file
```bash
python options_serializer_pc.py section1.bin section2.bin section3.bin -o OPTIONS.bin
```

#### Compress a single file
```bash
python lzss_compressor_pc.py input.bin output.bin
```

### PS3 OPTIONS Files

#### Decompress a PS3 OPTIONS file
```bash
# Decompress all 4 sections
python lzss_decompressor_ps3.py OPTIONS.PS3

# Decompress specific section (1, 2, 3, or 4)
python lzss_decompressor_ps3.py OPTIONS.PS3 2
```
Outputs: `section1.bin`, `section2.bin`, `section3.bin`, `section4.bin`

Section 4 contains DualShock 3 controller mappings (PS3-only).

#### Rebuild a PS3 OPTIONS file
```bash
# With all 4 sections (includes controller mappings)
python options_serializer_ps3.py section1.bin section2.bin section3.bin section4.bin -o OPTIONS.PS3

# With 3 sections only (no controller mappings)
python options_serializer_ps3.py section1.bin section2.bin section3.bin -o OPTIONS.PS3

# With validation (decompresses and verifies output)
python options_serializer_ps3.py section1.bin section2.bin section3.bin section4.bin -o OPTIONS.PS3 --validate
```

## File Structure

### PC OPTIONS File (3 sections)
```
[Section 1: 44-byte header + LZSS compressed data]
[Section 2: 44-byte header + LZSS compressed data]
[Section 3: 44-byte header + LZSS compressed data]
[Footer: 01 00 00 00 0C]
```

### PS3 OPTIONS File (4 sections)
```
[8-byte prefix: size (BE) + CRC32 (BE)]
[Section 1: 44-byte header + LZSS compressed data]
[Section 2: 44-byte header + LZSS compressed data]
[Section 3: 44-byte header + LZSS compressed data]
[8-byte gap marker: size (BE) + type 0x08 (BE)]
[Section 4: 44-byte header + LZSS compressed data]
[Zero padding to 51,200 bytes]
```

PS3 files have no footer. Section 4 contains DualShock 3 controller mappings.

## Documentation

See `docs/` for detailed reverse engineering notes:
- `LZSS_LOGIC_FLOW_ANALYSIS.md` - Compression algorithm details
- `PS3_OPTIONS_FORMAT.md` - Standalone PS3 format specification
- `PS3_vs_PC_STRUCTURE_ANALYSIS.md` - PC/PS3 format differences and Section 4 analysis
- `ACB_OPTIONS_Header_Complete_Specification.md` - File format specifications

## Requirements

- Python 3.6+
- No external dependencies

## License

This project is for educational and research purposes.
