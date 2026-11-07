from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import Mock

from backend.controls import Engine
from backend.preferences import DEFAULT, initialize, load, remember, save, adopt_session
from test_controls import CheckedHardware, control_tree, TOKEN


class StartupPreferencesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / 'state/power-fan.json'
        self.hardware = CheckedHardware(control_tree(self.root / 'sys'))
        self.engine = Engine(self.hardware, self.root / 'journal/session.json', 'boot-one', lambda: 0)

    def test_no_preferences_apply_saver_and_auto_through_existing_engine(self):
        result = initialize(self.engine.request, TOKEN, self.path)
        self.assertEqual((result['startup'], result['preference_source']), ('ready', 'defaults'))
        self.assertEqual((result['power_mode'], result['fan_mode']), ('saver', 'auto'))
        self.assertGreater(int(self.hardware.read('fan.pwm')), 77)
        self.assertEqual(set(result['changed_groups']), {'power', 'fan'})

    def test_saved_choices_survive_a_new_engine_session(self):
        save(self.path, dict(DEFAULT, power='balanced', fan='manual', fan_percent=65))
        result = initialize(self.engine.request, TOKEN, self.path)
        self.assertEqual((result['power_mode'], result['fan_mode'], result['fan_percent']), ('balanced', 'manual', 65))
        self.engine.restore()
        result = initialize(self.engine.request, 'next_session_0123456789', self.path)
        self.assertEqual((result['power_mode'], result['fan_mode']), ('balanced', 'manual'))

    def test_corrupt_preferences_fall_back_without_overwriting_bad_file(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text('{broken')
        result = initialize(self.engine.request, TOKEN, self.path)
        self.assertEqual(result['preference_source'], 'invalid-saved-defaults')
        self.assertEqual((result['power_mode'], result['fan_mode']), ('saver', 'auto'))
        self.assertEqual(self.path.read_text(), '{broken')

    def test_existing_newer_owned_choices_are_never_reset(self):
        self.engine.request(dict(op='fan', token=TOKEN, mode='max'))
        self.engine.request(dict(op='power', token=TOKEN, mode='performance'))
        self.hardware.writes.clear()
        result = initialize(self.engine.request, TOKEN, self.path)
        self.assertEqual((result['fan_mode'], result['power_mode']), ('max', 'performance'))
        self.assertEqual(self.hardware.writes, [])

    def test_other_lease_is_not_stolen(self):
        self.engine.request(dict(op='fan', token=TOKEN, mode='max'))
        self.hardware.writes.clear()
        result = initialize(self.engine.request, 'other_session_0123456789', self.path)
        self.assertEqual(result['startup'], 'waiting')
        self.assertTrue(result['occupied'])
        self.assertEqual(self.hardware.writes, [])

    def test_saved_manual_mode_still_obeys_hot_and_missing_sensor_safeguards(self):
        save(self.path, dict(DEFAULT, fan='manual', fan_percent=30))
        (self.hardware.root / 'class/thermal/thermal_zone7/temp').write_text('90000')
        result = initialize(self.engine.request, TOKEN, self.path)
        self.assertEqual(result['fan_mode'], 'manual')
        self.assertEqual(self.hardware.read('fan.pwm'), '255')
        (self.hardware.root / 'class/thermal/thermal_zone9/temp').unlink()
        self.engine.tick()
        self.assertEqual(self.hardware.read('fan.pwm'), '255')

    def test_only_successful_explicit_power_fan_actions_are_remembered(self):
        request = dict(op='power', token=TOKEN, mode='balanced')
        result = self.engine.request(request)
        remember(self.path, request, result)
        self.assertEqual(load(self.path)[0]['power'], 'balanced')
        remember(self.path, dict(op='fan'), dict(owned=True, error='refused', fan_mode='max'))
        self.assertEqual(load(self.path)[0]['fan'], 'auto')
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.path.parent.stat().st_mode & 0o777, 0o700)

    def test_failed_power_startup_reestablishes_auto_fan_and_reports_waiting(self):
        calls=[]
        def exchange(request):
            calls.append(request)
            return {'available':True,'owned':False} if request['op']=='status' else \
                {'owned':True,'fan_mode':'auto'} if request['op']=='fan' else {'error':'write refused'}
        result=initialize(exchange,TOKEN,self.path)
        self.assertEqual(result['startup'],'waiting')
        self.assertEqual([c['op'] for c in calls], ['status','fan','power','fan'])
        self.assertEqual(calls[-1]['mode'],'auto')

    def kernel_fan(self):
        zone = self.root / 'sys/class/thermal/thermal_zone15'
        device = self.root / 'sys/class/thermal/cooling_device4'
        device.mkdir(parents=True)
        (device / 'type').write_text('pwm-fan')
        zone.mkdir(parents=True, exist_ok=True)
        (zone / 'cdev0').symlink_to(device)

    def test_kernel_owned_fan_is_reported_and_startup_applies_power_only(self):
        self.kernel_fan()
        save(self.path, dict(DEFAULT, power='performance', fan='manual', fan_percent=65))
        calls = []
        def exchange(request):
            calls.append(request['op'])
            return self.engine.request(request)
        result = initialize(exchange, TOKEN, self.path)
        self.assertEqual(result['startup'], 'ready')
        self.assertEqual(result['fan_owner'], 'kernel')
        self.assertEqual(calls, ['status', 'power'])
        self.assertEqual(result['power_mode'], 'performance')
        # The saved fan choice is kept for kernels where the helper owns the fan.
        self.assertEqual(load(self.path)[0]['fan'], 'manual')
        # A later startup check is already ready and changes nothing.
        calls.clear()
        self.assertEqual(initialize(exchange, TOKEN, self.path)['startup'], 'ready')
        self.assertEqual(calls, ['status'])

    def test_helper_owned_fan_is_reported(self):
        status = self.engine.request(dict(op='status', token=TOKEN))
        self.assertEqual(status['fan_owner'], 'helper')

    def test_one_time_handoff_preserves_current_session_without_hardware_writes(self):
        self.engine.request(dict(op='fan',token=TOKEN,mode='manual',percent=65))
        self.engine.request(dict(op='power',token=TOKEN,mode='balanced'))
        self.hardware.writes.clear()
        path=self.root/'handoff.json'
        path.write_text(json.dumps(dict(token=TOKEN,boot_id='boot-one',created_at=100)))
        path.chmod(0o600)
        result=adopt_session(self.engine.request,path,self.path,'boot-one',101)
        self.assertEqual(result,dict(adopted=True,token=TOKEN))
        self.assertEqual((load(self.path)[0]['power'],load(self.path)[0]['fan']),('balanced','manual'))
        self.assertEqual(self.hardware.writes,[])
        self.assertFalse(adopt_session(self.engine.request,path,self.path,'boot-one',102)['adopted'])

    def test_invalid_handoff_cannot_acquire_or_steal_a_session(self):
        path=self.root/'handoff.json'
        for token,boot,created in [(TOKEN,'old-boot',100),(TOKEN,'boot-one',0),('other_session_0123456789','boot-one',100)]:
            path.write_text(json.dumps(dict(token=token,boot_id=boot,created_at=created)))
            path.chmod(0o600)
            self.assertFalse(adopt_session(self.engine.request,path,self.path,'boot-one',101)['adopted'])
            self.assertFalse(self.engine.request(dict(op='status',token=TOKEN)).get('owned'))
        self.assertEqual(self.hardware.writes,[])
