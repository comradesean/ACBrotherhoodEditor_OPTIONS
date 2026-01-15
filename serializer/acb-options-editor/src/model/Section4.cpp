#include "Section4.h"
#include "core/BinaryReader.h"
#include "core/BinaryWriter.h"

namespace acb {

Section4::Section4()
    : m_rootTypeHash(0)
{
    m_rootInfo.nbClassVersions = 0;
    m_rootInfo.objectName = 0;
    m_rootInfo.objectId = 0;
    m_rootInfo.instancingMode = 0;
}

Section4::~Section4()
{
}

int Section4::typeSizeBytes(uint8_t typeCode)
{
    switch (typeCode) {
        case TypeBool:
        case TypeBoolAlt:
        case TypeUInt8:
        case TypeInt8:
            return 1;
        case TypeUInt16:
        case TypeInt16:
            return 2;
        case TypeInt32:
        case TypeInt32v2:
        case TypeUInt32:
        case TypeFloatAlt:
            return 4;
        case TypeUInt64:
        case TypeFloat64:
        case TypeVec2:
        case TypeEnumAlt:
            return 8;
        case TypeVec3:
            return 12;
        case TypeVec4:
            return 16;
        case TypeMat3x3:
            return 36;
        case TypeMat4x4:
            return 64;
        default:
            return -1;
    }
}

bool Section4::isFixedSizeType(uint8_t typeCode)
{
    int size = typeSizeBytes(typeCode);
    return size > 0;
}

Section4::ObjectInfo Section4::parseObjectInfo(BinaryReader& reader)
{
    ObjectInfo info;
    info.nbClassVersions = reader.readU8();
    info.objectName = reader.readU32();
    info.objectId = reader.readU32();
    info.instancingMode = reader.readU8();
    return info;
}

QVariant Section4::parseVarString(BinaryReader& reader)
{
    // VarString format: MarkerByte(1) + Length(4) + Chars + NullTerminator(1)
    uint8_t marker = reader.readU8();
    if (marker != 0x0B) {
        qWarning() << "Section4: Expected 0x0B marker, got" << Qt::hex << marker;
    }

    uint32_t length = reader.readU32();
    QByteArray strData;
    if (length > 0) {
        strData = reader.readBytes(static_cast<int>(length));
    }
    reader.readU8(); // null terminator

    return QString::fromUtf8(strData);
}

QVector<Section4::ClassEntry> Section4::parseClassEntries(BinaryReader& reader, int count)
{
    QVector<ClassEntry> entries;

    for (int i = 0; i < count; ++i) {
        ClassEntry entry;

        // ObjectInfo header (10 bytes)
        entry.info = parseObjectInfo(reader);

        // TypeHash
        entry.typeHash = reader.readU32();

        // Object size
        uint32_t objectSize = reader.readU32();
        int objectEnd = reader.tell() + static_cast<int>(objectSize);

        // Properties size
        uint32_t propertiesSize = reader.readU32();
        int propertiesEnd = reader.tell() + static_cast<int>(propertiesSize);

        // Parse properties within this CLASS entry
        while (reader.tell() < propertiesEnd && reader.remaining() >= 12) {
            uint32_t propSize = reader.readU32();
            if (propSize == 0) break;

            int propEnd = reader.tell() + static_cast<int>(propSize);

            S4Property prop = parseNestedProperty(reader, propEnd);
            entry.properties.append(prop);

            reader.seek(propEnd);
        }

        // Read dynamic properties size
        entry.dynamicPropertiesSize = reader.readU32();

        // Ensure we're at the correct position
        reader.seek(objectEnd);

        entries.append(entry);
    }

    return entries;
}

Section4::S4Property Section4::parseNestedProperty(BinaryReader& reader, int propEnd)
{
    S4Property prop;

    // Property ID (4 bytes)
    prop.propertyId = reader.readU32();

    // Type Descriptor (8 bytes)
    prop.typeDescriptor = reader.readBytes(8);

    // Extract type code and element type
    prop.typeCode = static_cast<uint8_t>(prop.typeDescriptor[6]) & 0x3F;
    prop.elementType = ((static_cast<uint8_t>(prop.typeDescriptor[6]) >> 6) |
                        ((static_cast<uint8_t>(prop.typeDescriptor[7]) & 0x0F) << 2)) & 0x3F;

    int bytesRemaining = propEnd - reader.tell();

    // Parse value based on type code
    uint32_t typeHash = 0; // For CLASS entries
    if (prop.typeDescriptor.size() >= 4) {
        typeHash = static_cast<uint32_t>(static_cast<uint8_t>(prop.typeDescriptor[0])) |
                   (static_cast<uint32_t>(static_cast<uint8_t>(prop.typeDescriptor[1])) << 8) |
                   (static_cast<uint32_t>(static_cast<uint8_t>(prop.typeDescriptor[2])) << 16) |
                   (static_cast<uint32_t>(static_cast<uint8_t>(prop.typeDescriptor[3])) << 24);
    }

    prop.value = parseValue(reader, prop.typeCode, bytesRemaining, prop.elementType, typeHash);

    return prop;
}

Section4::S4Property Section4::parseProperty(BinaryReader& reader)
{
    S4Property prop;

    // Block size (4 bytes)
    uint32_t blockSize = reader.readU32();
    int propEnd = reader.tell() + static_cast<int>(blockSize);

    // Property ID (4 bytes)
    prop.propertyId = reader.readU32();

    // Type Descriptor (8 bytes)
    prop.typeDescriptor = reader.readBytes(8);

    // Extract type code and element type
    prop.typeCode = static_cast<uint8_t>(prop.typeDescriptor[6]) & 0x3F;
    prop.elementType = ((static_cast<uint8_t>(prop.typeDescriptor[6]) >> 6) |
                        ((static_cast<uint8_t>(prop.typeDescriptor[7]) & 0x0F) << 2)) & 0x3F;

    int bytesRemaining = propEnd - reader.tell();

    // Get type hash from descriptor (for CLASS entries)
    uint32_t typeHash = 0;
    if (prop.typeDescriptor.size() >= 4) {
        typeHash = static_cast<uint32_t>(static_cast<uint8_t>(prop.typeDescriptor[0])) |
                   (static_cast<uint32_t>(static_cast<uint8_t>(prop.typeDescriptor[1])) << 8) |
                   (static_cast<uint32_t>(static_cast<uint8_t>(prop.typeDescriptor[2])) << 16) |
                   (static_cast<uint32_t>(static_cast<uint8_t>(prop.typeDescriptor[3])) << 24);
    }

    prop.value = parseValue(reader, prop.typeCode, bytesRemaining, prop.elementType, typeHash);

    reader.seek(propEnd);
    return prop;
}

QVariant Section4::parseValue(BinaryReader& reader, uint8_t typeCode, int bytesRemaining, uint8_t elementType, uint32_t typeHash)
{
    // Mode 3: 0x0B marker precedes the value for primitives
    if (isFixedSizeType(typeCode) && bytesRemaining > 0) {
        uint8_t marker = reader.readU8();
        if (marker != 0x0B) {
            qWarning() << "Section4: Expected 0x0B marker, got" << Qt::hex << marker;
            reader.seek(reader.tell() - 1);
        }
    }

    switch (typeCode) {
        case TypeBool:
        case TypeBoolAlt:
            return QVariant(reader.readU8() != 0);
        case TypeUInt8:
            return QVariant(reader.readU8());
        case TypeInt8:
            return QVariant(reader.readS8());
        case TypeUInt16:
            return QVariant(reader.readU16());
        case TypeInt16:
            return QVariant(reader.readS16());
        case TypeInt32:
        case TypeInt32v2:
            return QVariant(reader.readS32());
        case TypeUInt32:
            return QVariant(reader.readU32());
        case TypeUInt64:
            return QVariant(static_cast<quint64>(reader.readU64()));
        case TypeFloatAlt:
            return QVariant(reader.readFloat32());
        case TypeFloat64:
            return QVariant(reader.readFloat64());
        case TypeVec2: {
            QVariantList vec;
            vec << reader.readFloat32() << reader.readFloat32();
            return vec;
        }
        case TypeVec3: {
            QVariantList vec;
            vec << reader.readFloat32() << reader.readFloat32() << reader.readFloat32();
            return vec;
        }
        case TypeVec4: {
            QVariantList vec;
            vec << reader.readFloat32() << reader.readFloat32()
                << reader.readFloat32() << reader.readFloat32();
            return vec;
        }
        case TypeMat3x3: {
            QVariantList mat;
            for (int i = 0; i < 9; ++i) mat << reader.readFloat32();
            return mat;
        }
        case TypeMat4x4: {
            QVariantList mat;
            for (int i = 0; i < 16; ++i) mat << reader.readFloat32();
            return mat;
        }
        case TypeEnumAlt: {
            QVariantMap enumVal;
            enumVal["value"] = reader.readU32();
            enumVal["classId"] = reader.readU32();
            return enumVal;
        }
        case TypeString:
        case TypeVarString:
            // VarString has marker already read by parseVarString
            if (typeCode == TypeVarString) {
                // Marker byte already consumed for fixed types
                uint32_t length = reader.readU32();
                QByteArray strData;
                if (length > 0) {
                    strData = reader.readBytes(static_cast<int>(length));
                }
                reader.readU8(); // null terminator
                return QString::fromUtf8(strData);
            } else {
                uint8_t marker = reader.readU8();
                if (marker != 0x0B) {
                    reader.seek(reader.tell() - 1);
                }
                uint32_t length = reader.readU32();
                QByteArray strData;
                if (length > 0) {
                    strData = reader.readBytes(static_cast<int>(length));
                }
                reader.readU8(); // null terminator
                return QString::fromUtf8(strData);
            }
        case TypeMap:
        case TypeMapAlt:
            return parseMap(reader, bytesRemaining, elementType);
        case TypeArray: {
            // Array format: Marker(1) + Count(4) + Elements
            uint8_t marker = reader.readU8();
            if (marker != 0x0B) {
                reader.seek(reader.tell() - 1);
            }
            uint32_t count = reader.readU32();
            QVariantList elements;
            int elemSize = typeSizeBytes(elementType);
            for (uint32_t i = 0; i < count; ++i) {
                if (elemSize == 1) {
                    elements << reader.readU8();
                } else if (elemSize == 4) {
                    elements << reader.readU32();
                } else if (elemSize == 8) {
                    elements << static_cast<quint64>(reader.readU64());
                } else {
                    break;
                }
            }
            QVariantMap arr;
            arr["count"] = count;
            arr["elements"] = elements;
            return arr;
        }
        case TypeClass: {
            // CLASS: contains nested ObjectInfo + properties
            ObjectInfo classInfo = parseObjectInfo(reader);
            uint32_t classTypeHash = reader.readU32();

            uint32_t objectSize = reader.readU32();
            int objectEnd = reader.tell() + static_cast<int>(objectSize);

            uint32_t propertiesSize = reader.readU32();
            int propertiesEnd = reader.tell() + static_cast<int>(propertiesSize);

            QVariantList classProperties;
            while (reader.tell() < propertiesEnd && reader.remaining() >= 4) {
                uint32_t propSize = reader.readU32();
                if (propSize == 0) break;

                int propEnd = reader.tell() + static_cast<int>(propSize);
                S4Property prop = parseNestedProperty(reader, propEnd);

                QVariantMap propMap;
                propMap["propertyId"] = prop.propertyId;
                propMap["typeCode"] = prop.typeCode;
                propMap["value"] = prop.value;
                classProperties << propMap;

                reader.seek(propEnd);
            }

            uint32_t dynPropsSize = reader.readU32();

            reader.seek(objectEnd);

            QVariantMap classData;
            classData["typeHash"] = classTypeHash;
            classData["properties"] = classProperties;
            return classData;
        }
        default:
            // Unknown type - read remaining bytes as raw
            if (bytesRemaining > 0) {
                return QVariant(reader.readBytes(bytesRemaining));
            }
            return QVariant();
    }
}

QVariant Section4::parseMap(BinaryReader& reader, int bytesRemaining, uint8_t elementType)
{
    Q_UNUSED(bytesRemaining);

    // MAP format: Marker(1) + Count(4) + CLASS entries
    uint8_t marker = reader.readU8();
    if (marker != 0x0B) {
        reader.seek(reader.tell() - 1);
    }

    uint32_t count = reader.readU32();

    QVariantMap mapData;
    mapData["count"] = count;

    if (count > 0 && (elementType == TypeClass || elementType == 0x16)) {
        QVector<ClassEntry> entries = parseClassEntries(reader, static_cast<int>(count));
        QVariantList entriesList;
        for (const ClassEntry& entry : entries) {
            QVariantMap entryMap;
            entryMap["typeHash"] = entry.typeHash;
            QVariantList props;
            for (const S4Property& prop : entry.properties) {
                QVariantMap propMap;
                propMap["propertyId"] = prop.propertyId;
                propMap["typeCode"] = prop.typeCode;
                propMap["value"] = prop.value;
                props << propMap;
            }
            entryMap["properties"] = props;
            entriesList << entryMap;
        }
        mapData["entries"] = entriesList;
    } else {
        QVariantList entries;
        mapData["entries"] = entries;
    }

    return mapData;
}

bool Section4::parse()
{
    if (m_rawDecompressed.isEmpty()) {
        return false;
    }

    BinaryReader reader(m_rawDecompressed);

    // Parse root ObjectInfo header (10 bytes)
    m_rootInfo = parseObjectInfo(reader);

    // Root TypeHash
    m_rootTypeHash = reader.readU32();

    // Object size
    uint32_t objectSize = reader.readU32();
    int objectEnd = reader.tell() + static_cast<int>(objectSize);

    // Properties size
    uint32_t propertiesSize = reader.readU32();
    int propertiesEnd = reader.tell() + static_cast<int>(propertiesSize);

    // Parse properties
    m_properties.clear();
    m_dynProps.clear();

    while (reader.tell() < propertiesEnd && reader.remaining() >= 16) {
        S4Property prop = parseProperty(reader);
        if (prop.propertyId == 0 && prop.typeDescriptor.isEmpty()) {
            break;
        }
        m_properties.append(prop);
    }

    // Seek to properties end
    reader.seek(propertiesEnd);

    // Dynamic properties size
    uint32_t dynPropsSize = reader.readU32();

    // Parse dynamic properties if size > 0
    if (dynPropsSize > 0) {
        int dynPropsEnd = reader.tell() + static_cast<int>(dynPropsSize);
        while (reader.tell() < dynPropsEnd && reader.remaining() >= 16) {
            S4Property prop = parseProperty(reader);
            if (prop.propertyId == 0 && prop.typeDescriptor.isEmpty()) {
                break;
            }
            m_dynProps.append(prop);
        }
        reader.seek(dynPropsEnd);
    }

    buildPropertyTree();

    m_valid = true;
    return true;
}

void Section4::buildPropertyTree()
{
    delete m_rootProperty;
    m_rootProperty = nullptr;

    m_rootProperty = new Property(m_rootTypeHash);

    for (const S4Property& prop : m_properties) {
        Property* child = buildPropertyFromS4(prop);
        if (child) {
            m_rootProperty->addChild(child);
        }
    }
}

Property* Section4::buildPropertyFromS4(const S4Property& prop)
{
    Property* result = new Property(prop.propertyId);
    result->setTypeInfo(prop.typeDescriptor);

    switch (prop.typeCode) {
        case TypeBool:
        case TypeBoolAlt:
            result->value().setType(TypeCode::Bool);
            result->value().setBool(prop.value.toBool());
            break;
        case TypeUInt8:
            result->value().setType(TypeCode::UInt8);
            result->value().setUInt8(static_cast<uint8_t>(prop.value.toUInt()));
            break;
        case TypeInt8:
            result->value().setType(TypeCode::Int8);
            result->value().setInt8(static_cast<int8_t>(prop.value.toInt()));
            break;
        case TypeUInt16:
            result->value().setType(TypeCode::UInt16);
            result->value().setUInt16(static_cast<uint16_t>(prop.value.toUInt()));
            break;
        case TypeInt16:
            result->value().setType(TypeCode::Int16);
            result->value().setInt16(static_cast<int16_t>(prop.value.toInt()));
            break;
        case TypeInt32:
        case TypeInt32v2:
            result->value().setType(TypeCode::Int32);
            result->value().setInt32(prop.value.toInt());
            break;
        case TypeUInt32:
            result->value().setType(TypeCode::UInt32);
            result->value().setUInt32(prop.value.toUInt());
            break;
        case TypeUInt64:
            result->value().setType(TypeCode::UInt64);
            result->value().setUInt64(prop.value.toULongLong());
            break;
        case TypeFloatAlt:
            result->value().setType(TypeCode::Float32);
            result->value().setFloat32(prop.value.toFloat());
            break;
        case TypeFloat64:
            result->value().setType(TypeCode::Float64);
            result->value().setFloat64(prop.value.toDouble());
            break;
        case TypeString:
        case TypeVarString:
            result->value().setType(TypeCode::String);
            result->value().setString(prop.value.toString());
            break;
        case TypeMap:
        case TypeMapAlt: {
            result->value().setType(TypeCode::Container);
            // Build children from map entries
            QVariantMap mapData = prop.value.toMap();
            QVariantList entries = mapData["entries"].toList();
            for (int i = 0; i < entries.size(); ++i) {
                QVariantMap entry = entries[i].toMap();
                Property* entryProp = new Property(static_cast<uint32_t>(i));

                QByteArray entryTypeInfo(8, 0);
                entryTypeInfo[6] = TypeClass & 0x3F;
                entryProp->setTypeInfo(entryTypeInfo);
                entryProp->value().setType(TypeCode::Container);

                // Add properties of this entry as children
                QVariantList props = entry["properties"].toList();
                for (int j = 0; j < props.size(); ++j) {
                    QVariantMap propMap = props[j].toMap();
                    uint8_t propTypeCode = static_cast<uint8_t>(propMap["typeCode"].toUInt());
                    S4Property childS4;
                    childS4.propertyId = propMap["propertyId"].toUInt();
                    childS4.typeCode = propTypeCode;
                    childS4.value = propMap["value"];
                    childS4.typeDescriptor = QByteArray(8, 0);
                    childS4.typeDescriptor[6] = propTypeCode & 0x3F;

                    Property* childProp = buildPropertyFromS4(childS4);
                    if (childProp) {
                        entryProp->addChild(childProp);
                    }
                }

                result->addChild(entryProp);
            }
            break;
        }
        case TypeArray: {
            result->value().setType(TypeCode::Array);
            QVariantMap arrData = prop.value.toMap();

            // Check if array contains class elements (stored in "entries")
            if (prop.elementType == TypeClass || prop.elementType == 0x16) {
                QVariantList entries = arrData["entries"].toList();
                for (int i = 0; i < entries.size(); ++i) {
                    QVariantMap entry = entries[i].toMap();
                    Property* entryProp = new Property(static_cast<uint32_t>(i));

                    QByteArray entryTypeInfo(8, 0);
                    entryTypeInfo[6] = TypeClass & 0x3F;
                    entryProp->setTypeInfo(entryTypeInfo);
                    entryProp->value().setType(TypeCode::Container);

                    // Add properties of this entry as children
                    QVariantList props = entry["properties"].toList();
                    for (int j = 0; j < props.size(); ++j) {
                        QVariantMap propMap = props[j].toMap();
                        uint8_t propTypeCode = static_cast<uint8_t>(propMap["typeCode"].toUInt());
                        S4Property childS4;
                        childS4.propertyId = propMap["propertyId"].toUInt();
                        childS4.typeCode = propTypeCode;
                        childS4.value = propMap["value"];
                        childS4.typeDescriptor = QByteArray(8, 0);
                        childS4.typeDescriptor[6] = propTypeCode & 0x3F;

                        Property* childProp = buildPropertyFromS4(childS4);
                        if (childProp) {
                            entryProp->addChild(childProp);
                        }
                    }

                    result->addChild(entryProp);
                }
            } else {
                // Simple element types stored in "elements"
                QVariantList elements = arrData["elements"].toList();
                for (int i = 0; i < elements.size(); ++i) {
                    Property* elemProp = new Property(static_cast<uint32_t>(i));

                    QByteArray elemTypeInfo(8, 0);
                    elemTypeInfo[6] = prop.elementType & 0x3F;
                    elemProp->setTypeInfo(elemTypeInfo);

                    const QVariant& elem = elements[i];
                    int elemSize = typeSizeBytes(prop.elementType);
                    if (elemSize == 1) {
                        elemProp->value().setType(TypeCode::UInt8);
                        elemProp->value().setUInt8(static_cast<uint8_t>(elem.toUInt()));
                    } else if (elemSize == 4) {
                        elemProp->value().setType(TypeCode::UInt32);
                        elemProp->value().setUInt32(elem.toUInt());
                    } else if (elemSize == 8) {
                        elemProp->value().setType(TypeCode::UInt64);
                        elemProp->value().setUInt64(elem.toULongLong());
                    } else {
                        elemProp->value().setType(TypeCode::UInt32);
                        elemProp->value().setUInt32(elem.toUInt());
                    }

                    result->addChild(elemProp);
                }
            }
            break;
        }
        case TypeClass: {
            result->value().setType(TypeCode::Container);
            // Build children from class properties
            QVariantMap classData = prop.value.toMap();
            QVariantList props = classData["properties"].toList();
            for (int i = 0; i < props.size(); ++i) {
                QVariantMap propMap = props[i].toMap();
                uint8_t propTypeCode = static_cast<uint8_t>(propMap["typeCode"].toUInt());
                S4Property childS4;
                childS4.propertyId = propMap["propertyId"].toUInt();
                childS4.typeCode = propTypeCode;
                childS4.value = propMap["value"];
                childS4.typeDescriptor = QByteArray(8, 0);
                childS4.typeDescriptor[6] = propTypeCode & 0x3F;

                Property* childProp = buildPropertyFromS4(childS4);
                if (childProp) {
                    result->addChild(childProp);
                }
            }
            break;
        }
        default:
            if (prop.value.typeId() == QMetaType::QByteArray) {
                result->value().setType(TypeCode::Unknown);
                result->value().setRawBytes(prop.value.toByteArray());
            } else {
                result->value().setType(TypeCode::UInt32);
                result->value().setUInt32(prop.value.toUInt());
            }
            break;
    }

    return result;
}

// Serialization implementation

void Section4::serializeObjectInfo(BinaryWriter& writer, const ObjectInfo& info) const
{
    writer.writeU8(info.nbClassVersions);
    writer.writeU32(info.objectName);
    writer.writeU32(info.objectId);
    writer.writeU8(info.instancingMode);
}

void Section4::serializeVarString(BinaryWriter& writer, const QString& value) const
{
    QByteArray utf8 = value.toUtf8();
    writer.writeU8(0x0B);
    writer.writeU32(static_cast<uint32_t>(utf8.size()));
    if (!utf8.isEmpty()) {
        writer.writeBytes(utf8);
    }
    writer.writeU8(0);
}

void Section4::serializeValue(BinaryWriter& writer, uint8_t typeCode, const QVariant& value, uint8_t elementType, uint32_t typeHash) const
{
    Q_UNUSED(typeHash);

    // Mode 3: 0x0B marker precedes the value for primitives
    if (isFixedSizeType(typeCode)) {
        writer.writeU8(0x0B);
    }

    switch (typeCode) {
        case TypeBool:
        case TypeBoolAlt:
            writer.writeU8(value.toBool() ? 1 : 0);
            break;
        case TypeUInt8:
            writer.writeU8(static_cast<uint8_t>(value.toUInt()));
            break;
        case TypeInt8:
            writer.writeS8(static_cast<int8_t>(value.toInt()));
            break;
        case TypeUInt16:
            writer.writeU16(static_cast<uint16_t>(value.toUInt()));
            break;
        case TypeInt16:
            writer.writeS16(static_cast<int16_t>(value.toInt()));
            break;
        case TypeInt32:
        case TypeInt32v2:
            writer.writeS32(value.toInt());
            break;
        case TypeUInt32:
            writer.writeU32(value.toUInt());
            break;
        case TypeUInt64:
            writer.writeU64(value.toULongLong());
            break;
        case TypeFloatAlt:
            writer.writeFloat32(value.toFloat());
            break;
        case TypeFloat64:
            writer.writeFloat64(value.toDouble());
            break;
        case TypeVec2: {
            QVariantList vec = value.toList();
            writer.writeFloat32(vec.value(0).toFloat());
            writer.writeFloat32(vec.value(1).toFloat());
            break;
        }
        case TypeVec3: {
            QVariantList vec = value.toList();
            writer.writeFloat32(vec.value(0).toFloat());
            writer.writeFloat32(vec.value(1).toFloat());
            writer.writeFloat32(vec.value(2).toFloat());
            break;
        }
        case TypeVec4: {
            QVariantList vec = value.toList();
            writer.writeFloat32(vec.value(0).toFloat());
            writer.writeFloat32(vec.value(1).toFloat());
            writer.writeFloat32(vec.value(2).toFloat());
            writer.writeFloat32(vec.value(3).toFloat());
            break;
        }
        case TypeMat3x3: {
            QVariantList mat = value.toList();
            for (int i = 0; i < 9; ++i) writer.writeFloat32(mat.value(i).toFloat());
            break;
        }
        case TypeMat4x4: {
            QVariantList mat = value.toList();
            for (int i = 0; i < 16; ++i) writer.writeFloat32(mat.value(i).toFloat());
            break;
        }
        case TypeEnumAlt: {
            QVariantMap enumVal = value.toMap();
            writer.writeU32(enumVal["value"].toUInt());
            writer.writeU32(enumVal["classId"].toUInt());
            break;
        }
        case TypeString:
        case TypeVarString:
            serializeVarString(writer, value.toString());
            break;
        case TypeMap:
        case TypeMapAlt:
            serializeMap(writer, value, elementType);
            break;
        case TypeArray: {
            QVariantMap arr = value.toMap();
            writer.writeU8(0x0B);
            writer.writeU32(arr["count"].toUInt());
            QVariantList elements = arr["elements"].toList();
            int elemSize = typeSizeBytes(elementType);
            for (const QVariant& elem : elements) {
                if (elemSize == 1) {
                    writer.writeU8(static_cast<uint8_t>(elem.toUInt()));
                } else if (elemSize == 4) {
                    writer.writeU32(elem.toUInt());
                } else if (elemSize == 8) {
                    writer.writeU64(elem.toULongLong());
                }
            }
            break;
        }
        default:
            // Unknown type - try to write as raw bytes
            if (value.typeId() == QMetaType::QByteArray) {
                writer.writeBytes(value.toByteArray());
            }
            break;
    }
}

void Section4::serializeMap(BinaryWriter& writer, const QVariant& value, uint8_t elementType) const
{
    QVariantMap mapData = value.toMap();

    writer.writeU8(0x0B);
    writer.writeU32(mapData["count"].toUInt());

    if (elementType == TypeClass || elementType == 0x16) {
        QVariantList entries = mapData["entries"].toList();
        for (const QVariant& entryVar : entries) {
            QVariantMap entry = entryVar.toMap();

            // ObjectInfo for CLASS entry
            ObjectInfo info;
            info.nbClassVersions = 0;
            info.objectName = 0;
            info.objectId = 0;
            info.instancingMode = 0;
            serializeObjectInfo(writer, info);

            // TypeHash
            writer.writeU32(entry["typeHash"].toUInt());

            // Begin Object section
            int objectSectionPos = writer.openSection();

            // Begin Properties section
            int propertiesSectionPos = writer.openSection();

            // Write properties
            QVariantList props = entry["properties"].toList();
            for (const QVariant& propVar : props) {
                QVariantMap propMap = propVar.toMap();

                int propSectionPos = writer.openSection();

                writer.writeU32(propMap["propertyId"].toUInt());
                // Type descriptor - simplified, just write zeros
                writer.writeBytes(QByteArray(8, 0));

                // Serialize value
                uint8_t propTypeCode = static_cast<uint8_t>(propMap["typeCode"].toUInt());
                serializeValue(writer, propTypeCode, propMap["value"], 0, 0);

                writer.closeSection();
            }

            writer.closeSection(); // Properties

            // Dynamic properties size (always 0)
            writer.writeU32(0);

            writer.closeSection(); // Object
        }
    }
}

void Section4::serializeProperty(BinaryWriter& writer, const S4Property& prop) const
{
    // Begin property section
    int propSectionPos = writer.openSection();

    // Property ID
    writer.writeU32(prop.propertyId);

    // Type Descriptor
    writer.writeBytes(prop.typeDescriptor);

    // Value
    uint32_t typeHash = 0;
    if (prop.typeDescriptor.size() >= 4) {
        typeHash = static_cast<uint32_t>(static_cast<uint8_t>(prop.typeDescriptor[0])) |
                   (static_cast<uint32_t>(static_cast<uint8_t>(prop.typeDescriptor[1])) << 8) |
                   (static_cast<uint32_t>(static_cast<uint8_t>(prop.typeDescriptor[2])) << 16) |
                   (static_cast<uint32_t>(static_cast<uint8_t>(prop.typeDescriptor[3])) << 24);
    }

    serializeValue(writer, prop.typeCode, prop.value, prop.elementType, typeHash);

    writer.closeSection();
}

QByteArray Section4::serialize() const
{
    BinaryWriter writer;

    // Root ObjectInfo header
    serializeObjectInfo(writer, m_rootInfo);

    // Root TypeHash
    writer.writeU32(m_rootTypeHash);

    // Begin Object section
    int objectSectionPos = writer.openSection();

    // Begin Properties section
    int propertiesSectionPos = writer.openSection();

    // Write properties
    for (const S4Property& prop : m_properties) {
        serializeProperty(writer, prop);
    }

    writer.closeSection(); // Properties

    // Dynamic properties section
    writer.openSection();

    for (const S4Property& prop : m_dynProps) {
        serializeProperty(writer, prop);
    }

    writer.closeSection(); // Dynamic properties (backpatches size)

    writer.closeSection(); // Object

    return writer.data();
}

} // namespace acb
