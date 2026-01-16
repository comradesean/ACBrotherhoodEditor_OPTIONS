  PS3 SAV Format Differences

  | Feature           | PC                  | PS3                               |
  |-------------------|---------------------|-----------------------------------|
  | Prefix            | None                | 8-byte: [size 4B BE][CRC32 4B BE] |
  | Header fields 0-2 | Little-endian       | Big-endian                        |
  | Size fields       | Little-endian       | Little-endian (same)              |
  | File size         | Variable            | Padded to 307,200 bytes           |
  | Checksum          | Adler32 (zero-seed) | CRC32 custom (init=0xBAE23CD0)    |
  | Cape structure    | Same                | Same (LE hashes)                  |

  PS3 CRC32 Parameters

  poly=0x04C11DB7, init=0xBAE23CD0, xorout=0xFFFFFFFF, refin=true, refout=true

  Usage

  # Unlock capes
  python cape_unlocker_ps3.py AC2_0.SAV

  # Unlock capes + change name
  python cape_unlocker_ps3.py AC2_0.SAV --name "Ezio"

  # Verbose output
  python cape_unlocker_ps3.py AC2_0.SAV -v