# AC Brotherhood OPTIONS File Tools

Reverse-engineered LZSS compression/decompression tools for Assassin's Creed Brotherhood's OPTIONS save files. Achieves **100% byte-for-byte accuracy** with the game's implementation.

## Tools

| Tool | Description |
|------|-------------|
| `lzss_decompressor_final.py` | Decompress OPTIONS files with full header/checksum validation |
| `lzss_compressor_final.py` | Compress data using the exact game LZSS algorithm |
| `options_serializer.py` | Rebuild complete OPTIONS files from decompressed sections |

## Usage

### Decompress an OPTIONS file
```bash
# Decompress all 3 sections
python lzss_decompressor_final.py OPTIONS.bin

# Decompress specific section (1, 2, or 3)
python lzss_decompressor_final.py OPTIONS.bin 2
```
Outputs: `game_uncompressed_1.bin`, `game_uncompressed_2.bin`, `game_uncompressed_3.bin`

### Rebuild an OPTIONS file
```bash
python options_serializer.py section1.bin section2.bin section3.bin -o OPTIONS.bin
```

### Compress a single file
```bash
python lzss_compressor_final.py input.bin output.bin
```

## File Structure

Each OPTIONS file contains 3 compressed sections + 5-byte footer:

```
[Section 1: 44-byte header + LZSS compressed data]
[Section 2: 44-byte header + LZSS compressed data]
[Section 3: 44-byte header + LZSS compressed data]
[Footer: 01 00 00 00 54]
```

## Documentation

See `docs/` for detailed reverse engineering notes:
- `LZSS_LOGIC_FLOW_ANALYSIS.md` - Compression algorithm details
- `OPTIONS_Header_*.md` - File format specifications

## Requirements

- Python 3.6+
- No external dependencies

## License

This project is for educational and research purposes.
