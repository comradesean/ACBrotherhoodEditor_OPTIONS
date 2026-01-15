import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import AcbOptionsEditor 1.0
import "components"

ApplicationWindow {
    id: root
    visible: true
    width: 1200
    height: 800
    title: optionsFile.filePath ? "ACB Options Editor - " + optionsFile.filePath : "ACB Options Editor"

    OptionsFileModel {
        id: optionsFile

        onError: function(message) {
            errorDialog.text = message
            errorDialog.open()
        }
    }

    menuBar: MenuBar {
        Menu {
            title: qsTr("&File")

            Action {
                text: qsTr("&Open...")
                shortcut: StandardKey.Open
                onTriggered: openDialog.open()
            }

            Action {
                text: qsTr("&Save")
                shortcut: StandardKey.Save
                enabled: optionsFile.isValid
                onTriggered: optionsFile.save()
            }

            Action {
                text: qsTr("Save &As...")
                shortcut: StandardKey.SaveAs
                enabled: optionsFile.isValid
                onTriggered: saveDialog.open()
            }

            MenuSeparator {}

            Action {
                text: qsTr("&Export JSON...")
                enabled: optionsFile.isValid
                onTriggered: exportDialog.open()
            }

            MenuSeparator {}

            Action {
                text: qsTr("E&xit")
                shortcut: StandardKey.Quit
                onTriggered: Qt.quit()
            }
        }

        Menu {
            title: qsTr("&Edit")

            Action {
                text: qsTr("&Undo")
                shortcut: StandardKey.Undo
                enabled: optionsFile.properties.canUndo
                onTriggered: optionsFile.properties.undo()
            }

            Action {
                text: qsTr("&Redo")
                shortcut: StandardKey.Redo
                enabled: optionsFile.properties.canRedo
                onTriggered: optionsFile.properties.redo()
            }
        }

        Menu {
            title: qsTr("&Help")

            Action {
                text: qsTr("&About")
                onTriggered: aboutDialog.open()
            }
        }
    }

    header: ToolBar {
        RowLayout {
            anchors.fill: parent
            anchors.margins: 4

            ToolButton {
                icon.name: "document-open"
                text: qsTr("Open")
                onClicked: openDialog.open()
            }

            ToolButton {
                icon.name: "document-save"
                text: qsTr("Save")
                enabled: optionsFile.isValid
                onClicked: optionsFile.save()
            }

            ToolButton {
                icon.name: "document-save-as"
                text: qsTr("Save As")
                enabled: optionsFile.isValid
                onClicked: saveDialog.open()
            }

            ToolSeparator {}

            ToolButton {
                icon.name: "edit-undo"
                text: qsTr("Undo")
                enabled: optionsFile.properties.canUndo
                onClicked: optionsFile.properties.undo()
            }

            ToolButton {
                icon.name: "edit-redo"
                text: qsTr("Redo")
                enabled: optionsFile.properties.canRedo
                onClicked: optionsFile.properties.redo()
            }

            Item { Layout.fillWidth: true }

            Label {
                text: optionsFile.isValid ? "Platform: " + optionsFile.platform : ""
            }
        }
    }

    SplitView {
        anchors.fill: parent
        orientation: Qt.Horizontal

        // Left panel: Section list
        Pane {
            SplitView.preferredWidth: 200
            SplitView.minimumWidth: 150

            ColumnLayout {
                anchors.fill: parent

                Label {
                    text: qsTr("Sections")
                    font.bold: true
                }

                ListView {
                    id: sectionList
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    model: optionsFile.sections
                    currentIndex: optionsFile.currentSectionIndex
                    clip: true

                    delegate: ItemDelegate {
                        width: sectionList.width
                        highlighted: ListView.isCurrentItem

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 4

                            Rectangle {
                                width: 8
                                height: 8
                                radius: 4
                                color: model.isKnown ? "#4CAF50" : "#FF9800"
                            }

                            Label {
                                Layout.fillWidth: true
                                text: model.name
                                elide: Text.ElideRight
                            }

                            Label {
                                text: model.isDirty ? "*" : ""
                                color: "#F44336"
                            }
                        }

                        onClicked: optionsFile.currentSectionIndex = index
                    }

                    ScrollBar.vertical: ScrollBar {}
                }
            }
        }

        // Right panel: Property tree and hex view
        SplitView {
            SplitView.fillWidth: true
            orientation: Qt.Vertical

            // Property tree view
            Pane {
                SplitView.preferredHeight: parent.height * 0.6
                SplitView.minimumHeight: 200

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 4

                    Label {
                        text: qsTr("Properties (Parsed Data)")
                        font.bold: true
                    }

                    PropertyTreeView {
                        id: propertyTree
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        model: optionsFile.properties
                    }
                }
            }

            // Hex view
            Pane {
                SplitView.fillHeight: true
                SplitView.minimumHeight: 150

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 4

                    Label {
                        text: qsTr("Hex View (Raw Decompressed Bytes)")
                        font.bold: true
                    }

                    HexEditor {
                        id: hexEditor
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        data: optionsFile.currentSectionHex()
                        readOnly: {
                            if (optionsFile.currentSectionIndex < 0) return false
                            var section = optionsFile.sections.sectionAt(optionsFile.currentSectionIndex)
                            return section && section.isKnown === true
                        }
                    }
                }
            }
        }
    }

    footer: StatusBar {
        id: statusBar
        filePath: optionsFile.filePath
        platform: optionsFile.platform
        sectionCount: optionsFile.sectionCount
        isDirty: optionsFile.isDirty
    }

    // Helper function to convert file URL to local path
    function urlToPath(url) {
        var path = url.toString()
        // Remove file:// prefix
        if (path.startsWith("file:///")) {
            // On Windows, file:///C:/... -> C:/...
            // On Linux, file:///home/... -> /home/...
            if (path.charAt(9) === ':') {
                // Windows path
                path = path.substring(8)
            } else {
                // Unix path
                path = path.substring(7)
            }
        }
        // Decode URI components (spaces, special chars)
        return decodeURIComponent(path)
    }

    // Dialogs
    FileDialog {
        id: openDialog
        title: qsTr("Open OPTIONS File")
        nameFilters: ["OPTIONS files (OPTIONS* *.bin)", "All files (*)"]
        onAccepted: optionsFile.load(urlToPath(selectedFile))
    }

    FileDialog {
        id: saveDialog
        title: qsTr("Save OPTIONS File")
        fileMode: FileDialog.SaveFile
        acceptLabel: qsTr("Save")
        nameFilters: ["OPTIONS files (OPTIONS* *.bin)", "All files (*)"]
        onAccepted: optionsFile.save(urlToPath(selectedFile))
    }

    FileDialog {
        id: exportDialog
        title: qsTr("Export JSON")
        fileMode: FileDialog.SaveFile
        acceptLabel: qsTr("Export")
        nameFilters: ["JSON files (*.json)", "All files (*)"]
        onAccepted: optionsFile.exportJson(urlToPath(selectedFile))
    }

    Dialog {
        id: errorDialog
        title: qsTr("Error")
        modal: true
        anchors.centerIn: parent

        property alias text: errorLabel.text

        Label {
            id: errorLabel
        }

        standardButtons: Dialog.Ok
    }

    Dialog {
        id: aboutDialog
        title: qsTr("About ACB Options Editor")
        modal: true
        anchors.centerIn: parent

        ColumnLayout {
            Label {
                text: qsTr("ACB Options Editor")
                font.bold: true
                font.pointSize: 14
            }
            Label {
                text: qsTr("Version 1.0.0")
            }
            Label {
                text: qsTr("A tool for editing Assassin's Creed Brotherhood\nOPTIONS save files.")
            }
        }

        standardButtons: Dialog.Ok
    }
}
