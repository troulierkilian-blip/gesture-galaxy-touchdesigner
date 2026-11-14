"""Frame-rate independent gesture mapping; no TouchDesigner dependency."""
import math
from dataclasses import dataclass


def clamp(value, low=0.0, high=1.0):
    return max(low, min(high, value))


@dataclass
class Hand:
    present: bool = False
    x: float = 0.5
    y: float = 0.5
    pinch: float = 1.0  # thumb-index distance / palm width
    fist: float = 0.0
    palm: float = 0.0
    victory: float = 0.0
    thumb_up: float = 0.0


class GestureControl:
    """h1=left, h2=right. Freshness is required even when CHOPs hold old data."""
    def __init__(self):
        self.reset()

    def reset(self):
        self.x, self.y = 0.5, 0.5
        self.expansion, self.scale, self.glow = 0.45, 1.0, 0.0
        self.theme = 0
        self.pose = "idle"
        self.candidate = "idle"
        self.held = 0.0
        self.victory_held = 0.0
        self.victory_latched = False
        self.cooldown = 0.0
        self.selected = "none"

    def update(self, dt, left=None, right=None, pair_distance=None,
               fresh=True, sensitivity=1.0):
        dt = clamp(dt, 0.0, 0.1)
        left, right = left or Hand(), right or Hand()
        self.cooldown = max(0.0, self.cooldown - dt)
        hand = None
        self.selected = "none"
        if fresh:
            if right.present:
                hand, self.selected = right, "right"
            elif left.present:
                hand, self.selected = left, "left"
        tx, ty, expansion, scale, glow = 0.5, 0.5, 0.45, 1.0, 0.0
        detected_pose = "idle"
        victory = False
        if hand:
            tx = clamp(0.5 + (hand.x - 0.5) * sensitivity, 0.08, 0.92)
            ty = clamp(0.5 + (hand.y - 0.5) * sensitivity, 0.08, 0.92)
            if hand.fist >= 0.65 and hand.fist > hand.palm:
                detected_pose = "fist"
            elif hand.palm >= 0.65:
                detected_pose = "palm"
            else:
                detected_pose = "track"
            # Fists have close fingertips too; avoid falsely brightening a fist.
            if detected_pose != "fist":
                glow = 1.0 - clamp((hand.pinch - 0.18) / 0.55)
            if left.present and right.present and pair_distance is not None:
                scale = clamp(0.5 + pair_distance * 2.4, 0.55, 1.8)
            victory = hand.victory >= 0.7
        if detected_pose == self.candidate:
            self.held += dt
        else:
            self.candidate, self.held = detected_pose, 0.0
        if self.held >= 0.12 or hand is None:
            self.pose = detected_pose
        expansion = {"fist": 0.0, "palm": 1.0}.get(self.pose, 0.45)
        if victory:
            self.victory_held += dt
            if self.victory_held >= 0.25 and not self.victory_latched and self.cooldown <= 0:
                self.theme = (self.theme + 1) % 3
                self.victory_latched, self.cooldown = True, 0.8
        else:
            self.victory_held = 0.0
            self.victory_latched = False
        # Smooth at the same speed at 30 and 60 fps.
        follow = 1.0 - math.exp(-dt / 0.13)
        shape = 1.0 - math.exp(-dt / 0.28)
        for attr, target, rate in (("x", tx, follow), ("y", ty, follow),
                                   ("expansion", expansion, shape),
                                   ("scale", scale, shape), ("glow", glow, follow)):
            setattr(self, attr, getattr(self, attr) + (target - getattr(self, attr)) * rate)
        return self


def hands_from_channels(channels):
    """Read v0.6.0 joint + gesture channels, already in y-up coordinates."""
    def val(key):
        try:
            value = float(channels.get(key, 0.0))
            return value if math.isfinite(value) else 0.0
        except (TypeError, ValueError):
            return 0.0

    def read(prefix):
        present = max(val(prefix + ':Leftness'), val(prefix + ':Rightness')) > 0.5
        if not present:
            return Hand()
        def point(joint):
            return [val(prefix + ':' + joint + ':' + axis) for axis in 'xyz']
        a, b = point('thumb_tip'), point('index_finger_tip')
        p, q = point('index_finger_mcp'), point('pinky_mcp')
        distance = lambda u, v: math.sqrt(sum((x-y)**2 for x, y in zip(u, v)))
        palm_width = max(distance(p, q), 0.025)
        center = [point(j) for j in ('wrist', 'index_finger_mcp', 'middle_finger_mcp', 'ring_finger_mcp', 'pinky_mcp')]
        return Hand(True, sum(p[0] for p in center)/5, sum(p[1] for p in center)/5,
                    distance(a, b)/palm_width,
                    val(prefix + ':Closed_Fist'), val(prefix + ':Open_Palm'),
                    val(prefix + ':Victory'), val(prefix + ':Thumb_Up'))
    return read('h1'), read('h2'), val('h1h2:distance')
