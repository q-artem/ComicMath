#!/usr/bin/env python3
"""Comic Math: a Comic Sans-style math font for Typst, built on Fira Math.

Keeps Fira Math's OpenType MATH table, metrics and per-glyph advance widths and
replaces the outlines. In the default "relief" mode the Latin, Greek, Cyrillic
and digits come from Comic Relief; operators, relations, the radical, brackets,
arrows, accents and the prime are drawn procedurally; blackboard letters are
imported from hand-drawn SVGs (svg/bb/, see import_rnote.py); calligraphic,
fraktur and bold are grafted from Courgette / UnifrakturCook / Comic Relief
Bold. Italic math slots are sheared 12 deg (Comic Relief has no italic). The
"neue" mode instead sources the Latin from Comic Neue.

Usage:  python build.py [wobble] [relief|neue]
  wobble : outline-distortion strength (0 = clean, the default)
  donor  : Latin donor, "relief" (default) or "neue"
Output: fonts/ComicMathRelief.otf (relief) or fonts/ComicMath-Regular.otf (neue).
"""
import math, sys, random, os
import xml.etree.ElementTree as ET
import pathops
from fontTools.svgLib.path import parse_path
from fontTools.ttLib import TTFont
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.qu2cuPen import Qu2CuPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.recordingPen import DecomposingRecordingPen, RecordingPen
from fontTools.pens.boundsPen import BoundsPen

BASE    = "fonts/FiraMath-Regular.otf"
COMIC_I = "fonts/ComicNeue-Italic.ttf"     # Latin math variables (already slanted)
COMIC_R = "fonts/ComicNeue-Regular.ttf"    # Latin digits + upright
GREEK   = "fonts/donor-ComicRelief.ttf"    # Greek (comic style), upright
# argv[1] = wobble strength (0 = clean). argv[2] = latin donor: "relief" | "neue"
WOBBLE  = float(sys.argv[1]) if len(sys.argv) > 1 else 0.0
LATIN   = sys.argv[2] if len(sys.argv) > 2 else "relief"   # default = release variant
_parts  = ["Comic Math"] + (["Relief"] if LATIN == "relief" else []) + (["Wobble"] if WOBBLE else [])
FAMILY  = " ".join(_parts)
OUT     = "fonts/" + FAMILY.replace(" ", "") + ".otf" if len(_parts) > 1 else "fonts/ComicMath-Regular.otf"

fira = TTFont(BASE);    fira_cmap = fira.getBestCmap(); fira_gs = fira.getGlyphSet()
ci   = TTFont(COMIC_I); ci_cmap = ci.getBestCmap();     ci_gs = ci.getGlyphSet()
cr   = TTFont(COMIC_R); cr_cmap = cr.getBestCmap();     cr_gs = cr.getGlyphSet()
gk   = TTFont(GREEK);   gk_cmap = gk.getBestCmap();     gk_gs = gk.getGlyphSet()
crb  = TTFont("fonts/donor-ComicReliefBold.ttf")        # bold latin/greek/digits
crb_cmap = crb.getBestCmap(); crb_gs = crb.getGlyphSet()
pac  = TTFont("fonts/donor-Courgette.ttf")              # casual script -> calligraphic
pac_cmap = pac.getBestCmap(); pac_gs = pac.getGlyphSet()
_pnb = BoundsPen(pac_gs); pac_gs[pac_cmap[ord('N')]].draw(_pnb)   # OS/2 capheight is bogus
PAC_CAP = _pnb.bounds[3] - _pnb.bounds[1]              # measure real cap height

cff      = fira["CFF "].cff
top      = cff[cff.fontNames[0]]
charstrs = top.CharStrings
private  = top.Private
gsubrs   = cff.GlobalSubrs
hmtx     = fira["hmtx"]

# Snapshot original charstring identities. Any glyph we never reassign keeps its
# object identity, so the final corner-rounding pass can target exactly the
# untouched raw-Fira symbols (the long tail) and skip everything we restyled.
_ORIG_IDS = {g: id(charstrs[g]) for g in charstrs.keys()}

F_X, F_CAP = fira["OS/2"].sxHeight, fira["OS/2"].sCapHeight
S_LOW = F_X   / ci["OS/2"].sxHeight        # Comic Neue lowercase -> Fira x-height
S_CAP = F_CAP / ci["OS/2"].sCapHeight      # Comic Neue uppercase/digits -> cap-height
G_LOW = F_X   / gk["OS/2"].sxHeight        # Comic Relief greek lowercase
G_CAP = F_CAP / gk["OS/2"].sCapHeight      # Comic Relief greek uppercase
B_LOW = F_X   / crb["OS/2"].sxHeight       # Comic Relief Bold lowercase
B_CAP = F_CAP / crb["OS/2"].sCapHeight     # Comic Relief Bold uppercase/digits
SKEW  = math.tan(math.radians(12))         # match Comic Neue italic angle (-12)

LOWER = "abcdefghijklmnopqrstuvwxyz"
UPPER = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

# jobs: (target_cp_in_fira, source_cp, source_cmap, source_glyphset, scale, skew)
jobs = []

# --- Latin -------------------------------------------------------------------
if LATIN == "relief":
    # all latin from Comic Relief (upright donor): shear italic slots like greek
    IT_CMAP, IT_GS, UP_CMAP, UP_GS = gk_cmap, gk_gs, gk_cmap, gk_gs
    L_LOW, L_CAP, IT_SKEW = G_LOW, G_CAP, SKEW
else:
    # Comic Neue: Italic donor for italic slots (pre-slanted), Regular for upright
    IT_CMAP, IT_GS, UP_CMAP, UP_GS = ci_cmap, ci_gs, cr_cmap, cr_gs
    L_LOW, L_CAP, IT_SKEW = S_LOW, S_CAP, 0

for i, ch in enumerate(LOWER):                       # math italic lowercase
    tgt = 0x210E if ch == "h" else 0x1D44E + i       # h -> PLANCK
    jobs.append((tgt, ord(ch), IT_CMAP, IT_GS, L_LOW, IT_SKEW))
for i, ch in enumerate(UPPER):                       # math italic uppercase
    jobs.append((0x1D434 + i, ord(ch), IT_CMAP, IT_GS, L_CAP, IT_SKEW))
for i in range(10):                                  # digits (upright)
    jobs.append((0x30 + i, ord(str(i)), UP_CMAP, UP_GS, L_CAP, 0))
for ch in LOWER:                                     # ascii upright lowercase
    jobs.append((ord(ch), ord(ch), UP_CMAP, UP_GS, L_LOW, 0))
for ch in UPPER:                                     # ascii upright uppercase
    jobs.append((ord(ch), ord(ch), UP_CMAP, UP_GS, L_CAP, 0))

# --- Greek (Comic Relief, upright donor) -------------------------------------
# lowercase 0x03B1..0x03C9 maps 1:1 (incl. final sigma) to italic block 0x1D6FC..
for i in range(25):
    plain = 0x03B1 + i
    jobs.append((0x1D6FC + i, plain, gk_cmap, gk_gs, G_LOW, SKEW))  # italic slot (default)
    jobs.append((plain,        plain, gk_cmap, gk_gs, G_LOW, 0))    # upright slot
# uppercase upright (math default); skip reserved 0x03A2
for cp in range(0x0391, 0x03AA):
    if cp == 0x03A2:
        continue
    jobs.append((cp, cp, gk_cmap, gk_gs, G_CAP, 0))

# --- Cyrillic (Comic Relief) for text-in-math, e.g. subscript "дуга" ----------
for cp in list(range(0x0410, 0x0430)) + [0x0401]:    # А-Я + Ё (upright)
    jobs.append((cp, cp, gk_cmap, gk_gs, G_CAP, 0))
for cp in list(range(0x0430, 0x0450)) + [0x0451]:    # а-я + ё
    jobs.append((cp, cp, gk_cmap, gk_gs, G_LOW, 0))

# --- Bold + Bold-italic (Comic Relief Bold; donor is upright -> shear italics) -
for i in range(26):                                   # bold / bold-italic Latin
    jobs.append((0x1D400 + i, 0x41 + i, crb_cmap, crb_gs, B_CAP, 0))
    jobs.append((0x1D468 + i, 0x41 + i, crb_cmap, crb_gs, B_CAP, SKEW))
    jobs.append((0x1D41A + i, 0x61 + i, crb_cmap, crb_gs, B_LOW, 0))
    jobs.append((0x1D482 + i, 0x61 + i, crb_cmap, crb_gs, B_LOW, SKEW))
for i in range(10):                                   # bold digits
    jobs.append((0x1D7CE + i, 0x30 + i, crb_cmap, crb_gs, B_CAP, 0))
for cp in range(0x0391, 0x03AA):                      # bold greek uppercase (upright)
    if cp != 0x03A2:
        jobs.append((0x1D6A8 + (cp - 0x391), cp, crb_cmap, crb_gs, B_CAP, 0))
for cp in range(0x03B1, 0x03CA):                      # bold greek lowercase (upright)
    jobs.append((0x1D6C2 + (cp - 0x3B1), cp, crb_cmap, crb_gs, B_LOW, 0))

def hcenter(b):
    return (b[0] + b[2]) / 2 if b else 0

def replay_mapped(recording, pf, outpen):
    """Replay a recorded outline, passing every point through pf(x,y)->(x,y)."""
    for op, args in recording:
        if op == "moveTo":   outpen.moveTo(pf(*args[0]))
        elif op == "lineTo": outpen.lineTo(pf(*args[0]))
        elif op == "qCurveTo":
            outpen.qCurveTo(*[pf(*p) if p is not None else None for p in args])
        elif op == "curveTo":
            outpen.curveTo(*[pf(*p) for p in args])
        elif op == "closePath": outpen.closePath()
        elif op == "endPath":   outpen.endPath()

def make_pointfunc(gname, s, skew, dx, cx, cy):
    """affine (scale+shear+shift) -> tiny rotation -> domain warp (hand-drawn)."""
    if not WOBBLE:
        return lambda x, y: (s * x + skew * s * y + dx, s * y)
    rng = random.Random(gname)               # deterministic per glyph
    px1, py1 = rng.uniform(0, 6.283), rng.uniform(0, 6.283)
    px2, py2 = rng.uniform(0, 6.283), rng.uniform(0, 6.283)
    ang = math.radians(rng.uniform(-1.3, 1.3)) * WOBBLE
    ca, sa = math.cos(ang), math.sin(ang)
    A  = 9.0 * WOBBLE                         # warp amplitude (em=1000)
    W1 = 2 * math.pi / 175.0                  # primary wavelength
    W2 = 2 * math.pi / 76.0                   # finer octave
    def pf(x, y):
        ax = s * x + skew * s * y + dx; ay = s * y          # affine
        rx = cx + (ax - cx) * ca - (ay - cy) * sa           # rotate about centre
        ry = cy + (ax - cx) * sa + (ay - cy) * ca
        wx = rx + A * math.sin(W1 * ry + px1) + 0.45 * A * math.sin(W2 * ry + px2)
        wy = ry + A * math.sin(W1 * rx + py1) + 0.45 * A * math.sin(W2 * rx + py2)
        return (wx, wy)
    return pf

done = skip = 0
grafted_letters = set()                              # for sidebearing normalisation below
for tgt, src_cp, src_cmap, src_gs, s, skew in jobs:
    gname = fira_cmap.get(tgt)
    src   = src_cmap.get(src_cp)
    if gname is None or src is None or gname not in charstrs:
        skip += 1; continue
    grafted_letters.add(gname)

    # horizontal centre of the original Fira glyph (preserve placement)
    ob = BoundsPen(fira_gs); fira_gs[gname].draw(ob)
    ocx = hcenter(ob.bounds)

    rec = DecomposingRecordingPen(src_gs); src_gs[src].draw(rec)

    # measure source after scale+shear (dx=0) to align centres
    mb = BoundsPen(src_gs); rec.replay(TransformPen(mb, (s, 0, skew * s, s, 0, 0)))
    dx = ocx - hcenter(mb.bounds)
    cy = (mb.bounds[1] + mb.bounds[3]) / 2 if mb.bounds else 0

    width = hmtx[gname][0]                            # keep Fira's advance width
    t2 = T2CharStringPen(width, src_gs)
    pf = make_pointfunc(gname, s, skew, dx, ocx, cy)
    replay_mapped(rec.value, pf, Qu2CuPen(t2, max_err=0.6, reverse_direction=True))
    charstrs[gname] = t2.getCharString(private=private)
    done += 1

# --- normalise sidebearings: comic outlines are wider than Fira's, so wide -----
#     glyphs (esp. the sheared italic caps like I/J) overhang their advance box
#     and collide with neighbours. Guarantee a minimum L/R sidebearing by
#     shifting right + growing the advance. Only ever GROWS the box, so glyphs
#     that already sit comfortably are left untouched.
MIN_LSB = 40        # minimum left sidebearing  (em/1000)
MIN_RSB = 40        # minimum right sidebearing
def fit_sidebearings(gname, min_l=MIN_LSB, min_r=MIN_RSB):
    if gname not in charstrs:
        return
    cs = charstrs[gname]
    bp = BoundsPen(None); cs.draw(bp)
    if not bp.bounds:
        return
    xmin, _, xmax, _ = bp.bounds
    aw = hmtx[gname][0]
    shift  = max(0, min_l - xmin)                    # push right if ink overhangs left
    new_xmax = xmax + shift
    new_aw = max(aw, int(round(new_xmax + min_r)))   # grow advance for right clearance
    if shift == 0 and new_aw == aw:
        return                                       # already comfortable
    pen = T2CharStringPen(new_aw, None)
    cs.draw(TransformPen(pen, (1, 0, 0, 1, shift, 0)))
    charstrs[gname] = pen.getCharString(private=private)
    hmtx[gname] = (new_aw, int(round(xmin + shift)))

sb_fixed = 0
for gname in grafted_letters:
    before = hmtx[gname][0]
    fit_sidebearings(gname)
    if hmtx[gname][0] != before:
        sb_fixed += 1
print(f"sidebearing-normalised {sb_fixed} wide glyphs (min L/R = {MIN_LSB}/{MIN_RSB})")

# --- adjust digit stroke weight ----------------------------------------------
#   d > 0  -> DILATE (thicker): stroke the contour and UNION it, growing the
#            stroke ~2*d outward.  d < 0 -> erode (thinner) via DIFFERENCE.
#   Digit comic stroke is ~75/1000em; DIGIT_WEIGHT=6 ≈ +15% thicker.
DIGIT_WEIGHT = 6
def reweight_glyph(gname, d):
    if gname not in charstrs or d == 0:
        return
    src = pathops.Path(); charstrs[gname].draw(src.getPen())
    rib = pathops.Path(); charstrs[gname].draw(rib.getPen())
    rib.stroke(2*abs(d), pathops.LineCap.ROUND_CAP, pathops.LineJoin.ROUND_JOIN, 4)
    rib.convertConicsToQuads(0.5)
    op = pathops.PathOp.UNION if d > 0 else pathops.PathOp.DIFFERENCE
    try:
        res = pathops.op(src, rib, op, fix_winding=True)
    except pathops.PathOpsError:
        return
    res.convertConicsToQuads(0.5)
    w = hmtx[gname][0]
    t2 = T2CharStringPen(w, None); res.draw(Qu2CuPen(t2, max_err=0.6))
    charstrs[gname] = t2.getCharString(private=private, globalSubrs=gsubrs)
if DIGIT_WEIGHT:
    for cp in range(0x30, 0x3A):                 # plain digits 0-9
        g = fira_cmap.get(cp)
        if g:
            reweight_glyph(g, DIGIT_WEIGHT)

# digit "1" is narrow but inherits Fira's tabular advance (560) -> big right gap
# (rsb ~186). Trim its advance to make it proportional so it doesn't trail space.
_g1 = fira_cmap.get(0x31)
if _g1 and _g1 in charstrs:
    _bp = BoundsPen(None); charstrs[_g1].draw(_bp)
    if _bp.bounds:
        _x0, _, _x1, _ = _bp.bounds
        hmtx[_g1] = (int(round(_x1 + max(_x0, 60))), hmtx[_g1][1])   # rsb ≈ lsb

# --- Symbols (operators, relations, big operators) from Comic Relief ----------
CR_STROKE   = 75.2 * gk["head"].unitsPerEm / 1000   # donor stroke in donor units (~154)
STROKE_MAX  = 96                                     # target symbol stroke (20% thinner)
STROKE_CAP  = STROKE_MAX / CR_STROKE                 # horizontal scale that yields it (~0.62)
SIZE_CAP    = 0.78                                   # vertical scale cap for big operators

def graft_symbol(gname, donor_cp, stroke_cap=False, size_cap=None):
    """Fit a Comic Relief symbol into the bbox of a Fira glyph, keeping Fira's
    advance width. Non-uniform: x-scale capped to hold a constant stroke weight,
    y-scale free (to reach height) so big variants don't balloon in thickness."""
    if gname not in charstrs:
        return False
    src = gk_cmap.get(donor_cp)
    if src is None:
        return False
    ob = BoundsPen(fira_gs); fira_gs[gname].draw(ob)
    if not ob.bounds:
        return False
    oxmin, oymin, oxmax, oymax = ob.bounds
    rec = DecomposingRecordingPen(gk_gs); gk_gs[src].draw(rec)
    db = BoundsPen(gk_gs); rec.replay(db)
    if not db.bounds:
        return False
    dxmin, dymin, dxmax, dymax = db.bounds
    dh = dymax - dymin
    if dh <= 0:
        return False
    s_h = (oymax - oymin) / dh                                   # height-fit scale
    sx = min(s_h, STROKE_CAP) if stroke_cap else s_h             # constant stroke weight
    sy = min(s_h, size_cap) if size_cap else s_h                 # height (capped for big ops)
    tx = (oxmin + oxmax) / 2 - sx * (dxmin + dxmax) / 2          # centre x
    ty = (oymin + oymax) / 2 - sy * (dymin + dymax) / 2          # centre y
    t2 = T2CharStringPen(hmtx[gname][0], gk_gs)
    rec.replay(TransformPen(Qu2CuPen(t2, max_err=0.6, reverse_direction=True),
                            (sx, 0, 0, sy, tx, ty)))
    charstrs[gname] = t2.getCharString(private=private)
    return True

# single-glyph operators / relations (skipped silently if donor lacks the cp)
SIMPLE = [0x2202, 0x221E, 0x00B1, 0x00D7, 0x00F7, 0x2212, 0x002B, 0x0021,
          0x2248, 0x2192, 0x21D2, 0x2208,
          0x2219, 0x003C, 0x003E, 0x00AC, 0x2113, 0x2026]  # bullet < > neg ell ldots !
          # =, !=, <=, >=, prime are synthesised below (rounded/Russian-style/larger)
# big operators: each maps to its inline + .display variant glyph names
BIG = {0x2211: ["uni2211", "uni2211.display"],
       0x220F: ["uni220F", "uni220F.display"],
       0x222B: ["uni222B", "uni222B.display"]}
# radical: drawn procedurally in a comic stroke with a FLAT top arm (thickness =
# RadicalRuleThickness) so it merges with the engine vinculum at any size. Only the
# straight rise lengthens between sizes — the foot and arm stay fixed.
RAD_W = 96   # comic radical stroke weight (also the rule thickness)
COMIC_RADICAL = ["uni221A"] + [f"uni221A.size{i}" for i in range(1, 16)]

def _cw(pts):
    a = sum(pts[i][0]*pts[(i+1) % len(pts)][1] - pts[(i+1) % len(pts)][0]*pts[i][1]
            for i in range(len(pts)))
    return pts[::-1] if a > 0 else pts            # force clockwise (area < 0)

def _seg(ax, ay, bx, by, w):
    dx, dy = bx-ax, by-ay
    L = math.hypot(dx, dy)
    if L == 0:
        return None
    nx, ny = -dy/L*w/2, dx/L*w/2
    return _cw([(ax+nx, ay+ny), (bx+nx, by+ny), (bx-nx, by-ny), (ax-nx, ay-ny)])

def _disc(cx, cy, r, n=16):
    return _cw([(cx+r*math.cos(2*math.pi*i/n), cy+r*math.sin(2*math.pi*i/n))
                for i in range(n)])

def _catmull(pts, n=12):
    """Sample a Catmull-Rom spline through pts (with reflected end tangents)."""
    P = [(2*pts[0][0]-pts[1][0], 2*pts[0][1]-pts[1][1])] + list(pts) + \
        [(2*pts[-1][0]-pts[-2][0], 2*pts[-1][1]-pts[-2][1])]
    out = []
    for i in range(1, len(P)-2):
        p0, p1, p2, p3 = P[i-1], P[i], P[i+1], P[i+2]
        for s in range(n):
            t = s/n; t2 = t*t; t3 = t2*t
            x = 0.5*((2*p1[0]) + (-p0[0]+p2[0])*t +
                     (2*p0[0]-5*p1[0]+4*p2[0]-p3[0])*t2 +
                     (-p0[0]+3*p1[0]-3*p2[0]+p3[0])*t3)
            y = 0.5*((2*p1[1]) + (-p0[1]+p2[1])*t +
                     (2*p0[1]-5*p1[1]+4*p2[1]-p3[1])*t2 +
                     (-p0[1]+3*p1[1]-3*p2[1]+p3[1])*t3)
            out.append((x, y))
    out.append(pts[-1])
    return out

def _emit(pen, contours):
    for ct in contours:
        if not ct:
            continue
        pen.moveTo(ct[0])
        for p in ct[1:]:
            pen.lineTo(p)
        pen.closePath()

def emit_pathops(gname, draw_fn):
    """Run draw_fn(pen) into a Skia path, union/clean it, store as the glyph
    (keeps Fira's advance width). Lets composite shapes overlap freely."""
    if gname not in charstrs:
        return False
    p = pathops.Path()
    draw_fn(p.getPen())
    p = pathops.simplify(p, fix_winding=True)
    t2 = T2CharStringPen(hmtx[gname][0], None)
    p.draw(t2)
    charstrs[gname] = t2.getCharString(private=private)
    return True

def _ring(cx, cy, R, th, n=44):
    pts = [(cx + R*math.cos(2*math.pi*i/n), cy + R*math.sin(2*math.pi*i/n)) for i in range(n)]
    pts.append(pts[0])
    cs  = [_seg(*pts[i], *pts[i+1], th) for i in range(len(pts)-1)]
    cs += [_disc(*p, th/2, 10) for p in pts[:-1]]
    return cs

def draw_comic_radical(gname, w):
    if gname not in charstrs:
        return False
    ob = BoundsPen(fira_gs); fira_gs[gname].draw(ob)
    if not ob.bounds:
        return False
    x0, y0, x1, y1 = ob.bounds
    W  = hmtx[gname][0]
    Wd = W - x0
    H  = y1 - y0
    top = y1 - w/2                                  # arm centreline (top edge at y1)
    # control points: small rounded foot -> bottom -> rise -> peak -> arm -> flat end
    ctrl = [(x0 + 0.18*Wd, y0 + 0.26*H),           # flag tip (short, rounded foot)
            (x0 + 0.37*Wd, y0 + 0.05*H + 0.3*w),   # rounded bottom
            (x0 + 0.70*Wd, top - 0.05*H),          # lower rise (steeper, peak later)
            (x0 + 0.85*Wd, top),                   # peak near advance -> short arm
            (x0 + 0.93*Wd, top),                   # short arm (horizontal tangent)
            (W, top)]                              # arm end -> flat butt at vinculum
    center = _catmull(ctrl, n=14)                   # smooth dense centreline
    center = [(x, min(y, top)) for x, y in center]  # clamp out spline overshoot above arm
    contours  = [_seg(*center[i], *center[i+1], w) for i in range(len(center)-1)]
    contours += [_disc(*p, w/2) for p in center[:-1]]   # round profile + round foot cap
    return emit_pathops(gname, lambda pen: _emit(pen, contours))

def graft_multi_integral(gname, n, contour=False, w=96):
    """Build ∬ ∮ ∭ from comic ∫ copies (+ ring for contour integrals)."""
    if gname not in charstrs:
        return False
    src = gk_cmap.get(0x222B)
    if src is None:
        return False
    ob = BoundsPen(fira_gs); fira_gs[gname].draw(ob)
    if not ob.bounds:
        return False
    x0, y0, x1, y1 = ob.bounds
    rec = DecomposingRecordingPen(gk_gs); gk_gs[src].draw(rec)
    db = BoundsPen(gk_gs); rec.replay(db)
    dx0, dy0, dx1, dy1 = db.bounds
    sy = (y1 - y0) / (dy1 - dy0)
    sx = min(sy, STROKE_CAP)
    single = (dx1 - dx0) * sx
    step = single * 0.72
    cx0  = (x0 + x1)/2 - (single + (n-1)*step)/2 + single/2
    ty   = (y0 + y1)/2 - sy*(dy0 + dy1)/2
    def df(pen):
        for i in range(n):
            tx = cx0 + i*step - sx*(dx0 + dx1)/2
            rec.replay(TransformPen(Qu2CuPen(pen, max_err=0.6, reverse_direction=True),
                                    (sx, 0, 0, sy, tx, ty)))
        if contour:                                  # small ring on the integral stem
            _emit(pen, _ring(cx0, (y0 + y1)/2, 0.17*(y1 - y0), w*0.85))
    return emit_pathops(gname, df)

RADICAL = (0x221A, [])   # handled by draw_comic_radical below

sym_done = 0
for cp in SIMPLE:
    g = fira_cmap.get(cp)
    if g and graft_symbol(g, cp):                                 # small ops: uniform
        sym_done += 1
# ∂ (partial) comes in a hair lighter than the letters -> nudge to common weight
_gpar = fira_cmap.get(0x2202)
if _gpar:
    reweight_glyph(_gpar, 7)
for cp, names in BIG.items():
    for g in names:
        if graft_symbol(g, cp, stroke_cap=True, size_cap=SIZE_CAP):  # thin + sized
            sym_done += 1
rad_done = sum(draw_comic_radical(g, RAD_W) for g in COMIC_RADICAL)   # procedural comic √
sym_done += rad_done

# double/triple/contour integrals synthesised from comic ∫ (Comic Relief lacks them)
MULTI = {"uni222C": 2, "uni222C.display": 2,        # ∬
         "uni222D": 3, "uni222D.display": 3,        # ∭
         "uni222E": (1, True), "uni222E.display": (1, True)}  # ∮ (with ring)
for g, spec in MULTI.items():
    n, ring = (spec, False) if isinstance(spec, int) else spec
    if graft_multi_integral(g, n, contour=ring, w=RAD_W):
        sym_done += 1

# delimiters: ( ) [ ] { } | from Comic Relief — base + discrete size variants,
# stretched at constant stroke. Extensible assembly (very tall) stays Fira.
mvar = fira["MATH"].table.MathVariants
_vv = dict(zip(mvar.VertGlyphCoverage.glyphs, mvar.VertGlyphConstruction)) \
    if mvar.VertGlyphCoverage else {}
def vert_variants(gname):
    con = _vv.get(gname)
    return [r.VariantGlyph for r in con.MathGlyphVariantRecord] if con else [gname]

def graft_bracket(cp):
    """Grow the donor bracket across its whole size family at a CONSTANT x-scale
    (taken from the base = natural Comic Sans proportions). Base looks like the
    real donor bracket; tall variants only stretch vertically -> stroke weight
    stays identical at every size (no thickening on multi-line)."""
    g0 = fira_cmap.get(cp)
    if g0 is None:
        return 0
    src = gk_cmap.get(cp)
    if src is None:
        return 0
    rec = DecomposingRecordingPen(gk_gs); gk_gs[src].draw(rec)
    db = BoundsPen(gk_gs); rec.replay(db)
    if not db.bounds:
        return 0
    dxmin, dymin, dxmax, dymax = db.bounds
    dh = dymax - dymin
    if dh <= 0:
        return 0
    variants = vert_variants(g0)
    ob0 = BoundsPen(fira_gs); fira_gs[variants[0]].draw(ob0)
    if not ob0.bounds:
        return 0
    sx = (ob0.bounds[3] - ob0.bounds[1]) / dh        # base natural (uniform) x-scale, held
    n = 0
    for vg in variants:
        ob = BoundsPen(fira_gs); fira_gs[vg].draw(ob)
        if not ob.bounds:
            continue
        oxmin, oymin, oxmax, oymax = ob.bounds
        sy = (oymax - oymin) / dh                     # stretch to this size's height
        tx = (oxmin + oxmax)/2 - sx*(dxmin + dxmax)/2
        ty = (oymin + oymax)/2 - sy*(dymin + dymax)/2
        t2 = T2CharStringPen(hmtx[vg][0], gk_gs)
        rec.replay(TransformPen(Qu2CuPen(t2, max_err=0.6, reverse_direction=True),
                                (sx, 0, 0, sy, tx, ty)))
        charstrs[vg] = t2.getCharString(private=private)
        n += 1
    return n

for cp in [0x7C]:                                    # | straight bar: vertical stretch is fine
    sym_done += graft_bracket(cp)
for cp in [0x28, 0x29, 0x5B, 0x5D, 0x7B, 0x7D]:      # base = natural donor; tall variants
    g0 = fira_cmap.get(cp)                           # drawn procedurally below (no distortion)
    if g0 and graft_symbol(g0, cp):
        sym_done += 1
_brk_w = {}                                          # natural base widths for the variants
for cp in [0x28, 0x29, 0x5B, 0x5D, 0x7B, 0x7D]:
    g0 = fira_cmap.get(cp)
    if g0 and g0 in charstrs:
        bp = BoundsPen(None); charstrs[g0].draw(bp)
        if bp.bounds:
            _brk_w[cp] = bp.bounds[2] - bp.bounds[0]

# ============================================================================
# synthesised symbols (Comic Relief lacks them) — drawn in the target glyph's
# box, unioned via pathops. Stroke held at a comic weight.
# ============================================================================
SW = 86   # synthesised-symbol stroke weight

def box_of(gname):
    ob = BoundsPen(fira_gs); fira_gs[gname].draw(ob)
    return ob.bounds

def _poly(pts, sw, caps=True):
    cs = [_seg(*pts[i], *pts[i+1], sw) for i in range(len(pts)-1) if pts[i] != pts[i+1]]
    idx = range(len(pts)) if caps else range(1, len(pts)-1)
    cs += [_disc(*pts[i], sw/2) for i in idx]
    return cs

def synth(gname, contours):
    if gname not in charstrs or not box_of(gname):
        return False
    return emit_pathops(gname, lambda pen: _emit(pen, contours))

def flip_glyph(target, src_name, vflip=False, hflip=False):
    if target not in charstrs or src_name not in charstrs:
        return False
    rec = RecordingPen(); charstrs[src_name].draw(rec)
    sb = BoundsPen({}); rec.replay(sb)
    tb = box_of(target)
    if not sb.bounds or not tb:
        return False
    sx0, sy0, sx1, sy1 = sb.bounds
    tx0, ty0, tx1, ty1 = tb
    s = (ty1 - ty0) / (sy1 - sy0)
    ax = -s if hflip else s
    ay = -s if vflip else s
    dx = (tx0 + tx1)/2 - ax*(sx0 + sx1)/2
    dy = (ty0 + ty1)/2 - ay*(sy0 + sy1)/2
    return emit_pathops(target, lambda pen:
                        rec.replay(TransformPen(pen, (ax, 0, 0, ay, dx, dy))))

def cmap_g(cp):
    return fira_cmap.get(cp)

extra = 0

# --- group 2: flips/mirrors of existing comic glyphs -------------------------
flips = [(0x2207, 0x394, True, False),   # ∇ = Δ flipped vertically
         (0x2200, 0x41,  True, False),   # ∀ = A flipped vertically
         (0x2203, 0x45,  False, True)]   # ∃ = E mirrored horizontally
for tcp, scp, vf, hf in flips:
    tg, sg = cmap_g(tcp), cmap_g(scp)
    if tg and sg and flip_glyph(tg, sg, vflip=vf, hflip=hf):
        extra += 1
for tg, sg in [("uni2210", "uni220F"), ("uni2210.display", "uni220F.display")]:  # ∐ = ∏ flipped
    if sg in charstrs and flip_glyph(tg, sg, vflip=True):
        extra += 1

# --- group 3: circled operators ---------------------------------------------
def circled(gname, inner):
    b = box_of(gname)
    if not b:
        return False
    x0, y0, x1, y1 = b
    cx, cy = (x0+x1)/2, (y0+y1)/2
    R = min(x1-x0, y1-y0)/2 - SW*0.55
    th = SW*0.82
    cs = _ring(cx, cy, R, th)
    cs += inner(cx, cy, R)
    return synth(gname, cs)

def _plus(cx, cy, R):  r = R*0.62; return _poly([(cx-r,cy),(cx+r,cy)],SW)+_poly([(cx,cy-r),(cx,cy+r)],SW)
def _times(cx, cy, R): r = R*0.52; return _poly([(cx-r,cy-r),(cx+r,cy+r)],SW)+_poly([(cx-r,cy+r),(cx+r,cy-r)],SW)
def _dotc(cx, cy, R):  return [_disc(cx,cy,SW*0.7)]
def _minus(cx, cy, R): r = R*0.62; return _poly([(cx-r,cy),(cx+r,cy)],SW)
def _slash(cx, cy, R): r = R*0.95; return _poly([(cx-r,cy-r),(cx+r,cy+r)],SW)

for cp, inner in [(0x2295,_plus),(0x2297,_times),(0x2299,_dotc),(0x2296,_minus),
                  (0x2298,_slash),(0x2205,_slash)]:   # ⊕ ⊗ ⊙ ⊖ ⊘ ∅
    g = cmap_g(cp)
    if g and circled(g, inner):
        extra += 1

# --- group 4a: arrows -------------------------------------------------------
def arrow_h(b, head_l, head_r, double=False, barl=False):
    x0, y0, x1, y1 = b
    cy = (y0+y1)/2
    x0 += SW/2; x1 -= SW/2
    if double:
        g  = SW*0.95                                       # line offset
        hl = min((x1-x0)*0.42, (y1-y0)*0.66); sp = g + SW*1.05  # head taller than the gap
    else:
        g  = 0.0
        hl = min((x1-x0)*0.34, (y1-y0)*0.42); sp = hl*0.62
    xr = (x1-hl*0.9) if head_r else x1                     # shafts stop at the head base
    xl = (x0+hl*0.9) if head_l else x0
    cs = []
    if double:
        cs += _poly([(xl,cy+g),(xr,cy+g)],SW) + _poly([(xl,cy-g),(xr,cy-g)],SW)
    else:
        cs += _poly([(xl,cy),(xr,cy)],SW)
    if head_r: cs += _poly([(x1-hl,cy+sp),(x1,cy),(x1-hl,cy-sp)],SW)
    if head_l: cs += _poly([(x0+hl,cy+sp),(x0,cy),(x0+hl,cy-sp)],SW)
    if barl:   cs += _poly([(x0,cy-(y1-y0)*0.28),(x0,cy+(y1-y0)*0.28)],SW)
    return cs

def arrow_v(b, head_u, head_d):
    x0, y0, x1, y1 = b
    cx = (x0+x1)/2
    y0 += SW/2; y1 -= SW/2
    hl = min((y1-y0)*0.34, (x1-x0)*0.7); sp = hl*0.62
    cs = _poly([(cx,y0),(cx,y1)],SW)
    if head_u: cs += _poly([(cx-sp,y1-hl),(cx,y1),(cx+sp,y1-hl)],SW)
    if head_d: cs += _poly([(cx-sp,y0+hl),(cx,y0),(cx+sp,y0+hl)],SW)
    return cs

arrows = [(0x2192,arrow_h,dict(head_l=False,head_r=True)),
          (0x2190,arrow_h,dict(head_l=True,head_r=False)),
          (0x2194,arrow_h,dict(head_l=True,head_r=True)),
          (0x21D2,arrow_h,dict(head_l=False,head_r=True,double=True)),
          (0x21D0,arrow_h,dict(head_l=True,head_r=False,double=True)),
          (0x21D4,arrow_h,dict(head_l=True,head_r=True,double=True)),
          (0x21A6,arrow_h,dict(head_l=False,head_r=True,barl=True)),
          (0x27F6,arrow_h,dict(head_l=False,head_r=True)),
          (0x2191,arrow_v,dict(head_u=True,head_d=False)),
          (0x2193,arrow_v,dict(head_u=False,head_d=True)),
          (0x2195,arrow_v,dict(head_u=True,head_d=True))]
for cp, fn, kw in arrows:
    g = cmap_g(cp); b = box_of(g) if g else None
    if b and synth(g, fn(b, **kw)):
        extra += 1

# --- group 4b: set/logic shapes ---------------------------------------------
def _wave(x0, x1, y, amp, n=24):
    return [(x0 + (x1-x0)*i/n, y + amp*math.sin(2*math.pi*i/n)) for i in range(n+1)]

def shape(gname, fn):
    b = box_of(gname)
    return synth(gname, fn(b)) if b else False

def s_cup(b):
    x0,y0,x1,y1=b; r=SW/2; xl,xr=x0+r,x1-r; cxm=(xl+xr)/2; h=y1-y0
    return _poly(_catmull([(xl,y1),(xl,y0+0.28*h),(cxm,y0+r),(xr,y0+0.28*h),(xr,y1)],8),SW)
def s_cap(b):
    x0,y0,x1,y1=b; r=SW/2; xl,xr=x0+r,x1-r; cxm=(xl+xr)/2; h=y1-y0
    return _poly(_catmull([(xl,y0),(xl,y1-0.28*h),(cxm,y1-r),(xr,y1-0.28*h),(xr,y0)],8),SW)
def s_vee(b):  x0,y0,x1,y1=b; r=SW/2; return _poly([(x0+r,y1),((x0+x1)/2,y0+r),(x1-r,y1)],SW)
def s_wedge(b):x0,y0,x1,y1=b; r=SW/2; return _poly([(x0+r,y0),((x0+x1)/2,y1-r),(x1-r,y0)],SW)
def s_subset(b, eq=False):
    x0,y0,x1,y1=b; r=SW/2; w=x1-x0
    yb=y0+r+(SW*1.7 if eq else 0); yt=y1-r; cy=(yb+yt)/2
    cs=_poly(_catmull([(x1-r,yt),(x0+w*0.32,yt),(x0+r,cy),(x0+w*0.32,yb),(x1-r,yb)],8),SW)
    if eq: cs+=_poly([(x0+r,y0+r),(x1-r,y0+r)],SW)
    return cs
def s_supset(b, eq=False):
    x0,y0,x1,y1=b; r=SW/2; w=x1-x0
    yb=y0+r+(SW*1.7 if eq else 0); yt=y1-r; cy=(yb+yt)/2
    cs=_poly(_catmull([(x0+r,yt),(x1-w*0.32,yt),(x1-r,cy),(x1-w*0.32,yb),(x0+r,yb)],8),SW)
    if eq: cs+=_poly([(x0+r,y0+r),(x1-r,y0+r)],SW)
    return cs

setshapes = [(0x222A,s_cup),(0x2229,s_cap),(0x2228,s_vee),(0x2227,s_wedge),
             (0x2282,lambda b:s_subset(b)),(0x2283,lambda b:s_supset(b)),
             (0x2286,lambda b:s_subset(b,eq=True)),(0x2287,lambda b:s_supset(b,eq=True))]
for cp, fn in setshapes:
    g = cmap_g(cp)
    if g and shape(g, fn):
        extra += 1

# --- group 4c: tilde/equiv relations ----------------------------------------
def r_sim(b):   x0,y0,x1,y1=b; cy=(y0+y1)/2; return _poly(_wave(x0+SW/2,x1-SW/2,cy,(y1-y0)*0.16),SW)
def r_equiv(b): x0,y0,x1,y1=b; r=SW/2; g=(y1-y0-SW)/2; cy=(y0+y1)/2; \
    return sum((_poly([(x0+r,cy+dy),(x1-r,cy+dy)],SW) for dy in (-g,0,g)),[])
def r_cong(b):  x0,y0,x1,y1=b; r=SW/2; \
    return _poly(_wave(x0+r,x1-r,y0+(y1-y0)*0.68,(y1-y0)*0.12),SW)+_poly([(x0+r,y0+(y1-y0)*0.28),(x1-r,y0+(y1-y0)*0.28)],SW)
def r_simeq(b): return r_cong(b)
def r_propto(b):x0,y0,x1,y1=b; r=SW/2; cy=(y0+y1)/2; \
    return _poly([(x0+r,cy),(x0+(x1-x0)*0.45,y1-r),(x0+(x1-x0)*0.45,y0+r),(x0+r,cy)],SW)+_poly([(x0+(x1-x0)*0.45,cy),(x1-r,cy)],SW)

for cp, fn in [(0x223C,r_sim),(0x2261,r_equiv),(0x2245,r_cong),(0x2243,r_simeq)]:
    g = cmap_g(cp)
    if g and shape(g, fn):
        extra += 1

# --- group 4c': Russian-style <= >=, longer =, rounded prime ----------------
def r_le(b):            # ⩽ : chevron + slanted bar parallel to its lower arm
    x0,y0,x1,y1=b; xl,xr=x0+SW/2,x1-SW/2; H=y1-y0; vy=y0+H*0.60
    cs  = _poly([(xr,y1-SW/2),(xl,vy)],SW)          # upper arm -> vertex (left)
    cs += _poly([(xl,vy),(xr,vy-H*0.26)],SW)        # lower arm (down to right)
    d   = H*0.34
    cs += _poly([(xl,vy-d),(xr,vy-H*0.26-d)],SW)    # bar parallel to lower arm
    return cs
def r_ge(b):            # ⩾ : mirror of ⩽ (vertex on the right)
    x0,y0,x1,y1=b; xl,xr=x0+SW/2,x1-SW/2; H=y1-y0; vy=y0+H*0.60
    cs  = _poly([(xl,y1-SW/2),(xr,vy)],SW)
    cs += _poly([(xr,vy),(xl,vy-H*0.26)],SW)
    d   = H*0.34
    cs += _poly([(xr,vy-d),(xl,vy-H*0.26-d)],SW)
    return cs
_eqb = box_of(cmap_g(0x3D))
EQ_GAP = (_eqb[3]-_eqb[1]) * 0.30 if _eqb else 130    # absolute bar gap, shared by = and !=
def r_equal(b):         # longer + slightly bolder than the donor "="
    x0,y0,x1,y1=b; W=x1-x0; cy=(y0+y1)/2; g=EQ_GAP    # fixed gap -> = and != match
    xl=x0-W*0.05; xr=x1+W*0.05                       # extend a touch past the box
    return _poly([(xl,cy+g),(xr,cy+g)],SW)+_poly([(xl,cy-g),(xr,cy-g)],SW)
def r_neq(b):           # not-equal: the (new, long) "=" with a slash through it
    x0,y0,x1,y1=b; cx=(x0+x1)/2; cy=(y0+y1)/2; H=y1-y0
    return r_equal(b) + _poly([(cx-H*0.20, cy-H*0.52),(cx+H*0.20, cy+H*0.52)], SW)
for cp, fn in [(0x2264,r_le),(0x2265,r_ge),(0x003D,r_equal),(0x2260,r_neq)]:
    g = cmap_g(cp)
    if g and shape(g, fn):
        extra += 1

# prime ' '' ''' as raised COMMA shapes — copy the right-single-quote U+2019
# (it already renders as a clean raised comma) enlarged, n times across the box.
_quote_g = fira_cmap.get(0x2019)
def stamp_prime(gname, n, scale=1.35):
    if gname not in charstrs or _quote_g is None or _quote_g not in charstrs:
        return False
    rec = RecordingPen(); charstrs[_quote_g].draw(rec)
    qb = BoundsPen(None); charstrs[_quote_g].draw(qb)
    pb = box_of(gname)
    if not qb.bounds or not pb:
        return False
    qx0,qy0,qx1,qy1 = qb.bounds
    qcx,qcy = (qx0+qx1)/2, (qy0+qy1)/2
    qw = (qx1-qx0)*scale; step = qw*1.15
    cx = (pb[0]+pb[2])/2
    startx = cx - (qw + (n-1)*step)/2 + qw/2          # centre of first copy
    def df(pen):
        for k in range(n):
            tcx = startx + k*step
            rec.replay(TransformPen(pen, (scale, 0, 0, scale,
                                          tcx - scale*qcx, qcy*(1-scale))))
    return emit_pathops(gname, df)
#   incl. plain apostrophe U+0027 and modifier prime U+02B9 — in math these are
#   used as derivative marks too, so they must match the comma prime.
for cp, n in [(0x2032,1),(0x2033,2),(0x2034,3),(0x0027,1),(0x02B9,1)]:
    g = cmap_g(cp)
    if g and stamp_prime(g, n):
        extra += 1

# --- group 4d: dots / cdot / circ / ast -------------------------------------
def d_cdot(b):  x0,y0,x1,y1=b; return [_disc((x0+x1)/2,(y0+y1)/2,SW*0.85)]
def d_cdots(b): x0,y0,x1,y1=b; cy=(y0+y1)/2; xs=[x0+(x1-x0)*t for t in (0.2,0.5,0.8)]; return [_disc(x,cy,SW*0.55) for x in xs]
def d_vdots(b): x0,y0,x1,y1=b; cx=(x0+x1)/2; ys=[y0+(y1-y0)*t for t in (0.2,0.5,0.8)]; return [_disc(cx,y,SW*0.55) for y in ys]
def d_ddots(b): x0,y0,x1,y1=b; ts=(0.2,0.5,0.8); return [_disc(x0+(x1-x0)*t,y0+(y1-y0)*(1-t),SW*0.55) for t in ts]
def d_circ(b):  x0,y0,x1,y1=b; return _ring((x0+x1)/2,(y0+y1)/2, min(x1-x0,y1-y0)/2-SW*0.12, SW*0.72, n=28)
def d_ast(b):
    x0,y0,x1,y1=b; cx,cy=(x0+x1)/2,(y0+y1)/2; r=min(x1-x0,y1-y0)*0.42; cs=[]
    for k in range(3):
        a=math.pi/2+k*math.pi/3
        cs+=_poly([(cx-r*math.cos(a),cy-r*math.sin(a)),(cx+r*math.cos(a),cy+r*math.sin(a))],SW*0.8)
    return cs

for cp, fn in [(0x22C5,d_cdot),(0x22EF,d_cdots),(0x22EE,d_vdots),(0x22F1,d_ddots),
               (0x2218,d_circ),(0x2217,d_ast)]:
    g = cmap_g(cp)
    if g and shape(g, fn):
        extra += 1

# --- group 4e: stretchy delimiters (base + size variants) -------------------
def d_lfloor(b): x0,y0,x1,y1=b; r=SW/2; return _poly([(x0+r,y1),(x0+r,y0+r),(x1-r,y0+r)],SW)
def d_rfloor(b): x0,y0,x1,y1=b; r=SW/2; return _poly([(x1-r,y1),(x1-r,y0+r),(x0+r,y0+r)],SW)
def d_lceil(b):  x0,y0,x1,y1=b; r=SW/2; return _poly([(x0+r,y0),(x0+r,y1-r),(x1-r,y1-r)],SW)
def d_rceil(b):  x0,y0,x1,y1=b; r=SW/2; return _poly([(x1-r,y0),(x1-r,y1-r),(x0+r,y1-r)],SW)
def d_langle(b): x0,y0,x1,y1=b; r=SW/2; return _poly([(x1-r,y1-r),(x0+r,(y0+y1)/2),(x1-r,y0+r)],SW)
def d_rangle(b): x0,y0,x1,y1=b; r=SW/2; return _poly([(x0+r,y1-r),(x1-r,(y0+y1)/2),(x0+r,y0+r)],SW)
def d_vert2(b):  x0,y0,x1,y1=b; cx=(x0+x1)/2; g=SW*0.9; return _poly([(cx-g,y0),(cx-g,y1)],SW)+_poly([(cx+g,y0),(cx+g,y1)],SW)

for cp, fn in [(0x230A,d_lfloor),(0x230B,d_rfloor),(0x2308,d_lceil),(0x2309,d_rceil),
               (0x27E8,d_langle),(0x27E9,d_rangle),(0x2016,d_vert2)]:
    g0 = cmap_g(cp)
    if not g0:
        continue
    for g in vert_variants(g0):
        b = box_of(g)
        if b and synth(g, fn(b)):
            extra += 1

# Tall ( ) [ ] { } variants drawn PROCEDURALLY so the curved/cornered ends stay a
# CONSTANT size & width (only the straight middle lengthens) — avoids the
# donor-stretch deformation on tall cases()/matrices. Base size stays natural donor.
BR_W = 92
def _vbrace(b, left, W):
    x0,y0,x1,y1=b; cx=(x0+x1)/2; ymid=(y0+y1)/2
    s = 1 if left else -1                                # left brace: nib points -x
    spine = cx + s*W*0.10; nibw = W*0.46; t = W*0.20
    curl  = min(W*0.95, (y1-y0)*0.30)                   # end curl (fixed)
    run   = min(W*0.70, (y1-y0)*0.22)                   # vertical reach around the nib
    pts = [(spine + s*t, y1), (spine, y1-curl), (spine, ymid+run),
           (spine - s*nibw, ymid),                      # nib tip
           (spine, ymid-run), (spine, y0+curl), (spine + s*t, y0)]
    return _poly(_catmull(pts, 10), BR_W)
def _vparen(b, left, W):
    x0,y0,x1,y1=b; cx=(x0+x1)/2
    s = 1 if left else -1
    bx = cx - s*W*0.30                                  # bulge (leftmost for "(")
    tx = cx + s*W*0.26                                  # terminals curve toward content
    hook = min(W*1.4, (y1-y0)*0.45)                     # end-curve reach (fixed)
    pts = [(tx, y1-BR_W/2), (bx, y1-hook), (bx, y0+hook), (tx, y0+BR_W/2)]
    return _poly(_catmull(pts, 16), BR_W)               # straight middle + curved ends
def _vbracket(b, left, W):
    x0,y0,x1,y1=b; cx=(x0+x1)/2
    s = 1 if left else -1
    spine = cx - s*W*0.28; arm = cx + s*W*0.28
    pts = [(arm, y1-BR_W/2), (spine, y1-BR_W/2), (spine, y0+BR_W/2), (arm, y0+BR_W/2)]
    return _poly(pts, BR_W)                             # square corners (rounded caps)
_proc_delim = {0x28:(_vparen,True), 0x29:(_vparen,False),
               0x5B:(_vbracket,True), 0x5D:(_vbracket,False),
               0x7B:(_vbrace,True), 0x7D:(_vbrace,False)}
for cp,(fn,left) in _proc_delim.items():
    g0 = cmap_g(cp)
    if not g0:
        continue
    W = _brk_w.get(cp, 300)
    for g in vert_variants(g0)[1:]:                  # base stays natural donor (above)
        b = box_of(g)
        if b and synth(g, fn(b, left, W)):
            extra += 1

# --- diagonal arrows, multi-prime, dotless i/j ------------------------------
def arrow_diag(b, dx, dy):
    x0,y0,x1,y1=b; r=SW/2
    tail=(x0+r if dx>0 else x1-r, y0+r if dy>0 else y1-r)
    tip =(x1-r if dx>0 else x0+r, y1-r if dy>0 else y0+r)
    cs=_poly([tail,tip],SW)
    ang=math.atan2(tip[1]-tail[1], tip[0]-tail[0]); hl=min(x1-x0,y1-y0)*0.36
    for da in (math.radians(148), math.radians(-148)):
        a=ang+da
        cs+=_poly([tip,(tip[0]+hl*math.cos(a), tip[1]+hl*math.sin(a))],SW)
    return cs
for cp, d in [(0x2197,(1,1)),(0x2198,(1,-1)),(0x2196,(-1,1)),(0x2199,(-1,-1))]:
    g=cmap_g(cp); b=box_of(g) if g else None
    if b and synth(g, arrow_diag(b,*d)):
        extra += 1
for cp in (0x0131, 0x0237):                              # dotless i, j from Comic Relief
    g=cmap_g(cp)
    if g and graft_symbol(g, cp):
        extra += 1

# --- horizontal stretchy over/under braces, brackets, parens ----------------
_hv = dict(zip(mvar.HorizGlyphCoverage.glyphs, mvar.HorizGlyphConstruction)) \
    if mvar.HorizGlyphCoverage else {}
def horiz_variants(gname):
    con = _hv.get(gname)
    return [r.VariantGlyph for r in con.MathGlyphVariantRecord] if con else [gname]
BW = 74
def _hbrace(b, nib_up):
    x0,y0,x1,y1=b; W=x1-x0; cx=(x0+x1)/2; r=BW/2
    yt, yn = (y0+r, y1-r) if nib_up else (y1-r, y0+r)        # tips line / nib
    pts=[(x0+r,yt),(x0+W*0.22,yt),(cx-W*0.10,(yt+yn)/2),(cx,yn),
         (cx+W*0.10,(yt+yn)/2),(x1-W*0.22,yt),(x1-r,yt)]
    return _poly(_catmull(pts,8),BW)
def hb_overbrace(b):    return _hbrace(b, True)
def hb_underbrace(b):   return _hbrace(b, False)
def hb_overbracket(b):  x0,y0,x1,y1=b; r=BW/2; return _poly([(x0+r,y0),(x0+r,y1-r),(x1-r,y1-r),(x1-r,y0)],BW)
def hb_underbracket(b): x0,y0,x1,y1=b; r=BW/2; return _poly([(x0+r,y1),(x0+r,y0+r),(x1-r,y0+r),(x1-r,y1)],BW)
def hb_overparen(b):    x0,y0,x1,y1=b; r=BW/2; cx=(x0+x1)/2; return _poly(_catmull([(x0+r,y0+r),(cx,y1-r),(x1-r,y0+r)],10),BW)
def hb_underparen(b):   x0,y0,x1,y1=b; r=BW/2; cx=(x0+x1)/2; return _poly(_catmull([(x0+r,y1-r),(cx,y0+r),(x1-r,y1-r)],10),BW)

for cp, fn in [(0x23DE,hb_overbrace),(0x23DF,hb_underbrace),(0x23B4,hb_overbracket),
               (0x23B5,hb_underbracket),(0x23DC,hb_overparen),(0x23DD,hb_underparen)]:
    g0 = cmap_g(cp)
    if not g0:
        continue
    for g in horiz_variants(g0):
        b = box_of(g)
        if b and synth(g, fn(b)):
            extra += 1

# --- math accents (hat/tilde/bar/vec/dot/ddot/check/breve/acute/grave/ring) --
AW = 74
def ac_hat(b):   x0,y0,x1,y1=b; r=AW/2; return _poly([(x0+r,y0+r),((x0+x1)/2,y1-r),(x1-r,y0+r)],AW)
def ac_check(b): x0,y0,x1,y1=b; r=AW/2; return _poly([(x0+r,y1-r),((x0+x1)/2,y0+r),(x1-r,y1-r)],AW)
def ac_bar(b):   x0,y0,x1,y1=b; r=AW/2; cy=(y0+y1)/2; bow=min((x1-x0)*0.05, AW*1.6); return _poly(_catmull([(x0+r,cy-bow*0.35),((x0+x1)/2,cy+bow),(x1-r,cy-bow*0.35)],12),AW)
def ac_tilde(b): x0,y0,x1,y1=b; r=AW/2; cy=(y0+y1)/2; return _poly(_wave(x0+r,x1-r,cy,(y1-y0)*0.30),AW)
def ac_dot(b):   x0,y0,x1,y1=b; return [_disc((x0+x1)/2,(y0+y1)/2,AW*0.62)]
def ac_ddot(b):  x0,y0,x1,y1=b; cy=(y0+y1)/2; g=(x1-x0)*0.26; cx=(x0+x1)/2; return [_disc(cx-g,cy,AW*0.55),_disc(cx+g,cy,AW*0.55)]
def ac_breve(b): x0,y0,x1,y1=b; r=AW/2; cx=(x0+x1)/2; return _poly(_catmull([(x0+r,y1-r),(cx,y0+r),(x1-r,y1-r)],8),AW)
def ac_ring(b):  x0,y0,x1,y1=b; cx,cy=(x0+x1)/2,(y0+y1)/2; return _ring(cx,cy,min(x1-x0,y1-y0)/2-AW*0.4,AW*0.62,n=22)
def ac_acute(b): x0,y0,x1,y1=b; r=AW/2; return _poly([(x0+r,y0+r),(x1-r,y1-r)],AW)
def ac_grave(b): x0,y0,x1,y1=b; r=AW/2; return _poly([(x0+r,y1-r),(x1-r,y0+r)],AW)
def ac_vec(b):
    x0,y0,x1,y1=b; r=AW/2; cy=(y0+y1)/2; hl=(x1-x0)*0.42; sp=hl*0.6
    return _poly([(x0+r,cy),(x1-r,cy)],AW)+_poly([(x1-r-hl,cy+sp),(x1-r,cy),(x1-r-hl,cy-sp)],AW)

for cp, fn in [(0x0302,ac_hat),(0x030C,ac_check),(0x0304,ac_bar),(0x0305,ac_bar),
               (0x0303,ac_tilde),(0x0307,ac_dot),(0x0308,ac_ddot),(0x0306,ac_breve),
               (0x030A,ac_ring),(0x0301,ac_acute),(0x0300,ac_grave),(0x20D7,ac_vec)]:
    g = cmap_g(cp)
    if g and shape(g, fn):
        extra += 1

# (blackboard moved below — auto-outline via pathops.stroke, after add_glyph)

# --- calligraphic alphabet (new glyphs from Pacifico, casual script) ---------
_orig_order = list(fira.getGlyphOrder())
_new_names = []
def add_glyph(name, ch, width):
    charstrs.charStrings[name] = len(charstrs.charStringsIndex)
    charstrs.charStringsIndex.append(ch)
    top.charset.append(name)
    hmtx.metrics[name] = (int(round(width)), 0)
    _new_names.append(name)
def add_cmap(cp, name):
    for t in fira["cmap"].tables:
        if cp <= 0xFFFF or t.format >= 12:
            t.cmap[cp] = name

SCRIPT_UP = {'A':0x1D49C,'B':0x212C,'C':0x1D49E,'D':0x1D49F,'E':0x2130,'F':0x2131,
             'G':0x1D4A2,'H':0x210B,'I':0x2110,'J':0x1D4A5,'K':0x1D4A6,'L':0x2112,
             'M':0x2133,'N':0x1D4A9,'O':0x1D4AA,'P':0x1D4AB,'Q':0x1D4AC,'R':0x211B,
             'S':0x1D4AE,'T':0x1D4AF,'U':0x1D4B0,'V':0x1D4B1,'W':0x1D4B2,'X':0x1D4B3,
             'Y':0x1D4B4,'Z':0x1D4B5}
SCRIPT_LOW = {'a':0x1D4B6,'b':0x1D4B7,'c':0x1D4B8,'d':0x1D4B9,'e':0x212F,'f':0x1D4BB,
              'g':0x210A,'h':0x1D4BD,'i':0x1D4BE,'j':0x1D4BF,'k':0x1D4C0,'l':0x1D4C1,
              'm':0x1D4C2,'n':0x1D4C3,'o':0x2134,'p':0x1D4C5,'q':0x1D4C6,'r':0x1D4C7,
              's':0x1D4C8,'t':0x1D4C9,'u':0x1D4CA,'v':0x1D4CB,'w':0x1D4CC,'x':0x1D4CD,
              'y':0x1D4CE,'z':0x1D4CF}
S_CAL = F_CAP / PAC_CAP                                  # uniform (keeps script proportions)
def add_cal(ch, cp):
    src = pac_cmap.get(ord(ch))
    if src is None:
        return False
    rec = DecomposingRecordingPen(pac_gs); pac_gs[src].draw(rec)
    adv = pac["hmtx"][src][0] * S_CAL
    t2 = T2CharStringPen(adv, None)
    rec.replay(TransformPen(Qu2CuPen(t2, max_err=0.6, reverse_direction=True),
                            (S_CAL, 0, 0, S_CAL, 0, 0)))
    name = "cm_cal_%04X" % cp
    add_glyph(name, t2.getCharString(private=private, globalSubrs=gsubrs), adv)
    add_cmap(cp, name)
    return True
for ch, cp in {**SCRIPT_UP, **SCRIPT_LOW}.items():
    if add_cal(ch, cp):
        extra += 1

# --- sans-serif: our comic letters ARE sans -> alias slots to existing glyphs -
def alias(cp, src_cp):
    nm = fira_cmap.get(src_cp)
    if nm:
        add_cmap(cp, nm)
for i in range(26):
    alias(0x1D5A0+i, 0x41+i); alias(0x1D5BA+i, 0x61+i)            # sans up/low
    alias(0x1D5D4+i, 0x1D400+i); alias(0x1D5EE+i, 0x1D41A+i)      # sans-bold up/low
    alias(0x1D608+i, 0x1D434+i)                                   # sans-italic up
    alias(0x1D622+i, 0x210E if i == 7 else 0x1D44E+i)             # sans-italic low (h->planck)
for i in range(10):
    alias(0x1D7E2+i, 0x30+i); alias(0x1D7EC+i, 0x1D7CE+i)         # sans / sans-bold digits
for i in range(26):
    alias(0x1D670+i, 0x41+i); alias(0x1D68A+i, 0x61+i)           # mono -> comic letters
for i in range(10):
    alias(0x1D7F6+i, 0x30+i)                                     # mono digits

# --- blackboard: keep Fira's real double-struck, override only where an SVG ---
# is provided in svg/bb/. (Auto-outline removed — user draws proper double-struck.)
BB_UP = {'A':0x1D538,'B':0x1D539,'C':0x2102,'D':0x1D53B,'E':0x1D53C,'F':0x1D53D,
         'G':0x1D53E,'H':0x210D,'I':0x1D540,'J':0x1D541,'K':0x1D542,'L':0x1D543,
         'M':0x1D544,'N':0x2115,'O':0x1D546,'P':0x2119,'Q':0x211A,'R':0x211D,
         'S':0x1D54A,'T':0x1D54B,'U':0x1D54C,'V':0x1D54D,'W':0x1D54E,'X':0x1D54F,
         'Y':0x1D550,'Z':0x2124}

# --- hand-drawn SVG override for blackboard (svg/bb/<NAME>.svg) --------------
# Convention: viewBox height 1000, BASELINE at y=800, cap line at y=111 (cap 689),
# descender to ~y=900. Any width; advance auto-fit with sidebearings. y flips.
SVG_BASELINE = 800
BB_EMBOLDEN = 10        # grow hand-drawn blackboard strokes outward (units), 0 = off
BB_SCALE = 1.06         # hand-drawn letters read a touch small vs caps -> scale up ~6%
def _style(el, key):
    v = el.get(key)
    if v:
        return v
    for part in (el.get('style') or '').split(';'):
        if ':' in part and part.split(':', 1)[0].strip() == key:
            return part.split(':', 1)[1].strip()
    return None

# Hand-drawn (Rnote) outlines carry ~1800 tessellation points per glyph; the
# shape is already a dense polygon, so Ramer–Douglas–Peucker decimation cuts
# that ~10x with no visible change. Applied to the final outline at emit time.
BB_DECIMATE_EPS = 2.0           # max deviation (em/1000); 0 = keep all points
def _rdp(pts, eps):
    """Decimate a closed contour polyline, keeping points that deviate > eps."""
    n = len(pts)
    if n < 4:
        return pts
    P = pts + [pts[0]]                                   # treat as closed
    # Seed a SECOND anchor (farthest point from start) so the initial segment
    # isn't the degenerate start==end chord that would collapse the contour.
    ax, ay = P[0]
    far = max(range(1, n), key=lambda i: (P[i][0]-ax)**2 + (P[i][1]-ay)**2)
    keep = [False] * len(P); keep[0] = keep[-1] = keep[far] = True
    stack = [(0, far), (far, len(P) - 1)]
    while stack:
        a, b = stack.pop()
        ax, ay = P[a]; bx, by = P[b]
        dx, dy = bx - ax, by - ay
        nrm = math.hypot(dx, dy) or 1.0
        dmax, idx = 0.0, -1
        for i in range(a + 1, b):
            px, py = P[i]
            d = abs((px - ax) * dy - (py - ay) * dx) / nrm
            if d > dmax:
                dmax, idx = d, i
        if dmax > eps and idx != -1:
            keep[idx] = True
            stack.append((a, idx)); stack.append((idx, b))
    R = [P[i] for i in range(len(P)) if keep[i]]
    if R[-1] == R[0]:
        R = R[:-1]
    return R

def _flatten(acc, steps=4):
    """Flatten a pathops outline to per-contour straight-line polylines."""
    rp = RecordingPen(); acc.draw(rp)
    contours = []; cur = None; start = None
    def quad(p0, c, p1):
        for k in range(1, steps + 1):
            t = k / steps; mt = 1 - t
            cur.append((mt*mt*p0[0] + 2*mt*t*c[0] + t*t*p1[0],
                        mt*mt*p0[1] + 2*mt*t*c[1] + t*t*p1[1]))
    for op, args in rp.value:
        if op == "moveTo":
            cur = [args[0]]; start = args[0]
        elif op == "lineTo":
            cur.append(args[0])
        elif op == "qCurveTo":                          # TrueType quad run (+implied on-curves)
            offs = list(args)
            last = offs[-1] if offs[-1] is not None else start
            offs = offs[:-1]
            p0 = cur[-1]
            for i, c in enumerate(offs):
                p1 = last if i == len(offs) - 1 else ((c[0]+offs[i+1][0])/2, (c[1]+offs[i+1][1])/2)
                quad(p0, c, p1); p0 = p1
        elif op == "curveTo":                           # cubic -> sample
            p0 = cur[-1]; c1, c2, p1 = args
            for k in range(1, steps + 1):
                t = k / steps; mt = 1 - t
                cur.append((mt**3*p0[0] + 3*mt*mt*t*c1[0] + 3*mt*t*t*c2[0] + t**3*p1[0],
                            mt**3*p0[1] + 3*mt*mt*t*c1[1] + 3*mt*t*t*c2[1] + t**3*p1[1]))
        elif op in ("closePath", "endPath"):
            if cur: contours.append(cur); cur = None
    if cur: contours.append(cur)
    return contours

def load_svg_glyph(svgpath, sb=40):
    """Accept both FILLED paths (Inkscape) and STROKED centreline paths (Rnote):
    a path with fill:none + stroke is stroked by its stroke-width; else filled."""
    root = ET.parse(svgpath).getroot()
    paths = root.findall('.//{http://www.w3.org/2000/svg}path') or root.findall('.//path')
    flip = (1, 0, 0, -1, 0, SVG_BASELINE)
    acc = pathops.Path()
    for el in paths:
        d = el.get('d')
        if not d:
            continue
        rec = RecordingPen(); parse_path(d, rec)
        sub = pathops.Path(); rec.replay(TransformPen(sub.getPen(), flip))
        fill, stroke, sw = _style(el, 'fill'), _style(el, 'stroke'), _style(el, 'stroke-width')
        if fill in ('none', 'transparent') and stroke and stroke != 'none':   # stroked centreline
            sub.stroke(float(sw) if sw else 28,
                       pathops.LineCap.ROUND_CAP, pathops.LineJoin.ROUND_JOIN, 4)
            sub.convertConicsToQuads(0.5)
        acc.addPath(sub)
    try:
        acc = pathops.simplify(acc, fix_winding=True)
    except pathops.PathOpsError:
        try:
            acc = pathops.simplify(acc)          # retry w/o fix_winding
        except pathops.PathOpsError:
            acc.fillType = pathops.FillType.WINDING   # raw union, nonzero fill
    acc.convertConicsToQuads(0.5)
    if BB_SCALE != 1.0 and acc.bounds:                # scale about the baseline (y=0)
        sc = pathops.Path(); acc.draw(TransformPen(sc.getPen(), (BB_SCALE, 0, 0, BB_SCALE, 0, 0)))
        acc = sc
    if BB_EMBOLDEN and acc.bounds:                    # thicken strokes outward
        rib = pathops.Path(); acc.draw(rib.getPen())
        rib.stroke(2*BB_EMBOLDEN, pathops.LineCap.ROUND_CAP,
                   pathops.LineJoin.ROUND_JOIN, 4)
        rib.convertConicsToQuads(0.5)
        try:
            bld = pathops.OpBuilder(fix_winding=True, keep_starting_points=False)
            bld.add(acc, pathops.PathOp.UNION); bld.add(rib, pathops.PathOp.UNION)
            acc = bld.resolve()
        except pathops.PathOpsError:
            acc.addPath(rib); acc.fillType = pathops.FillType.WINDING
    if not acc.bounds:
        return None
    xmin, _, xmax, _ = acc.bounds
    dx = sb - xmin; adv = int(round((xmax - xmin) + 2*sb))
    t2 = T2CharStringPen(adv, None)
    if BB_DECIMATE_EPS:                                  # prune tessellation points
        for c in _flatten(acc):
            c = _rdp(c, BB_DECIMATE_EPS)
            if len(c) < 3:
                continue
            t2.moveTo((c[0][0] + dx, c[0][1]))
            for x, y in c[1:]:
                t2.lineTo((x + dx, y))
            t2.closePath()
    else:
        acc.draw(TransformPen(Qu2CuPen(t2, max_err=0.6), (1, 0, 0, 1, dx, 0)))
    return t2.getCharString(private=private, globalSubrs=gsubrs), adv

_svg_map = dict(BB_UP)                                    # 'A'..'Z' -> bb codepoint
_svg_map.update({chr(0x61+i): 0x1D552+i for i in range(26)})   # lowercase 'a'..'z'
_svg_map.update({str(i): 0x1D7D8+i for i in range(10)})        # digits '0'..'9'
for fn, cp in _svg_map.items():
    pth = os.path.join("svg", "bb", fn + ".svg")
    if not os.path.exists(pth):
        continue
    out = load_svg_glyph(pth)
    if not out:
        continue
    cs, adv = out
    name = next((t.cmap[cp] for t in fira["cmap"].tables if cp in t.cmap), None)
    if name and name in charstrs:
        charstrs[name] = cs; hmtx.metrics[name] = (adv, 0)
    else:
        nm = "cm_bb_%04X" % cp; add_glyph(nm, cs, adv); add_cmap(cp, nm)
    print(f"  SVG override: {fn} -> U+{cp:04X}")

# --- fraktur (new glyphs from UnifrakturCook, blackletter donor) -------------
frk = TTFont("fonts/donor-UnifrakturCook-Bold.ttf")
frk_cmap = frk.getBestCmap(); frk_gs = frk.getGlyphSet()
_fnb = BoundsPen(frk_gs); frk_gs[frk_cmap[ord('N')]].draw(_fnb)
S_FRK = F_CAP / (_fnb.bounds[3] - _fnb.bounds[1])               # measured cap height
FRAK_UP = {'A':0x1D504,'B':0x1D505,'C':0x212D,'D':0x1D507,'E':0x1D508,'F':0x1D509,
           'G':0x1D50A,'H':0x210C,'I':0x2111,'J':0x1D50D,'K':0x1D50E,'L':0x1D50F,
           'M':0x1D510,'N':0x1D511,'O':0x1D512,'P':0x1D513,'Q':0x1D514,'R':0x211C,
           'S':0x1D516,'T':0x1D517,'U':0x1D518,'V':0x1D519,'W':0x1D51A,'X':0x1D51B,
           'Y':0x1D51C,'Z':0x2128}
FRAK_LOW = {chr(0x61+i): 0x1D51E+i for i in range(26)}
def add_frak(ch, cp):
    src = frk_cmap.get(ord(ch))
    if src is None:
        return False
    rec = DecomposingRecordingPen(frk_gs); frk_gs[src].draw(rec)
    adv = frk["hmtx"][src][0] * S_FRK
    t2 = T2CharStringPen(adv, None)
    rec.replay(TransformPen(Qu2CuPen(t2, max_err=0.6, reverse_direction=True),
                            (S_FRK, 0, 0, S_FRK, 0, 0)))
    name = "cm_frak_%04X" % cp
    add_glyph(name, t2.getCharString(private=private, globalSubrs=gsubrs), adv)
    add_cmap(cp, name)
    return True
for ch, cp in {**FRAK_UP, **FRAK_LOW}.items():
    if add_frak(ch, cp):
        extra += 1

fira.setGlyphOrder(_orig_order + _new_names)            # set order ONCE (all new glyphs)
fira["maxp"].numGlyphs = len(_orig_order) + len(_new_names)

print(f"synthesised {extra} extra TeX symbols (incl. blackboard + calligraphic)")

# harmonise engine-drawn rules with the (thinner) comic stroke weight
mc = fira["MATH"].table.MathConstants
for fld, val in [("FractionRuleThickness", 88), ("RadicalRuleThickness", RAD_W),
                 ("OverbarRuleThickness", 85), ("UnderbarRuleThickness", 85)]:
    rec = getattr(mc, fld)
    if rec is not None:
        rec.Value = val
# radical degree (root index n) spacing: don't let the small n stick to the sign
for fld, val in [("RadicalKernBeforeDegree", 220), ("RadicalKernAfterDegree", -200),
                 ("RadicalDegreeBottomRaisePercent", 64)]:
    rec = getattr(mc, fld, None)
    if rec is not None:
        if hasattr(rec, "Value"):
            rec.Value = val
        else:
            setattr(mc, fld, val)
print(f"grafted {sym_done} symbol glyphs from Comic Relief; tuned rule thicknesses")

# --- Universal pass: round sharp corners + lightly embolden every glyph we left
#     untouched (the raw-Fira long tail of rare symbols), so they stop looking
#     like a different font sitting in a comic document. Comic-native drawn /
#     grafted glyphs are skipped (their charstring identity changed). Geometry:
#     at each on-curve corner we trim both adjacent sides and bridge them with a
#     fillet cubic; smooth joins (small turn angle) are left alone.
ROUND_R    = 140.0     # target fillet radius (em/1000)
ROUND_ANG  = 30.0      # minimum corner turn angle (deg) to round
ROUND_FRAC = 0.5       # max fraction of a segment chord eaten from one end
ROUND_K    = 0.5       # fillet handle pull toward the original vertex
SYM_EMB    = 4         # light embolden (digits use 6 ≈ +15%)

def _rsub(a, b): return (a[0]-b[0], a[1]-b[1])
def _radd(a, b): return (a[0]+b[0], a[1]+b[1])
def _rmul(a, s): return (a[0]*s, a[1]*s)
def _rlen(a): return math.hypot(a[0], a[1])
def _runit(a):
    l = _rlen(a); return (a[0]/l, a[1]/l) if l else (0.0, 0.0)

def _rcub_sub(P, t0, t1):
    """control points of the cubic portion between params t0 and t1."""
    def right(P, t):
        p0, p1, p2, p3 = P
        a = _radd(p0, _rmul(_rsub(p1, p0), t)); b = _radd(p1, _rmul(_rsub(p2, p1), t))
        c = _radd(p2, _rmul(_rsub(p3, p2), t)); d = _radd(a, _rmul(_rsub(b, a), t))
        e = _radd(b, _rmul(_rsub(c, b), t));    f = _radd(d, _rmul(_rsub(e, d), t))
        return (f, e, c, p3)
    def left(P, t):
        p0, p1, p2, p3 = P
        a = _radd(p0, _rmul(_rsub(p1, p0), t)); b = _radd(p1, _rmul(_rsub(p2, p1), t))
        c = _radd(p2, _rmul(_rsub(p3, p2), t)); d = _radd(a, _rmul(_rsub(b, a), t))
        e = _radd(b, _rmul(_rsub(c, b), t));    f = _radd(d, _rmul(_rsub(e, d), t))
        return (p0, a, d, f)
    return left(right(P, t0), (t1-t0)/(1-t0) if t0 < 1 else 0.0)

def _rparse(rec):
    """RecordingPen value -> list of closed contours of segs.
    seg = ('L', p0, p1) or ('C', p0, c1, c2, p1)."""
    contours = []; cur = None; start = None; pt = None
    for op, args in rec.value:
        if op == "moveTo":
            if cur is not None: contours.append(cur)
            start = args[0]; pt = start; cur = []
        elif op == "lineTo":
            cur.append(('L', pt, args[0])); pt = args[0]
        elif op == "curveTo":
            c1, c2, p1 = args; cur.append(('C', pt, c1, c2, p1)); pt = p1
        elif op == "qCurveTo":
            cur.append(('L', pt, args[-1])); pt = args[-1]
        elif op in ("closePath", "endPath"):
            if cur:
                if _rlen(_rsub(pt, start)) > 1e-3: cur.append(('L', pt, start))
                contours.append(cur); cur = None
    if cur: contours.append(cur)
    return contours

def _rtan_in(seg):    # tangent arriving at the seg end node
    if seg[0] == 'L': return _rsub(seg[2], seg[1])
    d = _rsub(seg[-1], seg[-2]);  return d if _rlen(d) > 1e-6 else _rsub(seg[-1], seg[1])
def _rtan_out(seg):   # tangent leaving the seg start node
    if seg[0] == 'L': return _rsub(seg[2], seg[1])
    d = _rsub(seg[2], seg[1]);    return d if _rlen(d) > 1e-6 else _rsub(seg[4], seg[1])
def _rseglen(seg):
    return _rlen(_rsub(seg[2], seg[1])) if seg[0] == 'L' else _rlen(_rsub(seg[-1], seg[1]))

def _rround_contour(segs):
    m = len(segs)
    if m < 2: return None
    node = [s[1] for s in segs]
    trim = [0.0]*m; corner = [False]*m
    for i in range(m):
        din = _rtan_in(segs[(i-1) % m]); dout = _rtan_out(segs[i])
        if _rlen(din) < 1e-6 or _rlen(dout) < 1e-6: continue
        ui, uo = _runit(din), _runit(dout)
        dot = max(-1.0, min(1.0, ui[0]*uo[0]+ui[1]*uo[1]))
        if math.degrees(math.acos(dot)) >= ROUND_ANG:
            corner[i] = True
            trim[i] = min(ROUND_R, ROUND_FRAC*_rseglen(segs[(i-1) % m]),
                                   ROUND_FRAC*_rseglen(segs[i]))
    if not any(corner): return None
    for i in range(m):                                 # keep both trims inside the seg
        L = _rseglen(segs[i]); a = trim[i]; b = trim[(i+1) % m]
        if a+b > L and a+b > 0:
            sc = L/(a+b); trim[i] = a*sc; trim[(i+1) % m] = b*sc
    def trim_seg(seg, ta, tb):
        if seg[0] == 'L':
            p0, p1 = seg[1], seg[2]; u = _runit(_rsub(p1, p0))
            s = _radd(p0, _rmul(u, ta)); e = _rsub(p1, _rmul(u, tb))
            return s, ('l', e), e
        P = (seg[1], seg[2], seg[3], seg[4]); L = _rseglen(seg)
        t0 = max(0.0, min(0.49, (ta/L) if L else 0.0))
        t1 = max(t0+0.01, min(1.0, 1-(tb/L) if L else 1.0))
        q = _rcub_sub(P, t0, t1)
        return q[0], ('c', q[1], q[2], q[3]), q[3]
    starts = []; ends = []; mids = []
    for i in range(m):
        ta = trim[i] if corner[i] else 0.0
        tb = trim[(i+1) % m] if corner[(i+1) % m] else 0.0
        s, mid, e = trim_seg(segs[i], ta, tb)
        starts.append(s); ends.append(e); mids.append(mid)
    out = [('m', starts[0])]
    for i in range(m):
        out.append(mids[i])
        j = (i+1) % m
        if corner[j]:
            B = ends[i]; V = node[j]; A = starts[j]
            out.append(('c', _radd(B, _rmul(_rsub(V, B), ROUND_K)),
                             _radd(A, _rmul(_rsub(V, A), ROUND_K)), A))
    return out

def round_glyph(gname):
    if gname not in charstrs: return False
    rec = RecordingPen(); charstrs[gname].draw(rec)
    contours = _rparse(rec)
    if not contours: return False
    pen = T2CharStringPen(hmtx[gname][0], None); changed = False
    for segs in contours:
        ops = _rround_contour(segs)
        if ops is None:                                # no corners: replay raw
            first = True
            for seg in segs:
                if first: pen.moveTo(seg[1]); first = False
                if seg[0] == 'L': pen.lineTo(seg[2])
                else: pen.curveTo(seg[2], seg[3], seg[4])
            pen.closePath()
        else:
            changed = True
            for op in ops:
                if op[0] == 'm': pen.moveTo(op[1])
                elif op[0] == 'l': pen.lineTo(op[1])
                else: pen.curveTo(op[1], op[2], op[3])
            pen.closePath()
    if changed:
        charstrs[gname] = pen.getCharString(private=private)
    return changed

_rounded = 0
for _g in list(charstrs.keys()):
    if "." in _g:                                      # variant/assembly pieces: tiling seams
        continue
    if id(charstrs[_g]) != _ORIG_IDS.get(_g):          # already restyled by us
        continue
    _bp = BoundsPen(None); charstrs[_g].draw(_bp)
    if not _bp.bounds:                                 # empty (space, etc.)
        continue
    reweight_glyph(_g, SYM_EMB)                         # light embolden to match comic weight
    if round_glyph(_g):
        _rounded += 1
print(f"rounded {_rounded} untouched symbols (R={ROUND_R:.0f}, embolden={SYM_EMB})")

name = fira["name"]
def setname(nameID, value):
    name.setName(value, nameID, 3, 1, 0x409)
    name.setName(value, nameID, 1, 0, 0)
ps = FAMILY.replace(" ", "")
VERSION   = "1.0"                                   # bump per release
COPYRIGHT = ("Copyright (c) 2026 Pshenichnikov Artem | Claude code. "
             "Derived from Fira Math (c) 2018-2020 Xiangdong Zeng, plus Comic "
             "Relief, Courgette and UnifrakturCook. Hand-drawn blackboard "
             "letters are original. Licensed under the SIL Open Font License 1.1.")
LICENSE   = ("This Font Software is licensed under the SIL Open Font License, "
             "Version 1.1. This license is available with a FAQ at "
             "https://openfontlicense.org")
setname(0,  COPYRIGHT)                              # copyright (was Fira's)
setname(1,  FAMILY);            setname(4, f"{FAMILY} Regular")
setname(3,  f"{VERSION};{ps};{ps}-Regular")         # unique id (was Fira's)
setname(5,  f"Version {VERSION}")                   # version (was Fira's 0.3.4)
setname(6,  f"{ps}-Regular");   setname(16, FAMILY); setname(17, "Regular")
setname(13, LICENSE);           setname(14, "https://openfontlicense.org")
fira["head"].fontRevision = float(VERSION)

fira.save(OUT)
print(f"grafted {done} glyphs, skipped {skip}, wobble={WOBBLE} -> {OUT}")
