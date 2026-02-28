from types import SimpleNamespace

from pianoplayer import core


def test_core_annotate_writes_output(tmp_path) -> None:
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


def test_core_warns_and_clamps_depth(caplog) -> None:
    args = SimpleNamespace(depth=12)
    caplog.set_level("WARNING")
    core._normalize_requested_depth(args)
    assert args.depth == 9
    assert "above max 9" in caplog.text


def test_core_logs_detected_anchors(caplog) -> None:
    args = SimpleNamespace(left_only=False, right_only=False)
    caplog.set_level("INFO")
    rh = [SimpleNamespace(fingering=1), SimpleNamespace(fingering=0)]
    lh = [SimpleNamespace(fingering=2), SimpleNamespace(fingering=-3)]
    core._log_anchored_fingers(rh, lh, args)
    assert "Detected pre-annotated fingers" in caplog.text
