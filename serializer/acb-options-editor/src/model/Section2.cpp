#include "Section2.h"
#include "core/BinaryReader.h"
#include "core/BinaryWriter.h"
#include <QVariantList>
#include <QVariantMap>

namespace acb {

Section2::Section2()
{
}

Section2::~Section2()
{
}

int Section2::elementSizeForType(uint8_t typeCode)
{
    switch (typeCode) {
        case TypeBoolean: return 1;
        case TypeByte: return 1;
        case TypeFloat: return 4;
        case TypeComplex: return 4;
        case TypeFloatAlt: return 4;
        case TypeNumeric: return 4;
        case TypeClassId: return 4;
        case TypeEnumSmall: return 4;
        case TypeEnumVariant: return 8; // value + class_id
        case TypeClassIdAlt: return 4;
        default: return 0; // Unknown/variable
    }
}

bool Section2::isFloatType(uint8_t typeCode)
{
    return typeCode == TypeFloat || typeCode == TypeFloatAlt;
}

Section2::ObjectInfo Section2::parseObjectInfo(BinaryReader& reader)
{
    ObjectInfo info;

    // NbClassVersionsInfo: count of class version entries
    info.nbClassVersions = reader.readU8();

    // Skip class version entries (game ignores them, just uses count to skip bytes)
    // Each entry: ClassID (4 bytes) + Version (2 bytes) = 6 bytes
    for (int i = 0; i < info.nbClassVersions; ++i) {
        reader.readU32(); // ClassID hash
        reader.readU16(); // Version number
    }

    // ObjectName: length-prefixed string (no null terminator)
    uint32_t nameLen = reader.readU32();
    if (nameLen > 0) {
        QByteArray nameBytes = reader.readBytes(static_cast<int>(nameLen));
        info.objectName = QString::fromUtf8(nameBytes);
    }

    // ObjectID
    info.objectId = reader.readU32();

    // InstancingMode
    info.instancingMode = reader.readU8();

    // FatherID: only present if InstancingMode == 1
    if (info.instancingMode == 1) {
        info.fatherId = reader.readU32();
    } else {
        info.fatherId = 0;
    }

    return info;
}

Section2::ObjectStructure Section2::parseObjectStructure(BinaryReader& reader)
{
    ObjectStructure obj;

    // Parse ObjectInfo header
    obj.info = parseObjectInfo(reader);

    // T-hash: type identifier for this object
    obj.tHash = reader.readU32();

    // Object size (skip - not needed)
    reader.readU32();

    // Properties size: tells us where properties block ends
    uint32_t propertiesSize = reader.readU32();
    int propertiesEnd = reader.tell() + static_cast<int>(propertiesSize);

    // Parse property records
    obj.properties = parsePropertyRecords(reader, propertiesEnd);

    // DynProps block (usually empty)
    uint32_t dynPropsSize = reader.readU32();
    if (dynPropsSize > 0) {
        int dynPropsEnd = reader.tell() + static_cast<int>(dynPropsSize);
        obj.dynProps = parsePropertyRecords(reader, dynPropsEnd);
    }

    return obj;
}

QVector<Section2::S2Property> Section2::parsePropertyRecords(BinaryReader& reader, int endOffset)
{
    QVector<S2Property> records;

    while (reader.tell() < endOffset) {
        if (reader.remaining() < 17) { // Minimum: size(4) + header(13)
            break;
        }
        S2Property prop = parsePropertyRecord(reader);
        records.append(prop);
    }

    return records;
}

Section2::S2Property Section2::parsePropertyRecord(BinaryReader& reader)
{
    S2Property prop;

    // Block size (not including the size field itself)
    uint32_t blockSize = reader.readU32();

    // Validate
    if (blockSize == 0 || static_cast<int>(blockSize) > reader.remaining() + 4) {
        // Invalid, return empty
        return prop;
    }

    // Parse 13-byte header
    prop.propertyId = reader.readU32();
    prop.classId = reader.readU32();
    prop.typeId = reader.readU32();
    prop.packedInfo = reader.readU8();

    // Extract type code from bits 16-21
    uint8_t typeCode = (prop.typeId >> 16) & 0x3F;
    int valueSize = static_cast<int>(blockSize) - 13;

    // Parse value based on type code
    if (valueSize <= 0) {
        prop.value = QVariant();
    } else if (typeCode == TypeContainer || typeCode == TypeNestedObject) {
        // Nested object structure - recursively parse
        ObjectStructure nested = parseObjectStructure(reader);
        QVariantMap nestedMap;
        nestedMap["_type"] = "object";
        nestedMap["tHash"] = nested.tHash;
        // Store as a special nested variant
        // We'll handle this during tree building
        prop.value = QVariant::fromValue(nestedMap);
        // Preserve nested ObjectInfo for round-trip
        prop.nestedInfo = nested.info;
        prop.hasNestedInfo = true;
        // Parse children from nested object
        for (const auto& p : nested.properties) {
            prop.childProperties.append(p);
        }
        for (const auto& p : nested.dynProps) {
            prop.childDynProps.append(p);
        }
    } else if (typeCode == TypeArray || typeCode == TypeArrayAlt) {
        prop.value = parseArrayValue(reader, valueSize, prop.typeId);
    } else if (typeCode == TypeVector) {
        prop.value = parseVectorValue(reader, valueSize, prop.typeId);
    } else {
        prop.value = parseSimpleValue(reader, typeCode, valueSize);
    }

    return prop;
}

QVariant Section2::parseArrayValue(BinaryReader& reader, int valueSize, uint32_t typeId)
{
    // Array structure: ContentCode(1) + Count(4) + Elements
    uint8_t contentCode = reader.readU8();
    uint32_t count = reader.readU32();
    uint8_t elementType = (typeId >> 23) & 0x3F;

    QVariantMap arr;
    arr["contentCode"] = contentCode;
    arr["count"] = count;

    int elementsSize = valueSize - 5; // Subtract ContentCode(1) + Count(4)

    if (elementsSize > 0 && count > 0) {
        int elemSize = elementSizeForType(elementType);
        if (elemSize > 0) {
            QVariantList elements;
            for (uint32_t i = 0; i < count; ++i) {
                if (elemSize == 1) {
                    elements.append(reader.readU8());
                } else if (elemSize == 4) {
                    if (isFloatType(elementType)) {
                        elements.append(reader.readFloat32());
                    } else {
                        elements.append(reader.readU32());
                    }
                } else if (elemSize == 8) {
                    // EnumVariant: value + class_id
                    QVariantMap enumVal;
                    enumVal["value"] = reader.readU32();
                    enumVal["classId"] = reader.readU32();
                    elements.append(enumVal);
                }
            }
            arr["elements"] = elements;
        } else {
            // Unknown element type - store raw bytes
            QByteArray raw = reader.readBytes(elementsSize);
            arr["rawElements"] = raw;
            arr["unknownElementType"] = true;
        }
    } else {
        arr["elements"] = QVariantList();
    }

    return arr;
}

QVariant Section2::parseVectorValue(BinaryReader& reader, int valueSize, uint32_t typeId)
{
    // Vector structure: Count(4) + Elements (no ContentCode)
    uint32_t count = reader.readU32();
    uint8_t elementType = (typeId >> 23) & 0x3F;

    QVariantMap vec;
    vec["count"] = count;

    int elementsSize = valueSize - 4; // Subtract Count(4)

    if (elementsSize > 0 && count > 0) {
        int elemSize = elementSizeForType(elementType);
        if (elemSize > 0) {
            QVariantList elements;
            for (uint32_t i = 0; i < count; ++i) {
                if (elemSize == 1) {
                    elements.append(reader.readU8());
                } else if (elemSize == 4) {
                    if (isFloatType(elementType)) {
                        elements.append(reader.readFloat32());
                    } else {
                        elements.append(reader.readU32());
                    }
                } else if (elemSize == 8) {
                    QVariantMap enumVal;
                    enumVal["value"] = reader.readU32();
                    enumVal["classId"] = reader.readU32();
                    elements.append(enumVal);
                }
            }
            vec["elements"] = elements;
        } else {
            QByteArray raw = reader.readBytes(elementsSize);
            vec["rawElements"] = raw;
            vec["unknownElementType"] = true;
        }
    } else {
        vec["elements"] = QVariantList();
    }

    return vec;
}

QVariant Section2::parseSimpleValue(BinaryReader& reader, uint8_t typeCode, int valueSize)
{
    if (valueSize == 1) {
        uint8_t val = reader.readU8();
        if (typeCode == TypeBoolean) {
            return QVariant(val != 0);
        }
        return QVariant(val);
    } else if (valueSize == 4) {
        if (isFloatType(typeCode)) {
            return QVariant(reader.readFloat32());
        }
        return QVariant(reader.readU32());
    } else if (valueSize == 8) {
        // EnumVariant (0x19): EnumValue(4) + EnumName(4)
        QVariantMap enumVal;
        enumVal["value"] = reader.readU32();
        enumVal["classId"] = reader.readU32();
        return enumVal;
    } else {
        // Unknown size - preserve as raw bytes
        QByteArray raw = reader.readBytes(valueSize);
        QVariantMap result;
        result["rawBytes"] = raw;
        return result;
    }
}

bool Section2::parse()
{
    if (m_rawDecompressed.isEmpty()) {
        return false;
    }

    BinaryReader reader(m_rawDecompressed);

    // Parse the root object structure
    m_rootObject = parseObjectStructure(reader);

    // Build the property tree for UI display
    buildPropertyTree();

    m_valid = true;
    return true;
}

void Section2::buildPropertyTree()
{
    delete m_rootProperty;
    m_rootProperty = nullptr;

    // Create root property from root object
    m_rootProperty = new Property(m_rootObject.tHash);

    // Build children from root object's properties
    buildChildrenFromObject(m_rootProperty, m_rootObject);
}

void Section2::buildChildrenFromObject(Property* parent, const ObjectStructure& obj)
{
    for (const S2Property& s2prop : obj.properties) {
        Property* child = buildPropertyFromS2(s2prop);
        if (child) {
            parent->addChild(child);
        }
    }
}

Property* Section2::buildPropertyFromS2(const S2Property& s2prop)
{
    Property* prop = new Property(s2prop.propertyId);
    prop->setFlags(s2prop.packedInfo);

    // Build type info: classId (hash_id, 4 bytes) + typeId (type_id, 4 bytes)
    uint8_t typeCode = (s2prop.typeId >> 16) & 0x3F;
    QByteArray typeInfo(8, 0);
    // First 4 bytes: classId (hash_id)
    typeInfo[0] = (s2prop.classId >> 0) & 0xFF;
    typeInfo[1] = (s2prop.classId >> 8) & 0xFF;
    typeInfo[2] = (s2prop.classId >> 16) & 0xFF;
    typeInfo[3] = (s2prop.classId >> 24) & 0xFF;
    // Next 4 bytes: typeId (type_id)
    typeInfo[4] = (s2prop.typeId >> 0) & 0xFF;
    typeInfo[5] = (s2prop.typeId >> 8) & 0xFF;
    typeInfo[6] = (s2prop.typeId >> 16) & 0xFF;
    typeInfo[7] = (s2prop.typeId >> 24) & 0xFF;
    prop->setTypeInfo(typeInfo);

    // Set value based on type
    if (typeCode == TypeBoolean) {
        prop->value().setType(TypeCode::Bool);
        prop->value().setBool(s2prop.value.toBool());
    } else if (isFloatType(typeCode)) {
        prop->value().setType(TypeCode::Float32);
        prop->value().setFloat32(s2prop.value.toFloat());
    } else if (typeCode == TypeContainer || typeCode == TypeNestedObject) {
        prop->value().setType(TypeCode::Container);
        // Add child properties
        for (const S2Property& childProp : s2prop.childProperties) {
            Property* child = buildPropertyFromS2(childProp);
            if (child) {
                prop->addChild(child);
            }
        }
    } else if (typeCode == TypeArray || typeCode == TypeArrayAlt || typeCode == TypeVector) {
        prop->value().setType(TypeCode::Array);
        // Build child properties for array elements
        QVariantMap arrMap = s2prop.value.toMap();
        QVariantList elements = arrMap.value("elements").toList();
        uint8_t elementType = (s2prop.typeId >> 23) & 0x3F;

        for (int i = 0; i < elements.size(); ++i) {
            Property* elemProp = new Property(static_cast<uint32_t>(i));  // Use index as hash

            // Build type info for element
            QByteArray elemTypeInfo(8, 0);
            elemTypeInfo[6] = elementType & 0x3F;
            elemProp->setTypeInfo(elemTypeInfo);

            const QVariant& elem = elements[i];
            if (elem.typeId() == qMetaTypeId<QVariantMap>()) {
                QVariantMap elemMap = elem.toMap();
                if (elemMap.contains("value") && elemMap.contains("classId")) {
                    // EnumVariant
                    elemProp->value().setType(TypeCode::UInt32);
                    elemProp->value().setUInt32(elemMap["value"].toUInt());
                } else {
                    elemProp->value().setType(TypeCode::Unknown);
                }
            } else if (isFloatType(elementType)) {
                elemProp->value().setType(TypeCode::Float32);
                elemProp->value().setFloat32(elem.toFloat());
            } else if (elementType == TypeBoolean) {
                elemProp->value().setType(TypeCode::Bool);
                elemProp->value().setBool(elem.toBool());
            } else {
                elemProp->value().setType(TypeCode::UInt32);
                elemProp->value().setUInt32(elem.toUInt());
            }

            prop->addChild(elemProp);
        }
    } else if (s2prop.value.typeId() == qMetaTypeId<QVariantMap>()) {
        QVariantMap map = s2prop.value.toMap();
        if (map.contains("rawBytes")) {
            prop->value().setType(TypeCode::Unknown);
            prop->value().setRawBytes(map["rawBytes"].toByteArray());
        } else {
            prop->value().setType(TypeCode::UInt32);
            prop->value().setUInt32(0);
        }
    } else {
        prop->value().setType(TypeCode::UInt32);
        prop->value().setUInt32(s2prop.value.toUInt());
    }

    return prop;
}

// Serialization implementation

void Section2::serializeObjectInfo(BinaryWriter& writer, const ObjectInfo& info) const
{
    // NbClassVersionsInfo: always write 0
    // Game ignores class version entries, just uses count to skip bytes
    // Since we don't preserve entries, writing 0 keeps byte stream correct
    Q_UNUSED(info.nbClassVersions);
    writer.writeU8(0);

    // ObjectName: 4-byte length + UTF-8 string (no null terminator)
    QByteArray nameBytes = info.objectName.toUtf8();
    writer.writeU32(static_cast<uint32_t>(nameBytes.size()));
    if (!nameBytes.isEmpty()) {
        writer.writeBytes(nameBytes);
    }

    // ObjectID
    writer.writeU32(info.objectId);

    // InstancingMode
    writer.writeU8(info.instancingMode);

    // FatherID only if instancingMode == 1
    if (info.instancingMode == 1) {
        writer.writeU32(info.fatherId);
    }
}

void Section2::serializeObjectStructure(BinaryWriter& writer, const ObjectStructure& obj) const
{
    // ObjectInfo header
    serializeObjectInfo(writer, obj.info);

    // T-hash
    writer.writeU32(obj.tHash);

    // Begin Object block (size placeholder)
    int objectSectionPos = writer.openSection();

    // Begin Properties block (size placeholder)
    int propertiesSectionPos = writer.openSection();

    // Write properties
    for (const S2Property& prop : obj.properties) {
        serializePropertyRecord(writer, prop);
    }

    writer.closeSection(); // End Properties block

    // Begin DynProps block
    int dynPropsSectionPos = writer.openSection();

    // Write dynProps
    for (const S2Property& prop : obj.dynProps) {
        serializePropertyRecord(writer, prop);
    }

    writer.closeSection(); // End DynProps block

    writer.closeSection(); // End Object block
}

void Section2::serializePropertyRecord(BinaryWriter& writer, const S2Property& prop) const
{
    // Begin sized block for property
    int propSectionPos = writer.openSection();

    // Write 13-byte header
    writer.writeU32(prop.propertyId);
    writer.writeU32(prop.classId);
    writer.writeU32(prop.typeId);
    writer.writeU8(prop.packedInfo);

    // Write value based on type code
    uint8_t typeCode = (prop.typeId >> 16) & 0x3F;

    if (typeCode == TypeContainer || typeCode == TypeNestedObject) {
        // Nested object - use preserved ObjectInfo for round-trip
        ObjectStructure nested;
        if (prop.hasNestedInfo) {
            nested.info = prop.nestedInfo;
        } else {
            // Fallback to defaults if no preserved info
            nested.info.nbClassVersions = 0;
            nested.info.objectName = "";
            nested.info.objectId = 0;
            nested.info.instancingMode = 0;
            nested.info.fatherId = 0;
        }
        nested.tHash = prop.classId;

        for (const S2Property& child : prop.childProperties) {
            nested.properties.append(child);
        }
        for (const S2Property& dynProp : prop.childDynProps) {
            nested.dynProps.append(dynProp);
        }

        serializeObjectStructure(writer, nested);
    } else if (typeCode == TypeArray || typeCode == TypeArrayAlt) {
        serializeArrayValue(writer, prop.value, prop.typeId);
    } else if (typeCode == TypeVector) {
        serializeVectorValue(writer, prop.value, prop.typeId);
    } else {
        serializeSimpleValue(writer, prop.value, typeCode);
    }

    writer.closeSection();
}

void Section2::serializeArrayValue(BinaryWriter& writer, const QVariant& value, uint32_t typeId) const
{
    QVariantMap arr = value.toMap();

    uint8_t contentCode = static_cast<uint8_t>(arr.value("contentCode", 0).toUInt());
    uint32_t count = arr.value("count", 0).toUInt();
    uint8_t elementType = (typeId >> 23) & 0x3F;

    writer.writeU8(contentCode);
    writer.writeU32(count);

    if (arr.contains("rawElements")) {
        writer.writeBytes(arr["rawElements"].toByteArray());
    } else {
        QVariantList elements = arr.value("elements").toList();
        int elemSize = elementSizeForType(elementType);

        for (const QVariant& elem : elements) {
            if (elemSize == 1) {
                writer.writeU8(static_cast<uint8_t>(elem.toUInt()));
            } else if (elemSize == 4) {
                if (isFloatType(elementType)) {
                    writer.writeFloat32(elem.toFloat());
                } else {
                    writer.writeU32(elem.toUInt());
                }
            } else if (elemSize == 8) {
                QVariantMap enumVal = elem.toMap();
                writer.writeU32(enumVal["value"].toUInt());
                writer.writeU32(enumVal["classId"].toUInt());
            }
        }
    }
}

void Section2::serializeVectorValue(BinaryWriter& writer, const QVariant& value, uint32_t typeId) const
{
    QVariantMap vec = value.toMap();

    uint32_t count = vec.value("count", 0).toUInt();
    uint8_t elementType = (typeId >> 23) & 0x3F;

    writer.writeU32(count);

    if (vec.contains("rawElements")) {
        writer.writeBytes(vec["rawElements"].toByteArray());
    } else {
        QVariantList elements = vec.value("elements").toList();
        int elemSize = elementSizeForType(elementType);

        for (const QVariant& elem : elements) {
            if (elemSize == 1) {
                writer.writeU8(static_cast<uint8_t>(elem.toUInt()));
            } else if (elemSize == 4) {
                if (isFloatType(elementType)) {
                    writer.writeFloat32(elem.toFloat());
                } else {
                    writer.writeU32(elem.toUInt());
                }
            } else if (elemSize == 8) {
                QVariantMap enumVal = elem.toMap();
                writer.writeU32(enumVal["value"].toUInt());
                writer.writeU32(enumVal["classId"].toUInt());
            }
        }
    }
}

void Section2::serializeSimpleValue(BinaryWriter& writer, const QVariant& value, uint8_t typeCode) const
{
    if (value.isNull()) {
        return;
    }

    if (value.typeId() == qMetaTypeId<bool>() || typeCode == TypeBoolean) {
        writer.writeU8(value.toBool() ? 1 : 0);
    } else if (value.typeId() == qMetaTypeId<QVariantMap>()) {
        QVariantMap map = value.toMap();
        if (map.contains("rawBytes")) {
            writer.writeBytes(map["rawBytes"].toByteArray());
        } else if (map.contains("value") && map.contains("classId")) {
            // EnumVariant
            writer.writeU32(map["value"].toUInt());
            writer.writeU32(map["classId"].toUInt());
        }
    } else if (isFloatType(typeCode)) {
        writer.writeFloat32(value.toFloat());
    } else {
        // Integer type - determine size from type code
        int elemSize = elementSizeForType(typeCode);
        if (elemSize == 1) {
            writer.writeU8(static_cast<uint8_t>(value.toUInt()));
        } else {
            writer.writeU32(value.toUInt());
        }
    }
}

QByteArray Section2::serialize() const
{
    BinaryWriter writer;
    serializeObjectStructure(writer, m_rootObject);
    return writer.data();
}

} // namespace acb
