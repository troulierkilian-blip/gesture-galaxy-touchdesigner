import math
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from gesture_control import Hand, hands_from_channels
from orbit_control import OrbitControl


class OrbitTests(unittest.TestCase):
    def setUp(self): self.o=OrbitControl()
    def frame(self,x=.5,y=.5,thumb=0,**kwargs):
        return self.o.update(1/60,right=Hand(True,x,y,thumb_up=thumb),**kwargs)
    def hold(self,seconds,**kwargs):
        for _ in range(round(seconds*60)): self.frame(**kwargs)
    def test_direction_gain_unbounded_yaw_pitch_limits(self):
        self.frame(0,.5);self.frame(1,.5)
        self.assertAlmostEqual(self.o.target_yaw,math.tau)
        self.frame(1,1);self.assertAlmostEqual(self.o.target_pitch,math.radians(80))
        self.frame(1,0);self.assertAlmostEqual(self.o.target_pitch,math.radians(-80))
        self.frame(2,0);self.assertGreater(self.o.target_yaw,math.tau)
    def test_stationary_and_jitter(self):
        self.frame();self.frame(.7)
        self.hold(2,x=.7)
        self.assertAlmostEqual(self.o.yaw,self.o.target_yaw,places=4)
        original=self.o.target_yaw
        for i in range(120): self.frame(.7+(-1)**i*.0005)
        self.assertEqual(original,self.o.target_yaw)
    def test_slow_drag_accumulates(self):
        self.frame()
        for i in range(100):self.frame(.5+i*.0005)
        self.assertGreater(self.o.target_yaw,.28)
    def test_lost_hand_and_owner_switch(self):
        self.frame();self.frame(.6)
        target=self.o.target_yaw
        self.o.update(.1,fresh=False)
        self.frame(.9)
        self.assertEqual(target,self.o.target_yaw)
        self.o.update(.02,left=Hand(True,.1,.1))
        self.assertEqual(target,self.o.target_yaw)
        self.o.update(.02,left=Hand(True,.2,.1))
        self.assertGreater(self.o.target_yaw,target)
    def test_two_hands_pause_and_reanchor(self):
        self.frame();self.frame(.6)
        target=self.o.target_yaw
        self.frame(.9,left=Hand(True,.1,.1))
        self.frame(.2)
        self.assertEqual(target,self.o.target_yaw)
        self.frame(.3)
        self.assertGreater(self.o.target_yaw,target)
    def test_thumb_threshold_hold_latch_release_cooldown(self):
        self.hold(1,thumb=.74);self.assertEqual(self.o.mode,'rotate')
        self.hold(.48,thumb=.75);self.assertEqual(self.o.mode,'rotate')
        self.hold(.02,thumb=.75);self.assertEqual(self.o.mode,'move')
        self.hold(2,thumb=.99);self.assertEqual(self.o.mode,'move')
        self.hold(.1);self.hold(1,thumb=.99);self.assertEqual(self.o.mode,'move')
        self.hold(.2);self.hold(.5,thumb=.99);self.assertEqual(self.o.mode,'rotate')
        self.hold(.2);self.hold(.5,thumb=.99);self.assertEqual(self.o.mode,'rotate')
        self.hold(.31,thumb=.99);self.assertEqual(self.o.mode,'move')
    def test_thumb_freezes_drag_and_reanchors(self):
        self.frame();self.frame(.7,thumb=.99)
        self.assertEqual(self.o.target_yaw,0)
        self.frame(.9);self.assertEqual(self.o.target_yaw,0)
        self.frame(.8);self.assertLess(self.o.target_yaw,0)
    def test_move_mode_idle_center_and_spin(self):
        self.o.set_mode('move');self.hold(2,center=(.8,.3))
        self.assertAlmostEqual(self.o.x,.8,places=4)
        self.assertEqual(self.o.spin,0)
        angle=self.o.yaw
        for _ in range(120): self.o.update(1/60)
        self.assertAlmostEqual(self.o.x,.5,places=4)
        self.assertEqual(self.o.yaw,angle);self.assertGreater(self.o.spin,0)
    def test_mode_change_and_reset(self):
        self.frame();self.frame(.9)
        self.o.set_mode('move');self.frame(.1)
        target=self.o.target_yaw
        self.o.set_mode('rotate');self.frame(.8)
        self.assertEqual(target,self.o.target_yaw)
        self.o.reset_view();self.hold(2,x=.8)
        self.assertAlmostEqual(self.o.pitch,math.radians(55),places=4)
        self.assertAlmostEqual(self.o.yaw,0,places=4)
    def test_thumb_channel_parser(self):
        left,right,_=hands_from_channels({'h2:Rightness':.99,'h2:Thumb_Up':.88})
        self.assertFalse(left.present);self.assertEqual(right.thumb_up,.88)
    def test_fps_independent(self):
        outcomes=[]
        for hz in (30,60,120):
            orbit=OrbitControl();orbit.target_yaw=1
            for _ in range(hz): orbit.update(1/hz)
            outcomes.append(orbit.yaw)
        self.assertAlmostEqual(outcomes[0],outcomes[2],places=10)

if __name__=='__main__':unittest.main()
