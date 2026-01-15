#include "Section1.h"
#include "core/BinaryReader.h"
#include "core/BinaryWriter.h"

namespace acb {

Section1::Section1()
{
    m_objectInfo.nbClassVersions = 0;
    m_objectInfo.objectNameLength = 0;
    m_objectInfo.objectId = 0;
    m_objectInfo.instancingMode = 0;
}

Section1::~Section1()
{
}

uint32_t Section1::extractDescriptorType(uint32_t typeId)
{
    // From FUN_01b0c2e0: (type_id >> 16) & 0x3F
    return (typeId >> 16) & 0x3F;
}

QString Section1::valueFormat(uint32_t descriptorType)
{
    // Determine value format from descriptor type
    if (descriptorType == DescriptorBool) {
        return "bool";
    } else if (descriptorType == DescriptorString) {
        return "string";
    } else {
        return "numeric"; // Complex, Pointer, etc. are all 4 bytes
    }
}

uint32_t Section1::computeTypePrefix(uint32_t descriptorType)
{
    // Compute binary Type Prefix from descriptor type
    switch (descriptorType) {
        case DescriptorBool: return TypePrefixBool;       // 0x00 → 0x0E
        case DescriptorComplex: return TypePrefixNumeric; // 0x07 → 0x11
        case DescriptorPointer: return TypePrefixNumeric; // 0x12 → 0x11
        case DescriptorString: return TypePrefixString;   // 0x1A → 0x19
        default: return TypePrefixNumeric;
    }
}

QVariant Section1::parseValue(BinaryReader& reader, const QString& format)
{
    if (format == "bool") {
        return QVariant(reader.readU8() != 0);
    } else if (format == "string") {
        uint32_t strLen = reader.readU32();
        QByteArray strData = reader.readBytes(static_cast<int>(strLen));
        reader.readU8(); // null terminator
        return QVariant(QString::fromUtf8(strData));
    } else { // numeric
        return QVariant(reader.readU32());
    }
}

int Section1::valueSize(const QVariant& value, const QString& format) const
{
    if (format == "bool") {
        return 1;
    } else if (format == "string") {
        QString str = value.toString();
        QByteArray utf8 = str.toUtf8();
        return 4 + utf8.size() + 1; // len(4) + chars + null
    } else { // numeric
        return 4;
    }
}

void Section1::serializeValue(BinaryWriter& writer, const QVariant& value, const QString& format) const
{
    if (format == "bool") {
        writer.writeU8(value.toBool() ? 1 : 0);
    } else if (format == "string") {
        QString str = value.toString();
        QByteArray utf8 = str.toUtf8();
        writer.writeU32(static_cast<uint32_t>(utf8.size()));
        writer.writeBytes(utf8);
        writer.writeU8(0); // null terminator
    } else { // numeric
        writer.writeU32(value.toUInt());
    }
}

bool Section1::parse()
{
    if (m_rawDecompressed.isEmpty()) {
        return false;
    }

    BinaryReader reader(m_rawDecompressed);

    // =========================================================================
    // Platform-specific header handling
    // PC format:  10-byte zero prefix, then container hash at offset 10
    // PS3 format: 16-byte header, then container hash at offset 16
    //
    // Detect using section ID: 0xC5 = PC, 0xC6 = PS3
    // =========================================================================
    bool isPS3 = (m_header.sectionId() == 0x000000C6);

    // Read and store header for round-trip
    m_objectInfo.nbClassVersions = reader.readU8();

    if (!isPS3) {
        // PC format: standard ObjectInfo
        m_objectInfo.objectNameLength = reader.readU32();
        if (m_objectInfo.objectNameLength > 0 && m_objectInfo.objectNameLength < 10000) {
            reader.skip(static_cast<int>(m_objectInfo.objectNameLength));
        }
        m_objectInfo.objectId = reader.readU32();
        m_objectInfo.instancingMode = reader.readU8();
    } else {
        // PS3 format: different header structure
        // Skip remaining 15 bytes of PS3-specific header
        reader.skip(15);
        m_objectInfo.objectNameLength = 0;
        m_objectInfo.objectId = 0;
        m_objectInfo.instancingMode = 0;
    }

    // TypeHash (4 bytes) - should match our root hash
    uint32_t typeHash = reader.readU32();
    if (typeHash != m_rootHash) {
        qWarning() << "Section1: TypeHash mismatch:" << Qt::hex << typeHash << "vs" << m_rootHash;
    }

    // =========================================================================
    // Section Size Reservations (computed during serialization)
    // =========================================================================
    reader.readU32(); // Object block size
    reader.readU32(); // Properties block size
    reader.readU32(); // Root block size

    // =========================================================================
    // Root property (HAS block size already read above, NO Type prefix)
    // Format: Hash(4) + ClassID(4) + type_id(4) + PackedInfo(1) + Value(variable)
    // =========================================================================
    m_rootProp.hash = reader.readU32();
    m_rootProp.classId = reader.readU32();
    m_rootProp.typeId = reader.readU32();
    m_rootProp.packedInfo = reader.readU8();

    uint32_t rootDescriptor = extractDescriptorType(m_rootProp.typeId);
    QString rootFormat = valueFormat(rootDescriptor);
    m_rootProp.value = parseValue(reader, rootFormat);

    // =========================================================================
    // Child properties (NO block size, WITH Type prefix)
    // Read until we hit Dynamic Properties section
    // =========================================================================
    m_childProps.clear();
    m_dynProps.clear();

    while (reader.remaining() >= 4) {
        uint32_t marker = reader.peekU32();

        // Check for Dynamic Properties section
        // If marker is 0 or looks like a size (not a valid Type prefix), it's dynprops
        if (marker == 0 || (marker != TypePrefixBool && marker != TypePrefixNumeric && marker != TypePrefixString)) {
            uint32_t dynPropsSize = reader.readU32();

            // If size > 0, parse dynamic properties (same format as child properties)
            if (dynPropsSize > 0) {
                int dynPropsEnd = reader.tell() + static_cast<int>(dynPropsSize);
                while (reader.tell() < dynPropsEnd && reader.remaining() >= 17) {
                    S1Property prop;
                    uint32_t typePrefix = reader.readU32();
                    prop.hash = reader.readU32();
                    prop.classId = reader.readU32();
                    prop.typeId = reader.readU32();
                    prop.packedInfo = reader.readU8();

                    QString format;
                    if (typePrefix == TypePrefixBool) {
                        format = "bool";
                    } else if (typePrefix == TypePrefixString) {
                        format = "string";
                    } else {
                        format = "numeric";
                    }
                    prop.value = parseValue(reader, format);

                    m_dynProps.append(prop);
                }
                reader.seek(dynPropsEnd);
            }
            break;
        }

        // Read child property with type prefix
        // Format: Type(4) + Hash(4) + ClassID(4) + type_id(4) + PackedInfo(1) + Value(variable)
        S1Property prop;
        uint32_t typePrefix = reader.readU32();
        prop.hash = reader.readU32();
        prop.classId = reader.readU32();
        prop.typeId = reader.readU32();
        prop.packedInfo = reader.readU8();

        // Value format determined by Type prefix (NOT descriptor type)
        QString format;
        if (typePrefix == TypePrefixBool) {
            format = "bool";
        } else if (typePrefix == TypePrefixString) {
            format = "string";
        } else {
            format = "numeric";
        }
        prop.value = parseValue(reader, format);

        m_childProps.append(prop);
    }

    // Build the property tree for UI display
    buildPropertyTree();

    m_valid = true;
    return true;
}

void Section1::buildPropertyTree()
{
    // Clean up existing tree
    delete m_rootProperty;
    m_rootProperty = nullptr;

    // Create root property
    m_rootProperty = new Property(m_rootProp.hash);
    m_rootProperty->setFlags(m_rootProp.packedInfo);

    // Set root value
    uint32_t rootDescriptor = extractDescriptorType(m_rootProp.typeId);
    if (rootDescriptor == DescriptorBool) {
        m_rootProperty->value().setType(TypeCode::Bool);
        m_rootProperty->value().setBool(m_rootProp.value.toBool());
    } else if (rootDescriptor == DescriptorString) {
        m_rootProperty->value().setType(TypeCode::String);
        m_rootProperty->value().setString(m_rootProp.value.toString());
    } else {
        m_rootProperty->value().setType(TypeCode::UInt32);
        m_rootProperty->value().setUInt32(m_rootProp.value.toUInt());
    }

    // Build type info: classId (hash_id, 4 bytes) + typeId (type_id, 4 bytes)
    QByteArray typeInfo(8, 0);
    // First 4 bytes: classId (hash_id)
    typeInfo[0] = (m_rootProp.classId >> 0) & 0xFF;
    typeInfo[1] = (m_rootProp.classId >> 8) & 0xFF;
    typeInfo[2] = (m_rootProp.classId >> 16) & 0xFF;
    typeInfo[3] = (m_rootProp.classId >> 24) & 0xFF;
    // Next 4 bytes: typeId (type_id)
    typeInfo[4] = (m_rootProp.typeId >> 0) & 0xFF;
    typeInfo[5] = (m_rootProp.typeId >> 8) & 0xFF;
    typeInfo[6] = (m_rootProp.typeId >> 16) & 0xFF;
    typeInfo[7] = (m_rootProp.typeId >> 24) & 0xFF;
    m_rootProperty->setTypeInfo(typeInfo);

    // Add child properties
    for (const S1Property& childProp : m_childProps) {
        Property* child = new Property(childProp.hash);
        child->setFlags(childProp.packedInfo);

        uint32_t childDescriptor = extractDescriptorType(childProp.typeId);
        if (childDescriptor == DescriptorBool) {
            child->value().setType(TypeCode::Bool);
            child->value().setBool(childProp.value.toBool());
        } else if (childDescriptor == DescriptorString) {
            child->value().setType(TypeCode::String);
            child->value().setString(childProp.value.toString());
        } else {
            child->value().setType(TypeCode::UInt32);
            child->value().setUInt32(childProp.value.toUInt());
        }

        // Build type info: classId (hash_id, 4 bytes) + typeId (type_id, 4 bytes)
        QByteArray childTypeInfo(8, 0);
        // First 4 bytes: classId (hash_id)
        childTypeInfo[0] = (childProp.classId >> 0) & 0xFF;
        childTypeInfo[1] = (childProp.classId >> 8) & 0xFF;
        childTypeInfo[2] = (childProp.classId >> 16) & 0xFF;
        childTypeInfo[3] = (childProp.classId >> 24) & 0xFF;
        // Next 4 bytes: typeId (type_id)
        childTypeInfo[4] = (childProp.typeId >> 0) & 0xFF;
        childTypeInfo[5] = (childProp.typeId >> 8) & 0xFF;
        childTypeInfo[6] = (childProp.typeId >> 16) & 0xFF;
        childTypeInfo[7] = (childProp.typeId >> 24) & 0xFF;
        child->setTypeInfo(childTypeInfo);

        m_rootProperty->addChild(child);
    }
}

QByteArray Section1::serialize() const
{
    BinaryWriter writer;

    // =========================================================================
    // ObjectInfo Header (universal structure)
    // =========================================================================
    writer.writeU8(m_objectInfo.nbClassVersions);
    writer.writeU32(m_objectInfo.objectNameLength);
    // Object name string would go here if length > 0
    writer.writeU32(m_objectInfo.objectId);
    writer.writeU8(m_objectInfo.instancingMode);

    // TypeHash (4 bytes)
    writer.writeU32(m_rootHash);

    // =========================================================================
    // Compute sizes following LIFO backpatching logic
    // =========================================================================

    // Root property content size: Hash(4) + ClassID(4) + type_id(4) + PackedInfo(1) + Value
    uint32_t rootDescriptor = extractDescriptorType(m_rootProp.typeId);
    QString rootFormat = valueFormat(rootDescriptor);
    int rootValueSize = valueSize(m_rootProp.value, rootFormat);
    uint32_t rootBlockSize = 13 + rootValueSize; // 13 = Hash(4) + ClassID(4) + type_id(4) + PackedInfo(1)

    // Child properties total size
    int childTotal = 0;
    for (const S1Property& prop : m_childProps) {
        uint32_t descType = extractDescriptorType(prop.typeId);
        QString format = valueFormat(descType);
        int valSize = valueSize(prop.value, format);
        childTotal += 17 + valSize; // Type(4) + Hash(4) + ClassID(4) + type_id(4) + PackedInfo(1) + Value
    }

    // Properties block: root_block_size_field(4) + root_content + children
    uint32_t propertiesBlockSize = 4 + rootBlockSize + childTotal;

    // Object block: properties_block_size_field(4) + properties_content + dynamic_props_block(4)
    uint32_t objectBlockSize = 4 + propertiesBlockSize + 4;

    // Write section size reservations (computed block sizes)
    writer.writeU32(objectBlockSize);
    writer.writeU32(propertiesBlockSize);
    writer.writeU32(rootBlockSize);

    // =========================================================================
    // Root property (NO Type prefix - block size already written above)
    // =========================================================================
    writer.writeU32(m_rootProp.hash);
    writer.writeU32(m_rootProp.classId);
    writer.writeU32(m_rootProp.typeId);
    writer.writeU8(m_rootProp.packedInfo);  // Use parsed value, not hardcoded constant
    serializeValue(writer, m_rootProp.value, rootFormat);

    // =========================================================================
    // Child properties (WITH Type prefix, NO block size)
    // =========================================================================
    for (const S1Property& prop : m_childProps) {
        uint32_t descType = extractDescriptorType(prop.typeId);
        uint32_t typePrefix = computeTypePrefix(descType);
        QString format = valueFormat(descType);

        writer.writeU32(typePrefix);
        writer.writeU32(prop.hash);
        writer.writeU32(prop.classId);
        writer.writeU32(prop.typeId);
        writer.writeU8(prop.packedInfo);  // Use parsed value, not hardcoded constant
        serializeValue(writer, prop.value, format);
    }

    // =========================================================================
    // Dynamic Properties section
    // =========================================================================
    if (m_dynProps.isEmpty()) {
        // Empty - just write size 0
        writer.writeU32(0);
    } else {
        // Calculate dynprops size
        int dynPropsContentSize = 0;
        for (const S1Property& prop : m_dynProps) {
            uint32_t descType = extractDescriptorType(prop.typeId);
            QString format = valueFormat(descType);
            int valSize = valueSize(prop.value, format);
            dynPropsContentSize += 17 + valSize; // Type(4) + Hash(4) + ClassID(4) + type_id(4) + PackedInfo(1) + Value
        }

        writer.writeU32(static_cast<uint32_t>(dynPropsContentSize));

        // Write dynprops (same format as child properties)
        for (const S1Property& prop : m_dynProps) {
            uint32_t descType = extractDescriptorType(prop.typeId);
            uint32_t typePrefix = computeTypePrefix(descType);
            QString format = valueFormat(descType);

            writer.writeU32(typePrefix);
            writer.writeU32(prop.hash);
            writer.writeU32(prop.classId);
            writer.writeU32(prop.typeId);
            writer.writeU8(prop.packedInfo);
            serializeValue(writer, prop.value, format);
        }
    }

    return writer.data();
}

} // namespace acb
