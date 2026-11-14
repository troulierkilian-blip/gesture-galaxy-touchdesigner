"""Run inside an Execute DAT, with project folder = project root/build."""
import os
import traceback
from pathlib import Path

ROOT = Path(project.folder).parent if Path(project.folder).name == 'build' else Path(project.folder)
_last_action = 0


def onStart():
    run("op('/project1/bootstrap').module.build()", delayFrames=10)


def build():
    try:
        namespace = dict(globals(), ROOT=ROOT)
        exec(compile((ROOT/'src/build_scene.py').read_text(encoding='utf-8'), 'build_scene.py', 'exec'), namespace)
    except Exception:
        (ROOT/'docs/build-error.log').write_text(traceback.format_exc(), encoding='utf-8')
        raise


def onFrameStart(frame):
    global _last_action
    # Development-only, local file mailbox. Disabled in the final saved project.
    path = ROOT/'build/action.py'
    if path.exists() and path.stat().st_mtime_ns != _last_action:
        _last_action = path.stat().st_mtime_ns
        try:
            exec(compile(path.read_text(encoding='utf-8'), str(path), 'exec'), dict(globals()))
        except Exception:
            (ROOT/'docs/action-error.log').write_text(traceback.format_exc(), encoding='utf-8')


def onCreate(): pass
def onExit(): pass
def onFrameEnd(frame): pass
def onPlayStateChange(state): pass
def onDeviceChange(): pass
def onProjectPreSave(): pass
def onProjectPostSave(): pass
