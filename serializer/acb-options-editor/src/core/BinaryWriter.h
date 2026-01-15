#pragma once

#include "BinaryReader.h"  // For Endian enum
#include <QByteArray>
#include <QStack>
#include <QtEndian>
#include <cstdint>

namespace acb {

class BinaryWriter {
public:
    explicit BinaryWriter(Endian endian = Endian::Little);

    // Write unsigned integers
    void writeU8(uint8_t val);
    void writeU16(uint16_t val);
    void writeU32(uint32_t val);
    void writeU64(uint64_t val);

    // Write signed integers
    void writeS8(int8_t val);
    void writeS16(int16_t val);
    void writeS32(int32_t val);
    void writeS64(int64_t val);

    // Write floating point
    void writeFloat32(float val);
    void writeFloat64(double val);

    // Write raw bytes
    void writeBytes(const QByteArray& data);
    void writeBytes(const char* data, int len);

    // Sized block management (LIFO backpatching)
    // Opens a sized block by writing a 4-byte placeholder, returns position
    int openSection();
    // Closes a sized block by backpatching the size
    int closeSection();

    // Position control
    int tell() const { return m_data.size(); }
    void writeAt(int pos, uint32_t val);

    // Get result
    QByteArray data() const { return m_data; }
    void clear() { m_data.clear(); m_sectionStack.clear(); }

    // Endian control
    void setEndian(Endian endian) { m_endian = endian; }
    Endian endian() const { return m_endian; }

private:
    QByteArray m_data;
    QStack<int> m_sectionStack;
    Endian m_endian;
};

} // namespace acb
