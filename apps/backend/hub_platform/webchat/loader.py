# Публичный JS-лоадер виджета (SPEC-HUB-0003 §3, SPEC-HUB-0010 §7.1). Подключается
# одним тегом:
#   sales:    <script src="https://hub.edevs.tech/chat-widget.js" data-channel="edevs" async></script>
#   support:  <script src=".../chat-widget.js" data-channel="foxray-support"
#                        data-mode="support" data-support-token="<token>" async></script>
# Лоадер рисует launcher и открывает панель в изолированном iframe (/chat/).
#
# TODO (SPEC-HUB-0010 §7.3, security): для production настроить CSP
# `frame-ancestors` для /chat/ (раздаётся vite/nginx, не Django — настраивается в
# infra/deploy), разрешив домены продуктов Edevs (foxray.pro, firepage.ru и т.д.).
# Только origin недостаточен — support-виджет дополнительно проверяется signed
# Product Support Token. Домены — у владельца.

LOADER_JS = r"""
(function () {
  var script = document.currentScript;
  if (!script) return;
  var channel = script.getAttribute("data-channel") || "edevs";
  var mode = script.getAttribute("data-mode") || "sales";
  var origin = new URL(script.src, location.href).origin;
  var panelUrl = origin + "/chat/?channel=" + encodeURIComponent(channel);
  if (mode === "support") {
    var token = script.getAttribute("data-support-token") || "";
    panelUrl += "&mode=support&token=" + encodeURIComponent(token);
  }

  var open = false, frame = null, unread = false, callActive = false;

  var style = document.createElement("style");
  style.textContent = "@keyframes edevs-chat-message-bump{0%,100%{transform:translateY(0)}35%{transform:translateY(-6px)}70%{transform:translateY(-2px)}}@keyframes edevs-chat-call-shake{0%,18%,100%{transform:translateX(0)}3%{transform:translateX(-5px)}6%{transform:translateX(5px)}9%{transform:translateX(-4px)}12%{transform:translateX(4px)}15%{transform:translateX(-2px)}}.edevs-chat-message-bump{animation:edevs-chat-message-bump .42s ease-out}.edevs-chat-call-shake{animation:edevs-chat-call-shake 3.2s ease-in-out infinite}.edevs-chat-launcher:hover{transform:translateY(-2px);box-shadow:0 12px 30px rgba(22,119,255,0.45)}.edevs-chat-launcher:focus-visible{outline:3px solid rgba(22,119,255,0.45);outline-offset:2px}";
  (document.head || document.documentElement).appendChild(style);

  // Launcher — «пилюля» с иконкой (Tabler brand-hipchat) и подписью. Иконка
  // вшита как inline SVG: на сайте продукта шрифта Tabler нет.
  var btn = document.createElement("button");
  btn.className = "edevs-chat-launcher";
  btn.type = "button";
  btn.setAttribute("aria-label", "Открыть чат");
  btn.style.cssText = "position:fixed;right:24px;bottom:24px;height:52px;padding:0 20px;border:none;border-radius:999px;background:#1677ff;box-shadow:0 8px 24px rgba(22,119,255,0.35);cursor:pointer;z-index:2147483000;display:flex;align-items:center;gap:9px;color:#fff;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;font-size:15px;font-weight:600;line-height:1;letter-spacing:0;transition:transform .18s ease,box-shadow .18s ease;";
  btn.innerHTML = '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex:none"><path d="M17.802 17.292s.077-.055.2-.149c1.843-1.425 3-3.49 3-5.789c0-4.286-4.03-7.764-9-7.764c-4.97 0-9 3.478-9 7.764c0 4.288 4.03 7.646 9 7.646c.424 0 1.12-.028 2.088-.084c1.262.82 3.104 1.493 4.716 1.493c.499 0 .734-.41.414-.828c-.486-.596-1.156-1.551-1.416-2.29z"/><path d="M7.5 13.5c2.5 2.5 6.5 2.5 9 0"/></svg><span style="white-space:nowrap">Чат</span>';

  var dot = document.createElement("span");
  dot.style.cssText = "position:absolute;top:-2px;right:-2px;width:12px;height:12px;border-radius:50%;background:#faad14;border:2px solid #fff;display:none;";
  btn.appendChild(dot);

  var notification = new Audio(origin + "/chat/audio/notification.mp3");
  var ringtone = new Audio(origin + "/chat/audio/ringtone.mp3");
  notification.preload = "auto";
  ringtone.preload = "auto";
  ringtone.loop = true;
  ringtone.volume = 1;

  function play(audio) {
    var result = audio.play();
    if (result && result.catch) result.catch(function () {});
  }

  function updateDot() {
    dot.style.display = !open && (unread || callActive) ? "block" : "none";
  }

  function bumpLauncher() {
    btn.classList.remove("edevs-chat-message-bump");
    void btn.offsetWidth;
    btn.classList.add("edevs-chat-message-bump");
    window.setTimeout(function () { btn.classList.remove("edevs-chat-message-bump"); }, 450);
  }

  function setCallActive(active) {
    callActive = active;
    btn.classList.toggle("edevs-chat-call-shake", active);
    if (active) play(ringtone);
    else {
      ringtone.pause();
      ringtone.currentTime = 0;
    }
    updateDot();
  }

  function ensureFrame() {
    if (frame) return;
    frame = document.createElement("iframe");
    frame.src = panelUrl;
    frame.title = "Чат";
    frame.style.cssText = "position:fixed;right:24px;bottom:24px;width:min(440px,calc(100vw - 32px));height:min(720px,calc(100vh - 48px));border:none;border-radius:16px;box-shadow:0 12px 40px rgba(0,0,0,0.18);z-index:2147483000;display:none;background:transparent;";
    // Панель может открыться раньше, чем загрузится iframe — тогда сообщение
    // «открыто» (по нему виджет доскроллит ленту вниз) будет потеряно, поэтому
    // повторяем его на load.
    frame.addEventListener("load", function () { if (open) notifyOpened(); });
    document.body.appendChild(frame);
    window.addEventListener("message", function (e) {
      if (e.origin !== origin) return;
      var d = e.data || {};
      if (d.type === "edevs-chat-close") setOpen(false);
      if (d.type === "edevs-chat-unread") {
        unread = Boolean(d.unread);
        updateDot();
      }
      if (d.type === "edevs-chat-activity" && d.kind === "message") {
        unread = !open;
        updateDot();
        if (!open && !callActive) bumpLauncher();
        notification.currentTime = 0;
        play(notification);
      }
      if (d.type === "edevs-chat-activity" && d.kind === "call") setCallActive(Boolean(d.active));
    });
  }

  function notifyOpened() {
    try { frame.contentWindow.postMessage({ type: "edevs-chat-opened" }, origin); } catch (_) {}
  }

  function setOpen(next) {
    ensureFrame();
    open = next;
    frame.style.display = open ? "block" : "none";
    btn.style.display = open ? "none" : "flex";
    if (open) {
      unread = false;
      updateDot();
      if (callActive) play(ringtone);
      notifyOpened();
    } else updateDot();
  }

  btn.addEventListener("click", function () { setOpen(true); });
  function mount() {
    document.body.appendChild(btn);
    ensureFrame();
  }
  if (document.body) mount();
  else window.addEventListener("DOMContentLoaded", mount);
})();
"""
