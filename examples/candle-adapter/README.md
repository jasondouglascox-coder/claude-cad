# Candle adapter

Hot-glue it into a flat chandelier cup; a 20 mm candle sits 15 mm deep in it. Black, one piece, no supports.
Sizes in `candle/params.py`; design in `docs/specs/candle-adapter.md`.

```bash
uv sync
uv run pytest                      # printable, sizes, the plate file, and a Bambu Studio slice if installed
uv run python -m candle.build      # out/plates/candle_adapter_1.3mf (opens black), out/step/candle_adapter.step
```
