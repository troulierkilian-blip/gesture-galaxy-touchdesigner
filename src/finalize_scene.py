"""Apply and save the completed source in the running development instance."""
from pathlib import Path
import json
source_namespace={}
exec(compile((ROOT/'src/shader_source.py').read_text(encoding='utf-8'),'shader_source.py','exec'),source_namespace)
load_source=source_namespace['load_source']

s = op('/project1/scene')
s.op('runtime').module.stop()
for name, source in [('runtime','td_runtime.py'),('gesture_control','gesture_control.py'),('orbit_control','orbit_control.py'),('particle_vertex','particles.vert'),('particle_fragment','particles.frag'),('nebula_fragment','galaxy_nebula.frag'),('composite_fragment','galaxy_composite.frag')]:
    s.op(name).text = load_source(ROOT,source)
s.op('runtime').module.start()
s.op('camera').par.tz = 7.4
s.op('glow').par.bloomthreshold = .55
s.op('render').par.bgcolorr,s.op('render').par.bgcolorg,s.op('render').par.bgcolorb=.0001,.00015,.00035
for node in s.op('hand_tracking').findChildren():
    p=getattr(node.par,'file',None)
    if p is not None and 'td_scripts' in str(p.eval()):
        old=str(p.eval())
        text=(ROOT/'upstream'/old[old.index('td_scripts'):]).read_text(encoding='utf-8')
        node.par.file=''
        node.text=text
s.op('hand_tracking').par.externaltox=''
s.op('hand_tracking').par.enableexternaltox=False
s.op('hand_tracking').par.Maxhands.mode=ParMode.CONSTANT
s.op('hand_tracking').par.Maxhands=2
s.op('MediaPipe').par.Gnumhands.mode=ParMode.CONSTANT
s.op('MediaPipe').par.Gnumhands=2
incoming=s.op('hand_input') or s.create(selectDAT,'hand_input')
incoming.par.dat=s.op('MediaPipe/hand_results')
s.op('hand_tracking').inputConnectors[0].connect(incoming)
settings=s.op('settings')
page=settings.customPages[0]
for name,label in [('Benchmark','开始 10 分钟测试'),('Stoptest','停止测试记录')]:
    if getattr(settings.par,name,None) is None: page.appendPulse(name,label=label)
view=op('/project1/interface')
view.op('controls').par.h=440
view.op('controls').par.y=130
view.op('camera_preview').par.y=570
view.op('camera_preview').par.h=100
for name in ('native_validation','browser_info','gesture_diagnostic','recovery_validation','recovery_browser_info','cold_validation','cold_browser_info','ui_validation','view_validation','orbit_validation'):
    if s.op(name): s.op(name).destroy()
settings.par.Mode='camera'
settings.par.Interactionmode='rotate'
settings.par.Rotationsensitivity=1
settings.par.Count='20000'
settings.par.Palette=0
settings.par.Simpose='track'
settings.par.Simscale=1
settings.par.Glow=.32
settings.par.Trail=.08
s.op('runtime').module.controller.reset()
s.op('runtime').module.orbit=s.op('orbit_control').module.OrbitControl()
for i,v in enumerate([.5,.5,.45,1,0,0,0,0,.959931,0]):
    getattr(s.op('state').par,f'const{i}value').val=v
s.op('MediaPipe').par.Detectgestures=True
exec(compile((ROOT/'src/save_project.py').read_text(encoding='utf-8'),
             'save_project.py', 'exec'), dict(globals()))
(ROOT/'docs/finalized.json').write_text(json.dumps({'project':project.name,'folder':project.folder}),encoding='utf-8')
