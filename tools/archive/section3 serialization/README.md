# Section 3 Serialization Documentation

Documentation for Assassin's Creed Brotherhood save file Section 3 binary format.

## Documentation Files

| File | Purpose |
|------|---------|
| [SECTION3_SERIALIZATION.md](docs/SECTION3_SERIALIZATION.md) | Main doc - format spec & core concepts |
| [FUNCTIONS.md](docs/FUNCTIONS.md) | Detailed function documentation |
| [TYPE_CODES.md](docs/TYPE_CODES.md) | Type code reference table |
| [VTABLES.md](docs/VTABLES.md) | VTable reference |
| [STREAM_IO.md](docs/STREAM_IO.md) | Stream I/O functions |
| [DIAGRAMS.md](docs/DIAGRAMS.md) | Visual diagrams |
| [TRACES.md](docs/TRACES.md) | Execution traces |
| [DISASSEMBLY.md](docs/DISASSEMBLY.md) | Assembly code |
| [PROPERTY_DESCRIPTORS.md](docs/PROPERTY_DESCRIPTORS.md) | Property hex dumps |

## Quick Reference

**Property format:** `[size 4][hash 4][type_info 8][flags 1][value N]`

**Type codes (byte 6 of type_info):**
- `0x00` = bool (1 byte)
- `0x07` = uint32 (4 bytes)
- `0x09` = uint64 (8 bytes)

**Reference implementation:** [section3_parser.py](section3_parser.py)
