#pragma once

#include <QAbstractListModel>
#include "model/OptionsFile.h"

namespace acb {

class SectionListModel : public QAbstractListModel {
    Q_OBJECT
    Q_PROPERTY(int count READ rowCount NOTIFY countChanged)

public:
    enum Roles {
        NameRole = Qt::UserRole + 1,
        NumberRole,
        IsKnownRole,
        IsDirtyRole,
        RootHashRole,
        CompressedSizeRole,
        UncompressedSizeRole
    };
    Q_ENUM(Roles)

    explicit SectionListModel(QObject* parent = nullptr);
    ~SectionListModel() override;

    void setOptionsFile(OptionsFile* file);
    OptionsFile* optionsFile() const { return m_file; }

    // QAbstractListModel interface
    int rowCount(const QModelIndex& parent = QModelIndex()) const override;
    QVariant data(const QModelIndex& index, int role = Qt::DisplayRole) const override;
    QHash<int, QByteArray> roleNames() const override;

    // Get section by index
    Q_INVOKABLE Section* sectionAt(int index) const;

signals:
    void countChanged();

private:
    OptionsFile* m_file;
};

} // namespace acb
