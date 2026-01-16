#pragma once

#include <QByteArray>
#include <cstdint>

namespace acb {

class Checksum {
public:
    // Adler-32 with zero seed (AC Brotherhood variant)
    // Standard Adler-32 uses s1=1, s2=0. This game uses s1=0, s2=0.
    static uint32_t adler32ZeroSeed(const QByteArray& data);

    // CRC32 using PS3's custom parameters
    // poly=0x04C11DB7, init=0xBAE23CD0, xorout=0xFFFFFFFF
    // refin=true, refout=true
    static uint32_t crc32PS3(const QByteArray& data);

private:
    // Helper to reflect bits
    static uint8_t reflectByte(uint8_t b);
    static uint32_t reflectU32(uint32_t v);
};

} // namespace acb
