import pytest

import web.main as web


@pytest.mark.parametrize("tone", [1, 2, 3, 4, 5])
def test_badge_shows_number_and_class_for_each_tone(tone):
    badge = web.tone_badge(tone)
    assert f"tone-{tone}" in badge
    assert f">{tone}<" in badge


def test_badge_for_missing_tone_is_grey_dash():
    badge = web.tone_badge(None)
    assert "tone-none" in badge
    assert ">—<" in badge


def test_badge_for_out_of_range_tone_is_treated_as_missing():
    assert "tone-none" in web.tone_badge(9)
