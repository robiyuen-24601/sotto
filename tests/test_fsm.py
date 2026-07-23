from sotto.fsm import Action, HotkeyFSM


def make(min_hold=0.3):
    return HotkeyFSM(min_hold_seconds=min_hold)


def test_down_starts_recording():
    fsm = make()
    assert fsm.on_hotkey_down(t=10.0) == Action.START


def test_up_after_long_hold_stops():
    fsm = make()
    fsm.on_hotkey_down(t=10.0)
    assert fsm.on_hotkey_up(t=11.0) == Action.STOP


def test_up_after_short_hold_discards():
    fsm = make(min_hold=0.3)
    fsm.on_hotkey_down(t=10.0)
    assert fsm.on_hotkey_up(t=10.1) == Action.DISCARD


def test_other_key_while_holding_cancels():
    fsm = make()
    fsm.on_hotkey_down(t=10.0)
    assert fsm.on_other_key() == Action.CANCEL
    # release after a cancel does nothing
    assert fsm.on_hotkey_up(t=11.0) == Action.NONE


def test_other_key_while_idle_is_ignored():
    fsm = make()
    assert fsm.on_other_key() == Action.NONE


def test_down_while_busy_is_ignored():
    fsm = make()
    fsm.set_busy(True)
    assert fsm.on_hotkey_down(t=10.0) == Action.IGNORED_BUSY
    assert fsm.on_hotkey_up(t=11.0) == Action.NONE
    fsm.set_busy(False)
    assert fsm.on_hotkey_down(t=12.0) == Action.START


def test_up_without_down_is_ignored():
    fsm = make()
    assert fsm.on_hotkey_up(t=10.0) == Action.NONE
