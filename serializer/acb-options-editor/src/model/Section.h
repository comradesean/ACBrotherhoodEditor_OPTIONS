#pragma once

#include <QByteArray>
#include <QString>
#include <QList>
#include <cstdint>
#include "SectionHeader.h"
#include "Property.h"
#include "core/TypeCodes.h"

namespace acb {

class Section {
public:
    Section();
    virtual ~Section();

    // Header information
    const SectionHeader& header() const { return m_header; }
    SectionHeader& header() { return m_header; }

    // Raw data
    QByteArray rawCompressed() const { return m_rawCompressed; }
    QByteArray rawDecompressed() const { return m_rawDecompressed; }
    void setRawCompressed(const QByteArray& data) { m_rawCompressed = data; }
    void setRawDecompressed(const QByteArray& data) { m_rawDecompressed = data; }

    // Root hash (first 4 bytes of decompressed data, identifies section type)
    uint32_t rootHash() const { return m_rootHash; }
    void setRootHash(uint32_t hash) { m_rootHash = hash; }

    // Parsing and serialization (pure virtual - implemented by subclasses)
    virtual bool parse() = 0;
    virtual QByteArray serialize() const = 0;

    // Compress/decompress
    bool decompress();
    bool compress();

    // Section identification
    virtual QString sectionName() const = 0;
    virtual int sectionNumber() const = 0;
    virtual bool isKnown() const { return true; }

    // Properties tree
    Property* rootProperty() const { return m_rootProperty; }
    void setRootProperty(Property* prop);

    // State
    bool isValid() const { return m_valid; }
    bool isDirty() const { return m_dirty; }
    void setDirty(bool dirty) { m_dirty = dirty; }

    // Factory method to create appropriate section type from root hash
    static Section* createFromHash(uint32_t rootHash);

protected:
    SectionHeader m_header;
    QByteArray m_rawCompressed;
    QByteArray m_rawDecompressed;
    uint32_t m_rootHash;
    Property* m_rootProperty;
    bool m_valid;
    bool m_dirty;
};

} // namespace acb
