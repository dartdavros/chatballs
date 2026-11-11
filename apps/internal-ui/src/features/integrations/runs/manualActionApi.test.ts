import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../../../api/client";
import { getManualAction, getManualActions } from "./api";

vi.mock("../../../api/client", () => ({ api: vi.fn() }));
beforeEach(() => vi.mocked(api).mockReset());

describe("manual action picker API", () => {
  it("requests a lightweight conversation-scoped list and supports cancelling it", async () => {
    const signal = new AbortController().signal;
    vi.mocked(api).mockResolvedValue({ items: [], files: [] });
    await getManualActions(42, signal);
    expect(api).toHaveBeenCalledExactlyOnceWith("/api/v1/integrations/run-actions/?conversation=42&summary=1", { signal });
  });

  it("loads the selected exact identity with GET without previewing or launching it", async () => {
    const signal = new AbortController().signal;
    const result = { item: { id: "chatballs:contacts.get", kind: "operation" }, files: [] };
    vi.mocked(api).mockResolvedValue(result);
    expect(await getManualAction(73, { id: "chatballs:contacts.get", kind: "operation" }, signal)).toBe(result);
    expect(api).toHaveBeenCalledExactlyOnceWith("/api/v1/integrations/run-actions/?conversation=73&kind=operation&id=chatballs%3Acontacts.get", { signal });
  });
});
