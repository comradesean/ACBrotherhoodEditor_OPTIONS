#include "SectionListModel.h"
#include "model/Section.h"

namespace acb {

SectionListModel::SectionListModel(QObject* parent)
    : QAbstractListModel(parent)
    , m_file(nullptr)
{
}

SectionListModel::~SectionListModel()
{
}

void SectionListModel::setOptionsFile(OptionsFile* file)
{
    beginResetModel();
    m_file = file;
    endResetModel();
    emit countChanged();
}

int SectionListModel::rowCount(const QModelIndex& parent) const
{
    if (parent.isValid() || !m_file) {
        return 0;
    }
    return m_file->sectionCount();
}

QVariant SectionListModel::data(const QModelIndex& index, int role) const
{
    if (!index.isValid() || !m_file) {
        return QVariant();
    }

    int row = index.row();
    if (row < 0 || row >= m_file->sectionCount()) {
        return QVariant();
    }

    Section* section = m_file->section(row);
    if (!section) {
        return QVariant();
    }

    switch (role) {
        case Qt::DisplayRole:
        case NameRole:
            return section->sectionName();

        case NumberRole:
            return section->sectionNumber();

        case IsKnownRole:
            return section->isKnown();

        case IsDirtyRole:
            return section->isDirty();

        case RootHashRole:
            return QString("0x%1").arg(section->rootHash(), 8, 16, QChar('0')).toUpper();

        case CompressedSizeRole:
            return section->header().compressedSize();

        case UncompressedSizeRole:
            return section->header().uncompressedSize();

        default:
            return QVariant();
    }
}

QHash<int, QByteArray> SectionListModel::roleNames() const
{
    QHash<int, QByteArray> roles;
    roles[Qt::DisplayRole] = "display";
    roles[NameRole] = "name";
    roles[NumberRole] = "number";
    roles[IsKnownRole] = "isKnown";
    roles[IsDirtyRole] = "isDirty";
    roles[RootHashRole] = "rootHash";
    roles[CompressedSizeRole] = "compressedSize";
    roles[UncompressedSizeRole] = "uncompressedSize";
    return roles;
}

Section* SectionListModel::sectionAt(int index) const
{
    if (m_file && index >= 0 && index < m_file->sectionCount()) {
        return m_file->section(index);
    }
    return nullptr;
}

} // namespace acb
