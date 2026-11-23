const preview = document.getElementById("screen");

preview.addEventListener("load", () => {
  const screen = preview.contentDocument;
  if (!screen) return;
  const menus = ["role", "status"];

  function closeMenus() {
    for (const kind of menus) screen.getElementById(`${kind}-menu`).style.display = "none";
  }

  function activate(target) {
    const option = target.closest("[data-kind]");
    if (option) {
      screen.getElementById(`${option.dataset.kind}-value`).textContent = option.dataset.value;
      closeMenus();
      return;
    }
    const trigger = target.closest('[id$="-trigger"]');
    const kind = trigger?.id.replace("-trigger", "");
    if (!menus.includes(kind)) {
      closeMenus();
      return;
    }
    const menu = screen.getElementById(`${kind}-menu`);
    const opening = menu.style.display === "none";
    closeMenus();
    if (opening) menu.style.display = "inline";
  }

  screen.addEventListener("click", event => activate(event.target));
  screen.addEventListener("keydown", event => {
    if (event.key === "Escape") closeMenus();
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      activate(event.target);
    }
  });
});
