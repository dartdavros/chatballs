(function () {
  var script = document.currentScript;
  if (!script) return;
  var widgetKey = script.getAttribute("data-widget-key") || "";
  var legacyChannel = script.getAttribute("data-channel") || "";
  if (!widgetKey && !legacyChannel) return;
  var origin = new URL(script.src, location.href).origin;
  var instanceId = "chat_" + Math.random().toString(36).slice(2);
  var entryQuery = widgetKey
    ? "widgetKey=" + encodeURIComponent(widgetKey)
    : "channel=" + encodeURIComponent(legacyChannel);
  var panelUrl = origin + "/chat/?" + entryQuery + "&instanceId=" + encodeURIComponent(instanceId);

  var open = false, frame = null, shell = null, unread = false, callActive = false, expanded = false;
  var animating = false, pendingAppearance = null;
  var api = window.ChatballsChat = window.ChatballsChat || {};
  window.ChatballsChat = api; // legacy alias для уже встроенных хостов

  /*__SITE_FIELDS__*/
  /*__OBSERVATIONS__*/

  /*__APPEARANCE__*/

  /*__LAUNCHER__*/
  /*__SITE_EVENTS__*/
  /*__SITE_INVITATION__*/

  function ensureFrame() {
    if (frame) return;
    shell = document.createElement("div");
    shell.style.cssText = "position:fixed;width:" + PANEL_WIDTH.normal + ";height:" + panelHeight() + ";z-index:2147483001;display:none;transition:width .32s cubic-bezier(.4,0,.2,1),height .32s cubic-bezier(.4,0,.2,1);";
    frame = document.createElement("iframe");
    frame.src = panelUrl;
    frame.allow = "microphone 'src'";
    frame.title = "Чат";
    frame.style.cssText = "width:100%;height:100%;border:none;border-radius:24px;box-shadow:0 12px 40px rgba(0,0,0,0.18);background:transparent;display:block;transform-origin:0 0;";
    shell.appendChild(frame);
    layoutShell();
    // Панель может открыться раньше, чем загрузится iframe — тогда сообщение
    // «открыто» (по нему виджет доскроллит ленту вниз) будет потеряно, поэтому
    // повторяем его на load.
    frame.addEventListener("load", function () {
      notifyLayout();
      if (open) notifyOpened();
    });
    document.body.appendChild(shell);
    window.addEventListener("message", function (e) {
      if (e.origin !== origin || !frame || e.source !== frame.contentWindow) return;
      var d = e.data || {};
      if (d.instanceId && d.instanceId !== instanceId) return;
      handleSiteEventMessage(d);
      if (d.type === "chatballs-fields-ready") {
        fieldsReady = true;
        sendFields();
      }
      if (d.type === "chatballs-visitor-ready") notifyVisitorState();
      if (d.type === "chatballs-chat-close") setOpen(false);
      if (d.type === "chatballs-chat-layout-request") notifyLayout();
      if (d.type === "chatballs-chat-expand") setExpanded(Boolean(d.expanded));
      if (d.type === "chatballs-chat-unread") {
        unread = Boolean(d.unread);
        updateDot();
      }
      if (d.type === "chatballs-chat-activity" && d.kind === "message") {
        unread = !open;
        updateDot();
        if (!open && !callActive) bumpLauncher();
        notification.currentTime = 0;
        play(notification);
      }
      if (d.type === "chatballs-chat-activity" && d.kind === "call") setCallActive(Boolean(d.active));
    });
  }

  // Развёрнутая панель почти вдвое шире и немного выше; переход анимируется
  // самим iframe (transition в его стилях).
  var PANEL_WIDTH = { normal: "min(440px,calc(100vw - 32px))", expanded: "min(820px,calc(100vw - 32px))" };
  function panelHeight() {
    return "min(" + (expanded ? 820 : 720) + "px,calc(100vh - " + (appearance.size + 60) + "px))";
  }

  // На телефоне плавающее окно не помещается: панель занимает весь экран,
  // разворачивать её уже некуда, а закрывают её кнопкой в шапке.
  var mobile = window.matchMedia("(max-width: 480px)");

  function panelRadius() { return mobile.matches ? 0 : 24; }

  function layoutShell() {
    if (!shell) return;
    var full = mobile.matches;
    shell.style.top = full ? "0" : "";
    shell.style.left = full ? "0" : appearance.position === "left" ? "24px" : "";
    shell.style.right = full ? "0" : appearance.position === "right" ? "24px" : "";
    shell.style.bottom = full ? "0" : (appearance.size + 36) + "px";
    shell.style.width = full ? "100%" : expanded ? PANEL_WIDTH.expanded : PANEL_WIDTH.normal;
    shell.style.height = full ? "100%" : panelHeight();
    frame.style.borderRadius = panelRadius() + "px";
    showLauncher();
    layoutSiteInvitation();
    notifyLayout();
  }

  // Сама панель ширину экрана не видит: в iframe её вьюпорт — это окно
  // виджета. Поэтому про полноэкранный режим ей говорит лоадер.
  function notifyLayout() {
    try { frame.contentWindow.postMessage({ type: "chatballs-chat-layout", fullscreen: mobile.matches }, origin); } catch (_) {}
  }

  // Пока панель на весь экран, кнопка висела бы поверх поля ввода.
  function showLauncher() {
    var hidden = open && mobile.matches;
    btn.style.opacity = hidden ? "0" : "1";
    btn.style.pointerEvents = hidden ? "none" : "";
  }

  if (mobile.addEventListener) mobile.addEventListener("change", layoutShell);
  else if (mobile.addListener) mobile.addListener(layoutShell);

  function setExpanded(next) {
    expanded = next;
    layoutShell();
  }

  /*__GENIE__*/

  function notifyOpened() {
    try { frame.contentWindow.postMessage({ type: "chatballs-chat-opened" }, origin); } catch (_) {}
  }

  function finishAnimation() {
    animating = false;
    genieSvg.style.display = "none";
    restPanel();
    showLauncher();
    focusSiteEventPanel();
    if (pendingAppearance) {
      var next = pendingAppearance;
      pendingAppearance = null;
      applyAppearance(next);
    }
  }

  function setOpen(next) {
    ensureFrame();
    // Слой силуэта нужен уже на первом кадре: первый же кадр рисуется до
    // запуска анимации, чтобы панель не мелькнула целиком.
    ensureGenie();
    open = next;
    layoutSiteInvitation();
    if (!next) notifySiteEvent("cancel");
    notifyVisitor(next ? "widget_open" : "widget_close");
    animating = true;
    btn.style.opacity = "0";
    btn.style.pointerEvents = "none";
    if (open) {
      // Контейнер раскладывается до расчёта: силуэт строится по настоящим
      // границам панели, а они известны только разложенной.
      shell.style.display = "block";
      paintGenie(1, panelRect(), iconRect());
      playGenie(1, 0, GENIE_OPEN_MS, panelRect(), iconRect(), function () {
        if (!open) return;
        finishAnimation();
      });
    } else {
      var box = panelRect();
      playGenie(0, 1, GENIE_CLOSE_MS, box, iconRect(), function () {
        if (open) return;
        shell.style.display = "none";
        finishAnimation();
      });
    }
    renderLauncher();
    btn.setAttribute("aria-label", open ? "Свернуть чат" : "Открыть чат");
    if (open) {
      unread = false;
      updateDot();
      if (callActive) play(ringtone);
      notifyOpened();
    } else updateDot();
  }

  btn.addEventListener("click", function () { setOpen(!open); });
  function mount() {
    document.body.appendChild(btn);
    ensureFrame();
    loadAppearance();
  }
  if (document.body) mount();
  else window.addEventListener("DOMContentLoaded", mount);
})();
