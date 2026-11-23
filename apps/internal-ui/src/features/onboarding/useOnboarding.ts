import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import type { SettingsSectionKey } from "../settings/sections";
import type { RouteKey, SessionUser } from "../../types";
import { canManagePlatform, isManager } from "../../auth/access";
import { PENDING_STATE, fetchOnboarding, postOnboardingAction, type OnboardingState } from "./api";
import { type OnboardingStep } from "./steps";
import { operationModeSteps } from "./operationModeSteps";
import { t } from "../../i18n";
import { useRealtimeEvent } from "../realtime/RealtimeProvider";

// Состояние онбординга на одну сессию рабочего места.
//
// Живёт контекстом, а не пропсами: визард монтируется в Shell, а ссылка
// «Начало работы» — в субменю «Настроек», глубоко в дереве страницы. Тянуть
// один и тот же прогресс двумя маршрутами дороже, чем один провайдер.

export type OnboardingView = "welcome" | "steps" | "done" | null;

export type OnboardingApi = {
  /** Шаги, доступные этому человеку: у не-администратора установки их семь. */
  steps: OnboardingStep[];
  state: OnboardingState;
  view: OnboardingView;
  index: number;
  /** Шаг, чьё место показывает тур; модалка на это время прячется. */
  tourIndex: number | null;
  doneCount: number;
  /** Заголовок приветствия числом-словом, как в макете: «Восемь шагов…». */
  welcomeTitle: string;
  /** Возврат после открытия раздела, пока пользователь явно не закрыл мастер. */
  showLauncher: boolean;
  available: boolean;
  open: () => void;
  openWelcome: () => void;
  startSteps: () => void;
  goTo: (index: number) => void;
  next: () => void;
  back: () => void;
  showTour: () => void;
  hideTour: () => void;
  openSection: () => void;
  dismiss: () => void;
  complete: () => void;
  completeToChat: () => void;
  restart: () => void;
};

const OnboardingContext = createContext<OnboardingApi | null>(null);

export const OnboardingProvider = OnboardingContext.Provider;

/** Внутри Shell контекст есть всегда; заглушка нужна тестам отдельных страниц. */
export function useOnboarding(): OnboardingApi | null {
  return useContext(OnboardingContext);
}

export function useOnboardingState({ user, setRoute, openSettings }: {
  user: SessionUser;
  setRoute: (route: RouteKey) => void;
  openSettings: (section: SettingsSectionKey | null) => void;
}): OnboardingApi {
  const available = isManager(user);
  const [state, setState] = useState<OnboardingState>(PENDING_STATE);
  const platformAccess = canManagePlatform(user);
  const steps = useMemo(() => operationModeSteps(platformAccess, state.operationMode), [platformAccess, state.operationMode]);
  const [loaded, setLoaded] = useState(false);
  const [closedInSession, setClosedInSession] = useState(false);
  const [view, setView] = useState<OnboardingView>(null);
  const [index, setIndex] = useState(0);
  const [tourIndex, setTourIndex] = useState<number | null>(null);

  const refresh = useCallback(async () => {
    try {
      setState(await fetchOnboarding());
    } catch {
      // Молчим: онбординг — подсказка, а не рабочая функция. Не смог
      // загрузиться — просто не показывается.
    }
  }, []);

  useEffect(() => {
    if (!available) return;
    let cancelled = false;
    fetchOnboarding()
      .then((payload) => {
        if (cancelled) return;
        setState(payload);
        setLoaded(true);
        // Ни закрывал, ни проходил — значит видит визард при этом входе,
        // сколько бы он ни работал в системе до сегодня.
        if (!payload.dismissedAt && !payload.completedAt) setView("welcome");
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [available]);

  useRealtimeEvent("organization.changed", () => { if (available) void refresh(); });

  const act = useCallback(async (action: "dismiss" | "complete" | "restart") => {
    try {
      setState(await postOnboardingAction(action));
    } catch {
      // Не записалось — визард всё равно закрыт до конца сессии.
    }
  }, []);

  const doneCount = steps.filter((step) => state.steps[step.key]).length;

  const goTo = useCallback((next: number) => {
    setIndex(Math.max(0, Math.min(steps.length - 1, next)));
    setTourIndex(null);
  }, [steps.length]);

  // Стабильная ссылка: тур вызывает её из эффекта замера, и меняющаяся
  // функция перезапускала бы замер на каждом рендере Shell.
  const hideTour = useCallback(() => setTourIndex(null), []);

  function closeWizard(action: "dismiss" | "complete") {
    setClosedInSession(true);
    setTourIndex(null);
    setView(null);
    void act(action);
  }

  const api: OnboardingApi = {
    steps,
    state,
    view,
    index,
    tourIndex,
    doneCount,
    // Шагов бывает семь или восемь — по одному заголовку на каждый случай:
    // в макете число написано словом, а не цифрой.
    welcomeTitle: state.operationMode === "OPERATORS_ONLY" ? t("onboarding.welcome_operators") : steps.length === 7 ? t("onboarding.welcome_title_7") : t("onboarding.welcome_title_8"),
    available,
    showLauncher: available && loaded && !closedInSession && !state.dismissedAt && !state.completedAt
      && view === null && tourIndex === null && doneCount < steps.length,
    open: () => {
      void refresh();
      setIndex(0);
      setView("steps");
    },
    openWelcome: () => {
      void refresh();
      setIndex(0);
      setView("welcome");
    },
    startSteps: () => {
      setIndex(0);
      setView("steps");
    },
    goTo,
    next: () => {
      if (index >= steps.length - 1) {
        void refresh();
        setView("done");
        return;
      }
      goTo(index + 1);
    },
    back: () => {
      if (index === 0) {
        setView("welcome");
        return;
      }
      goTo(index - 1);
    },
    showTour: () => {
      const step = steps[index];
      if (!step) return;
      // Раздел «Настроек» открывается одним вызовом вместе с маршрутом.
      if (step.target.section) openSettings(step.target.section);
      else setRoute(step.target.route);
      setTourIndex(index);
    },
    hideTour,
    openSection: () => {
      const step = steps[index];
      if (!step) return;
      if (step.target.section) openSettings(step.target.section);
      else setRoute(step.target.route);
      // Переход из шага временно прячет мастер, до явного закрытия.
      setTourIndex(null);
      setView(null);
    },
    dismiss: () => closeWizard("dismiss"),
    complete: () => closeWizard("complete"),
    completeToChat: () => {
      closeWizard("complete");
      setRoute("chat");
    },
    restart: () => {
      setIndex(0);
      setView("welcome");
      void act("restart");
    },
  };

  return api;
}
