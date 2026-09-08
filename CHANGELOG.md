# Changelog

## 1.6.0-recovery5

- Add an opt-in browser-local setting for delayed automatic refresh of the entire Guacamole page after confirmed network or control failure; the default is off.
- Keep a lower-right manual **Refresh page** action whenever automatic refresh is disabled or unavailable.
- Apply the same preference to terminal client/tunnel error countdowns and manual error-dialog recovery.
- Protect active file transfers and persist a per-tab refresh guard through `sessionStorage`, with 5/10-second backoff, a two-attempt limit, and a stable-minute reset.
- Disable automatic refresh when cross-reload loop state cannot be stored safely, while preserving manual refresh.
- Warn that full-page refresh can select a different backend or remote session.

## 1.6.0-recovery4

- Remove synchronous full-display thumbnail generation from the live sync callback; thumbnails remain captured on initial connection and disconnect.
- Disable Guacamole display statistics by default and enable a smaller one-second window only while intentional clicks are being checked for responsiveness.
- Stop temporary rendering statistics immediately after a timely sync, a watchdog timeout, a hidden page, or tunnel teardown.
- Preserve all recovery3 input, network, mouse ordering, and balancing-group safeguards.

## 1.6.0-recovery3

- Rebuild a confirmed, persistently unstable direct connection without waiting for the tunnel to recover or the browser page to be refreshed.
- Detect a wedged or backlogged downstream control path when three intentional mouse presses receive no timely remote display sync for eight seconds.
- Use Guacamole display statistics and relative sync timestamp drift to reject syncs delayed by more than three seconds as evidence of responsive control.
- Preserve pending recovery if the tunnel closes while the rebuild timer is active.
- Keep balancing-group recovery manual because reconnecting a group may select a different backend and display another session.
- Retain the recovery2 mouse coalescing and all existing keyboard/IME fixes.

## 1.6.0-recovery2

- Coalesce high-frequency physical and emulated mouse movement to the latest state at roughly 30 Hz.
- Flush the latest pending position before every mouse button transition so clicks, releases, wheel events, and drag endpoints are never delayed behind stale movement.
- Copy queued mouse state and clear it when the managed client changes or the directive is destroyed.
- Add regression coverage for movement collapse, immutable queued state, click ordering, drag release, and connection replacement.

## 1.6.0-recovery1

- Debounce the visible tunnel-instability warning and suppress false warnings while the page is hidden.
- Automatically rebuild only affected connections after confirmed instability recovers, using bounded exponential backoff.
- Cancel pending automatic recovery when instability returns, a file transfer is active, or the user keeps the current session.
- Preserve the manual reconnect action after the retry limit while retaining the Guacamole login, route, and unaffected tiled connections.
- Keep Guacamole's original instability detector and 15-second receive timeout unchanged.
- Add regression coverage for brief stalls, sustained stalls, background throttling, transfer protection, retry limits, and stable-period reset.

## 1.6.0-inputfix7

- Make raw-keyboard mode authoritative by preventing the hidden input sink from accepting local IME composition text.
- Recover keyboard and IME capture across blur, visibility, freeze, page-cache, fullscreen, and pointer-lock transitions.
- Retry recovery through pointer, mouse, touch, click, and first-key gestures without stealing focus from local controls.
- Make `Ctrl+Alt+Shift` independently recover input and toggle the Guacamole menu even when keyboard state is stale.
- Add `Ctrl+Alt+K` and a menu action as manual recovery paths.
- Reset stale shortcut latches when keyup events are lost and avoid AltGr conflicts.
- Restore the visible text-input target when focus lands on a remote non-form element.

## 1.6.0-inputfix6

- Recover native IME contexts after long browser freezes through the first trusted pointer gesture.
- Listen for page lifecycle `freeze`, `resume`, and `pageshow` events in addition to focus and visibility changes.
- Restore text-input and raw-keyboard modes synchronously when user activation is required by Chromium.
- Verify that release metadata contains the actual distributed patch SHA-256.
