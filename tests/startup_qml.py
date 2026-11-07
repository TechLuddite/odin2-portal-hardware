"""Actual Service process lifecycle against a disposable fake helper, no sysfs."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


def run(kernel_fan):
    repo=Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix='portal-startup-qml-') as directory:
        root=Path(directory)
        (root/'runtime').mkdir(mode=0o700)
        shutil.copy2(repo/'Service.qml',root/'Service.qml')
        helper=root/'helper.py';counter=root/'startup-count'
        helper.write_text('''import json,pathlib,sys
count=pathlib.Path(sys.argv[1]);mode=sys.argv[2]
if mode=='adopt':
 print(json.dumps({'adopted':True,'token':'fixture_session_0123456789'}));sys.exit()
if mode=='read':assert sys.argv[3]=='fixture_session_0123456789'
if mode=='start':count.write_text(str(int(count.read_text())+1) if count.exists() else '1')
kernel=__KERNEL__
controls={'available':True,'owned':count.exists(),'fan_mode':None if kernel else ('auto' if count.exists() else None),'fan_owner':'kernel' if kernel else 'helper','power_mode':'saver' if count.exists() else None}
print(json.dumps(dict(controls,startup='ready') if mode=='start' else {'schema_version':1,'supported':True,'cpus':[],'gpus':[],'thermals':{'sensors':[]},'fan':{},'battery':{},'controls':controls}))
'''.replace('__KERNEL__',repr(kernel_fan)))
        read=json.dumps(['/usr/bin/python3',str(helper),str(counter),'read'])
        adopt=json.dumps(['/usr/bin/python3',str(helper),str(counter),'adopt'])
        start=json.dumps(['/usr/bin/python3',str(helper),str(counter),'start'])
        (root/'shell.qml').write_text('''import QtQuick
import Quickshell
ShellRoot {
  Service { id: service; handoffCommand: __ADOPT__; readerCommand: __READ__.concat([sessionToken]); startupCommand: __START__ }
  property int ticks: 0
  property int stable: 0
  Timer { interval: 100; running: true; repeat: true
    onTriggered: {
      if (++ticks > 80) { console.error("Startup timed out"); Qt.quit(1) }
      // Readiness must hold for 1.5 s: a startup loop would rerun within that time.
      stable = service.startupReady && !service.busy && !service.controlling ? stable + 1 : 0
      if (stable >= 15) {
        if (service.controls.power_mode !== "saver" || service.controls.fan_mode !== __FAN__) Qt.quit(2)
        else { console.log("STARTUP_QML_OK"); Qt.quit() }
      }
    }
  }
}
'''.replace('__FAN__','null' if kernel_fan else '"auto"').replace('__READ__',read).replace('__START__',start).replace('__ADOPT__',adopt))
        env=dict(os.environ,HOME=str(root),XDG_RUNTIME_DIR=str(root/'runtime'),
            XDG_CONFIG_HOME=str(root/'config'),XDG_STATE_HOME=str(root/'state'),XDG_CACHE_HOME=str(root/'cache'),
            HYPRLAND_INSTANCE_SIGNATURE='',DBUS_SESSION_BUS_ADDRESS='unix:path=/nonexistent-startup-fixture',
            QT_QPA_PLATFORM='offscreen',QT_QUICK_BACKEND='software',QS_DISABLE_CRASH_HANDLER='1')
        result=subprocess.run(['quickshell','-p',str(root/'shell.qml')],env=env,capture_output=True,text=True,timeout=10)
        output=result.stdout+result.stderr
        print(output[-3000:])
        assert result.returncode==0 and 'STARTUP_QML_OK' in output
        assert counter.read_text()=='1','Startup loop must not repeat after readiness'


def main():
    run(False)
    # Mainline: the kernel owns the fan, so fan_mode stays unset after startup.
    run(True)


if __name__=='__main__':main()
