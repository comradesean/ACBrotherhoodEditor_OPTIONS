#include "OptionsFile.h"
#include "core/BinaryReader.h"
#include "core/BinaryWriter.h"
#include "core/Checksum.h"
#include "core/LZSS.h"
#include <QFile>
#include <QDebug>

namespace acb {

OptionsFile::OptionsFile()
    : m_platform(Platform::Unknown)
    , m_valid(false)
{
}

OptionsFile::~OptionsFile()
{
    clearSections();
}

bool OptionsFile::load(const QString& path)
{
    QFile file(path);
    if (!file.open(QIODevice::ReadOnly)) {
        return false;
    }

    QByteArray data = file.readAll();
    file.close();

    m_filePath = path;
    return parseFile(data);
}

bool OptionsFile::save(const QString& path)
{
    QByteArray data = serialize();
    if (data.isEmpty()) {
        return false;
    }

    QFile file(path);
    if (!file.open(QIODevice::WriteOnly)) {
        return false;
    }

    file.write(data);
    file.close();

    m_filePath = path;

    // Clear dirty flags
    for (Section* section : m_sections) {
        section->setDirty(false);
    }

    return true;
}

QByteArray OptionsFile::serialize() const
{
    return buildFile();
}

Section* OptionsFile::section(int index) const
{
    if (index >= 0 && index < m_sections.size()) {
        return m_sections[index];
    }
    return nullptr;
}

void OptionsFile::addSection(Section* section)
{
    if (section) {
        m_sections.append(section);
    }
}

void OptionsFile::removeSection(Section* section)
{
    m_sections.removeOne(section);
    delete section;
}

void OptionsFile::clearSections()
{
    qDeleteAll(m_sections);
    m_sections.clear();
}

bool OptionsFile::isDirty() const
{
    for (const Section* section : m_sections) {
        if (section->isDirty()) {
            return true;
        }
    }
    return false;
}

Platform OptionsFile::detectPlatform(const QByteArray& data)
{
    // Method 1: PS3 files are exactly 51200 bytes
    if (data.size() == PS3_FILE_SIZE) {
        if (data.size() >= 8) {
            BinaryReader reader(data, 0, Endian::Big);
            uint32_t prefixSize = reader.readU32();
            uint32_t prefixCrc = reader.readU32();

            if (prefixSize < static_cast<uint32_t>(data.size() - 8)) {
                uint32_t actualCrc = Checksum::crc32PS3(data.mid(8, prefixSize));
                if (actualCrc == prefixCrc) {
                    return Platform::PS3;
                }
            }
        }
    }

    // Method 2: Check magic pattern location
    QByteArray magicShort = MAGIC_PATTERN.left(4);

    // PC: Magic at offset 0x10
    if (data.size() > 0x14 && data.mid(0x10, 4) == magicShort) {
        return Platform::PC;
    }

    // PS3: Magic at offset 0x18 (8-byte prefix + header at 0x08)
    if (data.size() > 0x1C && data.mid(0x18, 4) == magicShort) {
        return Platform::PS3;
    }

    return Platform::Unknown;
}

bool OptionsFile::parseFile(const QByteArray& data)
{
    clearSections();
    m_valid = false;

    // Detect platform
    m_platform = detectPlatform(data);
    if (m_platform == Platform::Unknown) {
        return false;
    }

    int startOffset = 0;

    // Handle PS3 prefix
    if (m_platform == Platform::PS3) {
        m_ps3Prefix = data.left(8);
        startOffset = 8;
    }

    BinaryReader reader(data, startOffset);

    // Find and parse section headers
    while (reader.remaining() >= SECTION_HEADER_SIZE) {
        // Check for magic pattern at expected offset
        int currentPos = reader.tell();

        // Look for magic pattern
        if (reader.remaining() < SECTION_HEADER_SIZE) {
            break;
        }

        // Try to parse header
        SectionHeader header;
        if (!header.parse(reader, m_platform)) {
            // Check if we hit footer or padding
            reader.seek(currentPos);

            // PC footer check: 01 00 00 00 XX
            if (m_platform == Platform::PC && reader.remaining() >= 5) {
                uint8_t b0 = reader.peekU8();
                if (b0 == 0x01) {
                    m_footer = reader.readBytes(reader.remaining());
                    break;
                }
            }

            // Skip unknown bytes and try again
            reader.skip(1);
            continue;
        }

        // Extract compressed data
        if (reader.remaining() < header.compressedSize()) {
            break;
        }

        QByteArray compressedData = reader.readBytes(header.compressedSize());

        // Decompress
        QByteArray decompressedData = LZSS::decompress(compressedData);

        // Use section ID from header to determine section type
        uint32_t rootHash = 0;
        switch (header.sectionNumber()) {
            case 1: rootHash = SectionHash::SaveGame; break;
            case 2: rootHash = SectionHash::PlayerOptionsSaveData; break;
            case 3: rootHash = SectionHash::AssassinSingleProfileData; break;
            case 4: rootHash = SectionHash::AssassinMultiProfileData; break;
            default: rootHash = 0; break;
        }

        // Create appropriate section type
        Section* section = Section::createFromHash(rootHash);
        section->header() = header;
        section->setRawCompressed(compressedData);
        section->setRawDecompressed(decompressedData);
        section->setRootHash(rootHash);

        // Parse section contents
        section->parse();

        m_sections.append(section);
    }

    // Store any remaining data as footer
    if (m_platform == Platform::PC && m_footer.isEmpty() && reader.remaining() > 0) {
        m_footer = reader.readBytes(reader.remaining());
    }

    m_valid = !m_sections.isEmpty();
    return m_valid;
}

QByteArray OptionsFile::buildFile() const
{
    BinaryWriter writer;

    // PS3 prefix placeholder (will be filled at end)
    int prefixPos = 0;
    if (m_platform == Platform::PS3) {
        prefixPos = writer.tell();
        writer.writeU32(0);  // Size placeholder
        writer.writeU32(0);  // CRC placeholder
    }

    int contentStart = writer.tell();

    // Write each section
    for (const Section* section : m_sections) {
        QByteArray compressed;
        QByteArray decompressed;
        uint32_t checksum;

        // If section is unmodified, use original data for perfect round-trip
        if (!section->isDirty() && !section->rawCompressed().isEmpty()) {
            compressed = section->rawCompressed();
            decompressed = section->rawDecompressed();
            checksum = section->header().checksum();
        } else {
            // Serialize and recompress modified sections
            decompressed = section->serialize();
            compressed = LZSS::compress(decompressed);
            checksum = Checksum::adler32ZeroSeed(compressed);
        }

        // Build header (checksum is stored in header, not after data)
        SectionHeader header = section->header();
        if (section->isDirty()) {
            header.build(header.sectionId(),
                         decompressed.size(),
                         compressed.size(),
                         checksum,
                         m_platform);
        }

        // For section 4, add gap marker before header
        // Gap marker format: (section4_total_size + 4, type)
        // where type=0x0E for PC, 0x08 for PS3
        if (header.sectionNumber() == 4) {
            int section4TotalSize = SECTION_HEADER_SIZE + static_cast<int>(compressed.size());
            uint32_t gapMarkerSize = static_cast<uint32_t>(section4TotalSize + 4);
            uint32_t gapMarkerType = (m_platform == Platform::PS3) ? 0x08 : 0x0E;

            if (m_platform == Platform::PS3) {
                writer.setEndian(Endian::Big);
            } else {
                writer.setEndian(Endian::Little);
            }
            writer.writeU32(gapMarkerSize);
            writer.writeU32(gapMarkerType);
            writer.setEndian(Endian::Little);  // Reset to default
        }

        // Write header
        header.serialize(writer, m_platform);

        // Write compressed data (no separate checksum - it's in header)
        writer.writeBytes(compressed);
    }

    // Write footer (only if original file had one)
    if (m_platform == Platform::PC && !m_footer.isEmpty()) {
        writer.writeBytes(m_footer);
    }

    if (m_platform == Platform::PS3) {
        // Calculate content size and CRC for prefix
        int contentSize = writer.tell() - contentStart;
        QByteArray content = writer.data().mid(contentStart, contentSize);
        uint32_t crc = Checksum::crc32PS3(content);

        // Update prefix (PS3 prefix is big-endian)
        writer.setEndian(Endian::Big);
        writer.writeAt(prefixPos, static_cast<uint32_t>(contentSize));
        writer.writeAt(prefixPos + 4, crc);
        writer.setEndian(Endian::Little);

        // Pad to 51200 bytes
        int paddingNeeded = PS3_FILE_SIZE - writer.tell();
        if (paddingNeeded > 0) {
            QByteArray padding(paddingNeeded, 0);
            writer.writeBytes(padding);
        }
    }

    return writer.data();
}

} // namespace acb
