#!/usr/bin/env python3
"""Extract hand-drawn glyphs from ONE Rnote SVG export and write each as a clean
svg/bb/<LETTER>.svg in the template coordinate system (baseline y=800, cap y=111),
so build.py's blackboard importer picks them up.

Usage: python import_rnote.py "<rnote.svg>" ABCDEFG...   (letters in drawing order,
       reading order = top-to-bottom rows, left-to-right within a row)
Targets: uppercase A-Z, lowercase a-z, digits 0-9 (named <char>.svg).
"""
import re, sys, os
import xml.etree.ElementTree as ET
import pathops
from fontTools.svgLib.path import parse_path
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.svgPathPen import SVGPathPen

SRC = sys.argv[1]
LETTERS = sys.argv[2] if len(sys.argv) > 2 else "ABC"
BASELINE, CAP_Y, LSB = 800, 111, 40           # template convention
CAPH = BASELINE - CAP_Y
NS = '{http://www.w3.org/2000/svg}'

root = ET.parse(SRC).getroot()
parent = {c: p for p in root.iter() for c in p}

def mul(A, B):
    a,b,c,d,e,f = A; g,h,i,j,k,l = B
    return (a*g+c*h, b*g+d*h, a*i+c*j, b*i+d*j, a*k+c*l+e, b*k+d*l+f)
def parse_tf(s):
    M = (1,0,0,1,0,0)
    for n, a in re.findall(r'(\w+)\s*\(([^)]*)\)', s or ''):
        v = [float(x) for x in re.split('[ ,]+', a.strip()) if x]
        if n == 'matrix': M = mul(M, tuple(v))
        elif n == 'translate': M = mul(M, (1,0,0,1, v[0], v[1] if len(v) > 1 else 0))
        elif n == 'scale': M = mul(M, (v[0],0,0, v[1] if len(v) > 1 else v[0], 0, 0))
    return M
def acc(el):
    ch = []; e = el
    while e is not None:
        if e.get('transform'): ch.append(e.get('transform'))
        e = parent.get(e)
    M = (1,0,0,1,0,0)
    for tr in reversed(ch): M = mul(M, parse_tf(tr))
    return M
def under_defs(el):
    e = el
    while e is not None:
        if e.tag.split('}')[-1] in ('defs','pattern','clipPath'): return True
        e = parent.get(e)
    return False

# collect ink strokes (black fill, not the page rect / not background)
strokes = []
for el in root.iter(NS+'path'):
    if under_defs(el):
        continue
    if not (el.get('fill') == '#000000' and (el.get('stroke') in (None,'none'))):
        continue
    d = el.get('d')
    if not d:
        continue
    M = acc(el); rec = RecordingPen(); parse_path(d, rec)
    bp = BoundsPen({}); rec.replay(TransformPen(bp, M))
    if not bp.bounds or (bp.bounds[2]-bp.bounds[0]) > 1000:
        continue
    x0,y0,x1,y1 = bp.bounds
    strokes.append({'cx':(x0+x1)/2,'cy':(y0+y1)/2,'rec':rec,'M':M,'b':bp.bounds})
print(f"{len(strokes)} ink strokes")

# rows: split sorted-by-cy where the gap is an outlier (inter-row gap >> dab gaps)
strokes.sort(key=lambda s: s['cy'])
cyg = [strokes[i+1]['cy']-strokes[i]['cy'] for i in range(len(strokes)-1)]
medy = sorted(cyg)[len(cyg)//2] or 1
rows = [[strokes[0]]]
for s, g in zip(strokes[1:], cyg):
    (rows.append([s]) if g > max(8*medy, 50) else rows[-1].append(s))
# letters within a row: split by WHITESPACE gap (> fraction of the row's letter height)
letters = []; per_row = []
for row in rows:
    row.sort(key=lambda s: s['cx'])
    row_h = max(s['b'][3] for s in row) - min(s['b'][1] for s in row)
    cur = [row[0]]; right = row[0]['b'][2]; n0 = len(letters)
    for s in row[1:]:
        if s['b'][0] - right > 0.16*row_h:
            letters.append(cur); cur = [s]
        else:
            cur.append(s)
        right = max(right, s['b'][2])
    letters.append(cur); per_row.append(len(letters) - n0)
print(f"{len(rows)} rows, {len(letters)} letters; expected {len(LETTERS)}; per row {per_row}")
if len(letters) != len(LETTERS):
    print("WARNING: letter count mismatch — check spacing/order")

os.makedirs("svg/bb", exist_ok=True)
for grp, ch in zip(letters, LETTERS):
    gx0 = min(s['b'][0] for s in grp); gx1 = max(s['b'][2] for s in grp)
    gy0 = min(s['b'][1] for s in grp); gy1 = max(s['b'][3] for s in grp)
    sc = CAPH / (gy1 - gy0)
    # page -> template: tx = sc*x + (LSB - sc*gx0); ty = sc*y + (BASELINE - sc*gy1)
    tmpl = (sc, 0, 0, sc, LSB - sc*gx0, BASELINE - sc*gy1)
    # each pen-stroke becomes its own closed path, unioned robustly via OpBuilder
    subs = []
    for s in grp:
        sp_ = pathops.Path()
        s['rec'].replay(TransformPen(TransformPen(sp_.getPen(), tmpl), s['M']))
        try:
            sp_ = pathops.simplify(sp_, fix_winding=True)   # clean each stroke first
        except pathops.PathOpsError:
            pass
        subs.append(sp_)
    try:
        b = pathops.OpBuilder(fix_winding=True, keep_starting_points=False)
        for sp_ in subs:
            b.add(sp_, pathops.PathOp.UNION)
        pp = b.resolve()
    except pathops.PathOpsError:
        pp = pathops.Path()
        for sp_ in subs:
            pp.addPath(sp_)
        try:
            pp = pathops.simplify(pp, fix_winding=True)
        except pathops.PathOpsError:
            print(f"  (union failed for {ch}; raw)")
    sp = SVGPathPen(None); pp.draw(sp)
    w = int(sc*(gx1-gx0) + 2*LSB)
    out = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} 1000">\n'
           f'  <path d="{sp.getCommands()}" fill="black"/>\n</svg>\n')
    open(f"svg/bb/{ch}.svg", "w").write(out)
    print(f"  wrote svg/bb/{ch}.svg")
