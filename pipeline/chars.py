"""Cartoon character rig for Night Shift (pycairo). Head radius ~100 units at scale 1."""
import cairo, math
PI = math.pi

def hexc(h, a=1.0): h = h.lstrip('#'); return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)) + (a,)
def mix(a, b, k): return tuple(a[i] + (b[i] - a[i]) * k for i in range(4))
def src(c, col, a=1.0): c.set_source_rgba(col[0], col[1], col[2], col[3] * a)
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
INK = (0.07, 0.045, 0.04, 1.0)   # toon outline colour
HEAD_K = 1.22                    # toon proportions: bigger head
def inkfill(c, col, w=6.0, a=1.0):
    src(c, col, a); c.fill_preserve(); src(c, INK, a); c.set_line_width(w); c.set_line_join(cairo.LINE_JOIN_ROUND); c.stroke()

CHARS = {
    'daniel': dict(skin='c99a78', hair='2b1d15', hairstyle='short', shirt='e8e2d4', jacket='3b4a3a', iris='5a3a22', brow='24170f', tag=True),
    'double': dict(skin='a9a49c', hair='2b1d15', hairstyle='short', shirt='e8e2d4', jacket='3b4a3a', iris='000000', brow='24170f', tag=True, hollow=True),
    'marcus': dict(skin='8a5a3c', hair='3a3a3a', hairstyle='cap', shirt='c9d4e0', jacket='1f2d44', iris='3a2414', brow='1d1410', mustache=True),
    'priya': dict(skin='9a6a48', hair='141012', hairstyle='bun', shirt='4f8f86', jacket='4f8f86', iris='3a2414', brow='15100c', outfit='scrubs', tag=True),
    'novak': dict(skin='d9c3b0', hair='e6e2dc', hairstyle='bald', shirt='b9c7d6', jacket='a9b8c9', iris='6b7f8f', brow='cfcac2', outfit='gown', pale=True),
    'leo': dict(skin='e0b090', hair='6b4a2a', hairstyle='short', shirt='2a2a2a', jacket='9b2a2a', iris='3b5a7a', brow='4a3018', outfit='hoodie'),
    'stranger': dict(skin='b8b4ac', hair='111111', hairstyle='fedora', shirt='d8d4cc', jacket='2a2622', iris='0a0a0a', brow='111111', outfit='coat', pale=True),
    'zara': dict(skin='c48a64', hair='3a1c14', hairstyle='shoulder', shirt='e9c46a', jacket='8c3b4a', iris='4a2c1a', brow='22140f', outfit='scarf', lashes=True, lips='b5525e'),
    'adam': dict(skin='d7a47e', hair='3a2618', hairstyle='short', shirt='dfe6ee', jacket='2f3b4c', iris='4a6a3a', brow='2a1a10', tag=True),
    'woman': dict(skin='d8d2c8', hair='0d0d10', hairstyle='long', shirt='6b6f72', jacket='4a4f55', iris='9fb8c0', brow='1a1a1e', pale=True, wet=True),
}

EXPR = {  # brow_inner_raise, brow_outer, lid_top(0 open .. 1 closed), eye_wide, mouth_curve(+smile), pupil
    'neutral': (0.0, 0.0, 0.15, 0.0, 0.0, 1.0),
    'worried': (0.6, -0.2, 0.1, 0.2, -0.3, 1.0),
    'fear': (0.9, 0.1, 0.0, 0.8, -0.5, 0.7),
    'shock': (1.0, 0.8, 0.0, 1.0, -0.2, 0.55),
    'sinister': (-0.7, 0.3, 0.45, 0.0, 0.9, 1.0),
    'sad': (0.8, -0.5, 0.35, 0.0, -0.5, 1.0),
    'calm': (0.1, 0.0, 0.3, 0.0, 0.25, 1.0),
}
def blend_expr(a, b, k):
    ea, eb = EXPR[a], EXPR[b]; return tuple(ea[i] + (eb[i] - ea[i]) * k for i in range(6))

def blink_amount(T, seed=0.0):
    # natural blink every ~3.5s, 0.14s long
    p = (T + seed * 1.7) % 3.7
    return max(0.0, 1 - abs(p - 0.07) / 0.07) if p < 0.14 else 0.0

def _head_path(c, w=86, top=-112, chin=112):
    c.new_path()
    c.move_to(0, top)
    c.curve_to(w * 0.75, top, w * 1.02, -60, w, -5)
    c.curve_to(w * 0.98, 45, w * 0.7, 88, 0, chin)
    c.curve_to(-w * 0.7, 88, -w * 0.98, 45, -w, -5)
    c.curve_to(-w * 1.02, -60, -w * 0.75, top, 0, top)
    c.close_path()

def draw(c, who, x, y, s, T=0.0, turn=0.0, tilt=0.0, look=(0.0, 0.0), expr='neutral', expr2=None, ek=0.0,
         mouth=0.0, light=(1.0, -0.6), light_col=hexc('ffb347'), ambient=0.75, back=False, body=True,
         breathe=True, seed=0.0, alpha=1.0, under=False, eyes_glow=0.0, hand=None, lid_override=None):
    """Draw a character. turn: -1 (facing screen-left) .. 1 (facing screen-right)."""
    C = CHARS[who]
    skin = hexc(C['skin']); hair = hexc(C['hair']); jacket = hexc(C['jacket']); shirt = hexc(C['shirt'])
    # light tint
    def lit(col, k=1.0): return mix(mix(col, hexc('000000'), 1 - ambient), mix(col, light_col, 0.35), 0.0)
    skin_l = lit(skin); hair_l = lit(hair); jacket_l = lit(jacket); shirt_l = lit(shirt)
    E = blend_expr(expr, expr2, ek) if expr2 else EXPR[expr]
    br = 1.5 * math.sin(T * 1.6 + seed) if breathe else 0
    sway = 0.0
    if breathe:
        # idle life: weight shift, head drift, nods while talking, eye saccades
        sway = 5 * math.sin(T * 0.57 + seed * 2.3) + 2 * math.sin(T * 1.21 + seed)
        tilt = tilt + 0.028 * math.sin(T * 0.83 + seed * 1.7) + 0.012 * math.sin(T * 1.9 + seed)
        if mouth > 0.08: tilt += 0.03 * mouth * math.sin(T * 6.5)
        k = int((T + seed * 3.1) * 0.9); fr = (T + seed * 3.1) * 0.9 - k
        def _sac(n): r = math.sin(n * 12.9898 + seed * 78.233) * 43758.5453; return (r - math.floor(r)) * 2 - 1
        e = clamp(fr / 0.08)
        look = (look[0] + 0.16 * (_sac(k) * e + _sac(k - 1) * (1 - e)), look[1] + 0.10 * (_sac(k + 77) * e + _sac(k + 76) * (1 - e)))
    c.save(); c.translate(x, y); c.scale(s, s); c.translate(sway, 0)
    if alpha < 1: c.push_group()
    if body:  # soft cast shadow on the wall behind, thrown away from the key light
        lx0, ly0 = light
        sx0, sy0 = -lx0 * 70, 150 - ly0 * 30
        g = cairo.RadialGradient(sx0, sy0, 60, sx0, sy0, 420)
        g.add_color_stop_rgba(0, 0, 0, 0, 0.42); g.add_color_stop_rgba(1, 0, 0, 0, 0)
        c.save(); c.translate(sx0, sy0); c.scale(1, 1.35); c.translate(-sx0, -sy0)
        c.set_source(g); c.new_path(); c.arc(sx0, sy0, 420, 0, 2 * PI); c.fill(); c.restore()
    # ---------- body ----------
    if body:
        c.save(); c.translate(0, br)
        c.new_path()
        c.move_to(-34, 120); c.line_to(34, 120)
        c.curve_to(120, 150, 210, 170, 235, 300); c.line_to(260, 1100); c.line_to(-260, 1100); c.line_to(-235, 300)
        c.curve_to(-210, 170, -120, 150, -34, 120); c.close_path(); inkfill(c, jacket_l, 8)
        _body_shade(c, light, light_col)
        outfit = C.get('outfit', 'jacket')
        if outfit == 'hoodie':
            c.new_path(); c.move_to(-110, 150); c.curve_to(-100, 60, 100, 60, 110, 150); c.curve_to(60, 175, -60, 175, -110, 150); inkfill(c, mix(jacket_l, hexc('000000'), 0.25), 5)
        if not back and outfit == 'jacket':
            c.new_path(); c.move_to(-48, 128); c.line_to(0, 260); c.line_to(48, 128); c.close_path(); inkfill(c, shirt_l, 5)
            c.new_path(); c.move_to(-48, 128); c.line_to(-12, 175); c.line_to(-30, 200); c.close_path(); src(c, mix(shirt_l, hexc('000000'), 0.15)); c.fill()
            c.new_path(); c.move_to(48, 128); c.line_to(12, 175); c.line_to(30, 200); c.close_path(); src(c, mix(shirt_l, hexc('000000'), 0.15)); c.fill()
        elif not back and outfit == 'scrubs':
            c.new_path(); c.move_to(-40, 124); c.line_to(0, 200); c.line_to(40, 124); c.close_path(); src(c, mix(skin_l, hexc('000000'), 0.25)); c.fill()
            c.new_path(); c.rectangle(90, 300, 70, 60); inkfill(c, mix(jacket_l, hexc('000000'), 0.2), 5)
        elif not back and outfit == 'gown':
            c.new_path(); c.arc(0, 128, 46, 0, PI); src(c, mix(skin_l, hexc('000000'), 0.25)); c.fill()
            for i in range(14):
                c.new_path(); c.arc(-200 + (i % 7) * 66, 260 + (i // 7) * 120, 6, 0, 2 * PI); src(c, hexc('7a8fa8'), 0.7); c.fill()
        elif not back and outfit == 'hoodie':
            for sx in (-28, 28):
                c.new_path(); c.move_to(sx, 160); c.line_to(sx + (4 if sx > 0 else -4), 280); src(c, hexc('e8e2d8'), 0.8); c.set_line_width(6); c.stroke()
            c.new_path(); c.rectangle(-120, 420, 240, 110); inkfill(c, mix(jacket_l, hexc('000000'), 0.15), 5)
        elif not back and outfit == 'scarf':
            c.new_path(); c.move_to(-40, 124); c.line_to(0, 210); c.line_to(40, 124); c.close_path(); src(c, mix(skin_l, hexc('000000'), 0.2)); c.fill()
            sc_ = lit(shirt)
            c.new_path(); c.move_to(-95, 120); c.curve_to(-60, 175, 60, 175, 95, 120); c.curve_to(110, 160, 60, 215, 0, 215); c.curve_to(-60, 215, -110, 160, -95, 120); c.close_path(); inkfill(c, sc_, 5)
            c.new_path(); c.move_to(30, 190); c.line_to(70, 380); c.line_to(20, 385); c.line_to(5, 200); c.close_path(); inkfill(c, mix(sc_, hexc('000000'), 0.12), 5)
        elif not back and outfit == 'coat':
            c.new_path(); c.move_to(-30, 124); c.line_to(0, 300); c.line_to(30, 124); c.close_path(); src(c, shirt_l); c.fill()
            c.new_path(); c.move_to(-14, 150); c.line_to(0, 300); c.line_to(14, 150); c.close_path(); src(c, hexc('5a0d12')); c.fill()
            for sg in (-1, 1):
                c.new_path(); c.move_to(sg * 34, 120); c.line_to(sg * 120, 170); c.line_to(sg * 60, 260); c.line_to(sg * 8, 330); c.close_path(); inkfill(c, mix(jacket_l, hexc('000000'), 0.35), 5)
            if C.get('tag'):
                c.new_path(); c.rectangle(-170, 260, 80, 30); src(c, hexc('d8c27a'), 0.9); c.fill()
            if who == 'marcus':
                c.new_path(); c.arc(-150, 270, 16, 0, 2 * PI); src(c, hexc('c9a24a')); c.fill()
                for i in range(3): c.new_path(); c.arc(0, 300 + i * 70, 7, 0, 2 * PI); src(c, hexc('c9a24a')); c.fill()
        c.restore()
    # neck
    c.new_path(); c.rectangle(-30, 70, 60, 70); src(c, mix(skin_l, hexc('000000'), 0.3)); c.fill()
    for nx_ in (-30, 30): c.new_path(); c.move_to(nx_, 70); c.line_to(nx_, 128); src(c, INK); c.set_line_width(6); c.stroke()
    # ---------- head ----------
    c.save(); c.translate(0, br * 0.6 + 100); c.scale(HEAD_K, HEAD_K); c.translate(0, -100); c.rotate(tilt)
    tx = turn * 30
    # long hair back layer
    if C['hairstyle'] == 'bun':
        c.new_path(); c.arc(tx * 0.1, -120, 42, 0, 2 * PI); inkfill(c, hair_l, 5)
    if C['hairstyle'] == 'shoulder':
        c.new_path(); c.move_to(-98, -40); c.curve_to(-125, 40, -118, 120, -132, 165); c.curve_to(-90, 182, -60, 150, -40, 140)
        c.line_to(40, 140); c.curve_to(60, 150, 90, 182, 132, 165); c.curve_to(118, 120, 125, 40, 98, -40); c.close_path(); inkfill(c, hair_l, 5)
    if C['hairstyle'] == 'long':
        c.new_path(); c.move_to(-95, -40); c.curve_to(-130, 80, -120, 220, -150, 300)
        c.line_to(150, 300); c.curve_to(120, 220, 130, 80, 95, -40); c.close_path(); inkfill(c, hair_l, 5)
    # ears
    if not back:
        for side in (-1, 1):
            if side * turn > 0.55: continue
            ex = side * 84 + tx * 0.3
            c.new_path(); c.save(); c.translate(ex, 5); c.scale(0.6, 1); c.arc(0, 0, 22, 0, 2 * PI); c.restore(); inkfill(c, mix(skin_l, hexc('000000'), 0.12), 4.5)
    # head shape
    c.save(); c.translate(tx * 0.25, 0); _head_path(c); c.restore()
    src(c, skin_l); c.fill()
    if back:
        c.save(); c.translate(tx * 0.25, 0); _head_path(c); c.restore(); c.clip()
        c.new_path(); c.rectangle(-120, -130, 240, 210); src(c, hair_l); c.fill()
        c.reset_clip()
        if C['hairstyle'] == 'cap': _cap(c, 0, back=True)
        if C['hairstyle'] == 'fedora': _fedora(c, 0)
    else:
        # ---------- face features ----------
        c.save(); c.translate(tx * 0.25, 0); _head_path(c); c.restore(); c.save(); c.clip()
        # cheeks
        for side in (-1, 1):
            g = cairo.RadialGradient(side * 48 + tx, 42, 0, side * 48 + tx, 42, 32)
            g.add_color_stop_rgba(0, 0.85, 0.35, 0.3, 0.0 if C.get('pale') else 0.3); g.add_color_stop_rgba(1, 0.85, 0.35, 0.3, 0)
            c.set_source(g); c.paint()
        if C.get('pale'):
            for side in (-1, 1):  # sunken eyes
                g = cairo.RadialGradient(side * 32 + tx, -2, 0, side * 32 + tx, -2, 34)
                g.add_color_stop_rgba(0, 0.15, 0.18, 0.25, 0.5); g.add_color_stop_rgba(1, 0.15, 0.18, 0.25, 0); c.set_source(g); c.paint()
        if C.get('hollow'):
            for side in (-1, 1):
                g = cairo.RadialGradient(side * 32 + tx, -2, 0, side * 32 + tx, -2, 36)
                g.add_color_stop_rgba(0, 0, 0, 0, 0.6); g.add_color_stop_rgba(1, 0, 0, 0, 0); c.set_source(g); c.paint()
        # eyes
        bl = max(blink_amount(T, seed), 0)
        lid = clamp(E[2] + bl * (1 - E[2]))
        if lid_override is not None: lid = lid_override
        wide = E[3]
        for side in (-1, 1):
            far = 1 - 0.35 * clamp(-side * turn) if turn != 0 else 1
            ex = side * 35 * (1 - 0.25 * abs(turn)) + tx; ey = 0
            rx = 17 * far * 1.4; ry = (11 + 4 * wide) * 1.4
            c.save(); c.translate(ex, ey); c.scale(rx / 17, ry / 11)
            c.new_path(); c.arc(0, 0, 11, 0, 2 * PI); c.restore()
            c.save(); c.clip_preserve()
            src(c, hexc('f2eee6') if not C.get('hollow') else hexc('0a0a0a')); c.fill()
            px = ex + look[0] * 7 * far + turn * 3; py = ey + look[1] * 4
            ir = 11.5 * (0.85 + 0.15 * (1 - wide * 0.4))
            if C.get('hollow'):
                c.new_path(); c.arc(px, py, 3.2, 0, 2 * PI); src(c, hexc('ffffff')); c.fill()
                if eyes_glow > 0:
                    pass
            else:
                c.new_path(); c.arc(px, py, ir, 0, 2 * PI); src(c, hexc(C['iris'])); c.fill()
                c.new_path(); c.arc(px, py, ir * 0.48 * E[5], 0, 2 * PI); src(c, hexc('050505')); c.fill()
                c.new_path(); c.arc(px + 4, py - 4, 3.6, 0, 2 * PI); src(c, hexc('ffffff'), 0.95); c.fill()
                c.new_path(); c.arc(px - 3.5, py + 4, 1.6, 0, 2 * PI); src(c, hexc('ffffff'), 0.8); c.fill()
            # upper lid
            c.new_path(); c.rectangle(ex - 30, ey - 26, 60, 2 * ry * lid + (26 - ry)); src(c, mix(skin_l, hexc('000000'), 0.08)); c.fill()
            c.restore()
            c.save(); c.translate(ex, ey); c.scale(rx / 17, ry / 11); c.new_path(); c.arc(0, 0, 11, 0, 2 * PI); c.restore()
            src(c, INK, 0.9); c.set_line_width(3); c.stroke()
            # lid line
            lty = ey - ry + 2 * ry * lid
            c.new_path(); c.save(); c.translate(ex, lty); c.scale(rx / 17, 0.5)
            c.arc(0, 8, 17, PI * 1.12, PI * 1.88); c.restore(); src(c, hexc('1a120c'), 0.85); c.set_line_width(3); c.stroke()
            if C.get('lashes'):
                for kk in range(3):
                    ox_ = ex + side * (rx * 0.75 + kk * 4); oy_ = lty - 2 + kk * 3
                    c.new_path(); c.move_to(ox_ - side * 6, oy_ + 2); c.line_to(ox_ + side * 6, oy_ - 6 + kk * 2)
                    src(c, hexc('120a08')); c.set_line_width(3.2); c.set_line_cap(cairo.LINE_CAP_ROUND); c.stroke()
            if eyes_glow > 0:
                g = cairo.RadialGradient(px, py, 0, px, py, 30); g.add_color_stop_rgba(0, 0.9, 0.95, 1, 0.6 * eyes_glow); g.add_color_stop_rgba(1, 0.9, 0.95, 1, 0)
                c.set_source(g); c.paint()
            # brows
            inner, outer = E[0], E[1]
            bx_in = ex - side * 4 * 0 + (-side) * 4; by = ey - 30 - 5 * wide
            c.new_path(); c.move_to(ex - side * (-14), by - outer * 6)
            c.curve_to(ex, by - 6 - (inner + outer) * 3, ex + side * (-10), by - 4 - inner * 10, ex + side * (-18), by - inner * 12 + 2)
            src(c, hexc(C['brow'])); c.set_line_width(9); c.set_line_cap(cairo.LINE_CAP_ROUND); c.stroke()
        # nose
        nx = tx * 1.35
        c.new_path(); c.move_to(nx + 2, 10); c.curve_to(nx + 4 + turn * 8, 30, nx + 10 + turn * 6, 36, nx, 38)
        src(c, mix(skin_l, hexc('000000'), 0.35)); c.set_line_width(3.5); c.stroke()
        # stubble / mustache
        if C.get('mustache'):
            c.new_path(); c.move_to(tx - 26, 52); c.curve_to(tx - 15, 40, tx + 15, 40, tx + 26, 52); c.curve_to(tx + 15, 48, tx - 15, 48, tx - 26, 52)
            src(c, hexc('2a2a2a')); c.set_line_width(6); c.stroke()
            g = cairo.RadialGradient(tx, 85, 0, tx, 85, 60); g.add_color_stop_rgba(0, 0.1, 0.08, 0.07, 0.35); g.add_color_stop_rgba(1, 0.1, 0.08, 0.07, 0)
            c.set_source(g); c.paint()
        # mouth
        mo = clamp(mouth); curve = E[4]
        mx, my = tx * 1.2, 62; mw = 22 + 6 * mo * 0.5
        if mo > 0.06:
            c.new_path(); c.move_to(mx - mw, my - curve * 6)
            c.curve_to(mx - mw * 0.5, my - 4 - curve * 2, mx + mw * 0.5, my - 4 - curve * 2, mx + mw, my - curve * 6)
            c.curve_to(mx + mw * 0.6, my + 20 * mo + 2, mx - mw * 0.6, my + 20 * mo + 2, mx - mw, my - curve * 6); c.close_path()
            src(c, hexc('2a0d0d')); c.fill_preserve(); c.save(); src(c, INK); c.set_line_width(3.5); c.stroke_preserve(); c.clip()
            c.new_path(); c.rectangle(mx - mw, my - 8, 2 * mw, 7); src(c, hexc('e8e2d8'), 0.9); c.fill()
            c.new_path(); c.arc(mx, my + 20 * mo + 6, mw * 0.55, 0, 2 * PI); src(c, hexc('a0424a'), 0.8); c.fill()
            c.restore()
        else:
            c.new_path(); c.move_to(mx - mw, my - curve * 7); c.curve_to(mx - mw * 0.4, my + curve * 5, mx + mw * 0.4, my + curve * 5, mx + mw, my - curve * 7)
            src(c, hexc(C.get('lips', '3a1a14'))); c.set_line_width(5 if C.get('lips') else 4); c.set_line_cap(cairo.LINE_CAP_ROUND); c.stroke()
        # form: occlusion under the hairline and jaw, soft sheen on the lit cheek/forehead
        lx, ly = light
        g = cairo.LinearGradient(0, -112, 0, -40); g.add_color_stop_rgba(0, 0, 0, 0, 0.28); g.add_color_stop_rgba(1, 0, 0, 0, 0)
        c.set_source(g); c.paint()
        g = cairo.LinearGradient(0, 112, 0, 70); g.add_color_stop_rgba(0, 0.2, 0.05, 0.05, 0.25); g.add_color_stop_rgba(1, 0.2, 0.05, 0.05, 0)
        c.set_source(g); c.paint()
        for (hx, hy, hr_, ha) in ((lx * 45 + tx * 0.5, -55, 38, 0.13), (lx * 55 + tx, 28, 26, 0.10)):
            g = cairo.RadialGradient(hx, hy, 0, hx, hy, hr_)
            g.add_color_stop_rgba(0, 1, 0.97, 0.92, ha); g.add_color_stop_rgba(1, 1, 0.97, 0.92, 0); c.set_source(g); c.paint()
        # lighting: shadow on far side from light
        g = cairo.LinearGradient(lx * 110, ly * 110, -lx * 110, -ly * 110)
        g.add_color_stop_rgba(0, light_col[0], light_col[1], light_col[2], 0.2)
        g.add_color_stop_rgba(0.5, light_col[0], light_col[1], light_col[2], 0.0)
        g.add_color_stop_rgba(0.64, 0, 0, 0, 0.0); g.add_color_stop_rgba(0.66, 0, 0, 0, 0.26); g.add_color_stop_rgba(1, 0, 0, 0, 0.34)
        c.set_source(g); c.paint()
        if under:
            g = cairo.LinearGradient(0, 110, 0, -110); g.add_color_stop_rgba(0, 0.8, 0.9, 1, 0.25); g.add_color_stop_rgba(0.6, 0, 0, 0, 0); g.add_color_stop_rgba(1, 0, 0, 0, 0.5)
            c.set_source(g); c.paint()
        c.restore()  # clip
    # rim light on the lit side of the head
    lx, ly = light
    c.save(); c.translate(tx * 0.25, 0); _head_path(c); c.restore()
    c.save(); c.clip_preserve()
    g = cairo.LinearGradient(lx * 100, ly * 100, -lx * 40, -ly * 40)
    g.add_color_stop_rgba(0, light_col[0], light_col[1], light_col[2], 0.8); g.add_color_stop_rgba(1, light_col[0], light_col[1], light_col[2], 0)
    c.set_source(g); c.set_line_width(9); c.stroke(); c.restore(); c.new_path()
    c.save(); c.translate(tx * 0.25, 0); _head_path(c); c.restore(); src(c, INK); c.set_line_width(6); c.stroke()
    if not back: _hair_front(c, C, hair_l, tx, T)
    c.restore()  # head transform
    if alpha < 1: c.pop_group_to_source(); c.paint_with_alpha(alpha)
    c.restore()

def _body_shade(c, light, light_col):
    """Volume on the torso: key light wraps one side, the other falls into shadow, plus a rim."""
    lx, ly = light
    c.save()
    c.new_path(); c.move_to(-34, 120); c.line_to(34, 120)
    c.curve_to(120, 150, 210, 170, 235, 300); c.line_to(260, 1100); c.line_to(-260, 1100); c.line_to(-235, 300)
    c.curve_to(-210, 170, -120, 150, -34, 120); c.close_path(); c.clip()
    sg = 1 if lx >= 0 else -1
    g = cairo.LinearGradient(sg * 260, 0, -sg * 260, 0)
    g.add_color_stop_rgba(0, light_col[0], light_col[1], light_col[2], 0.12)
    g.add_color_stop_rgba(0.45, 0, 0, 0, 0.0); g.add_color_stop_rgba(1, 0, 0, 0, 0.45)
    c.set_source(g); c.paint()
    g = cairo.LinearGradient(0, 120, 0, 700); g.add_color_stop_rgba(0, 0, 0, 0, 0); g.add_color_stop_rgba(1, 0, 0, 0, 0.35)
    c.set_source(g); c.paint()
    g = cairo.LinearGradient(0, 110, 0, 220); g.add_color_stop_rgba(0, 0, 0, 0, 0.45); g.add_color_stop_rgba(1, 0, 0, 0, 0)  # chin shadow
    c.set_source(g); c.new_path(); c.arc(0, 130, 120, 0, PI); c.fill()
    c.restore()


def _cap(c, tx, back=False):
    c.new_path(); c.move_to(-100 + tx * 0.3, -55); c.curve_to(-100, -150, 100, -150, 100 + tx * 0.3, -55); c.close_path()
    inkfill(c, hexc('16213a'), 5)
    c.new_path(); c.rectangle(-100 + tx * 0.3, -70, 200, 18); src(c, hexc('0d1424')); c.fill()
    if not back:
        c.new_path(); c.move_to(-95 + tx, -55); c.curve_to(-60 + tx, -30, 60 + tx, -30, 95 + tx, -55); c.close_path(); src(c, hexc('0a0f1c')); c.fill()
        c.new_path(); c.arc(tx * 0.6, -100, 14, 0, 2 * PI); src(c, hexc('c9a24a')); c.fill()

def _fedora(c, tx):
    c.new_path(); c.save(); c.translate(tx * 0.5, -78); c.scale(1, 0.22); c.arc(0, 0, 175, 0, 2 * PI); c.restore(); inkfill(c, hexc('2a241c'), 5)
    c.new_path(); c.move_to(-88 + tx * 0.4, -80); c.curve_to(-95, -200, 95, -200, 88 + tx * 0.4, -80); c.close_path(); inkfill(c, hexc('332c22'), 5)
    c.new_path(); c.rectangle(-88 + tx * 0.4, -100, 176, 18); src(c, hexc('3a0d10')); c.fill()

def _hair_front(c, C, hair_l, tx, T):
    hs = C['hairstyle']
    if hs == 'bun':
        c.new_path(); c.move_to(-90 + tx * 0.2, -10); c.curve_to(-100, -110, -30, -132, 5 + tx, -126); c.curve_to(60, -132, 100, -100, 90 + tx * 0.2, -10)
        c.curve_to(80, -70, 40, -95, 5 + tx, -96); c.curve_to(-35, -95, -80, -70, -90 + tx * 0.2, -10); c.close_path(); inkfill(c, hair_l, 5)
        return
    if hs == 'bald':
        for sg in (-1, 1):
            c.new_path(); c.save(); c.translate(sg * 82 + tx * 0.2, -25); c.scale(0.5, 1); c.arc(0, 0, 30, 0, 2 * PI); c.restore(); inkfill(c, hair_l, 4)
        return
    if hs == 'fedora':
        _fedora(c, tx); return
    if hs == 'short':
        c.new_path(); c.move_to(-92 + tx * 0.2, -10)
        c.curve_to(-105, -110, -40, -140, 10, -128); c.curve_to(80, -130, 105, -80, 92 + tx * 0.2, -15)
        c.curve_to(85, -55, 60, -70, 40 + tx, -62)
        c.curve_to(30 + tx, -80, 0 + tx, -60, -10 + tx, -70)
        c.curve_to(-30 + tx, -55, -60, -70, -80, -40); c.close_path()
        inkfill(c, hair_l, 5)
    elif hs == 'cap':
        c.new_path(); c.rectangle(-90 + tx * 0.2, -40, 12, 40); src(c, hexc('8a8a8a')); c.fill()
        c.new_path(); c.rectangle(78 + tx * 0.2, -40, 12, 40); src(c, hexc('8a8a8a')); c.fill()
        _cap(c, tx)
    elif hs == 'shoulder':
        # side-swept fringe with a soft highlight
        c.new_path(); c.move_to(-96, 30); c.curve_to(-112, -100, -40, -138, 10 + tx, -128)
        c.curve_to(80, -132, 112, -90, 97, 20); c.curve_to(92, -30, 78, -62, 50 + tx, -72)
        c.curve_to(10 + tx, -50, -40 + tx, -40, -70 + tx * 0.5, -10); c.curve_to(-80, 0, -90, 15, -96, 30); c.close_path()
        inkfill(c, hair_l, 5)
        c.new_path(); c.move_to(-50 + tx * 0.3, -108); c.curve_to(-10, -122, 30, -120, 60, -104); src(c, hexc('ffffff'), 0.18); c.set_line_width(7); c.set_line_cap(cairo.LINE_CAP_ROUND); c.stroke()
    elif hs == 'long':
        c.new_path(); c.move_to(-95, 40); c.curve_to(-110, -100, -40, -135, 5 + tx, -125)
        c.curve_to(70, -130, 110, -90, 96, 40); c.curve_to(90, -20, 70, -70, 30 + tx, -85)
        c.curve_to(20 + tx, -40, -10 + tx, -70, -40 + tx, -85); c.curve_to(-70, -70, -88, -20, -95, 40); c.close_path()
        inkfill(c, hair_l, 5)
        # wet strands across face
        for i, (sx, ln, w) in enumerate(() if not C.get('wet') else ((-62, 150, 9), (-48, 110, 4), (66, 165, 8), (50, 120, 3))):
            sw = 3 * math.sin(T * 0.8 + i)
            c.new_path(); c.move_to(sx + tx * 0.5, -75); c.curve_to(sx + tx * 0.5 + 14 + sw, -10, sx + tx * 0.5 - 10, 50, sx + tx * 0.5 + 6 + sw, -75 + ln)
            src(c, hair_l); c.set_line_width(w); c.set_line_cap(cairo.LINE_CAP_ROUND); c.stroke()
        if C.get('wet'):
            for i in range(4):
                dy = (T * 60 + i * 37) % 160
                c.new_path(); c.arc(-60 + i * 40 + tx * 0.3, 60 + dy, 3, 0, 2 * PI); src(c, hexc('bfe0ff'), 0.6 * (1 - dy / 160)); c.fill()

def hand(c, x, y, s, skin, angle=0.0):
    c.save(); c.translate(x, y); c.scale(s, s); c.rotate(angle)
    c.new_path(); c.save(); c.scale(1, 0.75); c.arc(0, 0, 34, 0, 2 * PI); c.restore(); inkfill(c, hexc(skin), 5)
    for i in range(4):
        c.new_path(); c.move_to(-18 + i * 12, -18); c.line_to(-20 + i * 12, -46 + abs(i - 1.5) * 4); src(c, INK); c.set_line_width(19); c.set_line_cap(cairo.LINE_CAP_ROUND); c.stroke()
    for i in range(4):
        c.new_path(); c.move_to(-18 + i * 12, -18); c.line_to(-20 + i * 12, -46 + abs(i - 1.5) * 4); src(c, hexc(skin)); c.set_line_width(11); c.set_line_cap(cairo.LINE_CAP_ROUND); c.stroke()
    c.restore()
