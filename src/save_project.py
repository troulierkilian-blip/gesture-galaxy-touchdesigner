"""Save our generated project with the developer mailbox disabled.

Executed inside TouchDesigner by the builder/finalizer. TouchDesigner can add
an increment to the requested filename; retain that save and also refresh the
stable filename used by the launcher. Previous generated files are backed up.
"""
from pathlib import Path
from shutil import copy2
from time import time_ns

target = Path(ROOT)/'GestureParticles.toe'
backup = Path(ROOT)/'build/backups'
backup.mkdir(parents=True, exist_ok=True)
stamp = str(time_ns())
boot = op('/project1/bootstrap')
was_active = boot.par.active.eval()
save_prompt = ui.preferences['general.saveprompt']
boot.par.active = False
try:
    for name in ('GestureParticles.toe', 'GestureParticles.1.toe'):
        previous = Path(ROOT)/name
        if previous.is_file():
            previous.rename(backup/(stamp+'-'+name))
    ui.preferences['general.saveprompt'] = 0
    project.save(str(target))
    saved = Path(project.folder)/project.name
    if saved.resolve() != target.resolve() and saved.is_file():
        copy2(saved, target)
    if not target.is_file():
        raise RuntimeError('TouchDesigner did not create the expected project file')
finally:
    ui.preferences['general.saveprompt'] = save_prompt
    boot.par.active = was_active
