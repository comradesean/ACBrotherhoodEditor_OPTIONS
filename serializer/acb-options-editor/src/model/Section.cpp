#include "Section.h"
#include "Section1.h"
#include "Section2.h"
#include "Section3.h"
#include "Section4.h"
#include "UnknownSection.h"
#include "core/LZSS.h"
#include "core/BinaryReader.h"

namespace acb {

Section::Section()
    : m_rootHash(0)
    , m_rootProperty(nullptr)
    , m_valid(false)
    , m_dirty(false)
{
}

Section::~Section()
{
    delete m_rootProperty;
}

void Section::setRootProperty(Property* prop)
{
    delete m_rootProperty;
    m_rootProperty = prop;
}

bool Section::decompress()
{
    if (m_rawCompressed.isEmpty()) {
        return false;
    }

    m_rawDecompressed = LZSS::decompress(m_rawCompressed);

    // Extract root hash (first 4 bytes after any prefix)
    if (m_rawDecompressed.size() >= 4) {
        BinaryReader reader(m_rawDecompressed);
        m_rootHash = reader.readU32();
    }

    return !m_rawDecompressed.isEmpty();
}

bool Section::compress()
{
    if (m_rawDecompressed.isEmpty()) {
        return false;
    }

    m_rawCompressed = LZSS::compress(m_rawDecompressed);
    return !m_rawCompressed.isEmpty();
}

Section* Section::createFromHash(uint32_t rootHash)
{
    switch (rootHash) {
        case SectionHash::SaveGame:
            return new Section1();
        case SectionHash::PlayerOptionsSaveData:
            return new Section2();
        case SectionHash::AssassinSingleProfileData:
            return new Section3();
        case SectionHash::AssassinMultiProfileData:
            return new Section4();
        default:
            return new UnknownSection();
    }
}

} // namespace acb
