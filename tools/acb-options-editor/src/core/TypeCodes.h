#pragma once

#include <QByteArray>
#include <QString>
#include <QMap>
#include <cstdint>

namespace acb {

enum class TypeCode : uint8_t {
    Bool = 0x00,
    Int8 = 0x01,
    UInt8 = 0x02,
    Int16 = 0x03,
    UInt16 = 0x04,
    Int32 = 0x05,
    UInt32 = 0x07,
    Int64 = 0x08,
    UInt64 = 0x09,
    Float32 = 0x0A,
    Float64 = 0x0B,
    Vec2 = 0x0C,
    Vec3 = 0x0D,
    Vec4 = 0x0E,
    Quat = 0x0F,
    Mat3x3 = 0x10,
    Mat4x4 = 0x11,
    String = 0x12,
    Container = 0x13,
    NestedObject = 0x16,
    Vector = 0x17,
    ArrayAlt = 0x18,
    EnumVariant = 0x19,
    Array = 0x1D,
    Unknown = 0xFF
};

enum class SerializerMode {
    Mode0,  // Standard mode with flags byte (Section 1, 2, 3)
    Mode3   // Binary mode without flags byte (Section 4)
};

enum class Platform {
    Unknown,
    PC,
    PS3
};

// Known section hashes
namespace SectionHash {
    constexpr uint32_t SaveGame = 0xBDBE3B52;               // Section 1
    constexpr uint32_t PlayerOptionsSaveData = 0x11FACE11; // Section 2
    constexpr uint32_t AssassinSingleProfileData = 0xC9876D66; // Section 3
    constexpr uint32_t AssassinMultiProfileData = 0xB4B55039;  // Section 4
}

// Extract type code from 8-byte type_info
inline TypeCode extractTypeCode(const QByteArray& typeInfo) {
    if (typeInfo.size() < 7) return TypeCode::Unknown;
    return static_cast<TypeCode>(static_cast<uint8_t>(typeInfo[6]) & 0x3F);
}

// Extract type code from 4-byte type_id (used in some contexts)
inline TypeCode extractTypeCodeFromId(uint32_t typeId) {
    return static_cast<TypeCode>((typeId >> 16) & 0x3F);
}

// Extract element type for containers
inline TypeCode extractElementType(const QByteArray& typeInfo) {
    if (typeInfo.size() < 7) return TypeCode::Unknown;
    // Element type is at different offset depending on context
    return static_cast<TypeCode>((static_cast<uint8_t>(typeInfo[6]) >> 6) |
                                  ((static_cast<uint8_t>(typeInfo[7]) & 0x0F) << 2));
}

// Get size in bytes for fixed-size types, -1 for variable
inline int typeSizeBytes(TypeCode code) {
    switch (code) {
        case TypeCode::Bool:
        case TypeCode::Int8:
        case TypeCode::UInt8:
            return 1;
        case TypeCode::Int16:
        case TypeCode::UInt16:
            return 2;
        case TypeCode::Int32:
        case TypeCode::UInt32:
        case TypeCode::Float32:
            return 4;
        case TypeCode::Int64:
        case TypeCode::UInt64:
        case TypeCode::Float64:
        case TypeCode::Vec2:
        case TypeCode::EnumVariant:
            return 8;
        case TypeCode::Vec3:
            return 12;
        case TypeCode::Vec4:
        case TypeCode::Quat:
            return 16;
        case TypeCode::Mat3x3:
            return 36;
        case TypeCode::Mat4x4:
            return 64;
        default:
            return -1; // Variable or unknown
    }
}

inline QString typeCodeName(TypeCode code) {
    static const QMap<TypeCode, QString> names = {
        {TypeCode::Bool, "bool"},
        {TypeCode::Int8, "int8"},
        {TypeCode::UInt8, "uint8"},
        {TypeCode::Int16, "int16"},
        {TypeCode::UInt16, "uint16"},
        {TypeCode::Int32, "int32"},
        {TypeCode::UInt32, "uint32"},
        {TypeCode::Int64, "int64"},
        {TypeCode::UInt64, "uint64"},
        {TypeCode::Float32, "float32"},
        {TypeCode::Float64, "float64"},
        {TypeCode::Vec2, "vec2"},
        {TypeCode::Vec3, "vec3"},
        {TypeCode::Vec4, "vec4"},
        {TypeCode::Quat, "quat"},
        {TypeCode::Mat3x3, "mat3x3"},
        {TypeCode::Mat4x4, "mat4x4"},
        {TypeCode::String, "string"},
        {TypeCode::Container, "container"},
        {TypeCode::NestedObject, "object"},
        {TypeCode::Vector, "vector"},
        {TypeCode::ArrayAlt, "array"},
        {TypeCode::EnumVariant, "enum"},
        {TypeCode::Array, "array"},
        {TypeCode::Unknown, "unknown"}
    };
    return names.value(code, "unknown");
}

inline bool isContainerType(TypeCode code) {
    return code == TypeCode::Container ||
           code == TypeCode::NestedObject ||
           code == TypeCode::Vector ||
           code == TypeCode::Array ||
           code == TypeCode::ArrayAlt;
}

} // namespace acb
