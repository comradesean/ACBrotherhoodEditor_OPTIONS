#include "PropertyTreeItem.h"

namespace acb {

PropertyTreeItem::PropertyTreeItem(Property* property, PropertyTreeItem* parent)
    : m_property(property)
    , m_parent(parent)
{
}

PropertyTreeItem::~PropertyTreeItem()
{
    qDeleteAll(m_children);
}

PropertyTreeItem* PropertyTreeItem::child(int row) const
{
    if (row >= 0 && row < m_children.size()) {
        return m_children[row];
    }
    return nullptr;
}

int PropertyTreeItem::row() const
{
    if (m_parent) {
        return m_parent->m_children.indexOf(const_cast<PropertyTreeItem*>(this));
    }
    return 0;
}

void PropertyTreeItem::appendChild(PropertyTreeItem* child)
{
    if (child) {
        child->m_parent = this;
        m_children.append(child);
    }
}

void PropertyTreeItem::removeChild(PropertyTreeItem* child)
{
    if (child) {
        m_children.removeOne(child);
        child->m_parent = nullptr;
    }
}

void PropertyTreeItem::clearChildren()
{
    qDeleteAll(m_children);
    m_children.clear();
}

QVariant PropertyTreeItem::data(int column) const
{
    if (!m_property) return QVariant();

    switch (column) {
        case 0:  // Name/Hash
            return m_property->displayName();
        case 1:  // Type
            return m_property->typeName();
        case 2:  // Value
            return m_property->value().toDisplayString();
        default:
            return QVariant();
    }
}

bool PropertyTreeItem::setData(int column, const QVariant& value)
{
    if (!m_property || column != 2) {
        return false;  // Only value column is editable
    }

    if (!m_property->isEditable()) {
        return false;
    }

    m_property->value().fromVariant(value);
    return true;
}

bool PropertyTreeItem::isEditable() const
{
    return m_property && m_property->isEditable();
}

} // namespace acb
