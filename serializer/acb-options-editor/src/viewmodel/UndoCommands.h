#pragma once

#include <QUndoCommand>
#include <QModelIndex>
#include <QVariant>

namespace acb {

class PropertyTreeModel;

// Undo command for property value edits
class PropertyEditCommand : public QUndoCommand {
public:
    PropertyEditCommand(PropertyTreeModel* model,
                        const QModelIndex& index,
                        const QVariant& oldValue,
                        const QVariant& newValue,
                        QUndoCommand* parent = nullptr);

    void undo() override;
    void redo() override;
    int id() const override { return 1; }
    bool mergeWith(const QUndoCommand* other) override;

private:
    PropertyTreeModel* m_model;
    QPersistentModelIndex m_index;
    QVariant m_oldValue;
    QVariant m_newValue;
};

} // namespace acb
