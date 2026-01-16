#pragma once

#include "Section.h"
#include <QVector>
#include <QVariant>

namespace acb {

class BinaryReader;
class BinaryWriter;

// Section 3: AssassinSingleProfileData (root hash 0xC9876D66)
// Contains save game state, player progress
// Uses LIFO section nesting with backpatching, base class property has no size field
class Section3 : public Section {
public:
    Section3();
    ~Section3() override;

    bool parse() override;
    QByteArray serialize() const override;

    QString sectionName() const override { return "AssassinSingleProfileData"; }
    int sectionNumber() const override { return 3; }

    // Type codes (from FUN_01b0c2e0 dispatcher)
    static constexpr uint8_t TypeBool = 0x00;
    static constexpr uint8_t TypeInt8 = 0x01;
    static constexpr uint8_t TypeUInt8 = 0x02;
    static constexpr uint8_t TypeInt16 = 0x03;
    static constexpr uint8_t TypeUInt16 = 0x04;
    static constexpr uint8_t TypeInt32 = 0x05;
    static constexpr uint8_t TypeUInt32 = 0x07;
    static constexpr uint8_t TypeInt64 = 0x08;
    static constexpr uint8_t TypeUInt64 = 0x09;
    static constexpr uint8_t TypeFloat32 = 0x0A;
    static constexpr uint8_t TypeFloat64 = 0x0B;
    static constexpr uint8_t TypeVec2 = 0x0C;
    static constexpr uint8_t TypeVec3 = 0x0D;
    static constexpr uint8_t TypeVec4 = 0x0E;
    static constexpr uint8_t TypeQuat = 0x0F;
    static constexpr uint8_t TypeMat3x3 = 0x10;
    static constexpr uint8_t TypeMat4x4 = 0x11;

    static constexpr uint8_t PropertyFlagsByte = 0x0B;

private:
    // Header info from ObjectInfo
    struct Header {
        uint8_t nbClassVersionsInfo;
        uint32_t objectNameLength;
        uint32_t objectId;
        uint8_t instancingMode;
        uint32_t typeHash;
    };

    // Base class field (no size field in binary)
    struct BaseClass {
        uint32_t hash;
        QByteArray typeInfo; // 8 bytes
        uint8_t flags;
        uint32_t value;
    };

    // Regular property (with size field)
    struct S3Property {
        uint32_t hash;
        QByteArray typeInfo; // 8 bytes
        uint8_t flags;
        QVariant value;
    };

    // Parse helpers
    static int typeSizeBytes(uint8_t typeCode);
    QVariant parseValue(BinaryReader& reader, uint8_t typeCode);
    void serializeValue(BinaryWriter& writer, uint8_t typeCode, const QVariant& value) const;

    // Build UI tree
    void buildPropertyTree();
    Property* buildPropertyFromS3(const S3Property& prop, const QString& name);

    // Parse property record (reusable for dynprops)
    S3Property parsePropertyRecord(BinaryReader& reader);

    Header m_header;
    BaseClass m_baseClass;
    QVector<S3Property> m_properties;
    QVector<S3Property> m_dynProps;  // Dynamic properties (if size > 0)
};

} // namespace acb
