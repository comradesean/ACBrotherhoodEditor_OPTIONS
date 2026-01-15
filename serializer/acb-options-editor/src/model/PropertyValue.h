#pragma once

#include <QVariant>
#include <QByteArray>
#include <QString>
#include <QVector>
#include <cstdint>
#include "core/TypeCodes.h"

namespace acb {

// Vector types for game data
struct Vec2 { float x, y; };
struct Vec3 { float x, y, z; };
struct Vec4 { float x, y, z, w; };
struct Mat3x3 { float m[9]; };
struct Mat4x4 { float m[16]; };

class PropertyValue {
public:
    PropertyValue();
    explicit PropertyValue(TypeCode type);

    // Type information
    TypeCode type() const { return m_type; }
    void setType(TypeCode type) { m_type = type; }
    bool isEditable() const;
    bool isContainer() const;

    // Primitive getters
    bool asBool() const;
    int8_t asInt8() const;
    uint8_t asUInt8() const;
    int16_t asInt16() const;
    uint16_t asUInt16() const;
    int32_t asInt32() const;
    uint32_t asUInt32() const;
    int64_t asInt64() const;
    uint64_t asUInt64() const;
    float asFloat32() const;
    double asFloat64() const;
    QString asString() const;
    QByteArray asRawBytes() const;

    // Vector/matrix getters
    Vec2 asVec2() const;
    Vec3 asVec3() const;
    Vec4 asVec4() const;
    Mat3x3 asMat3x3() const;
    Mat4x4 asMat4x4() const;

    // Primitive setters
    void setBool(bool val);
    void setInt8(int8_t val);
    void setUInt8(uint8_t val);
    void setInt16(int16_t val);
    void setUInt16(uint16_t val);
    void setInt32(int32_t val);
    void setUInt32(uint32_t val);
    void setInt64(int64_t val);
    void setUInt64(uint64_t val);
    void setFloat32(float val);
    void setFloat64(double val);
    void setString(const QString& val);
    void setRawBytes(const QByteArray& val);

    // Vector/matrix setters
    void setVec2(const Vec2& val);
    void setVec3(const Vec3& val);
    void setVec4(const Vec4& val);
    void setMat3x3(const Mat3x3& val);
    void setMat4x4(const Mat4x4& val);

    // Display helpers
    QString toDisplayString() const;
    QVariant toVariant() const;
    void fromVariant(const QVariant& val);

private:
    TypeCode m_type;
    QVariant m_data;
    QByteArray m_rawBytes;  // For unknown types
};

} // namespace acb

// Register types for QVariant
Q_DECLARE_METATYPE(acb::Vec2)
Q_DECLARE_METATYPE(acb::Vec3)
Q_DECLARE_METATYPE(acb::Vec4)
Q_DECLARE_METATYPE(acb::Mat3x3)
Q_DECLARE_METATYPE(acb::Mat4x4)
