#pragma once

#include "Section.h"
#include <QVector>
#include <QVariant>
#include <QVariantMap>
#include <QVariantList>

namespace acb {

class BinaryReader;
class BinaryWriter;

// Section 4: AssassinMultiProfileData (root hash 0xB4B55039)
// Contains multiplayer profile data (optional section)
// Uses Mode 3 binary serialization (no flags byte in property header)
// The 0x0B marker appears before the VALUE, not in header
class Section4 : public Section {
public:
    Section4();
    ~Section4() override;

    bool parse() override;
    QByteArray serialize() const override;

    QString sectionName() const override { return "AssassinMultiProfileData"; }
    int sectionNumber() const override { return 4; }

    // Type codes (same as other sections)
    static constexpr uint8_t TypeBool = 0x00;
    static constexpr uint8_t TypeBoolAlt = 0x01;
    static constexpr uint8_t TypeUInt8 = 0x02;
    static constexpr uint8_t TypeInt8 = 0x03;
    static constexpr uint8_t TypeUInt16 = 0x04;
    static constexpr uint8_t TypeInt16 = 0x05;
    static constexpr uint8_t TypeInt32v2 = 0x06;
    static constexpr uint8_t TypeUInt32 = 0x07;
    static constexpr uint8_t TypeInt32 = 0x08;
    static constexpr uint8_t TypeUInt64 = 0x09;
    static constexpr uint8_t TypeFloatAlt = 0x0A;
    static constexpr uint8_t TypeFloat64 = 0x0B;
    static constexpr uint8_t TypeVec2 = 0x0C;
    static constexpr uint8_t TypeVec3 = 0x0D;
    static constexpr uint8_t TypeVec4 = 0x0E;
    static constexpr uint8_t TypeMat3x3 = 0x0F;
    static constexpr uint8_t TypeMat4x4 = 0x10;
    static constexpr uint8_t TypeString = 0x11;
    static constexpr uint8_t TypeClass = 0x16;
    static constexpr uint8_t TypeArray = 0x17;
    static constexpr uint8_t TypeMap = 0x18;
    static constexpr uint8_t TypeEnumAlt = 0x19;
    static constexpr uint8_t TypeVarString = 0x1B;
    static constexpr uint8_t TypeMapAlt = 0x1D;

private:
    // ObjectInfo header (10 bytes)
    struct ObjectInfo {
        uint8_t nbClassVersions;
        uint32_t objectName;  // Hash, usually 0
        uint32_t objectId;
        uint8_t instancingMode;
    };

    // Property in Mode 3 format (12-byte header, no flags)
    struct S4Property {
        uint32_t propertyId;
        QByteArray typeDescriptor; // 8 bytes
        uint8_t typeCode;
        uint8_t elementType;
        QVariant value;
    };

    // CLASS entry within a MAP
    struct ClassEntry {
        ObjectInfo info;
        uint32_t typeHash;
        QVector<S4Property> properties;
        uint32_t dynamicPropertiesSize;
    };

    // Parse helpers
    ObjectInfo parseObjectInfo(BinaryReader& reader);
    S4Property parseProperty(BinaryReader& reader);
    QVariant parseValue(BinaryReader& reader, uint8_t typeCode, int bytesRemaining, uint8_t elementType, uint32_t typeHash);
    QVariant parseVarString(BinaryReader& reader);
    QVariant parseMap(BinaryReader& reader, int bytesRemaining, uint8_t elementType);
    QVector<ClassEntry> parseClassEntries(BinaryReader& reader, int count);
    S4Property parseNestedProperty(BinaryReader& reader, int propEnd);

    // Serialize helpers
    void serializeObjectInfo(BinaryWriter& writer, const ObjectInfo& info) const;
    void serializeProperty(BinaryWriter& writer, const S4Property& prop) const;
    void serializeValue(BinaryWriter& writer, uint8_t typeCode, const QVariant& value, uint8_t elementType, uint32_t typeHash) const;
    void serializeVarString(BinaryWriter& writer, const QString& value) const;
    void serializeMap(BinaryWriter& writer, const QVariant& value, uint8_t elementType) const;
    void serializeClassEntry(BinaryWriter& writer, const ClassEntry& entry) const;
    void serializeNestedProperty(BinaryWriter& writer, const S4Property& prop) const;

    // Type size helpers
    static int typeSizeBytes(uint8_t typeCode);
    static bool isFixedSizeType(uint8_t typeCode);

    // Build UI tree
    void buildPropertyTree();
    Property* buildPropertyFromS4(const S4Property& prop);

    ObjectInfo m_rootInfo;
    uint32_t m_rootTypeHash;
    QVector<S4Property> m_properties;
    QVector<S4Property> m_dynProps;  // Dynamic properties (if size > 0)
};

} // namespace acb
