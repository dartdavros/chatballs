import { useEffect, useRef, useState } from "react";
import type { SiteEventState } from "@chatballs/contracts";
import type { WebConfig } from "../api";
import { t } from "../i18n";
import { cancelEvent, sendEvent } from "./api";
import { SiteEventMemory, SITE_EVENT_TTL, validEvent } from "./memory";

type Options = { config: WebConfig | null; token: string | null; accepted: boolean; consentReady: boolean;
  widgetKey: string; hostOrigin: string };

export function useSiteEvents(options: Options) {
  const { config, token, accepted, consentReady, widgetKey, hostOrigin } = options;
  const instanceId = new URLSearchParams(location.search).get("instanceId") || "";
  const [memory] = useState(() => new SiteEventMemory(`chatballs-site-event:${hostOrigin}:${widgetKey}`, sessionStorage));
  const [revision, refresh] = useState(0);
  const [status, setStatus] = useState<SiteEventState | "expired" | null>(null);
  const [related, setRelated] = useState(false);
  const sending = useRef(false), cancelled = useRef(false);
  const current = useRef(options);
  current.current = options;
  const post = (type: string, fields: Record<string, unknown> = {}) => window.parent.postMessage(
    { type, instanceId, widgetKey, ...fields }, hostOrigin);

  function cancel() {
    memory.clear();
    cancelled.current = true;
    post("chatballs-site-event-invitation", { invitation: null });
    setStatus(null);
    const state = current.current;
    if (state.token && state.accepted && sending.current) void cancelEvent(state.token, hostOrigin).catch(() => undefined);
  }

  useEffect(() => {
    const receive = (message: MessageEvent) => {
      if (message.origin !== hostOrigin || message.source !== window.parent || !instanceId
        || message.data?.instanceId !== instanceId || message.data?.widgetKey !== widgetKey) return;
      const state = current.current;
      if (message.data.type === "chatballs-site-event") {
        const rule = state.config?.siteEvent;
        if (!state.consentReady || !rule || cancelled.current || sending.current || !validEvent(message.data.event, rule, widgetKey)
          || typeof message.data.receivedAt !== "number" || !Number.isFinite(message.data.receivedAt)) return;
        if (memory.receive(message.data.event, message.data.receivedAt, state.accepted)) { setRelated(true); refresh((n) => n + 1); }
      }
      if (message.data.type === "chatballs-site-event-control") {
        if (message.data.action === "focus") document.querySelector<HTMLButtonElement>(".cb-header button")?.focus();
        if (message.data.action === "accept") {
          if (memory.accept()) post("chatballs-site-event-open");
          else setStatus("expired");
        }
        else if (message.data.action === "dismiss" || message.data.action === "cancel") cancel();
        refresh((n) => n + 1);
      }
    };
    window.addEventListener("message", receive);
    return () => window.removeEventListener("message", receive);
  }, [memory, instanceId, widgetKey, hostOrigin]);

  useEffect(() => {
    if (config?.available && consentReady) post("chatballs-site-events-ready");
  }, [config?.available, consentReady, widgetKey, hostOrigin, instanceId]);

  useEffect(() => {
    const rule = config?.siteEvent;
    if (memory.pending && (!rule || !validEvent(memory.pending.event, rule, widgetKey))) memory.clear();
    if (memory.expire()) setStatus("expired");
    const active = memory.pending;
    post("chatballs-site-event-invitation", { invitation: active && !active.accepted && !accepted && rule ? {
      text: rule.invitation, label: t("site_events.invitation"), accept: t("site_events.accept"), dismiss: t("site_events.dismiss"),
    } : null });
    if (!active) return;
    const timer = setTimeout(() => {
      if (memory.expire()) { setStatus("expired"); refresh((n) => n + 1); }
    }, Math.max(0, SITE_EVENT_TTL - (Date.now() - active.receivedAt)));
    if (active.accepted && accepted && token && !sending.current) {
      sending.current = true;
      setStatus("pending");
      const event = active.event;
      memory.clear();
      post("chatballs-site-event-invitation", { invitation: null });
      void sendEvent(token, event, hostOrigin).then((result) => {
        if (cancelled.current) void cancelEvent(token, hostOrigin).catch(() => undefined);
        else if (result === "suppressed") setStatus("suppressed");
      }).catch(() => { if (!cancelled.current) { sending.current = false; setStatus("failed"); } });
    }
    return () => clearTimeout(timer);
  }, [revision, config?.siteEvent, accepted, token, memory]);

  return { status, related, updateStatus: (value: SiteEventState | null | undefined) => {
    if (value && !cancelled.current) { setRelated(true); setStatus(value); }
  }, cancel };
}
