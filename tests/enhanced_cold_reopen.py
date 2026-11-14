"""Load as scene/cold_validation after a clean .toe launch, then start().

No reconnect action is issued. Compare embedded shader DATs against sources
expanded by the same local include loader used during construction.
"""
import json
import time
import traceback
from pathlib import Path

first_frame = 0
deadline = 0.0
attempts = 0


def start():
    global first_frame, deadline, attempts
    deadline = time.monotonic() + 30.0
    attempts = 0
    first_frame = op('MediaPipe/hand_results').cookAbsFrame
    info = op('cold_browser_info') or parent().create(infoDAT, 'cold_browser_info')
    browser = op('MediaPipe/webBrowser1/webrender1')
    info.par.op = browser
    probe()
    run("op('/project1/scene/cold_validation').module.finish()", delayFrames=60)


def probe():
    browser = op('MediaPipe/webBrowser1/webrender1')
    browser.executeJavaScript("""(() => {
        const v=document.querySelector('video');
        const t=v?.srcObject?.getVideoTracks?.()[0];
        const s=t?.getSettings?.()||{};
        document.title=JSON.stringify({ready:v?.readyState,track:t?.readyState,
            width:s.width,height:s.height,frameRate:s.frameRate});
    })()""")


def normalized(text):
    return text.replace('\r\n', '\n').replace('\r', '\n')


def finish():
    global attempts
    attempts += 1
    root = Path(project.folder)
    record = {'passed': False}
    try:
        info = op('cold_browser_info')
        info.cook(force=True)
        raw = info['title', 1].val
        try:
            video = json.loads(raw)
        except (TypeError, ValueError):
            video = {'pending_title': raw}
        if (video.get('track') != 'live' or video.get('ready') != 4) and time.monotonic() < deadline:
            # WebRender JavaScript and Info DAT title propagation are async;
            # polling reads does not restart or repair the camera stream.
            probe()
            run("op('/project1/scene/cold_validation').module.finish()", delayFrames=60)
            return
        namespace = {'__file__': str(root / 'src/shader_source.py')}
        exec(compile((root / 'src/shader_source.py').read_text(encoding='utf-8'),
                     'shader_source.py', 'exec'), namespace)
        load_source = namespace['load_source']
        matches = {}
        for node, filename in [
            ('runtime', 'td_runtime.py'), ('gesture_control', 'gesture_control.py'),
            ('orbit_control', 'orbit_control.py'), ('particle_vertex', 'particles.vert'),
            ('particle_fragment', 'particles.frag'),
            ('nebula_fragment', 'galaxy_nebula.frag'),
            ('composite_fragment', 'galaxy_composite.frag'),
        ]:
            source = ((root / 'src' / filename).read_text(encoding='utf-8')
                      if filename.endswith('.py') else load_source(root, filename))
            matches[node] = normalized(op(node).text) == normalized(source)
        runtime = op('runtime').module
        record.update({
            'project': project.name, 'build': app.build, 'video': video,
            'probe_attempts': attempts,
            'camera': op('MediaPipe').par.Webcam.eval(),
            'input': op('settings').par.Mode.eval(),
            'interaction_mode': op('settings').par.Interactionmode.eval(),
            'resolution': [op('out1').width, op('out1').height],
            'particles': int(op('settings').par.Count.eval()),
            'nebula_resolution': [op('nebula').width, op('nebula').height],
            'trail': op('settings').par.Trail.eval(),
            'glow': op('settings').par.Glow.eval(),
            'hand_frames_advanced': op('MediaPipe/hand_results').cookAbsFrame > first_frame,
            'fresh': time.monotonic() - runtime._last_input < .6,
            'errors': parent().errors(recurse=True),
            'warnings': parent().warnings(recurse=True),
            'embedded_source_matches': matches,
            'external_component_exists': (root / op('MediaPipe').par.externaltox.eval()).is_file(),
            'hand_input_connected': bool(op('hand_tracking').inputs),
        })
        record['passed'] = (
            video.get('track') == 'live' and video.get('ready') == 4
            and video.get('width') == 1280 and video.get('height') == 720
            and video.get('frameRate') == 30 and record['input'] == 'camera'
            and record['fresh'] and record['hand_frames_advanced']
            and not record['errors'] and all(matches.values())
            and record['resolution'] == [1280, 720]
            and record['external_component_exists'] and record['hand_input_connected'])
        op('out1').save(str(root / 'docs/enhanced-camera-reopen.png'))
    except Exception:
        record['error'] = traceback.format_exc()
    (root / 'docs/enhanced-cold-reopen.json').write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
