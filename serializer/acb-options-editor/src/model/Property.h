#pragma once

#include <QList>
#include <QString>
#include <QByteArray>
#include <cstdint>
#include "PropertyValue.h"
#include "core/TypeCodes.h"

namespace acb {

class BinaryReader;
class BinaryWriter;

class Property {
public:
    Property();
    explicit Property(uint32_t hash);
    ~Property();

    // Property identification
    uint32_t hash() const { return m_hash; }
    void setHash(uint32_t hash) { m_hash = hash; }

    // Type information (8 bytes from binary)
    QByteArray typeInfo() const { return m_typeInfo; }
    void setTypeInfo(const QByteArray& typeInfo) { m_typeInfo = typeInfo; }
    TypeCode typeCode() const;

    // Flags (1 byte, typically 0x0B)
    uint8_t flags() const { return m_flags; }
    void setFlags(uint8_t flags) { m_flags = flags; }

    // Value
    PropertyValue& value() { return m_value; }
    const PropertyValue& value() const { return m_value; }
    void setValue(const PropertyValue& value) { m_value = value; }

    // Tree structure for nested properties
    Property* parent() const { return m_parent; }
    void setParent(Property* parent) { m_parent = parent; }

    const QList<Property*>& children() const { return m_children; }
    void addChild(Property* child);
    void removeChild(Property* child);
    void clearChildren();
    int childCount() const { return m_children.size(); }
    Property* child(int index) const;
    int row() const;

    // Display helpers
    QString displayName() const;
    QString typeName() const;
    bool isEditable() const;

    // Serialization
    void parse(BinaryReader& reader, SerializerMode mode);
    void serialize(BinaryWriter& writer, SerializerMode mode) const;

private:
    uint32_t m_hash;
    QByteArray m_typeInfo;  // 8 bytes
    uint8_t m_flags;
    PropertyValue m_value;

    Property* m_parent;
    QList<Property*> m_children;
};

} // namespace acb
