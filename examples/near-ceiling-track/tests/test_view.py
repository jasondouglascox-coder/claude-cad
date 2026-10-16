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


def test_render_leaves_take_the_nearest_colored_ancestor():
    """build render flattens nested Compounds (room → sections → parts); uncolored parts keep the group color."""
    from build123d import Box, Color, Compound, Pos
    from hotrain.build import _leaves
    red, blue = Color(1, 0, 0), Color(0, 0, 1)
    own, bare = Box(1, 1, 1), Pos(3, 0, 0) * Box(1, 1, 1)
    own.color = blue
    inner = Compound(children=[own, bare])
    inner.color = red
    leaves = _leaves(Compound(children=[inner]))
    assert [tuple(c) for _, c in leaves] == [tuple(blue), tuple(red)]
