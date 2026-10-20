"""uv run python -m refill_spool.build [--out out]: STEP for CAD, out/plates/refill_spool.3mf (one Bambu Studio
project, a plate per half; each plate also on its own), out/view/refill_spool_assembled.3mf (to look at, not print:
screwed together, and strapping a coil with the cap off), and shaded previews in out/render (iso.png: the halves
apart; top.png: the barrel half from above; cap.png: the cap as printed, spigot up)."""
import argparse
import sys
from pathlib import Path

from build123d import Align, Box, Color, Pos, export_step

from cadkit import bambu3mf

from cadkit.export import write_plates
from cadkit.plates import Plate, pack
from cadkit.render import render
from refill_spool.assembly import coil, placed_parts, strap_paths
from refill_spool.params import P
from refill_spool.parts import barrel_half, cap

GRAY, STRAP = Color(0.55, 0.57, 0.6), Color(0.9, 0.5, 0.15)


VIEW_COLORS = [("PLA", "#E8E8E8"), ("PLA", "#C8A165"), ("PLA", "#7A8088"), ("PLA", "#F28C28")]  # cap, coil, barrel, straps


def write_view(path: Path) -> None:
    """A Bambu project to look at, not print: screwed together, then strapping with the cap off over a coil cut in
    half (one strap under the coil, one in the open, one on the cut). Each plate is one object of colored parts, so
    nothing drops to the bed on its own."""
    (_, barrel), (_, cap_on) = placed_parts(P)
    at = Pos(P.rim_d / 2 + P.printer.margin, P.rim_d / 2 + P.printer.margin, 0)
    half = coil(P) & Pos(0, -P.rim_d, -1) * Box(P.rim_d, 2 * P.rim_d, P.width + 2, align=(Align.MIN,) * 3)
    straps = [(f"strap {k + 1}", at * s, 4) for k, s in enumerate(strap_paths(P))]
    path.parent.mkdir(parents=True, exist_ok=True)
    settings = bambu3mf.write_settings(path.with_suffix(".config"), VIEW_COLORS)
    bambu3mf.write_plates_project(path, [
        ("screwed together", [("spool", [("barrel_half", at * barrel, 3), ("cap", at * cap_on, 1)])]),
        ("strapping, cap off", [("strapping", [("barrel_half", at * barrel, 3), ("coil (cut in half)", at * half, 2)]
                                 + straps)])], settings)
    settings.unlink()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="refill_spool.build")
    ap.add_argument("--out", default="out")
    out = Path(ap.parse_args(argv).out)
    parts = [("barrel_half", barrel_half(P)), ("cap", cap(P))]
    (out / "step").mkdir(parents=True, exist_ok=True)
    for name, part in parts:
        export_step(part, out / "step" / f"{name}.step")
    plates = [Plate(name, 1, items) for name, part in parts for items in pack([(name, part)], P.printer)]
    write_plates(plates, out / "plates", out / "plates.csv", lambda name: P.filament, combined="refill_spool")
    write_view(out / "view" / "refill_spool_assembled.3mf")
    (_, b), (_, c) = placed_parts(P)
    apart = Pos(0, 0, 40) * c  # lifted off so the thread shows
    render([(b, GRAY), (apart, GRAY)] + [(s, STRAP) for s in strap_paths(P)[:1]], out / "render" / "iso.png",
           view=(0.6, -1, 0.7), px=900)
    render([(b, GRAY)], out / "render" / "top.png", view=(0, 0, 1), px=900)
    render([(cap(P), GRAY)], out / "render" / "cap.png", view=(0.6, -1, 0.8), px=900)
    print(f"wrote {out}/ (open plates/refill_spool.3mf in Bambu Studio: a plate per half)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
