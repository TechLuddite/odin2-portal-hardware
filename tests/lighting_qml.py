"""Real Service LED sync/error lifecycle with private synthetic helper processes."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


def main():
    repo = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="portal-lights-qml-") as directory:
        root = Path(directory)
        (root / "runtime").mkdir(mode=0o700)
        shutil.copy2(repo / "Service.qml", root / "Service.qml")
        helper = root / "helper.py"
        state = root / "state.json"
        state.write_text(json.dumps(dict(count=0, needs=True, fail=False)))
        helper.write_text('''import json,pathlib,sys
path=pathlib.Path(sys.argv[1]);action=sys.argv[2];state=json.loads(path.read_text())
controls=dict(available=True,owned=True,fan_mode='auto',power_mode='saver')
if action=='sync':
 state['count']+=1
 if not state['fail']:state['needs']=False
 path.write_text(json.dumps(state))
 print(json.dumps(dict(controls,error='synthetic write failure' if state['fail'] else '')))
elif action=='request':
 request=json.loads(sys.argv[-1]);state.update(needs=True,fail=request['op']=='force-failure')
 path.write_text(json.dumps(state));print(json.dumps(controls))
else:
 print(json.dumps(dict(schema_version=1,supported=True,cpus=[],gpus=[],thermals={'sensors':[]},fan={},battery={},controls=controls,
 lighting=dict(sides={},needs_sync=state['needs'],count=state['count']))))
''')
        argv = ["/usr/bin/python3", "-I", "-B", str(helper), str(state)]
        (root / "shell.qml").write_text('''import QtQuick
import Quickshell
ShellRoot {
  property int stage: 0
  property int ticks: 0
  property int waited: 0
  Service { id: service; startupManaged: false; startupReady: true; lightingManaged: true
    readerCommand: __READ__; lightingCommand: __SYNC__; controlCommand: __WRITE__ }
  function check(ok, message) { if (!ok) throw new Error(message) }
  Timer { interval: 100; running: true; repeat: true
    onTriggered: {
      try {
        if (++ticks > 80) throw new Error("LED fixture timed out at stage " + stage)
        if (service.busy || service.controlling || !service.snapshot) return
        if (stage === 0 && service.lighting.count === 1) {
          check(!service.lighting.needs_sync && !service.controlError, "first sync settles")
          service.refresh(); stage++
        } else if (stage === 1) {
          check(service.lighting.count === 1, "settled state does not resync")
          service.control({op: "force-failure"}); stage++
        } else if (stage === 2 && service.lightingFailed) {
          check(service.controlError === "synthetic write failure", "sync failure is visible")
          service.refresh(); stage++
        } else if (stage === 3) {
          if (++waited < 4) { service.refresh(); return }
          check(service.lighting.count === 2 && service.lightingFailed, "failed sync is not blindly retried")
          service.control({op: "fix"}); stage++
        } else if (stage === 4 && service.lighting.count === 3) {
          check(!service.lightingFailed && !service.controlError && !service.lighting.needs_sync, "explicit choice permits recovery")
          console.log("LIGHTING_QML_OK"); Qt.quit()
        }
      } catch (error) { console.error(error); Qt.exit(1) }
    }
  }
}
'''.replace("__READ__", json.dumps(argv + ["read"])).replace("__SYNC__", json.dumps(argv + ["sync"])).replace("__WRITE__", json.dumps(argv + ["request"])))
        env = dict(os.environ, HOME=str(root), XDG_RUNTIME_DIR=str(root / "runtime"),
                   XDG_CONFIG_HOME=str(root / "config"), XDG_STATE_HOME=str(root / "state"),
                   XDG_CACHE_HOME=str(root / "cache"), HYPRLAND_INSTANCE_SIGNATURE="",
                   DBUS_SESSION_BUS_ADDRESS="unix:path=/nonexistent-lighting-fixture",
                   QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software", QS_DISABLE_CRASH_HANDLER="1")
        env.pop("WAYLAND_DISPLAY", None)
        result = subprocess.run(["quickshell", "-p", str(root / "shell.qml")], env=env, capture_output=True, text=True, timeout=12)
        output = result.stdout + result.stderr
        print(output[-3500:])
        assert result.returncode == 0 and "LIGHTING_QML_OK" in output
        assert json.loads(state.read_text())["count"] == 3


if __name__ == "__main__":
    main()
