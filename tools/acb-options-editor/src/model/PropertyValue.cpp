#include "PropertyValue.h"

namespace acb {

PropertyValue::PropertyValue()
    : m_type(TypeCode::Unknown)
{
}

PropertyValue::PropertyValue(TypeCode type)
    : m_type(type)
{
}

bool PropertyValue::isEditable() const
{
    switch (m_type) {
        case TypeCode::Bool:
        case TypeCode::Int8:
        case TypeCode::UInt8:
        case TypeCode::Int16:
        case TypeCode::UInt16:
        case TypeCode::Int32:
        case TypeCode::UInt32:
        case TypeCode::Int64:
        case TypeCode::UInt64:
        case TypeCode::Float32:
        case TypeCode::Float64:
        case TypeCode::String:
            return true;
        default:
            return false;
    }
}

bool PropertyValue::isContainer() const
{
    return acb::isContainerType(m_type);
}

bool PropertyValue::asBool() const { return m_data.toBool(); }
int8_t PropertyValue::asInt8() const { return static_cast<int8_t>(m_data.toInt()); }
uint8_t PropertyValue::asUInt8() const { return static_cast<uint8_t>(m_data.toUInt()); }
int16_t PropertyValue::asInt16() const { return static_cast<int16_t>(m_data.toInt()); }
uint16_t PropertyValue::asUInt16() const { return static_cast<uint16_t>(m_data.toUInt()); }
int32_t PropertyValue::asInt32() const { return m_data.toInt(); }
uint32_t PropertyValue::asUInt32() const { return m_data.toUInt(); }
int64_t PropertyValue::asInt64() const { return m_data.toLongLong(); }
uint64_t PropertyValue::asUInt64() const { return m_data.toULongLong(); }
float PropertyValue::asFloat32() const { return m_data.toFloat(); }
double PropertyValue::asFloat64() const { return m_data.toDouble(); }
QString PropertyValue::asString() const { return m_data.toString(); }
QByteArray PropertyValue::asRawBytes() const { return m_rawBytes; }

Vec2 PropertyValue::asVec2() const { return m_data.value<Vec2>(); }
Vec3 PropertyValue::asVec3() const { return m_data.value<Vec3>(); }
Vec4 PropertyValue::asVec4() const { return m_data.value<Vec4>(); }
Mat3x3 PropertyValue::asMat3x3() const { return m_data.value<Mat3x3>(); }
Mat4x4 PropertyValue::asMat4x4() const { return m_data.value<Mat4x4>(); }

void PropertyValue::setBool(bool val) { m_data = val; }
void PropertyValue::setInt8(int8_t val) { m_data = val; }
void PropertyValue::setUInt8(uint8_t val) { m_data = val; }
void PropertyValue::setInt16(int16_t val) { m_data = val; }
void PropertyValue::setUInt16(uint16_t val) { m_data = val; }
void PropertyValue::setInt32(int32_t val) { m_data = val; }
void PropertyValue::setUInt32(uint32_t val) { m_data = val; }
void PropertyValue::setInt64(int64_t val) { m_data = static_cast<qlonglong>(val); }
void PropertyValue::setUInt64(uint64_t val) { m_data = static_cast<qulonglong>(val); }
void PropertyValue::setFloat32(float val) { m_data = val; }
void PropertyValue::setFloat64(double val) { m_data = val; }
void PropertyValue::setString(const QString& val) { m_data = val; }
void PropertyValue::setRawBytes(const QByteArray& val) { m_rawBytes = val; }

void PropertyValue::setVec2(const Vec2& val) { m_data = QVariant::fromValue(val); }
void PropertyValue::setVec3(const Vec3& val) { m_data = QVariant::fromValue(val); }
void PropertyValue::setVec4(const Vec4& val) { m_data = QVariant::fromValue(val); }
void PropertyValue::setMat3x3(const Mat3x3& val) { m_data = QVariant::fromValue(val); }
void PropertyValue::setMat4x4(const Mat4x4& val) { m_data = QVariant::fromValue(val); }

QString PropertyValue::toDisplayString() const
{
    switch (m_type) {
        case TypeCode::Bool:
            return asBool() ? "true" : "false";
        case TypeCode::Int8:
        case TypeCode::Int16:
        case TypeCode::Int32:
            return QString::number(asInt32());
        case TypeCode::UInt8:
        case TypeCode::UInt16:
        case TypeCode::UInt32:
            return QString("0x%1").arg(asUInt32(), 8, 16, QChar('0')).toUpper();
        case TypeCode::Int64:
            return QString::number(asInt64());
        case TypeCode::UInt64:
            return QString("0x%1").arg(asUInt64(), 16, 16, QChar('0')).toUpper();
        case TypeCode::Float32:
            return QString::number(asFloat32(), 'f', 6);
        case TypeCode::Float64:
            return QString::number(asFloat64(), 'f', 10);
        case TypeCode::String:
            return asString();
        case TypeCode::Vec2: {
            auto v = asVec2();
            return QString("(%1, %2)").arg(v.x).arg(v.y);
        }
        case TypeCode::Vec3: {
            auto v = asVec3();
            return QString("(%1, %2, %3)").arg(v.x).arg(v.y).arg(v.z);
        }
        case TypeCode::Vec4:
        case TypeCode::Quat: {
            auto v = asVec4();
            return QString("(%1, %2, %3, %4)").arg(v.x).arg(v.y).arg(v.z).arg(v.w);
        }
        case TypeCode::Container:
        case TypeCode::NestedObject:
        case TypeCode::Vector:
        case TypeCode::Array:
            return QString("[container]");
        default:
            if (!m_rawBytes.isEmpty()) {
                return m_rawBytes.toHex(' ').toUpper();
            }
            return QString("[unknown]");
    }
}

QVariant PropertyValue::toVariant() const
{
    return m_data;
}

void PropertyValue::fromVariant(const QVariant& val)
{
    switch (m_type) {
        case TypeCode::Bool:
            setBool(val.toBool());
            break;
        case TypeCode::Int8:
            setInt8(static_cast<int8_t>(val.toInt()));
            break;
        case TypeCode::UInt8:
            setUInt8(static_cast<uint8_t>(val.toUInt()));
            break;
        case TypeCode::Int16:
            setInt16(static_cast<int16_t>(val.toInt()));
            break;
        case TypeCode::UInt16:
            setUInt16(static_cast<uint16_t>(val.toUInt()));
            break;
        case TypeCode::Int32:
            setInt32(val.toInt());
            break;
        case TypeCode::UInt32:
            setUInt32(val.toUInt());
            break;
        case TypeCode::Int64:
            setInt64(val.toLongLong());
            break;
        case TypeCode::UInt64:
            setUInt64(val.toULongLong());
            break;
        case TypeCode::Float32:
            setFloat32(val.toFloat());
            break;
        case TypeCode::Float64:
            setFloat64(val.toDouble());
            break;
        case TypeCode::String:
            setString(val.toString());
            break;
        default:
            m_data = val;
            break;
    }
}

} // namespace acb
