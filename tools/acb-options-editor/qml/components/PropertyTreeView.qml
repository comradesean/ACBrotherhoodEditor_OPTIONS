import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import AcbOptionsEditor 1.0

Item {
    id: root

    property alias model: treeView.model

    TreeView {
        id: treeView
        anchors.fill: parent
        clip: true

        selectionModel: ItemSelectionModel {
            model: treeView.model
        }

        delegate: TreeViewDelegate {
            id: delegate
            implicitWidth: treeView.width > 0 ? treeView.width : 800
            implicitHeight: 28
            indentation: 20
            topPadding: 0
            bottomPadding: 0
            verticalPadding: 0

            // Disable built-in indicator to avoid duplicate arrows
            indicator: Item {
                width: 20
                height: 20

                Text {
                    anchors.centerIn: parent
                    text: delegate.hasChildren ? (delegate.expanded ? "▼" : "▶") : ""
                    font.pointSize: 8
                    color: delegate.hasChildren ? "#333" : "transparent"
                }
            }

            contentItem: RowLayout {
                spacing: 12

                // Name column - expands to fill
                Label {
                    id: nameLabel
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    verticalAlignment: Text.AlignVCenter
                    text: model.name || ""
                    elide: Text.ElideRight
                    font.family: "monospace"

                    MouseArea {
                        id: nameMouseArea
                        anchors.fill: parent
                        hoverEnabled: true
                        acceptedButtons: Qt.NoButton

                        ToolTip {
                            visible: nameMouseArea.containsMouse && model.hash !== model.name
                            text: model.hash || ""
                            delay: 500
                            x: nameMouseArea.mouseX + 10
                            y: nameMouseArea.mouseY + 10
                        }
                    }
                }

                // Type column - fixed width
                Label {
                    id: typeLabel
                    Layout.preferredWidth: 80
                    Layout.fillHeight: true
                    verticalAlignment: Text.AlignVCenter
                    text: model.type || ""
                    color: "#666"
                    font.family: "monospace"

                    MouseArea {
                        id: typeMouseArea
                        anchors.fill: parent
                        hoverEnabled: true
                        acceptedButtons: Qt.NoButton

                        ToolTip {
                            visible: typeMouseArea.containsMouse && model.typeInfo
                            text: model.typeInfo || ""
                            delay: 500
                            x: typeMouseArea.mouseX + 10
                            y: typeMouseArea.mouseY + 10
                        }
                    }
                }

                // Value column - fixed width
                Loader {
                    id: valueLoader
                    Layout.preferredWidth: 200
                    Layout.fillHeight: true
                    sourceComponent: {
                        if (!model.editable) return readOnlyValueComponent
                        if (model.type === "bool") return boolValueComponent
                        return editableValueComponent
                    }

                    property var valueText: model.value || ""
                    property var valueType: model.type || ""
                    property var modelIndex: (typeof row !== "undefined" && row >= 0) ? treeView.modelIndex(row, 0) : null
                }
            }
        }

        ScrollBar.vertical: ScrollBar {}
        ScrollBar.horizontal: ScrollBar {}
    }

    Component {
        id: readOnlyValueComponent

        Label {
            text: valueText
            elide: Text.ElideRight
            font.family: "monospace"
            anchors.fill: parent
            verticalAlignment: Text.AlignVCenter
        }
    }

    Component {
        id: editableValueComponent

        TextField {
            text: valueText
            font.family: "monospace"
            selectByMouse: true
            anchors.fill: parent
            verticalAlignment: Text.AlignVCenter

            background: Rectangle {
                color: parent.activeFocus ? "#E3F2FD" : "transparent"
                border.color: parent.activeFocus ? "#2196F3" : "#ddd"
                radius: 2
            }

            onEditingFinished: {
                if (text !== valueText) {
                    treeView.model.setData(modelIndex, text, Qt.EditRole)
                }
            }
        }
    }

    Component {
        id: boolValueComponent

        ComboBox {
            model: ["false", "true"]
            currentIndex: valueText === "true" ? 1 : 0
            font.family: "monospace"
            anchors.fill: parent

            onActivated: {
                var newValue = currentIndex === 1 ? "true" : "false"
                if (newValue !== valueText) {
                    treeView.model.setData(modelIndex, newValue, Qt.EditRole)
                }
            }
        }
    }
}
