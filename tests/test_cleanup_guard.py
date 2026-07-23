from sotto.cleanup import guard


def test_normal_output_is_kept():
    raw = "um so I think we should ship it tomorrow"
    cleaned = "I think we should ship it tomorrow."
    assert guard(raw, cleaned) == cleaned


def test_empty_output_falls_back():
    assert guard("ship it tomorrow", "") == "ship it tomorrow"
    assert guard("ship it tomorrow", "   ") == "ship it tomorrow"


def test_runaway_long_output_falls_back():
    raw = "a short sentence of dictation here"  # 34 chars
    cleaned = "x" * 200
    assert guard(raw, cleaned) == raw


def test_truncated_output_falls_back():
    raw = "this is a fairly long piece of dictated text with substance"
    cleaned = "ok"
    assert guard(raw, cleaned) == raw


def test_short_inputs_skip_ratio_check():
    # 4 chars raw; "Yes." to "Absolutely." is >2x but fine for tiny inputs
    assert guard("yeah", "Absolutely.") == "Absolutely."


def test_output_is_stripped():
    assert guard("hello there", "  Hello there.\n") == "Hello there."


def test_ratio_bounds_inclusive():
    # Exactly 0.5 ratio: 40 chars -> 20 chars
    raw_40 = "a" * 40
    assert guard(raw_40, "b" * 20) == "b" * 20
    # Exactly 2.0 ratio: 40 chars -> 80 chars
    assert guard(raw_40, "c" * 80) == "c" * 80


def test_ratio_min_input_chars_boundary():
    # 19 chars raw: skips ratio check, even with extreme ratio
    assert guard("a" * 19, "b" * 100) == "b" * 100
    # 20 chars raw: applies ratio check, truncated output falls back
    assert guard("a" * 20, "b" * 5) == "a" * 20


def test_surrounding_quotes_are_peeled():
    raw = "hello there friend of mine"
    cleaned = '"Hello there, friend of mine."'
    assert guard(raw, cleaned) == "Hello there, friend of mine."


def test_surrounding_curly_quotes_are_peeled():
    raw = "hello there friend of mine"
    cleaned = "“Hello there, friend of mine.”"
    assert guard(raw, cleaned) == "Hello there, friend of mine."
