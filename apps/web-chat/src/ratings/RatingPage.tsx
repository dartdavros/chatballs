import type { CSSProperties } from "react";
import { RatingForm } from "./RatingForm";
import { RatingOutcome } from "./RatingOutcome";
import { useRating } from "./useRating";
import "./rating.css";

export function RatingPage() {
  const rating = useRating();
  const presentation = rating.presentation;
  return <main className="rating-page" style={{ "--rating-brand": presentation?.accent } as CSSProperties}>
    <header>{presentation && <><span>{presentation.name.slice(0, 1)}</span><strong>{presentation.name}</strong></>}</header>
    <div className="rating-page-body">
      {rating.state === "form" && <RatingForm rating={rating} />}
      {["thanks", "rated", "unavailable"].includes(rating.state) && <RatingOutcome rating={rating} />}
    </div>
  </main>;
}
