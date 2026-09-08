#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


TARGETS = [
    "guacamole/src/main/frontend/src/app/client/controllers/clientController.js",
    "guacamole/src/main/frontend/src/app/client/templates/client.html",
    "guacamole/src/main/frontend/src/app/client/styles/connection-warning.css",
    "guacamole/src/main/frontend/src/app/client/types/ManagedClient.js",
    "guacamole/src/main/frontend/src/app/textInput/directives/guacTextInput.js",
    "guacamole/src/main/frontend/src/app/client/directives/guacTiledClients.js",
    "guacamole/src/main/frontend/src/app/client/directives/guacClient.js",
    "guacamole/src/main/frontend/src/app/client/directives/guacClientNotification.js",
    "guacamole/src/main/frontend/src/app/index/controllers/indexController.js",
    "guacamole/src/main/frontend/src/app/settings/services/preferenceService.js",
    "guacamole/src/main/frontend/src/app/settings/templates/settingsPreferences.html",
    "guacamole/src/main/frontend/src/translations/en.json",
    "guacamole/src/main/frontend/src/translations/zh.json",
]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    if len(sys.argv) != 2:
        print(f"用法：{sys.argv[0]} <package-dir>", file=sys.stderr)
        return 2

    root = Path(sys.argv[1]).resolve()
    patch_path = root / "patches/0001-fix-ime-and-keyboard-after-tab-switch.patch"
    patch = patch_path.read_text(encoding="utf-8")

    readme_en = (root / "README.md").read_text(encoding="utf-8")
    readme_zh = (root / "README.zh-CN.md").read_text(encoding="utf-8")
    require("# guacamole_patch" in readme_en,
            "README.md must contain the English documentation")
    require("[简体中文](README.zh-CN.md)" in readme_en,
            "English README must link to the Chinese README")
    require("# guacamole_patch" in readme_zh,
            "README.zh-CN.md must contain the Chinese documentation")
    require("[English](README.md)" in readme_zh,
            "Chinese README must link to the English README")
    require("ghcr.io/trilogys/guacamole_patch:1.6.0-recovery5" in readme_en and
            "ghcr.io/trilogys/guacamole_patch:1.6.0-recovery5" in readme_zh,
            "Both README files must document the default image")
    for needle in [
        "docker compose up -d --force-recreate --no-deps guacamole",
        "Ctrl+Alt+K",
        "Apache Guacamole 1.6.0",
    ]:
        require(needle in readme_en and needle in readme_zh,
                f"Both README files must document deployment step: {needle}")

    require("\nindex " not in "\n" + patch,
            "正式补丁不得包含伪造的 git postimage blob 哈希")

    for path in TARGETS:
        require(f"diff --git a/{path} b/{path}" in patch, f"缺少文件补丁头：{path}")
        require(f"--- a/{path}" in patch and f"+++ b/{path}" in patch,
                f"缺少标准 unified diff 路径：{path}")

    required = [
        "restoreRemoteKeyboardInput",
        "Downstream modification:",
        "sinkElement.readOnly = true;",
        "sinkElement.setAttribute('inputmode', 'none');",
        "REMOTE_MODIFIER_KEYSYMS",
        "0xFE03, /* AltGr",
        "hasActiveTunnel()",
        "sink.focus();",
        "keyboard.reset();",
        "guacKeyboardFocusRequested",
        "guacTextInputFocusRequested",
        "guacInputFocusRestoreRequested",
        "inputFocusEvent.defaultPrevented",
        "querySelector('.text-input .target')",
        "isVisibleLocalInput",
        "processTextInput",
        "compositionend",
        "visibilitychange",
        "keyboardRestorePendingUserGesture",
        "restoreRemoteKeyboardInputNow",
        "keyboardUserGesture",
        "'pointerdown'",
        "'mousedown'",
        "'touchstart'",
        "'click'",
        "'keydown'",
        "'pagehide'",
        "'pageshow'",
        "'freeze'",
        "'resume'",
        "sinkElement.focus();",
        "sinkElement.value = '';",
        "if (immediate)",
        "forceMenu",
        "guacToggleMenuRequested",
        "guacForceInputRecovery",
        "getModifierState('AltGraph')",
        "ACTION_RECOVER_KEYBOARD",
        "element.isContentEditable",
        "tagName === 'textarea'",
        "tagName === 'button'",
        "tagName === 'a'",
        "TUNNEL_UNSTABLE_WARNING_DELAY = 3000",
        "currentTunnelState",
        "scheduleUnstableWarning",
        "tunnelVisibilityChanged",
        "endUnstableWarning",
        "reconnectSuggested",
        "isConnectionRecoveryAvailable",
        "dismissConnectionRecovery",
        "TEXT_CLIENT_STATUS_RECOVERED_SLOW",
        "ACTION_DISMISS_RECOVERY",
        "hasActiveTransfers",
        "automaticRefresh : false",
        "AUTO_REFRESH_STATE_KEY",
        "AUTO_REFRESH_DELAY = 5000",
        "AUTO_REFRESH_MAX_ATTEMPTS = 2",
        "AUTO_REFRESH_RESET_DELAY = 60000",
        "automaticRefreshStorageAvailable",
        "typeof state.attempts !== 'number'",
        "canAutomaticallyRefresh",
        "getAutomaticRefreshDelay",
        "resetAutomaticRefresh",
        "$window.sessionStorage",
        "$window.location.reload();",
        "queueAutoRefresh",
        "cancelAutoRefresh",
        "isAutomaticRefreshPending",
        "TEXT_CLIENT_STATUS_RECOVERED_REFRESHING",
        "ACTION_REFRESH_PAGE",
        "HELP_AUTOMATIC_REFRESH",
        "MOUSE_MOVE_INTERVAL = 33",
        "copyMouseState",
        "pendingMouseMove",
        "flushPendingMouseMove",
        "cancelPendingMouseMove",
        "sendMouseEventState",
        "CONTROL_RESPONSE_TIMEOUT = 8000",
        "CONTROL_RESPONSE_MIN_INPUTS = 3",
        "CONTROL_MAX_DISPLAY_DELAY = 3000",
        "noteControlInput",
        "serverSyncGeneration",
        "minimumSyncOffset",
        "display.statisticWindow = 0",
        "enableControlResponseStatistics",
        "display.statisticWindow = 1000",
        "disableControlResponseStatistics",
        "controlVisibilityChanged",
        "displayProcessingLag",
        "without generating a synchronous",
        "resetControlResponseWatchdog",
        "controlUnresponsive",
        "isClientConnectionRecoverable",
    ]
    for needle in required:
        require(needle in patch, f"补丁缺少关键逻辑：{needle}")

    build = (root / "build.sh").read_text(encoding="utf-8")
    for needle, label in [
        ("--dry-run", "构建前补丁 dry-run"),
        ("-DskipTests=false", "默认运行 Guacamole 上游测试"),
        ("verify_patched_source.py", "已打补丁源码检查"),
        ("guacClientNotification.js", "连接错误整页刷新脚本语法检查"),
        ("preferenceService.js", "整页刷新偏好脚本语法检查"),
        ("SOURCE_SHA256=\"81f9fd5a", "Guacamole 1.6.0 源码哈希"),
        ("sha256sum --check --status SHA256SUMS", "补丁包内部完整性检查"),
        ("SUPPORTED_VERSION=\"1.6.0\"", "版本锁定"),
        ("BUILD_WORK_DIR=\"$(mktemp -d", "安全的独立临时目录"),
        ("ghcr.io/trilogys/guacamole_patch:", "Guacamole recovery image namespace"),
        ("PULL_BASE_IMAGES", "可控的基础镜像拉取策略"),
        ("docker image inspect", "构建结果检查"),
        ("/opt/guacamole/bin/initdb.sh", "镜像冒烟测试"),
        ("org.opencontainers.image.licenses=Apache-2.0", "OCI 许可证标签"),
        ("org.opencontainers.image.version=${GUACAMOLE_VERSION}-recovery5", "具名恢复版本标签"),
        ("io.guacamole.recovery.patch-sha256", "恢复补丁哈希标签"),
    ]:
        require(needle in build, f"构建脚本缺少：{label}")

    require('rm -rf -- "${WORK_DIR}"' not in build,
            "不得直接递归删除用户指定的 WORK_DIR")
    require("--pull" not in build.split("DOCKER_BUILD_ARGS=(", 1)[0],
            "不得无条件拉取浮动基础镜像")

    compose = (root / "docker-compose.override.yml").read_text(encoding="utf-8")
    require("ghcr.io/trilogys/guacamole_patch:1.6.0-recovery5" in compose,
            "Compose override must use the named recovery image")

    workflow = (root / ".github/workflows/build-image.yml").read_text(encoding="utf-8")
    for needle, label in [
        ("Build and publish Guacamole recovery image", "Actions 工作流名称"),
        ("Publish recovery5 from", "Actions 运行名称"),
        ("PACKAGE_TAG: 1.6.0-recovery5", "具名镜像标签"),
        ('"${PACKAGE_TAG}" "${RELEASE_TAG}" main', "具名与滚动标签发布"),
    ]:
        require(needle in workflow, f"Actions 工作流缺少：{label}")

    official_compose = (root / "docker-compose.official.yml").read_text(encoding="utf-8")
    require("guacamole/guacamole:1.6.0" in official_compose,
            "Official Compose fallback must use Apache Guacamole 1.6.0")

    metadata_path = root / "RELEASE_METADATA.json"
    require(metadata_path.exists(), "缺少 RELEASE_METADATA.json")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    require(metadata["release_status"] == "controlled-deployment-candidate",
            "发布状态必须明确为受控部署候选版")
    require(metadata["end_to_end_rdp_validation"] is False,
            "不得把尚未完成的端到端验证标记为已完成")
    require(metadata["package_version"] == "1.6.0-recovery5",
            "发布元数据版本必须为 recovery5")
    require(metadata["release_name"] == "Guacamole Input and Network Recovery",
            "发布元数据必须包含正式恢复版本名称")
    require(metadata["base_repository_commit"] == "db230461876a0b086f5ab32165a1eaea0dd39481",
            "发布元数据必须记录远端 main 比较基线")
    require(metadata["default_image"] == "ghcr.io/trilogys/guacamole_patch:1.6.0-recovery5",
            "Release metadata default image must use the named recovery tag")
    require(metadata["fallback_image"] == "guacamole/guacamole:1.6.0",
            "Release metadata fallback image must be official Guacamole 1.6.0")
    require(
        metadata["patch_sha256"] == hashlib.sha256(patch_path.read_bytes()).hexdigest(),
        "发布元数据中的补丁 SHA-256 与实际补丁不一致",
    )
    require(metadata["patch_sha256"] in readme_en and
            metadata["patch_sha256"] in readme_zh,
            "Both README files must document the current patch SHA-256")

    license_path = root / "LICENSE"
    notice_path = root / "NOTICE"
    require(license_path.exists(), "缺少 Apache License 2.0 全文")
    require("Apache License" in license_path.read_text(encoding="utf-8"), "LICENSE 内容异常")
    notice = notice_path.read_text(encoding="utf-8")
    require("Apache Guacamole" in notice and "modified" in notice.lower(),
            "NOTICE 必须包含上游归属和修改声明")

    print("补丁包结构、作用域、安全与合规检查通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
