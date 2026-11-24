# ===================== THE 11:40 (romance) SCENES =====================
# Executed inside render.py's namespace (exec), so it shares its helpers and globals.
ROSE = hexc('ff8fa3'); GOLD = hexc('ffcf8a'); WARM = hexc('ffb874'); COOLW = hexc('9fc4ff'); NAVY = hexc('0b1226')
RCITY = [(random.Random(i).uniform(-300, W + 300), random.Random(i + 50).uniform(140, 520), random.Random(i + 90).uniform(70, 170)) for i in range(26)]

def scene_occurrence(S):
    """0 for the first time this scene id appears in the episode, 1 for the second, ..."""
    return sum(1 for s in SCENES_T if s['id'] == S['id'] and s['start'] < S['start'])

def spk_line(S, i):
    t0 = S['start'] + B(S, i, 0)
    for l in LINES:
        if abs(l['start'] - t0) < 0.01: return l
    return None

def skyline(c, T, y0=980, dark=1.0, warmth=0.0, lit=1.0):
    for k, (x, h, w) in enumerate(RCITY):
        col = mix(hexc('0a0f1f'), hexc('3a2230'), warmth)
        rect(c, x, y0 - h, w, h + 400, mix(col, BLACK, 0.3 * dark))
        r = random.Random(k * 7)
        for wy in range(int(y0 - h + 20), int(y0 - 10), 34):
            for wx in range(int(x + 12), int(x + w - 12), 26):
                if r.random() < 0.28 * lit:
                    on = r.random() > 0.08 or int(T * 2 + k) % 3
                    rect(c, wx, wy, 12, 16, WARM if r.random() < 0.7 else COOLW, 0.75 if on else 0.15)

def lamp(c, x, y, s, on=1.0, col=WARM):
    rect(c, x - 2 * s, y - 120 * s, 4 * s, 120 * s, hexc('1a1a20'))
    quad(c, [(x - 30 * s, y), (x + 30 * s, y), (x + 18 * s, y - 22 * s), (x - 18 * s, y - 22 * s)], hexc('22222a'))
    if on > 0:
        circ(c, x, y + 4 * s, 12 * s, col, on); glow(c, x, y + 10 * s, 220 * s, col, 0.35 * on)
        quad(c, [(x - 26 * s, y), (x + 26 * s, y), (x + 200 * s, y + 900 * s), (x - 200 * s, y + 900 * s)], col, 0.05 * on)

def umbrella(c, x, y, s, col=hexc('2a2f45')):
    c.save(); c.translate(x, y); c.scale(s, s)
    rect(c, -3, 0, 6, 260, hexc('15151a'))
    c.new_path(); c.move_to(-230, 10); c.curve_to(-200, -160, 200, -160, 230, 10)
    for i in range(4): c.curve_to(200 - i * 115 + 40, -20, 230 - (i + 1) * 115 + 20, -20, 230 - (i + 1) * 115, 10)
    c.close_path(); src(c, col); c.fill_preserve(); src(c, CH.INK); c.set_line_width(5); c.stroke()
    c.restore()

def platform_bg(c, T, P, fl, lights):
    g = cairo.LinearGradient(0, -300, 0, 1100)
    g.add_color_stop_rgba(0, *mix(hexc('060914'), hexc('8090c0'), fl)); g.add_color_stop_rgba(1, *mix(hexc('2a1d3a'), hexc('a9b8da'), fl))
    c.set_source(g); c.rectangle(-400, -400, W + 800, 1600); c.fill()
    skyline(c, T, 1000, lit=0.6 + 0.4 * lights)
    # tracks on the right, receding
    quad(c, [(560, 1000), (1500, 1000), (1500, 2300), (760, 2300)], hexc('0c0d12'))
    for k, x0 in enumerate((780, 1180)):
        quad(c, [(x0 - 10 + (k * 300), 1000), (x0 + 10 + k * 300, 1000), (x0 + 60 + k * 500, 2300), (x0 + 20 + k * 500, 2300)], hexc('5a5e6a'), 0.8)
    # platform slab with yellow edge and wet reflections
    quad(c, [(-400, 1000), (600, 1000), (760, 2300), (-400, 2300)], hexc('1a1c24'))
    quad(c, [(570, 1000), (600, 1000), (760, 2300), (700, 2300)], hexc('e8c23a'), 0.8)
    # canopy
    quad(c, [(-400, -400), (900, -400), (700, 260), (-400, 330)], hexc('101219'))
    rect(c, -400, 300, 1100, 18, hexc('1d2030'))
    for x in (120, 520): rect(c, x - 10, 300, 20, 760, hexc('15171f'))
    # lamps + their reflections on the wet floor
    for i, x in enumerate((-40, 300, 620)):
        on = lights * (0.25 if (P.get('storm') and random.Random(int(T * 12) + i).random() < 0.07) else 1.0)
        lamp(c, x, 330, 1.0, on)
        if on > 0: rect(c, x - 14, 1100 + i * 40, 28, 500, WARM, 0.07 * on)
    # departure board
    c.save(); c.translate(250, 420)
    rrect(c, -170, -60, 340, 150, 12); src(c, hexc('07080c')); c.fill()
    if lights > 0:
        text(c, 'PLATFORM 4', 0, -15, 30, GOLD, alpha=0.9 * lights, font='JetBrains Mono')
        if P.get('closed'):
            if int(T * 2) % 2: text(c, 'ALL TRAINS CANCELLED', 0, 45, 24, hexc('ff5566'), alpha=lights, font='JetBrains Mono')
        else:
            text(c, P.get('clock', '11:40') + '  LAST TRAIN', 0, 45, 28, hexc('ffe6b0'), alpha=lights, font='JetBrains Mono')
    c.restore()
    # bench
    rect(c, -160, 1150, 380, 26, hexc('3a2a22')); rect(c, -160, 1100, 380, 18, hexc('3a2a22'))
    for x in (-130, 190): rect(c, x, 1176, 14, 70, hexc('15151a'))

def train_side(c, x, T, lit=1.0):
    """Train seen down the track: a long carriage with glowing windows."""
    c.save(); c.translate(x, 0)
    quad(c, [(700, 600), (2900, 600), (2900, 1150), (700, 1150)], hexc('3a3f4c'))
    rect(c, 700, 1050, 2200, 26, hexc('8c2a3a'))
    for i in range(9):
        wx = 760 + i * 240; rrect(c, wx, 700, 170, 170, 14); src(c, hexc('ffd9a0'), 0.75 * lit); c.fill()
        glow(c, wx + 85, 785, 160, WARM, 0.15 * lit)
    circ(c, 715, 1000, 30, hexc('fff6d8')); glow(c, 715, 1000, 300, hexc('fff6d8'), 0.6)
    c.restore()

def sc_platform(c, T, t, d, S, P):
    fl = flash(T); storm = P.get('storm')
    lo = P.get('lights_out'); lights = 1.0
    if lo is not None: lights = 1 - smooth(prog(t, B(S, lo) + 1.0, B(S, lo) + 1.6))
    c.save(); camera(c, 540, 960, 1.0 + 0.05 * t / d)
    platform_bg(c, T, P, fl, lights)
    tr = P.get('train')
    if tr is not None:  # the 11:40 arrives along the track
        bt = B(S, tr) - 2.5; k = ease(prog(t, bt, bt + 3.0))
        if t > bt - 1.5: glow(c, 980, 1000, 120 + 500 * prog(t, bt - 1.5, bt), hexc('fff6d8'), 0.5 * prog(t, bt - 1.5, bt))
        if k > 0: train_side(c, 1400 * (1 - k) + 140, T)
    if P.get('missed'):  # tail lights pulling away
        k = smooth(prog(t, 0.2, d)); s_ = 1 - 0.8 * k
        for dx in (-40, 40): circ(c, 980 + dx * s_, 960 + 60 * s_, 10 * s_ + 3, hexc('ff3344')); glow(c, 980 + dx * s_, 960, 80 * s_, hexc('ff3344'), 0.5)
    amb = 0.55 + 0.25 * lights
    if P.get('zara', True):
        zx = 330; walk = P.get('adam_arrive') is not None
        turn = 0.0
        if walk: turn = 0.6 * smooth(prog(t, B(S, 2) - 0.4, B(S, 2) + 0.4))
        if lo is not None and t > B(S, lo) + 1.2 and not walk: turn = -0.4
        if storm: umbrella(c, zx + 40, 690, 0.95, hexc('7a2a3a'))
        CH.draw(c, 'zara', zx, 840, 0.62, T=T, turn=turn, look=(turn, 0.1), expr='calm' if not storm else 'sad',
                light=(0.6, -1), light_col=WARM if lights > 0.5 else COOLW, ambient=amb)
        if P.get('notebook'):
            rrect(c, zx - 60, 1060, 80, 100, 6); src(c, hexc('5a3a26')); c.fill()
    aa = P.get('adam_arrive')
    if aa is not None and t > B(S, aa) - 2.5:
        k = smooth(prog(t, B(S, aa) - 2.5, B(S, aa) + 1.5))
        ax = 1000 - 360 * k; sc_ = 0.35 + 0.27 * k
        glow(c, ax - 40, 900, 260, hexc('f4f8ff'), 0.35)  # his torch
        quad(c, [(ax - 40, 880), (ax - 600, 760), (ax - 600, 1060)], hexc('f4f8ff'), 0.06)
        CH.draw(c, 'adam', ax, 840 + (1 - k) * 120, sc_, T=T, turn=-0.5, look=(-0.8, 0), expr='calm', light=(-1, -0.4), light_col=COOLW, ambient=0.45 + 0.3 * k, mouth=mouth_for('adam', T))
    c.restore()
    rain(c, T, 1.6 if storm else 0.8, fl)
    if storm: fog(c, T * 2, 1.0, col=hexc('8aa0c0'), y0=600, y1=1500)
    if lo is not None: rect(c, 0, 0, W, H, hexc('020308'), 0.45 * (1 - lights))
    if fl > 0: rect(c, 0, 0, W, H, WHITE, fl * 0.2)
    if scene_occurrence(S) == 0 and S['start'] == 0:
        a = prog(t, 0.6, 1.0) * (1 - prog(t, min(d - 1.2, 3.6), min(d - 0.6, 4.2))); s_ = P.get('clock', '11:40'); s_ = s_ + (' PM' if ':' in s_ and not s_.startswith('12') else (' AM' if s_.startswith('12') else ''))
        n = int(clamp((t - 0.6) / 0.8) * len(s_)); text(c, s_[:n], 90, 1420, 64, WHITE, align='l', alpha=a, font='JetBrains Mono')

# ---------- inside the carriage ----------
POLES = [i * 0.37 + random.Random(i).uniform(0, 0.2) for i in range(400)]
def window_view(c, T, x, y, w, h, speed=1.0, day=0.0):
    c.save(); c.rectangle(x, y, w, h); c.clip()
    g = cairo.LinearGradient(0, y, 0, y + h); g.add_color_stop_rgba(0, *mix(hexc('0a1024'), hexc('ffb48a'), day)); g.add_color_stop_rgba(1, *mix(hexc('2a1a34'), hexc('ffd9b0'), day))
    c.set_source(g); c.rectangle(x, y, w, h); c.fill()
    # far skyline (slow), mid buildings (faster), near poles/lights (very fast): parallax
    for k, (bx, bh, bw) in enumerate(RCITY):
        xx = x + ((bx - T * 40 * speed) % (W + 600)) - 300 + 0 * w
        rect(c, xx, y + h - bh * 0.55, bw * 0.6, bh, hexc('101528'))
        r = random.Random(k)
        for j in range(5): rect(c, xx + r.uniform(5, bw * 0.5), y + h - r.uniform(20, bh * 0.5), 8, 10, WARM, 0.7)
    for k in range(10):
        r = random.Random(k + 300); xx = x + ((r.uniform(0, 1600) - T * 260 * speed) % 1600) - 200
        rect(c, xx, y + h * 0.35, r.uniform(60, 160), h, hexc('070a14'))
        glow(c, xx + 40, y + h * 0.4, 60, GOLD, 0.5)
    for k in range(6):
        xx = x + ((k * 420 - T * 1400 * speed) % 2400) - 300
        rect(c, xx, y, 18, h, hexc('020306')); glow(c, xx + 9, y + 30, 90, hexc('fff0d0'), 0.6)
    c.restore()

def light_sweep(T, speed=1.0):
    """0..1 pulse whenever a trackside lamp passes the window."""
    p = (T * 1400 * speed / 420) % 1.0
    return max(0.0, 1 - abs(p - 0.5) * 6)

def carriage_bg(c, T):
    rect(c, -400, -400, W + 800, H + 800, hexc('1c1418'))
    # ceiling strip light
    rect(c, -400, -400, W + 800, 520, hexc('120d10')); rect(c, 60, 90, 960, 22, hexc('fff2d8'), 0.85); glow(c, 540, 100, 700, WARM, 0.18)
    window_view(c, T, 140, 300, 800, 560)
    c.new_path(); rrect(c, 140, 300, 800, 560, 40); src(c, hexc('2a2228')); c.set_line_width(36); c.stroke()
    rect(c, 140, 300, 800, 560, WHITE, 0.03)  # glass sheen
    rect(c, -400, 1500, W + 800, 900, hexc('120c0e'))

def seat(c, x, y, flip=1):
    c.save(); c.translate(x, y); c.scale(flip, 1)
    rrect(c, -220, -520, 120, 640, 40); src(c, hexc('6a2232')); c.fill_preserve(); src(c, CH.INK); c.set_line_width(6); c.stroke()
    rrect(c, -220, 40, 420, 140, 30); src(c, hexc('7a2a3a')); c.fill_preserve(); src(c, CH.INK); c.set_line_width(6); c.stroke()
    rect(c, -220, 180, 420, 400, hexc('0d090a'))
    c.restore()

def sc_carriage(c, T, t, d, S, P):
    c.save(); camera(c, 540, 1000, 1.0 + 0.05 * t / d)
    carriage_bg(c, T)
    sw = light_sweep(T); lc = mix(WARM, hexc('fff4dc'), sw)
    seat(c, 160, 1300, 1); seat(c, 920, 1300, -1)
    mode = P.get('adam', 'asleep'); lv = P.get('leave')
    # Adam, right seat facing left
    ax = 820; leave_k = smooth(prog(t, B(S, lv) + 0.6, B(S, lv) + 2.2)) if lv is not None else 0
    if mode != 'empty' and leave_k < 1:
        woke = lv is not None and t > B(S, lv) - 0.2
        asleep = mode == 'asleep' and not woke
        CH.draw(c, 'adam', ax + 500 * leave_k, 920 - (60 * smooth(prog(t, B(S, lv), B(S, lv) + 0.6)) if lv is not None else 0), 0.95, T=T,
                turn=-0.45 if leave_k < 0.3 else 0.5, tilt=0.22 if asleep else 0.0, look=(-0.6, 0.4) if mode == 'awake' else (-0.3, 0),
                expr='calm' if asleep else ('worried' if mode == 'awake' else 'shock'), lid_override=0.95 if asleep else None,
                light=(-0.5, -1), light_col=lc, ambient=0.72, seed=1.3)
    if (lv is not None and t > B(S, lv) + 1.0) or mode == 'notebook':
        a = prog(t, B(S, lv) + 1.0, B(S, lv) + 1.6)
        c.save(); c.translate(800, 1360); c.rotate(-0.12)
        rrect(c, -80, -16, 160, 32, 6); src(c, hexc('5a3a26'), a); c.fill(); rect(c, -80, -16, 160, 6, hexc('e8dcc0'), a)
        c.restore(); glow(c, 800, 1350, 160, GOLD, 0.25 * a * (0.6 + 0.4 * math.sin(T * 3)))
    # Zara, left seat facing right
    if P.get('zara_seat') != 'empty':
        look_book = lv is not None and t > B(S, lv) + 1.2
        CH.draw(c, 'zara', 260, 930, 0.95, T=T, turn=0.45, look=(0.7, 0.6 if look_book else 0.1),
                expr='calm', expr2='worried' if mode == 'empty' else 'shock', ek=smooth(prog(t, B(S, 1), B(S, 1) + 1)) if (mode == 'empty' or look_book) else 0,
                light=(0.5, -1), light_col=lc, ambient=0.75, seed=0.2)
    if P.get('drawing'):
        a = prog(t, B(S, 0) + 1.0, B(S, 0) + 1.8)
        c.save(); c.translate(430, 560); c.rotate(0.06)
        rect(c, -90, -70, 180, 140, hexc('f2ead8'), a); circ(c, 0, -5, 40, hexc('3a3a3a'), 0.0)
        c.new_path(); c.arc(0, -5, 40, 0, 2 * PI); src(c, hexc('3a3330'), 0.8 * a); c.set_line_width(3); c.stroke()
        c.new_path(); c.move_to(0, -5); c.line_to(0, -35); c.move_to(0, -5); c.line_to(0, -5 + 0.0); src(c, hexc('3a3330'), a); c.stroke()
        text(c, '4', 0, 62, 22, hexc('3a3330'), alpha=a, font='Caveat')
        for sx in (-1, 1): c.save(); c.translate(sx * 80, -66); c.rotate(sx * 0.5); rect(c, -24, -8, 48, 16, hexc('e8e0b8'), 0.7 * a); c.restore()
        c.restore(); glow(c, 430, 560, 160, GOLD, 0.06 * a)
    # passing light washes across the whole carriage
    rect(c, -400, -400, W + 800, H + 800, hexc('fff0d0'), 0.06 * sw)
    c.restore()

# ---------- notebook inserts ----------
SKETCHES = [('Mar 3', 'reading', 0.3), ('Apr 19', 'laughing', -0.2), ('Jun 8', 'window', 0.6), ('Sep 22', 'asleep', 0.1), ('Dec 1', 'scarf', -0.4)]
def sketch_of(c, x, y, s, pose, T):
    """Pencil sketch of Zara: the rig rendered off-screen, turned to graphite, laid on the paper."""
    SW, SH = 900, 1100
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, SW, SH); cc = cairo.Context(surf)
    expr = {'laughing': 'calm', 'asleep': 'calm'}.get(pose, 'neutral')
    CH.draw(cc, 'zara', SW / 2, 380, 1.05, T=0.5, turn={'window': 0.6, 'reading': -0.2}.get(pose, 0.1), look=(0.6, 0.6) if pose == 'reading' else (0.8, -0.2),
            expr=expr, lid_override=0.9 if pose == 'asleep' else None, mouth=0.35 if pose == 'laughing' else 0.0, light=(1, -0.5), light_col=WHITE, ambient=0.95, breathe=False)
    surf.flush(); a = np.ndarray((SH, SW, 4), np.uint8, surf.get_data()).astype(np.float32)
    al = a[..., 3:4] / 255.0
    g = (a[..., 0] * 0.114 + a[..., 1] * 0.587 + a[..., 2] * 0.299)[..., None] / np.maximum(al, 1e-3)
    g = 0.25 + 0.75 * (g / 255.0) ** 0.7                    # lift into soft graphite
    fade = np.clip((SH - 120 - np.arange(SH)) / 260.0, 0, 1)[:, None, None]  # sketch fades out at the bottom
    al = al * fade
    out = np.concatenate([g * 0.95, g * 0.93, g * 0.9, np.ones_like(g)], axis=2) * 255 * al
    out = np.ascontiguousarray(out.astype(np.uint8))
    img = cairo.ImageSurface.create_for_data(memoryview(bytearray(out.tobytes())), cairo.FORMAT_ARGB32, SW, SH)
    c.save(); c.translate(x - SW / 2 * s, y - 380 * s); c.scale(s, s); c.set_source_surface(img, 0, 0)
    c.set_operator(cairo.OPERATOR_MULTIPLY); c.paint(); c.set_operator(cairo.OPERATOR_OVER); c.restore()
    r = random.Random(int(x))
    for i in range(22):
        x0 = x - 300 * s + r.uniform(0, 600 * s); y0 = y + 250 * s + r.uniform(0, 250 * s)
        c.new_path(); c.move_to(x0, y0); c.line_to(x0 + 34 * s, y0 - 34 * s); src(c, hexc('4a4640'), 0.3); c.set_line_width(2); c.stroke()

def notebook_page(c, kind='blank'):
    rect(c, -440, -560, 880, 1120, hexc('f1e9d6'))
    for i in range(1, 18): rect(c, -440, -560 + i * 62, 880, 1.5, hexc('b8c8d8'), 0.5)
    rect(c, -380, -560, 2, 1120, hexc('e0a0a0'), 0.6)
    g = cairo.LinearGradient(-440, 0, -380, 0); g.add_color_stop_rgba(0, 0, 0, 0, 0.25); g.add_color_stop_rgba(1, 0, 0, 0, 0)
    c.set_source(g); c.rectangle(-440, -560, 60, 1120); c.fill()

def handwrite(c, s, x, y, size, t, t0, dur, col=hexc('2a2622'), font='Caveat', align='l'):
    n = int(clamp((t - t0) / max(dur, 0.01)) * len(s))
    if n > 0: text(c, s[:n], x, y, size, col, font=font, align=align, weight=cairo.FONT_WEIGHT_NORMAL)

def sc_notebook(c, T, t, d, S, P):
    pages = P.get('pages', 'sketches'); occ = scene_occurrence(S)
    rect(c, 0, 0, W, H, hexc('120c0a'))
    glow(c, 540, 700, 1000, WARM, 0.22)
    c.save(); c.translate(W / 2, 900); c.rotate(-0.035 + 0.01 * math.sin(t * 0.5)); z = 0.98 + 0.06 * t / d; c.scale(z, z)
    if pages == 'sketches':
        nb = len(S['beats']); idx = 0
        # flip a page every ~0.9s during line 2, then settle on the last page
        b1, b3 = B(S, 1), B(S, 3)
        if t >= b1: idx = min(len(SKETCHES) - 1, 1 + int((t - b1) / 0.9))
        last = t >= b3 - 0.3
        notebook_page(c)
        if not last:
            date, pose, sx = SKETCHES[idx]
            sketch_of(c, 0 + sx * 60, -250, 0.85, pose, T)
            text(c, date, 300, 480, 52, hexc('3a3430'), font='Caveat', weight=cairo.FONT_WEIGHT_NORMAL)
            # page-turn sweep
            ft = (t - b1) % 0.9 if t >= b1 else 1
            if ft < 0.18 and t >= b1:
                k = ft / 0.18; quad(c, [(440 - 880 * k, -560), (440, -560), (440, 560), (440 - 880 * k * 0.9, 560)], hexc('e6dcc4'))
            if t < b1:  # cover opening
                k = smooth(prog(t, 0.3, 1.3)); quad(c, [(-440 + 880 * k, -560), (440, -560), (440, 560), (-440 + 880 * k, 560)], hexc('4a3020'))
        else:
            handwrite(c, P.get('last', ''), -330, -40, 64, t, b3 + 0.2, 2.4)
            text(c, '- A.', 250, 80, 56, hexc('2a2622'), alpha=prog(t, b3 + 2.6, b3 + 3.0), font='Caveat')
    elif pages == 'cover':
        rect(c, -440, -560, 880, 1120, hexc('4a3020')); rect(c, -440, -560, 40, 1120, hexc('2e1d12'))
        rrect(c, -250, -300, 500, 160, 10); src(c, hexc('efe6d0')); c.fill()
        text(c, 'Adam R.', 0, -200, 80, hexc('1a1612'), font='Caveat', weight=cairo.FONT_WEIGHT_NORMAL)
        k = smooth(prog(t, 1.2, 2.2))
        c.save(); c.translate(0, 200 - 30 * k); c.rotate(-0.08)
        rrect(c, -260, -150, 520, 300, 18); src(c, hexc('e8edf2'), k); c.fill()
        rect(c, -260, -150, 520, 70, hexc('2f3b4c'), k)
        text(c, 'ELM STREET TOWER', 0, -102, 34, WHITE, alpha=k, spacing=2)
        rect(c, -220, -50, 140, 170, hexc('9aa8b8'), k)
        CH.draw(c, 'adam', -150, 30, 0.28, T=0, expr='calm', light=(1, -0.5), light_col=WHITE, ambient=0.9, breathe=False, alpha=k)
        text(c, 'ADAM REYES', -50, 10, 36, hexc('1a1f28'), align='l', alpha=k)
        text(c, 'NIGHT SECURITY', -50, 60, 28, hexc('8c2a3a'), align='l', alpha=k)
        c.restore()
    elif pages == 'hello':
        notebook_page(c)
        text(c, 'Hello.', -330, -300, 110, hexc('2a3a6a'), font='Homemade Apple', align='l', weight=cairo.FONT_WEIGHT_NORMAL)
        text(c, '- the girl on the 11:40', -300, -160, 58, hexc('2a3a6a'), font='Caveat', align='l', weight=cairo.FONT_WEIGHT_NORMAL)
        num = '0300 555 01'; tail = '47'
        text(c, num, -300, 40, 78, hexc('2a3a6a'), font='Caveat', align='l', weight=cairo.FONT_WEIGHT_NORMAL)
        tx_ = -300 + tw(c, num + ' ', 78, weight=cairo.FONT_WEIGHT_NORMAL, font='Caveat')
        sm = smooth(prog(t, B(S, 0) + 1.2, B(S, 0) + 3.0)) if occ == 1 else 0.0
        text(c, tail, tx_, 40, 78, hexc('2a3a6a'), alpha=1 - 0.85 * sm, font='Caveat', align='l', weight=cairo.FONT_WEIGHT_NORMAL)
        circ(c, -200, 240, 40, ROSE, 0.0)
        if occ == 1:  # rain drops land and the ink runs
            for i in range(9):
                r = random.Random(i); dx, dy, td = r.uniform(-60, 120), r.uniform(-60, 40), r.uniform(0, 1.5)
                k = prog(t, B(S, 0) + td, B(S, 0) + td + 0.4)
                if k > 0:
                    glow(c, tx_ + 40 + dx, 20 + dy, 50 * k, hexc('6a7aa8'), 0.35 * k)
                    for j in range(3): rect(c, tx_ + 20 + dx + j * 12, 20 + dy, 6, 120 * sm * r.uniform(0.5, 1.2), hexc('5a6a9a'), 0.3 * k)
    elif pages == 'invite':
        rect(c, -440, -560, 880, 1120, hexc('7a2a3a'))  # seat fabric behind the taped page
        c.save(); c.rotate(0.05)
        rect(c, -330, -420, 660, 760, hexc('f2ead8'))
        # pencil clock + platform sign
        c.new_path(); c.arc(0, -150, 150, 0, 2 * PI); src(c, hexc('3a3330')); c.set_line_width(5); c.stroke()
        for h in range(12):
            a = h * PI / 6; c.new_path(); c.move_to(130 * math.cos(a), -150 + 130 * math.sin(a)); c.line_to(145 * math.cos(a), -150 + 145 * math.sin(a)); c.set_line_width(4); c.stroke()
        c.new_path(); c.move_to(0, -150); c.line_to(0, -265); c.move_to(0, -150); c.line_to(8, -255); c.set_line_width(7); c.stroke()
        text(c, '4', 200, -60, 110, hexc('3a3330'), font='Caveat', weight=cairo.FONT_WEIGHT_NORMAL)
        handwrite(c, 'Platform 4.', -260, 120, 66, t, 0.4, 0.8, col=hexc('2a2622'))
        handwrite(c, 'Midnight. Saturday.', -260, 210, 66, t, 1.3, 1.2, col=hexc('2a2622'))
        handwrite(c, '- A.', 150, 300, 56, t, 2.6, 0.4, col=hexc('8c2a3a'))
        for sx in (-1, 1): c.save(); c.translate(sx * 300, -410); c.rotate(sx * 0.6); rect(c, -60, -16, 120, 32, hexc('e8e0b8'), 0.75); c.restore()
        c.restore()
    c.restore()
    ash(c, T, 0.25, col=hexc('ffe2b8'), up=True)

# ---------- street + security booth ----------
def sc_street(c, T, t, d, S, P):
    fl = flash(T)
    c.save(); camera(c, 540, 960, 1.0 + 0.06 * t / d)
    g = cairo.LinearGradient(0, -300, 0, 1200); g.add_color_stop_rgba(0, *hexc('070a16')); g.add_color_stop_rgba(1, *hexc('231a30'))
    c.set_source(g); c.rectangle(-400, -400, W + 800, 1700); c.fill()
    skyline(c, T, 820, lit=0.8)
    # tower with glass lobby
    rect(c, 330, -400, 700, 1350, hexc('121626'))
    for r in range(10):
        for col in range(5):
            rect(c, 370 + col * 130, -300 + r * 95, 90, 60, hexc('1d2440') if (r + col) % 4 else WARM, 0.8)
    rect(c, 360, 640, 640, 320, hexc('fff0d4'), 0.85); glow(c, 680, 800, 500, WARM, 0.35)
    text(c, 'ELM STREET TOWER', 680, 615, 38, hexc('e8edf2'), spacing=4)
    # guard at the desk inside
    if P.get('guard'):
        rect(c, 600, 860, 300, 100, hexc('3a2e28'))
        CH.draw(c, 'marcus', 750, 760, 0.33, T=T, turn=-0.3, look=(-0.7, 0), expr='neutral', light=(0, -1), light_col=WARM, ambient=0.85)
        rect(c, 600, 880, 300, 80, hexc('2a201c'))
    # neon signs
    for x, y, s_, col in ((120, 520, 'CAFE', ROSE), (150, 640, '24H', hexc('7fe0d0'))):
        on = 0.3 if random.Random(int(T * 10) + x).random() < 0.05 else 1.0
        text(c, s_, x, y, 64, col, alpha=on); glow(c, x, y - 20, 200, col, 0.25 * on)
    # wet street and reflections
    rect(c, -400, 960, W + 800, 1200, hexc('0c0d14'))
    for x, col in ((680, WARM), (120, ROSE), (150, hexc('7fe0d0'))):
        for i in range(6): rect(c, x - 60 + random.Random(i + x).uniform(-30, 30), 1000 + i * 70, 120, 26, col, 0.10)
    rect(c, -400, 960, W + 800, 10, hexc('3a3a48'))
    # Zara with an umbrella
    hand_ = P.get('handover')
    k = smooth(prog(t, 0.2, d * 0.7)); zx = -60 + 520 * k if not hand_ else 430
    zs = 0.55
    umbrella(c, zx + 20, 770 + math.sin(t * 6) * 4 * (1 - k), 0.75, hexc('7a2a3a'))
    CH.draw(c, 'zara', zx, 880 + math.sin(t * 6) * 4 * (1 - k), zs, T=T, turn=0.5, look=(0.8, 0), expr='calm', light=(0.8, -0.6), light_col=WARM, ambient=0.6)
    if hand_:
        rrect(c, zx + 90, 1080, 70, 90, 6); src(c, hexc('5a3a26')); c.fill()
    c.restore()
    rain(c, T, 1.0, fl)

def closeup_bg(c, T, bg):
    if bg == 'train':
        rect(c, -400, -400, W + 800, H + 800, hexc('1c1418'))
        window_view(c, T, -400, 100, W + 800, 900, 1.0)
        rect(c, -400, 1000, W + 800, 1200, hexc('241a1e'))
    elif bg in ('booth', 'booth_day'):
        day = bg == 'booth_day'
        rect(c, -400, -400, W + 800, H + 800, hexc('2a3240') if day else hexc('141820'))
        rect(c, 600, 100, 600, 700, hexc('ffe6c0') if day else hexc('0b1020')); glow(c, 900, 400, 700, GOLD if day else COOLW, 0.4 if day else 0.12)
        for i in range(3): rect(c, -200 + i * 250, 300, 200, 150, hexc('0a1210')); rect(c, -190 + i * 250, 310, 180, 130, hexc('2a6a5a'), 0.5)
        if day:
            for i in range(5): quad(c, [(1200, 60 + i * 120), (1200, 120 + i * 120), (-200, 1400 + i * 100), (-200, 1300 + i * 100)], GOLD, 0.05)
    elif bg == 'street':
        rect(c, -400, -400, W + 800, H + 800, hexc('0b0d18'))
        for i in range(12):
            r = random.Random(i + 70); glow(c, r.uniform(0, W), r.uniform(100, 1100), r.uniform(80, 200), r.choice([ROSE, WARM, hexc('7fe0d0')]), 0.25)
    else:  # platform at night
        rect(c, -400, -400, W + 800, H + 800, hexc('0a0c16'))
        for i, x in enumerate((100, 600, 1000)): glow(c, x, 200, 260, WARM, 0.35)
        skyline(c, T, 1100, dark=1.0, lit=0.5)

def sc_closeup(c, T, t, d, S, P):
    who = P.get('who') or (spk_line(S, 0) or {}).get('who', 'zara')
    char = 'marcus' if who == 'guard' else who
    bg = P.get('bg', 'train')
    c.save(); camera(c, 540, 900, 1.0 + 0.07 * t / d)
    closeup_bg(c, T, bg)
    sw = light_sweep(T) if bg == 'train' else 0.0
    lc = {'train': mix(WARM, hexc('fff4dc'), sw), 'booth': COOLW, 'booth_day': GOLD, 'street': ROSE, 'platform': WARM}.get(bg, WARM)
    e1 = P.get('expr', 'calm'); e2 = P.get('expr2'); ek = smooth(prog(t, B(S, 0) + 0.8, B(S, 0) + 2.0)) if e2 else 0
    if P.get('umbrella'): umbrella(c, 560, 300, 1.6, hexc('7a2a3a'))
    side = -1 if who == 'adam' else 1
    CH.draw(c, char, 540, 760, 2.2, T=T, turn=0.25 * side, look=(0.5 * side, 0.05), expr=e1, expr2=e2, ek=ek,
            mouth=mouth_for(who, T), light=(0.7 * side, -0.8), light_col=lc, ambient=0.78, seed=0.4 if who == 'zara' else 1.1)
    if P.get('smile') and mouth_for(who, T) < 0.05:
        pass
    c.restore()
    if bg in ('street', 'platform'): rain(c, T, 0.6)
    rect(c, 0, 0, W, H, hexc('fff0d0'), 0.05 * sw)

# ---------- dawn ----------
def sc_sunrise(c, T, t, d, S, P):
    k = smooth(prog(t, 0, d * 0.8))
    c.save(); camera(c, 540, 960, 1.08 - 0.06 * smooth(t / d))
    g = cairo.LinearGradient(0, -300, 0, 1100)
    g.add_color_stop_rgba(0, *mix(hexc('1a1a3a'), hexc('4a5a9a'), k)); g.add_color_stop_rgba(0.6, *mix(hexc('6a3a5a'), hexc('ff9a7a'), k)); g.add_color_stop_rgba(1, *mix(hexc('c9705a'), hexc('ffd9a0'), k))
    c.set_source(g); c.rectangle(-400, -400, W + 800, 1600); c.fill()
    sy = 700 - 260 * k; glow(c, 640, sy, 600, hexc('fff0c0'), 0.7); circ(c, 640, sy, 90, hexc('fff4d8'))
    for i in range(7):
        a = -PI / 2 + (i - 3) * 0.22; quad(c, [(640, sy), (640 + 2200 * math.cos(a - 0.04), sy + 2200 * math.sin(a - 0.04)), (640 + 2200 * math.cos(a + 0.04), sy + 2200 * math.sin(a + 0.04))], hexc('fff0c0'), 0.06 * k)
    for kk, (x, h, w) in enumerate(RCITY): rect(c, x, 1000 - h, w, h + 400, mix(hexc('1a1424'), hexc('5a3a44'), k * 0.5))
    quad(c, [(-400, 1000), (1500, 1000), (1500, 2300), (-400, 2300)], mix(hexc('1a1c24'), hexc('6a4a44'), k))
    rect(c, -400, 1000, W + 800, 1200, hexc('ffd9a0'), 0.06 * k)
    # bench with the two of them, from behind; her head on his shoulder
    rect(c, 200, 1290, 680, 30, hexc('2a1a14')); rect(c, 200, 1220, 680, 22, hexc('2a1a14'))
    lean = smooth(prog(t, 2.0, 4.0))
    glow(c, 560, 1000, 420, GOLD, 0.35 * k)
    CH.draw(c, 'adam', 660, 1020, 0.6, T=T, back=True, light=(0, -1), light_col=GOLD, ambient=0.35)
    CH.draw(c, 'zara', 440 + 30 * lean, 1035 + 10 * lean, 0.58, T=T, back=True, tilt=0.28 * lean, light=(0, -1), light_col=GOLD, ambient=0.35)
    c.restore()
    ash(c, T, 0.5 * k, col=hexc('ffe2b8'), up=True)

def sc_title_romance(c, T, t, d, S, P):
    TT = TM['title']; rect(c, 0, 0, W, H, hexc('0a0608'))
    a = prog(t, 0.3, 1.0)
    glow(c, W / 2, 840, 520, ROSE, 0.14 * a)
    text(c, TT['series'], W / 2, 880, 150, GOLD, alpha=a, font='Playfair Display', spacing=4)
    rect(c, W / 2 - 160 * a, 925, 320 * a, 3, ROSE, 0.8)
    text(c, TT['ep'], W / 2, 990, 38, hexc('e8d8d0'), alpha=prog(t, 0.9, 1.3), spacing=4, weight=cairo.FONT_WEIGHT_NORMAL)
    b = prog(t, 1.8, 2.2)
    text(c, TT['l1'], W / 2, 1180, 56, WHITE, alpha=b, font='Playfair Display'); text(c, TT['l2'], W / 2, 1250, 38, hexc('b9a8b0'), alpha=b, weight=cairo.FONT_WEIGHT_NORMAL)
    for i in range(30):
        r = random.Random(i); x = r.uniform(0, W); y = H - ((t * r.uniform(30, 80) + r.uniform(0, H)) % H)
        glow(c, x, y, r.uniform(6, 16), GOLD, 0.35 * a)

_old_title = sc_title
def sc_title(c, T, t, d, S, P):
    if TM['title'].get('style') == 'romance': return sc_title_romance(c, T, t, d, S, P)
    return _old_title(c, T, t, d, S, P)

SCENES.update({'platform': sc_platform, 'carriage': sc_carriage, 'notebook': sc_notebook, 'street': sc_street,
               'closeup': sc_closeup, 'sunrise': sc_sunrise, 'title': sc_title})
