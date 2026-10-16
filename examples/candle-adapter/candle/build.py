"""uv run python -m candle.build [--out out]: STEP for CAD, a Bambu Studio plate that opens black."""
import argparse
import sys
from pathlib import Path

from build123d import export_step

from cadkit.export import write_plates
from cadkit.plates import Plate, pack
from candle.params import P
from candle.parts import adapter


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="candle.build")
    ap.add_argument("--out", default="out")
    out = Path(ap.parse_args(argv).out)
    a = adapter(P)
    step = out / "step" / "candle_adapter.step"
    step.parent.mkdir(parents=True, exist_ok=True)
    export_step(a, step)
    beds = pack([("candle_adapter", a)], P.printer)
    write_plates([Plate(f"candle_adapter_{n + 1}", 1, items) for n, items in enumerate(beds)], out / "plates",
                 out / "plates.csv", lambda name: P.filament_black)
    print(f"wrote {out}/ (plates.csv lists what to print)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
