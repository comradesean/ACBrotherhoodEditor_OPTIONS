#include "JsonExporter.h"
#include "model/OptionsFile.h"
#include "model/Section.h"
#include "model/Property.h"
#include "core/HashLookup.h"
#include <QJsonDocument>
#include <QFile>

namespace acb {

QJsonObject JsonExporter::exportFile(const OptionsFile* file)
{
    QJsonObject root;

    if (!file) return root;

    root["platform"] = file->platform() == Platform::PC ? "PC" : "PS3";
    root["filePath"] = file->filePath();

    QJsonArray sectionsArray;
    for (const Section* section : file->sections()) {
        sectionsArray.append(exportSection(section));
    }
    root["sections"] = sectionsArray;

    return root;
}

QJsonObject JsonExporter::exportSection(const Section* section)
{
    QJsonObject obj;

    if (!section) return obj;

    obj["name"] = section->sectionName();
    obj["number"] = section->sectionNumber();
    obj["rootHash"] = QString("0x%1").arg(section->rootHash(), 8, 16, QChar('0')).toUpper();
    obj["isKnown"] = section->isKnown();
    obj["compressedSize"] = section->header().compressedSize();
    obj["uncompressedSize"] = section->header().uncompressedSize();

    if (section->rootProperty()) {
        obj["properties"] = exportProperty(section->rootProperty());
    }

    // For unknown sections or debugging, include hex dump
    if (!section->isKnown() || section->rawDecompressed().size() < 1000) {
        obj["hexDump"] = QString(section->rawDecompressed().toHex(' ').toUpper());
    }

    return obj;
}

QJsonObject JsonExporter::exportProperty(const Property* property)
{
    QJsonObject obj;

    if (!property) return obj;

    QString name = property->displayName();
    obj["name"] = name;
    obj["hash"] = QString("0x%1").arg(property->hash(), 8, 16, QChar('0')).toUpper();
    obj["type"] = property->typeName();
    obj["flags"] = QString("0x%1").arg(property->flags(), 2, 16, QChar('0')).toUpper();
    obj["typeInfo"] = QString(property->typeInfo().toHex(' ').toUpper());

    // Value
    const PropertyValue& val = property->value();
    obj["displayValue"] = val.toDisplayString();

    // Children
    if (property->childCount() > 0) {
        QJsonArray childrenArray;
        for (int i = 0; i < property->childCount(); ++i) {
            childrenArray.append(exportProperty(property->child(i)));
        }
        obj["children"] = childrenArray;
    }

    return obj;
}

bool JsonExporter::saveToFile(const QJsonObject& json, const QString& path)
{
    QFile file(path);
    if (!file.open(QIODevice::WriteOnly)) {
        return false;
    }

    QJsonDocument doc(json);
    file.write(doc.toJson(QJsonDocument::Indented));
    file.close();

    return true;
}

} // namespace acb
