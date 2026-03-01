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
        rbeam=0,
        lbeam=1,
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
        rbeam=0,
        lbeam=1,
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


def test_core_limited_measures_do_not_write_zero_fingering(tmp_path) -> None:
    output = tmp_path / "annotated_limited.xml"
    args = SimpleNamespace(
        filename="scores/test_scales.xml",
        outputfile=str(output),
        n_measures=10,
        start_measure=1,
        depth=0,
        rbeam=0,
        lbeam=1,
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
