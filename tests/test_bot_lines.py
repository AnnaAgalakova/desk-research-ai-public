import pytest

import bot.main as bot

ROW = ("Тест: сводка", "OpenAI", "https://example.com/a", "Hacker News")


@pytest.mark.parametrize(
    "tone, emoji",
    [(1, "🔴"), (2, "🟠"), (3, "🟡"), (4, "🟢"), (5, "🔵")],
)
def test_line_has_tone_emoji(tone, emoji):
    (line,) = bot.finding_lines([ROW + (tone,)])
    assert line.startswith(emoji + " ") or f" {emoji} " in line


def test_line_without_tone_has_no_emoji():
    (line,) = bot.finding_lines([ROW + (None,)])
    assert not any(e in line for e in ("🔴", "🟠", "🟡", "🟢", "🔵"))
    assert "Тест: сводка" in line
