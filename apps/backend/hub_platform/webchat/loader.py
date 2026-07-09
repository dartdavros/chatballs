# Публичный JS-лоадер виджета (SPEC-HUB-0003 §3, SPEC-HUB-0010 §7.1). Подключается
# одним тегом:
#   sales:    <script src=".../chat-widget.js" data-channel="edevs" async></script>
#   support:  <script src=".../chat-widget.js" data-channel="foxray-support"
#                        data-mode="support" data-support-token="<token>" async></script>
# Лоадер рисует launcher и открывает панель в изолированном iframe (/chat/).

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

  var open = false, frame = null;

  var btn = document.createElement("button");
  btn.setAttribute("aria-label", "Открыть чат");
  btn.style.cssText = "position:fixed;right:24px;bottom:24px;width:60px;height:60px;border-radius:50%;border:none;background:#1677ff;box-shadow:0 8px 24px rgba(22,119,255,0.4);cursor:pointer;z-index:2147483000;display:flex;align-items:center;justify-content:center;";
  btn.innerHTML = '<svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2Z"/></svg>';

  var dot = document.createElement("span");
  dot.style.cssText = "position:absolute;top:10px;right:10px;width:12px;height:12px;border-radius:50%;background:#ff4d4f;border:2px solid #1677ff;display:none;";
  btn.appendChild(dot);

  function ensureFrame() {
    if (frame) return;
    frame = document.createElement("iframe");
    frame.src = panelUrl;
    frame.title = "Чат";
    frame.style.cssText = "position:fixed;right:24px;bottom:24px;width:min(384px,calc(100vw - 32px));height:min(600px,calc(100vh - 48px));border:none;border-radius:16px;box-shadow:0 12px 40px rgba(0,0,0,0.18);z-index:2147483000;display:none;background:transparent;";
    document.body.appendChild(frame);
    window.addEventListener("message", function (e) {
      if (e.origin !== origin) return;
      var d = e.data || {};
      if (d.type === "edevs-chat-close") setOpen(false);
      if (d.type === "edevs-chat-unread") dot.style.display = d.unread && !open ? "block" : "none";
    });
  }

  function setOpen(next) {
    ensureFrame();
    open = next;
    frame.style.display = open ? "block" : "none";
    btn.style.display = open ? "none" : "flex";
    if (open) {
      dot.style.display = "none";
      try { frame.contentWindow.postMessage({ type: "edevs-chat-opened" }, origin); } catch (_) {}
    }
  }

  btn.addEventListener("click", function () { setOpen(true); });
  if (document.body) document.body.appendChild(btn);
  else window.addEventListener("DOMContentLoaded", function () { document.body.appendChild(btn); });
})();
"""
