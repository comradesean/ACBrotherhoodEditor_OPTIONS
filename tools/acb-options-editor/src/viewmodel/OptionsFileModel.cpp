#include "OptionsFileModel.h"
#include "util/JsonExporter.h"
#include "model/Section.h"

namespace acb {

OptionsFileModel::OptionsFileModel(QObject* parent)
    : QObject(parent)
    , m_file(new OptionsFile())
    , m_sectionsModel(new SectionListModel(this))
    , m_propertiesModel(new PropertyTreeModel(this))
    , m_currentSectionIndex(-1)
{
    // Connect property edits to dirty state change
    connect(m_propertiesModel, &PropertyTreeModel::undoStateChanged,
            this, &OptionsFileModel::dirtyChanged);
}

OptionsFileModel::~OptionsFileModel()
{
    delete m_file;
}

bool OptionsFileModel::load(const QString& path)
{
    if (!m_file->load(path)) {
        emit error(QString("Failed to load file: %1").arg(path));
        return false;
    }

    m_sectionsModel->setOptionsFile(m_file);
    m_currentSectionIndex = -1;

    // Select first section if available
    if (m_file->sectionCount() > 0) {
        setCurrentSectionIndex(0);
    }

    emit fileLoaded();
    emit dirtyChanged();
    return true;
}

bool OptionsFileModel::save(const QString& path)
{
    QString savePath = path.isEmpty() ? m_file->filePath() : path;
    if (savePath.isEmpty()) {
        emit error("No file path specified");
        return false;
    }

    if (!m_file->save(savePath)) {
        emit error(QString("Failed to save file: %1").arg(savePath));
        return false;
    }

    emit dirtyChanged();
    return true;
}

bool OptionsFileModel::exportJson(const QString& path)
{
    QJsonObject json = JsonExporter::exportFile(m_file);
    if (!JsonExporter::saveToFile(json, path)) {
        emit error(QString("Failed to export JSON: %1").arg(path));
        return false;
    }
    return true;
}

QString OptionsFileModel::filePath() const
{
    return m_file ? m_file->filePath() : QString();
}

QString OptionsFileModel::platformString() const
{
    if (!m_file) return "Unknown";
    switch (m_file->platform()) {
        case Platform::PC: return "PC";
        case Platform::PS3: return "PS3";
        default: return "Unknown";
    }
}

int OptionsFileModel::sectionCount() const
{
    return m_file ? m_file->sectionCount() : 0;
}

bool OptionsFileModel::isDirty() const
{
    return m_file && m_file->isDirty();
}

bool OptionsFileModel::isValid() const
{
    return m_file && m_file->isValid();
}

void OptionsFileModel::setCurrentSectionIndex(int index)
{
    if (index == m_currentSectionIndex) return;
    if (!m_file || index < -1 || index >= m_file->sectionCount()) return;

    m_currentSectionIndex = index;

    if (index >= 0) {
        Section* section = m_file->section(index);
        m_propertiesModel->setSection(section);
    } else {
        m_propertiesModel->setSection(nullptr);
    }

    emit currentSectionChanged();
}

QByteArray OptionsFileModel::currentSectionHex() const
{
    if (!m_file || m_currentSectionIndex < 0) {
        return QByteArray();
    }

    Section* section = m_file->section(m_currentSectionIndex);
    if (!section) {
        return QByteArray();
    }

    return section->rawDecompressed();
}

} // namespace acb
