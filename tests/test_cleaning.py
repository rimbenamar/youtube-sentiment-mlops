from src.utils.text_cleaning import clean_text


def test_removes_urls_and_mentions():
    out = clean_text("Check https://youtu.be/abc and www.site.com @john_doe great!")
    assert "http" not in out and "www" not in out and "john" not in out
    assert "great" in out


def test_lowercase_and_special_chars():
    assert clean_text("AMAZING!!! Video :)") == "amazing video"


def test_emojis_become_words():
    assert "love" in clean_text("❤️❤️")
    assert "sad" in clean_text("😭")


def test_keeps_negation_and_apostrophes():
    out = clean_text("I don't like it, NOT good")
    assert "don't" in out and "not" in out


def test_timestamps_and_hashtags():
    out = clean_text("at 3:45 the #docker part")
    assert "3" not in out and "docker" in out


def test_repeated_chars_and_empty():
    assert clean_text("soooooo goooood") == "soo good"
    assert clean_text(None) == ""
    assert clean_text("!!! ???") == ""


def test_very_long_text():
    out = clean_text("good " * 5000)
    assert out.startswith("good")
