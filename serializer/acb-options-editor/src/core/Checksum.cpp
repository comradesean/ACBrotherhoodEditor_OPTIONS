#include "Checksum.h"

namespace acb {

uint32_t Checksum::adler32ZeroSeed(const QByteArray& data)
{
    const uint32_t MOD_ADLER = 65521;
    uint32_t s1 = 0;
    uint32_t s2 = 0;

    for (int i = 0; i < data.size(); ++i) {
        s1 = (s1 + static_cast<uint8_t>(data[i])) % MOD_ADLER;
        s2 = (s2 + s1) % MOD_ADLER;
    }

    return (s2 << 16) | s1;
}

uint8_t Checksum::reflectByte(uint8_t b)
{
    uint8_t result = 0;
    for (int i = 0; i < 8; ++i) {
        if (b & (1 << i)) {
            result |= (1 << (7 - i));
        }
    }
    return result;
}

uint32_t Checksum::reflectU32(uint32_t v)
{
    uint32_t result = 0;
    for (int i = 0; i < 32; ++i) {
        if (v & (1u << i)) {
            result |= (1u << (31 - i));
        }
    }
    return result;
}

uint32_t Checksum::crc32PS3(const QByteArray& data)
{
    const uint32_t POLY = 0x04C11DB7;
    uint32_t crc = 0xBAE23CD0;

    for (int i = 0; i < data.size(); ++i) {
        // Reflect input byte
        uint8_t byte = reflectByte(static_cast<uint8_t>(data[i]));
        crc ^= (static_cast<uint32_t>(byte) << 24);

        for (int bit = 0; bit < 8; ++bit) {
            if (crc & 0x80000000) {
                crc = ((crc << 1) ^ POLY) & 0xFFFFFFFF;
            } else {
                crc = (crc << 1) & 0xFFFFFFFF;
            }
        }
    }

    // Reflect output
    crc = reflectU32(crc);
    return (crc ^ 0xFFFFFFFF) & 0xFFFFFFFF;
}

} // namespace acb
