import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Type-specific property editor
// Used inline in PropertyTreeView delegate
Loader {
    id: root

    property string propertyType: ""
    property var currentValue: null
    property var modelIndex: null
    property var treeModel: null

    sourceComponent: {
        switch (propertyType) {
            case "bool":
                return boolEditor
            case "int8":
            case "int16":
            case "int32":
            case "uint8":
            case "uint16":
            case "uint32":
                return intEditor
            case "float32":
            case "float64":
                return floatEditor
            case "string":
                return stringEditor
            default:
                return hexEditor
        }
    }

    Component {
        id: boolEditor

        CheckBox {
            checked: currentValue === "true"
            onToggled: {
                if (treeModel && modelIndex) {
                    treeModel.setData(modelIndex, checked, Qt.EditRole)
                }
            }
        }
    }

    Component {
        id: intEditor

        SpinBox {
            from: -2147483648
            to: 2147483647
            value: parseInt(currentValue) || 0
            editable: true

            onValueModified: {
                if (treeModel && modelIndex) {
                    treeModel.setData(modelIndex, value, Qt.EditRole)
                }
            }
        }
    }

    Component {
        id: floatEditor

        TextField {
            text: currentValue || "0.0"
            validator: DoubleValidator {}

            onEditingFinished: {
                if (treeModel && modelIndex) {
                    treeModel.setData(modelIndex, parseFloat(text), Qt.EditRole)
                }
            }
        }
    }

    Component {
        id: stringEditor

        TextField {
            text: currentValue || ""

            onEditingFinished: {
                if (treeModel && modelIndex) {
                    treeModel.setData(modelIndex, text, Qt.EditRole)
                }
            }
        }
    }

    Component {
        id: hexEditor

        TextField {
            text: currentValue || ""
            font.family: "monospace"
            readOnly: true
            color: "#666"

            background: Rectangle {
                color: "#F5F5F5"
                border.color: "#ddd"
            }
        }
    }
}
