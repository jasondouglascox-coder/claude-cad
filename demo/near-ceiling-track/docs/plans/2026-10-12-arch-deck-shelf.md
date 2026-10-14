# HO Arch-Deck Shelf Parts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate every printable part of the HO arch-deck ceiling shelf as STEP files from one parameter file and one bay list, with tests proving each part fits the Bambu A1 bed and the assembled run has no overlapping parts.

**Architecture:** A Python package `hotrain` built on build123d (an OpenCascade CAD kernel). `params.py` holds every dimension and `layout.py` does the pure layout math (ties, tabs, posts, ladder joints). Each part module draws a 2D profile, extrudes it, and returns the part lying flat in print orientation, plus a `place()` Location that puts it into the run frame. `assembly.py` places everything and checks for clashes. `build.py` is the CLI that writes STEP, optional STL and SVG previews, and a manifest.

**Tech Stack:** Python 3.12 (managed by uv; the system Python 3.14 is too new for build123d's OCP wheels), build123d 0.13.0, pytest.

**Spec:** `docs/specs/2026-10-12-arch-deck-shelf-design.md`

## Global Constraints

- Units are millimetres everywhere. `INCH = 25.4` is only for readable defaults.
- Every dimension lives in `hotrain/params.py` (`Params`, a frozen dataclass; default instance `P`). Part code never hard-codes a size.
- Run frame: X along the track (0 = first pier centerline), Y across (+ toward the room; the wall is at Y = −track_offset), Z up (0 = tie underside = top of the panels' top band).
- Every `make()` returns a single valid solid lying flat on Z = 0, with min X and Y ≥ 0 and a footprint ≤ 251 mm (`P.bed_usable` = 256 − 5).
- Bay lengths must be 203.2–495 mm. Anything else raises `ValueError`.
- STEP is the primary output (the user opens parts in Onshape). STL only with `--mesh`.
- 2D outlines that aren't rectangles go through `joints.poly()`, which forces counter-clockwise order. A clockwise outline extrudes toward −Z and silently splits the part.
- Commit after every task, ending the message with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **Empty or out-of-range bay list** (the user mis-types a stud measurement). Expect a clear `ValueError` naming the bay and the allowed range, not a malformed part. Covered by Task 2 `test_validate_bays_*` and Task 9 `test_placed_parts_rejects_bad_bays`.
2. **Fits retuned after the fit-test print** (`fit_slide` 0.3, `fit_snap` 0.1, Peco-style `rail_base_w` 2.4). The gauge must stay exact and no parts may clash. Covered by Task 6 `test_ladder_gauge[p1]` and Task 9 `test_no_interference[p3]`.
3. **Shortest and longest bays** (8" and 19.5"). Arch halves must still fit the bed with at least one tab and post per half, and the assembly must stay clean. Covered by Task 3 `test_arch_half_printable` and Task 9 `test_no_interference[p2]`.
4. **Opening the STEP in Onshape.** Part names and millimetre units must survive. Covered by Task 10 `test_assembly_step_carries_part_names`.
5. **Very shallow cross-frames near the crown** (no room for the lightening window). Must still be a single valid solid. Covered by Task 4 `test_shallow_cross_frame_skips_window`.

---

### Task 1: Project scaffold and parameters

**Files:**
- Create: `pyproject.toml`, `README.md`, `hotrain/__init__.py` (empty), `hotrain/parts/__init__.py` (empty), `hotrain/params.py`
- Modify: `.gitignore`, `docs/specs/2026-10-12-arch-deck-shelf-design.md` (append §13)
- Test: `tests/test_params.py`

**Interfaces:**
- Produces: `hotrain.params.INCH`, `Params` (frozen dataclass; fields as listed; properties `rail_ctc`, `rail_ys`, `rail_top`, `groove_w`, `bracket_depth`, `bed_usable`), `P = Params()`. Tests vary parameters with `dataclasses.replace(P, field=value)`.

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[project]
name = "hotrain"
version = "0.1.0"
description = "Parametric 3D-printable HO arch-deck ceiling shelf"
requires-python = ">=3.12,<3.13"
dependencies = ["build123d==0.13.0"]

[dependency-groups]
dev = ["pytest>=8"]

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
```

- [ ] **Step 2: Replace `.gitignore`**

```text
out/
.venv/
__pycache__/
*.pyc
.pytest_cache/
.DS_Store
```

- [ ] **Step 3: Install the toolchain**

Run: `uv python pin 3.12 && uv sync && mkdir -p hotrain/parts tests && touch hotrain/__init__.py hotrain/parts/__init__.py`
Expected: creates `.venv`, installs build123d 0.13.0 and pytest, with no errors.

- [ ] **Step 4: Write the failing test**

`tests/test_params.py`:

```python
import pytest

from hotrain.params import INCH, P


def test_derived_dimensions():
    assert P.rail_ctc == pytest.approx(17.7)
    assert P.rail_ys == pytest.approx((-8.85, 8.85))
    assert P.groove_w == pytest.approx(2.4)
    assert P.rail_top == pytest.approx(2.3 + 0.4 + 2.54)
    assert P.bracket_depth == pytest.approx(3 * INCH + 4)
    assert P.bed_usable == pytest.approx(251)


def test_bay_limits_fit_the_bed():
    assert P.max_bay_len / 2 <= P.bed_usable
    assert P.min_bay_len < P.bay_len < P.max_bay_len
```

- [ ] **Step 5: Run it and confirm it fails**

Run: `uv run pytest tests/test_params.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'hotrain.params'`

- [ ] **Step 6: Write `hotrain/params.py`**

```python
"""Every dimension in the project. Units: millimetres. Parts read these; nothing else hard-codes a size."""
from dataclasses import dataclass

INCH = 25.4


@dataclass(frozen=True)
class Params:
    # track (NMRA HO, Code 100)
    gauge: float = 16.6
    rail_height: float = 2.54
    rail_base_w: float = 2.2
    rail_head_w: float = 1.1
    track_offset: float = 2.5 * INCH  # wall to track centerline
    rail_top_below_ceiling: float = 12 * INCH

    # bridge ties
    tie_l: float = 35.0
    tie_w: float = 2.6
    tie_h: float = 2.3
    tie_pitch: float = 5.5  # nominal; each bay adjusts slightly to fit a whole number of ties
    tie_plate_h: float = 0.4
    shoulder_h: float = 0.6
    shoulder_w: float = 0.8
    spike_lip_every: int = 4
    spike_lip_overhang: float = 0.3
    spike_lip_t: float = 0.4
    long_tie_every: int = 8
    long_tie_reach: float = 28.0  # track center to room-side end of a long tie
    socket_pad: float = 4.4
    runner_w: float = 5.6
    jig_neck: float = 2.4
    jig_head: float = 3.6
    jig_len: float = 2.0

    # arch panels
    panel_t: float = 3.2
    pier_depth: float = 3 * INCH  # below tie underside
    crown_depth: float = 1 * INCH  # below tie underside
    top_band_h: float = 6.0
    rib_h: float = 6.0
    post_w: float = 3.0
    post_pitch: float = 2 * INCH
    pier_w: float = 1.25 * INCH  # full pier; each bay owns half
    crown_block_w: float = 7.0
    tab_len: float = 6.0
    tab_first: float = 1 * INCH
    tab_pitch: float = 2 * INCH
    tab_joint_keepout: float = 8.0
    bay_len: float = 16 * INCH
    min_bay_len: float = 8 * INCH
    max_bay_len: float = 495.0

    # keystone (butterfly key at the crown)
    key_len: float = 12.0
    key_waist: float = 8.0
    key_head: float = 14.0

    # cross-frames
    cf_t: float = 2.4
    cf_wall: float = 2.5
    cf_bar: float = 3.0
    cf_border: float = 2.5
    rib_notch: float = 1.0

    # bracket
    bracket_t: float = 6.0
    bracket_member: float = 5.0
    bracket_bar: float = 4.0
    deck_block_margin: float = 6.0
    pier_notch: float = 1.0
    flange_w: float = 30.0
    flange_t: float = 6.0
    screw_d: float = 3.6
    screw_travel: float = 0.25 * INCH  # ± vertical adjustment
    screw_zs: tuple = (15.0, 65.0)  # below tie underside
    latch_top: float = 8.5  # below tie underside
    latch_win_h: float = 3.0
    latch_engage: float = 0.8
    latch_finger_w: float = 2.0
    latch_relief: float = 1.0
    latch_finger_len: float = 40.0

    # handrail
    handrail_h: float = 19.0  # above rail top
    handrail_offset: float = 25.0  # track center to handrail centerline
    handrail_t: float = 1.6
    handrail_post_w: float = 2.0
    handrail_bar: float = 1.6
    peg_w: float = 1.6
    handrail_gap: float = 0.5

    # fits
    fit_slide: float = 0.20
    fit_snap: float = 0.05

    # printer (Bambu A1)
    bed: float = 256.0
    bed_margin: float = 5.0

    @property
    def rail_ctc(self) -> float:
        return self.gauge + self.rail_head_w

    @property
    def rail_ys(self) -> tuple:
        return (-self.rail_ctc / 2, self.rail_ctc / 2)

    @property
    def rail_top(self) -> float:
        """Rail top above the tie underside (Z=0)."""
        return self.tie_h + self.tie_plate_h + self.rail_height

    @property
    def groove_w(self) -> float:
        return self.rail_base_w + self.fit_slide

    @property
    def bracket_depth(self) -> float:
        return self.pier_depth + self.bracket_bar

    @property
    def bed_usable(self) -> float:
        return self.bed - self.bed_margin


P = Params()
```

- [ ] **Step 7: Run the test and confirm it passes**

Run: `uv run pytest tests/test_params.py -v`
Expected: 2 PASS

- [ ] **Step 8: Write `README.md`**

```markdown
# HOTrain: HO arch-deck ceiling shelf

Parametric, 3D-printable bridge shelf for HO Code 100 track. Spec: `docs/specs/2026-10-12-arch-deck-shelf-design.md`.

## Setup

    uv sync

## Build

    uv run python -m hotrain.build all --preview   # every part + assembly + fit test
    uv run python -m hotrain.build check           # interference check

Outputs land in `out/`:
- `out/step/*.step`: open these in Onshape (Create > Import). Each part is exported lying flat in its print orientation.
- `out/step/run_assembly.step`: the whole run assembled in place, for review.
- `out/manifest.csv`: how many of each part to print.
- `out/preview/*.svg`: line drawings (with `--preview`).
- Add `--mesh` for STL files too.

## Change the design

- Dimensions: `hotrain/params.py`.
- Your wall: set `BAYS` in `hotrain/layout.py` to your measured stud-to-stud distances in mm.
- Then `uv run pytest` and rebuild.

## Print

PETG, 0.4 mm nozzle, 0.2 mm layers, no supports. Print `fit_test.step` first and tune `fit_slide`, `fit_snap` and `rail_base_w`.
```

- [ ] **Step 9: Append the amendments to the spec**

Append to `docs/specs/2026-10-12-arch-deck-shelf-design.md`:

```markdown
## 13. Amendments from implementation planning (2026-10-12)

- `tie_plate_h` is 0.4 mm (two 0.2 mm layers), not 0.3.
- `end_pier` quantity is 2 per run end (one per panel).
- Bay length limits: 203.2–495 mm (8–19.5"). The build refuses anything outside that with a clear error.
- Keystone is a bow-tie (butterfly) key pushed in from the panel face.
- Cross-frames locate along the track with a 1 mm notch under the arch rib at each post.
- Bracket wall plate is a 30 mm L-flange printed as part of the bracket, with two vertical screw slots.
- Latch: a flexing finger in the bracket's room-side slot wall hooks into a small window through the pier.
- Code layout: `hotrain/joints.py` and `hotrain/checks.py` replace `lib/profiles.py` and `lib/joints.py`.
- CLI: `parts` (whole run plus `out/manifest.csv`) and `check` (interference) replace `bay N`.
```

- [ ] **Step 10: Commit**

```bash
git add -A
git commit -m "feat: project scaffold and parameters

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 2: Layout math

**Files:**
- Create: `hotrain/layout.py`
- Test: `tests/test_layout.py`

**Interfaces:**
- Consumes: `Params`, `P`, `INCH`.
- Produces: `BAYS: list[float]`; `Tie(x, long, lip)`; `Segment(x_start, x_end, female_start, male_end)`; `validate_bays(p, bays) -> None` (raises `ValueError`); `half_len(bay_len)`; `springing_u(p)`; `rib_low(p, bay_len, u) -> float` (Z of the rib underside); `bay_pitch`, `ties_per_bay`, `joint_u(p, bay_len)`; `post_us(p, bay_len) -> list[float]`; `tab_us(p, bay_len) -> list[float]`; `pier_xs(bays)`; `run_extent(p, bays)`; `ties(p, bays) -> list[Tie]`; `segments(p, bays) -> list[Segment]`; `tab_xs(p, bays) -> list[float]`.

- [ ] **Step 1: Write the failing test**

`tests/test_layout.py`:

```python
import pytest
from hotrain.layout import (BAYS, validate_bays, bay_pitch, joint_u, post_us, rib_low, segments, tab_us, tab_xs,
                            ties, ties_per_bay, half_len, springing_u)
from hotrain.params import INCH, P


def test_rib_low_hits_pier_and_crown_depths():
    b = 16 * INCH
    assert rib_low(P, b, springing_u(P)) == pytest.approx(-P.pier_depth)
    assert rib_low(P, b, half_len(b)) == pytest.approx(-P.crown_depth)


@pytest.mark.parametrize("b", [12 * INCH, 16 * INCH, 19.5 * INCH, 17.3 * INCH])
def test_bay_pitch_close_to_nominal_and_whole(b):
    pb = bay_pitch(P, b)
    assert abs(pb - P.tie_pitch) < 0.1
    assert ties_per_bay(P, b) * pb == pytest.approx(b)


@pytest.mark.parametrize("b", [12 * INCH, 16 * INCH, 19.5 * INCH, 17.3 * INCH])
def test_tabs_stay_clear_of_ladder_joint(b):
    uj = joint_u(P, b)
    assert tab_us(P, b), "every half needs at least one tab"
    for u in tab_us(P, b):
        assert abs(u - uj) >= P.tab_len / 2 + P.tab_joint_keepout


def test_default_bay_has_four_tabs_and_three_posts_per_half():
    assert tab_us(P, 16 * INCH) == pytest.approx([25.4, 76.2, 127.0, 177.8])
    assert post_us(P, 16 * INCH) == pytest.approx([50.8, 101.6, 152.4])


@pytest.mark.parametrize("bays", [[16 * INCH], [16 * INCH, 14 * INCH, 19.5 * INCH]])
def test_segments_fit_bed_and_chain(bays):
    segs = segments(P, bays)
    assert not segs[0].female_start and not segs[-1].male_end
    for a, b in zip(segs, segs[1:]):
        assert a.x_end == b.x_start and a.male_end and b.female_start
    for s in segs:
        assert 0 < s.x_end - s.x_start <= P.bed_usable


@pytest.mark.parametrize("bays", [[16 * INCH], [16 * INCH, 14 * INCH, 19.5 * INCH]])
def test_no_tie_straddles_a_ladder_joint(bays):
    for s in segments(P, bays)[1:]:
        for t in ties(P, bays):
            assert abs(t.x - s.x_start) >= P.tie_w / 2 + 0.5


def test_ties_cover_end_piers():
    ts = ties(P, BAYS)
    assert ts[0].x - P.tie_w / 2 >= -P.pier_w / 2
    assert ts[0].x < -P.pier_w / 2 + 5
    assert ts[-1].x + P.tie_w / 2 <= sum(BAYS) + P.pier_w / 2


def test_tab_xs_mirror_within_bay():
    xs = tab_xs(P, BAYS)
    b = BAYS[0]
    assert xs == pytest.approx(sorted(b - x for x in xs))


@pytest.mark.parametrize("bays", [[], [600.0], [16 * INCH, 100.0]])
def test_validate_bays_rejects_unprintable_runs(bays):
    with pytest.raises(ValueError):
        validate_bays(P, bays)


def test_validate_bays_accepts_range_ends():
    validate_bays(P, [P.min_bay_len, P.max_bay_len, 16 * INCH])
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `uv run pytest tests/test_layout.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'hotrain.layout'`

- [ ] **Step 3: Write `hotrain/layout.py`**

```python
"""Pure layout math: where ties, tabs, posts, piers and ladder joints go. No CAD here.

Run frame: X along the track (0 = first pier centerline), Y across (+ toward the room),
Z up (0 = tie underside = top of the arch panels' top band).
"""
import math
from dataclasses import dataclass

from hotrain.params import INCH, P, Params

# The run you are building, as stud-to-stud bay lengths (mm). Prototype: one 16" bay.
BAYS: list[float] = [16 * INCH]


@dataclass(frozen=True)
class Tie:
    x: float
    long: bool
    lip: bool


@dataclass(frozen=True)
class Segment:
    """One tie ladder (and the handrail piece above it)."""
    x_start: float
    x_end: float
    female_start: bool  # jigsaw socket at x_start (another ladder plugs in)
    male_end: bool  # jigsaw tab at x_end


def validate_bays(p: Params, bays: list[float]) -> None:
    """Fail loudly on a bay list that can't be printed, instead of exporting a broken part."""
    if not bays:
        raise ValueError("BAYS is empty: list at least one stud-to-stud bay length in mm")
    for i, b in enumerate(bays):
        if not p.min_bay_len <= b <= p.max_bay_len:
            raise ValueError(f"bay {i} is {b:.1f} mm; each bay must be {p.min_bay_len:.1f}-{p.max_bay_len:.1f} mm "
                             f"(add a drywall-anchored pier to split a longer span)")


def half_len(bay_len: float) -> float:
    return bay_len / 2


def springing_u(p: Params = P) -> float:
    return p.pier_w / 2


def rib_low(p: Params, bay_len: float, u: float) -> float:
    """Z of the arch rib's underside at half-local u (0 = pier centerline, half_len = crown)."""
    s, h = springing_u(p), half_len(bay_len)
    t = (u - s) / (h - s)
    return -p.crown_depth - (p.pier_depth - p.crown_depth) * (1 - t) ** 2


def bay_pitch(p: Params, bay_len: float) -> float:
    """Tie pitch adjusted so the bay holds a whole number of ties."""
    return bay_len / round(bay_len / p.tie_pitch)


def ties_per_bay(p: Params, bay_len: float) -> int:
    return round(bay_len / p.tie_pitch)


def joint_u(p: Params, bay_len: float) -> float:
    """Half-local u of the ladder joint near the quarter point (mid-gap between ties)."""
    pb = bay_pitch(p, bay_len)
    return pb * math.floor(bay_len / 4 / pb + 0.5)


def post_us(p: Params, bay_len: float) -> list[float]:
    h = half_len(bay_len)
    out, k = [], 1
    while k * p.post_pitch + p.post_w / 2 < h - p.crown_block_w:
        out.append(k * p.post_pitch)
        k += 1
    return out


def tab_us(p: Params, bay_len: float) -> list[float]:
    h, uj = half_len(bay_len), joint_u(p, bay_len)
    out, u = [], p.tab_first
    while u + p.tab_len / 2 <= h - p.crown_block_w - 1:
        if abs(u - uj) >= p.tab_len / 2 + p.tab_joint_keepout:
            out.append(u)
        u += p.tab_pitch
    return out


def pier_xs(bays: list[float]) -> list[float]:
    xs = [0.0]
    for b in bays:
        xs.append(xs[-1] + b)
    return xs


def run_extent(p: Params, bays: list[float]) -> tuple[float, float]:
    return -p.pier_w / 2, sum(bays) + p.pier_w / 2


def ties(p: Params, bays: list[float]) -> list[Tie]:
    out: list[Tie] = []
    x_lo, x_hi = run_extent(p, bays)
    pb0 = bay_pitch(p, bays[0])
    k = 0
    while -pb0 * (k + 0.5) - p.tie_w / 2 >= x_lo:  # ties over the start end pier
        out.insert(0, Tie(-pb0 * (k + 0.5), False, False))
        k += 1
    for x0, b in zip(pier_xs(bays), bays):
        pb = bay_pitch(p, b)
        for k in range(ties_per_bay(p, b)):
            out.append(Tie(x0 + pb * (k + 0.5), k % p.long_tie_every == 0, k % p.spike_lip_every == 0))
    xl, pbl = sum(bays), bay_pitch(p, bays[-1])
    k = 0
    while xl + pbl * (k + 0.5) + p.tie_w / 2 <= x_hi:  # ties over the far end pier
        out.append(Tie(xl + pbl * (k + 0.5), False, False))
        k += 1
    return out


def segments(p: Params, bays: list[float]) -> list[Segment]:
    x_lo, x_hi = run_extent(p, bays)
    cuts = [x_lo]
    for x0, b in zip(pier_xs(bays), bays):
        uj = joint_u(p, b)
        cuts += [x0 + uj, x0 + b - uj]
    cuts.append(x_hi)
    n = len(cuts) - 1
    return [Segment(cuts[i], cuts[i + 1], i > 0, i < n - 1) for i in range(n)]


def tab_xs(p: Params, bays: list[float]) -> list[float]:
    out = []
    for x0, b in zip(pier_xs(bays), bays):
        for u in tab_us(p, b):
            out += [x0 + u, x0 + b - u]
    return sorted(out)
```

- [ ] **Step 4: Run the test and confirm it passes**

Run: `uv run pytest tests/test_layout.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: layout math for ties, tabs, posts and ladder joints

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 3: Joints, printability check, arch half and keystone

**Files:**
- Create: `hotrain/joints.py`, `hotrain/checks.py`, `hotrain/parts/arch_half.py`, `hotrain/parts/keystone.py`
- Test: `tests/test_arch_half.py`

**Interfaces:**
- Consumes: `layout.half_len`, `springing_u`, `rib_low`, `post_us`, `tab_us`.
- Produces: `joints.poly(*pts) -> Sketch` (counter-clockwise polygon), `joints.rect(u0, u1, v0, v1) -> Sketch`, `joints.butterfly(p, clearance=0.0) -> Sketch` (waist on x=0), `joints.jigsaw(p, x, y, clearance=0.0) -> Sketch`; `checks.printable_problems(part, p=P) -> list[str]`; `arch_half.profile(p, bay_len)`, `arch_half.make(p, bay_len) -> Part`, `arch_half.place(p, x0, bay_len, y_c, end: bool) -> Location`; `keystone.make(p) -> Part`, `keystone.place(p, x, y_c) -> Location`.

- [ ] **Step 1: Write the failing test**

`tests/test_arch_half.py`:

```python
import pytest
from build123d import Pos

from hotrain.checks import printable_problems
from hotrain.params import INCH, P
from hotrain.parts import arch_half, keystone


@pytest.mark.parametrize("b", [P.min_bay_len, 16 * INCH, P.max_bay_len])
def test_arch_half_printable(b):
    assert printable_problems(arch_half.make(P, b)) == []


def test_arch_half_extent():
    bb = arch_half.make(P, 16 * INCH).bounding_box()
    assert bb.min.X == pytest.approx(0, abs=1e-6)
    assert bb.max.X == pytest.approx(8 * INCH)
    assert bb.max.Y == pytest.approx(P.pier_depth + P.tie_h)  # tabs poke up tie_h above the band
    assert bb.max.Z == pytest.approx(P.panel_t)


def test_keystone_printable_and_fits_socket_with_clearance():
    half = arch_half.make(P, 16 * INCH)
    key = keystone.make(P)
    assert printable_problems(key) == []
    h = 8 * INCH
    at_crown = Pos(h - P.key_len / 2, P.pier_depth - P.crown_depth / 2 - P.key_head / 2, 0) * key
    assert (half & at_crown).volume == pytest.approx(0, abs=1e-6)
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `uv run pytest tests/test_arch_half.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'hotrain.checks'`

- [ ] **Step 3: Write `hotrain/joints.py`**

```python
"""Shared 2D joint shapes. All are build123d sketches centered on the joint line."""
from build123d import Align, Kind, Polygon, Pos, Rectangle, Sketch, offset

from hotrain.params import Params


def poly(*pts: tuple) -> Sketch:
    """Polygon traced counter-clockwise whatever order the points come in, so it extrudes toward +Z."""
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
    return Polygon(*(pts if area > 0 else pts[::-1]), align=None)


def rect(u0: float, u1: float, v0: float, v1: float) -> Sketch:
    """Axis-aligned rectangle from corner (u0, v0) to (u1, v1)."""
    return Pos(u0, v0) * Rectangle(u1 - u0, v1 - v0, align=(Align.MIN, Align.MIN))


def butterfly(p: Params, clearance: float = 0.0) -> Sketch:
    """Bow-tie key: waist on the joint line (x=0), heads at x = ±key_len/2. clearance grows it."""
    hl, hh, hw = p.key_len / 2, p.key_head / 2, p.key_waist / 2
    key = poly((-hl, -hh), (0, -hw), (hl, -hh), (hl, hh), (0, hw), (-hl, hh))
    return offset(key, clearance, kind=Kind.INTERSECTION) if clearance else key


def jigsaw(p: Params, x: float, y: float, clearance: float = 0.0) -> Sketch:
    """Dovetail tab whose neck sits on x and widens toward +x (into the next ladder)."""
    n, h = p.jig_neck / 2, p.jig_head / 2
    tab = poly((x - 0.01, y - n), (x + p.jig_len, y - h), (x + p.jig_len, y + h), (x - 0.01, y + n))
    return offset(tab, clearance, kind=Kind.INTERSECTION) if clearance else tab
```

- [ ] **Step 4: Write `hotrain/checks.py`**

```python
"""Printability checks shared by tests and the build command."""
from build123d import Shape

from hotrain.params import P, Params


def printable_problems(part: Shape, p: Params = P) -> list[str]:
    """Why this part can't go straight to the A1 as exported. Empty list = fine."""
    probs = []
    if not part.is_valid:
        probs.append("invalid solid")
    if len(part.solids()) != 1:
        probs.append(f"{len(part.solids())} separate solids (expected 1)")
    bb = part.bounding_box()
    if abs(bb.min.Z) > 1e-6:
        probs.append(f"not on the bed: min Z = {bb.min.Z:.3f}")
    if bb.min.X < -1e-6 or bb.min.Y < -1e-6:
        probs.append("extends into negative X/Y")
    if bb.max.X > p.bed_usable or bb.max.Y > p.bed_usable:
        probs.append(f"footprint {bb.max.X:.1f} x {bb.max.Y:.1f} mm exceeds {p.bed_usable:.0f} mm")
    return probs
```

- [ ] **Step 5: Write `hotrain/parts/arch_half.py`**

```python
"""Half of one arch panel: half pier + top band + posts + half arch rib, pier at u=0, crown at u=half."""
from build123d import Bezier, Face, Line, Location, Part, Pos, Rot, Sketch, Wire, extrude

from hotrain import layout as L
from hotrain.joints import butterfly, rect
from hotrain.params import P, Params


def profile(p: Params, bay_len: float) -> Sketch:
    """Profile in (u, z): u from the pier centerline, z = 0 at the band top (tie underside)."""
    h, s = L.half_len(bay_len), L.springing_u(p)
    mid, cd, pd = (s + h) / 2, p.crown_depth, p.pier_depth
    lo = Bezier((s, -pd), (mid, -cd), (h, -cd))
    hi = Bezier((h, -cd + p.rib_h), (mid, -cd + p.rib_h), (s, -pd + p.rib_h))
    rib = Face(Wire([lo, Line((h, -cd), (h, -cd + p.rib_h)), hi, Line((s, -pd + p.rib_h), (s, -pd))]))
    adds = [
        rect(0, h, -p.top_band_h, 0),  # top band
        rect(0, s, -pd, 0),  # half pier
        rib,
        rect(h - p.crown_block_w, h, -cd, 0),  # crown block holding the keystone socket
    ]
    for u in L.post_us(p, bay_len):
        adds.append(rect(u - p.post_w / 2, u + p.post_w / 2, L.rib_low(p, bay_len, u) + 1, -p.top_band_h / 2))
    for u in L.tab_us(p, bay_len):
        adds.append(rect(u - p.tab_len / 2, u + p.tab_len / 2, -1, p.tie_h))
    cuts = []
    nw = (p.cf_t + p.fit_slide) / 2
    for u in L.post_us(p, bay_len):  # cross-frame locating notch under the rib
        z = L.rib_low(p, bay_len, u)
        cuts.append(rect(u - nw, u + nw, z - 2, z + p.rib_notch))
    bw = (p.bracket_t + p.fit_slide) / 2
    cuts.append(rect(-1, bw, -pd - 1, -pd + p.pier_notch))  # bracket tongue
    cuts.append(rect(-1, bw, -p.latch_top - p.latch_win_h, -p.latch_top))  # latch window
    cuts.append(Pos(h, -cd / 2) * butterfly(p, p.fit_snap))  # keystone socket
    return (Sketch() + adds) - cuts


def make(p: Params = P, bay_len: float = P.bay_len) -> Part:
    """Print orientation: flat on the bed, u along X, pier bottom on Y=0."""
    return Pos(0, p.pier_depth, 0) * extrude(profile(p, bay_len), p.panel_t)


def place(p: Params, x0: float, bay_len: float, y_c: float, end: bool) -> Location:
    """Location taking the print-frame part into the run frame. end=True mirrors it to the bay's far half."""
    centre = Pos(0, p.panel_t / 2, 0) * Rot(90, 0, 0)
    if end:
        return Pos(x0 + bay_len, y_c, -p.pier_depth) * Rot(0, 0, 180) * centre
    return Pos(x0, y_c, -p.pier_depth) * centre
```

- [ ] **Step 6: Write `hotrain/parts/keystone.py`**

```python
"""Bow-tie keystone that joins two arch halves at the crown."""
from build123d import Location, Part, Pos, Rot, extrude

from hotrain.joints import butterfly
from hotrain.params import P, Params


def make(p: Params = P) -> Part:
    return extrude(Pos(p.key_len / 2, p.key_head / 2) * butterfly(p), p.panel_t)


def place(p: Params, x: float, y_c: float) -> Location:
    return (Pos(x, y_c, -p.crown_depth / 2) * Pos(0, p.panel_t / 2, 0) * Rot(90, 0, 0)
            * Pos(-p.key_len / 2, -p.key_head / 2, 0))
```

- [ ] **Step 7: Run the test and confirm it passes**

Run: `uv run pytest tests/test_arch_half.py -v`
Expected: all PASS

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "feat: arch half panel and keystone

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 4: Cross-frame

**Files:**
- Create: `hotrain/parts/cross_frame.py`
- Test: `tests/test_cross_frame.py`

**Interfaces:**
- Consumes: `joints.rect`, `checks.printable_problems`.
- Produces: `cross_frame.width(p)`, `cross_frame.height(p, depth)`, `cross_frame.profile(p, depth)`, `cross_frame.make(p, depth) -> Part`, `cross_frame.place(p, x, depth) -> Location`. `depth` = −`layout.rib_low(p, bay_len, u)` at the post.

- [ ] **Step 1: Write the failing test**

`tests/test_cross_frame.py`:

```python
import pytest
from build123d import Align, Box, Pos

from hotrain.checks import printable_problems
from hotrain.params import P
from hotrain.parts import cross_frame


def test_cross_frame_printable_and_slot_width():
    cf = cross_frame.make(P, 40.0)
    assert printable_problems(cf) == []
    w, sw, h = cross_frame.width(P), P.panel_t + P.fit_slide, cross_frame.height(P, 40)

    def material_at(z_below_top):
        probe = Pos(0, h - z_below_top, 0) * Box(w, 0.5, P.cf_t, align=(Align.MIN, Align.MIN, Align.MIN))
        return (cf & probe).volume / (0.5 * P.cf_t)

    assert material_at(1.0) == pytest.approx(w - 2 * sw, abs=0.01)  # above the window: only the slots
    window = P.rail_ctc - sw - 2 * P.cf_border
    assert material_at(20.0) == pytest.approx(w - 2 * sw - window, abs=0.01)


def test_shallow_cross_frame_skips_window():
    assert printable_problems(cross_frame.make(P, 8.0)) == []
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `uv run pytest tests/test_cross_frame.py -v`
Expected: FAIL with `ImportError: cannot import name 'cross_frame'`

- [ ] **Step 3: Write `hotrain/parts/cross_frame.py`**

```python
"""H-frame between the two panels at a post. Slots hold panel spacing; its bar seats in the rib notch."""
from build123d import Location, Part, Pos, Rot, Sketch, extrude

from hotrain.joints import rect
from hotrain.params import P, Params


def width(p: Params) -> float:
    return p.rail_ctc + p.panel_t + p.fit_slide + 2 * p.cf_wall


def height(p: Params, depth: float) -> float:
    return depth + p.cf_bar


def profile(p: Params, depth: float) -> Sketch:
    """Profile in (y, z); depth = distance from tie underside down to the rib underside at this post."""
    w, sw = width(p), p.panel_t + p.fit_slide
    body = rect(-w / 2, w / 2, -height(p, depth), 0)
    slot_bottom = -depth + p.rib_notch
    cuts = [rect(y - sw / 2, y + sw / 2, slot_bottom, 1) for y in p.rail_ys]
    wy = p.rail_ctc / 2 - sw / 2 - p.cf_border
    if -p.cf_border - slot_bottom > 3:
        cuts.append(rect(-wy, wy, slot_bottom, -p.cf_border))
    return body - cuts


def make(p: Params = P, depth: float = 40.0) -> Part:
    return Pos(width(p) / 2, height(p, depth), 0) * extrude(profile(p, depth), p.cf_t)


def place(p: Params, x: float, depth: float) -> Location:
    return Pos(x, 0, 0) * Rot(0, 0, 90) * Rot(90, 0, 0) * Pos(-width(p) / 2, -height(p, depth), -p.cf_t / 2)
```

- [ ] **Step 4: Run the test and confirm it passes**

Run: `uv run pytest tests/test_cross_frame.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: cross-frame

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 5: Bracket and end pier

**Files:**
- Create: `hotrain/parts/bracket.py`, `hotrain/parts/end_pier.py`
- Test: `tests/test_bracket.py`

**Interfaces:**
- Consumes: `joints.poly`, `joints.rect`.
- Produces: `bracket.slot_w(p)`, `bracket.slots_and_latch(p, slot_bottom, ys) -> (list[Sketch], Sketch)` (also used by the fit test), `bracket.profile(p)`, `bracket.make(p) -> Part`, `bracket.place(p, xp) -> Location`; `end_pier.make(p) -> Part`, `end_pier.place(p, xp, y_c, run_start: bool) -> Location`.

- [ ] **Step 1: Write the failing test**

`tests/test_bracket.py`:

```python
import pytest

from hotrain.checks import printable_problems
from hotrain.params import P
from hotrain.parts import bracket, end_pier


def test_bracket_printable():
    assert printable_problems(bracket.make(P)) == []


def test_bracket_extent():
    bb = bracket.make(P).bounding_box()
    assert bb.max.X == pytest.approx(P.track_offset + P.tie_l / 2)  # wall to room-side tie end
    assert bb.max.Y == pytest.approx(P.bracket_depth)
    assert bb.max.Z == pytest.approx(P.flange_w)


def test_end_pier_printable():
    assert printable_problems(end_pier.make(P)) == []
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `uv run pytest tests/test_bracket.py -v`
Expected: FAIL with `ImportError: cannot import name 'bracket'`

- [ ] **Step 3: Write `hotrain/parts/bracket.py`**

```python
"""Wall bracket at each pier: flange on the stud, triangulated arm, deck block with pier slots and a latch."""
from build123d import (Location, Part, Plane, Pos, Rot, Sketch, SlotCenterToCenter, Box, Align,
                       extrude)

from hotrain.joints import poly, rect
from hotrain.params import P, Params


def slot_w(p: Params) -> float:
    return p.panel_t + p.fit_slide


def slots_and_latch(p: Params, slot_bottom: float, ys: tuple) -> tuple[list, Sketch]:
    """Pier slots at each y in ys (open at the top) plus the latch on the room-side slot.
    Returns (cuts, hook). Coordinates are (y, z) with z = 0 at the tie underside."""
    sw = slot_w(p)
    cuts = [rect(y - sw / 2, y + sw / 2, slot_bottom, 1) for y in ys]
    wall = max(ys) + sw / 2  # room-side wall of the room-side slot
    relief = wall + p.latch_finger_w
    cuts.append(rect(relief, relief + p.latch_relief, -p.latch_finger_len, 1))
    zb = -p.latch_top - p.latch_win_h + 0.5
    e = p.latch_engage
    hook = poly((wall + 0.05, zb), (wall - e, zb), (wall - e, zb + 0.8), (wall + 0.05, zb + 0.8 + e))
    return cuts, hook


def profile(p: Params) -> Sketch:
    """Profile in (y, z): y from the track centerline (+ room), z = 0 at the tie underside."""
    yw = -p.track_offset
    yf = yw + p.flange_t
    yd0 = min(p.rail_ys) - slot_w(p) / 2 - p.deck_block_margin
    yd1 = p.tie_l / 2
    zb, m = -p.bracket_depth, p.bracket_member
    bound = rect(yw, yd1, zb, 0)
    p0, p1 = (yf, zb), (yd0, -m)
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    ln = (dx * dx + dy * dy) ** 0.5
    nx, ny = -dy / ln * m / 2, dx / ln * m / 2
    diag = poly((p0[0] + nx, p0[1] + ny), (p1[0] + nx, p1[1] + ny), (p1[0] - nx, p1[1] - ny),
                (p0[0] - nx, p0[1] - ny)) & bound
    body = Sketch() + [
        rect(yw, yf, zb, 0),  # wall plate
        rect(yw, yd0, -m, 0),  # top arm
        rect(yw, yd0, zb, zb + m),  # bottom arm
        diag,
        rect(yd0, yd1, zb, 0),  # deck block
    ]
    cuts, hook = slots_and_latch(p, -p.pier_depth + p.pier_notch, p.rail_ys)
    return (body - cuts) + hook


def make(p: Params = P) -> Part:
    """Print orientation: plate flat (Z 0..bracket_t), flange standing up along the wall edge (X 0..flange_t)."""
    plate = extrude(Pos(p.track_offset, p.bracket_depth) * profile(p), p.bracket_t)
    flange = Box(p.flange_t, p.bracket_depth, p.flange_w, align=(Align.MIN, Align.MIN, Align.MIN))
    zc = p.bracket_t + (p.flange_w - p.bracket_t) / 2
    holes = [extrude(Plane.YZ * Pos(p.bracket_depth - z, zc) * SlotCenterToCenter(2 * p.screw_travel, p.screw_d),
                     p.flange_t) for z in p.screw_zs]
    return plate + flange - holes


def place(p: Params, xp: float) -> Location:
    return Pos(xp, 0, 0) * Rot(0, 0, 90) * Rot(90, 0, 0) * Pos(-p.track_offset, -p.bracket_depth, -p.bracket_t / 2)
```

- [ ] **Step 4: Write `hotrain/parts/end_pier.py`**

```python
"""Half pier that closes a run: the missing neighbor of the first and last arch halves."""
from build123d import Location, Part, Pos, Rot, Sketch, extrude

from hotrain.joints import rect
from hotrain.params import P, Params


def profile(p: Params) -> Sketch:
    s, bw = p.pier_w / 2, (p.bracket_t + p.fit_slide) / 2
    return rect(0, s, -p.pier_depth, 0) - [
        rect(-1, bw, -p.pier_depth - 1, -p.pier_depth + p.pier_notch),
        rect(-1, bw, -p.latch_top - p.latch_win_h, -p.latch_top),
    ]


def make(p: Params = P) -> Part:
    return Pos(0, p.pier_depth, 0) * extrude(profile(p), p.panel_t)


def place(p: Params, xp: float, y_c: float, run_start: bool) -> Location:
    centre = Pos(0, p.panel_t / 2, 0) * Rot(90, 0, 0)
    if run_start:
        return Pos(xp, y_c, -p.pier_depth) * Rot(0, 0, 180) * centre
    return Pos(xp, y_c, -p.pier_depth) * centre
```

- [ ] **Step 5: Run the test and confirm it passes**

Run: `uv run pytest tests/test_bracket.py -v`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: wall bracket with latch, and end pier

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 6: Tie ladder

**Files:**
- Create: `hotrain/parts/tie_ladder.py`
- Test: `tests/test_tie_ladder.py`

**Interfaces:**
- Consumes: `layout.ties`, `segments`, `tab_xs`, `Segment`, `Tie`; `joints.jigsaw`, `joints.rect`.
- Produces: `tie_ladder.build(p, ties, x_start, x_end, tab_xs, female_start, male_end) -> Part` (run frame; used by the fit test), `tie_ladder.make(p, bays, seg) -> Part` (print frame), `tie_ladder.place(p, seg) -> Location`.

- [ ] **Step 1: Write the failing test**

`tests/test_tie_ladder.py`:

```python
from dataclasses import replace

import pytest
from build123d import Align, Box, Pos

from hotrain import layout as L
from hotrain.checks import printable_problems
from hotrain.params import INCH, P
from hotrain.parts import tie_ladder


@pytest.mark.parametrize("bays", [[16 * INCH], [16 * INCH, 14 * INCH, P.max_bay_len]])
def test_every_ladder_printable(bays):
    for seg in L.segments(P, bays):
        assert printable_problems(tie_ladder.make(P, bays, seg)) == []


@pytest.mark.parametrize("p", [P, replace(P, rail_base_w=2.4, fit_slide=0.3)])
def test_ladder_gauge(p):
    """On a real tie: groove centerlines rail_ctc apart, each groove rail_base_w + fit_slide wide."""
    bays = [16 * INCH]
    seg = L.segments(p, bays)[1]
    lad = tie_ladder.make(p, bays, seg)
    t = next(t for t in L.ties(p, bays) if seg.x_start < t.x < seg.x_end and not t.lip and not t.long)
    x = t.x - seg.x_start
    z0 = p.tie_h + p.tie_plate_h + 0.1
    probe = Pos(x - 0.1, 0, z0) * Box(0.2, p.tie_l, 0.2, align=(Align.MIN, Align.MIN, Align.MIN))
    pieces = sorted((s.bounding_box() for s in (lad & probe).solids()), key=lambda b: b.min.Y)
    assert len(pieces) == 4, "two shoulders per rail"
    grooves = [(pieces[0].max.Y, pieces[1].min.Y), (pieces[2].max.Y, pieces[3].min.Y)]
    widths = [b - a for a, b in grooves]
    centres = [(a + b) / 2 for a, b in grooves]
    assert widths == pytest.approx([p.groove_w] * 2, abs=0.01)
    assert centres[1] - centres[0] == pytest.approx(p.rail_ctc, abs=0.01)
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `uv run pytest tests/test_tie_ladder.py -v`
Expected: FAIL with `ImportError: cannot import name 'tie_ladder'`

- [ ] **Step 3: Write `hotrain/parts/tie_ladder.py`**

```python
"""Open bridge-tie ladder: ties on two hidden runners, gauge-setting tie plates, spike lips, long ties."""
from build123d import Location, Part, Pos, Sketch, extrude

from hotrain import layout as L
from hotrain.joints import jigsaw, rect
from hotrain.params import P, Params


def build(p: Params, ties: list, x_start: float, x_end: float, tab_xs: list[float],
          female_start: bool, male_end: bool) -> Part:
    """Ladder in the run frame (x along track, y across, z = 0 at tie underside)."""
    ts = [t for t in ties if x_start < t.x < x_end]
    hw, g, sw = p.tie_w / 2, p.groove_w / 2, p.shoulder_w
    base = []
    for t in ts:
        base.append(rect(t.x - hw, t.x + hw, -p.tie_l / 2, p.long_tie_reach if t.long else p.tie_l / 2))
        if t.long:
            base.append(rect(t.x - p.socket_pad / 2, t.x + p.socket_pad / 2,
                             p.handrail_offset - p.socket_pad / 2, p.handrail_offset + p.socket_pad / 2))
    for y in p.rail_ys:
        base.append(rect(x_start, x_end, y - p.runner_w / 2, y + p.runner_w / 2))
        if male_end:
            base.append(jigsaw(p, x_end, y))
    cuts = []
    tl, tw = (p.tab_len + p.fit_slide) / 2, (p.panel_t + p.fit_slide) / 2
    for x in tab_xs:
        if x_start + tl < x < x_end - tl:
            cuts += [rect(x - tl, x + tl, y - tw, y + tw) for y in p.rail_ys]
    for t in ts:
        if t.long:
            px, py = (p.peg_w + p.fit_snap) / 2, (p.handrail_t + p.fit_snap) / 2
            cuts.append(rect(t.x - px, t.x + px, p.handrail_offset - py, p.handrail_offset + py))
    if female_start:
        cuts += [jigsaw(p, x_start, y, p.fit_snap) for y in p.rail_ys]
    part = extrude((Sketch() + base) - cuts, p.tie_h)

    plates, shoulders, lips = [], [], []
    for t in ts:
        for y in p.rail_ys:
            plates.append(rect(t.x - hw, t.x + hw, y - g - sw, y + g + sw))
            shoulders += [rect(t.x - hw, t.x + hw, y - g - sw, y - g), rect(t.x - hw, t.x + hw, y + g, y + g + sw)]
            if t.lip:
                o = p.spike_lip_overhang
                lips += [rect(t.x - hw, t.x + hw, y - g - sw, y - g + o), rect(t.x - hw, t.x + hw, y + g - o, y + g + sw)]
    z = p.tie_h
    part += Pos(0, 0, z) * extrude(Sketch() + plates, p.tie_plate_h)
    z += p.tie_plate_h
    part += Pos(0, 0, z) * extrude(Sketch() + shoulders, p.shoulder_h)
    z += p.shoulder_h
    if lips:
        part += Pos(0, 0, z) * extrude(Sketch() + lips, p.spike_lip_t)
    return part


def make(p: Params, bays: list[float], seg: L.Segment) -> Part:
    """Print orientation: ties flat on the bed, X from the ladder's start, Y from the wall-side tie end."""
    run = build(p, L.ties(p, bays), seg.x_start, seg.x_end, L.tab_xs(p, bays), seg.female_start, seg.male_end)
    return Pos(-seg.x_start, p.tie_l / 2, 0) * run


def place(p: Params, seg: L.Segment) -> Location:
    return Pos(seg.x_start, -p.tie_l / 2, 0)
```

- [ ] **Step 4: Run the test and confirm it passes**

Run: `uv run pytest tests/test_tie_ladder.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: open bridge-tie ladder with gauge-setting tie plates

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 7: Handrail

**Files:**
- Create: `hotrain/parts/handrail.py`
- Test: `tests/test_handrail.py`

**Interfaces:**
- Consumes: `layout.ties`, `layout.Segment`; `joints.rect`.
- Produces: `handrail.post_xs(p, bays, seg)`, `handrail.make(p, bays, seg) -> Part | None` (None when the segment has no long ties), `handrail.place(p, seg) -> Location`.

- [ ] **Step 1: Write the failing test**

`tests/test_handrail.py`:

```python
import pytest

from hotrain import layout as L
from hotrain.checks import printable_problems
from hotrain.params import INCH, P
from hotrain.parts import handrail


@pytest.mark.parametrize("bays", [[16 * INCH], [16 * INCH, 14 * INCH, P.max_bay_len]])
def test_every_handrail_printable(bays):
    for seg in L.segments(P, bays):
        hr = handrail.make(P, bays, seg)
        assert hr is not None, "every ladder carries at least one long tie"
        assert printable_problems(hr) == []


def test_handrail_height():
    seg = L.segments(P, [16 * INCH])[1]
    bb = handrail.make(P, [16 * INCH], seg).bounding_box()
    assert bb.max.Y == pytest.approx(P.rail_top + P.handrail_h)
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `uv run pytest tests/test_handrail.py -v`
Expected: FAIL with `ImportError: cannot import name 'handrail'`

- [ ] **Step 3: Write `hotrain/parts/handrail.py`**

```python
"""Room-side handrail piece: top and mid bars, posts on the long ties, pegs into the tie sockets."""
from build123d import Location, Part, Pos, Rot, Sketch, extrude

from hotrain import layout as L
from hotrain.joints import rect
from hotrain.params import P, Params


def post_xs(p: Params, bays: list[float], seg: L.Segment) -> list[float]:
    return [t.x for t in L.ties(p, bays) if t.long and seg.x_start < t.x < seg.x_end]


def make(p: Params, bays: list[float], seg: L.Segment) -> Part | None:
    """Print orientation: profile flat on the bed, X along the track from seg.x_start, Y = height above tie underside."""
    xs = [x - seg.x_start for x in post_xs(p, bays, seg)]
    if not xs:
        return None
    ln, top, b = seg.x_end - seg.x_start, p.rail_top + p.handrail_h, p.handrail_bar
    zm = (p.tie_h + top) / 2
    shapes = [rect(p.handrail_gap / 2, ln - p.handrail_gap / 2, top - b, top),
              rect(p.handrail_gap / 2, ln - p.handrail_gap / 2, zm - b / 2, zm + b / 2)]
    for x in xs:
        shapes.append(rect(x - p.handrail_post_w / 2, x + p.handrail_post_w / 2, p.tie_h, top))
        shapes.append(rect(x - p.peg_w / 2, x + p.peg_w / 2, 0, p.tie_h))
    return extrude(Sketch() + shapes, p.handrail_t)


def place(p: Params, seg: L.Segment) -> Location:
    return Pos(seg.x_start, p.handrail_offset + p.handrail_t / 2, 0) * Rot(90, 0, 0)
```

- [ ] **Step 4: Run the test and confirm it passes**

Run: `uv run pytest tests/test_handrail.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: room-side handrail

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 8: Fit-test coupon

**Files:**
- Create: `hotrain/parts/fit_test.py`
- Test: `tests/test_fit_test.py`

**Interfaces:**
- Consumes: `tie_ladder.build`, `bracket.slots_and_latch`, `bracket.slot_w`, `joints.butterfly`, `joints.rect`, `layout.Tie`.
- Produces: `fit_test.make(p) -> Compound` (11 separate solids on one bed). Variants are marked with 1/2/3 notches = `GROOVE_FITS` (0.10/0.20/0.30), `SLOT_FITS` (0.10/0.20/0.30), `KEY_FITS` (0.0/0.05/0.10).

- [ ] **Step 1: Write the failing test**

`tests/test_fit_test.py`:

```python
import pytest

from hotrain.params import P
from hotrain.parts import fit_test


def test_fit_test_fits_bed_and_has_every_piece():
    ft = fit_test.make(P)
    bb = ft.bounding_box()
    assert bb.max.X <= P.bed_usable and bb.max.Y <= P.bed_usable
    assert bb.min.Z == pytest.approx(0, abs=1e-6)
    solids = ft.solids()
    assert all(s.is_valid for s in solids)
    assert len(solids) == 3 + 2 + 3 + 1 + 2  # grooves, slot plate + tab strip, key blocks, key, latch pair
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `uv run pytest tests/test_fit_test.py -v`
Expected: FAIL with `ImportError: cannot import name 'fit_test'`

- [ ] **Step 3: Write `hotrain/parts/fit_test.py`**

```python
"""Calibration coupon: tie-plate grooves, tab slots and keystone sockets at three clearances, plus a latch.
Variant 1/2/3 = smallest/default/largest clearance, marked with 1/2/3 notches."""
from dataclasses import replace

from build123d import Compound, Part, Pos, Sketch, extrude

from hotrain.joints import butterfly, rect
from hotrain.layout import Tie
from hotrain.params import P, Params
from hotrain.parts import bracket, tie_ladder

GROOVE_FITS = (0.10, 0.20, 0.30)
SLOT_FITS = (0.10, 0.20, 0.30)
KEY_FITS = (0.0, 0.05, 0.10)
LATCH_DEPTH = 45.0


def marks(n: int, x: float, y: float) -> list[Sketch]:
    return [rect(x + 1.6 * i, x + 1.6 * i + 0.8, y - 0.01, y + 1.0) for i in range(n)]


def groove_sample(p: Params, fit: float, n: int) -> Part:
    q = replace(p, fit_slide=fit)
    ties = [Tie(2.75 + 5.5 * k, False, k == 1) for k in range(3)]
    lad = Pos(0, q.tie_l / 2, 0) * tie_ladder.build(q, ties, 0, 16.5, [], False, False)
    return lad - extrude(Sketch() + marks(n, 1.0, 0), q.tie_h)


def slot_plate(p: Params) -> Part:
    body = rect(0, 3 * 14 + 4, 0, 14)
    cuts = []
    for i, f in enumerate(SLOT_FITS):
        cx, hl, hw = 4 + 14 * i + 5, (p.tab_len + f) / 2, (p.panel_t + f) / 2
        cuts.append(rect(cx - hl, cx + hl, 7 - hw, 7 + hw))
        cuts += marks(i + 1, cx - 3, 0)
    return extrude(body - cuts, p.tie_h)


def tab_strip(p: Params) -> Part:
    return extrude(Sketch() + [rect(0, 30, 0, 10), rect(12, 12 + p.tab_len, 9, 10 + p.tie_h)], p.panel_t)


def key_block(p: Params, fit: float, n: int) -> Part:
    w, h = 16.0, p.key_head + 8
    body = rect(0, w, 0, h) - [Pos(w, h / 2) * butterfly(p, fit)] - marks(n, 1.0, 0)
    return extrude(body, p.panel_t)


def key(p: Params) -> Part:
    return extrude(Pos(p.key_len / 2, p.key_head / 2) * butterfly(p), p.panel_t)


def latch_block(p: Params) -> Part:
    """A short deck block with one pier slot and the latch, depth LATCH_DEPTH."""
    sw = bracket.slot_w(p)
    y0, y1 = -sw / 2 - 6, sw / 2 + p.latch_finger_w + p.latch_relief + 4
    cuts, hook = bracket.slots_and_latch(p, -LATCH_DEPTH + p.pier_notch, (0.0,))
    prof = (rect(y0, y1, -LATCH_DEPTH - 4, 0) - cuts) + hook
    return extrude(Pos(-y0, LATCH_DEPTH + 4) * prof, p.bracket_t)


def latch_pier(p: Params) -> Part:
    """Pier stub with the window and bottom notch centered, to snap into latch_block."""
    w, bw = 24.0, (p.bracket_t + p.fit_slide) / 2
    prof = rect(-w / 2, w / 2, -LATCH_DEPTH, 0) - [
        rect(-bw, bw, -LATCH_DEPTH - 1, -LATCH_DEPTH + p.pier_notch),
        rect(-bw, bw, -p.latch_top - p.latch_win_h, -p.latch_top),
    ]
    return extrude(Pos(w / 2, LATCH_DEPTH) * prof, p.panel_t)


def make(p: Params = P) -> Compound:
    pieces = []
    for i, f in enumerate(GROOVE_FITS):
        pieces.append(Pos(0, 50 * i, 0) * groove_sample(p, f, i + 1))
    pieces.append(Pos(60, 0, 0) * slot_plate(p))
    pieces.append(Pos(60, 25, 0) * tab_strip(p))
    for i, f in enumerate(KEY_FITS):
        pieces.append(Pos(110 + 22 * i, 0, 0) * key_block(p, f, i + 1))
    pieces.append(Pos(110, 35, 0) * key(p))
    pieces.append(Pos(60, 60, 0) * latch_block(p))
    pieces.append(Pos(110, 60, 0) * latch_pier(p))
    return Compound(children=pieces)
```

- [ ] **Step 4: Run the test and confirm it passes**

Run: `uv run pytest tests/test_fit_test.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: fit-test calibration coupon

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 9: Assembly and clash check

**Files:**
- Create: `hotrain/assembly.py`
- Test: `tests/test_assembly.py`

**Interfaces:**
- Consumes: every part's `make` and `place`; `layout.validate_bays`, `pier_xs`, `post_us`, `rib_low`, `segments`.
- Produces: `assembly.placed_parts(p, bays) -> list[tuple[str, Part]]` (names such as `bay0_room_arch_start`, `bracket0`, `ladder1`, `handrail1`), `assembly.make(p, bays) -> Compound` (labeled children), `assembly.find_clashes(items, tol=1e-3) -> list[tuple[str, str, float]]`.

- [ ] **Step 1: Write the failing test**

`tests/test_assembly.py`:

```python
from dataclasses import replace

import pytest

from hotrain import assembly
from hotrain import layout as L
from hotrain.params import INCH, P




@pytest.fixture(scope="module")
def parts():
    return dict(assembly.placed_parts(P, [16 * INCH]))


def test_part_count(parts):
    posts = len(L.post_us(P, 16 * INCH))
    segs = len(L.segments(P, [16 * INCH]))
    assert len(parts) == 4 + 2 + 2 * posts + 2 + 4 + 2 * segs


def test_arch_halves_sit_under_rails(parts):
    for y in P.rail_ys:
        s = "room" if y > 0 else "wall"
        a = parts[f"bay0_{s}_arch_start"].bounding_box()
        b = parts[f"bay0_{s}_arch_end"].bounding_box()
        assert a.min.X == pytest.approx(0, abs=1e-6) and a.max.X == pytest.approx(8 * INCH)
        assert b.min.X == pytest.approx(8 * INCH) and b.max.X == pytest.approx(16 * INCH)
        for bb in (a, b):
            assert (bb.min.Y + bb.max.Y) / 2 == pytest.approx(y)
            assert bb.min.Z == pytest.approx(-P.pier_depth)


def test_bracket_flange_on_wall_and_top_under_ties(parts):
    bb = parts["bracket0"].bounding_box()
    assert bb.min.Y == pytest.approx(-P.track_offset)
    assert bb.max.Z == pytest.approx(0, abs=1e-6)
    assert bb.min.X == pytest.approx(-P.bracket_t / 2)


def test_handrail_on_room_side(parts):
    bb = parts["handrail1"].bounding_box()
    assert (bb.min.Y + bb.max.Y) / 2 == pytest.approx(P.handrail_offset)
    assert bb.max.Z == pytest.approx(P.rail_top + P.handrail_h)


@pytest.mark.parametrize("p,bays", [
    (P, [16 * INCH]),
    (P, [16 * INCH, 14 * INCH, P.max_bay_len]),
    (P, [P.min_bay_len]),
    (replace(P, fit_slide=0.3, fit_snap=0.1, rail_base_w=2.4), [16 * INCH]),  # after a fit-test retune
])
def test_no_interference(p, bays):
    assert assembly.find_clashes(assembly.placed_parts(p, bays)) == []


def test_placed_parts_rejects_bad_bays():
    with pytest.raises(ValueError):
        assembly.placed_parts(P, [600.0])


def test_clash_check_catches_tight_fits():
    tight = replace(P, fit_slide=-0.3)  # slots narrower than the panels
    clashes = assembly.find_clashes(assembly.placed_parts(tight, [16 * INCH]))
    names = {n for pair in clashes for n in pair[:2]}
    assert any(n.startswith("bracket") for n in names)
    assert any("cross_frame" in n for n in names)
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `uv run pytest tests/test_assembly.py -v`
Expected: FAIL with `ImportError: cannot import name 'assembly'`

- [ ] **Step 3: Write `hotrain/assembly.py`**

```python
"""Every part of a run placed where it goes, for Onshape review and interference checks."""
import itertools

from build123d import Compound, Part

from hotrain import layout as L
from hotrain.params import P, Params
from hotrain.parts import arch_half, bracket, cross_frame, end_pier, handrail, keystone, tie_ladder


def side(y: float) -> str:
    return "room" if y > 0 else "wall"


def placed_parts(p: Params = P, bays: list[float] = L.BAYS) -> list[tuple[str, Part]]:
    L.validate_bays(p, bays)
    out: list[tuple[str, Part]] = []
    xs = L.pier_xs(bays)
    key = keystone.make(p)
    for i, (x0, b) in enumerate(zip(xs, bays)):
        half = arch_half.make(p, b)
        for y in p.rail_ys:
            out.append((f"bay{i}_{side(y)}_arch_start", arch_half.place(p, x0, b, y, end=False) * half))
            out.append((f"bay{i}_{side(y)}_arch_end", arch_half.place(p, x0, b, y, end=True) * half))
            out.append((f"bay{i}_{side(y)}_keystone", keystone.place(p, x0 + b / 2, y) * key))
        for k, u in enumerate(L.post_us(p, b)):
            d = -L.rib_low(p, b, u)
            cf = cross_frame.make(p, d)
            out.append((f"bay{i}_cross_frame_a{k}", cross_frame.place(p, x0 + u, d) * cf))
            out.append((f"bay{i}_cross_frame_b{k}", cross_frame.place(p, x0 + b - u, d) * cf))
    br = bracket.make(p)
    for i, x in enumerate(xs):
        out.append((f"bracket{i}", bracket.place(p, x) * br))
    ep = end_pier.make(p)
    for y in p.rail_ys:
        out.append((f"end_pier_start_{side(y)}", end_pier.place(p, xs[0], y, run_start=True) * ep))
        out.append((f"end_pier_end_{side(y)}", end_pier.place(p, xs[-1], y, run_start=False) * ep))
    for k, seg in enumerate(L.segments(p, bays)):
        out.append((f"ladder{k}", tie_ladder.place(p, seg) * tie_ladder.make(p, bays, seg)))
        hr = handrail.make(p, bays, seg)
        if hr is not None:
            out.append((f"handrail{k}", handrail.place(p, seg) * hr))
    return out


def make(p: Params = P, bays: list[float] = L.BAYS) -> Compound:
    children = []
    for name, part in placed_parts(p, bays):
        part.label = name
        children.append(part)
    return Compound(children=children, label="run")


def _boxes_overlap(a, b) -> bool:
    lo_a, hi_a, lo_b, hi_b = a.min, a.max, b.min, b.max
    return (lo_a.X < hi_b.X and lo_b.X < hi_a.X and lo_a.Y < hi_b.Y and lo_b.Y < hi_a.Y
            and lo_a.Z < hi_b.Z and lo_b.Z < hi_a.Z)


def find_clashes(items: list[tuple[str, Part]], tol: float = 1e-3) -> list[tuple[str, str, float]]:
    """Pairs of parts sharing more than tol mm^3 of volume. Touching faces don't count."""
    boxes = [(n, s, s.bounding_box()) for n, s in items]
    out = []
    for (na, a, ba), (nb, b, bb) in itertools.combinations(boxes, 2):
        if _boxes_overlap(ba, bb):
            v = (a & b).volume
            if v > tol:
                out.append((na, nb, round(v, 4)))
    return out
```

- [ ] **Step 4: Run the test and confirm it passes**

Run: `uv run pytest tests/test_assembly.py -v`
Expected: all PASS

- [ ] **Step 5: Run the whole suite**

Run: `uv run pytest -q`
Expected: all PASS (about 50 tests, roughly 80 s; the interference tests are the slow ones)

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: run assembly and interference check

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 10: Build CLI

**Files:**
- Create: `hotrain/build.py`
- Test: `tests/test_build.py`

**Interfaces:**
- Consumes: `assembly.make`, `assembly.placed_parts`, `assembly.find_clashes`, every part's `make`, `layout.BAYS`, `validate_bays`, `post_us`, `rib_low`, `segments`.
- Produces: `build.main(argv) -> int` with commands `all | parts | assembly | fit-test | check` and options `--out`, `--mesh`, `--preview`; `build.part_list(p, bays) -> list[(name, part, qty, note)]`; `build.write_svg(shape, path, view)`. Writes `out/step/*.step`, `out/manifest.csv`, plus `out/stl/*.stl` and `out/preview/*.svg` when asked.

- [ ] **Step 1: Write the failing test**

`tests/test_build.py`:

```python
import csv

from hotrain import build
from hotrain import layout as L
from hotrain.params import P


def read_manifest(out):
    with open(out / "manifest.csv") as f:
        return {r["file"]: int(r["quantity"]) for r in csv.DictReader(f)}


def test_parts_writes_step_per_part_and_manifest(tmp_path):
    assert build.main(["parts", "--out", str(tmp_path)]) == 0
    m = read_manifest(tmp_path)
    nb = len(L.BAYS)
    assert m["step/bracket.step"] == nb + 1
    assert m["step/keystone.step"] == 2 * nb
    assert m["step/end_pier.step"] == 4
    assert sum(q for f, q in m.items() if "arch_half" in f) == 4 * nb
    assert sum(1 for f in m if "ladder_" in f) == len(L.segments(P, L.BAYS))
    for f in m:
        text = (tmp_path / f).read_text()[:200]
        assert text.startswith("ISO-10303-21"), f


def test_fit_test_and_previews(tmp_path):
    assert build.main(["fit-test", "--out", str(tmp_path), "--preview", "--mesh"]) == 0
    assert (tmp_path / "step" / "fit_test.step").stat().st_size > 1000
    assert (tmp_path / "stl" / "fit_test.stl").stat().st_size > 1000
    assert "<svg" in (tmp_path / "preview" / "fit_test.svg").read_text()[:500]


def test_check_reports_clean_run(capsys):
    assert build.main(["check"]) == 0
    assert "no clashes" in capsys.readouterr().out


def test_assembly_step_carries_part_names(tmp_path):
    assert build.main(["assembly", "--out", str(tmp_path)]) == 0
    text = (tmp_path / "step" / "run_assembly.step").read_text()
    assert "bay0_room_arch_start" in text and "bracket0" in text
    assert "SI_UNIT(.MILLI.,.METRE.)" in text
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `uv run pytest tests/test_build.py -v`
Expected: FAIL with `ImportError: cannot import name 'build'`

- [ ] **Step 3: Write `hotrain/build.py`**

```python
"""Command line: export STEP files (and optional STL / SVG previews) for the run in layout.BAYS.

    uv run python -m hotrain.build all          # parts + assembly + fit test
    uv run python -m hotrain.build parts        # one STEP per distinct part + out/manifest.csv
    uv run python -m hotrain.build assembly     # out/step/run_assembly.step
    uv run python -m hotrain.build fit-test     # out/step/fit_test.step
    uv run python -m hotrain.build check        # interference check, exit 1 on any clash
Options: --out DIR (default out), --mesh (also STL), --preview (also SVG line drawings)
"""
import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

from build123d import ExportSVG, LineType, Shape, export_step, export_stl

from hotrain import assembly
from hotrain import layout as L
from hotrain.params import P, Params
from hotrain.parts import arch_half, bracket, cross_frame, end_pier, fit_test, handrail, keystone, tie_ladder

TOP = ((0, 0, 1), (0, 1, 0))  # (view direction toward the eye, up) for flat parts
FROM_ROOM = ((0, 1, 0), (0, 0, 1))  # assembly seen from the room


def write_svg(shape: Shape, path: Path, view: tuple) -> None:
    direction, up = view
    bb = shape.bounding_box()
    c = bb.center()
    dist = 10 * max(bb.size.X, bb.size.Y, bb.size.Z)
    origin = (c.X + direction[0] * dist, c.Y + direction[1] * dist, c.Z + direction[2] * dist)
    visible, hidden = shape.project_to_viewport(origin, viewport_up=up, look_at=(c.X, c.Y, c.Z))
    span = max(bb.size.X, bb.size.Y, bb.size.Z)
    exp = ExportSVG(scale=800 / span)
    exp.add_layer("visible")
    exp.add_layer("hidden", line_color=(0.63, 0.63, 0.63), line_type=LineType.ISO_DOT)
    exp.add_shape(visible, layer="visible")
    exp.add_shape(hidden, layer="hidden")
    path.parent.mkdir(parents=True, exist_ok=True)
    exp.write(str(path))


def export(shape: Shape, out: Path, name: str, mesh: bool, preview: bool, view: tuple = TOP) -> Path:
    step = out / "step" / f"{name}.step"
    step.parent.mkdir(parents=True, exist_ok=True)
    export_step(shape, str(step))
    if mesh:
        stl = out / "stl" / f"{name}.stl"
        stl.parent.mkdir(parents=True, exist_ok=True)
        export_stl(shape, str(stl))
    if preview:
        write_svg(shape, out / "preview" / f"{name}.svg", view)
    return step


def part_list(p: Params, bays: list[float]) -> list[tuple[str, Shape, int, str]]:
    """(name, part, quantity, note) for every distinct printable part in the run."""
    rows = []
    for b, n in sorted(Counter(round(b, 3) for b in bays).items()):
        tag = f"{b:.1f}mm"
        rows.append((f"arch_half_{tag}", arch_half.make(p, b), 4 * n, f"{n} bay(s) of {b:.1f} mm; 2 panels x 2 halves"))
        for k, u in enumerate(L.post_us(p, b)):
            d = -L.rib_low(p, b, u)
            rows.append((f"cross_frame_{tag}_{k}", cross_frame.make(p, d), 2 * n, f"post {k + 1} from each pier"))
    rows.append(("keystone", keystone.make(p), 2 * len(bays), "one per panel per bay"))
    rows.append(("bracket", bracket.make(p), len(bays) + 1, "one per pier"))
    rows.append(("end_pier", end_pier.make(p), 4, "two per run end"))
    for k, seg in enumerate(L.segments(p, bays)):
        rows.append((f"ladder_{k:02d}", tie_ladder.make(p, bays, seg), 1,
                     f"x {seg.x_start:.1f} to {seg.x_end:.1f} mm"))
        hr = handrail.make(p, bays, seg)
        if hr is not None:
            rows.append((f"handrail_{k:02d}", hr, 1, f"above ladder_{k:02d}"))
    return rows


def cmd_parts(p: Params, bays: list[float], out: Path, mesh: bool, preview: bool) -> None:
    rows = part_list(p, bays)
    for name, shape, _, _ in rows:
        export(shape, out, name, mesh, preview)
    with open(out / "manifest.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["file", "quantity", "note"])
        for name, _, qty, note in rows:
            w.writerow([f"step/{name}.step", qty, note])


def cmd_assembly(p: Params, bays: list[float], out: Path, mesh: bool, preview: bool) -> None:
    export(assembly.make(p, bays), out, "run_assembly", mesh, preview, FROM_ROOM)


def cmd_fit_test(p: Params, out: Path, mesh: bool, preview: bool) -> None:
    export(fit_test.make(p), out, "fit_test", mesh, preview)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="hotrain.build", description=__doc__.splitlines()[0])
    ap.add_argument("command", choices=["all", "parts", "assembly", "fit-test", "check"])
    ap.add_argument("--out", default="out")
    ap.add_argument("--mesh", action="store_true")
    ap.add_argument("--preview", action="store_true")
    a = ap.parse_args(argv)
    out, p, bays = Path(a.out), P, L.BAYS
    L.validate_bays(p, bays)
    out.mkdir(parents=True, exist_ok=True)
    if a.command == "check":
        clashes = assembly.find_clashes(assembly.placed_parts(p, bays))
        for na, nb, v in clashes:
            print(f"CLASH {na} x {nb}: {v} mm^3")
        print("no clashes" if not clashes else f"{len(clashes)} clash(es)")
        return 1 if clashes else 0
    if a.command in ("all", "parts"):
        cmd_parts(p, bays, out, a.mesh, a.preview)
    if a.command in ("all", "assembly"):
        cmd_assembly(p, bays, out, a.mesh, a.preview)
    if a.command in ("all", "fit-test"):
        cmd_fit_test(p, out, a.mesh, a.preview)
    print(f"wrote {out}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the test and confirm it passes**

Run: `uv run pytest tests/test_build.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: build CLI exporting STEP, manifest and previews

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 11: Generate the parts and review them

**Files:** none committed (`out/` is gitignored).

**Interfaces:**
- Consumes: `python -m hotrain.build`.

- [ ] **Step 1: Run the full suite**

Run: `uv run pytest -q`
Expected: all PASS

- [ ] **Step 2: Build everything with previews**

Run: `uv run python -m hotrain.build all --preview && uv run python -m hotrain.build check`
Expected: `wrote out/` then `no clashes`. `out/step/` holds `arch_half_406.4mm`, `cross_frame_406.4mm_0..2`, `keystone`, `bracket`, `end_pier`, `ladder_00..02`, `handrail_00..02`, `fit_test` and `run_assembly`.

- [ ] **Step 3: Render the previews and look at them**

Run: `for f in out/preview/*.svg; do rsvg-convert -b white -w 1400 "$f" -o "${f%.svg}.png"; done`
Check: `run_assembly.png` (seen from the room) shows piers, three posts per half, the arch rising to the keystone, ties and handrail on top. `bracket.png` shows the flange, triangulated arm, two pier slots and the latch finger. `fit_test.png` shows 11 pieces with no overlaps.

- [ ] **Step 4: Hand off to the user**

Tell the user:
1. Import `out/step/run_assembly.step` into Onshape to review the whole bay, and the individual `.step` files to print.
2. Print `fit_test.step` first (PETG, 0.2 mm layers, no supports). Then report which groove, slot and keystone variant fits best, and whether the latch clicks.
3. Measure the real stud-to-stud distances and put them in `hotrain/layout.py` `BAYS` before printing a full run.
