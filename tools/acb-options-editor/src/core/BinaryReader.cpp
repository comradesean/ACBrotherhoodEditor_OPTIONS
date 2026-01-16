#include "BinaryReader.h"

namespace acb {

BinaryReader::BinaryReader(const QByteArray& data, int offset, Endian endian)
    : m_data(data)
    , m_pos(offset)
    , m_endian(endian)
{
}

uint8_t BinaryReader::readU8()
{
    uint8_t val = static_cast<uint8_t>(m_data[m_pos]);
    m_pos += 1;
    return val;
}

uint16_t BinaryReader::readU16()
{
    uint16_t val;
    if (m_endian == Endian::Little) {
        val = qFromLittleEndian<uint16_t>(m_data.constData() + m_pos);
    } else {
        val = qFromBigEndian<uint16_t>(m_data.constData() + m_pos);
    }
    m_pos += 2;
    return val;
}

uint32_t BinaryReader::readU32()
{
    uint32_t val;
    if (m_endian == Endian::Little) {
        val = qFromLittleEndian<uint32_t>(m_data.constData() + m_pos);
    } else {
        val = qFromBigEndian<uint32_t>(m_data.constData() + m_pos);
    }
    m_pos += 4;
    return val;
}

uint64_t BinaryReader::readU64()
{
    uint64_t val;
    if (m_endian == Endian::Little) {
        val = qFromLittleEndian<uint64_t>(m_data.constData() + m_pos);
    } else {
        val = qFromBigEndian<uint64_t>(m_data.constData() + m_pos);
    }
    m_pos += 8;
    return val;
}

int8_t BinaryReader::readS8()
{
    return static_cast<int8_t>(readU8());
}

int16_t BinaryReader::readS16()
{
    return static_cast<int16_t>(readU16());
}

int32_t BinaryReader::readS32()
{
    return static_cast<int32_t>(readU32());
}

int64_t BinaryReader::readS64()
{
    return static_cast<int64_t>(readU64());
}

float BinaryReader::readFloat32()
{
    uint32_t bits = readU32();
    float val;
    memcpy(&val, &bits, sizeof(float));
    return val;
}

double BinaryReader::readFloat64()
{
    uint64_t bits = readU64();
    double val;
    memcpy(&val, &bits, sizeof(double));
    return val;
}

QByteArray BinaryReader::readBytes(int n)
{
    QByteArray val = m_data.mid(m_pos, n);
    m_pos += n;
    return val;
}

uint8_t BinaryReader::peekU8() const
{
    return static_cast<uint8_t>(m_data[m_pos]);
}

uint32_t BinaryReader::peekU32() const
{
    if (m_endian == Endian::Little) {
        return qFromLittleEndian<uint32_t>(m_data.constData() + m_pos);
    } else {
        return qFromBigEndian<uint32_t>(m_data.constData() + m_pos);
    }
}

} // namespace acb
