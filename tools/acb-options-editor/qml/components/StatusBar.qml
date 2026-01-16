import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ToolBar {
    id: root

    property string filePath: ""
    property string platform: ""
    property int sectionCount: 0
    property bool isDirty: false

    RowLayout {
        anchors.fill: parent
        anchors.margins: 4

        Label {
            text: filePath || qsTr("No file loaded")
            elide: Text.ElideMiddle
            Layout.fillWidth: true
        }

        Rectangle {
            width: 1
            height: parent.height - 8
            color: "#ccc"
            visible: platform !== ""
        }

        Label {
            text: platform ? qsTr("Platform: %1").arg(platform) : ""
            visible: platform !== ""
        }

        Rectangle {
            width: 1
            height: parent.height - 8
            color: "#ccc"
            visible: sectionCount > 0
        }

        Label {
            text: sectionCount > 0 ? qsTr("Sections: %1").arg(sectionCount) : ""
            visible: sectionCount > 0
        }

        Rectangle {
            width: 1
            height: parent.height - 8
            color: "#ccc"
            visible: isDirty
        }

        Label {
            text: qsTr("Modified")
            color: "#F44336"
            font.bold: true
            visible: isDirty
        }
    }
}
