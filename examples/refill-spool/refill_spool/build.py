"""uv run python -m refill_spool.build [--out out]: STEP for CAD, one Bambu Studio plate per half, and shaded
previews in out/render (iso.png: the halves apart over the coil's place; top.png: the barrel half from
above; cap.png: the cap as printed, spigot and lip up)."""
import argparse
import sys
from pathlib import Path

from build123d import Color, Pos, export_step

from cadkit.export import write_plates
from cadkit.plates import Plate, pack
from cadkit.render import render
from refill_spool.assembly import placed_parts, strap_paths
from refill_spool.params import P
from refill_spool.parts import barrel_half, cap

GRAY, STRAP = Color(0.55, 0.57, 0.6), Color(0.9, 0.5, 0.15)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="refill_spool.build")
    ap.add_argument("--out", default="out")
    out = Path(ap.parse_args(argv).out)
    parts = [("barrel_half", barrel_half(P)), ("cap", cap(P))]
    (out / "step").mkdir(parents=True, exist_ok=True)
    for name, part in parts:
        export_step(part, out / "step" / f"{name}.step")
    plates = [Plate(f"{name}_{n + 1}", 1, items) for name, part in parts
              for n, items in enumerate(pack([(name, part)], P.printer))]
    write_plates(plates, out / "plates", out / "plates.csv", lambda name: P.filament)
    (_, b), (_, c) = placed_parts(P)
    apart = Pos(0, 0, 40) * c  # lifted off so the thread shows
    render([(b, GRAY), (apart, GRAY)] + [(s, STRAP) for s in strap_paths(P)[:1]], out / "render" / "iso.png",
           view=(0.6, -1, 0.7), px=900)
    render([(b, GRAY)], out / "render" / "top.png", view=(0, 0, 1), px=900)
    render([(cap(P), GRAY)], out / "render" / "cap.png", view=(0.6, -1, 0.8), px=900)
    print(f"wrote {out}/ (plates.csv lists what to print)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
