"""Run inside a temporary Text DAT in the scene, after GPU startup."""
import json
import time
from pathlib import Path

cases = [('track',1),('fist',1),('palm',1),('pinch',1),('victory',1),
         ('victory',1),('track',1),('victory',1),('track',.55),('track',1.8)]
results = []
previous_mode = 'camera'
previous_enabled = True
case_started = 0.0

def start():
    global previous_mode, previous_enabled, results
    results=[]
    previous_mode=op('settings').par.Mode.eval()
    previous_enabled=op('../interface/canvas').par.enable.eval()
    op('../interface/canvas').par.enable=False
    op('runtime').module.controller.reset()
    op('settings').par.Mode = 'mouse'
    begin(0)

def begin(i):
    global case_started
    case_started = time.monotonic()
    pose, scale = cases[i]
    op('settings').par.Simpose = pose
    op('settings').par.Simscale = scale
    run("op('/project1/scene/native_validation').module.check(%d)" % i, delayFrames=5)

def check(i):
    c = op('runtime').module.controller
    data = {key:getattr(c,key) for key in ('pose','expansion','scale','glow','theme')}
    checks = [c.pose=='track', c.expansion<.02, c.expansion>.98, c.glow>.98,
              c.theme==1, c.theme==1, c.theme==1, c.theme==2,
              abs(c.scale-.55)<.01, abs(c.scale-1.8)<.01]
    elapsed = time.monotonic() - case_started
    # The controller smooths by real elapsed time (and caps long frame gaps).
    # Timeline frames can advance without 100 driver updates. Keep the original
    # thresholds, require a normal settling interval, and fail after 3 seconds.
    if elapsed < 1.4 or (not checks[i] and elapsed < 3.0):
        run("op('/project1/scene/native_validation').module.check(%d)" % i, delayFrames=5)
        return
    data.update(case=i,gesture=cases[i][0],settling_seconds=round(elapsed,3),passed=checks[i])
    results.append(data)
    if i in (0,1,2,3,4,7):
        op('out1').save(str(Path(project.folder)/'docs'/('enhanced-simulation-'+str(i)+'-'+cases[i][0]+'.png')))
    if i+1<len(cases):
        begin(i+1)
    else:
        (Path(project.folder)/'docs/enhanced-native-checks.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
        op('settings').par.Simpose='track'
        op('settings').par.Simscale=1
        op('settings').par.Palette=0
        op('runtime').module.controller.reset()
        op('settings').par.Mode=previous_mode
        op('../interface/canvas').par.enable=previous_enabled
