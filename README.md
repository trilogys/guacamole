English | [简体中文](README.zh-CN.md)

# guacamole_patch

An unofficial downstream patch for **Apache Guacamole 1.6.0** that improves keyboard and IME recovery after browser tab switching, background suspension, and page lifecycle changes.

This repository is not an official Apache Software Foundation release.

## Quick deployment

Pull the published image:

```bash
docker pull ghcr.io/trilogys/guacamole_patch:1.6.0-recovery4
```

Use it in Docker Compose:

```yaml
services:
  guacamole:
    image: ghcr.io/trilogys/guacamole_patch:1.6.0-recovery4
```

Update only the Guacamole web container:

```bash
docker compose pull guacamole
docker compose up -d --force-recreate --no-deps guacamole
docker compose ps
docker compose logs --tail=100 guacamole
```

Docker reuses unchanged layers, so later pulls normally download only changed layers. Do not run `docker compose down -v` or delete database volumes.

## Published image tags

- `1.6.0-recovery4`: current named recovery release documented by this package.
- `1.6.0-recovery3`: previous recovery release retained for rollback.
- `1.6.0`: current moving release image; this tag is updated on each release build.
- `main`: latest image built from the `main` branch.
- `sha-<commit>`: immutable tag for a specific source commit.
- `dev`: development image built from the `dev` branch.

For production builds, run the workflow from `main`. Running it from `dev` also updates the shared `1.6.0` tag.

## What the patch addresses

### Guacamole Text input with a local IME

```text
Remote Windows language: ENG
Guacamole input method: Text input
Local input method: Chinese IME
```

The patch recovers missing composition events, restores focus to the active connection, restores text/Backspace/Delete delivery, and prevents the hidden raw-keyboard input sink from stealing focus from the visible text field.

### Microsoft Pinyin inside remote Windows

```text
Guacamole input method: None
Local input language: ENG or a local IME
Remote Windows input method: Microsoft Pinyin
RDP keyboard layout: en-us-qwerty
```

The patch resets recorded key state when the page is hidden, restores keyboard capture after returning, releases stuck modifiers, handles long background suspension and page lifecycle events, and rebuilds Chromium's native input context on the first user gesture.

Manual recovery remains available through `Ctrl+Alt+K` and the **Recover keyboard capture** menu action.

### Transient network warning

Guacamole normally marks a tunnel unstable after roughly 1.5 seconds without inbound data. The patch waits for three additional seconds of continuous, visible-page instability before showing the warning. It suppresses the warning while the page is hidden and starts a fresh grace period when the page returns.

The underlying instability detector and 15-second receive timeout are unchanged. Sustained network or server failures are still reported and disconnected normally.

After a confirmed unstable period, recovery automatically rebuilds only the affected direct connection after five seconds, without requiring the tunnel to recover first. A second consecutive attempt waits ten seconds, and recovery stops after two attempts to prevent loops. One stable minute resets the retry budget.

If the tunnel remains open but three intentional mouse presses receive no timely remote display sync for eight seconds, recovery also treats the downstream control path as wedged. Guacamole's display statistics and relative sync timing are used to identify network queueing or browser rendering delays above three seconds, so a stream of stale frames does not mask the failure. Automatic reconnect is cancelled while a file transfer is active or if **Keep current session** is selected. Manual **Reconnect** remains available after the retry limit. The Guacamole login, page route, and unaffected tiled connections are preserved.

Reconnecting a balancing group may select another backend, so group recovery remains manual and never switches the displayed machine automatically. Use a specific Guacamole connection instead of a balancing group when the same remote host must be preserved.

### Mouse response under weak networks

High-frequency mouse movement is coalesced to the latest position at roughly 30 Hz. Button presses, releases, right-clicks, wheel events, and drag endpoints flush the latest position first and are sent immediately, preventing clicks from waiting behind stale movement. Pending movement is discarded when the connection is replaced.

### High display load from a remote browser

Chrome, Edge, video, animation, and complex page scrolling inside remote Windows generate substantial RDP display traffic. The patch detects severe backlog and recovers the connection, but cannot remove bottlenecks in the remote host, network, or `guacd` encoder. For the specific Guacamole RDP connection, prefer:

Recovery4 no longer flattens the full live display and generates a thumbnail every five seconds from the sync callback. Thumbnails are still saved after the first connected frame and on disconnect. Per-frame display statistics are disabled by default and enabled with a one-second window only after intentional clicks while responsiveness is checked. This reduces main-thread competition during full repaint bursts such as opening a new remote browser tab.

- `16`-bit color depth;
- force-lossless disabled;
- wallpaper, theming, font smoothing, full-window drag, desktop composition, and menu animations disabled;
- bitmap, offscreen, and glyph caching enabled by leaving their "disable" options unchecked;
- `1280x720` or `1600x900` with `96` DPI during initial troubleshooting.

## GitHub Actions build

Open **Actions → Build and publish Guacamole recovery image → Run workflow**, select `main`, and run the workflow.

A successful build publishes:

```text
ghcr.io/trilogys/guacamole_patch:1.6.0
ghcr.io/trilogys/guacamole_patch:1.6.0-recovery4
ghcr.io/trilogys/guacamole_patch:main
ghcr.io/trilogys/guacamole_patch:sha-<commit>
```

## Manual build

Requirements:

```text
Docker
curl
patch
Python 3
tar
sha256sum
mktemp
```

Clone and build:

```bash
git clone https://github.com/trilogys/guacamole_patch.git
cd guacamole_patch

IMAGE_NAME="ghcr.io/trilogys/guacamole_patch:1.6.0-recovery4" \
bash ./build.sh
```

For a faster troubleshooting build:

```bash
MAVEN_ARGUMENTS="-T 1C -Dmaven.test.skip=true" \
IMAGE_NAME="ghcr.io/trilogys/guacamole_patch:1.6.0-recovery4" \
bash ./build.sh
```

`build.sh` verifies the patch package and Apache source archive, runs regression checks, dry-runs and applies the patch, builds the official Dockerfile, inspects the image, and runs an `initdb` smoke test.

## Verify the image

```bash
docker image inspect ghcr.io/trilogys/guacamole_patch:1.6.0-recovery4 \
  --format '{{index .Config.Labels "io.guacamole.recovery.patch-sha256"}}'
```

Expected patch SHA-256:

```text
b022cfb268a0c18d812e1dcdc7867ee61554de2e9f02ffe369abce0dff535c89
```

## Acceptance testing

See [TEST_MATRIX.md](TEST_MATRIX.md) for the complete procedure. At minimum, verify:

- local Chinese IME with remote Windows set to ENG;
- remote Microsoft Pinyin candidate selection;
- repeated tab switching in Chrome and Edge;
- no stuck Ctrl, Shift, or Alt keys;
- Backspace, Delete, arrow keys, Enter, and numeric candidate selection;
- reconnecting the same account;
- rollback to a known working image.

## Scope and limitations

The patch does not modify `guacd`, PostgreSQL schema or data, Nginx, FRP, connection accounts, recordings, or shared directories.

Shortcuts such as `Win+Space` and `Alt+Tab` may be intercepted by the local operating system or browser. Validate the image against the actual Windows RDP environment before production rollout.

## License

This patch package is licensed under the Apache License 2.0. Apache Guacamole copyright and NOTICE requirements remain unchanged.
