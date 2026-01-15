#pragma once

#include <QString>
#include <QMap>
#include <cstdint>

namespace acb {

class HashLookup {
public:
    // Look up property name from hash
    static QString lookupPropertyName(uint32_t hash);

    // Look up section name from root hash
    static QString lookupSectionName(uint32_t hash);

    // Register a custom hash -> name mapping
    static void registerHash(uint32_t hash, const QString& name);

    // Load hash mappings from JSON file
    // Format: { "hashes": { "0xDEADBEEF": "property_name", ... } }
    // Or: { "hashes": { "3735928559": "property_name", ... } }
    static bool loadFromJson(const QString& path);

    // Load hash mappings from default locations
    // Searches: ./hashes.json, ~/.config/acb-options-editor/hashes.json
    static bool loadDefaults();

    // Get count of loaded hashes
    static int hashCount();

private:
    static QMap<uint32_t, QString>& propertyNames();
    static void initPropertyNames();
    static bool s_initialized;
};

} // namespace acb
