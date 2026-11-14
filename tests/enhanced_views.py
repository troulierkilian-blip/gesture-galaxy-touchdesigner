"""Deterministic native GPU captures; load as scene/view_validation and start().

These are render scenarios, not evidence of real gesture recognition. Restore
the previous state, runtime update switch and time expressions on completion.
"""
import json
import math
import traceback
from pathlib import Path

BASE = [.5, .5, .45, 1., 0., 0., 0., 0., math.radians(55), 0.]
CASES = [
    ('front', {7: 0., 8: 0.}),
    ('oblique', {}),
    ('side', {7: math.pi / 2, 8: 0.}),
    ('back', {7: math.pi, 8: 0.}),
    ('fist', {2: 0.}),
    ('palm', {2: 1.}),
    ('pinch', {4: 1.}),
    ('palette-violet', {5: 0.}),
    ('palette-cyan', {5: 1.}),
    ('palette-gold', {5: 2.}),
    ('move', {0: .64, 1: .57}),
    ('scale-small', {3: .55}),
    ('scale-large', {3: 1.8}),
    ('foreground-clusters', {7: math.radians(225), 8: math.radians(-35)}),
    ('camera-crossing-cluster', {2: 1., 3: 1.8, 7: math.pi/2, 8: 0.}),
]
results = []
saved = {}
sweep_errors = []


def later(function, argument, frames=30):
    run("op('/project1/scene/view_validation').module.%s(%d)" %
        (function, argument), delayFrames=frames)


def restore():
    if not saved:
        return
    for i, value in enumerate(saved['state']):
        getattr(op('state').par, 'const%dvalue' % i).val = value
    for node_name, (expression, mode, value) in saved['time'].items():
        par = op(node_name).par.vec0valuex
        par.val = value
        par.expr = expression
        par.mode = mode
    op('trail_previous').par.resetpulse.pulse()
    op('update').par.active = saved['update']


def finish(error=None):
    try:
        if error:
            results.append({'view': 'test_execution', 'passed': False,
                            'error': error})
        record = {
            'kind': 'deterministic_native_render',
            'resolution': [op('out1').width, op('out1').height],
            'particles': int(op('settings').par.Count.eval()),
            'nebula_resolution': [op('nebula').width, op('nebula').height],
            'trail': op('settings').par.Trail.eval(),
            'glow': op('settings').par.Glow.eval(),
            'fixed_time_seconds': 42.,
            'checks': results,
            'passed': bool(results) and all(row['passed'] for row in results),
            'visual_judgement': 'Screenshots require human review; no operator errors alone do not establish visual quality.',
        }
        (Path(project.folder) / 'docs/enhanced-view-checks.json').write_text(
            json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    finally:
        restore()


def start():
    global saved, results, sweep_errors
    results, sweep_errors = [], []
    saved = {
        'state': [getattr(op('state').par, 'const%dvalue' % i).eval()
                  for i in range(10)],
        'update': op('update').par.active.eval(),
        'time': {},
    }
    try:
        op('update').par.active = False
        for name in ('particle_material', 'nebula'):
            par = op(name).par.vec0valuex
            saved['time'][name] = (par.expr, par.mode, par.eval())
            par.mode = ParMode.CONSTANT
            par.val = 42.
        begin(0)
    except Exception:
        finish(traceback.format_exc())


def begin(index):
    try:
        values = BASE.copy()
        for i, value in CASES[index][1].items():
            values[i] = value
        for i, value in enumerate(values):
            getattr(op('state').par, 'const%dvalue' % i).val = value
        op('trail_previous').par.resetpulse.pulse()
        later('check', index)
    except Exception:
        finish(traceback.format_exc())


def check(index):
    try:
        name = CASES[index][0]
        filename = 'enhanced-view-' + name + '.png'
        op('out1').save(str(Path(project.folder) / 'docs' / filename))
        errors = parent().errors(recurse=True)
        values = [getattr(op('state').par, 'const%dvalue' % i).eval()
                  for i in range(10)]
        results.append({'view': name, 'state': values, 'screenshot': filename,
                        'errors': errors, 'warnings': parent().warnings(recurse=True),
                        'passed': not errors})
        if index + 1 < len(CASES):
            begin(index + 1)
        else:
            for i, value in enumerate(BASE):
                getattr(op('state').par, 'const%dvalue' % i).val = value
            sweep(0)
    except Exception:
        finish(traceback.format_exc())


def sweep(index):
    try:
        errors = parent().errors(recurse=True)
        if errors:
            sweep_errors.append({'step': index, 'errors': errors})
        if index <= 72:
            op('state').par.const7value = index * math.tau / 72
            later('sweep', index + 1, frames=2)
        else:
            results.append({'view': 'continuous_360', 'steps': 73,
                            'errors': sweep_errors, 'passed': not sweep_errors})
            finish()
    except Exception:
        finish(traceback.format_exc())
