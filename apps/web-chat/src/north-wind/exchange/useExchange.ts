import { useEffect, useMemo, useRef, useState } from "react";

import type { Size, StoreId } from "../model";
import { ShopRequestError, storefrontApi } from "../shopApi";
import { mountShopWidget, openPreparedShopWidget, openShopWidget } from "../widgetLauncher";
import type { ExchangeOptions, Request, VerifiedOrder } from "./model";

type Phase = "order" | "select" | "confirm" | "done" | "defect";

export function useExchange(token: string, orderNumber: number, widgetKey: string, prepared: boolean) {
  const api = useMemo(() => storefrontApi(token), [token]);
  const [verified, setVerified] = useState<VerifiedOrder | null>(null);
  const [phase, setPhase] = useState<Phase>("order");
  const [size, setSize] = useState<Size>("XL");
  const [store, setStore] = useState<StoreId>("gorki");
  const [lookup, setLookup] = useState<{size: Size; value: ExchangeOptions} | null>(null);
  const [result, setResult] = useState<Request | null>(null);
  const [revision, refresh] = useState(0);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const submission = useRef<{signature: string; key: string} | null>(null);
  const writing = useRef(false);
  const chatKey = useRef("");
  const openingChat = useRef(false);
  const options = lookup?.size === size ? lookup.value : null;

  useEffect(() => {
    let current = true;
    api<VerifiedOrder>("exchange/order", {order_number: orderNumber}).then(value => {
      if (!current) return;
      setVerified(value);
      setResult(value.exchange);
      if (value.exchange) setPhase("done");
      if (value.order.size === "XL") setSize("L");
    }).catch(failure => {
      if (current) setError(failure instanceof ShopRequestError && failure.code === "order_unavailable"
        ? failure.code : "unavailable");
    });
    return () => { current = false; };
  }, [api, orderNumber]);

  useEffect(() => {
    if (phase !== "select") return;
    let current = true;
    api<ExchangeOptions>("exchange/options", {order_number: orderNumber, target_size: size}).then(value => {
      if (!current) return;
      setLookup({size, value});
      setStore(previous => value.pickupPoints.find(point => point.available && point.store === previous)?.store
        ?? value.pickupPoints.find(point => point.available)?.store ?? previous);
    }).catch(() => { if (current) setError("unavailable"); });
    return () => { current = false; };
  }, [api, orderNumber, phase, revision, size]);

  function changePhase(next: Phase) {
    setError("");
    setPhase(next);
  }

  async function confirm() {
    if (writing.current || !options?.pickupPoints.some(point => point.store === store && point.available)) return;
    const values = {order_number: orderNumber, target_size: size, store, confirmed: true};
    const signature = JSON.stringify(values);
    const key = submission.current?.signature === signature ? submission.current.key : crypto.randomUUID();
    submission.current = {signature, key};
    writing.current = true;
    setPending(true);
    setError("");
    try {
      setResult(await api<Request>("exchange/submit", values, key));
      setPhase("done");
    } catch (failure) {
      const code = failure instanceof ShopRequestError ? failure.code : "unavailable";
      setError(code);
      if (failure instanceof ShopRequestError && failure.status === 409) {
        setLookup(null);
        refresh(previous => previous + 1);
        setPhase("select");
      }
    } finally {
      writing.current = false;
      setPending(false);
    }
  }

  async function startChat() {
    if (openingChat.current) return;
    openingChat.current = true;
    setError("");
    try {
      if (prepared && !chatKey.current) {
        const session = await api<{widgetKey: string; token: string}>("exchange/chat", {order_number: orderNumber});
        await openPreparedShopWidget(session);
        chatKey.current = session.widgetKey;
        return;
      }
      await mountShopWidget(chatKey.current || widgetKey);
      openShopWidget();
    } catch {
      setError("unavailable");
    } finally {
      openingChat.current = false;
    }
  }

  return {phase, verified, options, result, size, store, pending, error, setSize, setStore, changePhase, confirm, startChat};
}
