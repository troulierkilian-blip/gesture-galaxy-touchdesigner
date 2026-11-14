"""Check the generated file survives TouchDesigner's numbered-save behavior."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

SOURCE = (Path(__file__).resolve().parents[1]/'src/save_project.py').read_text(encoding='utf-8')


class ProjectSaveTests(unittest.TestCase):
    def run_save(self, root, fail=False):
        boot = SimpleNamespace(par=SimpleNamespace(active=SimpleNamespace(eval=lambda:True)))
        ui = SimpleNamespace(preferences={'general.saveprompt':1})
        project = SimpleNamespace(folder=str(root), name='GestureParticles.1.toe')

        def save(requested):
            self.assertFalse(boot.par.active)
            if fail:
                raise RuntimeError('simulated save failure')
            (root/project.name).write_bytes(b'new scene; mailbox disabled')

        project.save = save
        try:
            exec(compile(SOURCE, 'save_project.py', 'exec'),
                 dict(ROOT=root,op=lambda _:boot,ui=ui,project=project))
        finally:
            self.assertTrue(boot.par.active)
            self.assertEqual(ui.preferences['general.saveprompt'],1)

    def test_numbered_save_updates_launcher_file_and_keeps_backups(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'GestureParticles.toe').write_bytes(b'previous scene')
            (root/'GestureParticles.1.toe').write_bytes(b'previous numbered scene')
            self.run_save(root)
            self.assertEqual((root/'GestureParticles.toe').read_bytes(),b'new scene; mailbox disabled')
            self.assertEqual({p.read_bytes() for p in (root/'build/backups').iterdir()},
                             {b'previous scene',b'previous numbered scene'})

    def test_failed_save_keeps_previous_scene_recoverable(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'GestureParticles.toe').write_bytes(b'previous scene')
            with self.assertRaisesRegex(RuntimeError,'simulated save failure'):
                self.run_save(root,fail=True)
            self.assertEqual([p.read_bytes() for p in (root/'build/backups').iterdir()],
                             [b'previous scene'])
