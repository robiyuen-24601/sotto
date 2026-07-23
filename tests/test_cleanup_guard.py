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
