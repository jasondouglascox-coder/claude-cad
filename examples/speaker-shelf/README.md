# speaker-shelf

A little black shelf that clips onto two banister rails (about 12.4 mm square tubes, 86 mm apart) and holds a vertical
speaker (base 83 × 75 mm) centered on them both ways: its middle sits between the rails, which are its side walls
there. No hardware: the clips squeeze each rail front to back (12.3 mm jaws), with about 1 mm of side play.

<img src="docs/images/with_speaker.png" width="49%" alt="shelf on two rails with the speaker"> <img src="docs/images/shelf_on_rails.png" width="49%" alt="shelf clipped on two rails">

Print `out/plates/speaker_shelf.3mf` (black, no supports). Push it onto the rails from the front: each hook rides
over its rail and snaps behind it. Then set the speaker in. To take it off, pull the little tab at the back of each arm outward.

<img src="docs/images/fit_coupon.png" width="49%" alt="fit coupon: rail fork and gap gauge">

**The fit coupon** (`out/plates/fit_coupon.3mf`) set the sizes:

- **Rail fork:** push each slot onto a rail. Note the narrowest slot that slides on, and the one that's snug.
- **Gap gauge:** push the narrow end (84) between two rails. Note the label of the deepest step that goes in.

Those two numbers are in `docs/measurements.md` and `params.py` (`rail`, `rail_gap`).

```bash
uv sync
uv run pytest -n 6                        # print checks, dimensions, the plate through Bambu Studio
uv run python -m speaker_shelf.build      # out/plates (open in Bambu Studio), out/step, out/render
```

The pictures in `docs/images/` are copies of `out/render/`; refresh them after a visible change.
