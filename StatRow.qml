import QtQuick
import qs.Commons as Theme

Item {
  id: root
  property string label: ""
  property string value: "—"
  property color foreground: Theme.Color.popups.text
  readonly property real gap: Theme.Style.space(12)
  implicitWidth: Theme.Style.space(280)
  implicitHeight: Math.max(name.implicitHeight, reading.implicitHeight, Theme.Style.space(28))
  Text {
    id: name
    width: Math.max(0, (root.width - root.gap) * 0.42)
    y: (root.height - height) / 2
    text: root.label
    textFormat: Text.PlainText
    wrapMode: Text.Wrap
    color: Qt.darker(root.foreground, 1.35)
    font.family: Theme.Style.font.family
    font.pixelSize: Theme.Style.font.body
  }
  Text {
    id: reading
    x: name.width + root.gap
    width: Math.max(0, root.width - x)
    y: (root.height - height) / 2
    text: root.value
    textFormat: Text.PlainText
    wrapMode: Text.Wrap
    horizontalAlignment: Text.AlignRight
    color: root.foreground
    font.family: Theme.Style.font.family
    font.pixelSize: Theme.Style.font.body
  }
}
