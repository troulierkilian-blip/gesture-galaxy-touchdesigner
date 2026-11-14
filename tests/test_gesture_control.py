import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from gesture_control import GestureControl, Hand, hands_from_channels


def advance(control, seconds=1, **kwargs):
    for _ in range(round(seconds * 60)):
        control.update(1 / 60, **kwargs)
    return control


class ControlTests(unittest.TestCase):
    def test_right_priority_and_left_fallback(self):
        c = advance(GestureControl(), left=Hand(True, x=.2), right=Hand(True, x=.8))
        self.assertGreater(c.x, .75)
        c = advance(c, left=Hand(True, x=.2))
        self.assertLess(c.x, .25)
        self.assertEqual(c.selected, 'left')

    def test_fist_and_palm(self):
        c = advance(GestureControl(), right=Hand(True, fist=.95))
        self.assertLess(c.expansion, .05)
        c = advance(c, right=Hand(True, palm=.95))
        self.assertGreater(c.expansion, .94)

    def test_pinch_only_changes_glow(self):
        c = advance(GestureControl(), right=Hand(True, pinch=.05))
        self.assertGreater(c.glow, .95)
        self.assertEqual(c.scale, 1.)

    def test_two_hands_scale(self):
        c = advance(GestureControl(), left=Hand(True), right=Hand(True), pair_distance=.5)
        self.assertGreater(c.scale, 1.6)

    def test_victory_does_not_repeat_while_held(self):
        c = advance(GestureControl(), 3, right=Hand(True, victory=.95))
        self.assertEqual(c.theme, 1)
        advance(c, right=Hand(True))
        advance(c, right=Hand(True, victory=.95))
        self.assertEqual(c.theme, 2)

    def test_brief_victory_does_not_switch(self):
        c = advance(GestureControl(), .15, right=Hand(True, victory=.95))
        self.assertEqual(c.theme, 0)

    def test_stale_camera_returns_to_idle(self):
        c = advance(GestureControl(), right=Hand(True, x=.9, fist=.95))
        advance(c, 2, right=Hand(True, x=.9, fist=.95), fresh=False)
        self.assertEqual(c.pose, 'idle')
        self.assertAlmostEqual(c.x, .5, places=3)
        self.assertAlmostEqual(c.expansion, .45, places=3)

    def test_missing_and_nonfinite_channels(self):
        a, b, distance = hands_from_channels({'h1:Leftness': float('nan')})
        self.assertFalse(a.present)
        self.assertFalse(b.present)
        self.assertEqual(distance, 0)

    def test_frame_rate_independence(self):
        a, b = GestureControl(), GestureControl()
        for _ in range(30): a.update(1/30, right=Hand(True, x=.8))
        for _ in range(60): b.update(1/60, right=Hand(True, x=.8))
        self.assertAlmostEqual(a.x, b.x, places=6)


if __name__ == '__main__':
    unittest.main()
