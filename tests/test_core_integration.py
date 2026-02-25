from types import SimpleNamespace

import pytest


def test_core_annotate_writes_output(tmp_path) -> None:
    pytest.importorskip("music21")

    from pianoplayer import core

    output = tmp_path / "annotated.xml"
    args = SimpleNamespace(
        filename="scores/test_scales.xml",
        outputfile=str(output),
        n_measures=2,
        start_measure=1,
        depth=0,
        rbeam=0,
        lbeam=1,
        quiet=True,
        musescore=False,
        below_beam=False,
        with_vedo=False,
        vedo_speed=1.5,
        sound_off=True,
        left_only=False,
        right_only=False,
        hand_size="M",
        cost_path=None,
    )
    core.annotate(args)
    assert output.exists()
