#!/usr/bin/env python3
from __future__ import annotations

PADDING = 4
PAD = "\u200b"
MODIFIERS = [
    0xFE03,
    0xFFE1, 0xFFE2, 0xFFE3, 0xFFE4,
    0xFFE7, 0xFFE8, 0xFFE9, 0xFFEA,
    0xFFEB, 0xFFEC, 0xFFED, 0xFFEE,
]


class TextInputState:
    def __init__(self) -> None:
        self.composing = False
        self.value = PAD * (PADDING * 2)
        self.sent: list[str] = []
        self.focus_requests = 0
        self.target_focused = False

    def composition_start(self) -> None:
        self.composing = True

    def input(self, value: str) -> None:
        self.value = value
        if not self.composing:
            self.process()

    def composition_end(self) -> None:
        self.composing = False
        if self.value != PAD * (PADDING * 2):
            self.process()

    def browser_focus_change(self, hidden: bool) -> None:
        self.composing = False
        self.value = PAD * (PADDING * 2)
        if not hidden:
            self.focus_requests += 1

    def claim_global_focus_restore(self, visible_local_focus: bool = False) -> bool:
        """Return True to model Angular event.preventDefault()."""
        self.composing = False
        self.value = PAD * (PADDING * 2)
        self.focus_requests += 1
        if not visible_local_focus:
            self.target_focused = True
        return True

    def process(self) -> None:
        text = self.value.replace(PAD, "")
        if text:
            self.sent.append(text)
        self.value = PAD * (PADDING * 2)


class RemoteKeyboardState:
    def __init__(self) -> None:
        self.hidden = False
        self.document_focused = True
        self.ready = True
        self.active_tunnel = True
        self.visible_local_input = False
        self.text_input_target_active = False
        self.client_focused = False
        self.sink_focused = False
        self.text_target_focused = False
        self.pressed = {0xFFE1, 0xFFE3}
        self.remote_released: list[int] = []
        self.restore_queued = False
        self.restore_pending_user_gesture = False
        self.native_context_stale = False
        self.synchronous_restores = 0
        self.menu_shown = False
        self.menu_shortcut_active = False

    def reset(self) -> None:
        self.remote_released.extend(self.pressed)
        self.pressed.clear()

    def queue_restore(self) -> bool:
        if (
            self.hidden
            or not self.document_focused
            or not self.ready
            or not self.active_tunnel
            or self.visible_local_input
            or self.restore_queued
        ):
            return False
        self.restore_queued = True
        return True

    def execute_restore(self) -> None:
        if not self.restore_queued:
            return
        self.restore_queued = False
        self.perform_restore()

    def perform_restore(
        self,
        *,
        user_initiated: bool = False,
        ignore_existing_local_focus: bool = False,
    ) -> bool:
        if (
            self.hidden
            or not self.document_focused
            or not self.ready
            or not self.active_tunnel
            or (self.visible_local_input and not ignore_existing_local_focus)
        ):
            return False
        self.client_focused = True
        self.reset()
        self.remote_released.extend(MODIFIERS)
        native_focus_restored = user_initiated or not self.native_context_stale
        if self.text_input_target_active:
            self.text_target_focused = native_focus_restored
        else:
            self.sink_focused = native_focus_restored
        if user_initiated:
            self.native_context_stale = False
            self.synchronous_restores += 1
        return True

    def hide(self) -> None:
        self.hidden = True
        self.restore_queued = False
        self.restore_pending_user_gesture = True
        self.menu_shortcut_active = False
        self.reset()

    def freeze(self) -> None:
        self.hide()
        self.native_context_stale = True

    def show(self) -> None:
        self.hidden = False

    def pointer_event(self, event_type: str, *, local_control: bool = False) -> bool:
        if (
            not self.restore_pending_user_gesture
            or self.hidden
            or local_control
        ):
            return False
        restored = self.perform_restore(
            user_initiated=True,
            ignore_existing_local_focus=True,
        )
        if restored and event_type == "click":
            self.restore_pending_user_gesture = False
        return restored

    def keydown(
        self,
        *,
        force_recovery: bool = False,
        force_menu: bool = False,
        local_control: bool = False,
    ) -> bool:
        if force_menu and self.menu_shortcut_active:
            return False
        if force_menu:
            self.menu_shortcut_active = True
        if force_recovery or force_menu:
            self.restore_pending_user_gesture = True
        if (
            not self.restore_pending_user_gesture
            or self.hidden
            or (local_control and not force_recovery and not force_menu)
        ):
            return False
        restored = self.perform_restore(
            user_initiated=True,
            ignore_existing_local_focus=True,
        )
        if restored:
            self.restore_pending_user_gesture = False
            if force_menu:
                self.menu_shown = not self.menu_shown
        return restored

    def keyup(self) -> None:
        self.menu_shortcut_active = False

    def menu_recover(self) -> bool:
        self.restore_pending_user_gesture = True
        return self.keydown(force_recovery=True)


class MouseInputState:
    """Model coalesced movement with lossless button transitions."""

    MOVE_INTERVAL = 33

    def __init__(self) -> None:
        self.now = 0
        self.pending_move: dict[str, int | bool] | None = None
        self.move_due: int | None = None
        self.sent: list[tuple[str, dict[str, int | bool]]] = []

    def flush_move(self) -> None:
        self.move_due = None
        if self.pending_move is not None:
            self.sent.append(("mousemove", self.pending_move))
            self.pending_move = None

    def event(self, event_type: str, state: dict[str, int | bool]) -> None:
        copied_state = dict(state)
        if event_type != "mousemove":
            self.flush_move()
            self.sent.append((event_type, copied_state))
            return

        self.pending_move = copied_state
        if self.move_due is None:
            self.move_due = self.now + self.MOVE_INTERVAL

    def advance(self, milliseconds: int) -> None:
        self.now += milliseconds
        if self.move_due is not None and self.now >= self.move_due:
            self.flush_move()

    def replace_client(self) -> None:
        self.pending_move = None
        self.move_due = None


class PageRefreshState:
    """Model opt-in, bounded full-page refresh after confirmed instability."""

    WARNING_DELAY = 3000
    AUTO_REFRESH_DELAY = 5000
    AUTO_REFRESH_MAX_ATTEMPTS = 2
    AUTO_REFRESH_RESET_DELAY = 60000

    def __init__(self, *, automatic_refresh: bool = False) -> None:
        self.now = 0
        self.automatic_refresh = automatic_refresh
        self.storage_available = True
        self.hidden = False
        self.tunnel_state = "open"
        self.warning_visible = False
        self.warning_due: int | None = None
        self.reconnect_suggested = False
        self.active_transfer = False
        self.auto_refresh_due: int | None = None
        self.auto_refresh_attempts = 0
        self.page_refreshes = 0
        self.manual_refreshes = 0
        self.attempt_reset_due: int | None = None

    def schedule_warning(self) -> None:
        self.warning_visible = False
        self.warning_due = None
        if not self.hidden:
            self.warning_due = self.now + self.WARNING_DELAY

    def set_tunnel_state(self, state: str) -> None:
        self.tunnel_state = state
        if state == "unstable":
            self.attempt_reset_due = None
            self.schedule_warning()
        else:
            self.warning_visible = False
            self.warning_due = None
            if state == "open":
                self.queue_auto_refresh()
                if self.auto_refresh_attempts:
                    self.attempt_reset_due = self.now + self.AUTO_REFRESH_RESET_DELAY

    def set_hidden(self, hidden: bool) -> None:
        self.hidden = hidden
        if self.tunnel_state == "unstable":
            self.schedule_warning()

    def set_automatic_refresh(self, enabled: bool) -> None:
        self.automatic_refresh = enabled
        if enabled:
            self.queue_auto_refresh()
        else:
            self.auto_refresh_due = None

    def advance(self, milliseconds: int) -> None:
        self.now += milliseconds
        if self.warning_due is not None and self.now >= self.warning_due:
            self.warning_due = None
            if self.tunnel_state == "unstable" and not self.hidden:
                self.warning_visible = True
                self.reconnect_suggested = True
                self.queue_auto_refresh()

        if self.auto_refresh_due is not None and self.now >= self.auto_refresh_due:
            self.auto_refresh_due = None
            if self.can_auto_refresh():
                self.auto_refresh_attempts += 1
                self.page_refreshes += 1
                self.reconnect_suggested = False
                self.attempt_reset_due = self.now + self.AUTO_REFRESH_RESET_DELAY

        if self.attempt_reset_due is not None and self.now >= self.attempt_reset_due:
            self.attempt_reset_due = None
            if self.tunnel_state == "open" and not self.reconnect_suggested:
                self.auto_refresh_attempts = 0

    def can_auto_refresh(self) -> bool:
        return (
            self.automatic_refresh
            and self.storage_available
            and self.recovery_available()
            and not self.active_transfer
            and self.auto_refresh_attempts < self.AUTO_REFRESH_MAX_ATTEMPTS
        )

    def queue_auto_refresh(self) -> None:
        if self.can_auto_refresh() and self.auto_refresh_due is None:
            delay = self.AUTO_REFRESH_DELAY * (2 ** self.auto_refresh_attempts)
            self.auto_refresh_due = self.now + delay

    def set_active_transfer(self, active: bool) -> None:
        self.active_transfer = active
        if active:
            self.auto_refresh_due = None
        else:
            self.queue_auto_refresh()

    def dismiss_recovery(self) -> None:
        self.auto_refresh_due = None
        self.reconnect_suggested = False

    def manual_refresh(self) -> None:
        self.auto_refresh_due = None
        self.auto_refresh_attempts = 0
        self.manual_refreshes += 1

    def recovery_available(self) -> bool:
        return self.reconnect_suggested and self.tunnel_state in {
            "open", "unstable", "disconnected", "tunnel_error"
        }


class ControlResponseState:
    """Model recovery when input receives no later display synchronization."""

    RESPONSE_TIMEOUT = 8000
    MIN_INPUTS = 3
    MAX_DISPLAY_DELAY = 3000

    def __init__(self) -> None:
        self.now = 0
        self.hidden = False
        self.tunnel_state = "open"
        self.sync_generation = 0
        self.initial_sync_generation: int | None = None
        self.inputs_since_sync = 0
        self.response_due: int | None = None
        self.statistics_enabled = False
        self.control_unresponsive = False
        self.reconnect_suggested = False

    def note_input(self) -> None:
        if self.hidden or self.tunnel_state != "open":
            return
        if not self.inputs_since_sync:
            self.statistics_enabled = True
        self.inputs_since_sync += 1
        if self.response_due is None:
            self.initial_sync_generation = self.sync_generation
            self.response_due = self.now + self.RESPONSE_TIMEOUT

    def set_hidden(self, hidden: bool) -> None:
        self.hidden = hidden
        if hidden:
            self.inputs_since_sync = 0
            self.response_due = None
            self.initial_sync_generation = None
            self.statistics_enabled = False

    def sync(self, display_delay: int = 0, processing_lag: int = 0) -> None:
        if (
            display_delay > self.MAX_DISPLAY_DELAY
            or processing_lag > self.MAX_DISPLAY_DELAY
        ):
            return
        self.sync_generation += 1
        self.inputs_since_sync = 0
        self.response_due = None
        self.initial_sync_generation = None
        self.statistics_enabled = False
        if self.control_unresponsive:
            self.control_unresponsive = False
            self.reconnect_suggested = False

    def advance(self, milliseconds: int) -> None:
        self.now += milliseconds
        if self.response_due is None or self.now < self.response_due:
            return
        self.response_due = None
        self.statistics_enabled = False
        if (
            self.inputs_since_sync >= self.MIN_INPUTS
            and self.sync_generation == self.initial_sync_generation
            and self.tunnel_state == "open"
            and not self.hidden
        ):
            self.control_unresponsive = True
            self.reconnect_suggested = True
        self.inputs_since_sync = 0


class ThumbnailUpdateState:
    """Model thumbnails outside the latency-sensitive display sync path."""

    def __init__(self) -> None:
        self.updates: list[str] = []

    def connected(self) -> None:
        self.updates.append("connected")

    def sync(self) -> None:
        pass

    def disconnected(self) -> None:
        self.updates.append("disconnected")


class CacheRevalidatedRefreshState:
    """Model one-shot page reload after frontend cache revalidation."""

    def __init__(self) -> None:
        self.build_reload_lock = True
        self.revalidation_started = False
        self.reloads = 0
        self.finished = False

    def refresh(self) -> None:
        self.build_reload_lock = False
        self.revalidation_started = True

    def finish_revalidation(self) -> None:
        if self.finished:
            return
        self.finished = True
        self.reloads += 1


def main() -> None:
    # compositionend missing during tab switch must not permanently block input
    state = TextInputState()
    state.composition_start()
    state.input(PAD * PADDING + "zhong")
    state.browser_focus_change(True)
    state.browser_focus_change(False)
    state.input(PAD * PADDING + "中文" + PAD * PADDING)
    assert state.sent == ["中文"]
    assert state.composing is False
    assert state.focus_requests == 1

    # input-before-compositionend must flush exactly once
    reordered = TextInputState()
    reordered.composition_start()
    reordered.input(PAD * PADDING + "输入" + PAD * PADDING)
    assert reordered.sent == []
    reordered.composition_end()
    assert reordered.sent == ["输入"]

    # Text-input mode claims global focus restoration and keeps the visible target.
    text_mode = TextInputState()
    claimed = text_mode.claim_global_focus_restore()
    assert claimed is True
    assert text_mode.target_focused is True

    # If the user clicks a visible local control before the deferred focus runs,
    # text mode still claims the event but must not steal that new focus.
    text_with_local_control = TextInputState()
    claimed = text_with_local_control.claim_global_focus_restore(visible_local_focus=True)
    assert claimed is True
    assert text_with_local_control.target_focused is False

    # Raw-keyboard mode must recover client focus, release modifiers, and refocus sink.
    remote = RemoteKeyboardState()
    remote.hide()
    remote.hidden = False
    assert remote.queue_restore() is True
    # A simultaneous focus event must coalesce into the existing queued restore.
    assert remote.queue_restore() is False
    remote.execute_restore()
    assert remote.client_focused is True
    assert remote.sink_focused is True
    assert remote.pressed == set()
    assert all(keysym in remote.remote_released for keysym in MODIFIERS)

    # Text mode must still release modifiers but must not focus the hidden sink.
    remote_text = RemoteKeyboardState()
    remote_text.text_input_target_active = True
    assert remote_text.queue_restore() is True
    remote_text.execute_restore()
    assert remote_text.client_focused is True
    assert remote_text.text_target_focused is True
    assert remote_text.sink_focused is False
    assert all(keysym in remote_text.remote_released for keysym in MODIFIERS)

    # A visible local Guacamole form field must retain focus.
    local_form = RemoteKeyboardState()
    local_form.visible_local_input = True
    assert local_form.queue_restore() is False
    local_form.execute_restore()
    assert local_form.client_focused is False
    assert local_form.sink_focused is False

    # Hiding the page cancels any queued focus restoration.
    cancelled = RemoteKeyboardState()
    assert cancelled.queue_restore() is True
    cancelled.hide()
    cancelled.execute_restore()
    assert cancelled.sink_focused is False

    # A long browser freeze may invalidate Chromium's native editing context.
    # Deferred focus is insufficient. Early pointer/mouse events pre-restore the
    # context, while the bubbling click performs the final restore after browser
    # default focus actions have run.
    frozen = RemoteKeyboardState()
    frozen.freeze()
    frozen.show()
    assert frozen.queue_restore() is True
    frozen.execute_restore()
    assert frozen.client_focused is True
    assert frozen.sink_focused is False
    assert frozen.restore_pending_user_gesture is True
    assert frozen.pointer_event("pointerdown") is True
    assert frozen.restore_pending_user_gesture is True
    # Model the browser's default mousedown focus action stealing focus again.
    frozen.sink_focused = False
    assert frozen.pointer_event("mousedown") is True
    frozen.sink_focused = False
    assert frozen.pointer_event("click") is True
    assert frozen.sink_focused is True
    assert frozen.native_context_stale is False
    assert frozen.restore_pending_user_gesture is False
    assert frozen.synchronous_restores == 3

    # If a drag/touch sequence produces no final click, the first keydown must
    # complete recovery before Guacamole handles that same key event.
    key_fallback = RemoteKeyboardState()
    key_fallback.freeze()
    key_fallback.show()
    assert key_fallback.pointer_event("touchstart") is True
    key_fallback.sink_focused = False
    assert key_fallback.keydown() is True
    assert key_fallback.sink_focused is True
    assert key_fallback.restore_pending_user_gesture is False

    # Clicking a visible local control must not consume the pending trusted
    # gesture; a later click on the remote display can still recover input.
    frozen_local = RemoteKeyboardState()
    frozen_local.freeze()
    frozen_local.show()
    assert frozen_local.pointer_event("pointerdown", local_control=True) is False
    assert frozen_local.restore_pending_user_gesture is True
    assert frozen_local.pointer_event("click") is True
    assert frozen_local.sink_focused is True

    # Both manual fallbacks must recover even when the browser omitted all
    # lifecycle events and no pending marker exists.
    hotkey = RemoteKeyboardState()
    hotkey.native_context_stale = True
    assert hotkey.keydown(force_recovery=True) is True
    assert hotkey.sink_focused is True
    assert hotkey.restore_pending_user_gesture is False

    native_menu = RemoteKeyboardState()
    native_menu.native_context_stale = True
    native_menu.menu_shortcut_active = True
    native_menu.hide()
    native_menu.show()
    assert native_menu.menu_shortcut_active is False
    assert native_menu.keydown(force_menu=True) is True
    assert native_menu.sink_focused is True
    assert native_menu.menu_shown is True
    assert native_menu.restore_pending_user_gesture is False
    assert native_menu.keydown(force_menu=True) is False
    assert native_menu.menu_shown is True
    native_menu.keyup()
    assert native_menu.keydown(force_menu=True, local_control=True) is True
    assert native_menu.menu_shown is False

    menu_action = RemoteKeyboardState()
    menu_action.native_context_stale = True
    assert menu_action.menu_recover() is True
    assert menu_action.sink_focused is True
    assert menu_action.restore_pending_user_gesture is False

    # High-frequency movement must collapse to the most recent independent
    # state object and send no more than once per interval.
    mouse = MouseInputState()
    first_move = {"x": 10, "y": 20, "left": False}
    mouse.event("mousemove", first_move)
    first_move["x"] = 999
    mouse.event("mousemove", {"x": 30, "y": 40, "left": False})
    assert mouse.sent == []
    mouse.advance(MouseInputState.MOVE_INTERVAL - 1)
    assert mouse.sent == []
    mouse.advance(1)
    assert mouse.sent == [("mousemove", {"x": 30, "y": 40, "left": False})]

    # Button transitions flush the latest position first and are never delayed.
    mouse.event("mousemove", {"x": 50, "y": 60, "left": False})
    mouse.event("mousedown", {"x": 50, "y": 60, "left": True})
    assert mouse.sent[-2:] == [
        ("mousemove", {"x": 50, "y": 60, "left": False}),
        ("mousedown", {"x": 50, "y": 60, "left": True}),
    ]
    mouse.event("mousemove", {"x": 80, "y": 90, "left": True})
    mouse.event("mouseup", {"x": 80, "y": 90, "left": False})
    assert mouse.sent[-2:] == [
        ("mousemove", {"x": 80, "y": 90, "left": True}),
        ("mouseup", {"x": 80, "y": 90, "left": False}),
    ]

    # A movement queued for an old connection must never reach its replacement.
    stale_mouse = MouseInputState()
    stale_mouse.event("mousemove", {"x": 100, "y": 110, "left": False})
    stale_mouse.replace_client()
    stale_mouse.advance(MouseInputState.MOVE_INTERVAL)
    assert stale_mouse.sent == []

    # A brief unstable state must recover without flashing a warning.
    brief_stall = PageRefreshState()
    brief_stall.set_tunnel_state("unstable")
    brief_stall.advance(PageRefreshState.WARNING_DELAY - 1)
    assert brief_stall.warning_visible is False
    brief_stall.set_tunnel_state("open")
    brief_stall.advance(1)
    assert brief_stall.warning_visible is False
    assert brief_stall.reconnect_suggested is False

    # A sustained visible disruption must still warn before tunnel timeout.
    sustained_stall = PageRefreshState()
    sustained_stall.set_tunnel_state("unstable")
    sustained_stall.advance(PageRefreshState.WARNING_DELAY)
    assert sustained_stall.warning_visible is True
    assert sustained_stall.reconnect_suggested is True
    sustained_stall.set_tunnel_state("open")
    assert sustained_stall.warning_visible is False
    assert sustained_stall.reconnect_suggested is True
    assert sustained_stall.recovery_available() is True
    sustained_stall.set_tunnel_state("disconnected")
    assert sustained_stall.recovery_available() is True
    sustained_stall.dismiss_recovery()
    assert sustained_stall.reconnect_suggested is False

    # Background throttling must not produce a warning immediately on return.
    background_stall = PageRefreshState()
    background_stall.set_hidden(True)
    background_stall.set_tunnel_state("unstable")
    background_stall.advance(15000)
    assert background_stall.warning_visible is False
    background_stall.set_hidden(False)
    background_stall.advance(PageRefreshState.WARNING_DELAY - 1)
    assert background_stall.warning_visible is False
    background_stall.advance(1)
    assert background_stall.warning_visible is True

    # Hiding the page also clears a warning that was already visible.
    background_stall.set_hidden(True)
    assert background_stall.warning_visible is False
    assert background_stall.warning_due is None

    # Automatic full-page refresh is opt-in. Without it, the lower-right
    # warning remains available for explicit manual refresh.
    manual_only = PageRefreshState()
    manual_only.set_tunnel_state("unstable")
    manual_only.advance(PageRefreshState.WARNING_DELAY)
    manual_only.advance(PageRefreshState.AUTO_REFRESH_DELAY * 2)
    assert manual_only.page_refreshes == 0
    assert manual_only.recovery_available() is True
    manual_only.manual_refresh()
    assert manual_only.manual_refreshes == 1

    # With the preference enabled, a tunnel which remains unstable refreshes
    # the entire page before the underlying receive timeout.
    persistent_stall = PageRefreshState(automatic_refresh=True)
    persistent_stall.set_tunnel_state("unstable")
    persistent_stall.advance(PageRefreshState.WARNING_DELAY)
    assert persistent_stall.auto_refresh_due is not None
    persistent_stall.advance(PageRefreshState.AUTO_REFRESH_DELAY)
    assert persistent_stall.page_refreshes == 1

    # A confirmed tunnel failure that closes while recovery is pending retains
    # the pending full-page refresh.
    closed_stall = PageRefreshState(automatic_refresh=True)
    closed_stall.set_tunnel_state("unstable")
    closed_stall.advance(PageRefreshState.WARNING_DELAY)
    closed_stall.set_tunnel_state("tunnel_error")
    closed_stall.advance(PageRefreshState.AUTO_REFRESH_DELAY)
    assert closed_stall.page_refreshes == 1

    # Disabling the setting while a delayed refresh is pending cancels it
    # immediately without hiding the manual recovery path.
    preference_toggle = PageRefreshState(automatic_refresh=True)
    preference_toggle.set_tunnel_state("unstable")
    preference_toggle.advance(PageRefreshState.WARNING_DELAY)
    assert preference_toggle.auto_refresh_due is not None
    preference_toggle.set_automatic_refresh(False)
    preference_toggle.advance(PageRefreshState.AUTO_REFRESH_DELAY)
    assert preference_toggle.page_refreshes == 0
    assert preference_toggle.recovery_available() is True

    # Automatic refresh is disabled when session storage cannot preserve the
    # cross-reload loop guard. Manual refresh remains available.
    storage_guard = PageRefreshState(automatic_refresh=True)
    storage_guard.storage_available = False
    storage_guard.set_tunnel_state("unstable")
    storage_guard.advance(PageRefreshState.WARNING_DELAY)
    storage_guard.advance(PageRefreshState.AUTO_REFRESH_DELAY)
    assert storage_guard.page_refreshes == 0
    storage_guard.manual_refresh()
    assert storage_guard.manual_refreshes == 1

    # Several intentional presses with no later display sync indicate a
    # wedged downstream control path even while WebSocket pings remain healthy.
    input_stall = ControlResponseState()
    for _ in range(ControlResponseState.MIN_INPUTS):
        input_stall.note_input()
    input_stall.advance(ControlResponseState.RESPONSE_TIMEOUT)
    assert input_stall.reconnect_suggested is True
    input_stall.sync()
    assert input_stall.reconnect_suggested is False

    # Any remote sync acknowledges progress and cancels the input watchdog.
    responsive_input = ControlResponseState()
    for _ in range(ControlResponseState.MIN_INPUTS):
        responsive_input.note_input()
    responsive_input.sync()
    assert responsive_input.statistics_enabled is False
    responsive_input.advance(ControlResponseState.RESPONSE_TIMEOUT)
    assert responsive_input.reconnect_suggested is False

    # Stale syncs from a remote browser which is flooding the display queue do
    # not prove that current clicks can be processed in a timely manner.
    delayed_display = ControlResponseState()
    for _ in range(ControlResponseState.MIN_INPUTS):
        delayed_display.note_input()
    delayed_display.sync(display_delay=ControlResponseState.MAX_DISPLAY_DELAY + 1)
    assert delayed_display.statistics_enabled is True
    delayed_display.advance(ControlResponseState.RESPONSE_TIMEOUT)
    assert delayed_display.reconnect_suggested is True
    assert delayed_display.statistics_enabled is False

    delayed_render = ControlResponseState()
    for _ in range(ControlResponseState.MIN_INPUTS):
        delayed_render.note_input()
    delayed_render.sync(processing_lag=ControlResponseState.MAX_DISPLAY_DELAY + 1)
    delayed_render.advance(ControlResponseState.RESPONSE_TIMEOUT)
    assert delayed_render.reconnect_suggested is True

    # Fewer than three inert clicks must never rebuild an otherwise idle
    # session, and background input cannot arm recovery.
    inert_input = ControlResponseState()
    for _ in range(ControlResponseState.MIN_INPUTS - 1):
        inert_input.note_input()
    inert_input.advance(ControlResponseState.RESPONSE_TIMEOUT)
    assert inert_input.reconnect_suggested is False
    hidden_input = ControlResponseState()
    hidden_input.hidden = True
    for _ in range(ControlResponseState.MIN_INPUTS):
        hidden_input.note_input()
    hidden_input.advance(ControlResponseState.RESPONSE_TIMEOUT)
    assert hidden_input.reconnect_suggested is False
    assert hidden_input.statistics_enabled is False

    background_input = ControlResponseState()
    background_input.note_input()
    assert background_input.statistics_enabled is True
    background_input.set_hidden(True)
    assert background_input.response_due is None
    assert background_input.statistics_enabled is False

    # Live sync processing must never perform full-canvas thumbnail work. The
    # first useful frame and final disconnected state still provide previews.
    thumbnails = ThumbnailUpdateState()
    thumbnails.connected()
    for _ in range(1000):
        thumbnails.sync()
    thumbnails.disconnected()
    assert thumbnails.updates == ["connected", "disconnected"]

    # Manual and automatic recovery first clear Guacamole's stale-build lock
    # and request cache revalidation. Error/timeout/fallback completion may
    # race, but the actual page reload must occur exactly once.
    cache_refresh = CacheRevalidatedRefreshState()
    cache_refresh.refresh()
    assert cache_refresh.build_reload_lock is False
    assert cache_refresh.revalidation_started is True
    cache_refresh.finish_revalidation()
    cache_refresh.finish_revalidation()
    assert cache_refresh.reloads == 1

    # A confirmed disruption queues one bounded full-page refresh after the
    # initial delay when the opt-in preference is enabled.
    auto_recovery = PageRefreshState(automatic_refresh=True)
    auto_recovery.set_tunnel_state("unstable")
    auto_recovery.advance(PageRefreshState.WARNING_DELAY)
    auto_recovery.set_tunnel_state("open")
    auto_recovery.advance(PageRefreshState.AUTO_REFRESH_DELAY - 1)
    assert auto_recovery.page_refreshes == 0
    auto_recovery.advance(1)
    assert auto_recovery.page_refreshes == 1
    assert auto_recovery.auto_refresh_attempts == 1
    assert auto_recovery.reconnect_suggested is False

    # A second disruption backs off, while a third consecutive disruption
    # remains manual instead of entering a full-page refresh loop.
    auto_recovery.set_tunnel_state("unstable")
    auto_recovery.advance(PageRefreshState.WARNING_DELAY)
    auto_recovery.set_tunnel_state("open")
    auto_recovery.advance(PageRefreshState.AUTO_REFRESH_DELAY * 2)
    assert auto_recovery.page_refreshes == 2
    assert auto_recovery.auto_refresh_attempts == 2
    auto_recovery.set_tunnel_state("unstable")
    auto_recovery.advance(PageRefreshState.WARNING_DELAY)
    auto_recovery.set_tunnel_state("open")
    assert auto_recovery.auto_refresh_due is None
    auto_recovery.advance(PageRefreshState.AUTO_REFRESH_DELAY * 4)
    assert auto_recovery.page_refreshes == 2

    # A continuous stable minute resets the retry budget for a future event.
    auto_recovery.dismiss_recovery()
    auto_recovery.advance(PageRefreshState.AUTO_REFRESH_RESET_DELAY)
    assert auto_recovery.auto_refresh_attempts == 0

    # Active transfers and an explicit request not to refresh both cancel the
    # delayed action without clearing the manual recovery path prematurely.
    transfer_guard = PageRefreshState(automatic_refresh=True)
    transfer_guard.set_tunnel_state("unstable")
    transfer_guard.advance(PageRefreshState.WARNING_DELAY)
    transfer_guard.set_tunnel_state("open")
    transfer_guard.set_active_transfer(True)
    transfer_guard.advance(PageRefreshState.AUTO_REFRESH_DELAY * 2)
    assert transfer_guard.page_refreshes == 0
    assert transfer_guard.reconnect_suggested is True
    transfer_guard.set_active_transfer(False)
    assert transfer_guard.auto_refresh_due is not None
    transfer_guard.dismiss_recovery()
    transfer_guard.advance(PageRefreshState.AUTO_REFRESH_DELAY)
    assert transfer_guard.page_refreshes == 0

    print("输入法、鼠标合并、焦点所有权、网络提示、整页刷新和竞态状态回归测试通过。")


if __name__ == "__main__":
    main()
