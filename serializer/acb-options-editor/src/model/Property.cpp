#include "Property.h"
#include "core/BinaryReader.h"
#include "core/BinaryWriter.h"
#include "core/HashLookup.h"

namespace acb {

Property::Property()
    : m_hash(0)
    , m_flags(0x0B)
    , m_parent(nullptr)
{
    m_typeInfo.fill(0, 8);
}

Property::Property(uint32_t hash)
    : m_hash(hash)
    , m_flags(0x0B)
    , m_parent(nullptr)
{
    m_typeInfo.fill(0, 8);
}

Property::~Property()
{
    clearChildren();
}

TypeCode Property::typeCode() const
{
    return extractTypeCode(m_typeInfo);
}

void Property::addChild(Property* child)
{
    if (child) {
        child->setParent(this);
        m_children.append(child);
    }
}

void Property::removeChild(Property* child)
{
    if (child) {
        m_children.removeOne(child);
        child->setParent(nullptr);
    }
}

void Property::clearChildren()
{
    qDeleteAll(m_children);
    m_children.clear();
}

Property* Property::child(int index) const
{
    if (index >= 0 && index < m_children.size()) {
        return m_children[index];
    }
    return nullptr;
}

int Property::row() const
{
    if (m_parent) {
        return m_parent->m_children.indexOf(const_cast<Property*>(this));
    }
    return 0;
}

QString Property::displayName() const
{
    QString name = HashLookup::lookupPropertyName(m_hash);
    if (!name.isEmpty()) {
        return name;
    }
    return QString("0x%1").arg(m_hash, 8, 16, QChar('0')).toUpper();
}

QString Property::typeName() const
{
    return typeCodeName(typeCode());
}

bool Property::isEditable() const
{
    return m_value.isEditable();
}

void Property::parse(BinaryReader& reader, SerializerMode mode)
{
    // Read hash (4 bytes)
    m_hash = reader.readU32();

    // Read type info (8 bytes)
    m_typeInfo = reader.readBytes(8);

    // Read flags (1 byte) - only in Mode 0
    if (mode == SerializerMode::Mode0) {
        m_flags = reader.readU8();
    } else {
        m_flags = 0x0B;  // Default for Mode 3
    }

    // Parse value based on type
    TypeCode type = typeCode();
    m_value.setType(type);

    int size = typeSizeBytes(type);
    if (size > 0) {
        // Fixed-size type
        QByteArray bytes = reader.readBytes(size);
        BinaryReader valueReader(bytes);

        switch (type) {
            case TypeCode::Bool:
                m_value.setBool(valueReader.readU8() != 0);
                break;
            case TypeCode::Int8:
                m_value.setInt8(valueReader.readS8());
                break;
            case TypeCode::UInt8:
                m_value.setUInt8(valueReader.readU8());
                break;
            case TypeCode::Int16:
                m_value.setInt16(valueReader.readS16());
                break;
            case TypeCode::UInt16:
                m_value.setUInt16(valueReader.readU16());
                break;
            case TypeCode::Int32:
                m_value.setInt32(valueReader.readS32());
                break;
            case TypeCode::UInt32:
                m_value.setUInt32(valueReader.readU32());
                break;
            case TypeCode::Int64:
                m_value.setInt64(valueReader.readS64());
                break;
            case TypeCode::UInt64:
                m_value.setUInt64(valueReader.readU64());
                break;
            case TypeCode::Float32:
                m_value.setFloat32(valueReader.readFloat32());
                break;
            case TypeCode::Float64:
                m_value.setFloat64(valueReader.readFloat64());
                break;
            case TypeCode::Vec2: {
                Vec2 v;
                v.x = valueReader.readFloat32();
                v.y = valueReader.readFloat32();
                m_value.setVec2(v);
                break;
            }
            case TypeCode::Vec3: {
                Vec3 v;
                v.x = valueReader.readFloat32();
                v.y = valueReader.readFloat32();
                v.z = valueReader.readFloat32();
                m_value.setVec3(v);
                break;
            }
            case TypeCode::Vec4:
            case TypeCode::Quat: {
                Vec4 v;
                v.x = valueReader.readFloat32();
                v.y = valueReader.readFloat32();
                v.z = valueReader.readFloat32();
                v.w = valueReader.readFloat32();
                m_value.setVec4(v);
                break;
            }
            case TypeCode::EnumVariant:
                m_value.setUInt64(valueReader.readU64());
                break;
            default:
                m_value.setRawBytes(bytes);
                break;
        }
    } else {
        // Variable-size or container type
        m_value.setRawBytes(QByteArray());
    }
}

void Property::serialize(BinaryWriter& writer, SerializerMode mode) const
{
    // Write hash (4 bytes)
    writer.writeU32(m_hash);

    // Write type info (8 bytes)
    writer.writeBytes(m_typeInfo);

    // Write flags (1 byte) - only in Mode 0
    if (mode == SerializerMode::Mode0) {
        writer.writeU8(m_flags);
    }

    // Write value based on type
    TypeCode type = typeCode();
    int size = typeSizeBytes(type);

    if (size > 0) {
        switch (type) {
            case TypeCode::Bool:
                writer.writeU8(m_value.asBool() ? 1 : 0);
                break;
            case TypeCode::Int8:
                writer.writeS8(m_value.asInt8());
                break;
            case TypeCode::UInt8:
                writer.writeU8(m_value.asUInt8());
                break;
            case TypeCode::Int16:
                writer.writeS16(m_value.asInt16());
                break;
            case TypeCode::UInt16:
                writer.writeU16(m_value.asUInt16());
                break;
            case TypeCode::Int32:
                writer.writeS32(m_value.asInt32());
                break;
            case TypeCode::UInt32:
                writer.writeU32(m_value.asUInt32());
                break;
            case TypeCode::Int64:
                writer.writeS64(m_value.asInt64());
                break;
            case TypeCode::UInt64:
                writer.writeU64(m_value.asUInt64());
                break;
            case TypeCode::Float32:
                writer.writeFloat32(m_value.asFloat32());
                break;
            case TypeCode::Float64:
                writer.writeFloat64(m_value.asFloat64());
                break;
            case TypeCode::Vec2: {
                Vec2 v = m_value.asVec2();
                writer.writeFloat32(v.x);
                writer.writeFloat32(v.y);
                break;
            }
            case TypeCode::Vec3: {
                Vec3 v = m_value.asVec3();
                writer.writeFloat32(v.x);
                writer.writeFloat32(v.y);
                writer.writeFloat32(v.z);
                break;
            }
            case TypeCode::Vec4:
            case TypeCode::Quat: {
                Vec4 v = m_value.asVec4();
                writer.writeFloat32(v.x);
                writer.writeFloat32(v.y);
                writer.writeFloat32(v.z);
                writer.writeFloat32(v.w);
                break;
            }
            case TypeCode::EnumVariant:
                writer.writeU64(m_value.asUInt64());
                break;
            default:
                writer.writeBytes(m_value.asRawBytes());
                break;
        }
    } else {
        // Variable-size - write raw bytes if available
        writer.writeBytes(m_value.asRawBytes());
    }
}

} // namespace acb
