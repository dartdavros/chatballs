function installIconSprite() {
  if (!window.CHATBALLS_ICON_SPRITE || document.querySelector("[data-chatballs-icon-sprite]")) return;
  const container = document.createElement("div");
  container.hidden = true;
  container.dataset.chatballsIconSprite = "";
  container.innerHTML = window.CHATBALLS_ICON_SPRITE;
  document.body.prepend(container);
}

const pages = [
  ["index", "index.html", "Обзор", "grid"],
  ["foundations", "foundations.html", "Токены", "box"],
  ["components", "components.html", "Компоненты", "columns"],
  ["data-display", "data-display.html", "Данные и статусы", "list"],
  ["patterns", "patterns.html", "Паттерны", "settings"],
  ["layouts", "layouts.html", "Макеты страниц", "grid"],
  ["inventory", "inventory.html", "Инвентарь", "search"],
];

function icon(name) {
  return `<svg class="icon" aria-hidden="true"><use href="#i-${name}"></use></svg>`;
}

function buildSidebar() {
  const activePage = document.body.dataset.page || "index";
  const nav = pages.map(([key, href, label, iconName], index) => {
    const group = index === 0 ? '<div class="ds-nav-group">Система</div>' : index === 1 ? '<div class="ds-nav-group">Справочник</div>' : "";
    const active = key === activePage ? " is-active" : "";
    return `${group}<a class="${active.trim()}" href="${href}">${icon(iconName)}<span>${label}</span></a>`;
  }).join("");

  const sidebar = document.querySelector("[data-ds-sidebar]");
  if (!sidebar) return;
  sidebar.innerHTML = `
    <a class="ds-brand" href="index.html">
      <span class="ds-brand-mark">C</span>
      <span><strong>Chatballs</strong><small>Design System</small></span>
    </a>
    <nav class="ds-nav" aria-label="Разделы дизайн-системы">${nav}</nav>
    <div class="ds-sidebar-footer">Статический каталог текущего frontend UI.<br>Источник: <code>apps/internal-ui/src</code></div>
  `;
}

function activateInteractiveExamples() {
  document.querySelectorAll("[data-segmented]").forEach((group) => {
    group.addEventListener("click", (event) => {
      const button = event.target.closest("button");
      if (!button) return;
      group.querySelectorAll("button").forEach((item) => item.classList.toggle("active", item === button));
    });
  });

  document.querySelectorAll("[data-tabs]").forEach((group) => {
    group.addEventListener("click", (event) => {
      const button = event.target.closest("button");
      if (!button || button.disabled) return;
      group.querySelectorAll("button").forEach((item) => item.classList.toggle("active", item === button));
    });
  });

  document.querySelectorAll(".ui-switch").forEach((switchButton) => {
    switchButton.addEventListener("click", () => {
      if (switchButton.disabled) return;
      const checked = switchButton.classList.toggle("on");
      switchButton.setAttribute("aria-checked", String(checked));
    });
  });

  document.querySelectorAll("[data-open-dialog]").forEach((button) => {
    button.addEventListener("click", () => {
      const dialog = document.getElementById(button.dataset.openDialog);
      dialog?.classList.add("is-open");
    });
  });

  document.querySelectorAll("[data-close-dialog]").forEach((button) => {
    button.addEventListener("click", () => button.closest(".dialog-backdrop")?.classList.remove("is-open"));
  });

  document.querySelectorAll(".dialog-backdrop").forEach((backdrop) => {
    backdrop.addEventListener("click", (event) => {
      if (event.target === backdrop) backdrop.classList.remove("is-open");
    });
  });
}

function activateInventorySearch() {
  const input = document.querySelector("[data-inventory-search]");
  const rows = [...document.querySelectorAll("[data-inventory-row]")];
  const count = document.querySelector("[data-inventory-count]");
  if (!input || rows.length === 0) return;

  const update = () => {
    const query = input.value.trim().toLowerCase();
    let visible = 0;
    rows.forEach((row) => {
      const matches = row.textContent.toLowerCase().includes(query);
      row.hidden = !matches;
      if (matches) visible += 1;
    });
    if (count) count.textContent = `Показано: ${visible}`;
  };

  input.addEventListener("input", update);
  update();
}

function addCopyButtons() {
  document.querySelectorAll("[data-copy]").forEach((button) => {
    button.addEventListener("click", async () => {
      const value = button.dataset.copy;
      if (!value) return;
      try {
        await navigator.clipboard.writeText(value);
        const original = button.textContent;
        button.textContent = "Скопировано";
        setTimeout(() => { button.textContent = original; }, 900);
      } catch {
        button.title = value;
      }
    });
  });
}

function renderInventory() {
  const body = document.querySelector("[data-inventory-body]");
  const payload = window.CHATBALLS_INVENTORY;
  if (!body || !payload) return;

  body.innerHTML = payload.items.map((item) => {
    const name = item.documentedAt
      ? `<a class="link is-neutral" href="${item.documentedAt}">${item.name}</a>`
      : item.name;
    return `<tr data-inventory-row>
      <td><strong>${name}</strong><small style="display:block;margin-top:3px;color:#bfbfbf">${item.visibility}</small></td>
      <td>${item.kind}</td>
      <td>${item.category}</td>
      <td><span class="ds-chip">${item.scope}</span></td>
      <td><code class="ds-code">${item.source}</code></td>
      <td>${item.variants}</td>
    </tr>`;
  }).join("");

  const total = document.querySelector("[data-inventory-total]");
  if (total) total.textContent = String(payload.count);
}

installIconSprite();
buildSidebar();
renderInventory();
activateInteractiveExamples();
activateInventorySearch();
addCopyButtons();
