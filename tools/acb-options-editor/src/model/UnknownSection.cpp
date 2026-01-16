#include "UnknownSection.h"

namespace acb {

UnknownSection::UnknownSection()
{
}

UnknownSection::~UnknownSection()
{
}

bool UnknownSection::parse()
{
    // For unknown sections, just keep the raw decompressed data
    // The UI will display it as a hex blob
    m_valid = !m_rawDecompressed.isEmpty();
    return m_valid;
}

QByteArray UnknownSection::serialize() const
{
    // Return the raw decompressed data unchanged
    return m_rawDecompressed;
}

QString UnknownSection::sectionName() const
{
    return QString("Unknown (0x%1)").arg(m_rootHash, 8, 16, QChar('0')).toUpper();
}

} // namespace acb
