"""CLI: uv run python -m grover.build [all|step|stl|3mf|preview]"""

import sys
import time
from pathlib import Path

from build123d import Compound, Mesher, export_step, export_stl

from . import render as R
from .model import COLORS, assembly, bodies
from .params import P

OUT = Path(__file__).resolve().parent.parent / "out"


def step():
    (OUT / "step").mkdir(parents=True, exist_ok=True)
    export_step(assembly(P), str(OUT / "step" / "grover_keychain.step"))


def stl():
    (OUT / "stl").mkdir(parents=True, exist_ok=True)
    for c, body in bodies(P).items():
        export_stl(body, str(OUT / "stl" / f"grover_{c}.stl"), tolerance=0.01, angular_tolerance=0.1)


def three_mf(path: Path | None = None) -> Path:
    path = path or OUT / "grover_keychain.3mf"
    path.parent.mkdir(parents=True, exist_ok=True)
    m = Mesher()
    for c in COLORS:
        m.add_shape(bodies(P)[c], linear_deflection=0.01, angular_deflection=0.1)
    m.write(str(path))
    return path


def preview():
    (OUT / "preview").mkdir(parents=True, exist_ok=True)
    b = bodies(P)
    R.flat(b, str(OUT / "preview" / "front.png"))
    R.flat(b, str(OUT / "preview" / "back.png"), up=False)
    R.iso(b, str(OUT / "preview" / "iso.png"))
    print("QR decodes to:", R.decode_qr(str(OUT / "preview" / "back.png")))


TARGETS = {"step": step, "stl": stl, "3mf": three_mf, "preview": preview}


def main(argv):
    names = argv or ["all"]
    if names == ["all"]:
        names = list(TARGETS)
    for n in names:
        t = time.time()
        TARGETS[n]()
        print(f"{n}: {time.time() - t:.1f}s")


if __name__ == "__main__":
    main(sys.argv[1:])
