"""Run in scene/recovery_validation after the uninterrupted benchmark.

Stops only this project's browser video tracks, then uses the normal reconnect
button. This tests a software stream interruption, not a physical USB removal.
"""
import json
import time
from pathlib import Path

results = {}


def later(function, frames=30):
    run("op('/project1/scene/recovery_validation').module.%s()" % function,
        delayFrames=frames)


def browser():
    return op('MediaPipe/webBrowser1/webrender1')


def probe():
    browser().executeJavaScript("""(() => {
        const v = document.querySelector('video');
        const t = v?.srcObject?.getVideoTracks?.()[0];
        const s = t?.getSettings?.() || {};
        document.title = JSON.stringify({ready:v?.readyState,
            currentTime:v?.currentTime, track:t?.readyState,
            width:s.width, height:s.height, frameRate:s.frameRate});
    })()""")


def snapshot():
    info = op('recovery_browser_info')
    info.cook(force=True)
    cell = info['title', 1]
    try:
        video = json.loads(cell.val)
    except Exception:
        video = {'raw': str(cell)}
    runtime = op('runtime').module
    return {'video': video,
        'fresh': time.monotonic()-runtime._last_input < .6,
        'pose': runtime.controller.pose,
        'errors': parent().errors(recurse=True),
        'warnings': parent().warnings(recurse=True)}


def start():
    global results
    results = {}
    info = op('recovery_browser_info') or parent().create(infoDAT, 'recovery_browser_info')
    info.par.op = browser()
    probe()
    later('interrupt')


def interrupt():
    results['before'] = snapshot()
    browser().executeJavaScript("document.querySelector('video')?.srcObject?.getTracks().forEach(t=>t.stop())")
    later('observe_stopped', 180)


def observe_stopped():
    probe()
    later('recover')


def recover():
    results['interrupted'] = snapshot()
    op('settings').par.Reconnect.pulse()
    later('observe_recovered', 600)


def observe_recovered():
    probe()
    later('fullscreen')


def fullscreen():
    results['recovered'] = snapshot()
    op('settings').par.Fullscreen.pulse()
    later('windowed', 60)


def windowed():
    results['fullscreen'] = {'size': op('show').par.size.eval(),
        'borders': op('show').par.borders.eval()}
    op('settings').par.Fullscreen.pulse()
    later('finish', 60)


def finish():
    results['windowed'] = {'size': op('show').par.size.eval(),
        'borders': op('show').par.borders.eval()}
    results['passed'] = {
        'stream_stopped': results['interrupted']['video'].get('track') == 'ended',
        'idle_when_stale': not results['interrupted']['fresh'] and results['interrupted']['pose']=='idle',
        'reconnected': results['recovered']['video'].get('track')=='live' and results['recovered']['fresh'],
        'camera_720p30': results['recovered']['video'].get('width')==1280 and results['recovered']['video'].get('height')==720 and results['recovered']['video'].get('frameRate')==30,
        'fullscreen_toggle': results['fullscreen']['size']=='fill' and results['windowed']['size']=='custom',
        'no_operator_errors': not results['recovered']['errors'],
    }
    results['physical_usb_removal'] = 'not performed; integrated camera'
    (Path(project.folder)/'docs/enhanced-native-recovery.json').write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
