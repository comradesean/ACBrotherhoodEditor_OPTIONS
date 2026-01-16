#pragma once

#include <QString>
#include <QJsonObject>
#include <QJsonArray>

namespace acb {

class OptionsFile;
class Section;
class Property;

class JsonExporter {
public:
    // Export entire file to JSON
    static QJsonObject exportFile(const OptionsFile* file);

    // Export single section to JSON
    static QJsonObject exportSection(const Section* section);

    // Export property tree to JSON
    static QJsonObject exportProperty(const Property* property);

    // Save to file
    static bool saveToFile(const QJsonObject& json, const QString& path);
};

} // namespace acb
