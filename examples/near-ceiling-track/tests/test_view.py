import pytest

from hotrain import view
from hotrain.params import P


@pytest.mark.parametrize("name", ["run", "inside", "bridge", "fit-test"])
def test_targets_resolve_to_colored_models(name):
    m = view.target(P, name)
    kids = list(m.children) if hasattr(m, "children") else [m]
    assert kids
    assert all(getattr(k, "color", None) is not None for k in kids)


def test_unknown_target_lists_choices():
    with pytest.raises(ValueError, match="room"):
        view.target(P, "nope")
