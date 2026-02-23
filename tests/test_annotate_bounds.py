from types import SimpleNamespace

import pytest


def test_annotate_fingers_xml_handles_short_hand_sequence() -> None:
    music21 = pytest.importorskip("music21")

    from pianoplayer.core import annotate_fingers_xml

    score = music21.converter.parse("scores/test_scales.xml")

    # Deliberately shorter than the note stream to verify no IndexError is raised.
    short_hand = SimpleNamespace(
        noteseq=[SimpleNamespace(fingering=1)],
        lyrics=False,
    )
    args = SimpleNamespace(rbeam=0, lbeam=1)

    annotate_fingers_xml(score, short_hand, args, is_right=True)
