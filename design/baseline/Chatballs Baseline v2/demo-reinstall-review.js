"use strict";

const states = {
  busy: {
    title: "Переустанавливаем демо-данные",
    detail: "Готовим исходные данные магазина и диалоги.",
    tone: "neutral",
  },
  success: {
    title: "Демо-данные переустановлены",
    detail: "Можно повторить сценарии магазина с начала.",
    tone: "success",
  },
  error: {
    title: "Не удалось переустановить демо-данные",
    detail: "Данные магазина не загрузились. Текущий набор доступен. Попробуйте ещё раз.",
    tone: "error",
  },
  conflict: {
    title: "Не удалось переустановить демо-данные",
    detail: "С демо-данными связан рабочий диалог. Откройте его и снимите связь перед повтором.",
    tone: "error",
  },
};

const selector = document.querySelector("#review-state");
const modal = document.querySelector("#confirm-reinstall");
const reinstall = document.querySelector("#reinstall");
const remove = document.querySelector("#remove");
const notice = document.querySelector("#operation-notice");
const loader = document.querySelector("#operation-loader");

function showState(state) {
  selector.value = state;
  const message = states[state];
  notice.hidden = !message;
  notice.dataset.tone = message?.tone ?? "";
  document.querySelector("#operation-title").textContent = message?.title ?? "";
  document.querySelector("#operation-detail").textContent = message?.detail ?? "";
  document.querySelector("#record-info").textContent = state === "success"
    ? "3 412 записей · 24 ноя"
    : "3 412 записей · 23 ноя";
  loader.hidden = state !== "busy";
  reinstall.disabled = state === "busy";
  remove.disabled = state === "busy";

  if (state === "confirm" && !modal.open) modal.showModal();
  if (state !== "confirm" && modal.open) modal.close();
}

reinstall.addEventListener("click", () => showState("confirm"));
selector.addEventListener("change", () => showState(selector.value));
document.querySelector("#review-theme").addEventListener("change", (event) => {
  document.documentElement.dataset.theme = event.target.value;
});
document.querySelector("#confirm-action").addEventListener("click", () => showState("busy"));
modal.querySelectorAll("[data-cancel]").forEach((button) => {
  button.addEventListener("click", () => showState("ready"));
});
modal.addEventListener("cancel", () => showState("ready"));

showState("ready");
