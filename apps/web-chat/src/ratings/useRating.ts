import { useEffect, useState } from "react";
import { applyWidgetLanguage } from "../i18n";
import { ratingApi, RatingError, type RatingQuestion, type RatingResult } from "./api";
import { readRatingHandoff } from "./handoff";

export function useRating() {
  const [entry] = useState(readRatingHandoff);
  const [question, setQuestion] = useState<RatingQuestion | null>(null);
  const [result, setResult] = useState<RatingResult | null>(null);
  const [value, setValue] = useState(entry?.value || 0);
  const [comment, setComment] = useState("");
  const [state, setState] = useState<"loading" | "form" | "thanks" | "rated" | "unavailable">(entry?.credential ? "loading" : "unavailable");
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    if (!entry?.credential) return;
    let active = true;
    applyWidgetLanguage(entry.presentation.language);
    ratingApi<RatingQuestion>(entry.credential).then(data => {
      if (!active) return;
      applyWidgetLanguage(data.presentation.language);
      setQuestion(data); setResult(data.result);
      setValue(previous => data.scale.some(choice => choice.value === previous) ? previous : 0);
      setState(data.result ? "rated" : "form");
    }).catch(problem => {
      if (!active) return;
      if (problem instanceof RatingError && problem.status === 404) setState("unavailable");
      else { setFailed(true); setState("form"); }
    });
    return () => { active = false; };
  }, [entry]);
  async function submit() {
    if (!entry?.credential || busy) return;
    setBusy(true); setFailed(false);
    try {
      if (!question) {
        const data = await ratingApi<RatingQuestion>(entry.credential);
        setQuestion(data); setResult(data.result); setState(data.result ? "rated" : "form");
        return;
      }
      if (!value) return;
      const data = await ratingApi<RatingResult>(entry.credential, { value, comment });
      setResult(data); setState("thanks");
    } catch (problem) {
      if (problem instanceof RatingError && problem.status === 404) setState("unavailable");
      else if (problem instanceof RatingError && problem.status === 409) {
        try { const data = await ratingApi<RatingQuestion>(entry.credential); setQuestion(data); setResult(data.result); setState("rated"); }
        catch { setFailed(true); }
      } else setFailed(true);
    } finally { setBusy(false); }
  }
  return { presentation: question?.presentation || entry?.presentation, question, result, value, setValue, comment, setComment, state, busy, failed, submit };
}
