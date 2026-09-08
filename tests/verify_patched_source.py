#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise AssertionError(f"缺少补丁逻辑：{label}\n期望片段：{needle}")


def forbid(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise AssertionError(f"发现不应存在的逻辑：{label}\n片段：{needle}")


def main() -> int:
    if len(sys.argv) != 2:
        print(f"用法：{sys.argv[0]} <guacamole-client-source-dir>", file=sys.stderr)
        return 2

    root = Path(sys.argv[1]).resolve()
    text_input = (root / "guacamole/src/main/frontend/src/app/textInput/directives/guacTextInput.js").read_text(encoding="utf-8")
    tiled = (root / "guacamole/src/main/frontend/src/app/client/directives/guacTiledClients.js").read_text(encoding="utf-8")
    managed = (root / "guacamole/src/main/frontend/src/app/client/types/ManagedClient.js").read_text(encoding="utf-8")
    mouse_client = (root / "guacamole/src/main/frontend/src/app/client/directives/guacClient.js").read_text(encoding="utf-8")
    index = (root / "guacamole/src/main/frontend/src/app/index/controllers/indexController.js").read_text(encoding="utf-8")
    client = (root / "guacamole/src/main/frontend/src/app/client/controllers/clientController.js").read_text(encoding="utf-8")
    client_notification = (root / "guacamole/src/main/frontend/src/app/client/directives/guacClientNotification.js").read_text(encoding="utf-8")
    client_template = (root / "guacamole/src/main/frontend/src/app/client/templates/client.html").read_text(encoding="utf-8")
    connection_warning = (root / "guacamole/src/main/frontend/src/app/client/styles/connection-warning.css").read_text(encoding="utf-8")
    preferences = (root / "guacamole/src/main/frontend/src/app/settings/services/preferenceService.js").read_text(encoding="utf-8")
    settings_template = (root / "guacamole/src/main/frontend/src/app/settings/templates/settingsPreferences.html").read_text(encoding="utf-8")
    en = (root / "guacamole/src/main/frontend/src/translations/en.json").read_text(encoding="utf-8")
    zh = (root / "guacamole/src/main/frontend/src/translations/zh.json").read_text(encoding="utf-8")

    # All modified source files carry an explicit downstream modification notice.
    for text, label in [
        (text_input, "guacTextInput"),
        (tiled, "guacTiledClients"),
        (managed, "ManagedClient"),
        (mouse_client, "guacClient"),
        (index, "indexController"),
        (client_notification, "guacClientNotification"),
        (preferences, "preferenceService"),
    ]:
        require(text, "Downstream modification:", f"{label} 修改声明")

    # Local text-input mode
    require(text_input, "'$window'", "guacTextInput 注入 $window")
    require(text_input, "processTextInput", "统一处理文字、Backspace 与 Delete")
    require(text_input, "flushCompletedComposition", "处理 input/compositionend 乱序")
    require(text_input, "resetAfterBrowserFocusChange", "标签页切换后清除 composition 状态")
    require(text_input, "guacTextInputFocusRequested", "恢复文本输入的客户端焦点")
    require(text_input, "guacInputFocusRestoreRequested", "阻止隐藏 InputSink 抢占文本输入焦点")
    require(text_input, "event.preventDefault();", "文本模式声明拥有恢复焦点")
    require(text_input, "target.focus();", "文本模式重新聚焦可见 textarea")
    require(text_input, "target.blur();", "text input native IME context reset")
    require(text_input, "focusTextInputTarget", "text input trusted-gesture focus restore")
    require(text_input, "if (immediate)", "text input synchronous trusted-gesture path")
    require(text_input, "removeEventListener", "销毁时清理文本输入监听器")

    # Raw keyboard / remote Microsoft Pinyin mode
    for needle, label in [
        ("const $document", "indexController 已注入 $document"),
        ("const $window", "indexController 已注入 $window"),
        ("var sink = new Guacamole.InputSink()", "indexController 拥有 InputSink"),
        ("sinkElement.readOnly = true;", "raw input sink rejects local IME composition"),
        ("sinkElement.setAttribute('inputmode', 'none');", "raw input sink disables local software IME input"),
        ("var keyboard = new Guacamole.Keyboard", "indexController 拥有 keyboard"),
        ("var hasActiveTunnel", "indexController 可检查活动连接"),
        ("restoreRemoteKeyboardInput", "恢复原始键盘通道"),
        ("REMOTE_MODIFIER_KEYSYMS", "显式释放远端修饰键"),
        ("keyboard.reset();", "重置本地按键状态"),
        ("sink.focus();", "重新聚焦隐藏输入捕获器"),
        ("sinkElement.blur();", "raw input native IME context reset"),
        ("sinkElement.focus();", "raw input synchronous trusted-gesture restore"),
        ("sinkElement.value = '';", "clear stale native input value"),
        ("keyboardRestorePendingUserGesture", "long-suspension trusted-gesture marker"),
        ("cancelKeyboardRestoreTimer", "coalesced restore cancellation"),
        ("restoreRemoteKeyboardInputNow", "shared synchronous/deferred restore core"),
        ("keyboardUserGesture", "multi-phase pointer gesture restore"),
        ("keyboardKeyGesture", "first keydown and manual hotkey restore"),
        ("isRemoteKeyboardTarget", "restrict automatic restoration to remote surface"),
        ("'pointerdown'", "trusted pointer listener"),
        ("'mousedown'", "trusted mouse fallback listener"),
        ("'touchstart'", "trusted touch fallback listener"),
        ("'click'", "post-default-focus click listener"),
        ("'keydown'", "keyboard self-healing listener"),
        ("'pageshow'", "page cache restore listener"),
        ("'pagehide'", "page cache suspension listener"),
        ("'freeze'", "page lifecycle freeze listener"),
        ("'resume'", "page lifecycle resume listener"),
        ("'fullscreenchange'", "fullscreen focus recovery listener"),
        ("'pointerlockchange'", "pointer lock focus recovery listener"),
        ("'KeyK'", "Ctrl-Alt-K manual recovery hotkey"),
        ("forceMenu", "Ctrl-Alt-Shift menu recovery fallback"),
        ("guacToggleMenuRequested", "direct menu-toggle request after recovery"),
        ("!forceRecovery && !forceMenu", "manual shortcuts bypass stale event targets"),
        ("getModifierState('AltGraph')", "AltGr does not trigger local recovery shortcuts"),
        ("guacForceInputRecovery", "menu-driven forced recovery"),
        ("guacKeyboardFocusRequested", "恢复 ManagedClient 焦点"),
        ("guacInputFocusRestoreRequested", "协调文本/原始键盘焦点所有权"),
        ("inputFocusEvent.defaultPrevented", "文本模式可阻止隐藏输入框抢焦点"),
        ("querySelector('.text-input .target')", "文本输入目标不被误判为本地表单"),
        ("element.isContentEditable", "保护本地可编辑控件焦点"),
        ("$document[0].hasFocus()", "避免后台窗口错误恢复焦点"),
    ]:
        require(index, needle, label)

    if index.count("keyboardMenuShortcutActive = false;") < 5:
        raise AssertionError(
            "The menu shortcut latch must reset on key release and every "
            "background/page lifecycle path."
        )

    require(tiled, "guacTextInputFocusRequested", "接收文本输入焦点请求")
    require(tiled, "guacKeyboardFocusRequested", "接收原始键盘焦点请求")
    require(tiled, "ManagedClientGroup.verifyFocus", "恢复客户端焦点")

    # Mouse movement coalescing / lossless button transitions
    require(mouse_client, "MOUSE_MOVE_INTERVAL = 33", "鼠标移动发送频率上限")
    require(mouse_client, "copyMouseState", "复制浏览器可能复用的鼠标状态")
    require(mouse_client, "pendingMouseMove", "只保留最新待发送移动")
    require(mouse_client, "flushPendingMouseMove", "点击前刷新最后坐标")
    require(mouse_client, "cancelPendingMouseMove", "切换连接时清理旧移动")
    require(mouse_client, "event.type !== 'mousemove'", "按钮状态不进入移动合并")
    require(mouse_client, "client.sendMouseState(event.state, true);", "按钮状态立即发送")
    require(mouse_client, "$scope.client.noteControlInput()", "鼠标按下触发控制响应监测")
    require(mouse_client, "$scope.$on('$destroy', cancelPendingMouseMove)", "销毁时清理移动计时器")
    if mouse_client.count("sendMouseEventState(event);") < 2:
        raise AssertionError("物理鼠标和模拟鼠标必须共用安全的移动合并逻辑")

    # Transient tunnel instability / background throttling
    require(managed, "TUNNEL_UNSTABLE_WARNING_DELAY = 3000", "网络提示确认窗口")
    require(managed, "currentTunnelState", "跟踪 ChainedTunnel 转发的实际状态")
    require(managed, "scheduleUnstableWarning", "短暂异常提示防抖")
    require(managed, "$document[0].hidden", "后台页面不显示网络误报")
    require(managed, "tunnelVisibilityChanged", "页面恢复后重新确认异常")
    require(managed, "endUnstableWarning", "恢复或断线时清理提示状态")
    require(managed, "reconnectSuggested", "持续异常后保留重连建议")
    require(managed, "hasActiveTransfers", "自动整页刷新保护进行中的文件传输")
    require(managed, "ManagedFileTransferState.StreamState.OPEN", "识别活动文件流")
    require(managed, "CONTROL_RESPONSE_TIMEOUT = 8000", "控制响应超时窗口")
    require(managed, "CONTROL_RESPONSE_MIN_INPUTS = 3", "控制无响应最小点击数")
    require(managed, "CONTROL_MAX_DISPLAY_DELAY = 3000", "画面队列与渲染延迟上限")
    require(managed, "noteControlInput", "记录有意的控制输入")
    require(managed, "serverSyncGeneration", "以远端同步确认控制路径进展")
    require(managed, "minimumSyncOffset", "以最佳同步偏移识别网络排队")
    require(managed, "display.statisticWindow = 0", "默认关闭逐帧浏览器渲染统计")
    require(managed, "enableControlResponseStatistics", "点击后按需启用渲染统计")
    require(managed, "display.statisticWindow = 1000", "控制检查使用短统计窗口")
    require(managed, "disableControlResponseStatistics", "响应或超时后关闭渲染统计")
    require(managed, "controlVisibilityChanged", "页面隐藏时立即停止响应统计")
    require(managed, "displayProcessingLag", "识别浏览器本地画面处理积压")
    require(managed, "resetControlResponseWatchdog", "远端同步或断线时清理看门狗")
    require(managed, "controlUnresponsive", "控制路径无响应状态")
    require(managed, "removeEventListener(\n                            'visibilitychange', controlVisibilityChanged", "断线时清理响应统计监听器")
    require(managed, "without generating a synchronous", "同步回调避开全画面缩略图")
    forbid(managed, "THUMBNAIL_UPDATE_FREQUENCY", "前台同步不得周期生成缩略图")
    sync_handler = managed.split("client.onsync = function syncReceived", 1)[1]
    sync_handler = sync_handler.split("client.onargv", 1)[0]
    forbid(sync_handler, "ManagedClient.updateThumbnail", "实时同步回调不得生成缩略图")
    thumbnail_calls = managed.count("ManagedClient.updateThumbnail(managedClient);")
    if "/* sparse filler" not in managed and thumbnail_calls != 2:
        raise AssertionError("缩略图只能在首次连接和断开生命周期生成")
    forbid(managed, "tunnel.unstableThreshold =", "不得削弱底层不稳定检测阈值")
    forbid(managed, "tunnel.receiveTimeout =", "不得延长底层断线超时")

    # The client controller may request recovery but must not own keyboard/sink.
    require(client, "recoverKeyboardInput", "客户端菜单恢复入口")
    require(client, "$scope.$emit('guacForceInputRecovery')", "菜单向全局键盘控制器请求恢复")
    require(client, "$scope.$on('guacToggleMenuRequested'", "失效键盘恢复后直接切换菜单")
    require(client, "$scope.menu.shown = !$scope.menu.shown", "保留原生菜单开关语义")
    require(client, "isConnectionRecoveryAvailable", "恢复后显示重连入口")
    require(client, "ManagedClientState.ConnectionState.CONNECTED", "仅活动连接提供重连")
    require(client, "isClientConnectionRecoverable", "断线后仍允许刷新恢复")
    require(client, "dismissConnectionRecovery", "允许关闭重连建议")
    require(client, "automaticRefresh", "整页自动刷新偏好绑定")
    require(client, "canAutoRefresh", "自动刷新条件检查")
    require(client, "queueAutoRefresh", "延迟自动刷新排队")
    require(client, "cancelAutoRefresh", "关闭设置时取消待执行刷新")
    require(client, "AUTO_REFRESH_RESET_DELAY = 60000", "稳定后重置跨刷新计数")
    require(client, "preferenceService.getAutomaticRefreshDelay()", "跨刷新退避延迟")
    require(client, "preferenceService.refreshPage(false)", "自动刷新整个页面")
    require(client, "preferenceService.refreshPage(true)", "手动刷新整个页面")
    require(client, "ManagedClient.hasActiveTransfers", "文件传输期间不自动刷新")
    require(client, "$scope.$watchCollection", "监听网络和传输状态")
    require(client_template, "CLIENT.ACTION_RECOVER_KEYBOARD", "菜单恢复按钮")
    require(client_template, "recoverKeyboardInput()", "菜单恢复按钮绑定")
    require(en, '"ACTION_RECOVER_KEYBOARD" : "Recapture keyboard"', "英文恢复按钮")
    require(zh, '"ACTION_RECOVER_KEYBOARD" : "重新捕获键盘"', "中文恢复按钮")
    require(en, "Ctrl-Alt-K", "英文恢复热键提示")
    require(zh, "Ctrl-Alt-K", "中文恢复热键提示")
    require(client_template, "CLIENT.TEXT_CLIENT_STATUS_RECOVERED_SLOW", "恢复后卡顿提示")
    require(client_template, "CLIENT.TEXT_CLIENT_STATUS_RECOVERED_REFRESHING", "自动整页刷新提示")
    require(client_template, "isAutomaticRefreshPending()", "自动刷新状态绑定")
    require(client_template, "refreshPage()", "右下角手动刷新按钮")
    require(client_template, "menu.automaticRefresh", "连接菜单自动刷新开关")
    require(client_template, "CLIENT.ACTION_REFRESH_PAGE", "整页刷新操作文案")
    require(client_template, "!isConnectionUnstable() || isAutomaticRefreshPending()", "倒计时期间可取消整页刷新")
    require(client_template, "dismissConnectionRecovery()", "网络提示关闭按钮")
    require(en, '"ACTION_DISMISS_RECOVERY"', "英文关闭提示按钮")
    require(zh, '"ACTION_DISMISS_RECOVERY"', "中文关闭提示按钮")
    require(connection_warning, "#connection-warning .actions", "网络提示操作布局")
    forbid(client, "$window.location.reload", "整页刷新必须集中由偏好服务保护")

    # Full-page refresh preference and cross-reload loop guard
    require(preferences, "automaticRefresh : false", "整页自动刷新默认关闭")
    require(preferences, "AUTO_REFRESH_STATE_KEY", "跨刷新会话计数键")
    require(preferences, "AUTO_REFRESH_DELAY = 5000", "首次整页刷新延迟")
    require(preferences, "AUTO_REFRESH_MAX_ATTEMPTS = 2", "整页刷新循环上限")
    require(preferences, "$window.sessionStorage", "跨刷新循环保护持久化")
    require(preferences, "canAutomaticallyRefresh", "刷新额度检查")
    require(preferences, "getAutomaticRefreshDelay", "指数退避延迟")
    require(preferences, "resetAutomaticRefresh", "稳定后清理刷新计数")
    require(preferences, "$window.location.reload();", "执行完整窗口刷新")
    require(preferences, "automaticRefreshStorageAvailable", "存储不可用时安全禁用自动刷新")
    require(preferences, "typeof state.attempts !== 'number'", "拒绝损坏的跨刷新计数")
    require(settings_template, "preferences.automaticRefresh", "用户设置页自动刷新开关")

    # Terminal error dialog follows the same preference and keeps manual refresh.
    require(client_notification, "preferenceService.preferences.automaticRefresh", "错误窗口遵循自动刷新设置")
    require(client_notification, "preferenceService.canAutomaticallyRefresh()", "错误窗口遵循刷新次数上限")
    require(client_notification, "preferenceService.refreshPage(false)", "错误倒计时整页刷新")
    require(client_notification, "preferenceService.refreshPage(true)", "错误窗口手动整页刷新")
    require(client_notification, "CLIENT.ACTION_REFRESH_PAGE", "错误窗口刷新操作")
    forbid(client_notification, "guacClientManager.replaceManagedClient", "错误窗口不得只替换连接")

    require(en, '"ACTION_REFRESH_PAGE"', "英文整页刷新操作")
    require(zh, '"ACTION_REFRESH_PAGE"', "中文整页刷新操作")
    require(en, '"HELP_AUTOMATIC_REFRESH"', "英文自动刷新风险说明")
    require(zh, '"HELP_AUTOMATIC_REFRESH"', "中文自动刷新风险说明")
    require(text_input, "isVisibleLocalInput", "只保护真正的本地输入控件")
    forbid(text_input, "focusedRect", "不得把任意可见远程元素误判成本地输入控件")

    forbid(client, "REMOTE_MODIFIER_KEYSYMS", "修饰键恢复误放入 clientController")
    forbid(client, "new Guacamole.InputSink", "InputSink 不得移入 clientController")

    print("已打补丁源码的作用域、模式隔离与关键逻辑检查通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
