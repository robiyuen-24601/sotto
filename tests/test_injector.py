from unittest.mock import Mock, call

from sotto.injector import Injector


def make():
    parent = Mock()
    clipboard = parent.clipboard
    clipboard.read.return_value = "OLD"
    inj = Injector(
        clipboard=clipboard,
        paste_fn=parent.paste,
        sleep_fn=parent.sleep,
    )
    return parent, inj


def test_inject_sequence_order():
    parent, inj = make()
    inj.inject("NEW TEXT")
    assert parent.mock_calls == [
        call.clipboard.read(),
        call.clipboard.write("NEW TEXT"),
        call.sleep(Injector.PRE_PASTE_DELAY),
        call.paste(),
        call.sleep(Injector.RESTORE_DELAY),
        call.clipboard.write("OLD"),
    ]


def test_no_restore_when_old_clipboard_empty():
    parent, inj = make()
    parent.clipboard.read.return_value = None
    inj.inject("NEW TEXT")
    write_calls = [c for c in parent.mock_calls if c[0] == "clipboard.write"]
    assert write_calls == [call.clipboard.write("NEW TEXT")]


def test_empty_text_is_a_noop():
    parent, inj = make()
    inj.inject("   ")
    assert parent.mock_calls == []
