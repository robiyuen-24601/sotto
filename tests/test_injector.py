from unittest.mock import Mock, call

import pytest

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


def test_no_restore_when_old_clipboard_absent():
    """read() returning None means clipboard is absent; do not restore."""
    parent, inj = make()
    parent.clipboard.read.return_value = None
    inj.inject("NEW TEXT")
    write_calls = [c for c in parent.mock_calls if c[0] == "clipboard.write"]
    assert write_calls == [call.clipboard.write("NEW TEXT")]


def test_restore_when_old_clipboard_is_empty_string():
    """read() returning "" (empty string, not None) should still be restored."""
    parent, inj = make()
    parent.clipboard.read.return_value = ""
    inj.inject("NEW TEXT")
    write_calls = [c for c in parent.mock_calls if c[0] == "clipboard.write"]
    assert write_calls == [
        call.clipboard.write("NEW TEXT"),
        call.clipboard.write(""),
    ]


def test_empty_text_is_a_noop():
    parent, inj = make()
    inj.inject("   ")
    assert parent.mock_calls == []


def test_paste_fn_raising_still_restores_clipboard():
    """If paste_fn raises, the try/finally still restores the clipboard."""
    parent, inj = make()
    parent.paste.side_effect = RuntimeError("boom")
    with pytest.raises(RuntimeError):
        inj.inject("NEW TEXT")
    # Last call should be the restore of the original clipboard.
    assert parent.mock_calls[-1] == call.clipboard.write("OLD")
