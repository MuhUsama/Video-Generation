"""Night Shift renderer. Usage: python3 render.py <episode_dir> [stills t1 t2 ...]"""
import cairo, json, math, random, subprocess, sys
import numpy as np

EP = sys.argv[1].rstrip('/') + '/'
W, H, FPS = 1080, 1920, 30
TM = json.load(open(EP + 'timing.json'))
TOTAL = TM['total']; LINES = TM['lines']; PARAMS = TM.get('params', {})
SCENES_T = TM['scenes']
FONT = 'Inter'; PI = math.pi
random.seed(11)

def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def prog(t, a, b): return clamp((t - a) / (b - a)) if b > a else float(t >= a)
def smooth(x): x = clamp(x); return x * x * (3 - 2 * x)
def ease(x): x = clamp(x); return 1 - (1 - x) ** 3
def hexc(h, a=1.0): h = h.lstrip('#'); return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)) + (a,)
def mix(a, b, k): return tuple(a[i] + (b[i] - a[i]) * k for i in range(4))
def src(c, col, a=1.0): c.set_source_rgba(col[0], col[1], col[2], col[3] * a)

AMBER = hexc('ffb347'); NEON = hexc('ff2e4d'); GREEN = hexc('39ff8a'); COLD = hexc('cfe4ff')
INK = hexc('07080c'); WHITE = hexc('ffffff'); TEAL = hexc('7fe0d0'); BLACK = hexc('000000')

def text(c, s, x, y, size, col=WHITE, weight=cairo.FONT_WEIGHT_BOLD, align='c', alpha=1.0, outline=0, slant=cairo.FONT_SLANT_NORMAL, font=FONT, spacing=0):
    c.save(); c.select_font_face(font, slant, weight); c.set_font_size(size)
    w = c.text_extents(s).x_advance + spacing * len(s)
    x0 = {'c': x - w / 2, 'l': x, 'r': x - w}[align]
    if spacing:
        xx = x0
        for ch in s: c.move_to(xx, y); c.text_path(ch); xx += c.text_extents(ch).x_advance + spacing
    else: c.move_to(x0, y); c.text_path(s)
    if outline:
        c.set_source_rgba(0, 0, 0, 0.7 * alpha); c.set_line_width(outline); c.set_line_join(cairo.LINE_JOIN_ROUND); c.stroke_preserve()
    src(c, col, alpha); c.fill(); c.restore(); return w
def tw(c, s, size, weight=cairo.FONT_WEIGHT_BOLD, slant=0, font=FONT):
    c.save(); c.select_font_face(font, slant, weight); c.set_font_size(size); w = c.text_extents(s).x_advance; c.restore(); return w
def rect(c, x, y, w, h, col, a=1.0): c.new_path(); c.rectangle(x, y, w, h); src(c, col, a); c.fill()
def circ(c, x, y, r, col, a=1.0): c.new_path(); c.arc(x, y, max(r, .01), 0, 2 * PI); src(c, col, a); c.fill()
def glow(c, x, y, r, col, a=1.0):
    c.new_path(); g = cairo.RadialGradient(x, y, 0, x, y, r)
    g.add_color_stop_rgba(0, col[0], col[1], col[2], a); g.add_color_stop_rgba(1, col[0], col[1], col[2], 0)
    c.set_source(g); c.arc(x, y, r, 0, 2 * PI); c.fill()
def quad(c, pts, col, a=1.0):
    c.new_path(); c.move_to(*pts[0]); [c.line_to(*p) for p in pts[1:]]; c.close_path(); src(c, col, a); c.fill()
def rrect(c, x, y, w, h, r):
    c.new_path(); c.arc(x + w - r, y + r, r, -PI / 2, 0); c.arc(x + w - r, y + h - r, r, 0, PI / 2)
    c.arc(x + r, y + h - r, r, PI / 2, PI); c.arc(x + r, y + r, r, PI, 1.5 * PI); c.close_path()

def flash(T):
    v = 0
    for th in TM['thunder']:
        for off, amp in ((0, 1.0), (0.13, 0.7), (0.32, 0.45)):
            d = T - th - off
            if d >= 0: v = max(v, amp * math.exp(-d * 9))
    return v
def ringing(T):
    return any(r <= T < r + 0.9 or r + 1.6 <= T < r + 2.5 for r in TM['rings'])

# ---------- characters ----------
def body_path(c, x, y, s, turn=0.0, hair=False):
    c.new_path(); hr = 62 * s
    c.arc(x, y, hr, 0, 2 * PI); c.new_sub_path()
    c.arc(x - 6 * s * turn, y - 18 * s, hr * 0.98, PI * 1.05, PI * 1.95); c.new_sub_path()
    if abs(turn) > 0.05:
        nx = x + hr * 0.95 * (1 if turn > 0 else -1); c.arc(nx, y + 8 * s, 13 * s * abs(turn), 0, 2 * PI); c.new_sub_path()
    if hair:  # long hair falling to the shoulders
        c.move_to(x - hr * 1.05, y - 10 * s); c.curve_to(x - hr * 1.3, y + 60 * s, x - hr * 1.2, y + 120 * s, x - hr * 0.9, y + 150 * s)
        c.line_to(x + hr * 0.9, y + 150 * s); c.curve_to(x + hr * 1.2, y + 120 * s, x + hr * 1.3, y + 60 * s, x + hr * 1.05, y - 10 * s)
        c.close_path(); c.new_sub_path()
    ny = y + hr * 0.8
    c.move_to(x - 30 * s, ny); c.line_to(x + 30 * s, ny); c.line_to(x + 34 * s, ny + 50 * s)
    c.curve_to(x + 120 * s, ny + 60 * s, x + 190 * s, ny + 90 * s, x + 210 * s, ny + 200 * s)
    c.line_to(x + 230 * s, ny + 900 * s); c.line_to(x - 230 * s, ny + 900 * s); c.line_to(x - 210 * s, ny + 200 * s)
    c.curve_to(x - 190 * s, ny + 90 * s, x - 120 * s, ny + 60 * s, x - 34 * s, ny + 50 * s); c.close_path()

def person(c, x, y, s, rim=AMBER, rim_dir=(-1, 0), turn=0.0, eye=0.0, eye_wide=0.0, rim_a=1.0, col=INK, hair=False, eye_col=COLD, alpha=1.0):
    c.save(); c.translate(rim_dir[0] * 5 * s, rim_dir[1] * 5 * s)
    body_path(c, x, y, s, turn, hair); src(c, rim, 0.9 * rim_a * alpha); c.fill(); c.restore()
    body_path(c, x, y, s, turn, hair); src(c, col, alpha); c.fill()
    if eye > 0:
        if abs(turn) < 0.4: xs = [x + 26 * s * turn - 22 * s, x + 26 * s * turn + 22 * s]
        else: xs = [x + (36 * s if turn > 0 else -36 * s)]
        for ex in xs:
            c.save(); c.translate(ex, y - 4 * s); c.scale(1, 0.45 + 0.55 * eye_wide); circ(c, 0, 0, 7 * s, eye_col, eye * alpha); c.restore()

def creature(c, x, y, s, a, eyes, lean=0.0):
    c.save(); c.translate(x, y); c.rotate(lean * 0.12); c.scale(s, s); c.new_path()
    c.move_to(-40, -330); c.curve_to(-75, -330, -85, -270, -80, -220); c.curve_to(-80, -170, -70, -150, -60, -140)
    c.curve_to(-170, -120, -200, -60, -210, 80); c.line_to(-260, 520); c.line_to(-200, 530); c.line_to(-170, 150)
    c.line_to(-160, 900); c.line_to(160, 900); c.line_to(170, 150); c.line_to(200, 530); c.line_to(260, 520)
    c.line_to(210, 80); c.curve_to(200, -60, 170, -120, 60, -140); c.curve_to(70, -150, 80, -170, 80, -220)
    c.curve_to(85, -270, 75, -330, 40, -330); c.close_path(); c.set_source_rgba(0.01, 0.01, 0.02, a); c.fill()
    if eyes > 0:
        for ex in (-26, 26):
            glow(c, ex, -235, 30, hexc('d9e8ff'), 0.35 * eyes)
            c.save(); c.translate(ex, -235); c.scale(1, 0.5); circ(c, 0, 0, 7, hexc('eef4ff'), eyes); c.restore()
    c.restore()

# ---------- fx ----------
RAIN = [(random.uniform(-200, W + 200), random.uniform(0, H), random.uniform(0.6, 1.4)) for _ in range(220)]
def rain(c, T, a=1.0, lit=0.0, slant=0.18):
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    for x, y, z in RAIN:
        yy = (y + T * 2100 * z) % (H + 200) - 100; xx = x + yy * slant
        c.new_path(); c.set_line_width(1.6 * z); c.set_source_rgba(0.75, 0.82, 1, (0.18 + 0.4 * lit) * z * a)
        c.move_to(xx, yy); c.line_to(xx + 70 * z * slant, yy + 70 * z); c.stroke()
FOGB = [(random.uniform(0, W), random.uniform(0, H), random.uniform(250, 520), random.uniform(10, 40)) for _ in range(16)]
def fog(c, T, a=1.0, col=hexc('b9c3d6'), y0=0, y1=H):
    for x, y, r, sp in FOGB:
        xx = (x + T * sp) % (W + 2 * r) - r; yy = y0 + (y / H) * (y1 - y0)
        glow(c, xx, yy, r, col, 0.10 * a)
ASH = [(random.uniform(0, W), random.uniform(0, H), random.uniform(1.5, 4), random.uniform(15, 45), random.uniform(0, 6)) for _ in range(70)]
def ash(c, T, a=1.0, col=hexc('c9b9a6'), up=False):
    for x, y, r, sp, ph in ASH:
        yy = (y + (-1 if up else 1) * T * sp) % H; xx = x + 25 * math.sin(T * 0.7 + ph)
        circ(c, xx, yy, r, col, 0.5 * a)
GRAIN = []
for kk in range(6):
    arr = (np.random.default_rng(kk).random((H // 3, W // 3)) * 255).astype(np.uint8)
    rgba = np.dstack([arr, arr, arr, np.full_like(arr, 255)]).copy()
    GRAIN.append(cairo.ImageSurface.create_for_data(memoryview(bytearray(rgba.tobytes())), cairo.FORMAT_ARGB32, W // 3, H // 3))
def post(c, T):
    g = cairo.RadialGradient(W / 2, H / 2, 300, W / 2, H / 2, 1250)
    g.add_color_stop_rgba(0, 0, 0, 0, 0); g.add_color_stop_rgba(1, 0, 0, 0, 0.75); c.set_source(g); c.paint()
    c.save(); c.scale(3, 3); c.set_source_surface(GRAIN[int(T * 24) % 6], 0, 0)
    c.get_source().set_filter(cairo.FILTER_NEAREST); c.paint_with_alpha(0.045); c.restore()
def camera(c, fx, fy, z, shake=0.0, T=0):
    c.translate(W / 2 + shake * math.sin(T * 61) * 14, H / 2 + shake * math.cos(T * 47) * 14); c.scale(z, z); c.translate(-fx, -fy)
def flashlight(c, sx, sy, r0=80, r1=700, dark=0.85):
    g = cairo.RadialGradient(sx, sy, r0, sx, sy, r1)
    g.add_color_stop_rgba(0, 0, 0, 0, 0); g.add_color_stop_rgba(0.6, 0, 0, 0, 0.3 * dark / 0.85); g.add_color_stop_rgba(1, 0, 0, 0, dark)
    c.set_source(g); c.paint(); glow(c, sx, sy, 300, COLD, 0.08)
def B(S, i, default=99.0): return S['beats'][i] if i < len(S['beats']) else default

# ================= MOTEL SCENES =================
TREES = [(random.uniform(-100, W + 100), random.uniform(160, 320)) for _ in range(28)]
def sc_exterior(c, T, t, d, S, P):
    fl = flash(T)
    if P.get('pullout'): z = 1.15 - 0.2 * smooth(t / d)
    else: z = 0.95 + 0.12 * smooth(t / d)
    c.save(); camera(c, W / 2, 900, z)
    g = cairo.LinearGradient(0, 0, 0, 1300)
    g.add_color_stop_rgba(0, *mix(hexc('050813'), hexc('7d8fb8'), fl)); g.add_color_stop_rgba(1, *mix(hexc('16223f'), hexc('a9b8da'), fl))
    c.set_source(g); c.rectangle(-400, -400, W + 800, H + 800); c.fill()
    for x, h in TREES:
        quad(c, [(x, 1100 - h * 1.9 - 200), (x - h * 0.35, 1120), (x + h * 0.35, 1120)], mix(hexc('03050b'), hexc('1c2438'), fl * 0.6))
    rect(c, -400, 1110, W + 800, 1300, hexc('05070c'))
    bx, by, bw, bh = 40, 900, 1000, 260
    rect(c, bx, by, bw, bh, mix(hexc('121621'), hexc('3a4256'), fl)); rect(c, bx - 20, by - 30, bw + 40, 36, hexc('0b0d14'))
    for i in range(7):
        dx = bx + 40 + i * 140; rect(c, dx, by + 90, 60, 150, hexc('080a10'))
        text(c, str(i + 3), dx + 30, by + 75, 22, hexc('8d7a55'), alpha=0.7)
        lit = (i in (1, 4)) and not (i == 4 and 0.4 < (T % 3.1) < 0.5)
        if P.get('pullout') and i == 6: lit = int(T * 6) % 4 != 0   # room 9 flickers
        rect(c, dx + 72, by + 110, 50, 60, AMBER if lit else hexc('0d1018'), 0.85 if lit else 1)
        if lit: glow(c, dx + 97, by + 140, 70, AMBER, 0.25)
    ox = 860; rect(c, ox - 70, by + 100, 140, 110, AMBER, 0.95); glow(c, ox, by + 155, 200, AMBER, 0.35)
    c.save(); c.rectangle(ox - 70, by + 100, 140, 110); c.clip(); person(c, ox + 10, by + 150, 0.32, rim=AMBER, rim_dir=(0, 0)); c.restore()
    text(c, 'OFFICE', ox, by + 85, 22, AMBER, alpha=0.8)
    px = 210; rect(c, px - 8, 420, 16, 500, hexc('0b0d14'))
    rect(c, px - 160, 330, 320, 260, hexc('0c0f17')); c.new_path(); c.rectangle(px - 160, 330, 320, 260); src(c, NEON, 0.25); c.set_line_width(3); c.stroke()
    flick = 0.25 if (int(T * 13) % 17 in (3, 4) or 2.1 < T % 5 < 2.25) else 1.0
    glow(c, px, 420, 260, NEON, 0.18 * flick)
    text(c, 'PINEWOOD', px, 410, 54, NEON, alpha=flick, spacing=3); text(c, 'MOTEL', px, 480, 54, NEON, alpha=flick, spacing=10)
    nv = P.get('novacancy')
    if nv is not None and t >= B(S, nv) + 0.8:
        k = prog(t, B(S, nv) + 0.8, B(S, nv) + 1.6); on = k >= 1 or random.Random(int(T * 15)).random() < k
        text(c, 'NO VACANCY', px, 555, 40, NEON, alpha=0.95 if on else 0.15)
    else:
        vac = 'VACANCY'; x0 = px - tw(c, vac, 40) / 2
        for i, ch in enumerate(vac):
            on = not (i == 0 and int(T * 7) % 5 == 0); x0 += text(c, ch, x0, 555, 40, GREEN, align='l', alpha=0.95 if on else 0.15)
    glow(c, ox, 1300, 180, AMBER, 0.08)
    c.restore()
    rain(c, T, 1.0, fl)
    if P.get('clock', True) and not P.get('pullout'):
        a = prog(t, 0.6, 1.0) * (1 - prog(t, d - 1.2, d - 0.6)); s = '3:07 AM'; n = int(clamp((t - 0.6) / 0.8) * len(s))
        text(c, s[:n], 90, 1420, 64, WHITE, align='l', alpha=a, font='JetBrains Mono')
    if fl > 0: rect(c, 0, 0, W, H, WHITE, fl * 0.15)

def phone(c, x, y, s, T, ring_, screen, handset_up):
    c.save(); c.translate(x, y); c.scale(s, s)
    if ring_: c.translate(math.sin(T * 90) * 4, 0)
    quad(c, [(-150, 60), (150, 60), (120, -40), (-120, -40)], hexc('1a1410'))
    rect(c, -70, -20, 140, 50, hexc('0a1a10'))
    if screen > 0:
        glow(c, 0, 5, 160, GREEN, 0.3 * screen); rect(c, -70, -20, 140, 50, GREEN, 0.25 * screen)
        text(c, 'ROOM 9', 0, 18, 30, GREEN, alpha=screen, font='JetBrains Mono')
    if not handset_up:
        c.save(); c.translate(0, -60 - (8 if ring_ and int(T * 20) % 2 else 0)); c.new_path()
        c.move_to(-160, 0); c.curve_to(-120, -40, 120, -40, 160, 0); c.line_to(150, 30); c.line_to(-150, 30); c.close_path()
        src(c, hexc('120e0b')); c.fill_preserve(); src(c, AMBER, 0.4); c.set_line_width(3); c.stroke(); c.restore()
    c.restore()

def interior_bg(c, T, fl, lamp=1.0):
    rect(c, -400, -400, W + 800, H + 800, hexc('0d0a09'))
    for i in range(-3, 14): rect(c, i * 110, -400, 50, 1700, hexc('16110d'))
    wx, wy, ww, wh = 90, 420, 330, 440
    rect(c, wx, wy, ww, wh, mix(hexc('0b1426'), hexc('9fb3dd'), fl))
    c.save(); c.rectangle(wx, wy, ww, wh); c.clip(); rain(c, T, 0.8, fl); c.restore()
    rect(c, wx + ww / 2 - 6, wy, 12, wh, hexc('0a0807')); rect(c, wx, wy + wh / 2 - 6, ww, 12, hexc('0a0807'))
    c.new_path(); c.rectangle(wx, wy, ww, wh); src(c, hexc('0a0807')); c.set_line_width(18); c.stroke()
    glow(c, 820, 1080, 700, AMBER, 0.33 * lamp)
    kx, ky = 640, 470
    rect(c, kx, ky, 320, 360, hexc('2a1d12'))
    for n in range(12):
        hx = kx + 50 + (n % 4) * 74; hy = ky + 70 + (n // 4) * 110; circ(c, hx, hy, 5, AMBER, 0.7)
        if n + 1 != 9:
            c.save(); c.translate(hx, hy); c.rotate(0.1 * math.sin(T * 1.3 + n)); rect(c, -3, 4, 6, 26, hexc('b08a4a')); rect(c, -14, 30, 28, 34, hexc('7a1f1f')); c.restore()
    rect(c, -400, 1250, W + 800, 900, hexc('1c130c')); rect(c, -400, 1250, W + 800, 14, AMBER, 0.35)
    quad(c, [(760, 1250), (790, 1060), (810, 1060), (840, 1250)], hexc('100c08'))
    quad(c, [(720, 1080), (880, 1080), (840, 990), (760, 990)], hexc('2b2015'))
    glow(c, 800, 1090, 120, AMBER, 0.8 * lamp)

def sc_hall(c, T, t, d, S, P):
    run = P.get('run'); walker = P.get('walker', True)
    bob = math.sin(t * (14 if run else 6)) * (14 if run else 6)
    vx, vy = W / 2, 820 + bob
    z = 1.0 + (0.9 if run else 0.45) * (t / d) if (walker or run) else 1.05 + 0.1 * smooth(t / d)
    c.save(); camera(c, W / 2, 900, z, shake=0.5 if run else 0, T=T)
    rect(c, -400, -400, W + 800, H + 800, hexc('0c0d10'))
    fw, fh = 180, 260
    far = [(vx - fw / 2, vy - fh / 2), (vx + fw / 2, vy - fh / 2), (vx + fw / 2, vy + fh / 2), (vx - fw / 2, vy + fh / 2)]
    quad(c, [(-300, -300), (W + 300, -300), far[1], far[0]], hexc('0f1013'))
    quad(c, [(-300, H + 300), (W + 300, H + 300), far[2], far[3]], hexc('1a1210'))
    quad(c, [(-300, -300), far[0], far[3], (-300, H + 300)], hexc('15140f'))
    quad(c, [(W + 300, -300), far[1], far[2], (W + 300, H + 300)], hexc('13120e'))
    quad(c, [(W / 2 - 260, H + 300), (W / 2 + 260, H + 300), (vx + 40, vy + fh / 2), (vx - 40, vy + fh / 2)], hexc('3a1414'), 0.8)
    for side in (-1, 1):
        for k, num in enumerate((5, 7) if side < 0 else (6, 8)):
            f0 = 0.35 + k * 0.3; f1 = f0 + 0.15
            def wp(f, yy):
                ex = vx + side * fw / 2; x = (1 - f) * (W / 2 + side * (W / 2 + 300)) + f * ex
                top = (1 - f) * (-300) + f * (vy - fh / 2); bot = (1 - f) * (H + 300) + f * (vy + fh / 2); return x, top + (bot - top) * yy
            quad(c, [wp(1 - f0, 0.28), wp(1 - f1, 0.28), wp(1 - f1, 0.98), wp(1 - f0, 0.98)], hexc('1e140c'))
            x, y = wp(1 - (f0 + f1) / 2, 0.24); text(c, str(num), x, y, 40 * (1 - f0 * 0.6), hexc('8d7a55'), alpha=0.7)
    flick = 0.5 + 0.5 * (random.Random(int(T * 12)).random() > 0.3)
    rect(c, vx - 45, vy - 95, 90, 190, hexc('0a0706')); rect(c, vx - 45, vy - 95, 16, 190, hexc('ffcf8a'), 0.85 * flick)
    glow(c, vx - 40, vy, 160, hexc('ffb860'), 0.3 * flick)
    quad(c, [(vx - 29, vy + 95), (vx - 120, vy + 220), (vx - 40, vy + 220), (vx - 45, vy + 95)], hexc('ffb860'), 0.2 * flick)
    text(c, '9', vx + 5, vy - 40, 34, hexc('c9a76a'))
    if P.get('footprints'):
        fp = prog(t, B(S, 1) - 0.2, B(S, 1) + 2.0)
        for i in range(12):
            f = i / 12
            if f > fp: break
            yy = H + 100 - (H + 100 - (vy + 100)) * (1 - (1 - f) ** 1.6); sc = 1 - 0.8 * (1 - (1 - f) ** 1.6)
            xx = W / 2 + (40 if i % 2 else -40) * sc
            c.save(); c.translate(xx, yy); c.scale(sc, sc * 0.5); circ(c, 0, 0, 30, hexc('020202'), 0.9); circ(c, 0, -48, 20, hexc('020202'), 0.9)
            c.restore(); glow(c, xx, yy, 40 * sc, COLD, 0.08)
    c.restore()
    sx = W / 2 + 60 * math.sin(t * 0.9) + (220 * math.sin(t * 9) * (1 - prog(t, 0, 0.6)) if P.get('footprints') else 0)
    sy = 900 + 30 * math.cos(t * 1.3) + (300 * prog(t, B(S, 1), B(S, 1) + 1.0) if P.get('footprints') else 0)
    flashlight(c, sx, sy)
    if walker and not run:
        c.save(); c.translate(0, bob * 0.5)
        quad(c, [(470, 1560), (sx, sy), (sx + 220, sy + 160)], COLD, 0.05)
        person(c, 260, 1560, 1.1, rim=COLD, rim_dir=(0.6, -1), rim_a=0.5)
        c.new_path(); c.move_to(420, 1800); c.line_to(480, 1570); c.set_line_width(60); src(c, INK); c.stroke(); c.restore()

def sc_behind(c, T, t, d, S, P):
    fl = flash(T); recap = P.get('recap')
    z = 1.0 + 0.15 * smooth(t / d)
    c.save(); camera(c, W / 2, 900, z, shake=fl * 0.6, T=T)
    rect(c, -400, -400, W + 800, H + 800, mix(hexc('07080b'), hexc('8193b8'), fl * 0.9))
    rect(c, 230, 300, 620, 1300, mix(hexc('030304'), hexc('1a1d26'), fl))
    c.new_path(); c.rectangle(230, 300, 620, 1300); src(c, mix(hexc('1b1610'), hexc('c7d2ea'), fl)); c.set_line_width(26); c.stroke()
    text(c, '9', 540, 270, 60, mix(hexc('6b5b40'), WHITE, fl))
    if recap:
        seen = clamp(fl * 1.5 + 0.35); eyes = 1.0; lean = 1.0; hp = 1.0
    else:
        b0, b1 = B(S, 0), B(S, 1)
        seen = clamp(fl * 1.5 + 0.35 * prog(t, b0 + 0.2, b0 + 1.6)); eyes = prog(t, b0 + 0.6, b0 + 1.4)
        lean = smooth(prog(t, b1 + 1.5, d)); hp = smooth(prog(t, b1 + 2.6, b1 + 3.4))
    creature(c, 610, 860 + 80 * lean, 1.15 + 0.25 * lean, seen, eyes=eyes, lean=lean)
    glow(c, 470, 1400, 400, COLD, 0.12)
    person(c, 470, 1180, 1.25, rim=COLD, rim_dir=(-0.8, -1), turn=-0.15, eye=1, eye_wide=1, rim_a=0.7 + fl * 0.3)
    if hp > 0:
        c.save(); c.translate(720 - 40 * hp, 1250 - 40 * hp)
        for i in range(4):
            c.new_path(); c.move_to(i * 22, 0); c.curve_to(i * 22 - 5, 60 * hp, i * 22 - 10, 110 * hp, i * 22 - 18, 150 * hp)
            src(c, hexc('020203')); c.set_line_width(14); c.set_line_cap(cairo.LINE_CAP_ROUND); c.stroke()
        quad(c, [(-20, -60), (90, -60), (80, 30), (-10, 30)], hexc('020203')); c.restore()
    c.restore()
    if fl > 0: rect(c, 0, 0, W, H, WHITE, fl * 0.35)

def burnt_room(c, T, fl=0.0):
    rect(c, -400, -400, W + 800, H + 800, hexc('0b0908'))
    # walls with soot gradient
    g = cairo.LinearGradient(0, 200, 0, 1300); g.add_color_stop_rgba(0, 0.03, 0.025, 0.02, 1); g.add_color_stop_rgba(1, 0.13, 0.09, 0.07, 1)
    c.set_source(g); c.rectangle(-400, 0, W + 800, 1300); c.fill()
    r = random.Random(5)
    for i in range(26):  # soot streaks
        x = r.uniform(-100, W + 100); w = r.uniform(20, 90); h = r.uniform(300, 900)
        g = cairo.LinearGradient(0, 1300 - h, 0, 1300); g.add_color_stop_rgba(0, 0, 0, 0, 0); g.add_color_stop_rgba(1, 0, 0, 0, 0.6)
        c.set_source(g); c.rectangle(x, 1300 - h, w, h); c.fill()
    # broken window with moonlight
    wx, wy = 650, 330
    rect(c, wx, wy, 300, 380, mix(hexc('101a30'), hexc('9fb3dd'), fl))
    quad(c, [(wx, wy), (wx + 140, wy), (wx + 60, wy + 120), (wx + 120, wy + 200), (wx, wy + 260)], hexc('0b0908'))
    c.new_path(); c.rectangle(wx, wy, 300, 380); src(c, hexc('050403')); c.set_line_width(16); c.stroke()
    quad(c, [(wx + 150, wy + 380), (wx + 300, wy + 380), (500, 1400), (200, 1400)], COLD, 0.05 + 0.2 * fl)
    # floor
    rect(c, -400, 1300, W + 800, 900, hexc('120d0a'))
    for i in range(8): rect(c, -400, 1300 + i * 80, W + 800, 3, hexc('050403'))
    # bed
    rect(c, 140, 1000, 120, 330, hexc('060505'))  # headboard
    quad(c, [(150, 1150), (900, 1170), (950, 1330), (130, 1330)], hexc('1d1611'))
    quad(c, [(150, 1150), (900, 1170), (920, 1210), (140, 1195)], hexc('2b221b'))
    rect(c, 130, 1330, 820, 60, hexc('080605'))

def sc_room(c, T, t, d, S, P):
    z = 1.0 + 0.5 * smooth(prog(t, B(S, 1) - 0.5, d))
    fx = 540 + 0 * t; fy = 950 + 220 * smooth(prog(t, B(S, 1) - 0.5, d))
    c.save(); camera(c, fx, fy, z)
    burnt_room(c, T, flash(T))
    a = prog(t, B(S, 1) - 0.3, B(S, 1) + 0.6)
    c.save(); c.translate(560, 1185); c.scale(1, 0.45)
    rect(c, -110, -70, 220, 140, hexc('e9dfc8'), 0.25 + 0.75 * a); c.new_path(); c.move_to(0, -70); c.line_to(0, 70); src(c, hexc('5a4a3a'), a); c.set_line_width(4); c.stroke()
    c.restore(); glow(c, 560, 1185, 260, AMBER, 0.25 * a)
    c.restore()
    ash(c, T, 0.8)
    flashlight(c, 560 + 200 * math.sin(t * 0.8) * (1 - a), 1000 + 150 * a, r0=100, r1=760, dark=0.8)

def sc_room_phone(c, T, t, d, S, P):
    b1, b2 = B(S, 1), B(S, 2)
    rin = ringing(T) and t < b1
    z = 1.0 + 0.35 * smooth(prog(t, b2 - 0.3, d))
    c.save(); camera(c, 600, 900, z, shake=0.2 * rin + 0.3 * prog(t, b2 + 1.2, b2 + 1.6) * (1 - prog(t, d - 0.4, d)), T=T)
    burnt_room(c, T, flash(T))
    # wall phone
    px, py = 760, 820
    c.save(); c.translate(px + (math.sin(T * 90) * 4 if rin else 0), py)
    rrect(c, -80, -120, 160, 240, 18); src(c, hexc('1a1512')); c.fill()
    circ(c, 0, 30, 52, hexc('0d0a08'));
    for i in range(10):
        a = -PI * 0.2 + i * PI * 0.15; circ(c, 34 * math.cos(a), 30 + 34 * math.sin(a), 7, hexc('2c241e'))
    if t < b1:
        c.new_path(); c.move_to(-95, -100); c.curve_to(-60, -150, 60, -150, 95, -100); c.line_to(80, -80); c.line_to(-80, -80); c.close_path(); src(c, hexc('120e0b')); c.fill()
    c.restore()
    if rin:
        for k in range(3):
            r = ((T * 260) + k * 70) % 210; c.new_path(); c.arc(px, py - 100, 70 + r, PI * 1.1, PI * 1.9); src(c, AMBER, 0.5 * (1 - r / 210)); c.set_line_width(5); c.stroke()
    # cord + Daniel
    up = t >= b1 - 0.3
    turn = 0.9
    dx = 500
    person(c, dx, 860, 1.15, rim=COLD, rim_dir=(1, -0.3), turn=turn, eye=1, eye_wide=0.4 + 0.6 * prog(t, b2 + 0.5, b2 + 1.2))
    if up:
        c.new_path(); c.move_to(px - 40, py + 40); c.curve_to(px - 30, py + 220, dx + 80, py + 200, dx + 60, 900); src(c, hexc('2c241e')); c.set_line_width(5); c.stroke()
        c.save(); c.translate(dx + 70, 860); c.rotate(-1.2); c.scale(0.9, 0.9); c.new_path()
        c.move_to(-90, 0); c.curve_to(-60, -40, 60, -40, 90, 0); c.line_to(80, 30); c.line_to(-80, 30); c.close_path(); src(c, hexc('120e0b')); c.fill(); c.restore()
    c.restore()
    ash(c, T, 0.6)
    flashlight(c, 640, 860, r0=120, r1=800, dark=0.75)
    # red pulse when he hears himself
    k = prog(t, b2 + 0.4, b2 + 1.0)
    if k > 0:
        g = cairo.RadialGradient(W / 2, H / 2, 200, W / 2, H / 2, 1200); g.add_color_stop_rgba(0, 0.5, 0, 0, 0); g.add_color_stop_rgba(1, 0.5, 0, 0.02, 0.5 * k * (0.7 + 0.3 * math.sin(T * 6)))
        c.set_source(g); c.paint()

def sc_desk_other(c, T, t, d, S, P):
    b = S['beats']; b2, b3, b4 = B(S, 2), B(S, 3), B(S, 4)
    # wide: from the doorway, figure sitting at desk from behind; later turns
    zoom = smooth(prog(t, b3 + 1.8, b3 + 3.2))
    z = 1.0 + 0.9 * zoom + 0.05 * t / d
    c.save(); camera(c, 540 - 20 * zoom, 1000 - 250 * zoom, z)
    interior_bg(c, T, flash(T) * 0.4, lamp=0.9 + 0.1 * math.sin(T * 13) * (t > b3))
    turn = smooth(prog(t, b3 + 0.3, b3 + 1.6))
    # chair back
    rrect(c, 380, 1000, 300, 320, 40); src(c, hexc('120c08')); c.fill()
    person(c, 530, 980, 0.95, rim=AMBER, rim_dir=(0.9, -0.4), turn=0.0 if turn < 0.5 else 0.0,
           eye=turn, eye_wide=0.3, eye_col=hexc('ffe2b0'))
    if turn > 0.6:
        glow(c, 530, 975, 120, AMBER, 0.15 * turn)
    c.restore()
    # Daniel in the foreground doorway (back view), fades as camera pushes
    da = 1 - zoom
    if da > 0:
        c.save(); c.translate(0, 0)
        person(c, 180, 1450, 1.4, rim=COLD, rim_dir=(0.8, -1), rim_a=0.4, alpha=da)
        c.restore()
    if t > b4 - 0.2:   # creepy smile line when it speaks
        k = prog(t, b4 - 0.2, b4 + 0.6)
        c.new_path(); c.arc(W / 2 - 20, 960 + 140 * 0, 1, 0, 0)
    c.new_path()

def paper_scene(c, T, t, d, S, P):
    kind = P.get('kind', 'book')
    rect(c, 0, 0, W, H, hexc('0b0806'))
    glow(c, W / 2, 900, 900, AMBER if kind != 'news' else hexc('ff5a1e'), 0.18)
    if kind == 'news':
        a = prog(t, 0.2, 0.9)
        for i in range(50):
            r = random.Random(i); x = r.uniform(0, W); sp = r.uniform(40, 120); y = H - ((t * sp + r.uniform(0, H)) % H)
            circ(c, x, y, r.uniform(2, 4), hexc('9fb3dd'), 0.4 * a)
    z = 1.0 + 0.12 * t / d
    c.save(); c.translate(W / 2, 900); c.rotate(-0.04 + 0.01 * t); c.scale(z, z)
    paper = hexc('e6dcc3') if kind != 'ticket' else hexc('d9cfb2')
    ink = hexc('241a12'); red = hexc('9a1b14')
    if kind in ('book', 'log'):
        rect(c, -430, -420, 860, 840, paper); c.new_path(); c.move_to(0, -420); c.line_to(0, 420); src(c, hexc('8a7a60')); c.set_line_width(4); c.stroke()
        g = cairo.LinearGradient(-60, 0, 60, 0); g.add_color_stop_rgba(0, 0, 0, 0, 0); g.add_color_stop_rgba(0.5, 0, 0, 0, 0.25); g.add_color_stop_rgba(1, 0, 0, 0, 0)
        c.set_source(g); c.rectangle(-60, -420, 120, 840); c.fill()
        # soot burns at edges
        for i in range(14):
            r = random.Random(i + 40); glow(c, r.choice([-430, 430]) + r.uniform(-30, 30), r.uniform(-420, 420), r.uniform(60, 140), hexc('1a0f08'), 0.6)
        text(c, P.get('header', ''), -215, -350, 30, ink, font='Special Elite'); text(c, P.get('header', ''), 215, -350, 30, ink, font='Special Elite')
        for i in range(12): rect(c, -410, -300 + i * 60, 820, 2, hexc('9db0c8'), 0.6)
        rows = P.get('rows', [])
        for i, row in enumerate(rows):
            y = -260 + i * 60
            if kind == 'book':
                text(c, row[0], -400, y, 30, ink, font='Homemade Apple', align='l'); text(c, row[1], 30, y, 28, ink, font='Homemade Apple', align='l'); text(c, row[2], 250, y, 28, ink, font='Homemade Apple', align='l')
            else:
                text(c, row[0], -400, y, 30, ink, font='Special Elite', align='l'); text(c, row[1], -230, y, 30, ink, font='Homemade Apple', align='l')
        yN = -260 + len(rows) * 60
        for rv in P.get('reveal', []):
            bt = B(S, rv['beat']); k = prog(t, bt + 0.3, bt + 2.0)
            if k <= 0: continue
            c.save(); c.rectangle(-430, -500, 860 * k + 1, 1000); c.clip()
            if rv['type'] == 'row':
                row = rv['row']
                if kind == 'book':
                    text(c, row[1], 30, yN, 28, red, font='Homemade Apple', align='l'); text(c, row[2], 250, yN, 28, red, font='Homemade Apple', align='l')
                else:
                    text(c, row[0], -400, yN, 30, red, font='Special Elite', align='l'); text(c, row[1], -230, yN, 34, red, font='Homemade Apple', align='l')
            elif rv['type'] == 'sig':
                text(c, rv['text'], -400, yN, 34, red, font='Homemade Apple', align='l')
            c.restore()
            if rv['type'] == 'stamp':
                k2 = prog(t, bt + 1.2, bt + 1.5)
                if k2 > 0:
                    c.save(); c.translate(80, 200); c.rotate(-0.18); s2 = 1.6 - 0.6 * ease(k2); c.scale(s2, s2)
                    rrect(c, -260, -60, 520, 110, 10); src(c, red, 0.85 * k2); c.set_line_width(8); c.stroke()
                    text(c, rv['text'], 0, 20, 64, red, alpha=0.85 * k2, font='Special Elite'); c.restore()
        if kind == 'book':
            hl = prog(t, B(S, 1) + 0.3, B(S, 1) + 1.0)
            if hl > 0: glow(c, -250, yN - 10, 220, NEON, 0.2 * hl)
    elif kind == 'news':
        a = prog(t, 0.0, 0.6)
        rect(c, -420, -420, 840, 860, paper, a)
        text(c, P['header'], 0, -360, 34, ink, alpha=a, font='DejaVu Serif'); rect(c, -380, -340, 760, 3, ink, a)
        text(c, P.get('date', ''), 0, -305, 24, ink, alpha=a, font='DejaVu Serif')
        for i, h in enumerate(P['head']): text(c, h, 0, -220 + i * 76, 70, hexc('1a140e'), alpha=a, font='DejaVu Serif')
        text(c, P['sub'], 0, -40, 34, red, alpha=a, font='DejaVu Serif', slant=cairo.FONT_SLANT_ITALIC)
        rect(c, -380, 0, 400, 300, hexc('2a2118'), a * 0.9)
        # photo: bus in water
        quad(c, [(-360, 230), (-20, 230), (-20, 300), (-360, 300)], hexc('3c4a55'), a)
        c.save(); c.translate(-200, 200); c.rotate(0.25); rrect(c, -130, -50, 260, 90, 14); src(c, hexc('8a7a60'), a); c.fill()
        for i in range(5): rect(c, -110 + i * 45, -35, 32, 26, hexc('2a2118'), a)
        c.restore()
        for i in range(9): rect(c, 50, 10 + i * 32, 330 - (i % 3) * 40, 10, hexc('6b5e4a'), a * 0.8)
    elif kind == 'ticket':
        rrect(c, -380, -230, 760, 460, 20); src(c, paper); c.fill()
        for i in range(12): circ(c, -380 + 30 + i * 64, -230, 14, hexc('0b0806')); circ(c, -380 + 30 + i * 64, 230, 14, hexc('0b0806'))
        c.new_path(); c.set_dash([14, 10]); c.move_to(160, -210); c.line_to(160, 210); src(c, ink, 0.5); c.set_line_width(3); c.stroke(); c.set_dash([])
        text(c, 'ROUTE 13', -340, -130, 46, ink, align='l', font='Special Elite')
        text(c, 'HOLLOW CREEK', -340, -70, 36, red, align='l', font='Special Elite')
        text(c, 'ADMIT ONE', 270, -120, 30, ink, font='Special Elite')
        text(c, '13', 270, 40, 120, ink, font='Special Elite')
        for rv in P.get('reveal', []):
            bt = B(S, rv['beat']); k = prog(t, bt + 0.6, bt + 1.4)
            if k <= 0: continue
            if rv['type'] == 'date':
                text(c, 'TOMORROW  ·  2:14 AM', -340, 30, 34, ink, align='l', alpha=k, font='Special Elite')
            if rv['type'] == 'name':
                text(c, 'PASSENGER:', -340, 110, 28, ink, align='l', alpha=k, font='Special Elite')
                text(c, rv['text'], -340, 165, 50, red, align='l', alpha=k, font='Special Elite')
    c.restore()
    if kind == 'ticket': ash(c, T, 0.3, col=hexc('ffd9a0'), up=True)

# ================= BUS SCENES =================
def bus_side(c, x, y, s, T, lit=0.6, door_open=0.0):
    c.save(); c.translate(x, y); c.scale(s, s)
    rrect(c, -380, -170, 760, 300, 30); src(c, hexc('1d2a2e')); c.fill()
    rect(c, -380, 60, 760, 16, hexc('7a1f1f'))
    for i in range(7):
        wx = -350 + i * 92; rrect(c, wx, -140, 76, 100, 8); src(c, mix(hexc('0a1214'), hexc('b8f0d8'), lit * 0.5)); c.fill()
    # front windshield + route sign
    rrect(c, 300, -150, 70, 150, 10); src(c, hexc('0a1214')); c.fill()
    rect(c, 230, -165, 130, 22, hexc('0b0b0b')); text(c, '13', 295, -148, 20, hexc('ffb347'), font='JetBrains Mono')
    # door
    rect(c, 210 - 50 * door_open, -130, 70, 230, hexc('0a1214'))
    if door_open > 0: glow(c, 245, 0, 160, TEAL, 0.25 * door_open)
    for wx in (-250, 230):
        circ(c, wx, 130, 52, hexc('050505')); circ(c, wx, 130, 22, hexc('2a2a2a'))
    circ(c, 372, 60, 14, hexc('fff2c8'))
    c.restore()
    glow(c, x + 372 * s, y + 60 * s, 120 * s, hexc('fff2c8'), 0.6)
    quad(c, [(x + 372 * s, y + 50 * s), (x + 372 * s + 900, y - 60 * s), (x + 372 * s + 900, y + 260 * s)], hexc('fff2c8'), 0.08)

FTREES = [(random.uniform(0, 3000), random.uniform(180, 380)) for _ in range(30)]
def sc_road(c, T, t, d, S, P):
    g = cairo.LinearGradient(0, 0, 0, H); g.add_color_stop_rgba(0, *hexc('05070c')); g.add_color_stop_rgba(1, *hexc('141a24'))
    c.set_source(g); c.paint()
    circ(c, 820, 360, 70, hexc('d9dfe8'), 0.85); glow(c, 820, 360, 300, hexc('9fb3dd'), 0.15)
    fog(c, T, 0.8, y0=500, y1=1300)
    for x, h in FTREES:
        xx = (x - T * 140) % 3000 - 400
        quad(c, [(xx, 1150 - h * 1.8), (xx - h * 0.3, 1160), (xx + h * 0.3, 1160)], hexc('04060a'))
    rect(c, 0, 1150, W, 800, hexc('07090c'))
    for i in range(10):
        xx = (i * 240 - T * 600) % (W + 240) - 120; rect(c, xx, 1290, 120, 10, hexc('c9b26a'), 0.5)
    sign_x = 1200 - (t - 1.0) * 600
    if -200 < sign_x < 1300:
        rect(c, sign_x, 900, 10, 260, hexc('1a1a1a')); rect(c, sign_x - 70, 880, 150, 60, hexc('1f3b2a'))
        text(c, 'RT 13', sign_x + 5, 922, 28, WHITE, font='JetBrains Mono')
    bus_side(c, 500, 1080 + 3 * math.sin(T * 9), 0.95, T, lit=0.7)
    fog(c, T * 1.4, 0.6, y0=900, y1=1500)
    a = prog(t, 0.6, 1.0) * (1 - prog(t, d - 1.2, d - 0.6)); s = '2:14 AM'; n = int(clamp((t - 0.6) / 0.8) * len(s))
    text(c, s[:n], 90, 1420, 64, WHITE, align='l', alpha=a, font='JetBrains Mono')

def bus_interior(c, T, t, S, P, mirror_empty, woman_vis=1.0, mirror_zoom=0.0):
    # windshield view from behind the driver
    rect(c, -400, -400, W + 800, H + 800, hexc('0a0f10'))
    # windshield
    wy0, wy1 = 300, 1050
    g = cairo.LinearGradient(0, wy0, 0, wy1); g.add_color_stop_rgba(0, *hexc('04070b')); g.add_color_stop_rgba(1, *hexc('101820'))
    c.set_source(g); c.rectangle(40, wy0, W - 80, wy1 - wy0); c.fill()
    vx, vy = W / 2, 760
    quad(c, [(vx - 8, vy), (vx + 8, vy), (W - 40, wy1), (40, wy1)], hexc('0d1014'))
    for i in range(6):
        f = ((T * 1.2 + i / 6) % 1) ** 2
        y = vy + (wy1 - vy) * f; w = 4 + 20 * f; rect(c, vx - w / 2, y, w, 30 * f + 2, hexc('c9b26a'), 0.6)
    quad(c, [(vx - 60, vy - 10), (vx + 60, vy - 10), (W - 40, wy1), (40, wy1)], hexc('fff2c8'), 0.06)
    c.save(); c.rectangle(40, wy0, W - 80, wy1 - wy0); c.clip(); fog(c, T, 1.0, y0=600, y1=1000); c.restore()
    c.new_path(); c.rectangle(40, wy0, W - 80, wy1 - wy0); src(c, hexc('050707')); c.set_line_width(30); c.stroke()
    # dashboard
    rect(c, -400, 1050, W + 800, 900, hexc('0c1112')); rect(c, -400, 1050, W + 800, 10, TEAL, 0.15)
    glow(c, 820, 1100, 120, TEAL, 0.25)
    # mirror
    mx, my, mw, mh = 600, 330, 360, 140
    rrect(c, mx, my, mw, mh, 18); src(c, hexc('020303')); c.fill()
    c.save(); rrect(c, mx + 10, my + 10, mw - 20, mh - 20, 12); c.clip()
    rect(c, mx, my, mw, mh, hexc('16201f'))
    for i in range(4):
        rect(c, mx + 20 + i * 90, my + 70, 70, 60, hexc('0b1110'))
    if not mirror_empty and woman_vis > 0:
        person(c, mx + 230, my + 70, 0.35, rim=TEAL, rim_dir=(0, -1), rim_a=0.5, hair=True, eye=0.9, eye_col=hexc('e8fff6'), alpha=woman_vis)
    glow(c, mx + mw / 2, my + mh / 2, 200, TEAL, 0.08)
    c.restore()
    # driver from behind + wheel
    person(c, 330, 1180, 1.25, rim=TEAL, rim_dir=(0.5, -1), rim_a=0.45)
    c.save(); c.translate(380, 1450); c.scale(1, 0.4); c.new_path(); c.arc(0, 0, 230, 0, 2 * PI); src(c, hexc('050707')); c.set_line_width(40); c.stroke(); c.restore()

def sc_bus(c, T, t, d, S, P):
    wv = prog(t, B(S, 0) + 0.8, B(S, 0) + 1.8)
    z = 1.0 + 0.25 * smooth(prog(t, B(S, 1) - 0.3, B(S, 1) + 1.5)) - 0.1 * smooth(prog(t, B(S, 2), B(S, 2) + 1.0)) + 0.2 * smooth(prog(t, B(S, 3), d))
    c.save(); camera(c, 700, 600 + 200 * (1 - smooth(prog(t, B(S, 1) - 0.3, B(S, 1) + 1.5))), z, shake=0.04, T=T)
    bus_interior(c, T, t, S, P, mirror_empty=False, woman_vis=wv)
    c.restore()

def sc_mirror(c, T, t, d, S, P):
    z = 2.1 + 0.4 * smooth(t / d)
    c.save(); camera(c, 780, 420, z, shake=0.03, T=T)
    empty = t > B(S, 0) + 1.6
    bus_interior(c, T, t, S, P, mirror_empty=empty)
    c.restore()
    if empty:
        k = prog(t, B(S, 1), B(S, 1) + 2)
        # breath fog on the glass
        glow(c, 540, 1100, 320 + 60 * math.sin(T * 2.4), hexc('cfe4ff'), 0.12 * k * (0.5 + 0.5 * math.sin(T * 2.4)))

def sc_sign(c, T, t, d, S, P):
    rect(c, 0, 0, W, H, hexc('06090c'))
    vx, vy = W / 2, 820
    quad(c, [(vx - 10, vy), (vx + 10, vy), (W + 400, H), (-400, H)], hexc('0d1014'))
    for i in range(8):
        f = ((T * 0.9 + i / 8) % 1) ** 2; y = vy + (H - vy) * f; w = 4 + 40 * f; rect(c, vx - w / 2, y, w, 60 * f + 2, hexc('c9b26a'), 0.5)
    quad(c, [(vx - 80, vy - 30), (vx + 80, vy - 30), (W + 300, H), (-300, H)], hexc('fff2c8'), 0.07)
    k = smooth(prog(t, B(S, 0) + 0.4, d))
    s = 0.25 + 1.1 * k; sx = vx + 160 + 330 * k; sy = vy + 20 + 160 * k
    c.save(); c.translate(sx, sy); c.scale(s, s)
    rect(c, -8, -320, 16, 520, hexc('1a1a1a'))
    rect(c, -150, -420, 300, 150, hexc('233a2b')); c.new_path(); c.rectangle(-150, -420, 300, 150); src(c, hexc('e6e6d8'), 0.7); c.set_line_width(6); c.stroke()
    text(c, 'HOLLOW', 0, -360, 46, hexc('e6e6d8'), font='Special Elite'); text(c, 'CREEK', 0, -300, 46, hexc('e6e6d8'), font='Special Elite')
    # figure by the sign
    person(c, -130, -70, 0.55, rim=hexc('e6e6d8'), rim_dir=(-1, -0.4), rim_a=0.4, hair=True, eye=prog(t, B(S, 1), B(S, 1) + 0.6), eye_col=hexc('e8fff6'))
    c.restore()
    glow(c, sx, sy - 300 * s, 250 * s, hexc('fff2c8'), 0.12)
    fog(c, T, 1.4, y0=500, y1=1300)

def sc_stop(c, T, t, d, S, P):
    rect(c, 0, 0, W, H, hexc('090c10'))
    fog(c, T, 1.0, y0=300, y1=1400)
    rect(c, 0, 1250, W, 700, hexc('07090b'))
    door = prog(t, B(S, 0) - 0.2, B(S, 0) + 0.6)
    bx = 150
    c.save(); camera(c, 540, 1000, 1.0 + 0.1 * t / d)
    bus_side(c, bx, 1080, 0.75, T, lit=0.8, door_open=door)
    bb = P.get('board_beat', 2); board = prog(t, B(S, bb) + 0.5, B(S, bb) + 4.0)
    n = 8
    for i in range(n):
        base_x = 560 + i * 70; sc = 0.42 - i * 0.012
        appear = prog(t, B(S, 1) + i * 0.12, B(S, 1) + 0.8 + i * 0.12)
        mv = clamp(board * n - i * 0.6) ; mv = 0 if i == 2 else mv; x = base_x - (base_x - (bx + 185)) * smooth(mv)
        a = appear * (1 - prog(mv, 0.85, 1.0))
        if a <= 0: continue
        person(c, x, 1010 + (i % 2) * 8, sc, rim=hexc('b9c3d6'), rim_dir=(-1, -0.3), rim_a=0.35, alpha=a, hair=(i in (2, 5)),
               eye=0.7 if i == 2 and t > B(S, 4) else 0, eye_col=hexc('e8fff6'))
    c.restore()
    fog(c, T * 1.3, 1.2, y0=800, y1=1500)
    rain(c, T, 0.3)

def sc_dawn(c, T, t, d, S, P):
    k = smooth(prog(t, 0, d))
    rect(c, 0, 0, W, H, mix(hexc('101418'), hexc('3a2a22'), k))
    # aisle perspective
    vx, vy = W / 2, 760
    quad(c, [(-300, -300), (W + 300, -300), (vx + 90, vy - 120), (vx - 90, vy - 120)], mix(hexc('0c0f12'), hexc('5a4030'), k))
    quad(c, [(-300, H + 300), (W + 300, H + 300), (vx + 90, vy + 120), (vx - 90, vy + 120)], mix(hexc('0e1112'), hexc('2a1f18'), k))
    for side in (-1, 1):
        for i in range(6):
            f = 0.15 + i * 0.14
            x = vx + side * (90 + (W / 2 + 200) * (1 - f) ** 1.5); y = vy + 120 + (H - vy) * (1 - f) ** 1.5 * 0.9
            s = (1 - f) ** 1.5 * 2.2 + 0.2
            rrect(c, x - (side < 0) * 200 * s, y - 220 * s, 200 * s, 230 * s, 20 * s); src(c, mix(hexc('1a2224'), hexc('6b3a2a'), k)); c.fill()
            # window light
            wx = x + side * 60 * s; glow(c, wx, y - 400 * s, 300 * s, hexc('ffb36b'), 0.25 * k)
    # sun rays
    for i in range(5):
        quad(c, [(W, 200 + i * 80), (W, 260 + i * 80), (100, 1500 + i * 60), (60, 1400 + i * 60)], hexc('ffd09a'), 0.05 * k)
    ash(c, T, 0.5 * k, col=hexc('ffe2b8'))

def sc_title(c, T, t, d, S, P):
    TT = TM['title']; rect(c, 0, 0, W, H, BLACK)
    g = random.Random(int(T * 20)); a = prog(t, 0.3, 0.6); glitch = 1 if g.random() < 0.12 and t < 2.5 else 0
    if glitch:
        text(c, TT['series'], W / 2 - 6, 860, 130, hexc('00e5ff'), alpha=0.6 * a, spacing=6); text(c, TT['series'], W / 2 + 6, 860, 130, NEON, alpha=0.6 * a, spacing=6)
    else: text(c, TT['series'], W / 2, 860, 130, NEON, alpha=a, spacing=6)
    glow(c, W / 2, 820, 420, NEON, 0.12 * a)
    text(c, TT['ep'], W / 2, 960, 40, hexc('c9c9d1'), alpha=prog(t, 0.9, 1.3), spacing=3, weight=cairo.FONT_WEIGHT_NORMAL)
    b = prog(t, 1.8, 2.2)
    text(c, TT['l1'], W / 2, 1180, 52, WHITE, alpha=b); text(c, TT['l2'], W / 2, 1250, 40, hexc('9a9aa8'), alpha=b, weight=cairo.FONT_WEIGHT_NORMAL)

SCENES = {'exterior': sc_exterior, 'hall': sc_hall, 'behind': sc_behind, 'room': sc_room, 'book': paper_scene,
          'logbook': paper_scene, 'news': paper_scene, 'ticket': paper_scene, 'room_phone': sc_room_phone,
          'desk_other': sc_desk_other, 'road': sc_road, 'bus': sc_bus, 'mirror': sc_mirror, 'sign': sc_sign,
          'stop': sc_stop, 'dawn': sc_dawn, 'title': sc_title}

# ===================== CHARACTER FACE SCENES =====================
import chars as CH
CHAR_OF = {'daniel': 'daniel', 'other': 'double', 'marcus': 'marcus', 'woman': 'woman'}
def mouth_for(who, T):
    for l in LINES:
        if l['who'] == who and l.get('fx') != 'phone' and 'env' in l and l['start'] <= T < l['start'] + l['dur']:
            i = int((T - l['start']) * 30); e = l['env']
            v = (e[max(0, i - 1)] + 2 * e[min(i, len(e) - 1)] + e[min(i + 1, len(e) - 1)]) / 4
            return clamp(v * 0.95)
    return 0.0
def speaking(who, T):
    return any(l['who'] == who and l['start'] <= T < l['start'] + l['dur'] for l in LINES)
def cut(c, t, at, dur=0.07):
    if at <= t < at + dur: rect(c, 0, 0, W, H, BLACK)
def face(c, who, x, y, s, T, **kw):
    spk = {'daniel': 'daniel', 'double': 'other', 'marcus': 'marcus', 'woman': 'woman'}[who]
    kw.setdefault('mouth', mouth_for(spk, T))
    CH.draw(c, who, x, y, s, T=T, **kw)
def handset_at(c, x, y, s, ang=-0.9):
    c.save(); c.translate(x, y); c.rotate(ang); c.scale(s, s); c.new_path()
    c.move_to(-95, 0); c.curve_to(-60, -42, 60, -42, 95, 0); c.line_to(85, 30); c.line_to(-85, 30); c.close_path(); src(c, hexc('16110d')); c.fill()
    c.restore()

def desk_front(c, T, lamp=1.0):
    rect(c, -400, 1250, W + 800, 900, hexc('1c130c')); rect(c, -400, 1250, W + 800, 14, AMBER, 0.35)
    g = cairo.LinearGradient(0, 1250, 0, 1600); g.add_color_stop_rgba(0, 1, 0.7, 0.3, 0.12 * lamp); g.add_color_stop_rgba(1, 0, 0, 0, 0)
    c.set_source(g); c.rectangle(-400, 1250, W + 800, 400); c.fill()
    quad(c, [(760, 1250), (790, 1060), (810, 1060), (840, 1250)], hexc('100c08'))
    quad(c, [(720, 1080), (880, 1080), (840, 990), (760, 990)], hexc('2b2015'))
    glow(c, 800, 1090, 120, AMBER, 0.8 * lamp)

def sc_desk(c, T, t, d, S, P):
    b0, b1, b2, b3 = B(S, 0), B(S, 1), B(S, 2), B(S, 3)
    rin = ringing(T)
    pick = b2 - 0.3
    push = smooth(prog(t, b3, b3 + 2.5))
    z = 1.0 + 0.06 * t / d + 0.9 * push
    c.save(); camera(c, 540 - 120 * push, 1010 - 110 * push, z, shake=0.15 * rin, T=T)
    interior_bg(c, T, flash(T) * 0.4)
    # Daniel
    look_phone = smooth(prog(t, (TM['rings'][0] - S['start']) + 0.2 if TM['rings'] else 99, (TM['rings'][0] - S['start']) + 0.7 if TM['rings'] else 99))
    up = t >= pick
    turn = 0.15 + 0.3 * look_phone * (1 - smooth(prog(t, pick + 0.2, pick + 0.8)))
    look = (0.2 + 0.8 * look_phone, 0.7 * (1 - look_phone) + 0.2 * look_phone)
    if up: look = (0.1 + 0.25 * math.sin(t * 0.7), 0.0)
    expr, expr2, ek = 'neutral', 'worried', smooth(prog(t, b0, b0 + 1.0))
    if t > b3 + 1.2: expr, expr2, ek = 'worried', 'fear', smooth(prog(t, b3 + 1.2, b3 + 3.0))
    face(c, 'daniel', 420, 900, 1.15, T, turn=turn, look=look, expr=expr, expr2=expr2, ek=ek, light=(1, -0.3), light_col=AMBER, ambient=0.8)
    if up:
        handset_at(c, 560, 900, 0.9, -1.25)
        CH.hand(c, 560, 960, 1.0, CH.CHARS['daniel']['skin'], 0.3)
    desk_front(c, T)
    phone(c, 760, 1250, 1.0, T, rin, prog(t, b1 - 0.3, b1 + 0.2), up)
    if up:
        c.new_path(); c.move_to(700, 1225); c.curve_to(700, 1300, 600, 1150, 560, 990); src(c, hexc('2c241e')); c.set_line_width(5); c.stroke()
    if rin:
        for k in range(3):
            r = ((T * 260) + k * 70) % 210; c.new_path(); c.arc(760, 1190, 60 + r, PI * 1.15, PI * 1.85); src(c, AMBER, 0.6 * (1 - r / 210)); c.set_line_width(5); c.stroke()
    c.restore()
    for l in LINES:
        if l['who'] == 'caller' and l.get('fx') == 'phone' and l['start'] <= T <= l['start'] + l['dur']:
            k = T - l['start']; c.set_source_rgba(1, 0.2, 0.3, 0.7); c.set_line_width(4); c.new_path()
            for i in range(40):
                h = 10 + 50 * abs(math.sin(k * 9 + i * 1.7)) * abs(math.sin(i * 0.4 + k * 3))
                c.move_to(340 + i * 10, 1450 - h / 2); c.line_to(340 + i * 10, 1450 + h / 2)
            c.stroke()

def sc_keys(c, T, t, d, S, P):
    b0, b1 = B(S, 0), B(S, 1)
    if t < b1:
        mem = prog(t, b0 + 2.6, b0 + 3.3)   # newspaper memory near the end of the first line
        if mem < 1:
            c.save(); camera(c, 540, 860, 1.0 + 0.12 * t / b1)
            rect(c, -400, -400, W + 800, H + 800, hexc('0d0a09')); glow(c, 900, 1000, 900, AMBER, 0.25)
            face(c, 'daniel', 540, 820, 2.6, T, turn=0.05, look=(-0.2 + 0.4 * math.sin(t * 0.6), 0.1), expr='worried', expr2='shock', ek=smooth(prog(t, 0.2, 1.0)),
                 light=(1, -0.2), light_col=AMBER, ambient=0.7, mouth=0.08)
            c.restore()
        if mem > 0:
            c.push_group()
            rect(c, 0, 0, W, H, hexc('0b0806'))
            for i in range(60):
                r = random.Random(i); x = r.uniform(0, W); sp = r.uniform(60, 180); y = H - ((t * sp + r.uniform(0, H)) % H)
                circ(c, x + 20 * math.sin(t * 2 + i), y, r.uniform(2, 5), hexc('ff7a2e'), 0.6)
            glow(c, W / 2, 1500, 900, hexc('ff5a1e'), 0.22)
            c.save(); c.translate(W / 2, 900); c.rotate(-0.05 + 0.02 * t); sc = 0.9 + 0.05 * t; c.scale(sc, sc)
            rect(c, -400, -330, 800, 660, hexc('d8ccae'))
            text(c, 'THE DAILY HERALD', 0, -270, 34, hexc('2a2118'), font='DejaVu Serif'); rect(c, -360, -250, 720, 3, hexc('2a2118'))
            text(c, 'FIRE AT PINEWOOD', 0, -175, 64, hexc('1a140e'), font='DejaVu Serif'); text(c, 'MOTEL', 0, -105, 64, hexc('1a140e'), font='DejaVu Serif')
            text(c, 'Room 9 sealed after tragedy', 0, -45, 34, hexc('5a1a10'), font='DejaVu Serif', slant=cairo.FONT_SLANT_ITALIC)
            rect(c, -360, -10, 340, 260, hexc('2a2118'), 0.85)
            quad(c, [(-340, 250), (-270, 120), (-200, 170), (-120, 60), (-40, 250)], hexc('5c4a36'))
            for i in range(8): rect(c, 10, i * 30, 350 - (i % 3) * 40, 10, hexc('6b5e4a'), 0.8)
            c.restore(); c.pop_group_to_source(); c.paint_with_alpha(mem)
        return
    tt = t - b1; k = smooth(prog(tt, 0.8, 3.2))
    c.save(); camera(c, 800 - (800 - 690) * k, 650 + (790 - 650) * k, 1.0 + 1.6 * k)
    interior_bg(c, T, 0)
    hx, hy = 690, 760
    pulse = prog(tt, 2.6, 3.0) * (0.6 + 0.4 * math.sin(T * 8))
    glow(c, hx, hy + 30, 70, NEON, 0.5 * pulse); text(c, '9', hx + 18, hy - 10, 18, NEON, alpha=pulse)
    c.restore()

def sc_behind(c, T, t, d, S, P):
    fl = flash(T); recap = P.get('recap')
    z = 1.0 + 0.15 * smooth(t / d)
    c.save(); camera(c, W / 2, 900, z, shake=fl * 0.6, T=T)
    rect(c, -400, -400, W + 800, H + 800, mix(hexc('07080b'), hexc('8193b8'), fl * 0.9))
    rect(c, 230, 300, 620, 1300, mix(hexc('030304'), hexc('1a1d26'), fl))
    c.new_path(); c.rectangle(230, 300, 620, 1300); src(c, mix(hexc('1b1610'), hexc('c7d2ea'), fl)); c.set_line_width(26); c.stroke()
    text(c, '9', 540, 270, 60, mix(hexc('6b5b40'), WHITE, fl))
    if recap: seen = clamp(fl * 1.5 + 0.35); eyes = 1.0; lean = 1.0; hp = 1.0; b0 = -5; b1 = -5
    else:
        b0, b1 = B(S, 0), B(S, 1)
        seen = clamp(fl * 1.5 + 0.35 * prog(t, b0 + 0.2, b0 + 1.6)); eyes = prog(t, b0 + 0.6, b0 + 1.4)
        lean = smooth(prog(t, b1 + 1.5, d)); hp = smooth(prog(t, b1 + 2.6, b1 + 3.4))
    creature(c, 640, 820 + 80 * lean, 1.15 + 0.25 * lean, seen, eyes=eyes, lean=lean)
    side = smooth(prog(t, b0 + 0.6, b0 + 1.4))
    face(c, 'daniel', 470, 1130, 1.6, T, turn=-0.1 + 0.15 * side, look=(0.9 * side, -0.1 * side), expr='worried', expr2='fear', ek=max(side, 1.0 if recap else 0),
         light=(-0.3, 1), light_col=COLD, ambient=0.4 + 0.4 * fl, under=True, mouth=0.12 + 0.04 * math.sin(T * 20))
    if hp > 0:
        c.save(); c.translate(760 - 40 * hp, 1360 - 40 * hp)
        for i in range(4):
            c.new_path(); c.move_to(i * 22, 0); c.curve_to(i * 22 - 5, 60 * hp, i * 22 - 10, 110 * hp, i * 22 - 18, 150 * hp)
            src(c, hexc('020203')); c.set_line_width(14); c.set_line_cap(cairo.LINE_CAP_ROUND); c.stroke()
        quad(c, [(-20, -60), (90, -60), (80, 30), (-10, 30)], hexc('020203')); c.restore()
    c.restore()
    if fl > 0: rect(c, 0, 0, W, H, WHITE, fl * 0.3)

_old_hall = sc_hall
def sc_hall(c, T, t, d, S, P):
    walker = P.get('walker', True) and not P.get('run')
    _old_hall(c, T, t, d, S, dict(P, walker=False))
    if walker:
        bob = math.sin(t * 6) * 6
        CH.draw(c, 'daniel', 300, 1500 + bob * 0.5, 1.5, T=T, back=True, light=(0.5, -1), light_col=COLD, ambient=0.35)
        c.new_path(); c.move_to(470, 1800); c.line_to(560, 1580); c.set_line_width(70); src(c, hexc('1c241c')); c.stroke()

def sc_room_phone(c, T, t, d, S, P):
    b0, b1, b2 = B(S, 0), B(S, 1), B(S, 2)
    rin = ringing(T) and t < b1
    push = smooth(prog(t, b2 - 0.3, d))
    c.save(); camera(c, 620 - 100 * push, 900 - 40 * push, 1.0 + 0.6 * push, shake=0.2 * rin + 0.3 * prog(t, b2 + 1.2, b2 + 1.6) * (1 - prog(t, d - 0.4, d)), T=T)
    burnt_room(c, T, flash(T))
    px, py = 800, 820
    c.save(); c.translate(px + (math.sin(T * 90) * 4 if rin else 0), py)
    rrect(c, -80, -120, 160, 240, 18); src(c, hexc('1a1512')); c.fill(); circ(c, 0, 30, 52, hexc('0d0a08'))
    for i in range(10): a = -PI * 0.2 + i * PI * 0.15; circ(c, 34 * math.cos(a), 30 + 34 * math.sin(a), 7, hexc('2c241e'))
    if t < b1 - 0.3:
        c.new_path(); c.move_to(-95, -100); c.curve_to(-60, -150, 60, -150, 95, -100); c.line_to(80, -80); c.line_to(-80, -80); c.close_path(); src(c, hexc('120e0b')); c.fill()
    c.restore()
    if rin:
        for k in range(3):
            r = ((T * 260) + k * 70) % 210; c.new_path(); c.arc(px, py - 100, 70 + r, PI * 1.1, PI * 1.9); src(c, AMBER, 0.5 * (1 - r / 210)); c.set_line_width(5); c.stroke()
    up = t >= b1 - 0.3
    hear = smooth(prog(t, b2 + 0.3, b2 + 1.0))
    expr = 'worried' if not hear else 'worried'
    face(c, 'daniel', 470, 860, 1.3, T, turn=0.55, look=(0.8, -0.1) if not up else (0.3 - 0.3 * hear, 0.1), expr='worried', expr2='shock', ek=hear,
         light=(1, -0.2), light_col=COLD, ambient=0.6)
    if up:
        c.new_path(); c.move_to(px - 40, py + 40); c.curve_to(px - 30, py + 260, 700, 1000, 640, 900); src(c, hexc('2c241e')); c.set_line_width(5); c.stroke()
        handset_at(c, 600, 860, 0.95, -1.2); CH.hand(c, 610, 930, 1.05, CH.CHARS['daniel']['skin'], 0.4)
    c.restore()
    ash(c, T, 0.6); flashlight(c, 600, 860, r0=160, r1=850, dark=0.7)
    if hear > 0:
        g = cairo.RadialGradient(W / 2, H / 2, 200, W / 2, H / 2, 1200); g.add_color_stop_rgba(0, 0.5, 0, 0, 0); g.add_color_stop_rgba(1, 0.5, 0, 0.02, 0.5 * hear * (0.7 + 0.3 * math.sin(T * 6)))
        c.set_source(g); c.paint()

def sc_desk_other(c, T, t, d, S, P):
    b0, b1, b2, b3, b4 = [B(S, i) for i in range(5)]
    if t < b2:  # wide: someone in the chair, seen from behind
        c.save(); camera(c, 540, 1000, 1.0 + 0.08 * t / b2)
        interior_bg(c, T, flash(T) * 0.4, lamp=0.9)
        rrect(c, 390, 980, 300, 320, 40); src(c, hexc('120c08')); c.fill()
        CH.draw(c, 'double', 540, 930, 0.9, T=T, back=True, light=(1, -0.5), light_col=AMBER, ambient=0.7)
        desk_front(c, T, 0.9)
        c.restore()
        CH.draw(c, 'daniel', 170, 1480, 1.6, T=T, back=True, light=(0.6, -1), light_col=AMBER, ambient=0.4)
    elif t < b3:  # Daniel reacts
        cut(c, t, b2)
        c.save(); camera(c, 540, 900, 1.0 + 0.1 * (t - b2))
        rect(c, -400, -400, W + 800, H + 800, hexc('0c0d10')); glow(c, 700, 900, 800, AMBER, 0.2)
        face(c, 'daniel', 520, 860, 2.4, T, turn=0.2, look=(0.5, 0), expr='worried', expr2='fear', ek=0.4, light=(1, -0.2), light_col=AMBER, ambient=0.75)
        c.restore(); cut(c, t, b2)
    elif t < b4:  # the double turns around
        tt = t - b3; turn_k = smooth(prog(tt, 0.3, 1.4)); zoom = smooth(prog(tt, 1.6, 3.0))
        c.save(); camera(c, 540, 1000 - 120 * zoom, 1.0 + 1.0 * zoom)
        interior_bg(c, T, 0, lamp=0.9 + 0.1 * math.sin(T * 13))
        rrect(c, 390, 980, 300, 320, 40); src(c, hexc('120c08')); c.fill()
        if turn_k < 1: CH.draw(c, 'double', 540, 930, 0.9, T=T, back=True, light=(1, -0.5), light_col=AMBER, ambient=0.7, alpha=1 - turn_k)
        if turn_k > 0: face(c, 'double', 540, 930, 0.9, T, turn=0.6 * (1 - turn_k), expr='neutral', expr2='sinister', ek=zoom, light=(1, -0.3), light_col=AMBER, ambient=0.7, alpha=turn_k)
        desk_front(c, T, 0.9)
        c.restore(); cut(c, t, b3)
    else:  # it speaks
        cut(c, t, b4)
        c.save(); camera(c, 540, 880, 1.0 + 0.15 * (t - b4) / max(0.1, d - b4))
        rect(c, -400, -400, W + 800, H + 800, hexc('0d0a09')); glow(c, 860, 1000, 900, AMBER, 0.3 * (0.9 + 0.1 * math.sin(T * 13)))
        face(c, 'double', 540, 860, 2.5, T, turn=0.0, look=(0, 0), expr='sinister', light=(1, -0.3), light_col=AMBER, ambient=0.7, eyes_glow=0.6)
        c.restore()

_old_paper = paper_scene
def paper_scene(c, T, t, d, S, P):
    f = P.get('face')
    if f and t >= B(S, f['beat']) - 0.1:
        tt = t - B(S, f['beat']); cut(c, tt, -0.1)
        c.save(); camera(c, 540, 880, 1.0 + 0.1 * tt)
        rect(c, -400, -400, W + 800, H + 800, hexc('0d0a09')); glow(c, 540, 1300, 900, AMBER, 0.25)
        face(c, f['who'], 540, 860, 2.4, T, turn=0.0, look=(0, 0.6), expr='shock', light=(0, 1), light_col=AMBER, ambient=0.65, under=True)
        c.restore(); return
    _old_paper(c, T, t, d, S, P)

def bus_aisle(c, T, light=TEAL, warm=0.0, woman=None):
    rect(c, -400, -400, W + 800, H + 800, mix(hexc('0a1012'), hexc('3a2a22'), warm))
    vx, vy = 360, 700
    quad(c, [(-400, -400), (W + 400, -400), (vx + 70, vy - 90), (vx - 70, vy - 90)], mix(hexc('0e1416'), hexc('6a4a36'), warm))
    quad(c, [(-400, H + 400), (W + 400, H + 400), (vx + 70, vy + 90), (vx - 70, vy + 90)], mix(hexc('0c1011'), hexc('2a1f18'), warm))
    # rear window with streaking lights
    rect(c, vx - 70, vy - 90, 140, 180, mix(hexc('05080a'), hexc('ffb36b'), warm * 0.6))
    for i in range(6):  # ceiling light strips
        f = (i + 1) / 7; y = vy - 90 - (vy + 400) * (1 - f) ** 1.4
        if y > -400: rect(c, vx - 60 * (1 + 4 * (1 - f)), y, 120 * (1 + 4 * (1 - f)), 6 + 10 * (1 - f), light, 0.35 * (1 - warm))
    for side in (-1, 1):
        for i in range(6):
            f = 0.12 + i * 0.15; k = (1 - f) ** 1.5
            x = vx + side * (80 + 900 * k); y = vy + 90 + 1100 * k * 0.8; s = 0.25 + 2.0 * k
            rrect(c, x - (side < 0) * 180 * s, y - 230 * s, 180 * s, 240 * s, 18 * s); src(c, mix(hexc('1a2426'), hexc('6b3a2a'), warm)); c.fill()
            # passing streetlight on side windows
            wy = y - 420 * s; ph = (T * 0.8 + i * 0.37) % 1
            glow(c, x + side * 40 * s, wy, 160 * s, mix(hexc('ffd9a0'), hexc('ffb36b'), warm), (0.5 * max(0, 1 - abs(ph - 0.5) * 6)) * (1 - warm) + 0.3 * warm)
    if woman:
        wx, wy, ws, wa = woman
        rrect(c, wx - 70, wy + 40, 140, 160, 14); src(c, hexc('1a2426')); c.fill()
        face(c, 'woman', wx, wy, ws, T, turn=0.15, look=(0.2, 0.1), expr='calm', light=(0, -1), light_col=TEAL, ambient=0.75, alpha=wa)
        rrect(c, wx - 80, wy + 110, 160, 120, 14); src(c, hexc('1a2426')); c.fill()

def sc_bus(c, T, t, d, S, P):
    b0, b1, b2, b3 = [B(S, i) for i in range(4)]
    wv = prog(t, b0 + 0.8, b0 + 1.8)
    onW = 1 if (b1 <= t < b2) or t >= b3 else 0
    tgt = 'woman' if onW else 'marcus'
    if tgt == 'woman':
        c.save(); camera(c, 360, 660, 2.4 + 0.1 * math.sin(t * 0.5))
        bus_aisle(c, T, woman=(360, 650, 0.32, 1.0)); c.restore()
        cut(c, t, b1); cut(c, t, b3)
        return
    c.save(); camera(c, 540, 960, 1.0 + 0.04 * math.sin(t * 0.6), shake=0.04, T=T)
    walkin = 1 - smooth(prog(t, b0 + 0.2, b0 + 2.0))
    bus_aisle(c, T, woman=(360, 650 + 250 * walkin, 0.32 + 0.3 * walkin, wv))
    glance = smooth(prog(t, b2 + 0.4, b2 + 1.0))
    face(c, 'marcus', 760, 1080, 1.55, T, turn=-0.35 - 0.2 * glance, look=(-0.6 * glance, -0.4 * glance), expr='neutral', expr2='worried', ek=prog(t, b1, b1 + 1.0),
         light=(1, -0.5), light_col=TEAL, ambient=0.7)
    c.save(); c.translate(700, 1700); c.scale(1, 0.35); c.new_path(); c.arc(0, 0, 330, 0, 2 * PI); src(c, hexc('050707')); c.set_line_width(46); c.stroke(); c.restore()
    CH.hand(c, 440, 1690, 1.3, CH.CHARS['marcus']['skin'], -0.9); CH.hand(c, 960, 1690, 1.3, CH.CHARS['marcus']['skin'], 0.9)
    c.restore(); cut(c, t, b2)

def sc_mirror(c, T, t, d, S, P):
    b0, b1 = B(S, 0), B(S, 1)
    empty = t > b0 + 1.6
    c.save(); camera(c, 540, 900, 1.0 + 0.1 * t / d, shake=0.03, T=T)
    rect(c, -400, -400, W + 800, H + 800, hexc('0a1012'))
    # mirror at top
    mx, my, mw, mh = 220, 300, 640, 260
    rrect(c, mx - 14, my - 14, mw + 28, mh + 28, 30); src(c, hexc('020303')); c.fill()
    c.save(); rrect(c, mx, my, mw, mh, 22); c.clip()
    c.translate(mx + mw / 2, my + mh / 2); c.scale(0.38, 0.38); c.translate(-360, -680)
    bus_aisle(c, T, woman=None if empty else (360, 650, 0.32, 1.0))
    c.restore()
    glow(c, mx + mw / 2, my + mh / 2, 300, TEAL, 0.06)
    shock = smooth(prog(t, b0 + 1.6, b0 + 2.2)); fear = smooth(prog(t, b1, b1 + 1.5))
    face(c, 'marcus', 540, 1180, 2.2, T, turn=0.0, look=(0.0, -1.0 + 0.6 * fear * math.sin(t * 2)), expr='worried', expr2='shock' if fear < 0.5 else 'fear', ek=max(shock, fear),
         light=(0, -1), light_col=TEAL, ambient=0.65, mouth=0.15 * shock)
    c.restore()
    if empty:
        k = prog(t, b1, b1 + 2)
        glow(c, 540, 1000, 320 + 60 * math.sin(T * 2.4), hexc('cfe4ff'), 0.14 * k * (0.5 + 0.5 * math.sin(T * 2.4)))

_old_sign = sc_sign
def sc_sign(c, T, t, d, S, P):
    b1 = B(S, 1)
    if t < b1 - 0.1: return _old_sign(c, T, t, d, S, P)
    cut(c, t, b1 - 0.1)
    c.save(); camera(c, 540, 860, 1.0 + 0.2 * smooth(prog(t, b1, d)))
    rect(c, -400, -400, W + 800, H + 800, hexc('06090c')); glow(c, 540, 700, 900, hexc('fff2c8'), 0.18)
    fog(c, T, 1.0, y0=200, y1=1500)
    face(c, 'woman', 540, 860, 2.4, T, turn=0.0, look=(0, 0), expr='calm', expr2='sinister', ek=smooth(prog(t, b1 + 1.0, b1 + 2.0)), light=(0, -1), light_col=hexc('fff2c8'), ambient=0.8, eyes_glow=0.4)
    c.restore(); fog(c, T * 1.3, 0.8, y0=900, y1=1700)

_old_stop = sc_stop
def sc_stop(c, T, t, d, S, P):
    b3, b4 = B(S, 3), B(S, 4)
    if t < b3 - 0.1: return _old_stop(c, T, t, d, S, P)
    if t < b4 - 0.1:
        c.save(); camera(c, 540, 900, 1.0 + 0.05 * (t - b3))
        rect(c, -400, -400, W + 800, H + 800, hexc('0a1012')); glow(c, 300, 800, 800, TEAL, 0.25)
        face(c, 'marcus', 560, 880, 2.3, T, turn=-0.35, look=(-0.7, 0), expr='worried', light=(-1, -0.3), light_col=TEAL, ambient=0.7)
        c.restore(); cut(c, t, b3 - 0.1); return
    cut(c, t, b4 - 0.1)
    c.save(); camera(c, 540, 880, 1.0 + 0.12 * (t - b4) / max(0.1, d - b4))
    rect(c, -400, -400, W + 800, H + 800, hexc('090c10')); fog(c, T, 1.2, y0=200, y1=1600)
    glow(c, 300, 900, 700, TEAL, 0.2)
    face(c, 'woman', 540, 860, 2.4, T, turn=0.1, look=(-0.3, 0), expr='sad', expr2='calm', ek=smooth(prog(t, b4 + 1.0, b4 + 2.5)), light=(-1, -0.3), light_col=TEAL, ambient=0.75)
    c.restore(); rain(c, T, 0.4)

def sc_dawn(c, T, t, d, S, P):
    k = smooth(prog(t, 0, d * 0.7))
    c.save(); camera(c, 540, 960, 1.0 + 0.08 * t / d)
    bus_aisle(c, T, warm=k)
    for i in range(5):
        quad(c, [(W, 200 + i * 80), (W, 260 + i * 80), (100, 1500 + i * 60), (60, 1400 + i * 60)], hexc('ffd09a'), 0.05 * k)
    face(c, 'marcus', 780, 1150, 1.5, T, turn=-0.6, look=(-0.9, 0.1), expr='worried', expr2='sad', ek=k, light=(1, -0.6), light_col=hexc('ffb36b'), ambient=0.6 + 0.3 * k)
    c.restore(); ash(c, T, 0.5 * k, col=hexc('ffe2b8'))

SCENES.update({'desk': sc_desk, 'keys': sc_keys, 'behind': sc_behind, 'hall': sc_hall, 'room_phone': sc_room_phone,
               'desk_other': sc_desk_other, 'book': paper_scene, 'logbook': paper_scene, 'news': paper_scene, 'ticket': paper_scene,
               'bus': sc_bus, 'mirror': sc_mirror, 'sign': sc_sign, 'stop': sc_stop, 'dawn': sc_dawn})

CAPCOL = {'narrator': WHITE, 'daniel': AMBER, 'marcus': TEAL, 'woman': hexc('ff6b7d'), 'caller': hexc('ff6b7d'), 'other': hexc('ff6b7d')}
CAPNAME = {'daniel': 'DANIEL', 'marcus': 'MARCUS', 'woman': 'THE WOMAN', 'caller': 'ROOM 9', 'other': '???'}
def chunks_for(l):
    words = l['text'].split(); tot = sum(len(w) + 1 for w in words); acc = 0; times = []
    for w in words: times.append(l['start'] + l['dur'] * 0.95 * acc / tot); acc += len(w) + 1
    ch = []; cur = []
    for i, w in enumerate(words):
        if cur and len(' '.join(words[j] for j in cur + [i])) > 22: ch.append(cur); cur = []
        cur.append(i)
        if w[-1] in '.?!' or i == len(words) - 1: ch.append(cur); cur = []
    return words, times, ch
CAPS = [(l, *chunks_for(l)) for l in LINES if l['text']]
def captions(c, T):
    for l, words, times, ch in CAPS:
        if not (l['start'] <= T < l['start'] + l['dur'] + 0.25): continue
        for ci, cc in enumerate(ch):
            t0 = times[cc[0]]; t1 = times[ch[ci + 1][0]] if ci + 1 < len(ch) else l['start'] + l['dur'] + 0.25
            if not (t0 <= T < t1): continue
            col = CAPCOL.get(l['who'], WHITE); italic = l['who'] != 'narrator'; sl = cairo.FONT_SLANT_ITALIC if italic else 0
            full = ' '.join(words[j] for j in cc); x = W / 2 - tw(c, full, 66, slant=sl) / 2; y = 1640
            if italic: text(c, 'ROOM 9' if l.get('fx') == 'phone' else CAPNAME.get(l['who'], ''), W / 2, 1560, 30, col, spacing=6, alpha=0.85)
            for j in cc:
                if times[j] > T: break
                x += text(c, words[j] + ' ', x, y, 66, col, align='l', alpha=prog(T, times[j], times[j] + 0.08), outline=12, slant=sl)
            return

def frame(T, caps=True):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H); c = cairo.Context(surf); rect(c, 0, 0, W, H, BLACK)
    for s in SCENES_T:
        if s['start'] <= T < s['end']:
            t = T - s['start']; d = s['end'] - s['start']; sid = s['id']
            P = PARAMS.get(sid, {})
            c.save(); SCENES[sid](c, T, t, d, s, P); c.restore()
            k = min(prog(t, 0, 0.35) if s['start'] > 0 else prog(t, 0, 0.8), 1 - prog(t, d - 0.25, d))
            if sid == 'title': k = 1
            if k < 1: rect(c, 0, 0, W, H, BLACK, 1 - k)
    post(c, T)
    if caps: captions(c, T)
    if T > TOTAL - 0.6: rect(c, 0, 0, W, H, BLACK, prog(T, TOTAL - 0.6, TOTAL))
    return surf

if __name__ == '__main__':
    if sys.argv[2:3] == ['stills']:
        for T in [float(x) for x in sys.argv[3:]]: frame(T).write_to_png(EP + f'still_{T:05.1f}.png')
        sys.exit()
    n = int(TOTAL * FPS)
    ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgra', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                           '-i', EP + 'mix.wav', '-c:v', 'libx264', '-preset', 'medium', '-crf', '24', '-tune', 'grain', '-maxrate', '8M', '-bufsize', '16M',
                           '-pix_fmt', 'yuv420p', '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000',
                           '-shortest', '-movflags', '+faststart', EP + 'video.mp4'], stdin=subprocess.PIPE)
    for i in range(n): ff.stdin.write(bytes(frame(i / FPS).get_data()))
    ff.stdin.close(); ff.wait(); print('done', EP)
