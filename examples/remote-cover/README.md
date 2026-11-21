# HEXBUG remote battery cover

<img src="docs/images/iso.png" width="60%" alt="Battery cover: a 25 x 15 mm plate with a round-ended ear, a plug under the ear and two tabs on the bottom edge">

A replacement for the lost battery cover on a HEXBUG remote, printed in gray PETG. The plate is 25 × 15 × 1.6 mm,
with a round-ended screw ear on top and two tabs on the bottom edge that hook under the pocket's lip. The screw was
lost too, so a round plug under the ear presses into the circular indent round the remote's brass screw insert. The
hole through the ear still takes an M1.4 screw (an eyeglass screw) if one turns up.

The plug's size is a guess (about 5 mm), so the plate prints five covers with plugs from 4.8 to 5.2 mm, each
engraved on its inside face ("48" ... "52"). Keep the one that presses in snug and set it in `params.py`.
Sizes in `remote_cover/params.py`; decisions in `docs/specs/remote-cover.md`.

```bash
uv sync
uv run pytest -n 6                     # printable, sizes, the plate file, and a Bambu Studio slice (~15 s)
uv run python -m remote_cover.build    # out/plates/remote_cover.3mf (gray PETG, AMS slot 1), out/step, out/render
```

The picture in `docs/images/` is a copy of `out/render/iso.png`; refresh it after a visible change.
