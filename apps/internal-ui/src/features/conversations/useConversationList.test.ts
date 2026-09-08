import { describe, expect, it } from "vitest";

import { mergeHead } from "./useConversationList";
import type { ApiConversation } from "./model";

function conversation(id: number, lastActivityAt = "2026-09-08T10:00:00Z"): ApiConversation {
  return { id, lastActivityAt } as ApiConversation;
}

describe("mergeHead", () => {
  it("ставит свежую голову перед уже загруженным хвостом", () => {
    const merged = mergeHead([conversation(9)], [conversation(3), conversation(2)]);
    expect(merged.map((item) => item.id)).toEqual([9, 3, 2]);
  });

  it("не оставляет дубль, когда диалог поднялся наверх", () => {
    // Диалогу 2 ответили: он приходит в голове и обязан исчезнуть из хвоста.
    const merged = mergeHead([conversation(2), conversation(9)], [conversation(3), conversation(2)]);
    expect(merged.map((item) => item.id)).toEqual([2, 9, 3]);
  });

  it("сохраняет хвост, которого нет в голове", () => {
    const merged = mergeHead([conversation(9)], [conversation(8), conversation(7)]);
    expect(merged).toHaveLength(3);
  });
});
