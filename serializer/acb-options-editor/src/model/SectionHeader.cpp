#include "SectionHeader.h"
#include "core/BinaryReader.h"
#include "core/BinaryWriter.h"
#include <QDebug>

namespace acb {

SectionHeader::SectionHeader()
    : m_headerOffset(0)
    , m_dataOffset(0)
    , m_compressedSize(0)
    , m_uncompressedSize(0)
    , m_checksum(0)
    , m_sectionId(0)
    , m_platform(Platform::Unknown)
    , m_valid(false)
    , m_field0(0)
    , m_field1(0)
{
}

bool SectionHeader::parse(BinaryReader& reader, Platform platform)
{
    m_platform = platform;
    m_headerOffset = reader.tell();
    m_valid = false;

    if (reader.remaining() < SECTION_HEADER_SIZE) {
        return false;
    }

    // Save raw header for round-trip
    m_rawHeader = reader.readBytes(SECTION_HEADER_SIZE);
    BinaryReader headerReader(m_rawHeader);

    // Fields 0-2 are platform-dependent (BE for PS3, LE for PC)
    if (platform == Platform::PS3) {
        headerReader.setEndian(Endian::Big);
    }

    m_field0 = headerReader.readU32();  // Unknown field at 0x00
    m_field1 = headerReader.readU32();  // Unknown field at 0x04
    uint32_t field2 = headerReader.readU32();  // Section ID

    // Fields 3+ are always little-endian
    headerReader.setEndian(Endian::Little);

    uint32_t field3 = headerReader.readU32();  // Uncompressed size (0x0C)
    QByteArray magic = headerReader.readBytes(16);  // Magic pattern at offset 0x10
    uint32_t compressedSize = headerReader.readU32();  // Compressed size (0x20)
    uint32_t uncompressedCopy = headerReader.readU32();  // Copy of field3 (0x24)
    uint32_t checksum = headerReader.readU32();  // Checksum (0x28)
    Q_UNUSED(uncompressedCopy);

    // Validate magic pattern
    if (magic != MAGIC_PATTERN) {
        return false;
    }

    m_sectionId = field2;
    m_uncompressedSize = static_cast<int>(field3);
    m_compressedSize = static_cast<int>(compressedSize);
    m_checksum = checksum;
    m_dataOffset = m_headerOffset + SECTION_HEADER_SIZE;
    m_valid = true;

    return true;
}

void SectionHeader::serialize(BinaryWriter& writer, Platform platform) const
{
    // If we have raw header, use it for perfect round-trip
    if (!m_rawHeader.isEmpty()) {
        writer.writeBytes(m_rawHeader);
        return;
    }

    // Build new header (44 bytes total)
    BinaryWriter headerWriter;

    // Fields 0-2 are platform-dependent
    if (platform == Platform::PS3) {
        headerWriter.setEndian(Endian::Big);
    }

    headerWriter.writeU32(m_field0);     // field0 (0x00) - preserved
    headerWriter.writeU32(m_field1);     // field1 (0x04) - preserved
    headerWriter.writeU32(m_sectionId);  // field2 (0x08) - section ID

    // Fields 3+ are always little-endian
    headerWriter.setEndian(Endian::Little);

    headerWriter.writeU32(static_cast<uint32_t>(m_uncompressedSize));  // 0x0C - uncompressed size
    headerWriter.writeBytes(MAGIC_PATTERN);                            // 0x10 - magic (16 bytes)
    headerWriter.writeU32(static_cast<uint32_t>(m_compressedSize));    // 0x20 - compressed size
    headerWriter.writeU32(static_cast<uint32_t>(m_uncompressedSize));  // 0x24 - uncompressed copy
    headerWriter.writeU32(m_checksum);                                 // 0x28 - checksum
    // Total: 44 bytes (0x2C)

    writer.writeBytes(headerWriter.data());
}

void SectionHeader::build(uint32_t sectionId, int uncompressedSize, int compressedSize, uint32_t checksum, Platform platform)
{
    m_sectionId = sectionId;
    m_uncompressedSize = uncompressedSize;
    m_compressedSize = compressedSize;
    m_checksum = checksum;
    m_platform = platform;
    m_valid = true;
    m_rawHeader.clear();  // Clear raw header so serialize() builds new one
}

int SectionHeader::sectionNumber() const
{
    switch (m_sectionId) {
        case 0x000000C5:  // Section 1 PC
        case 0x000000C6:  // Section 1 PS3
            return 1;
        case 0x11FACE11:  // Section 2
            return 2;
        case 0x21EFFE22:  // Section 3
            return 3;
        case 0x00000007:  // Section 4
            return 4;
        default:
            return 0;  // Unknown
    }
}

QString SectionHeader::sectionName() const
{
    switch (sectionNumber()) {
        case 1: return "SaveGame";
        case 2: return "AssassinGlobalProfileData";
        case 3: return "AssassinSingleProfileData";
        case 4: return "AssassinMultiProfileData";
        default: return QString("Unknown (0x%1)").arg(m_sectionId, 8, 16, QChar('0'));
    }
}

} // namespace acb
