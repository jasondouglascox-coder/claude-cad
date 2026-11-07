"""uv run python -m speaker_shelf.build [--out out]: STEP for CAD, the fit-coupon plate for your slicer (opens black
in Bambu Studio), and a shaded preview in out/render/fit_coupon.png."""
import argparse
import sys
from pathlib import Path

from build123d import Color, export_step

from cadkit.export import write_plates
from cadkit.plates import Plate, pack
from cadkit.render import render
from speaker_shelf.assembly import rail_boxes, speaker_box
from speaker_shelf.parts import gap_gauge, rail_fork, shelf, shelf_body
from speaker_shelf.params import P

SHOWN = Color(0.18, 0.18, 0.18)  # black filament, lifted enough to see the shading


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="speaker_shelf.build")
    ap.add_argument("--out", default="out")
    out = Path(ap.parse_args(argv).out)
    fork, gauge, sh = rail_fork(P), gap_gauge(P), shelf(P)
    (out / "step").mkdir(parents=True, exist_ok=True)
    for part in (fork, gauge, sh):
        export_step(part, out / "step" / f"{part.label}.step")
    beds = pack([("rail_fork", fork), ("gap_gauge", gauge)], P.printer)
    assert len(beds) == 1, "the coupon fits one plate"
    shelf_bed = pack([("speaker_shelf", sh)], P.printer)
    write_plates([Plate("fit_coupon", 1, beds[0]), Plate("speaker_shelf", 1, shelf_bed[0])], out / "plates",
                 out / "plates.csv", lambda name: P.filament_black)
    rail, speaker = Color(0.62, 0.62, 0.64), Color(0.80, 0.80, 0.78)
    scene = [(shelf_body(P), SHOWN)] + [(b, rail) for _, b in rail_boxes(P)]
    render(scene, out / "render" / "shelf_on_rails.png", view=(0.6, -1, 0.8), px=900, crop=True)
    render(scene + [(speaker_box(P), speaker)], out / "render" / "with_speaker.png", view=(0.6, -1, 0.8), px=900,
           crop=True)
    render([(sh, SHOWN)], out / "render" / "shelf_top.png", view=(0, 0, 1), px=900, crop=True)
    render([(s, SHOWN) for _, s in beds[0]],
           out / "render" / "fit_coupon.png", view=(0.4, -1, 1.2), px=800, crop=True)
    print(f"wrote {out}/ (plates.csv lists what to print)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
