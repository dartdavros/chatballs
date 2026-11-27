  // Публичная конфигурация не должна мешать загрузке страницы хоста.
  var appearance = { accent: "#1677ff", rgb: [22, 119, 255], position: "right", size: 56, shape: "circle" };
  var launcherIcon = null;

  function choice(value, allowed, fallback) {
    if (value === undefined) return fallback;
    if (allowed.indexOf(value) < 0) throw new Error("Invalid launcher appearance");
    return value;
  }

  function readAppearance(config) {
    if (!config || config.available !== true) return null;
    var raw = config.appearance === undefined ? {} : config.appearance;
    if (!raw || typeof raw !== "object" || Array.isArray(raw)) throw new Error("Invalid appearance");
    var accent = raw.accent || config.accent || "#1677ff";
    if (typeof accent !== "string" || !/^#[0-9a-f]{6}$/i.test(accent)) throw new Error("Invalid accent");
    var icon = raw.launcherIcon || "";
    if (typeof icon !== "string") throw new Error("Invalid launcher icon");
    if (icon) {
      if (icon.length > 2048 || /[\x00-\x20\x7f\\]/.test(icon) ||
          !(/^(https?:\/\/|\/(?!\/))/i.test(icon))) throw new Error("Invalid launcher icon URL");
      icon = new URL(icon, origin).href;
    }
    return {
      accent: accent,
      rgb: [1, 3, 5].map(function (offset) { return parseInt(accent.slice(offset, offset + 2), 16); }),
      position: choice(raw.launcherPosition, ["left", "right"], "right"),
      size: choice(raw.launcherSize, [48, 56, 64], 56),
      shape: choice(raw.launcherShape, ["circle", "rounded", "square"], "circle"),
      theme: raw.theme === "dark" ? "dark" : "light",
      css: typeof raw.launcherCss === "string" ? raw.launcherCss : "",
      icon: icon
    };
  }

  function launcherRadius() {
    if (typeof btn !== "undefined" && typeof window !== "undefined" && window.getComputedStyle) {
      var corner = window.getComputedStyle(btn).borderTopLeftRadius;
      var radius = parseFloat(corner);
      if (Number.isFinite(radius)) return corner.indexOf("%") >= 0 ? btn.offsetWidth * radius / 100 : radius;
    }
    return appearance.shape === "square" ? 10 : appearance.size * (appearance.shape === "rounded" ? 0.3 : 0.5);
  }

  function launcherHeight() {
    return btn.offsetHeight || appearance.size;
  }

  function renderLauncher() {
    btn.innerHTML = open ? CHEVRON_ICON : BOT_ICON;
    if (!open && launcherIcon) {
      btn.textContent = "";
      btn.appendChild(launcherIcon);
    }
    btn.appendChild(dot);
  }

  function applyAppearance(next) {
    if (animating) {
      pendingAppearance = next;
      return;
    }
    appearance = next;
    btn.style.setProperty("--chatballs-accent", next.accent);
    btn.style.setProperty("--chatballs-accent-rgb", next.rgb.join(","));
    btn.style.left = next.position === "left" ? "24px" : "";
    btn.style.right = next.position === "right" ? "24px" : "";
    btn.style.setProperty("--chatballs-launcher-size", next.size + "px");
    btn.style.setProperty("--chatballs-launcher-radius", next.shape === "square" ? "10px" : next.shape === "rounded" ? "30%" : "50%");
    applyLauncherCss(next.css);
    layoutShell();
    if (!next.icon) return;
    // Загружаем как изображение, не вставляем SVG/URL в HTML страницы хоста.
    var image = document.createElement("img");
    image.alt = "";
    image.onload = function () {
      launcherIcon = image;
      renderLauncher();
    };
    image.onerror = function () {
      launcherIcon = null;
      renderLauncher();
    };
    image.src = next.icon;
  }

  function loadAppearance() {
    if (!window.fetch) return;
    var configUrl = origin + "/api/v1/webchat/config/?" + entryQuery + "&hostOrigin=" + encodeURIComponent(location.origin);
    window.fetch(configUrl, { cache: "no-cache", credentials: "omit" })
      .then(function (response) {
        if (!response.ok) throw new Error("Widget configuration unavailable");
        return response.json();
      })
      .then(function (config) {
        var next = readAppearance(config);
        if (next) applyAppearance(next);
      })
      .catch(function () { /* Стандартная кнопка уже смонтирована. */ });
  }
