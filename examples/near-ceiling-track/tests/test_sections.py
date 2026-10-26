"""Section kits: the room printed a bay at a time. Each run (between two corners) is first / middle / last bays;
identical sections across runs are one kit with a print count. Together they print every part of every run once."""
import re
from collections import Counter
from dataclasses import replace
from functools import lru_cache

import pytest

from hotrain import plates, room
from hotrain.params import P

D = replace(P, run_style="deck_truss")


@lru_cache(maxsize=None)
def secs():
    return plates.sections(D)


def _parts(items):
    """Parts by name; a nested pair of truss halves counts as its two halves."""
    c = Counter()
    for n, sh in items:
        if n.endswith("#pair"):
            for child in sh.children:
                c[child.label] += 1
        else:
            c[re.sub(r"_\d+$", "", n.split("#")[0]) if n.startswith(("ladder", "handrail")) else n.split("#")[0]] += 1
    return c  # ladders and handrails by type: identical bays share one kit under its first bay's numbers


def test_sections_print_every_part_of_every_run_once():
    want = Counter()
    for s in room.sections(D):
        if s.kind == "run":
            for _, _, items in plates._kits(D, list(s.bays), s.ends):
                want.update(_parts(items))
    got = Counter()
    for sec in secs():
        for n, c in _parts(sec.items).items():
            got[n] += c * sec.qty
    assert got == want


def test_first_middle_last_per_bay_length():
    names = {s.name: s.qty for s in secs()}
    assert names == {"section_418mm_first": 3, "section_418mm_middle": 6, "section_418mm_last": 3,
                     "section_443mm_first": 1, "section_443mm_middle": 1, "section_443mm_last": 1}


def test_last_bay_has_no_bracket_and_first_carries_the_corner_ladder():
    by = {s.name: _parts(s.items) for s in secs()}
    assert by["section_418mm_last"]["bracket"] == 0 and by["section_418mm_middle"]["bracket"] == 1
    ladders = lambda c: sum(v for k, v in c.items() if k.startswith("ladder"))
    assert ladders(by["section_418mm_first"]) == ladders(by["section_418mm_middle"]) + 1


def test_build_writes_a_combined_project_per_section(tmp_path):
    import csv
    from cadkit import slicers
    from cadkit.bambu3mf import read_plates
    from hotrain import build
    assert build.main(["sections", "--run-style", "deck_truss", "--out", str(tmp_path)]) == 0
    d = tmp_path / "sections"
    with open(d / "sections.csv", encoding="utf-8") as f:
        rows = {r["section"]: int(r["print"]) for r in csv.DictReader(f)}
    assert rows == {s.name: s.qty for s in secs()}
    first = d / "section_418mm_first" / f"section_418mm_first{slicers.active().project_suffix}"
    assert len(read_plates(first)) >= 2


def test_section_kits_fill_the_gaps_between_parts():
    """Packed by real outlines, no kit needs more plates than by rectangles, and the kits together need fewer."""
    by_rect = {s.name: len(plates.pack(D, s.items)) for s in secs()}
    filled = {s.name: len(plates.section_plates(D, s)) for s in secs()}
    assert all(filled[n] <= by_rect[n] for n in by_rect)
    assert sum(filled.values()) < sum(by_rect.values())
