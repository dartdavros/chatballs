import { useEffect, useMemo, useRef, useState } from "react";

import { ShopRequestError, storefrontApi } from "../shopApi";
import { initialDraft, type LiveQuote, type PartyResponse, type ProposalDraft, type ProposalResult } from "./model";

type Stored = {draft?: ProposalDraft; result?: ProposalResult};

function readStored(key: string): Stored {
  try {
    return JSON.parse(sessionStorage.getItem(key) || "{}") ?? {};
  } catch {
    return {};
  }
}

function errorCode(error: unknown) {
  return error instanceof ShopRequestError ? error.code : "unavailable";
}

export function useProposal(token: string) {
  const key = `north-wind-quote:${token}`;
  const api = useMemo(() => storefrontApi(token), [token]);
  const [draft, setDraft] = useState(() => readStored(key).draft ?? initialDraft);
  const [result, setResult] = useState(() => readStored(key).result ?? null);
  const [catalogue, setCatalogue] = useState<PartyResponse | null>(null);
  const [calculation, setCalculation] = useState<{key: string; quote: LiveQuote} | null>(null);
  const [review, setReview] = useState(0);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const submission = useRef<{fingerprint: string; id: string} | null>(null);
  const submitting = useRef(false);
  const {productId, quantities, city, budget} = draft;
  const selection = JSON.stringify({productId, quantities, city, budget, review});
  const quote = calculation?.key === selection ? calculation.quote : null;

  useEffect(() => {
    try {
      sessionStorage.setItem(key, JSON.stringify({draft, result}));
    } catch {
      // The form also works when browser storage is unavailable.
    }
  }, [key, draft, result]);

  useEffect(() => {
    if (result) return;
    let active = true;
    const update = setTimeout(async () => {
      const values = {
        quantities: Object.fromEntries(Object.entries(quantities).filter(([, count]) => count > 0)),
        city, budget,
      };
      try {
        const options = await api<PartyResponse>("proposal/options", values);
        if (!active) return;
        setCatalogue(options);
        if (!productId || !options.options.some(option => option.id === productId && option.available && option.withinBudget)) return;
        const next = await api<LiveQuote>("proposal/quote", {...values, product_id: productId}, crypto.randomUUID());
        if (active) setCalculation({key: selection, quote: next});
      } catch (failure) {
        if (active) setError(errorCode(failure));
      }
    }, 200);
    return () => { active = false; clearTimeout(update); };
  }, [api, budget, city, productId, quantities, result, selection]);

  useEffect(() => {
    if (!quote) return;
    const refresh = setTimeout(() => setReview(previous => previous + 1),
      Math.max(250, Date.parse(quote.validUntil) - Date.now()));
    return () => clearTimeout(refresh);
  }, [quote]);

  useEffect(() => {
    if (result?.mail.status !== "queued") return;
    let active = true;
    const timer = setInterval(async () => {
      try {
        const next = await api<ProposalResult>("proposal/status", {
          number: result.proposal.number, quote_id: result.proposal.quoteId,
        });
        if (active && next.mail.status !== "queued") setResult(next);
      } catch (failure) {
        if (active) setError(errorCode(failure));
      }
    }, 1500);
    return () => { active = false; clearInterval(timer); };
  }, [api, result]);

  function update(changes: Partial<ProposalDraft>) {
    setError("");
    setDraft(previous => ({
      ...previous, ...changes,
      confirmed: changes.email !== undefined ? false : changes.confirmed ?? previous.confirmed,
    }));
  }

  async function submit() {
    if (submitting.current || !quote || !draft.confirmed) return;
    const values = {
      quote_id: quote.id, company: draft.company, contact: draft.contact,
      address: draft.address, email: draft.email.trim().toLowerCase(), confirmed: true,
    };
    const fingerprint = JSON.stringify(values);
    const id = submission.current?.fingerprint === fingerprint ? submission.current.id : crypto.randomUUID();
    submission.current = {fingerprint, id};
    submitting.current = true;
    setError("");
    setPending(true);
    try {
      setResult(await api<ProposalResult>("proposal/submit", values, id));
    } catch (failure) {
      const code = errorCode(failure);
      setError(code);
      if (["quote_changed", "party_stock_unavailable", "party_budget_exceeded"].includes(code)) {
        setReview(previous => previous + 1);
      }
    } finally {
      submitting.current = false;
      setPending(false);
    }
  }

  return {draft, catalogue, quote, result, pending, error, update, submit};
}
