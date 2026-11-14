"""Embedded scene driver. Only controls a few uniforms; particles animate on GPU."""
import csv
import hashlib
import json
import math
import os
import re
import shutil
import time
import traceback
from datetime import datetime, timezone
from urllib.parse import urlencode
from pathlib import Path

controller = None
orbit = None
_last = 0.0
_last_ui = 0.0
_last_frame = None
_last_input = 0.0
_frame_count = 0
_fps = 0.0
_period = 0.0
_last_error = ''
_benchmark = None
_updating_settings = False
_acceptance = None


def start():
    global controller, orbit, _last, _period, _frame_count, _last_frame, _last_input
    controller = op('gesture_control').module.GestureControl()
    orbit = op('orbit_control').module.OrbitControl()
    orbit.set_mode(op('settings').par.Interactionmode.eval())
    _last = _period = time.monotonic()
    _frame_count, _last_frame, _last_input = 0, None, 0.0
    controller.theme = op('settings').par.Palette.menuIndex
    run("op('/project1/scene/show').par.winopen.pulse()",delayFrames=30)
    # Reload once after upstream port/device callbacks settle. This avoids an
    # ended stream caused by overlapping startup camera requests in v0.6.0.
    run("op('/project1/scene/runtime').module.reconnect()",delayFrames=180)
    run("op('/project1/scene/runtime').module.startup_health()",delayFrames=480)
    if os.environ.get('GESTURE_PARTICLES_VALIDATE') == '1':
        boot=op('/project1/bootstrap')
        if boot:
            boot.par.start=False
            boot.par.active=True
        # Developer mode enables inspection only. Tests start explicitly so a
        # cold-start check cannot overwrite the completed 10-minute evidence.


def startup_health():
    s=op('/project1/scene')
    record={'project':project.name,'build':app.build,'resolution':[s.op('out1').width,s.op('out1').height],
        'errors':s.errors(recurse=True),'warnings':s.warnings(recurse=True),
        'input_connected':bool(s.op('hand_tracking').inputs),
        'camera':s.op('MediaPipe').par.Webcam.eval()}
    (Path(project.folder)/'docs/startup-health.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')


def reconnect():
    """Build a fresh URL after restored device parameters and ports settle.

    Upstream noReload parameters can send their initial WebSocket update before
    the browser is connected, leaving the author's saved camera in the URL.
    """
    mp=op('MediaPipe')
    config={'Webcam':mp.par.Webcam.eval(),'Wwidth':1280,'Wheight':720,
        'Wtargetframerate':30,'Wflip':int(mp.par.Wflip.eval()),'Gnumhands':2,
        'Detectgestures':int(op('settings').par.Mode.eval()=='camera'),
        'Showoverlays':0,'Hdetectconf':.2,'Hpresconf':.2,'Htrackconf':.5,
        'Gnumgestures':2,'Gscore':.2}
    for key in ('Detectfacelandmarks','Detectfaces','Detectposes','Detectobjects',
                'Detectimages','Detectsegments','Detectimageembeddings'):
        config[key]=0
    address='http://localhost:'+str(mp.op('webserver1').par.port.eval())+'/?'+urlencode(config)
    mp.op('current_url').text=address
    mp.op('webBrowser1').par.Address=address
    mp.op('webBrowser1/webrender1').par.reload.pulse()


def setting_changed(par, prev):
    global _updating_settings
    if _updating_settings: return
    mp = op('MediaPipe')
    if par.name == 'Mirror': mp.par.Wflip = par.eval()
    if par.name == 'Camera' and par.eval() not in ('','waiting'):
        mp.par.Webcam = par.eval()
        reconnect()
    if par.name == 'Palette' and controller is not None: controller.theme = par.menuIndex
    if par.name == 'Interactionmode' and orbit is not None: orbit.set_mode(par.eval())
    if par.name == 'Mode':
        if orbit is not None: orbit.anchor = None
        # Simulation does not use or classify webcam frames.
        enabled = par.eval() == 'camera'
        mp.par.Detectgestures = enabled


def pulse(par):
    settings = op('settings')
    if par.name == 'Reset':
        controller.reset()
        orbit.reset_view()
        settings.par.Palette = 0
        settings.par.Simscale = 1
        op('trail_previous').par.resetpulse.pulse()
    elif par.name == 'Resetview':
        orbit.reset_view()
    elif par.name == 'Fullscreen':
        window = op('show')
        window.par.winclose.pulse()
        fullscreen = not parent().fetch('fullscreen', False)
        parent().store('fullscreen', fullscreen)
        window.par.borders = not fullscreen
        window.par.size = 'fill' if fullscreen else 'custom'
        window.par.winopen.pulse()
    elif par.name == 'Reconnect':
        reconnect()
    elif par.name == 'Benchmark':
        begin_benchmark(600,op('settings').par.Mode.eval())
    elif par.name == 'Stoptest':
        stop()


def _channel_values():
    values = {}
    tracker = op('hand_tracking')
    for name in ('rename_joints','gestures','helpers'):
        node = tracker.op(name)
        if node is None: raise RuntimeError('缺少手势输出：' + name)
        for channel in node.chans():
            values[channel.name] = channel[0]
    return values


def ui_action(name, direction=1):
    """Click handlers for the CJK-safe control surface; settings stay public."""
    par=getattr(op('settings').par,name)
    if name in ('Reset','Resetview','Fullscreen','Reconnect','Benchmark','Stoptest'):
        par.pulse()
    elif name=='Mirror':
        par.val=not par.eval()
    elif name in ('Sensitivity','Rotationsensitivity','Glow','Trail','Simscale'):
        step=.05 if name in ('Glow','Trail') else .1
        par.val=round(max(par.min,min(par.max,par.eval()+direction*step)),2)
    else:
        names=list(par.menuNames)
        if names:
            current=names.index(str(par.eval())) if str(par.eval()) in names else -1
            par.val=names[(current+direction)%len(names)]


def _control_text():
    table=op('control_labels')
    if table is None: return
    settings=op('settings')
    numeric={'Sensitivity','Rotationsensitivity','Glow','Trail','Simscale'}
    names=op('../interface/controls').fetch('row_names',[])
    row=2
    for name in names:
        p=getattr(settings.par,name)
        if name in ('Reset','Resetview','Fullscreen','Reconnect','Benchmark','Stoptest'):
            value=''
        elif name=='Mirror': value='[ 开启 ]' if p.eval() else '[ 关闭 ]'
        elif name in numeric: value=f'{p.eval():.2f}'
        elif name=='Camera':
            camera=str(p.eval())
            value='[ 内置摄像头 ]' if 'Integrated Camera' in camera else camera[:17]
        else: value='[ '+str(p.menuLabels[p.menuIndex])+' ]'
        if table[row,2].val!=value: table[row,2]=value
        row+=4 if name in numeric else 2


def _simulated_input():
    module = op('gesture_control').module
    settings = op('settings')
    canvas = op('../interface/canvas')
    x, y = float(canvas.panel.u), float(canvas.panel.v)
    inside=bool(canvas.par.enable.eval()) and bool(canvas.panel.inside)
    if not inside:
        x, y = controller.x, controller.y
    pose = settings.par.Simpose.eval()
    hand = module.Hand(True, x=x, y=y,
        pinch=.06 if pose=='pinch' else 1.0,
        fist=.99 if pose=='fist' or (inside and bool(canvas.panel.lselect)) else 0.,
        palm=.99 if pose=='palm' or (inside and bool(canvas.panel.rselect)) else 0.,
        victory=.99 if pose=='victory' else 0.,
        thumb_up=.99 if pose=='thumb_up' else 0.)
    return None, hand


def _refresh_ui(now, status):
    global _updating_settings
    settings, mp = op('settings'), op('MediaPipe')
    names, labels = list(mp.par.Webcam.menuNames), list(mp.par.Webcam.menuLabels)
    # Ignore the author's saved device list until this machine sends its list.
    camera_table = mp.op('webcam_menu')
    if camera_table.numRows > 1:
        actual = [str(camera_table[i,0]) for i in range(1,camera_table.numRows)]
        if mp.par.Webcam.eval() not in actual:
            mp.par.Webcam = actual[0]
        names = labels = actual
    if names and names != list(settings.par.Camera.menuNames):
        _updating_settings = True
        try:
            settings.par.Camera.menuNames = names
            settings.par.Camera.menuLabels = labels
            settings.par.Camera = mp.par.Webcam.eval()
        finally:
            _updating_settings = False
    mode = settings.par.Mode.eval()
    if _benchmark:
        status += '\n测试记录 ' + str(int(now-_benchmark['start'])) + '/' + str(_benchmark['seconds']) + ' 秒'
    labels = {'fist':'握拳 · 聚合','palm':'张掌 · 扩散','track':'手掌跟随','idle':'待机'}
    source = '鼠标模拟' if mode=='mouse' else {'right':'右手','left':'左手','none':'未检测到手'}.get(controller.selected,'')
    op('status').par.text = '\n'.join([
        source + '  /  ' + labels[controller.pose],
        f'{_fps:.1f} FPS  ·  {int(settings.par.Count.eval()):,} 星点',
        status,
        ('旋转视角' if orbit.mode=='rotate' else '移动银河')+' · 竖拇指切换',
        f'水平 {math.degrees(orbit.yaw)%360:.0f}° / 俯仰 {math.degrees(orbit.pitch):.0f}°',
        '握拳收拢 · 张掌舒展 · 捏合增亮',
        '双手缩放 · V 换色 · 无手慢自转'])
    _control_text()


def _parse_nebula_steps(source):
    """Read the embedded shader's literal budget; never substitute a default."""
    source = re.sub(r'/\*.*?\*/|//[^\n]*', '', source, flags=re.S)
    matches = re.findall(r'\bconst\s+int\s+VOLUME_STEPS\s*=\s*(\d+)\s*;', source)
    if len(matches) == 1 and int(matches[0]) > 0:
        return int(matches[0]), None
    return None, 'Embedded nebula_fragment must contain one positive literal const int VOLUME_STEPS.'


def _benchmark_configuration():
    """Inspect the live graph, not the source files or a previous report."""
    result, diagnostics = {}, []
    readers = {
        'mode': lambda: str(op('settings').par.Mode.eval()),
        'particles': lambda: int(op('settings').par.Count.eval()),
        'trail': lambda: float(op('settings').par.Trail.eval()),
        'glow': lambda: float(op('settings').par.Glow.eval()),
        'camera': lambda: str(op('MediaPipe').par.Webcam.eval()),
        'output_resolution': lambda: [int(op('out1').width), int(op('out1').height)],
        'nebula_resolution': lambda: [int(op('nebula').width), int(op('nebula').height)],
    }
    for name, read in readers.items():
        try:
            result[name] = read()
        except Exception as error:
            result[name] = None
            diagnostics.append(name + ': ' + str(error))
    try:
        source = op('nebula_fragment').text
        result['nebula_steps'], diagnostic = _parse_nebula_steps(source)
        result['nebula_shader_sha256'] = hashlib.sha256(source.encode('utf-8')).hexdigest()
        if diagnostic: diagnostics.append(diagnostic)
    except Exception as error:
        result['nebula_steps'] = result['nebula_shader_sha256'] = None
        diagnostics.append('nebula_fragment: ' + str(error))
    result['metadata_diagnostics'] = diagnostics
    return result


def _benchmark_frames():
    # cookAbsFrame is the last frame on which a node cooked, not a cook count.
    # Recording it proves sampled output advanced without mislabelling it FPS.
    result = {}
    for name, node in (('render', 'render'), ('nebula', 'nebula'),
                       ('output', 'out1'), ('input', 'MediaPipe/hand_results')):
        try: result[name] = int(op(node).cookAbsFrame)
        except Exception: result[name] = None
    try: result['timeline'] = int(absTime.frame)
    except Exception: result['timeline'] = None
    return result


def _benchmark_summary(b, now, status):
    samples = sorted(b['samples'])
    count = len(samples)
    config = b['configuration']
    summary = dict(config)
    summary.update({
        'status': status, 'run_id': b['run_id'], 'started_at_utc': b['started_at_utc'],
        'updated_at_utc': datetime.now(timezone.utc).isoformat(),
        'requested_seconds': b['seconds'], 'duration_seconds': round(now-b['start'], 2),
        'samples': count, 'fps_measurement': 'TouchDesigner frame-loop frequency; not camera capture FPS',
        'min_fps': min(samples) if count else None,
        'median_fps': samples[count//2] if count else None,
        'mean_fps': sum(samples)/count if count else None,
        'configuration_at_start': b['configuration_at_start'],
        'configuration_changes': b['configuration_changes'],
        'configuration_unchanged': not b['configuration_changes'],
        'input_fresh_samples': b['fresh_samples'],
        'input_fresh_fraction': b['fresh_samples']/count if count else None,
        'camera_samples': b['camera_samples'],
        'camera_fresh_samples': b['camera_fresh_samples'],
        'camera_fresh_fraction': (b['camera_fresh_samples']/b['camera_samples']) if b['camera_samples'] else None,
        'frame_evidence_start': b['frames_at_start'], 'frame_evidence_end': b['last_frames'],
        'frame_advanced_samples': b['frame_advanced_samples'],
        'frame_stalled_samples': b['frame_stalled_samples'],
        'frame_unavailable_samples': b['frame_unavailable_samples'],
        'at_least_30fps': bool(status == 'completed' and count and min(samples) >= 30),
    })
    summary['valid_completed_run'] = bool(status == 'completed' and count
        and now-b['start'] >= b['seconds'] and not b['configuration_changes']
        and not config['metadata_diagnostics']
        and b['frame_advanced_samples']['render'] == count
        and b['frame_advanced_samples']['output'] == count
        and b['camera_fresh_samples'] == b['camera_samples'])
    return summary


def _write_benchmark_summary(b, now, status):
    b['summary_path'].write_text(json.dumps(_benchmark_summary(b, now, status),
        ensure_ascii=False, indent=2), encoding='utf-8')


def begin_benchmark(seconds=600, name='simulation'):
    global _benchmark
    stop()
    if seconds <= 0: raise ValueError('Benchmark duration must be positive.')
    if not name or Path(name).name != name or any(c in name for c in '/\\'):
        raise ValueError('Benchmark name must be one filename component.')
    docs = Path(project.folder)/'docs'
    docs.mkdir(parents=True, exist_ok=True)
    now_utc = datetime.now(timezone.utc)
    run_id = now_utc.strftime('%Y%m%dT%H%M%S.%fZ')
    path = docs/('benchmark-'+name+'.csv')
    summary_path = path.with_suffix('.json')
    # Preserve both old evidence files before replacing the public summary with
    # a running marker. An interrupted new run can never look like an old pass.
    for previous in (path, summary_path):
        if previous.exists():
            history = docs/'benchmark-history'/run_id
            history.mkdir(parents=True, exist_ok=True)
            shutil.copy2(previous, history/previous.name)
    configuration = _benchmark_configuration()
    frames = _benchmark_frames()
    handle = path.open('w',encoding='utf-8',newline='')
    writer = csv.writer(handle)
    writer.writerow(['elapsed_seconds','fps','mode','particles','input_fresh','hand','pose',
        'trail','glow','camera','output_width','output_height','nebula_width','nebula_height',
        'nebula_steps','render_cook_abs_frame','nebula_cook_abs_frame','output_cook_abs_frame',
        'input_cook_abs_frame','timeline_frame','run_id'])
    handle.flush()
    _benchmark = {'start':time.monotonic(),'seconds':seconds,'name':name,'file':handle,
        'writer':writer,'samples':[],'summary_path':summary_path,'run_id':run_id,
        'started_at_utc':now_utc.isoformat(),'configuration':configuration,
        'configuration_at_start':configuration,'configuration_changes':[],
        'fresh_samples':0,'camera_samples':0,'camera_fresh_samples':0,
        'frames_at_start':frames,'last_frames':frames,
        'frame_advanced_samples':dict.fromkeys(frames,0),
        'frame_stalled_samples':dict.fromkeys(frames,0),
        'frame_unavailable_samples':dict.fromkeys(frames,0)}
    _write_benchmark_summary(_benchmark, _benchmark['start'], 'running')


def stop():
    global _benchmark
    if _benchmark:
        b, _benchmark = _benchmark, None
        b['file'].close()
        _write_benchmark_summary(b, time.monotonic(), 'stopped')


def _sample_benchmark(now, fresh):
    global _benchmark
    if not _benchmark: return
    b = _benchmark
    elapsed = now-b['start']
    config = _benchmark_configuration()
    if config != b['configuration']:
        b['configuration_changes'].append({'elapsed_seconds':round(elapsed,2), 'configuration':config})
        b['configuration'] = config
    frames = _benchmark_frames()
    for key, current in frames.items():
        previous = b['last_frames'][key]
        if current is None or previous is None: bucket = 'frame_unavailable_samples'
        elif current > previous: bucket = 'frame_advanced_samples'
        else: bucket = 'frame_stalled_samples'
        b[bucket][key] += 1
    b['last_frames'] = frames
    b['fresh_samples'] += int(bool(fresh))
    if config['mode'] == 'camera':
        b['camera_samples'] += 1
        b['camera_fresh_samples'] += int(bool(fresh))
    output = config['output_resolution'] or [None,None]
    nebula = config['nebula_resolution'] or [None,None]
    b['writer'].writerow([round(elapsed,2),round(_fps,2),config['mode'],config['particles'],
        int(fresh),controller.selected,controller.pose,config['trail'],config['glow'],config['camera'],
        *output,*nebula,config['nebula_steps'],frames['render'],frames['nebula'],frames['output'],
        frames['input'],frames['timeline'],b['run_id']])
    b['file'].flush()
    b['samples'].append(_fps)
    completed = elapsed >= b['seconds']
    _write_benchmark_summary(b, now, 'completed' if completed else 'running')
    if completed:
        b['file'].close()
        _benchmark = None


def start_acceptance(name='galaxy-camera-interactions'):
    global _acceptance
    if _acceptance: _acceptance['file'].close()
    path=Path(project.folder)/'docs'/(name+'.csv')
    handle=path.open('w',encoding='utf-8',newline='')
    writer=csv.writer(handle)
    writer.writerow(['seconds','fresh','hand','pose','x','y','expansion','scale','glow','theme','mode','thumb_up','two_hands','yaw_rad','pitch_rad','spin_rad'])
    _acceptance={'start':time.monotonic(),'last':0,'file':handle,'writer':writer}


def _record_acceptance(now,fresh):
    if not _acceptance or now-_acceptance['last']<.1: return
    a=_acceptance
    a['last']=now
    c=controller
    a['writer'].writerow([round(now-a['start'],2),int(fresh),c.selected,c.pose,
        round(c.x,3),round(c.y,3),round(c.expansion,3),round(c.scale,3),round(c.glow,3),c.theme,
        orbit.mode,round(orbit.thumb_score,3),int(orbit.two_hands),round(orbit.yaw,4),round(orbit.pitch,4),round(orbit.spin,4)])
    a['file'].flush()


def tick():
    global _last, _last_ui, _frame_count, _fps, _period, _last_input, _last_frame, _last_error
    if controller is None: start()
    now = time.monotonic()
    dt, _last = min(now-_last,.1), now
    _frame_count += 1
    settings = op('settings')
    fresh = False
    try:
        if settings.par.Mode.eval() == 'mouse':
            left, right = _simulated_input()
            fresh = True
            controller.update(dt,left,right,fresh=True,sensitivity=settings.par.Sensitivity.eval())
            controller.scale = settings.par.Simscale.eval()
            status = '模拟输入 · 不代表真实识别'
        else:
            data = op('MediaPipe/hand_results')
            frame = data.cookAbsFrame
            if frame != _last_frame and data.text.strip():
                _last_frame, _last_input = frame, now
            fresh = (now-_last_input) < .6
            values = _channel_values()
            left,right,distance = op('gesture_control').module.hands_from_channels(values)
            controller.update(dt,left,right,distance,fresh,settings.par.Sensitivity.eval())
            status = '摄像头已连接' if fresh else '等待视频输入 · 检查摄像头'
        orbit.update(dt,left,right,fresh,settings.par.Rotationsensitivity.eval(),(controller.x,controller.y))
        if settings.par.Interactionmode.eval() != orbit.mode:
            settings.par.Interactionmode = orbit.mode
        if settings.par.Mode.eval() == 'camera': _record_acceptance(now,fresh)
        if settings.par.Palette.menuIndex != controller.theme:
            settings.par.Palette = controller.theme
        values = [orbit.x,orbit.y,controller.expansion,controller.scale,controller.glow,controller.theme,int(controller.selected!='none'),orbit.yaw,orbit.pitch,orbit.spin]
        for i,value in enumerate(values):
            getattr(op('state').par,f'const{i}value').val = value
        if now-_period >= 1.0:
            _fps = _frame_count/(now-_period)
            _frame_count,_period = 0,now
            _sample_benchmark(now,fresh)
        if now-_last_ui >= .25:
            _last_ui = now
            _refresh_ui(now,status)
        _last_error = ''
    except Exception:
        error = traceback.format_exc()
        if error != _last_error:
            _last_error = error
            (Path(project.folder)/'docs/runtime-error.log').write_text(error,encoding='utf-8')
        op('status').par.text = '输入初始化失败\n请查看 docs/runtime-error.log\n可切换鼠标模拟继续预览'
