"""Exercise the embedded driver with synthetic hands; never label as real input."""
import json
import math
from pathlib import Path
injected=(None,None)
original=None
results=[]
before=0

def hand(x=.5,y=.5,thumb=0):
    return op('gesture_control').module.Hand(True,x,y,thumb_up=thumb)

def input_pair():return injected

def start():
    global original,results
    results=[]
    rt=op('runtime').module
    original=rt._simulated_input
    rt._simulated_input=input_pair
    rt.orbit=op('orbit_control').module.OrbitControl()
    op('settings').par.Mode='mouse'
    op('settings').par.Interactionmode='rotate'
    step(0)

def step(i):
    global injected,before
    rt=op('runtime').module
    before=rt.orbit.target_yaw
    pairs=[(None,hand(.2,.4)),(None,hand(.7,.5)),(None,hand(.7,.5)),
        (None,hand(.8,.7,.99)),(None,hand(.8,.7,.99)),(None,hand()),
        (None,hand(.1,.3,.99)),(hand(.1,.1),hand(.9,.9)),
        (None,hand(.1,.1)),(None,hand(.3,.1)),(None,None),
        (hand(.8,.1),None),(hand(.7,.1),None),(None,None)]
    injected=pairs[i]
    if i==13:op('settings').par.Resetview.pulse()
    run("op('/project1/scene/orbit_validation').module.check(%d)"%i,delayFrames=90)

def check(i):
    o=op('runtime').module.orbit
    checks=[abs(o.target_yaw)<1e-5,abs(o.target_yaw-math.pi)<1e-5,
        abs(o.yaw-o.target_yaw)<.001,o.mode=='move',o.mode=='move',o.mode=='move',
        o.mode=='rotate',abs(o.target_yaw-before)<1e-5,abs(o.target_yaw-before)<1e-5,
        o.target_yaw>before,o.owner=='none',abs(o.target_yaw-before)<1e-5,
        o.target_yaw<before,abs(o.pitch-math.radians(55))<.001]
    results.append(dict(case=i,mode=o.mode,owner=o.owner,yaw=o.yaw,pitch=o.pitch,passed=checks[i]))
    if i+1<14:step(i+1)
    else:
        rt=op('runtime').module
        rt._simulated_input=original
        rt.orbit=op('orbit_control').module.OrbitControl()
        op('settings').par.Mode='camera'
        op('settings').par.Interactionmode='rotate'
        (Path(project.folder)/'docs/enhanced-orbit-integration.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
