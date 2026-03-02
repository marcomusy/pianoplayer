import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace
from zipfile import ZipFile

from pianoplayer import core


def test_core_annotate_writes_output(tmp_path) -> None:
    output = tmp_path / "annotated.xml"
    args = SimpleNamespace(
        filename="scores/test_scales.xml",
        outputfile=str(output),
        n_measures=2,
        start_measure=1,
        depth=0,
        rpart=0,
        lpart=1,
        quiet=True,
        musescore=False,
        below_beam=False,
        with_vedo=False,
        sound_off=True,
        left_only=False,
        right_only=False,
        hand_size="M",
        cost_path=None,
    )
    core.annotate(args)
    assert output.exists()


def test_core_annotate_reads_mxl_input(tmp_path) -> None:
    source_xml = Path("scores/test_scales.xml")
    mxl = tmp_path / "test_scales.mxl"
    with ZipFile(mxl, "w") as zf:
        zf.writestr(
            "META-INF/container.xml",
            (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
                "<rootfiles>"
                '<rootfile full-path="score.xml" '
                'media-type="application/vnd.recordare.musicxml+xml"/>'
                "</rootfiles>"
                "</container>"
            ),
        )
        zf.write(source_xml, arcname="score.xml")

    output = tmp_path / "annotated_from_mxl.xml"
    args = SimpleNamespace(
        filename=str(mxl),
        outputfile=str(output),
        n_measures=2,
        start_measure=1,
        depth=0,
        rpart=0,
        lpart=1,
        quiet=True,
        musescore=False,
        below_beam=False,
        with_vedo=False,
        sound_off=True,
        left_only=False,
        right_only=False,
        hand_size="M",
        cost_path=None,
    )
    core.annotate(args)
    assert output.exists()


def test_core_warns_and_clamps_depth(caplog) -> None:
    args = SimpleNamespace(
        filename="scores/test_scales.xml",
        outputfile=None,
        n_measures=1,
        start_measure=1,
        depth=12,
        rpart=0,
        lpart=1,
        quiet=True,
        musescore=False,
        below_beam=False,
        with_vedo=False,
        sound_off=True,
        left_only=False,
        right_only=False,
        hand_size="M",
        chord_note_stagger_s=0.05,
        cost_path=None,
    )
    caplog.set_level("WARNING")
    core.annotate(args)
    assert "above max 9" in caplog.text


def test_core_logs_detected_anchors(caplog) -> None:
    args = SimpleNamespace(
        filename="scores/test_scales_all_keys.xml",
        outputfile=None,
        n_measures=1,
        start_measure=1,
        depth=0,
        rpart=0,
        lpart=1,
        quiet=True,
        musescore=False,
        below_beam=False,
        with_vedo=False,
        sound_off=True,
        left_only=False,
        right_only=False,
        hand_size="M",
        chord_note_stagger_s=0.05,
        cost_path=None,
    )
    caplog.set_level("INFO")
    core.annotate(args)
    assert "Detected pre-annotated fingers" in caplog.text


def test_core_limited_measures_do_not_write_zero_fingering(tmp_path) -> None:
    output = tmp_path / "annotated_limited.xml"
    args = SimpleNamespace(
        filename="scores/test_scales.xml",
        outputfile=str(output),
        n_measures=10,
        start_measure=1,
        depth=0,
        rpart=0,
        lpart=1,
        quiet=True,
        musescore=False,
        below_beam=False,
        with_vedo=False,
        sound_off=True,
        left_only=False,
        right_only=False,
        hand_size="M",
        cost_path=None,
    )
    core.annotate(args)
    root = ET.parse(output).getroot()
    fingerings = root.findall(".//fingering")
    assert fingerings
    assert all((f.text or "").strip() != "0" for f in fingerings)
