"""Night Shift cinematic layer: virtual camera, foreground depth layer and film grade.

Used by render.py. Every scene is drawn through `camera()` (moves, handheld, punch-ins,
impact shake), then `foreground()` adds out-of-focus particles with parallax, and
`grade()` runs the colour pipeline on the finished frame (bloom, halation, filmic tone
curve, split-tone look per location, saturation, chromatic aberration, vignette, grain).
"""
import math, random
import numpy as np
import cv2

PI = math.pi


def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def smooth(x): x = clamp(x); return x * x * (3 - 2 * x)
def ease_out(x): x = clamp(x); return 1 - (1 - x) ** 3


# ---------------------------------------------------------------- looks
# shadow / highlight tints are BGR offsets; sat = saturation, con = contrast,
# exp = exposure, bloom = (threshold, strength), hal = halation strength
LOOKS = {
    'noir_amber': dict(shadow=(0.050, 0.022, -0.004), high=(-0.035, 0.010, 0.045), sat=1.18, con=1.26, exp=1.00, bloom=(0.52, 0.75), hal=0.30),
    'sodium':     dict(shadow=(0.055, 0.025, -0.008), high=(-0.045, 0.020, 0.055), sat=1.22, con=1.28, exp=1.02, bloom=(0.50, 0.80), hal=0.30),
    'sickly':     dict(shadow=(0.040, 0.030, -0.006), high=(-0.010, 0.030, -0.015), sat=0.92, con=1.24, exp=1.02, bloom=(0.55, 0.60), hal=0.15),
    'teal_night': dict(shadow=(0.060, 0.030, -0.010), high=(-0.020, 0.020, 0.030), sat=1.12, con=1.26, exp=1.00, bloom=(0.50, 0.75), hal=0.25),
    'paper':      dict(shadow=(0.010, 0.010, 0.020), high=(-0.020, 0.005, 0.020), sat=1.00, con=1.22, exp=0.95, bloom=(0.70, 0.35), hal=0.10),
    'cctv':       dict(shadow=(0.000, 0.015, 0.000), high=(0.000, 0.000, 0.000), sat=1.00, con=1.19, exp=0.95, bloom=(0.60, 0.40), hal=0.00),
    'title':      dict(shadow=(0.030, 0.010, 0.000), high=(0.000, 0.000, 0.020), sat=1.05, con=1.22, exp=0.90, bloom=(0.45, 0.90), hal=0.30),
}
SCENE_LOOK = {
    # motel
    'exterior': 'noir_amber', 'desk': 'noir_amber', 'keys': 'noir_amber', 'hall': 'noir_amber', 'behind': 'noir_amber',
    'room': 'noir_amber', 'room_phone': 'noir_amber', 'desk_other': 'noir_amber',
    # bus
    'road': 'teal_night', 'bus': 'teal_night', 'mirror': 'teal_night', 'sign': 'teal_night', 'stop': 'teal_night', 'dawn': 'noir_amber',
    # hospital
    'nurse_station': 'sickly', 'hosp_hall': 'sickly', 'patient_room': 'sickly', 'monitor': 'sickly', 'hosp_ext': 'teal_night',
    # gas station
    'gas_ext': 'sodium', 'store': 'sodium', 'cctv': 'cctv',
    # inserts
    'news': 'paper', 'book': 'paper', 'logbook': 'paper', 'ticket': 'paper', 'title': 'title',
}
RAINY = {'exterior', 'road', 'gas_ext', 'hosp_ext', 'stop', 'sign'}
INTERIOR_DUST = {'desk', 'keys', 'room', 'room_phone', 'desk_other', 'store', 'nurse_station', 'patient_room', 'hall', 'hosp_hall', 'bus', 'mirror'}
NO_CAMERA = {'title'}

# camera moves, cycled through scenes so consecutive shots never repeat
MOVES = ['push', 'truck_r', 'crane_down', 'pull', 'truck_l', 'arc']


class Cinema:
    def __init__(self, TM, W, H, FPS):
        self.W, self.H, self.FPS = W, H, FPS
        self.TM = TM
        self.total = TM['total']
        scenes = TM['scenes']
        self.scene_index = {id(s): i for i, s in enumerate(scenes)}
        self.moves = {i: MOVES[i % len(MOVES)] for i in range(len(scenes))}
        # line starts for dialogue punch-ins (not the narrator)
        self.punch = [(l['start'], l['start'] + l['dur']) for l in TM['lines']
                      if l['who'] not in ('narrator', 'none') and l.get('dur', 0) > 0]
        # impacts: thunder, sfx stings/knocks/slams, the title sting
        imp = [(t, 0.9) for t in TM.get('thunder', [])]
        for l in TM['lines']:
            for sx in l.get('sfx', []):
                if any(k in sx for k in ('sting', 'knock', 'slam', 'bang', 'crash', 'scream')):
                    imp.append((l['start'] - 0.05, 0.7 if 'soft' not in sx else 0.35))
        title = [s for s in scenes if s['id'] == 'title']
        if title: imp.append((title[0]['start'], 0.6))
        self.impacts = sorted(imp)
        self.cuts = [s['start'] for s in scenes[1:]]
        self._prep_grade()
        rnd = random.Random(7)
        self.bokeh = [(rnd.uniform(-200, W + 200), rnd.uniform(-200, H + 200), rnd.uniform(40, 120), rnd.uniform(0.3, 1.0), rnd.uniform(0, 6.28)) for _ in range(14)]
        self.dust = [(rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(1.2, 3.2), rnd.uniform(0, 6.28), rnd.uniform(0.4, 1.0)) for _ in range(60)]
        self.drops = [(rnd.uniform(40, W - 40), rnd.uniform(40, H - 40), rnd.uniform(10, 34), rnd.uniform(0, 30)) for _ in range(22)]
        self.prev = None
        self.cam_off = (0.0, 0.0)

    # ------------------------------------------------------------ camera
    def _handheld(self, T, amp):
        # layered sines at incommensurate frequencies: reads as a breathing operator
        x = (math.sin(T * 0.71) * 0.55 + math.sin(T * 1.37 + 1.3) * 0.3 + math.sin(T * 3.1 + 0.4) * 0.15)
        y = (math.sin(T * 0.53 + 2.1) * 0.55 + math.sin(T * 1.91 + 0.2) * 0.3 + math.sin(T * 2.7 + 2.4) * 0.15)
        r = math.sin(T * 0.43 + 0.9) * 0.6 + math.sin(T * 1.13) * 0.4
        return x * 9 * amp, y * 9 * amp, r * 0.0045 * amp

    def _impact(self, T):
        v = 0.0
        for t0, a in self.impacts:
            d = T - t0
            if 0 <= d < 1.2: v = max(v, a * math.exp(-d * 5.5))
        return v

    def tension(self, T):
        # handheld gets nervier as the episode heads to its cliffhanger
        return 0.6 + 0.9 * smooth((T / max(self.total, 1) - 0.35) / 0.55)

    def camera(self, c, T, scene, t, d):
        """Apply the virtual camera to cairo context c before the scene draws."""
        W, H = self.W, self.H
        sid = scene['id']
        if sid in NO_CAMERA:
            self.cam_off = (0.0, 0.0); return
        i = self.scene_index.get(id(scene), 0)
        u = smooth(t / max(d, 0.1))
        mv = self.moves[i]
        z, dx, dy, rot = 1.06, 0.0, 0.0, 0.0
        if mv == 'push': z = 1.05 + 0.09 * u
        elif mv == 'pull': z = 1.14 - 0.08 * u
        elif mv == 'truck_r': dx = 46 - 92 * u; z = 1.09
        elif mv == 'truck_l': dx = -46 + 92 * u; z = 1.09
        elif mv == 'crane_down': dy = -50 + 100 * u; z = 1.08 + 0.03 * u
        elif mv == 'arc': rot = -0.018 + 0.036 * u; z = 1.08 + 0.04 * u; dx = 20 - 40 * u
        # cold open: fast ease-out push to grab attention in the first second
        if T < 1.2: z += 0.22 * (1 - ease_out(T / 1.2))
        # quick settle after every cut: shot "lands" instead of popping
        if t < 0.45 and scene['start'] > 0: z += 0.035 * (1 - ease_out(t / 0.45))
        # punch-in on character dialogue
        for a, b in self.punch:
            if a - 0.1 <= T < b + 0.5:
                z += 0.045 * ease_out((T - a + 0.1) / 0.35) * (1 - smooth((T - b) / 0.5)); break
        amp = self.tension(T) * (0.35 if sid == 'cctv' else 1.0)
        hx, hy, hr = self._handheld(T, amp)
        k = self._impact(T)
        if k > 0:
            hx += k * 26 * math.sin(T * 57); hy += k * 22 * math.cos(T * 43); hr += k * 0.012 * math.sin(T * 39); z += 0.03 * k
        ox, oy = dx + hx, dy + hy
        self.cam_off = (ox * z, oy * z)
        c.translate(W / 2 + ox, H / 2 + oy); c.rotate(rot + hr); c.scale(z, z); c.translate(-W / 2, -H / 2)

    # ------------------------------------------------------------ depth layer
    def foreground(self, c, T, sid):
        """Out-of-focus particles in front of the scene, moving with stronger parallax."""
        import cairo
        if sid in NO_CAMERA or sid == 'cctv': return
        W, H = self.W, self.H
        px, py = self.cam_off[0] * 1.8, self.cam_off[1] * 1.8
        look = SCENE_LOOK.get(sid, 'noir_amber')
        warm = {'noir_amber': (1.0, 0.72, 0.35), 'sodium': (1.0, 0.66, 0.30), 'sickly': (0.75, 1.0, 0.85),
                'teal_night': (0.55, 0.85, 1.0), 'paper': (1.0, 0.9, 0.75)}.get(look, (1, 0.8, 0.5))
        # bokeh orbs: lights far behind or in front, way out of focus
        for x, y, r, a, ph in self.bokeh:
            xx = (x + px + 18 * math.sin(T * 0.21 + ph)) % (W + 400) - 200
            yy = (y + py + 12 * math.cos(T * 0.17 + ph)) % (H + 400) - 200
            g = cairo.RadialGradient(xx, yy, r * 0.55, xx, yy, r)
            al = 0.03 * a * (0.8 + 0.2 * math.sin(T * 1.3 + ph))
            g.add_color_stop_rgba(0, warm[0], warm[1], warm[2], al); g.add_color_stop_rgba(0.85, warm[0], warm[1], warm[2], al * 1.4)
            g.add_color_stop_rgba(1, warm[0], warm[1], warm[2], 0)
            c.set_source(g); c.new_path(); c.arc(xx, yy, r, 0, 2 * PI); c.fill()
        if sid in INTERIOR_DUST:
            for x, y, r, ph, a in self.dust:
                xx = (x + px * 0.6 + 30 * math.sin(T * 0.3 + ph)) % W
                yy = (y + py * 0.6 - T * 14 * a + 20 * math.sin(T * 0.23 + ph * 2)) % H
                tw = 0.5 + 0.5 * math.sin(T * 2.1 + ph * 3)
                c.new_path(); c.arc(xx, yy, r, 0, 2 * PI); c.set_source_rgba(1, 0.95, 0.85, 0.22 * a * tw); c.fill()
        if sid in RAINY:
            # rain beading on the lens: refracting drops that slowly slide down
            for x, y, r, sp in self.drops:
                yy = (y + T * sp) % (H + 80) - 40
                g = cairo.RadialGradient(x - r * 0.3, yy - r * 0.3, 0, x, yy, r)
                g.add_color_stop_rgba(0, 1, 1, 1, 0.20); g.add_color_stop_rgba(0.5, 0.8, 0.88, 1, 0.06)
                g.add_color_stop_rgba(0.9, 0, 0, 0, 0.10); g.add_color_stop_rgba(1, 0, 0, 0, 0)
                c.set_source(g); c.new_path(); c.arc(x, yy, r, 0, 2 * PI); c.fill()

    # ------------------------------------------------------------ grade
    def _prep_grade(self):
        W, H = self.W, self.H
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        nx = (xx - W / 2) / (W / 2); ny = (yy - H / 2) / (H / 2)
        rr = np.sqrt(nx * nx * 1.0 + ny * ny * 0.62)
        self.vig = (1 - 0.62 * np.clip((rr - 0.45) / 0.85, 0, 1) ** 1.6).astype(np.float32)[..., None]
        # chromatic aberration: red channel scaled out, blue in, around the centre
        def mp(s):
            return ((xx - W / 2) * s + W / 2).astype(np.float32), ((yy - H / 2) * s + H / 2).astype(np.float32)
        self.ca_r = mp(1 / 1.0028); self.ca_b = mp(1 / 0.9972)
        rng = np.random.default_rng(5)
        self.grain = []
        for _ in range(8):
            g = rng.standard_normal((H // 2, W // 2)).astype(np.float32)
            g = cv2.GaussianBlur(g, (0, 0), 0.6)
            self.grain.append(cv2.resize(g, (W, H), interpolation=cv2.INTER_LINEAR))

    def grade(self, arr, T, sid, flash=0.0, is_cut=False):
        """arr: HxWx4 uint8 BGRA view of the cairo surface; graded in place."""
        L = LOOKS[SCENE_LOOK.get(sid, 'noir_amber')]
        W, H = self.W, self.H
        f = arr[:, :, :3].astype(np.float32) * (1 / 255.0)
        # shutter: blend a little of the last frame for motion smoothness (never across cuts)
        if self.prev is not None and not is_cut:
            diff = float(np.abs(f[::16, ::16] - self.prev[::16, ::16]).mean())
            if diff < 0.06: f = cv2.addWeighted(f, 0.78, self.prev, 0.22, 0)
        self.prev = f
        # bloom + halation from highlights
        thr, bs = L['bloom']
        sm = cv2.resize(f, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
        lum = sm.max(axis=2)
        m = np.clip((lum - thr) / (1 - thr), 0, 1)[..., None]
        hi = sm * m
        b = cv2.GaussianBlur(hi, (0, 0), 5) * 0.55 + cv2.GaussianBlur(hi, (0, 0), 18) * 0.75 + cv2.GaussianBlur(hi, (0, 0), 45) * 0.5
        if L['hal'] > 0:
            hal = cv2.GaussianBlur(m[..., 0], (0, 0), 8)
            b[..., 2] += hal * L['hal'] * 0.9; b[..., 1] += hal * L['hal'] * 0.25
        # clarity: large-radius local contrast gives flat fills some depth
        base = cv2.resize(cv2.GaussianBlur(sm, (0, 0), 10), (W, H), interpolation=cv2.INTER_LINEAR)
        f = f + (f - base) * 0.35
        f = f + cv2.resize(b, (W, H), interpolation=cv2.INTER_LINEAR) * bs
        # exposure (+ lightning flash) then filmic tone curve (ACES-ish)
        x = f * (L['exp'] + 0.6 * flash)
        f = (x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14)
        # contrast around mid grey
        f = np.clip((f - 0.035) * (1 / 0.965), 0, None)          # crush the black point
        f = (f - 0.38) * L['con'] + 0.38
        # split tone: teal shadows / warm highlights (per look)
        luma = (f[..., 0] * 0.114 + f[..., 1] * 0.587 + f[..., 2] * 0.299)[..., None]
        sh = (np.clip(1 - luma * 2.2, 0, 1) ** 1.5) * np.clip(luma * 12, 0, 1); hl = np.clip((luma - 0.35) * 1.6, 0, 1)
        f = f + sh * np.array(L['shadow'], np.float32) + hl * np.array(L['high'], np.float32)
        # saturation
        f = luma + (f - luma) * L['sat']
        f = f * self.vig
        # grain, stronger in mid-tones like film
        g = self.grain[int(T * 24) % len(self.grain)]
        f = f + g[..., None] * (0.028 * (0.4 + 0.6 * np.clip(1 - np.abs(luma - 0.4) * 1.8, 0, 1)))
        out = np.clip(f * 255, 0, 255).astype(np.uint8)
        # chromatic aberration on the edges
        out[..., 2] = cv2.remap(out[..., 2], *self.ca_r, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        out[..., 0] = cv2.remap(out[..., 0], *self.ca_b, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        arr[:, :, :3] = out
        arr[:, :, 3] = 255
