#pragma once

#include <QList>
#include <QString>
#include <QByteArray>
#include "Section.h"
#include "core/TypeCodes.h"

namespace acb {

class OptionsFile {
public:
    OptionsFile();
    ~OptionsFile();

    // Load file from disk
    bool load(const QString& path);

    // Save file to disk
    bool save(const QString& path);

    // Get serialized data (for saving)
    QByteArray serialize() const;

    // Platform
    Platform platform() const { return m_platform; }
    void setPlatform(Platform platform) { m_platform = platform; }

    // Sections
    int sectionCount() const { return m_sections.size(); }
    Section* section(int index) const;
    const QList<Section*>& sections() const { return m_sections; }
    void addSection(Section* section);
    void removeSection(Section* section);
    void clearSections();

    // State
    bool isValid() const { return m_valid; }
    bool isDirty() const;
    QString filePath() const { return m_filePath; }

    // Platform detection
    static Platform detectPlatform(const QByteArray& data);

private:
    bool parseFile(const QByteArray& data);
    QByteArray buildFile() const;

    QList<Section*> m_sections;
    Platform m_platform;
    QString m_filePath;
    bool m_valid;

    // For round-trip: store original footer/prefix
    QByteArray m_ps3Prefix;
    QByteArray m_footer;
};

} // namespace acb
