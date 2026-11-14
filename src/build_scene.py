"""Executed inside TouchDesigner. All generated nodes belong to /project1/scene."""
import json
import random
from pathlib import Path

ROOT = Path(ROOT)
source_namespace = {}
exec(compile((ROOT/'src/shader_source.py').read_text(encoding='utf-8'),'shader_source.py','exec'),source_namespace)
load_source = source_namespace['load_source']
host = op('/project1')
host.op('bootstrap').par.file = ''
host.op('bootstrap').par.loadonstart = False
if host.op('scene'):
    host.op('scene').destroy()
scene = host.create(containerCOMP, 'scene')
scene.par.w = 1280
scene.par.h = 720
scene.nodeX, scene.nodeY = 0, 0

def setpar(node, name, value):
    par = getattr(node.par, name, None)
    if par is None:
        raise RuntimeError('Missing required parameter: ' + node.path + '.' + name)
    par.mode = ParMode.CONSTANT
    par.val = value

def textdat(name, file):
    dat = scene.create(textDAT, name)
    dat.text = load_source(ROOT, file)
    return dat

settings = scene.create(baseCOMP, 'settings')
page = settings.appendCustomPage('控制')

def custom(kind, name, label, default=None, low=None, high=None, names=None, labels=None):
    p = getattr(page, 'append' + kind)(name, label=label)[0]
    if names is not None:
        p.menuNames, p.menuLabels = names, labels or names
    if default is not None:
        p.default = default
        p.val = default
    if low is not None:
        p.min = p.normMin = low
        p.clampMin = True
    if high is not None:
        p.max = p.normMax = high
        p.clampMax = True
    return p

custom('Menu','Mode','输入方式',0,names=['camera','mouse'],labels=['摄像头手势','鼠标模拟'])
custom('StrMenu','Camera','摄像头','waiting',names=['waiting'],labels=['等待摄像头列表'])
custom('Toggle','Mirror','镜像画面',True)
custom('Menu','Interactionmode','操作模式',0,names=['rotate','move'],labels=['旋转视角','移动银河'])
custom('Float','Rotationsensitivity','旋转灵敏度',1.0,.4,2.0)
custom('Pulse','Resetview','复位视角')
custom('Float','Sensitivity','移动灵敏度',1.0,.4,2.0)
custom('Menu','Count','粒子数量',2,names=['5000','10000','20000'],labels=['5,000','10,000','20,000'])
custom('Float','Glow','辉光强度',.32,0,2)
custom('Float','Trail','拖尾长度',.08,0,.8)
custom('Menu','Palette','配色',0,names=['violet','cyan','gold'],labels=['蓝紫','青蓝','金橙'])
custom('Menu','Simpose','模拟手势',0,names=['track','fist','palm','pinch','victory','thumb_up'],labels=['移动','握拳聚合','张掌扩散','捏合增亮','V 手势换色','竖拇指切换'])
custom('Float','Simscale','模拟双手缩放',1,.55,1.8)
custom('Pulse','Reset','重置效果')
custom('Pulse','Fullscreen','全屏 / 退出全屏')
custom('Pulse','Reconnect','重新连接摄像头')
custom('Pulse','Benchmark','开始 10 分钟测试')
custom('Pulse','Stoptest','停止测试记录')

vendor = ROOT/'vendor/mediapipe-v0.6.0/toxes'
mp = scene.loadTox(str(vendor/'MediaPipe.tox'))
mp.name = 'MediaPipe'
mp.par.externaltox = str(vendor/'MediaPipe.tox')
mp.par.enableexternaltox = True
for name in ('Detectfacelandmarks','Detectfaces','Detectposes','Detectobjects',
             'Detectimages','Detectsegments','Detectimageembeddings'):
    setpar(mp, name, False)
for name in ('Detectgestures',):
    setpar(mp, name, True)
for name, val in {'Gnumhands':2,'Resolutionw':1280,'Resolutionh':720,
                  'Wtargetframerate':'30','Wflip':1,'Showoverlays':0}.items():
    # Builds expose either Hnumhands or Gnumhands; set every provided alias.
    if getattr(mp.par,name,None) is not None:
        setpar(mp,name,val)
hands = scene.loadTox(str(vendor/'hand_tracking.tox'))
hands.name = 'hand_tracking'
# The tag's missing release component references development Python files.
# Embed those exact tag sources, so the delivered project is relocatable.
for node in hands.findChildren():
    file_par = getattr(node.par,'file',None)
    if file_par is not None and 'td_scripts' in str(file_par.eval()):
        old_path = str(file_par.eval())
        source = ROOT/'upstream'/old_path[old_path.index('td_scripts'):]
        node.par.file = ''
        node.text = source.read_text(encoding='utf-8')
hands.par.externaltox = ''
hands.par.enableexternaltox = False
hands.par.Lockhandedness = True
hands.par.Maxhands.mode = ParMode.CONSTANT
hands.par.Maxhands = 2
hand_input = scene.create(selectDAT,'hand_input')
hand_input.par.dat = mp.op('hand_results')
hands.inputConnectors[0].connect(hand_input)

control_module = textdat('gesture_control', 'gesture_control.py')
orbit_module = textdat('orbit_control', 'orbit_control.py')
runtime = textdat('runtime', 'td_runtime.py')
state = scene.create(constantCHOP, 'state')
state.seq.const.numBlocks = 10
for i, (name,value) in enumerate([('x',.5),('y',.5),('expansion',.45),('scale',1),('glow',0),('theme',0),('present',0),('yaw',0),('pitch',.959931),('spin',0)]):
    setattr(state.par, f'const{i}name', name)
    setattr(state.par, f'const{i}value', value)

# A locked point cloud of random seeds; the vertex shader animates every point.
points = scene.create(scriptSOP,'particle_seeds')
points.lock = True
points.clear()
rng = random.Random(20261022)
for i in range(20000):
    p = points.appendPoint()
    p.P = (rng.random(), rng.random(), (i+.5)/20000)
points.display = False

vertex, fragment = textdat('particle_vertex','particles.vert'), textdat('particle_fragment','particles.frag')
material = scene.create(glslMAT,'particle_material')
material.par.vdat, material.par.pdat = vertex, fragment
material.par.blending = True
material.par.srcblend = 'one'
material.par.destblend = 'one'
material.par.depthwriting = False
material.par.depthtest = False
material.seq.vec.numBlocks = 4
material.par.vec0name = 'uMotion'
material.par.vec1name = 'uControl'
material.par.vec2name = 'uView'
material.par.vec3name = 'uProjection'
expressions = {
    'vec0valuex':'absTime.seconds',
    'vec0valuey':"op('state')['expansion'][0]",'vec0valuez':"op('state')['scale'][0]",'vec0valuew':"op('state')['glow'][0]",
    'vec1valuex':"op('state')['x'][0]",'vec1valuey':"op('state')['y'][0]",
    'vec1valuez':"int(op('settings').par.Count.eval())",'vec1valuew':"op('state')['theme'][0]",
    'vec2valuex':"op('state')['yaw'][0]",'vec2valuey':"op('state')['pitch'][0]",
    'vec2valuez':"op('state')['spin'][0]",'vec2valuew':'0',
    'vec3valuex':"op('camera').par.tz.eval()",
    'vec3valuey':"2*op('camera').par.tz.eval()*__import__('math').tan(__import__('math').radians(op('camera').par.fov.eval())/2)",
    'vec3valuez':"2*op('camera').par.tz.eval()*__import__('math').tan(__import__('math').radians(op('camera').par.fov.eval())/2)*720/1280",
    'vec3valuew':'0'}
for name, expression in expressions.items():
    getattr(material.par,name).expr = expression

geo = scene.create(geometryCOMP,'particles')
for child in list(geo.children): child.destroy()
geometry = geo.create(selectSOP,'points')
geometry.par.sop = points
sprites = geo.create(convertSOP,'sprites')
sprites.inputConnectors[0].connect(geometry)
sprites.par.totype = 'particlesperpoint'
sprites.par.prtype = 'pointsprites'
sprites.display = sprites.render = True
geo.par.material = material
camera = scene.create(cameraCOMP,'camera')
camera.par.tz = 7.4
camera.par.fov = 55
render = scene.create(renderTOP,'render')
render.par.camera, render.par.geometry = camera, geo
render.par.lights = ''
render.par.resolutionw, render.par.resolutionh = 1280,720
render.par.format = 'rgba16float'
render.par.bgcolorr,render.par.bgcolorg,render.par.bgcolorb,render.par.bgcolora = .0001,.00015,.00035,1

# Native feedback and bloom provide the temporal trail and glow.
feedback = scene.create(feedbackTOP,'trail_previous')
feedback.inputConnectors[0].connect(render)
level = scene.create(levelTOP,'trail_decay')
level.inputConnectors[0].connect(feedback)
level.par.opacity.expr = "op('settings').par.Trail.eval()"
trail = scene.create(compositeTOP,'trail')
trail.par.operand = 'add'
trail.inputConnectors[0].connect(render)
trail.inputConnectors[1].connect(level)
feedback.par.top = trail
bloom = scene.create(bloomTOP,'glow')
bloom.inputConnectors[0].connect(trail)
bloom.par.bloomintensity.expr = "op('settings').par.Glow.eval() * (1 + op('state')['glow'][0])"
bloom.par.bloomthreshold = .55
nebula_dat=textdat('nebula_fragment','galaxy_nebula.frag')
nebula=scene.create(glslTOP,'nebula')
nebula.par.pixeldat=nebula_dat
nebula.par.outputresolution='custom'
nebula.par.resolutionw,nebula.par.resolutionh=640,360
nebula.par.format='rgba16float'
nebula.seq.vec.numBlocks=4
nebula.par.vec0name,nebula.par.vec1name='uMotion','uControl'
nebula.par.vec2name='uView'
nebula.par.vec3name='uProjection'
for name,expression in expressions.items(): getattr(nebula.par,name).expr=expression
combine_dat=textdat('composite_fragment','galaxy_composite.frag')
combine=scene.create(glslTOP,'galaxy_composite')
combine.par.pixeldat=combine_dat
combine.inputConnectors[0].connect(bloom)
combine.inputConnectors[1].connect(nebula)
combine.par.outputresolution='custom'
combine.par.resolutionw,combine.par.resolutionh=1280,720
combine.par.format='rgba16float'
out = scene.create(nullTOP,'out1')
out.inputConnectors[0].connect(combine)
scene.par.top = out

# A native control panel alongside the full 720p visualization.
view = host.create(containerCOMP,'interface') if not host.op('interface') else host.op('interface')
for child in list(view.children): child.destroy()
view.par.w,view.par.h = 1280,720
canvas = view.create(containerCOMP,'canvas')
canvas.par.w,canvas.par.h = 1000,720
canvas.par.top = out
exec(compile((ROOT/'src/build_controls.py').read_text(encoding='utf-8'),
             'build_controls.py','exec'),globals())
preview = view.create(containerCOMP,'camera_preview')
preview.par.x,preview.par.y,preview.par.w,preview.par.h = 1000,570,280,100
preview.par.top = mp.op('webBrowser1/webrender1')
status = scene.create(textTOP,'status')
status.par.text = '手势银河 / GESTURE GALAXY\n正在初始化…'
status.par.resolutionw,status.par.resolutionh = 280,130
status.par.font = 'Microsoft YaHei'
status.par.fontsizex = 11
status_panel = view.create(containerCOMP,'status')
status_panel.par.x,status_panel.par.y = 1000,0
status_panel.par.w,status_panel.par.h = 280,130
status_panel.par.top = status
title = scene.create(textTOP,'title')
title.par.text = '星团银河 · 手势漫游'
title.par.resolutionw,title.par.resolutionh = 280,50
title.par.font = 'Microsoft YaHei'
title.par.fontsizex = 20
title_panel=view.create(containerCOMP,'title')
title_panel.par.x,title_panel.par.y=1000,670
title_panel.par.w,title_panel.par.h=280,50
title_panel.par.top=title

window = scene.create(windowCOMP,'show')
window.par.winop = view
window.par.title = '手势银河 · MediaPipe × TouchDesigner'
window.par.winw,window.par.winh = 1280,720
window.par.borders = True
window.par.alwaysontop = False

callbacks = scene.create(parameterexecuteDAT,'settings_events')
callbacks.par.op = settings
callbacks.par.pars = '*'
callbacks.par.valuechange = True
callbacks.par.onpulse = True
callbacks.text = '''def onValueChange(par, prev):
    op('runtime').module.setting_changed(par, prev)
def onPulse(par):
    op('runtime').module.pulse(par)
'''
execute = scene.create(executeDAT,'update')
execute.par.start = True
execute.par.framestart = True
execute.text = '''def onStart():
    op('runtime').module.start()
def onFrameStart(frame):
    op('runtime').module.tick()
def onExit():
    op('runtime').module.stop()
'''
runtime.module.start()
for index, child in enumerate(scene.children):
    child.nodeX, child.nodeY = (index % 6)*220, -(index // 6)*160
host.par.w,host.par.h = 1280,720
host.par.top = out
op('/perform').par.winop = view
# Keep the runtime paths relative to the delivered project.
mp.par.externaltox = 'vendor/mediapipe-v0.6.0/toxes/MediaPipe.tox'
(ROOT/'docs/build-complete.json').write_text(json.dumps({'project':str(ROOT/'GestureParticles.toe'),'build':app.build},indent=2),encoding='utf-8')
window.par.winopen.pulse()
exec(compile((ROOT/'src/save_project.py').read_text(encoding='utf-8'),
             'save_project.py', 'exec'), dict(globals()))
