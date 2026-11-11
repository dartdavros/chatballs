import { useEffect, useLayoutEffect, useState } from "react";

import { Icon } from "../../shared/icons";
import { t } from "../../i18n";
import { useOnboarding } from "./useOnboarding";

// Тур «Показать где»: приложение остаётся видимым, а нужный элемент —
// единственное светлое место на затемнённом экране.
//
// Геометрия слоёв повторяет дизайн-референс `design/baseline/Онбординг`:
// рамка цели с отступом 6px, обводка `0 0 0 2px` и поверх неё пульсирующее
// кольцо, разлетающееся до scale(1.45).
//
// Все слои абсолютные внутри `.hub-shell` и считают координаты от него: цель
// живёт в прокручиваемой колонке, и фиксированный слой уехал бы от неё при
// первой же прокрутке. Затемнение — четыре прямоугольника вокруг цели, а не
// один `box-shadow: 0 0 0 9999px`: так корректно выходит на скриншотах и при
// экспорте страницы.

const CALLOUT_WIDTH = 344;
const PAD = 6;

type Rect = { x: number; y: number; w: number; h: number };

function measure(element: string): { target: Rect; rootW: number; rootH: number } | null {
  const root = document.querySelector(".hub-shell");
  const target = document.querySelector(`[data-onboarding-target="${element}"]`);
  if (!(root instanceof HTMLElement) || !(target instanceof HTMLElement)) return null;
  const rootBox = root.getBoundingClientRect();
  const targetBox = target.getBoundingClientRect();
  if (targetBox.width === 0 && targetBox.height === 0) return null;
  return {
    target: { x: targetBox.left - rootBox.left, y: targetBox.top - rootBox.top, w: targetBox.width, h: targetBox.height },
    rootW: rootBox.width,
    rootH: rootBox.height,
  };
}

/** Конечные анимации, внутри которых лежит цель, — прежде всего въезд нового
 *  экрана (`surface-enter`, translateY 6px). Их надо дождаться: пока они идут,
 *  `getBoundingClientRect()` отдаёт позицию в полёте, причём композитная
 *  анимация повторяет одно и то же значение несколько кадров подряд, так что
 *  «подождать, пока перестанет меняться» здесь не работает. Бесконечные
 *  анимации (свой же пульс рамки, прелоадеры) пропускаем — их не дождаться. */
function settlingAnimations(target: Element): Promise<unknown>[] {
  return document.getAnimations().flatMap((animation) => {
    const effect = animation.effect;
    const owner = effect instanceof KeyframeEffect ? effect.target : null;
    if (!owner || !owner.contains(target)) return [];
    if (effect!.getComputedTiming().iterations === Infinity) return [];
    return [animation.finished.catch(() => undefined)];
  });
}

export function OnboardingTour() {
  const onboarding = useOnboarding();
  const tourIndex = onboarding?.tourIndex ?? null;
  const step = tourIndex === null ? null : onboarding?.steps[tourIndex] ?? null;
  const element = step?.target.element ?? null;
  const hideTour = onboarding?.hideTour;
  const [box, setBox] = useState<{ target: Rect; rootW: number; rootH: number } | null>(null);

  useLayoutEffect(() => {
    if (!element) {
      setBox(null);
      return;
    }
    // Экран за окном только что переключился: цель может ещё не смонтироваться,
    // а смонтировавшись — ехать вместе с новым маршрутом. Сначала ищем её по
    // кадрам, показываем подсветку сразу, а как экран встанет — перемеряем.
    // Если цель так и не нашлась (раздел пуст, элемент скрыт узким экраном),
    // возвращаем окно: иначе человек остался бы перед приложением без
    // единственного пути назад.
    let cancelled = false;
    let frame = 0;

    const apply = () => {
      const measured = measure(element);
      if (measured) setBox(measured);
    };

    const locate = (attempts: number) => {
      if (cancelled) return;
      const target = document.querySelector(`[data-onboarding-target="${element}"]`);
      const found = target instanceof HTMLElement && (target.offsetWidth > 0 || target.offsetHeight > 0);
      if (!found) {
        if (attempts >= 40) {
          hideTour?.();
          return;
        }
        frame = requestAnimationFrame(() => locate(attempts + 1));
        return;
      }
      // После переноса пунктов в главное меню цель может быть ниже прокрутки.
      target.scrollIntoView({ block: "nearest", inline: "nearest", behavior: "instant" });
      apply();
      void Promise.all(settlingAnimations(target)).then(() => {
        if (cancelled) return;
        frame = requestAnimationFrame(() => {
          if (!cancelled) apply();
        });
      });
    };

    locate(0);
    return () => {
      cancelled = true;
      cancelAnimationFrame(frame);
    };
  }, [element, hideTour]);

  useEffect(() => {
    if (!element) return;
    const remeasure = () => setBox(measure(element));
    window.addEventListener("resize", remeasure);
    window.addEventListener("scroll", remeasure, true);
    return () => {
      window.removeEventListener("resize", remeasure);
      window.removeEventListener("scroll", remeasure, true);
    };
  }, [element]);

  useEffect(() => {
    if (!element || !hideTour) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.stopPropagation();
        hideTour();
      }
    };
    window.addEventListener("keydown", onKey, true);
    return () => window.removeEventListener("keydown", onKey, true);
  }, [element, hideTour]);

  if (!onboarding || tourIndex === null || !step || !box) return null;

  const { target, rootW, rootH } = box;
  const px = (value: number) => `${Math.round(value)}px`;
  // Границы рамки цели: отступ 6px со всех сторон.
  const top = Math.max(0, target.y - PAD);
  const bottom = target.y + target.h + PAD;
  const left = Math.max(0, target.x - PAD);
  const right = target.x + target.w + PAD;
  const frame = { top: px(target.y - PAD), left: px(target.x - PAD), width: px(target.w + PAD * 2), height: px(target.h + PAD * 2) };
  // Колаут справа от цели, а если не помещается — слева.
  const preferred = target.x + target.w + 20;
  const calloutX = preferred + CALLOUT_WIDTH > rootW - 16 ? Math.max(16, target.x - CALLOUT_WIDTH - 20) : preferred;
  const calloutY = Math.min(Math.max(16, target.y - 14), Math.max(16, rootH - 250));

  return (
    <>
      <button className="ob-tour-backdrop" type="button" aria-label={t("onboarding.tour_ok")} onClick={onboarding.hideTour} />
      <div className="ob-tour-dim" style={{ left: 0, top: 0, right: 0, height: px(top) }} />
      <div className="ob-tour-dim" style={{ left: 0, top: px(bottom), right: 0, bottom: 0 }} />
      <div className="ob-tour-dim" style={{ left: 0, top: px(top), width: px(left), height: px(bottom - top) }} />
      <div className="ob-tour-dim" style={{ left: px(right), top: px(top), right: 0, height: px(bottom - top) }} />
      <div className="ob-tour-spot" style={frame} />
      <div className="ob-tour-ring" style={frame} />
      <div className="ob-tour-callout" style={{ top: px(calloutY), left: px(calloutX) }} role="dialog" aria-label={step.target.title}>
        <p className="ob-eyebrow">{t("onboarding.tour_eyebrow", { index: tourIndex + 1 })}</p>
        <strong>{step.target.title}</strong>
        <p>{step.target.text}</p>
        <button className="ob-tour-back" type="button" onClick={onboarding.hideTour} autoFocus>
          {t("onboarding.tour_ok")}
          <Icon name="chevronLeft" size={15} strokeWidth={1.9} />
        </button>
      </div>
    </>
  );
}
