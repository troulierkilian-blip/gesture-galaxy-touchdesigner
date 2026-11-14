"""Exercise actual native panel-click events, not just the action function."""
import json
from pathlib import Path
cases=[('Mode_plus','Mode','mouse'),('Mode_plus','Mode','camera'),
       ('Interactionmode_plus','Interactionmode','move'),('Interactionmode_plus','Interactionmode','rotate'),
       ('Rotationsensitivity_minus','Rotationsensitivity',.9),('Rotationsensitivity_plus','Rotationsensitivity',1.),
       ('Resetview_plus','Interactionmode','rotate'),('Camera_plus','Mode','camera'),
       ('Reconnect_plus','Mode','camera'),
       ('Glow_minus','Glow',.27),('Glow_plus','Glow',.32),
       ('Count_plus','Count','5000'),('Count_plus','Count','10000'),
       ('Count_plus','Count','20000'),('Palette_plus','Palette','cyan'),
       ('Palette_plus','Palette','gold'),('Palette_plus','Palette','violet')]
results=[]

def start():
    global results
    results=[]
    settings=op('settings')
    settings.par.Mode='camera'
    settings.par.Interactionmode='rotate'
    settings.par.Rotationsensitivity=1
    settings.par.Glow=.32
    settings.par.Count='20000'
    settings.par.Palette=0
    begin(0)

def begin(index):
    button=op('../interface/controls/'+cases[index][0])
    button.click(.5,.5)
    run("op('/project1/scene/ui_validation').module.check(%d)"%index,delayFrames=30)

def check(index):
    button,name,expected=cases[index]
    actual=getattr(op('settings').par,name).eval()
    passed=abs(actual-expected)<.001 if isinstance(expected,float) else actual==expected
    results.append(dict(button=button,actual=actual,expected=expected,passed=passed))
    if index+1<len(cases): begin(index+1)
    else:
        (Path(project.folder)/'docs/enhanced-ui-checks.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
        op('control_text').save(str(Path(project.folder)/'docs/enhanced-controls.png'))
