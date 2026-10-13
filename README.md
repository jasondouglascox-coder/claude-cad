# Grover & Pals keychain

4-color multi-material keychain traced from `art/logo.svg`, QR to groverandpals.com on the back.

```bash
uv run python -m grover.build all      # STEP, STLs, 3MF, previews -> out/
uv run pytest -q                        # ~3 min
```

## Printing (Bambu A1 + AMS lite)
1. Bambu Studio: select all four `out/stl/grover_*.stl` and import together; answer **Yes** to
   "load as a single object with multiple parts".
2. Assign filaments per part: orange, yellow, white, brown.
3. The model is already in print orientation: QR side down on the bed. Smooth/textured PEI both work;
   smooth plate gives the glossiest QR.
4. 0.2 mm layers (all Z steps are multiples of 0.2), 0.4 nozzle, 4 wall loops (hole strength),
   no supports, Arachne walls (default).

Tunables live in `grover/params.py` (size, zone heights, outline width, hole, QR module size).
