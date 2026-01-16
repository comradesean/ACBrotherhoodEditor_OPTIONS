#pragma once

#include <QByteArray>
#include <cstdint>
#include "core/TypeCodes.h"

namespace acb {

class BinaryReader;
class BinaryWriter;

// Magic pattern found at offset 0x10 in each section header
static const QByteArray MAGIC_PATTERN = QByteArray::fromHex("33AAFB5799FA04100100020080000001");

// Section header size is 44 bytes
static const int SECTION_HEADER_SIZE = 44;

// PS3 file padding size
static const int PS3_FILE_SIZE = 51200;

class SectionHeader {
public:
    SectionHeader();

    // Parse header from binary data at current position
    bool parse(BinaryReader& reader, Platform platform);

    // Serialize header to binary
    void serialize(BinaryWriter& writer, Platform platform) const;

    // Build header for a new section
    void build(uint32_t sectionId, int uncompressedSize, int compressedSize, uint32_t checksum, Platform platform);

    // Accessors
    int headerOffset() const { return m_headerOffset; }
    int dataOffset() const { return m_dataOffset; }
    int compressedSize() const { return m_compressedSize; }
    int uncompressedSize() const { return m_uncompressedSize; }
    uint32_t checksum() const { return m_checksum; }
    uint32_t sectionId() const { return m_sectionId; }
    Platform platform() const { return m_platform; }

    // Section type helpers
    int sectionNumber() const;
    QString sectionName() const;

    // Validate magic pattern
    bool isValid() const { return m_valid; }

private:
    int m_headerOffset;
    int m_dataOffset;
    int m_compressedSize;
    int m_uncompressedSize;
    uint32_t m_checksum;
    uint32_t m_sectionId;
    Platform m_platform;
    bool m_valid;

    // Preserved header fields for round-trip
    uint32_t m_field0;  // Unknown field at 0x00
    uint32_t m_field1;  // Unknown field at 0x04

    // Raw header for perfect round-trip
    QByteArray m_rawHeader;
};

} // namespace acb
