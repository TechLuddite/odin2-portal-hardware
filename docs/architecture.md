# Architecture

`Service.qml` owns bounded one-shot telemetry and control clients. The bar and
panel use installed Commons/Ui components; Controls has Power, Fan and Lights
sections. Monitoring runs every 15 seconds, or three seconds while open/owning
a lease. Hardware readings and applied control status are authoritative backend
responses; the UI does not optimistically report success.

`backend/portal.py` remains read-only. CPUFreq units are kHz, GPU devfreq Hz,
thermal zones milli-Celsius, and battery temperature deci-Celsius. Missing
values stay null. Fan RPM and PWM duty are distinct; cooling-state numbers are
not duty percentages.

`backend/client.py` sends bounded JSON to the separately installed root daemon.
`backend/controls.py` validates the exact board and fixed logical endpoints,
then applies allowed operations with readback. RGB uses each group's reported
multi_index order, rather than assuming red/green/blue; only standard grouped
LED devices are written. There are four groups per ring.

Power Save uses the advertised step at or below 65% of each domain's maximum.
Balanced uses 85% CPU caps, full GPU range and schedutil CPU governors. Full uses
full advertised CPU ranges and the performance CPU governor. GPU minimum and governor remain unchanged; only its maximum clock is capped.
Effective GPU minimum constraints can vary with DRM client QoS requests. No UFS or GPU/GMU
runtime-power-management setting is changed. These are Linux presets, not copied
Android policy or watt/TDP limits.

The fan loop runs in the root helper once per second while owned. Auto maps the
hottest CPU/GPU reading from 30% at 45°C to full at 85°C. Manual has the same
30% floor and emergency override. No pwm1_enable=2 automatic-mode assumption is
made: this driver implements PWM/regulator enable semantics, not a fan curve.

Settings are session scoped. A token identifies one lease; the configured UID
is authenticated by the Unix socket's peer credentials. Status reads renew
only that session's existing lease, and never acquire one. A ten-second timeout
or a boot-clock scheduling gap over five seconds restores prior values. The
journal records logical keys and allowed transaction values before writes; it
is fsynced per user transaction, not per fan tick. Restart recovery revalidates
all saved values and never interprets journal fields as filesystem paths. A new
boot discards the previous boot's journal without hardware writes.

Version0.3 adds user-owned power/fan preference persistence above that unchanged
helper. `backend/preferences.py` validates a closed schema and the CLI records
only successful explicit power/fan changes. At plugin load, initialization uses
saved choices or Saver/Auto defaults, starting the fan first. It waits for an
existing lease/recovery, preserves a valid current owned session, and retries
failed startup at the sampling cadence. If power initialization fails after a
helper rollback, it independently requests Auto fan before a later retry.
The manifest retains the service across unrelated plugin rescans. Actual shell
exit/explicit disable still release it.

Version 0.4 adds `backend/lighting.py` above the same root API. A separate private,
closed-schema per-side preference file records RGB channels, brightness and
Manual/Follow theme. The existing reader describes saved state and a complete
current palette; it never writes LEDs. A separate Service process serializes
theme sync and explicit LED actions with an advisory preference lock, verifies
ownership, computes selected targets and calls the existing off-first RGB client.
Only settled readback is saved, and matching targets do not generate writes.
Automatic failures latch visibly until explicit interaction or service reload.
Startup/resume synchronization waits for power/fan ownership; explicit Restore
suppresses both initializers. Guarded adoption saves actual uniform ring state
without writes and preserves any existing manual preference. Each side is a
separate acknowledged operation; a later-side failure can leave an earlier side
applied, and is reported rather than claimed atomic. Root journaling and external
change refusal remain authoritative.

Recovery restores only groups still consistent with owned values. Live external
changes are preserved and reported. Fan recovery at 85°C or unavailable sensors
keeps full cooling until conditions permit restoration. The daemon can continue
recovery after a restart; stopping it while hot leaves full fan and its journal.
See [security](../SECURITY.md) and [installation/recovery](../README.md).

Other devices require explicitly reviewed adapters. Charge limits, animated RGB,
custom fan curves and device-independent boot profiles remain future work.
