#pragma once

#include <QAbstractItemModel>
#include <QUndoStack>
#include "PropertyTreeItem.h"

namespace acb {

class Section;

class PropertyTreeModel : public QAbstractItemModel {
    Q_OBJECT
    Q_PROPERTY(bool canUndo READ canUndo NOTIFY undoStateChanged)
    Q_PROPERTY(bool canRedo READ canRedo NOTIFY undoStateChanged)

public:
    enum Roles {
        NameRole = Qt::UserRole + 1,
        HashRole,
        TypeRole,
        TypeInfoRole,
        ValueRole,
        EditableRole,
        RawBytesRole
    };
    Q_ENUM(Roles)

    explicit PropertyTreeModel(QObject* parent = nullptr);
    ~PropertyTreeModel() override;

    // Set the section to display
    void setSection(Section* section);
    Section* section() const { return m_section; }

    // QAbstractItemModel interface
    QModelIndex index(int row, int column, const QModelIndex& parent = QModelIndex()) const override;
    QModelIndex parent(const QModelIndex& index) const override;
    int rowCount(const QModelIndex& parent = QModelIndex()) const override;
    int columnCount(const QModelIndex& parent = QModelIndex()) const override;
    QVariant data(const QModelIndex& index, int role = Qt::DisplayRole) const override;
    bool setData(const QModelIndex& index, const QVariant& value, int role = Qt::EditRole) override;
    Qt::ItemFlags flags(const QModelIndex& index) const override;
    QVariant headerData(int section, Qt::Orientation orientation, int role = Qt::DisplayRole) const override;
    QHash<int, QByteArray> roleNames() const override;

    // Undo/redo
    Q_INVOKABLE void undo();
    Q_INVOKABLE void redo();
    bool canUndo() const;
    bool canRedo() const;
    QUndoStack* undoStack() const { return m_undoStack; }

signals:
    void undoStateChanged();
    void sectionChanged();

private:
    void buildTree();
    void buildTreeRecursive(PropertyTreeItem* parentItem, Property* property);
    PropertyTreeItem* itemFromIndex(const QModelIndex& index) const;

    Section* m_section;
    PropertyTreeItem* m_rootItem;
    QUndoStack* m_undoStack;
};

} // namespace acb
