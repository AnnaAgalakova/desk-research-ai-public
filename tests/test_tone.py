import worker.main as worker


def test_parse_tone_accepts_1_to_5():
    for value in (1, 2, 3, 4, 5):
        assert worker.parse_tone(value) == value


def test_parse_tone_accepts_digit_string():
    assert worker.parse_tone("4") == 4


def test_parse_tone_rejects_out_of_range_and_garbage():
    for value in (0, 6, -1, "7", "много", None, 3.5, True):
        assert worker.parse_tone(value) is None


def test_prompt_v2_asks_for_tone():
    assert worker.PROMPT_VERSION == "v2"
    assert '"tone"' in worker.PROMPT
