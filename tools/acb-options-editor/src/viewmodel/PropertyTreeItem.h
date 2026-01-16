#pragma once

#include <QList>
#include <QVariant>
#include "model/Property.h"

namespace acb {

// Tree node wrapper for PropertyTreeModel
// Wraps a Property for use in QAbstractItemModel
class PropertyTreeItem {
public:
    explicit PropertyTreeItem(Property* property, PropertyTreeItem* parent = nullptr);
    ~PropertyTreeItem();

    // Tree navigation
    PropertyTreeItem* parent() const { return m_parent; }
    PropertyTreeItem* child(int row) const;
    int childCount() const { return m_children.size(); }
    int row() const;

    // Add/remove children
    void appendChild(PropertyTreeItem* child);
    void removeChild(PropertyTreeItem* child);
    void clearChildren();

    // Data access
    Property* property() const { return m_property; }
    QVariant data(int column) const;
    bool setData(int column, const QVariant& value);

    // Column info - use 1 for QML TreeView (delegate handles all fields)
    static int columnCount() { return 1; }

    // State
    bool isEditable() const;

private:
    Property* m_property;
    PropertyTreeItem* m_parent;
    QList<PropertyTreeItem*> m_children;
};

} // namespace acb
