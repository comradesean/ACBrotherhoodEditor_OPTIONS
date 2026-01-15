import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root

    property alias data: hexView.hexData
    property bool readOnly: false

    ColumnLayout {
        anchors.fill: parent
        spacing: 4

        // Toolbar
        RowLayout {
            Layout.fillWidth: true

            Label {
                text: qsTr("Hex View")
                font.bold: true
            }

            Item { Layout.fillWidth: true }

            Label {
                text: hexView.hexData ? qsTr("%1 bytes").arg(hexView.hexData.length) : ""
                color: "#666"
            }

            ToolButton {
                text: qsTr("Copy")
                enabled: hexView.hexData && hexView.hexData.length > 0
                onClicked: {
                    hexView.selectAll()
                    hexView.copy()
                }
            }
        }

        // Hex display
        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            TextArea {
                id: hexView
                readOnly: root.readOnly
                font.family: "monospace"
                font.pointSize: 10
                wrapMode: TextArea.Wrap
                selectByMouse: true

                property var hexData: null

                text: formatHex(hexData)

                background: Rectangle {
                    color: root.readOnly ? "#F5F5F5" : "white"
                    border.color: "#ddd"
                }

                function formatHex(data) {
                    if (!data || data.length === 0) {
                        return ""
                    }

                    var result = ""
                    var bytesPerLine = 16

                    for (var i = 0; i < data.length; i += bytesPerLine) {
                        // Address
                        var addr = i.toString(16).toUpperCase().padStart(8, '0')
                        result += addr + "  "

                        // Hex bytes
                        var hexPart = ""
                        var asciiPart = ""

                        for (var j = 0; j < bytesPerLine; j++) {
                            if (i + j < data.length) {
                                var byteVal = data.charCodeAt(i + j) & 0xFF
                                hexPart += byteVal.toString(16).toUpperCase().padStart(2, '0') + " "

                                // ASCII representation
                                if (byteVal >= 32 && byteVal <= 126) {
                                    asciiPart += String.fromCharCode(byteVal)
                                } else {
                                    asciiPart += "."
                                }
                            } else {
                                hexPart += "   "
                                asciiPart += " "
                            }

                            if (j === 7) {
                                hexPart += " "
                            }
                        }

                        result += hexPart + " |" + asciiPart + "|\n"
                    }

                    return result
                }
            }
        }

        // Status bar
        RowLayout {
            Layout.fillWidth: true

            Label {
                text: root.readOnly ? qsTr("Read-only (known section)") : qsTr("Editable (unknown section)")
                color: "#666"
                font.pointSize: 9
            }
        }
    }
}
