"""Benchmark evidence must describe the live graph and the current run."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


SOURCE = Path(__file__).resolve().parents[1]/'src/td_runtime.py'


class Parameter:
    def __init__(self, value): self.value = value
    def eval(self): return self.value


class RuntimeMetadataTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('runtime_metadata_under_test', SOURCE)
        self.runtime = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.runtime)
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.nodes = {
            'settings': SimpleNamespace(par=SimpleNamespace(**{
                name:Parameter(value) for name,value in {
                    'Mode':'camera','Count':'20000','Trail':.08,'Glow':.32}.items()})),
            'MediaPipe': SimpleNamespace(par=SimpleNamespace(Webcam=Parameter('Test Camera (USB)'))),
            'out1': SimpleNamespace(width=1280,height=720,cookAbsFrame=100),
            'nebula': SimpleNamespace(width=640,height=360,cookAbsFrame=100),
            'render': SimpleNamespace(cookAbsFrame=100),
            'MediaPipe/hand_results': SimpleNamespace(cookAbsFrame=100),
            'nebula_fragment': SimpleNamespace(text='const int VOLUME_STEPS=16;'),
        }
        self.runtime.op = self.nodes.get
        self.runtime.project = SimpleNamespace(folder=str(self.root))
        self.runtime.absTime = SimpleNamespace(frame=100)
        self.runtime.controller = SimpleNamespace(selected='right',pose='track')
        self.runtime._fps = 60.

    def tearDown(self):
        if self.runtime._benchmark:
            self.runtime.stop()
        self.directory.cleanup()

    def advance_frames(self, count=60):
        for node in self.nodes.values():
            if hasattr(node,'cookAbsFrame'): node.cookAbsFrame += count
        self.runtime.absTime.frame += count

    def summary(self, name='metadata'):
        return json.loads((self.root/'docs'/('benchmark-'+name+'.json')).read_text(encoding='utf-8'))

    def sample_at(self, elapsed, fresh=True):
        self.advance_frames()
        self.runtime._sample_benchmark(self.runtime._benchmark['start']+elapsed, fresh)

    def test_steps_read_live_shader_and_ignore_comments(self):
        self.nodes['nebula_fragment'].text = '''
        // const int VOLUME_STEPS=12;
        /* const int VOLUME_STEPS=24; */
        const int VOLUME_STEPS = 16;
        '''
        result = self.runtime._benchmark_configuration()
        self.assertEqual(result['nebula_steps'],16)
        self.assertEqual(result['metadata_diagnostics'],[])
        self.nodes['nebula_fragment'].text = 'const int VOLUME_STEPS=8;'
        self.assertEqual(self.runtime._benchmark_configuration()['nebula_steps'],8)
        self.assertNotEqual(result['nebula_shader_sha256'],self.runtime._benchmark_configuration()['nebula_shader_sha256'])

    def test_unknown_steps_are_null_with_diagnostic_never_guessed(self):
        for source in ('', 'const int VOLUME_STEPS=QUALITY;',
                       'const int VOLUME_STEPS=0;',
                       'const int VOLUME_STEPS=12; const int VOLUME_STEPS=16;'):
            with self.subTest(source=source):
                self.nodes['nebula_fragment'].text = source
                result = self.runtime._benchmark_configuration()
                self.assertIsNone(result['nebula_steps'])
                self.assertTrue(result['metadata_diagnostics'])
        del self.nodes['nebula_fragment']
        result = self.runtime._benchmark_configuration()
        self.assertIsNone(result['nebula_steps'])
        self.assertTrue(result['metadata_diagnostics'])

    def test_actual_graph_quality_configuration_is_reported(self):
        self.nodes['settings'].par.Count.value = '10000'
        self.nodes['settings'].par.Trail.value = .05
        self.nodes['settings'].par.Glow.value = .27
        self.nodes['nebula'].width,self.nodes['nebula'].height = 512,288
        self.nodes['nebula_fragment'].text = 'const int VOLUME_STEPS=12;'
        result = self.runtime._benchmark_configuration()
        self.assertEqual(result['particles'],10000)
        self.assertEqual(result['trail'],.05)
        self.assertEqual(result['glow'],.27)
        self.assertEqual(result['camera'],'Test Camera (USB)')
        self.assertEqual(result['output_resolution'],[1280,720])
        self.assertEqual(result['nebula_resolution'],[512,288])
        self.assertEqual(result['nebula_steps'],12)

    def test_restart_archives_previous_evidence_and_immediately_marks_running(self):
        docs = self.root/'docs'
        docs.mkdir()
        (docs/'benchmark-metadata.json').write_text('{"status":"completed","min_fps":60}',encoding='utf-8')
        (docs/'benchmark-metadata.csv').write_text('old samples',encoding='utf-8')
        self.runtime.begin_benchmark(2,'metadata')
        current = self.summary()
        self.assertEqual(current['status'],'running')
        self.assertEqual(current['samples'],0)
        self.assertFalse(current['at_least_30fps'])
        self.assertFalse(current['valid_completed_run'])
        archived = docs/'benchmark-history'/current['run_id']
        self.assertEqual(json.loads((archived/'benchmark-metadata.json').read_text())['status'],'completed')
        self.assertEqual((archived/'benchmark-metadata.csv').read_text(),'old samples')

    def test_completed_run_has_actual_frames_and_fresh_coverage(self):
        self.runtime.begin_benchmark(2,'metadata')
        self.sample_at(1)
        self.assertEqual(self.summary()['status'],'running')
        self.sample_at(2)
        result = self.summary()
        self.assertIsNone(self.runtime._benchmark)
        self.assertEqual(result['status'],'completed')
        self.assertEqual(result['samples'],2)
        self.assertEqual(result['input_fresh_fraction'],1.)
        self.assertEqual(result['camera_fresh_fraction'],1.)
        self.assertEqual(result['frame_evidence_start']['render'],100)
        self.assertEqual(result['frame_evidence_end']['output'],220)
        self.assertEqual(result['frame_advanced_samples']['render'],2)
        self.assertTrue(result['valid_completed_run'])
        self.assertTrue(result['at_least_30fps'])
        csv = (self.root/'docs/benchmark-metadata.csv').read_text()
        self.assertIn('render_cook_abs_frame',csv)
        self.assertIn(result['run_id'],csv)

    def test_config_change_and_stale_camera_prevent_valid_completed_claim(self):
        self.runtime.begin_benchmark(2,'metadata')
        self.sample_at(1)
        self.nodes['settings'].par.Count.value = '10000'
        self.nodes['settings'].par.Trail.value = .05
        self.sample_at(2,False)
        result = self.summary()
        self.assertEqual(result['status'],'completed')
        self.assertEqual(result['particles'],10000)
        self.assertEqual(result['configuration_at_start']['particles'],20000)
        self.assertEqual(len(result['configuration_changes']),1)
        self.assertFalse(result['configuration_unchanged'])
        self.assertEqual(result['camera_fresh_fraction'],.5)
        self.assertFalse(result['valid_completed_run'])

    def test_frozen_renderer_does_not_pass_even_with_fast_loop(self):
        self.runtime.begin_benchmark(1,'metadata')
        self.runtime._sample_benchmark(self.runtime._benchmark['start']+1,True)
        result = self.summary()
        self.assertEqual(result['frame_stalled_samples']['render'],1)
        self.assertEqual(result['min_fps'],60)
        self.assertFalse(result['valid_completed_run'])

    def test_manual_stop_cannot_claim_completed_performance(self):
        self.runtime.begin_benchmark(600,'metadata')
        self.sample_at(1)
        with patch.object(self.runtime.time,'monotonic',return_value=self.runtime._benchmark['start']+1.5):
            self.runtime.stop()
        result = self.summary()
        self.assertEqual(result['status'],'stopped')
        self.assertEqual(result['duration_seconds'],1.5)
        self.assertFalse(result['at_least_30fps'])
        self.assertFalse(result['valid_completed_run'])


if __name__ == '__main__': unittest.main()
