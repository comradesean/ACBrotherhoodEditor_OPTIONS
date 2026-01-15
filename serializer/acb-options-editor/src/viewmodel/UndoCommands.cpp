#include "UndoCommands.h"
#include "PropertyTreeModel.h"
#include "PropertyTreeItem.h"
#include "model/Section.h"

namespace acb {

PropertyEditCommand::PropertyEditCommand(PropertyTreeModel* model,
                                         const QModelIndex& index,
                                         const QVariant& oldValue,
                                         const QVariant& newValue,
                                         QUndoCommand* parent)
    : QUndoCommand(parent)
    , m_model(model)
    , m_index(index)
    , m_oldValue(oldValue)
    , m_newValue(newValue)
{
    setText(QString("Edit property"));
}

void PropertyEditCommand::undo()
{
    if (!m_index.isValid() || !m_model) return;

    PropertyTreeItem* item = static_cast<PropertyTreeItem*>(m_index.internalPointer());
    if (item) {
        item->setData(m_index.column(), m_oldValue);
        emit m_model->dataChanged(m_index, m_index, {Qt::DisplayRole, PropertyTreeModel::ValueRole});

        // Mark section as dirty
        if (m_model->section()) {
            m_model->section()->setDirty(true);
        }
    }
}

void PropertyEditCommand::redo()
{
    if (!m_index.isValid() || !m_model) return;

    PropertyTreeItem* item = static_cast<PropertyTreeItem*>(m_index.internalPointer());
    if (item) {
        item->setData(m_index.column(), m_newValue);
        emit m_model->dataChanged(m_index, m_index, {Qt::DisplayRole, PropertyTreeModel::ValueRole});

        // Mark section as dirty
        if (m_model->section()) {
            m_model->section()->setDirty(true);
        }
    }
}

bool PropertyEditCommand::mergeWith(const QUndoCommand* other)
{
    if (other->id() != id()) return false;

    const PropertyEditCommand* cmd = static_cast<const PropertyEditCommand*>(other);
    if (cmd->m_index != m_index) return false;

    m_newValue = cmd->m_newValue;
    return true;
}

} // namespace acb
