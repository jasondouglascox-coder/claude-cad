"""uv run python -m remote_cover.build [--out out]: STEP for CAD, one Bambu Studio plate of the clearance ladder (opens
in gray PETG), and shaded previews in out/render/ (copy iso.png to docs/images/ after a visible change)."""
import argparse
import sys
from pathlib import Path

from build123d import Color, export_step

from cadkit import bambu3mf
from cadkit.export import write_plates
from cadkit.plates import Plate, pack
from cadkit.render import render
from remote_cover.params import P
from remote_cover.parts import cover


def name(clearance: float) -> str:
    return f"cover_gap_{clearance:.1f}".replace(".", "_")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="remote_cover.build")
    ap.add_argument("--out", default="out")
    out = Path(ap.parse_args(argv).out)
    covers = [(name(k), cover(P, k)) for k in P.clearances]
    mid = covers[len(covers) // 2][1]
    step = out / "step" / "remote_cover.step"
    step.parent.mkdir(parents=True, exist_ok=True)
    export_step(mid, step)
    (bed,) = pack(covers, P.printer)
    ams = bambu3mf.write_settings(out / "bambu_project_settings.config", list(P.filaments))
    write_plates([Plate("remote_cover", 1, bed)], out / "plates", out / "plates.csv",
                 lambda n: P.filament_gray, settings=ams)
    gray = Color(0.45, 0.46, 0.48)
    render([(mid, gray)], out / "render" / "iso.png", view=(0.4, -0.7, 1), px=600, crop=True)
    render([(mid, gray)], out / "render" / "inside.png", view=(0, 0, 1), px=600, crop=True)
    render([(mid, gray)], out / "render" / "outside.png", view=(0, 0, -1), px=600, crop=True)
    print(f"wrote {out}/ (plates.csv lists what to print)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
