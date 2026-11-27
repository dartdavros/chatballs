  var style = document.createElement("style");
  style.textContent = "@keyframes chatballs-chat-pop{from{opacity:0;transform:scale(.55) rotate(-25deg)}to{opacity:1;transform:none}}.chatballs-chat-launcher svg{animation:chatballs-chat-pop .24s cubic-bezier(.16,1,.3,1)}@keyframes chatballs-chat-blink{0%,92%,100%{transform:scaleY(1)}95%{transform:scaleY(.12)}}.chatballs-chat-eyes{transform-origin:24px 20px;animation:chatballs-chat-blink 4.2s infinite}@keyframes chatballs-chat-message-bump{0%,100%{transform:translateY(0)}35%{transform:translateY(-6px)}70%{transform:translateY(-2px)}}@keyframes chatballs-chat-call-shake{0%,18%,100%{transform:translateX(0)}3%{transform:translateX(-5px)}6%{transform:translateX(5px)}9%{transform:translateX(-4px)}12%{transform:translateX(4px)}15%{transform:translateX(-2px)}}.chatballs-chat-message-bump{animation:chatballs-chat-message-bump .42s ease-out}.chatballs-chat-call-shake{animation:chatballs-chat-call-shake 3.2s ease-in-out infinite}.chatballs-chat-launcher{box-shadow:0 8px 24px rgba(var(--chatballs-accent-rgb),0.35)}.chatballs-chat-launcher:hover{transform:translateY(-2px);box-shadow:0 12px 30px rgba(var(--chatballs-accent-rgb),0.45)}.chatballs-chat-launcher:focus-visible{outline:3px solid rgba(var(--chatballs-accent-rgb),0.45);outline-offset:2px}";
  style.textContent += ".chatballs-chat-launcher{position:fixed;right:24px;bottom:24px;width:var(--chatballs-launcher-size,56px);height:var(--chatballs-launcher-size,56px);padding:0;border:none;border-radius:var(--chatballs-launcher-radius,50%);--chatballs-accent-rgb:22,119,255;--chatballs-accent:#1677ff;background:var(--chatballs-accent);cursor:pointer;z-index:2147483002;display:flex;align-items:center;justify-content:center;color:#fff;transition:transform .18s ease,box-shadow .18s ease,opacity .14s ease;} :where(.chatballs-chat-launcher img){width:30px;height:30px;object-fit:contain;flex:none;}";
  (document.head || document.documentElement).appendChild(style);

  var launcherStyles = null;

  function applyLauncherCss(css) {
    if (!launcherStyles && css && btn.parentNode) {
      var host = document.createElement("div");
      if (!host.attachShadow) return;
      host.style.display = "contents";
      var shadow = host.attachShadow({ mode: "open" });
      launcherStyles = document.createElement("style");
      btn.parentNode.insertBefore(host, btn);
      shadow.appendChild(style.cloneNode(true));
      shadow.appendChild(launcherStyles);
      shadow.appendChild(btn);
      if (window.ResizeObserver) new window.ResizeObserver(layoutShell).observe(btn);
    }
    if (launcherStyles) launcherStyles.textContent = css;
  }

  // Launcher — круглая кнопка со знаком агента. Знак вшит как inline SVG:
  // на сайте, где стоит виджет, наших файлов нет. Пока панель открыта, кнопка
  // остаётся на месте и показывает шеврон — им же панель и закрывают.
  var BOT_ICON = '<svg viewBox="0 0 48 48" width="30" height="30" fill="currentColor" style="flex:none"><mask id="chatballs-launcher-face" maskUnits="userSpaceOnUse" x="0" y="0" width="48" height="48"><rect width="48" height="48" fill="#fff"/><g class="chatballs-chat-eyes"><rect x="15" y="16.4" width="4" height="7.2" rx="2" fill="#000"/><rect x="29" y="16.4" width="4" height="7.2" rx="2" fill="#000"/></g><path d="M17.6 26.4c1.7 2.4 3.9 3.6 6.4 3.6s4.7-1.2 6.4-3.6" fill="none" stroke="#000" stroke-width="2.6" stroke-linecap="round"/></mask><circle cx="24" cy="3.6" r="2.4"/><rect x="22.8" y="4.8" width="2.4" height="5"/><rect x="2.2" y="18" width="2.6" height="8.4" rx="1.3"/><rect x="43.2" y="18" width="2.6" height="8.4" rx="1.3"/><path mask="url(#chatballs-launcher-face)" d="M14 9.2h20a6.8 6.8 0 0 1 6.8 6.8v12.4a6.8 6.8 0 0 1-6.8 6.8H21.6l-6.4 5.2a.9.9 0 0 1-1.5-.7v-4.5h-.3A6.8 6.8 0 0 1 7.2 28.4V16A6.8 6.8 0 0 1 14 9.2Z"/></svg>';
  var CHEVRON_ICON = '<svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" style="flex:none"><polyline points="6 9 12 15 18 9"/></svg>';

  var btn = document.createElement("button");
  btn.className = "chatballs-chat-launcher cb-launcher";
  btn.type = "button";
  btn.setAttribute("aria-label", "Открыть чат");
  btn.innerHTML = BOT_ICON;

  var dot = document.createElement("span");
  dot.className = "chatballs-chat-dot";
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
    btn.classList.remove("chatballs-chat-message-bump");
    void btn.offsetWidth;
    btn.classList.add("chatballs-chat-message-bump");
    window.setTimeout(function () { btn.classList.remove("chatballs-chat-message-bump"); }, 450);
  }

  function setCallActive(active) {
    callActive = active;
    btn.classList.toggle("chatballs-chat-call-shake", active);
    if (active) play(ringtone);
    else {
      ringtone.pause();
      ringtone.currentTime = 0;
    }
    updateDot();
  }
