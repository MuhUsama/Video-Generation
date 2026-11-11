"""Night Shift audio: TTS per line + sound design. Usage: python3 audio.py <episode_dir>"""
import json, sys, os, numpy as np, soundfile as sf
from scipy import signal
EP = sys.argv[1].rstrip('/') + '/'
MODELS = os.environ.get('KOKORO_DIR', os.path.dirname(os.path.abspath(__file__)) + '/models/')
SR = 24000
rng = np.random.default_rng(3)
S = json.load(open(EP + 'script.json'))
lines = S['lines']

from kokoro_onnx import Kokoro
k = Kokoro(MODELS + 'kokoro-v1.0.onnx', MODELS + 'voices-v1.0.bin')
for l in lines:
    if l['who'] == 'none': continue
    v, sp = S['voices'][l['who']]
    a, _ = k.create(l['text'], voice=v, speed=sp, lang='en-us')
    idx = np.where(np.abs(a) > 0.01)[0]; l['wav'] = a[max(0, idx[0] - 200):idx[-1] + 1000]

cur = 0.0; scenes = []
for l in lines:
    if not scenes or scenes[-1]['id'] != l['scene']:
        scenes.append({'id': l['scene'], 'start': cur, 'beats': []})
    l['gap'] = cur; st = cur + l['pre']
    if l['who'] == 'none':
        l['start'] = st; l['dur'] = 0; cur = st + 5.0; continue
    l['start'] = st; l['dur'] = len(l['wav']) / SR; cur = st + l['dur']
    scenes[-1]['beats'].append(st - scenes[-1]['start'])
TOTAL = cur
for j, s in enumerate(scenes):
    s['end'] = scenes[j + 1]['start'] if j + 1 < len(scenes) else TOTAL
N = int(TOTAL * SR) + 1; t = np.arange(N) / SR

def lp(x, f, o=2): return signal.sosfilt(signal.butter(o, f, 'low', fs=SR, output='sos'), x)
def hp(x, f, o=2): return signal.sosfilt(signal.butter(o, f, 'high', fs=SR, output='sos'), x)
def bp(x, a, b, o=4): return signal.sosfilt(signal.butter(o, [a, b], 'band', fs=SR, output='sos'), x)
def place(buf, x, at, g=1.0):
    s = int(max(at, 0) * SR); e = min(len(buf), s + len(x)); buf[s:e] += x[:e - s] * g
def reverb(x, secs=1.6, wet=0.35):
    n = int(secs * SR); ir = rng.standard_normal(n) * np.exp(-np.arange(n) / SR * 4.5)
    ir = lp(ir, 3500); y = signal.fftconvolve(x, ir)
    out = np.zeros(len(y)); out[:len(x)] = x * (1 - wet)
    return out + y * wet / max(1e-9, np.abs(y).max()) * np.abs(x).max()

vox = np.zeros(N + SR * 4)
for l in lines:
    if 'wav' not in l: continue
    a = l['wav'].astype(np.float64); fx = l.get('fx')
    if fx == 'phone': a = bp(a, 350, 3200); a = np.tanh(a * 3) * 0.45 + rng.standard_normal(len(a)) * 0.006
    elif fx == 'close': a = reverb(a * 1.3, 2.2, 0.45)
    elif l['who'] == 'narrator': a = reverb(a, 0.8, 0.12)
    else: a = reverb(a, 0.6, 0.1)
    place(vox, a, l['start']); l.pop('wav')
vox = vox[:N]

fxb = np.zeros(N)
def scene_mask(ids, fade=0.5):
    m = np.zeros(N)
    for s in scenes:
        if s['id'] in ids:
            m += np.clip((t - s['start']) / fade, 0, 1) * np.clip((s['end'] - t) / fade, 0, 1)
    return np.clip(m, 0, 1)
AMB = {'exterior': 'rain_out', 'desk': 'rain_in', 'keys': 'rain_in', 'hall': 'rain_in', 'behind': 'rain_in',
       'room': 'rain_in', 'book': 'rain_in', 'room_phone': 'rain_in', 'desk_other': 'rain_in', 'logbook': 'rain_in',
       'road': 'engine_out', 'bus': 'engine_in', 'mirror': 'engine_in', 'sign': 'engine_in', 'stop': 'fog',
       'news': 'none', 'dawn': 'engine_idle', 'ticket': 'engine_idle', 'title': 'none'}
used = {AMB.get(s['id'], 'none') for s in scenes}
rain = bp(rng.standard_normal(N), 600, 7000) * 0.05
rain += hp((rng.random(N) < 0.0008) * rng.standard_normal(N), 2000) * 0.25
def ids_for(kind): return [s['id'] for s in scenes if AMB.get(s['id']) == kind]
if 'rain_out' in used: fxb += rain * scene_mask(ids_for('rain_out'))
if 'rain_in' in used: fxb += lp(rain, 900) * 1.1 * scene_mask(ids_for('rain_in'))
eng = lp(sum(np.sin(2 * np.pi * f * t + p) for f, p in [(38, 0), (76, 1), (114, 2)]) * (1 + 0.3 * np.sin(2 * np.pi * 7 * t)), 300) * 0.06
eng += lp(rng.standard_normal(N), 200) * 0.05
for kind, g in (('engine_out', 1.0), ('engine_in', 0.7), ('engine_idle', 0.35)):
    if kind in used: fxb += eng * g * scene_mask(ids_for(kind))
if 'fog' in used:
    wind = bp(rng.standard_normal(N), 200, 900) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.15 * t)) * 0.06
    fxb += wind * scene_mask(ids_for('fog'))
drone = sum(np.sin(2 * np.pi * f * t + p) for f, p in [(55, 0), (55.4, 1), (82.4, 2), (110.7, 0.5)])
fxb += lp(drone, 400) * (0.02 + 0.05 * (t / TOTAL) ** 2)

thunders = []
def thunder(at, g=1.0):
    n = int(4 * SR); x = rng.standard_normal(n); tt = np.arange(n) / SR
    y = lp(x, 180, 3) * np.exp(-tt * 1.3) * (1 - np.exp(-tt * 30)) * 3.5
    c = int(0.25 * SR); y[:c] += hp(rng.standard_normal(c), 1500) * np.exp(-tt[:c] * 18) * 0.4
    place(fxb, y * g, at); thunders.append(at)
def ring(at, n=2, g=1.0, far=False):
    for i in range(n):
        L = int(0.9 * SR); tt = np.arange(L) / SR
        r = (np.sin(2 * np.pi * 440 * tt) + np.sin(2 * np.pi * 480 * tt)) * (np.sin(2 * np.pi * 20 * tt) > 0) * 0.06
        r *= np.minimum(1, tt / 0.01) * np.minimum(1, (0.9 - tt) / 0.02)
        r = bp(r, 300, 3000) * 1.4
        if far: r = reverb(lp(r, 1500), 2.5, 0.6) * 0.6
        place(fxb, r * g, at + i * 1.6)
def click(at):
    c = int(0.05 * SR); place(fxb, hp(rng.standard_normal(c), 1500) * np.exp(-np.arange(c) / SR * 80) * 0.3, at)
def doors(at):
    L = int(1.0 * SR); tt = np.arange(L) / SR
    hiss = bp(rng.standard_normal(L), 2000, 8000) * np.exp(-tt * 3) * 0.25
    clunk = lp(rng.standard_normal(L), 150) * np.exp(-np.maximum(tt - 0.7, 0) * 20) * (tt > 0.7) * 1.2
    place(fxb, hiss + clunk, at)
def sting(at, g=1.0):
    L = int(3.5 * SR); tt = np.arange(L) / SR
    s = sum(np.sin(2 * np.pi * f * tt) for f in (73.4, 77.8, 146.8, 155.6, 311)) * np.exp(-tt * 1.1) * 0.12
    s += lp(rng.standard_normal(L), 300) * np.exp(-tt * 3) * 0.6
    place(fxb, s * g, at)
ring_times = []
for l in lines:
    for sx in l.get('sfx', []):
        at = l['gap'] + 0.1
        if sx == 'thunder': thunder(at, 1.0)
        elif sx == 'ring': ring(at, 1 if l['pre'] < 1.2 else 1); ring_times.append(at)
        elif sx == 'ring_far': ring(l['start'] + l['dur'] * 0.6, 2, 1.0, far=True); ring_times.append(l['start'] + l['dur'] * 0.6)
        elif sx == 'click': click(l['start'] - 0.25)
        elif sx == 'doors': doors(at)
        elif sx == 'sting_soft': sting(l['start'] - 0.1, 0.5)
        elif sx == 'engine_start': pass
# thunder in rainy episodes at the very start
if 'rain_out' in used or 'rain_in' in used:
    if not thunders or thunders[0] > 3: thunder(0.6, 0.8)
# heartbeat in hall / mirror / sign
def thump(at, g):
    L = int(0.25 * SR); tt = np.arange(L) / SR; place(fxb, np.sin(2 * np.pi * 50 * tt) * np.exp(-tt * 18) * g, at)
for s in scenes:
    if s['id'] in ('hall', 'mirror', 'sign', 'room', 'desk_other'):
        hb = s['start'] + 0.4
        while hb < s['end'] - 0.2:
            k2 = (hb - s['start']) / (s['end'] - s['start'])
            thump(hb, 0.3 + 0.2 * k2); thump(hb + 0.22, 0.2 + 0.15 * k2); hb += 60 / (70 + 40 * k2)
title = next(s for s in scenes if s['id'] == 'title')
sting(title['start'] - 0.05)
fxb *= np.clip((TOTAL - t) / 1.5, 0, 1) * np.clip(t / 0.4, 0, 1)
venv = np.convolve(np.abs(vox), np.ones(2400) / 2400, 'same')
mix = vox + fxb * (1 - 0.4 * np.clip(venv / 0.04, 0, 1))
mix = mix / np.abs(mix).max() * 0.9
sf.write(EP + 'mix.wav', mix.astype(np.float32), SR)
# lip-sync envelope at 30 fps per line
hop = SR // 30
for l in lines:
    if l['who'] == 'none': continue
    s0 = int(l['start'] * SR); n = int(l['dur'] * 30) + 1
    seg = vox[s0:s0 + n * hop]
    env = [float(np.sqrt(np.mean(seg[i * hop:(i + 1) * hop] ** 2))) if len(seg[i * hop:(i + 1) * hop]) else 0.0 for i in range(n)]
    ref = np.percentile(env, 90) if max(env) > 0 else 1
    l['env'] = [round(min(1.0, e / ref), 3) for e in env]
json.dump({'total': TOTAL, 'scenes': scenes, 'lines': lines, 'thunder': sorted(thunders), 'rings': ring_times,
           'params': S.get('params', {}), 'title': S['title']}, open(EP + 'timing.json', 'w'), indent=1)
print(round(TOTAL, 2), [(s['id'], round(s['start'], 1)) for s in scenes])
