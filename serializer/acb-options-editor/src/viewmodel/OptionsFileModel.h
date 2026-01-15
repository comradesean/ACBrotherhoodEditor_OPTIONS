#pragma once

#include <QObject>
#include <QString>
#include "model/OptionsFile.h"
#include "SectionListModel.h"
#include "PropertyTreeModel.h"

namespace acb {

class OptionsFileModel : public QObject {
    Q_OBJECT
    Q_PROPERTY(QString filePath READ filePath NOTIFY fileLoaded)
    Q_PROPERTY(QString platform READ platformString NOTIFY fileLoaded)
    Q_PROPERTY(int sectionCount READ sectionCount NOTIFY fileLoaded)
    Q_PROPERTY(bool isDirty READ isDirty NOTIFY dirtyChanged)
    Q_PROPERTY(bool isValid READ isValid NOTIFY fileLoaded)
    Q_PROPERTY(SectionListModel* sections READ sectionsModel CONSTANT)
    Q_PROPERTY(PropertyTreeModel* properties READ propertiesModel CONSTANT)
    Q_PROPERTY(int currentSectionIndex READ currentSectionIndex WRITE setCurrentSectionIndex NOTIFY currentSectionChanged)

public:
    explicit OptionsFileModel(QObject* parent = nullptr);
    ~OptionsFileModel() override;

    // File operations
    Q_INVOKABLE bool load(const QString& path);
    Q_INVOKABLE bool save(const QString& path = QString());
    Q_INVOKABLE bool exportJson(const QString& path);

    // Accessors
    QString filePath() const;
    QString platformString() const;
    int sectionCount() const;
    bool isDirty() const;
    bool isValid() const;

    // Models
    SectionListModel* sectionsModel() const { return m_sectionsModel; }
    PropertyTreeModel* propertiesModel() const { return m_propertiesModel; }

    // Current section
    int currentSectionIndex() const { return m_currentSectionIndex; }
    void setCurrentSectionIndex(int index);
    Q_INVOKABLE QByteArray currentSectionHex() const;

    // Underlying file
    OptionsFile* optionsFile() const { return m_file; }

signals:
    void fileLoaded();
    void dirtyChanged();
    void currentSectionChanged();
    void error(const QString& message);

private:
    OptionsFile* m_file;
    SectionListModel* m_sectionsModel;
    PropertyTreeModel* m_propertiesModel;
    int m_currentSectionIndex;
};

} // namespace acb
