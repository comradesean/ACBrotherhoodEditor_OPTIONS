#pragma once

#include <QByteArray>
#include <QtEndian>
#include <cstdint>

namespace acb {

enum class Endian {
    Little,
    Big
};

class BinaryReader {
public:
    explicit BinaryReader(const QByteArray& data, int offset = 0, Endian endian = Endian::Little);

    // Read unsigned integers
    uint8_t readU8();
    uint16_t readU16();
    uint32_t readU32();
    uint64_t readU64();

    // Read signed integers
    int8_t readS8();
    int16_t readS16();
    int32_t readS32();
    int64_t readS64();

    // Read floating point
    float readFloat32();
    double readFloat64();

    // Read raw bytes
    QByteArray readBytes(int n);

    // Peek without advancing
    uint8_t peekU8() const;
    uint32_t peekU32() const;

    // Position control
    int tell() const { return m_pos; }
    void seek(int pos) { m_pos = pos; }
    void skip(int n) { m_pos += n; }
    int remaining() const { return m_data.size() - m_pos; }
    int size() const { return m_data.size(); }
    bool atEnd() const { return m_pos >= m_data.size(); }

    // Endian control
    void setEndian(Endian endian) { m_endian = endian; }
    Endian endian() const { return m_endian; }

    // Access to underlying data
    const QByteArray& data() const { return m_data; }

private:
    QByteArray m_data;
    int m_pos;
    Endian m_endian;
};

} // namespace acb
