#!/usr/bin/env python3
"""Prototype: universal corner-rounding pass for untouched (raw-Fira) glyphs.

Loads the built ComicMathRelief.otf, rounds the sharp corners of a sample of
rare math symbols, writes _round.otf with family "Comic Math Round" so we can
render before/after side by side.
"""
import math, sys
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.boundsPen import BoundsPen
import pathops

R      = float(sys.argv[1]) if len(sys.argv) > 1 else 60.0   # target fillet radius (em/1000)
ANG    = float(sys.argv[2]) if len(sys.argv) > 2 else 35.0   # min corner angle (deg) to round
FRAC   = 0.5     # max fraction of a segment chord we may eat from one end
K      = 0.5     # fillet control-handle pull toward the vertex

def vsub(a, b): return (a[0]-b[0], a[1]-b[1])
def vadd(a, b): return (a[0]+b[0], a[1]+b[1])
def vscale(a, s): return (a[0]*s, a[1]*s)
def vlen(a): return math.hypot(a[0], a[1])
def vunit(a):
    l = vlen(a)
    return (a[0]/l, a[1]/l) if l else (0.0, 0.0)

def cub_point(P, t):
    mt = 1-t
    x = mt*mt*mt*P[0][0]+3*mt*mt*t*P[1][0]+3*mt*t*t*P[2][0]+t*t*t*P[3][0]
    y = mt*mt*mt*P[0][1]+3*mt*mt*t*P[1][1]+3*mt*t*t*P[2][1]+t*t*t*P[3][1]
    return (x, y)

def cub_split_right(P, t):
    """portion t..1 of the cubic, as 4 control points."""
    p0, p1, p2, p3 = P
    a = vadd(p0, vscale(vsub(p1, p0), t))
    b = vadd(p1, vscale(vsub(p2, p1), t))
    c = vadd(p2, vscale(vsub(p3, p2), t))
    d = vadd(a, vscale(vsub(b, a), t))
    e = vadd(b, vscale(vsub(c, b), t))
    f = vadd(d, vscale(vsub(e, d), t))
    return (f, e, c, p3)

def cub_split_left(P, t):
    """portion 0..t of the cubic."""
    p0, p1, p2, p3 = P
    a = vadd(p0, vscale(vsub(p1, p0), t))
    b = vadd(p1, vscale(vsub(p2, p1), t))
    c = vadd(p2, vscale(vsub(p3, p2), t))
    d = vadd(a, vscale(vsub(b, a), t))
    e = vadd(b, vscale(vsub(c, b), t))
    f = vadd(d, vscale(vsub(e, d), t))
    return (p0, a, d, f)

def cub_sub(P, t0, t1):
    return cub_split_left(cub_split_right(P, t0), (t1-t0)/(1-t0) if t0 < 1 else 0.0)

def parse_contours(rec):
    """RecordingPen value -> list of contours; each contour is a list of segs.
    seg = ('L', p0, p1) or ('C', p0, c1, c2, p1). Closed."""
    contours = []
    cur = None; start = None; pen_pt = None
    for op, args in rec.value:
        if op == "moveTo":
            if cur is not None: contours.append(cur)
            start = args[0]; pen_pt = start; cur = []
        elif op == "lineTo":
            assert cur is not None
            cur.append(('L', pen_pt, args[0])); pen_pt = args[0]
        elif op == "curveTo":
            c1, c2, p1 = args
            assert cur is not None
            cur.append(('C', pen_pt, c1, c2, p1)); pen_pt = p1
        elif op == "qCurveTo":
            # shouldn't happen for CFF, but handle: treat as line to last
            assert cur is not None
            cur.append(('L', pen_pt, args[-1])); pen_pt = args[-1]
        elif op in ("closePath", "endPath"):
            if cur:
                # close back to start if needed
                if vlen(vsub(pen_pt, start)) > 1e-3:
                    cur.append(('L', pen_pt, start))
                contours.append(cur); cur = None
    if cur: contours.append(cur)
    return contours

def seg_node_out(seg):
    """outgoing tangent direction at the seg start node."""
    if seg[0] == 'L': return vsub(seg[2], seg[1])
    d = vsub(seg[2], seg[1])               # c1 - p0
    return d if vlen(d) > 1e-6 else vsub(seg[4], seg[1])

def seg_node_in(seg):
    """incoming tangent direction arriving at the seg end node."""
    if seg[0] == 'L': return vsub(seg[2], seg[1])
    d = vsub(seg[-1], seg[-2])             # p1 - c2
    return d if vlen(d) > 1e-6 else vsub(seg[-1], seg[1])

def seg_len(seg):
    if seg[0] == 'L': return vlen(vsub(seg[2], seg[1]))
    # chord length (approx)
    return vlen(vsub(seg[-1], seg[1]))

def round_contour(segs):
    m = len(segs)
    if m < 2: return segs
    node = [s[1] for s in segs]            # node[i] = start of seg i = end of seg i-1
    # corner test + desired trim per node
    trim = [0.0]*m                          # trim radius applied at node i
    is_corner = [False]*m
    for i in range(m):
        din = seg_node_in(segs[(i-1) % m])
        dout = seg_node_out(segs[i])
        if vlen(din) < 1e-6 or vlen(dout) < 1e-6: continue
        ui, uo = vunit(din), vunit(dout)
        dot = max(-1.0, min(1.0, ui[0]*uo[0]+ui[1]*uo[1]))
        turn = math.degrees(math.acos(dot))   # 0 = straight, 180 = spike
        if turn >= ANG:
            is_corner[i] = True
            li = seg_len(segs[(i-1) % m]); lo = seg_len(segs[i])
            trim[i] = min(R, FRAC*li, FRAC*lo)
    # resolve overlap: per seg, trim at its two ends must fit its length
    for i in range(m):
        L = seg_len(segs[i])
        a = trim[i]; b = trim[(i+1) % m]
        if a+b > L and a+b > 0:
            sc = L/(a+b)
            trim[i] = min(trim[i], a*sc)
            trim[(i+1) % m] = min(trim[(i+1) % m], b*sc)
    if not any(is_corner): return segs
    # build output as list of pen ops: ('m',p) ('l',p) ('c',c1,c2,p)
    out = []
    # compute trimmed start/end points per seg
    def trim_seg(seg, ta, tb):
        """return (start_pt, mid_ops, end_pt) for seg trimmed by ta at start, tb at end.
        mid_ops is a list like [('l',end)] or [('c',c1,c2,end)] from start_pt."""
        if seg[0] == 'L':
            p0, p1 = seg[1], seg[2]
            u = vunit(vsub(p1, p0))
            s = vadd(p0, vscale(u, ta))
            e = vsub(p1, vscale(u, tb))
            return s, [('l', e)], e
        P = (seg[1], seg[2], seg[3], seg[4])
        L = seg_len(seg)
        t0 = (ta/L) if L else 0.0
        t1 = 1-(tb/L) if L else 1.0
        t0 = max(0.0, min(0.49, t0)); t1 = max(t0+0.01, min(1.0, t1))
        q = cub_sub(P, t0, t1)
        return q[0], [('c', q[1], q[2], q[3])], q[3]

    starts = []; ends = []; mids = []
    for i in range(m):
        ta = trim[i] if is_corner[i] else 0.0
        tb = trim[(i+1) % m] if is_corner[(i+1) % m] else 0.0
        s, mid, e = trim_seg(segs[i], ta, tb)
        starts.append(s); ends.append(e); mids.append(mid)
    # emit
    out.append(('m', starts[0]))
    for i in range(m):
        out.extend(mids[i])                       # trimmed segment i -> ends[i]
        j = (i+1) % m
        if is_corner[j]:
            # fillet from ends[i] (=B) around node[j] (=V) to starts[j] (=A)
            B = ends[i]; V = node[j]; A = starts[j]
            c1 = vadd(B, vscale(vsub(V, B), K))
            c2 = vadd(A, vscale(vsub(V, A), K))
            out.append(('c', c1, c2, A))
    return out

def round_glyph_charstring(cs, width, private):
    rec = RecordingPen(); cs.draw(rec)
    contours = parse_contours(rec)
    pen = T2CharStringPen(width, None)
    for segs in contours:
        ops = round_contour(segs)
        if not ops: continue
        if isinstance(ops[0], tuple) and ops[0][0] == 'm':
            for op in ops:
                if op[0] == 'm': pen.moveTo(op[1])
                elif op[0] == 'l': pen.lineTo(op[1])
                elif op[0] == 'c': pen.curveTo(op[1], op[2], op[3])
            pen.closePath()
        else:
            # untouched contour: replay raw
            first = True
            for seg in segs:
                if first: pen.moveTo(seg[1]); first = False
                if seg[0] == 'L': pen.lineTo(seg[2])
                else: pen.curveTo(seg[2], seg[3], seg[4])
            pen.closePath()
    return pen.getCharString(private=private)

# ---- run on a sample -------------------------------------------------------
TEST = "⊢⊣⊤⊥⊓⊔⊏⊐⊑⊒⊲⊳⊴⊵⋈⊞⊟⊠⊡⌐¬⋆◇△▽▷◁∠⊿†‡⊺⋄♦⊻⊼⊽⨆⨅∧∨⊕⊗⊞♢▢□■◆"

f = TTFont("fonts/ComicMathRelief.otf")
cmap = f.getBestCmap()
cff = f["CFF "].cff; topd = cff[cff.fontNames[0]]
charstrs = topd.CharStrings; private = topd.Private
hmtx = f["hmtx"]

present = []
for ch in TEST:
    assert cmap is not None
    g = cmap.get(ord(ch))
    if g and g in charstrs:
        present.append((ch, g))
print("rounding", len(present), "glyphs:", "".join(c for c, _ in present))

for ch, g in present:
    w = hmtx[g][0]
    try:
        charstrs[g] = round_glyph_charstring(charstrs[g], w, private)
    except Exception as e:
        print("  FAIL", ch, repr(e))

# rename family so it coexists with the original
TAG = "R%d" % int(R)
for rec in f["name"].names:
    if rec.nameID in (1, 4, 6, 16):
        s = rec.toUnicode().replace("Comic Math Relief", "Comic Math " + TAG)
        s = s.replace("ComicMathRelief", "ComicMath" + TAG)
        rec.string = s
f.save("_round_%s.otf" % TAG)
print("wrote _round_%s.otf  (R=%.0f ANG=%.0f)" % (TAG, R, ANG))
