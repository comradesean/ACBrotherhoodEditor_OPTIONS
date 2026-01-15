#pragma once

#include "Section.h"
#include <QVector>
#include <QVariant>

namespace acb {

class BinaryReader;
class BinaryWriter;

// Section 2: PlayerOptionsSaveData (root hash 0x11FACE11)
// Contains graphics, audio, control bindings
// Uses hierarchical ObjectStructure with PropertyIteratorCore records
class Section2 : public Section {
public:
    Section2();
    ~Section2() override;

    bool parse() override;
    QByteArray serialize() const override;

    QString sectionName() const override { return "PlayerOptionsSaveData"; }
    int sectionNumber() const override { return 2; }

    // Type codes from FUN_01b0c2e0 (TypeDispatcher)
    static constexpr uint8_t TypeBoolean = 0x00;
    static constexpr uint8_t TypeByte = 0x03;
    static constexpr uint8_t TypeFloat = 0x06;
    static constexpr uint8_t TypeComplex = 0x07;
    static constexpr uint8_t TypeFloatAlt = 0x0A;
    static constexpr uint8_t TypeNumeric = 0x11;
    static constexpr uint8_t TypeClassId = 0x12;
    static constexpr uint8_t TypeContainer = 0x13;
    static constexpr uint8_t TypeEnumSmall = 0x15;
    static constexpr uint8_t TypeNestedObject = 0x16;
    static constexpr uint8_t TypeVector = 0x17;
    static constexpr uint8_t TypeArrayAlt = 0x18;
    static constexpr uint8_t TypeEnumVariant = 0x19;
    static constexpr uint8_t TypeArray = 0x1D;
    static constexpr uint8_t TypeClassIdAlt = 0x1E;

private:
    // ObjectInfo header structure
    struct ObjectInfo {
        uint8_t nbClassVersions;  // Count byte - entries are skipped, always write 0
        QString objectName;
        uint32_t objectId;
        uint8_t instancingMode;
        uint32_t fatherId; // Only if instancingMode == 1
    };

    // Property record structure
    struct S2Property {
        uint32_t propertyId;
        uint32_t classId;
        uint32_t typeId;
        uint8_t packedInfo;
        QVariant value;
        QVector<S2Property> childProperties;  // For containers/nested objects
        QVector<S2Property> childDynProps;    // Dynamic properties for nested objects
        ObjectInfo nestedInfo;                // ObjectInfo for nested objects (preserved for round-trip)
        bool hasNestedInfo = false;           // True if nestedInfo is valid
    };

    // Object structure (recursive)
    struct ObjectStructure {
        ObjectInfo info;
        uint32_t tHash;
        QVector<S2Property> properties;
        QVector<S2Property> dynProps;
    };

    // Parsing helpers
    ObjectInfo parseObjectInfo(BinaryReader& reader);
    ObjectStructure parseObjectStructure(BinaryReader& reader);
    QVector<S2Property> parsePropertyRecords(BinaryReader& reader, int endOffset);
    S2Property parsePropertyRecord(BinaryReader& reader);
    QVariant parseArrayValue(BinaryReader& reader, int valueSize, uint32_t typeId);
    QVariant parseVectorValue(BinaryReader& reader, int valueSize, uint32_t typeId);
    QVariant parseSimpleValue(BinaryReader& reader, uint8_t typeCode, int valueSize);

    // Serialization helpers
    void serializeObjectInfo(BinaryWriter& writer, const ObjectInfo& info) const;
    void serializeObjectStructure(BinaryWriter& writer, const ObjectStructure& obj) const;
    void serializePropertyRecord(BinaryWriter& writer, const S2Property& prop) const;
    void serializeArrayValue(BinaryWriter& writer, const QVariant& value, uint32_t typeId) const;
    void serializeVectorValue(BinaryWriter& writer, const QVariant& value, uint32_t typeId) const;
    void serializeSimpleValue(BinaryWriter& writer, const QVariant& value, uint8_t typeCode) const;

    // Element size helpers
    static int elementSizeForType(uint8_t typeCode);
    static bool isFloatType(uint8_t typeCode);

    // Build UI tree from parsed data
    void buildPropertyTree();
    Property* buildPropertyFromS2(const S2Property& s2prop);
    void buildChildrenFromObject(Property* parent, const ObjectStructure& obj);

    ObjectStructure m_rootObject;
};

} // namespace acb
