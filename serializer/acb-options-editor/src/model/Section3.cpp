#include "Section3.h"
#include "core/BinaryReader.h"
#include "core/BinaryWriter.h"
#include <QVariantList>

namespace acb {

Section3::Section3()
{
    m_header.nbClassVersionsInfo = 0;
    m_header.objectNameLength = 0;
    m_header.objectId = 0;
    m_header.instancingMode = 0;
    m_header.typeHash = 0;
}

Section3::~Section3()
{
}

int Section3::typeSizeBytes(uint8_t typeCode)
{
    switch (typeCode) {
        case TypeBool:
        case TypeInt8:
        case TypeUInt8:
            return 1;
        case TypeInt16:
        case TypeUInt16:
            return 2;
        case TypeInt32:
        case TypeUInt32:
        case TypeFloat32:
            return 4;
        case TypeInt64:
        case TypeUInt64:
        case TypeFloat64:
        case TypeVec2:
            return 8;
        case TypeVec3:
            return 12;
        case TypeVec4:
        case TypeQuat:
            return 16;
        case TypeMat3x3:
            return 36;
        case TypeMat4x4:
            return 64;
        default:
            return -1;
    }
}

QVariant Section3::parseValue(BinaryReader& reader, uint8_t typeCode)
{
    switch (typeCode) {
        case TypeBool:
            return QVariant(reader.readU8() != 0);
        case TypeInt8:
            return QVariant(reader.readS8());
        case TypeUInt8:
            return QVariant(reader.readU8());
        case TypeInt16:
            return QVariant(reader.readS16());
        case TypeUInt16:
            return QVariant(reader.readU16());
        case TypeInt32:
            return QVariant(reader.readS32());
        case TypeUInt32:
            return QVariant(reader.readU32());
        case TypeInt64:
            return QVariant(static_cast<qint64>(reader.readS64()));
        case TypeUInt64:
            return QVariant(static_cast<quint64>(reader.readU64()));
        case TypeFloat32:
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
        case TypeVec4:
        case TypeQuat: {
            QVariantList vec;
            vec << reader.readFloat32() << reader.readFloat32()
                << reader.readFloat32() << reader.readFloat32();
            return vec;
        }
        case TypeMat3x3: {
            QVariantList mat;
            for (int i = 0; i < 9; ++i) {
                mat << reader.readFloat32();
            }
            return mat;
        }
        case TypeMat4x4: {
            QVariantList mat;
            for (int i = 0; i < 16; ++i) {
                mat << reader.readFloat32();
            }
            return mat;
        }
        default:
            return QVariant();
    }
}

void Section3::serializeValue(BinaryWriter& writer, uint8_t typeCode, const QVariant& value) const
{
    switch (typeCode) {
        case TypeBool:
            writer.writeU8(value.toBool() ? 1 : 0);
            break;
        case TypeInt8:
            writer.writeS8(static_cast<int8_t>(value.toInt()));
            break;
        case TypeUInt8:
            writer.writeU8(static_cast<uint8_t>(value.toUInt()));
            break;
        case TypeInt16:
            writer.writeS16(static_cast<int16_t>(value.toInt()));
            break;
        case TypeUInt16:
            writer.writeU16(static_cast<uint16_t>(value.toUInt()));
            break;
        case TypeInt32:
            writer.writeS32(value.toInt());
            break;
        case TypeUInt32:
            writer.writeU32(value.toUInt());
            break;
        case TypeInt64:
            writer.writeS64(value.toLongLong());
            break;
        case TypeUInt64:
            writer.writeU64(value.toULongLong());
            break;
        case TypeFloat32:
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
        case TypeVec4:
        case TypeQuat: {
            QVariantList vec = value.toList();
            writer.writeFloat32(vec.value(0).toFloat());
            writer.writeFloat32(vec.value(1).toFloat());
            writer.writeFloat32(vec.value(2).toFloat());
            writer.writeFloat32(vec.value(3).toFloat());
            break;
        }
        case TypeMat3x3: {
            QVariantList mat = value.toList();
            for (int i = 0; i < 9; ++i) {
                writer.writeFloat32(mat.value(i).toFloat());
            }
            break;
        }
        case TypeMat4x4: {
            QVariantList mat = value.toList();
            for (int i = 0; i < 16; ++i) {
                writer.writeFloat32(mat.value(i).toFloat());
            }
            break;
        }
        default:
            break;
    }
}

Section3::S3Property Section3::parsePropertyRecord(BinaryReader& reader)
{
    S3Property prop;

    int32_t propSize = reader.readS32();
    if (propSize < 13) {
        return prop;
    }

    prop.hash = reader.readU32();
    prop.typeInfo = reader.readBytes(8);
    prop.flags = reader.readU8();

    uint8_t typeCode = static_cast<uint8_t>(prop.typeInfo[6]) & 0x3F;
    int expectedSize = typeSizeBytes(typeCode);
    int valueSize = propSize - 13;

    if (expectedSize > 0 && valueSize == expectedSize) {
        prop.value = parseValue(reader, typeCode);
    } else if (valueSize > 0) {
        prop.value = QVariant(reader.readBytes(valueSize));
    }

    return prop;
}

bool Section3::parse()
{
    if (m_rawDecompressed.isEmpty()) {
        return false;
    }

    BinaryReader reader(m_rawDecompressed);

    // ObjectInfo Header (0x00-0x0D)
    // FUN_01b08ce0

    // NbClassVersionsInfo (1 byte)
    m_header.nbClassVersionsInfo = reader.readU8();

    // ObjectName length (4 bytes) - string length, usually 0
    m_header.objectNameLength = reader.readU32();
    // Skip object name string if present
    if (m_header.objectNameLength > 0) {
        reader.skip(static_cast<int>(m_header.objectNameLength));
    }

    // ObjectID (4 bytes)
    m_header.objectId = reader.readU32();

    // InstancingMode (1 byte)
    m_header.instancingMode = reader.readU8();

    // TypeHash (4 bytes) - should match section root hash
    m_header.typeHash = reader.readU32();

    // Section Size Reservations (0x0E-0x19) - these are computed values, skip them
    reader.readU32(); // Object section size
    reader.readU32(); // Properties section size
    reader.readU32(); // Base class section size

    // Base Class Field (0x1A-0x2A) - NO size field
    // Format: Hash(4) + type_info(8) + flags(1) + value(4) = 17 bytes
    m_baseClass.hash = reader.readU32();
    m_baseClass.typeInfo = reader.readBytes(8);
    m_baseClass.flags = reader.readU8();
    m_baseClass.value = reader.readU32();

    // Parse properties until dynamic properties section
    // Each property: [size 4][hash 4][type_info 8][flags 1][value N]
    m_properties.clear();
    m_dynProps.clear();

    // Parse regular properties - we read until we hit a size that looks like dynprops marker
    // The pattern is: properties continue until we read a 4-byte value that when interpreted
    // as the start of dynprops content (or 0 for empty), makes sense
    while (reader.remaining() >= 4) {
        int32_t propSize = reader.readS32();

        // If propSize is 0, this is the dynamic properties section size (empty)
        if (propSize == 0) {
            // No dynamic properties
            break;
        }

        // If propSize looks invalid, it might be the dynprops size for non-empty dynprops
        if (propSize < 13 || propSize > reader.remaining()) {
            // This is likely the dynprops section size
            if (propSize > 0 && propSize <= reader.remaining()) {
                // Parse dynamic properties content
                int dynPropsEnd = reader.tell() + propSize;
                while (reader.tell() < dynPropsEnd && reader.remaining() >= 17) {
                    S3Property dynProp = parsePropertyRecord(reader);
                    m_dynProps.append(dynProp);
                }
                reader.seek(dynPropsEnd);
            }
            break;
        }

        // Valid property - parse it
        S3Property prop;
        prop.hash = reader.readU32();
        prop.typeInfo = reader.readBytes(8);
        prop.flags = reader.readU8();

        uint8_t typeCode = static_cast<uint8_t>(prop.typeInfo[6]) & 0x3F;
        int expectedSize = typeSizeBytes(typeCode);
        int valueSize = propSize - 13;

        if (expectedSize > 0 && valueSize == expectedSize) {
            prop.value = parseValue(reader, typeCode);
        } else if (valueSize > 0) {
            prop.value = QVariant(reader.readBytes(valueSize));
        }

        m_properties.append(prop);
    }

    buildPropertyTree();

    m_valid = true;
    return true;
}

void Section3::buildPropertyTree()
{
    delete m_rootProperty;
    m_rootProperty = nullptr;

    // Create root property
    m_rootProperty = new Property(m_header.typeHash);

    // Add base class as first child
    Property* baseClassProp = new Property(m_baseClass.hash);
    baseClassProp->setTypeInfo(m_baseClass.typeInfo);
    baseClassProp->setFlags(m_baseClass.flags);
    baseClassProp->value().setType(TypeCode::UInt32);
    baseClassProp->value().setUInt32(m_baseClass.value);
    m_rootProperty->addChild(baseClassProp);

    // Add regular properties
    for (const S3Property& prop : m_properties) {
        Property* child = buildPropertyFromS3(prop, QString("0x%1").arg(prop.hash, 8, 16, QChar('0')));
        if (child) {
            m_rootProperty->addChild(child);
        }
    }
}

Property* Section3::buildPropertyFromS3(const S3Property& prop, const QString& name)
{
    Q_UNUSED(name);

    Property* result = new Property(prop.hash);
    result->setTypeInfo(prop.typeInfo);
    result->setFlags(prop.flags);

    uint8_t typeCode = static_cast<uint8_t>(prop.typeInfo[6]) & 0x3F;

    switch (typeCode) {
        case TypeBool:
            result->value().setType(TypeCode::Bool);
            result->value().setBool(prop.value.toBool());
            break;
        case TypeInt8:
            result->value().setType(TypeCode::Int8);
            result->value().setInt8(static_cast<int8_t>(prop.value.toInt()));
            break;
        case TypeUInt8:
            result->value().setType(TypeCode::UInt8);
            result->value().setUInt8(static_cast<uint8_t>(prop.value.toUInt()));
            break;
        case TypeInt16:
            result->value().setType(TypeCode::Int16);
            result->value().setInt16(static_cast<int16_t>(prop.value.toInt()));
            break;
        case TypeUInt16:
            result->value().setType(TypeCode::UInt16);
            result->value().setUInt16(static_cast<uint16_t>(prop.value.toUInt()));
            break;
        case TypeInt32:
            result->value().setType(TypeCode::Int32);
            result->value().setInt32(prop.value.toInt());
            break;
        case TypeUInt32:
            result->value().setType(TypeCode::UInt32);
            result->value().setUInt32(prop.value.toUInt());
            break;
        case TypeInt64:
            result->value().setType(TypeCode::Int64);
            result->value().setInt64(prop.value.toLongLong());
            break;
        case TypeUInt64:
            result->value().setType(TypeCode::UInt64);
            result->value().setUInt64(prop.value.toULongLong());
            break;
        case TypeFloat32:
            result->value().setType(TypeCode::Float32);
            result->value().setFloat32(prop.value.toFloat());
            break;
        case TypeFloat64:
            result->value().setType(TypeCode::Float64);
            result->value().setFloat64(prop.value.toDouble());
            break;
        case TypeVec2:
            result->value().setType(TypeCode::Vec2);
            {
                QVariantList v = prop.value.toList();
                Vec2 vec = {v.value(0).toFloat(), v.value(1).toFloat()};
                result->value().setVec2(vec);
            }
            break;
        case TypeVec3:
            result->value().setType(TypeCode::Vec3);
            {
                QVariantList v = prop.value.toList();
                Vec3 vec = {v.value(0).toFloat(), v.value(1).toFloat(), v.value(2).toFloat()};
                result->value().setVec3(vec);
            }
            break;
        case TypeVec4:
        case TypeQuat:
            result->value().setType(TypeCode::Vec4);
            {
                QVariantList v = prop.value.toList();
                Vec4 vec = {v.value(0).toFloat(), v.value(1).toFloat(),
                            v.value(2).toFloat(), v.value(3).toFloat()};
                result->value().setVec4(vec);
            }
            break;
        default:
            // Unknown type - store as raw bytes if available
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

QByteArray Section3::serialize() const
{
    BinaryWriter writer;

    // ObjectInfo Header
    writer.writeU8(m_header.nbClassVersionsInfo);
    writer.writeU32(m_header.objectNameLength);
    // Skip object name string if present (unlikely)
    writer.writeU32(m_header.objectId);
    writer.writeU8(m_header.instancingMode);
    writer.writeU32(m_header.typeHash);

    // Open Object section (reserves 4 bytes)
    int objectSectionPos = writer.openSection();

    // Open Properties section (reserves 4 bytes)
    int propertiesSectionPos = writer.openSection();

    // Open Base class section (reserves 4 bytes)
    int baseClassSectionPos = writer.openSection();

    // Write base class field (no size field)
    writer.writeU32(m_baseClass.hash);
    writer.writeBytes(m_baseClass.typeInfo);
    writer.writeU8(m_baseClass.flags);
    writer.writeU32(m_baseClass.value);

    // Close base class section
    writer.closeSection();

    // Write regular properties
    for (const S3Property& prop : m_properties) {
        // Open property section
        int propSectionPos = writer.openSection();

        writer.writeU32(prop.hash);
        writer.writeBytes(prop.typeInfo);
        writer.writeU8(prop.flags);

        // Write value based on type
        uint8_t typeCode = static_cast<uint8_t>(prop.typeInfo[6]) & 0x3F;
        if (prop.value.typeId() == QMetaType::QByteArray) {
            // Raw bytes - write directly
            writer.writeBytes(prop.value.toByteArray());
        } else {
            serializeValue(writer, typeCode, prop.value);
        }

        // Close property section
        writer.closeSection();
    }

    // Close Properties section
    writer.closeSection();

    // Open Dynamic Properties section
    writer.openSection();

    // Write dynamic properties if any
    for (const S3Property& prop : m_dynProps) {
        writer.openSection();

        writer.writeU32(prop.hash);
        writer.writeBytes(prop.typeInfo);
        writer.writeU8(prop.flags);

        uint8_t typeCode = static_cast<uint8_t>(prop.typeInfo[6]) & 0x3F;
        if (prop.value.typeId() == QMetaType::QByteArray) {
            writer.writeBytes(prop.value.toByteArray());
        } else {
            serializeValue(writer, typeCode, prop.value);
        }

        writer.closeSection();
    }

    // Close Dynamic Properties section (backpatches size)
    writer.closeSection();

    // Close Object section
    writer.closeSection();

    return writer.data();
}

} // namespace acb
