#include "PropertyTreeModel.h"
#include "UndoCommands.h"
#include "model/Section.h"

namespace acb {

PropertyTreeModel::PropertyTreeModel(QObject* parent)
    : QAbstractItemModel(parent)
    , m_section(nullptr)
    , m_rootItem(nullptr)
    , m_undoStack(new QUndoStack(this))
{
    connect(m_undoStack, &QUndoStack::canUndoChanged, this, &PropertyTreeModel::undoStateChanged);
    connect(m_undoStack, &QUndoStack::canRedoChanged, this, &PropertyTreeModel::undoStateChanged);
}

PropertyTreeModel::~PropertyTreeModel()
{
    delete m_rootItem;
}

void PropertyTreeModel::setSection(Section* section)
{
    beginResetModel();

    delete m_rootItem;
    m_rootItem = nullptr;
    m_section = section;
    m_undoStack->clear();

    if (m_section) {
        buildTree();
    }

    endResetModel();
    emit sectionChanged();
}

void PropertyTreeModel::buildTree()
{
    if (!m_section || !m_section->rootProperty()) {
        return;
    }

    m_rootItem = new PropertyTreeItem(m_section->rootProperty());
    buildTreeRecursive(m_rootItem, m_section->rootProperty());
}

void PropertyTreeModel::buildTreeRecursive(PropertyTreeItem* parentItem, Property* property)
{
    for (int i = 0; i < property->childCount(); ++i) {
        Property* childProp = property->child(i);
        PropertyTreeItem* childItem = new PropertyTreeItem(childProp, parentItem);
        parentItem->appendChild(childItem);
        buildTreeRecursive(childItem, childProp);
    }
}

QModelIndex PropertyTreeModel::index(int row, int column, const QModelIndex& parent) const
{
    if (!hasIndex(row, column, parent)) {
        return QModelIndex();
    }

    PropertyTreeItem* parentItem;
    if (!parent.isValid()) {
        parentItem = m_rootItem;
    } else {
        parentItem = itemFromIndex(parent);
    }

    if (!parentItem) {
        return QModelIndex();
    }

    PropertyTreeItem* childItem = parentItem->child(row);
    if (childItem) {
        return createIndex(row, column, childItem);
    }
    return QModelIndex();
}

QModelIndex PropertyTreeModel::parent(const QModelIndex& index) const
{
    if (!index.isValid()) {
        return QModelIndex();
    }

    PropertyTreeItem* childItem = itemFromIndex(index);
    if (!childItem) {
        return QModelIndex();
    }

    PropertyTreeItem* parentItem = childItem->parent();
    if (!parentItem || parentItem == m_rootItem) {
        return QModelIndex();
    }

    return createIndex(parentItem->row(), 0, parentItem);
}

int PropertyTreeModel::rowCount(const QModelIndex& parent) const
{
    if (parent.column() > 0) {
        return 0;
    }

    PropertyTreeItem* parentItem;
    if (!parent.isValid()) {
        parentItem = m_rootItem;
    } else {
        parentItem = itemFromIndex(parent);
    }

    return parentItem ? parentItem->childCount() : 0;
}

int PropertyTreeModel::columnCount(const QModelIndex& parent) const
{
    Q_UNUSED(parent)
    return PropertyTreeItem::columnCount();
}

QVariant PropertyTreeModel::data(const QModelIndex& index, int role) const
{
    if (!index.isValid()) {
        return QVariant();
    }

    PropertyTreeItem* item = itemFromIndex(index);
    if (!item || !item->property()) {
        return QVariant();
    }

    Property* prop = item->property();

    switch (role) {
        case Qt::DisplayRole:
            return item->data(index.column());

        case NameRole:
            return prop->displayName();

        case HashRole:
            return QString("0x%1").arg(prop->hash(), 8, 16, QChar('0')).toUpper();

        case TypeRole:
            return prop->typeName();

        case TypeInfoRole: {
            // typeInfo is 8 bytes: hash_id (4 bytes) + type_id (4 bytes)
            QByteArray typeInfo = prop->typeInfo();
            return QString(typeInfo.toHex(' ').toUpper());
        }

        case ValueRole:
            return prop->value().toDisplayString();

        case EditableRole:
            return item->isEditable();

        case RawBytesRole:
            return prop->value().asRawBytes().toHex(' ').toUpper();

        default:
            return QVariant();
    }
}

bool PropertyTreeModel::setData(const QModelIndex& index, const QVariant& value, int role)
{
    if (!index.isValid() || role != Qt::EditRole) {
        return false;
    }

    PropertyTreeItem* item = itemFromIndex(index);
    if (!item || !item->isEditable()) {
        return false;
    }

    // Use undo command
    QVariant oldValue = item->property()->value().toVariant();
    m_undoStack->push(new PropertyEditCommand(this, index, oldValue, value));

    return true;
}

Qt::ItemFlags PropertyTreeModel::flags(const QModelIndex& index) const
{
    if (!index.isValid()) {
        return Qt::NoItemFlags;
    }

    Qt::ItemFlags flags = Qt::ItemIsEnabled | Qt::ItemIsSelectable;

    // Only value column (2) is editable
    if (index.column() == 2) {
        PropertyTreeItem* item = itemFromIndex(index);
        if (item && item->isEditable()) {
            flags |= Qt::ItemIsEditable;
        }
    }

    return flags;
}

QVariant PropertyTreeModel::headerData(int section, Qt::Orientation orientation, int role) const
{
    if (orientation == Qt::Horizontal && role == Qt::DisplayRole) {
        switch (section) {
            case 0: return "Name";
            case 1: return "Type";
            case 2: return "Value";
        }
    }
    return QVariant();
}

QHash<int, QByteArray> PropertyTreeModel::roleNames() const
{
    QHash<int, QByteArray> roles;
    roles[Qt::DisplayRole] = "display";
    roles[NameRole] = "name";
    roles[HashRole] = "hash";
    roles[TypeRole] = "type";
    roles[TypeInfoRole] = "typeInfo";
    roles[ValueRole] = "value";
    roles[EditableRole] = "editable";
    roles[RawBytesRole] = "rawBytes";
    return roles;
}

void PropertyTreeModel::undo()
{
    m_undoStack->undo();
}

void PropertyTreeModel::redo()
{
    m_undoStack->redo();
}

bool PropertyTreeModel::canUndo() const
{
    return m_undoStack->canUndo();
}

bool PropertyTreeModel::canRedo() const
{
    return m_undoStack->canRedo();
}

PropertyTreeItem* PropertyTreeModel::itemFromIndex(const QModelIndex& index) const
{
    if (index.isValid()) {
        return static_cast<PropertyTreeItem*>(index.internalPointer());
    }
    return m_rootItem;
}

} // namespace acb
