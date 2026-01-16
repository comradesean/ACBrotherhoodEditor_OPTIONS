#include "BinaryWriter.h"
#include "BinaryReader.h" // For Endian enum

namespace acb {

BinaryWriter::BinaryWriter(Endian endian)
    : m_endian(endian)
{
}

void BinaryWriter::writeU8(uint8_t val)
{
    m_data.append(static_cast<char>(val));
}

void BinaryWriter::writeU16(uint16_t val)
{
    char buf[2];
    if (m_endian == Endian::Little) {
        qToLittleEndian(val, buf);
    } else {
        qToBigEndian(val, buf);
    }
    m_data.append(buf, 2);
}

void BinaryWriter::writeU32(uint32_t val)
{
    char buf[4];
    if (m_endian == Endian::Little) {
        qToLittleEndian(val, buf);
    } else {
        qToBigEndian(val, buf);
    }
    m_data.append(buf, 4);
}

void BinaryWriter::writeU64(uint64_t val)
{
    char buf[8];
    if (m_endian == Endian::Little) {
        qToLittleEndian(val, buf);
    } else {
        qToBigEndian(val, buf);
    }
    m_data.append(buf, 8);
}

void BinaryWriter::writeS8(int8_t val)
{
    writeU8(static_cast<uint8_t>(val));
}

void BinaryWriter::writeS16(int16_t val)
{
    writeU16(static_cast<uint16_t>(val));
}

void BinaryWriter::writeS32(int32_t val)
{
    writeU32(static_cast<uint32_t>(val));
}

void BinaryWriter::writeS64(int64_t val)
{
    writeU64(static_cast<uint64_t>(val));
}

void BinaryWriter::writeFloat32(float val)
{
    uint32_t bits;
    memcpy(&bits, &val, sizeof(float));
    writeU32(bits);
}

void BinaryWriter::writeFloat64(double val)
{
    uint64_t bits;
    memcpy(&bits, &val, sizeof(double));
    writeU64(bits);
}

void BinaryWriter::writeBytes(const QByteArray& data)
{
    m_data.append(data);
}

void BinaryWriter::writeBytes(const char* data, int len)
{
    m_data.append(data, len);
}

int BinaryWriter::openSection()
{
    int pos = m_data.size();
    writeU32(0);  // Placeholder for size
    m_sectionStack.push(pos);
    return pos;
}

int BinaryWriter::closeSection()
{
    int startPos = m_sectionStack.pop();
    int contentStart = startPos + 4;  // Content begins after 4-byte size field
    int blockSize = m_data.size() - contentStart;
    writeAt(startPos, static_cast<uint32_t>(blockSize));
    return blockSize;
}

void BinaryWriter::writeAt(int pos, uint32_t val)
{
    char buf[4];
    if (m_endian == Endian::Little) {
        qToLittleEndian(val, buf);
    } else {
        qToBigEndian(val, buf);
    }
    for (int i = 0; i < 4; ++i) {
        m_data[pos + i] = buf[i];
    }
}

} // namespace acb
