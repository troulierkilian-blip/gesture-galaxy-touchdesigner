"""Relative hand dragging, independent of TouchDesigner and gesture effects.

Angles are radians. Pitch is the actual disk tilt (55 degrees at reset).
An anchor is invalidated at every ownership boundary, never transferred.
"""
import math


class OrbitControl:
    def __init__(self):
        self.mode = 'rotate'
        self.yaw = self.target_yaw = 0.0
        self.pitch = self.target_pitch = math.radians(55)
        self.spin = 0.0
        self.x = self.y = .5
        self.anchor = None
        self.owner = 'none'
        self.thumb_held = self.release_held = self.cooldown = 0.0
        self.thumb_latched = False
        self.thumb_score = 0.0
        self.two_hands = self.switch_pending = False

    def set_mode(self, mode):
        if mode not in ('rotate', 'move'):
            raise ValueError(mode)
        if mode != self.mode:
            self.mode = mode
            self.anchor = None

    def reset_view(self):
        # Return by the shortest route, including after multiple revolutions.
        self.target_yaw = round(self.yaw / math.tau) * math.tau
        self.target_pitch = math.radians(55)
        self.anchor = None

    def update(self, dt, left=None, right=None, fresh=True, sensitivity=1.0,
               center=(.5, .5)):
        dt = max(0., min(.1, dt))
        self.cooldown = max(0., self.cooldown - dt)
        lp = bool(fresh and left and left.present)
        rp = bool(fresh and right and right.present)
        hand = right if rp else left if lp else None
        owner = 'right' if rp else 'left' if lp else 'none'
        self.two_hands = lp and rp
        if owner != self.owner:
            self.anchor = None
            # A different hand must complete its own continuous hold.
            self.thumb_held = 0.0
        self.owner = owner
        self.thumb_score = hand.thumb_up if hand else 0.0
        thumb = self.thumb_score >= .75
        self.switch_pending = thumb
        if thumb:
            self.release_held = 0.0
            self.thumb_held += dt
            if self.thumb_held + 1e-9 >= .5 and not self.thumb_latched and self.cooldown <= 0:
                self.set_mode('move' if self.mode == 'rotate' else 'rotate')
                self.thumb_latched = True
                self.cooldown = 1.0
        else:
            self.thumb_held = 0.0
            self.release_held += dt
            if self.release_held + 1e-9 >= .2:
                self.thumb_latched = False

        dragging = hand and self.mode == 'rotate' and not self.two_hands and not thumb
        if dragging:
            position = (float(hand.x), float(hand.y))
            if not all(math.isfinite(v) for v in position):
                self.anchor = None
            elif self.anchor is None:
                self.anchor = position
            else:
                dx, dy = position[0] - self.anchor[0], position[1] - self.anchor[1]
                # Keep the anchor until movement exceeds jitter: slow dragging
                # accumulates instead of disappearing in a per-frame deadzone.
                if math.hypot(dx, dy) >= .002:
                    gain = max(.4, min(2., sensitivity))
                    self.target_yaw += dx * math.tau * gain
                    limit = math.radians(80)
                    self.target_pitch = max(-limit, min(limit,
                        self.target_pitch + dy * math.pi * gain))
                    self.anchor = position
        else:
            self.anchor = None

        a = 1. - math.exp(-dt / .15)
        self.yaw += (self.target_yaw - self.yaw) * a
        self.pitch += (self.target_pitch - self.pitch) * a
        if hand is None:
            self.spin = (self.spin + dt * .025) % math.tau
            tx, ty = .5, .5
        elif self.mode == 'move':
            tx, ty = center
        else:
            tx, ty = self.x, self.y
        self.x += (tx - self.x) * a
        self.y += (ty - self.y) * a
        return self
