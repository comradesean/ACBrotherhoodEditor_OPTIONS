#include "HashLookup.h"
#include "core/TypeCodes.h"
#include <QFile>
#include <QJsonDocument>
#include <QJsonObject>
#include <QStandardPaths>
#include <QCoreApplication>
#include <QDir>
#include <QDebug>

namespace acb {

bool HashLookup::s_initialized = false;

QMap<uint32_t, QString>& HashLookup::propertyNames()
{
    static QMap<uint32_t, QString> names;
    return names;
}

void HashLookup::initPropertyNames()
{
    if (s_initialized) return;
    s_initialized = true;

    auto& names = propertyNames();

    // Section root hashes
    names[SectionHash::SaveGame] = "SaveGame";
    names[SectionHash::PlayerOptionsSaveData] = "PlayerOptionsSaveData";
    names[SectionHash::AssassinSingleProfileData] = "AssassinSingleProfileData";
    names[SectionHash::AssassinMultiProfileData] = "AssassinMultiProfileData";

    // Common property hashes (from Python parsers)
    // Section 1
    names[0xBF4C2013] = "base_class";

    // Section 2 - Player Options
    names[0x11FACE11] = "T_hash";
    names[0x305AE1A8] = "PlayerOptionsSaveData";

    // Section 3 - Single Profile
    names[0xC9876D66] = "AssassinSingleProfileData";
    names[0x3B546966] = "bool_field";

    // Section 4 - Multi Profile
    names[0xB4B55039] = "AssassinMultiProfileData";

    // Add more known hashes as they are discovered
}

QString HashLookup::lookupPropertyName(uint32_t hash)
{
    initPropertyNames();
    return propertyNames().value(hash, QString());
}

QString HashLookup::lookupSectionName(uint32_t hash)
{
    switch (hash) {
        case SectionHash::SaveGame:
            return "SaveGame";
        case SectionHash::PlayerOptionsSaveData:
            return "PlayerOptionsSaveData";
        case SectionHash::AssassinSingleProfileData:
            return "AssassinSingleProfileData";
        case SectionHash::AssassinMultiProfileData:
            return "AssassinMultiProfileData";
        default:
            return QString();
    }
}

void HashLookup::registerHash(uint32_t hash, const QString& name)
{
    initPropertyNames();
    propertyNames()[hash] = name;
}

bool HashLookup::loadFromJson(const QString& path)
{
    initPropertyNames();

    QFile file(path);
    if (!file.open(QIODevice::ReadOnly)) {
        qWarning() << "HashLookup: Could not open" << path;
        return false;
    }

    QByteArray data = file.readAll();
    file.close();

    QJsonParseError parseError;
    QJsonDocument doc = QJsonDocument::fromJson(data, &parseError);
    if (parseError.error != QJsonParseError::NoError) {
        qWarning() << "HashLookup: JSON parse error:" << parseError.errorString();
        return false;
    }

    if (!doc.isObject()) {
        qWarning() << "HashLookup: JSON root must be an object";
        return false;
    }

    QJsonObject root = doc.object();
    QJsonObject hashes;

    // Support both { "hashes": {...} } and flat { "0x...": "name", ... }
    if (root.contains("hashes") && root["hashes"].isObject()) {
        hashes = root["hashes"].toObject();
    } else {
        hashes = root;
    }

    int count = 0;
    auto& names = propertyNames();

    for (auto it = hashes.begin(); it != hashes.end(); ++it) {
        QString key = it.key();
        QString name = it.value().toString();

        if (name.isEmpty()) continue;

        // Parse hash from key (supports "0x..." hex or decimal)
        bool ok = false;
        uint32_t hash = 0;

        if (key.startsWith("0x") || key.startsWith("0X")) {
            hash = key.mid(2).toUInt(&ok, 16);
        } else {
            hash = key.toUInt(&ok, 10);
        }

        if (ok) {
            names[hash] = name;
            count++;
        }
    }

    qDebug() << "HashLookup: Loaded" << count << "hashes from" << path;
    return count > 0;
}

bool HashLookup::loadDefaults()
{
    // Try several locations
    QStringList searchPaths = {
        QDir::currentPath() + "/hashes.json",
        QCoreApplication::applicationDirPath() + "/hashes.json",
        QStandardPaths::writableLocation(QStandardPaths::ConfigLocation) + "/acb-options-editor/hashes.json"
    };

    for (const QString& path : searchPaths) {
        if (QFile::exists(path)) {
            if (loadFromJson(path)) {
                return true;
            }
        }
    }

    return false;
}

int HashLookup::hashCount()
{
    initPropertyNames();
    return propertyNames().size();
}

} // namespace acb
