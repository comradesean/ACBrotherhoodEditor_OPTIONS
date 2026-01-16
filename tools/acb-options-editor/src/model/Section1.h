#pragma once

#include "Section.h"
#include <QVector>

namespace acb {

// Section 1: SaveGame (root hash 0xBDBE3B52)
// Contains system/profile metadata
// Uses universal ObjectInfo header like other sections.
// Root property has block size but no type prefix,
// child properties have type prefix but no block size.
class Section1 : public Section {
public:
    Section1();
    ~Section1() override;

    bool parse() override;
    QByteArray serialize() const override;

    QString sectionName() const override { return "SaveGame"; }
    int sectionNumber() const override { return 1; }

    // Property flags byte
    static constexpr uint8_t PackedInfo = 0x0B;

    // Descriptor type codes (extracted from type_id)
    static constexpr uint32_t DescriptorBool = 0x00;
    static constexpr uint32_t DescriptorComplex = 0x07;
    static constexpr uint32_t DescriptorPointer = 0x12;
    static constexpr uint32_t DescriptorArray = 0x17;
    static constexpr uint32_t DescriptorString = 0x1A;
    static constexpr uint32_t DescriptorPointerAlt = 0x1E;

    // Binary type prefix codes (written for child properties)
    static constexpr uint32_t TypePrefixBool = 0x0E;
    static constexpr uint32_t TypePrefixNumeric = 0x11;
    static constexpr uint32_t TypePrefixString = 0x19;

private:
    // ObjectInfo header (universal structure across all sections)
    struct ObjectInfo {
        uint8_t nbClassVersions;
        uint32_t objectNameLength;
        uint32_t objectId;
        uint8_t instancingMode;
    };

    // Internal property structure for Section 1
    struct S1Property {
        uint32_t hash;
        uint32_t classId;
        uint32_t typeId;
        uint8_t packedInfo;
        QVariant value;       // bool, int, or QString
    };

    // Parse helpers
    static uint32_t extractDescriptorType(uint32_t typeId);
    static QString valueFormat(uint32_t descriptorType);
    static uint32_t computeTypePrefix(uint32_t descriptorType);

    // Parse/serialize value based on format
    QVariant parseValue(BinaryReader& reader, const QString& format);
    int valueSize(const QVariant& value, const QString& format) const;
    void serializeValue(BinaryWriter& writer, const QVariant& value, const QString& format) const;

    // Build property tree from parsed data
    void buildPropertyTree();

    ObjectInfo m_objectInfo;
    S1Property m_rootProp;
    QVector<S1Property> m_childProps;
    QVector<S1Property> m_dynProps;  // Dynamic properties (if size > 0)
};

} // namespace acb
