  var siteInvitation = null;
  // Geometry and controls from the personally accepted visitor baseline.
  var invitationStyle = document.createElement("style");
  invitationStyle.textContent = ".chatballs-site-invitation{position:fixed;box-sizing:border-box;width:min(320px,calc(100vw - 48px));padding:18px 16px 14px;background:#fff;color:#262626;border:1px solid #eee;border-radius:12px;box-shadow:0 12px 40px rgba(0,0,0,.18);z-index:2147483001;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif}.chatballs-site-invitation p{font-size:15.5px;line-height:22px;margin:0 30px 18px 0;overflow-wrap:anywhere}.chatballs-site-invitation button{font:inherit;cursor:pointer}.chatballs-site-invitation .cb-start-button{display:block;width:100%;height:44px;border:0;border-radius:10px;background:var(--cb-accent);color:#fff;font-size:14px;font-weight:600}.chatballs-site-invitation .cb-composer-button{position:absolute;right:10px;top:10px;width:32px;height:32px;display:flex;align-items:center;justify-content:center;padding:0;border:0;background:transparent;color:#8c8c8c;border-radius:50%;transition:box-shadow .16s ease,transform .12s ease}.chatballs-site-invitation .cb-composer-button:hover{box-shadow:inset 0 0 0 999px rgba(0,0,0,.07)}.chatballs-site-invitation .cb-composer-button:active{transform:scale(.93)}";
  (document.head || document.documentElement).appendChild(invitationStyle);
  function layoutSiteInvitation() {
    if (!siteInvitation) return;
    siteInvitation.style.display = open ? "none" : "";
    siteInvitation.style.left = appearance.position === "left" ? "24px" : "";
    siteInvitation.style.right = appearance.position === "right" ? "24px" : "";
    siteInvitation.style.bottom = (appearance.size + 36) + "px";
    siteInvitation.style.setProperty("--cb-accent", appearance.accent);
  }
  function renderSiteInvitation(copy) {
    if (siteInvitation) { siteInvitation.remove(); siteInvitation = null; }
    if (!copy || typeof copy.text !== "string" || typeof copy.accept !== "string" || typeof copy.dismiss !== "string") return;
    siteInvitation = document.createElement("section");
    siteInvitation.className = "chatballs-site-invitation";
    siteInvitation.setAttribute("aria-label", copy.label);
    var text = document.createElement("p");
    text.textContent = copy.text;
    var dismiss = document.createElement("button");
    dismiss.type = "button"; dismiss.className = "wc-icon-button cb-composer-button";
    dismiss.setAttribute("aria-label", copy.dismiss);
    dismiss.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18M6 6l12 12"/></svg>';
    dismiss.addEventListener("click", function () { notifySiteEvent("dismiss"); renderSiteInvitation(null); btn.focus(); });
    var accept = document.createElement("button");
    accept.type = "button"; accept.className = "cb-start-button"; accept.textContent = copy.accept;
    accept.addEventListener("click", function () { notifySiteEvent("accept"); });
    siteInvitation.appendChild(text); siteInvitation.appendChild(dismiss); siteInvitation.appendChild(accept);
    document.body.appendChild(siteInvitation);
    layoutSiteInvitation();
  }
  window.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && siteInvitation && !open) {
      notifySiteEvent("dismiss"); renderSiteInvitation(null); btn.focus();
    }
  });
