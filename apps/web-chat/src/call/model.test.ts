import { describe, expect, it, vi } from "vitest";

import type { CallInfo } from "../api";
import { buildCallViewStatus, isTerminalCall, resolveCallViewMode } from "./model";

const call: CallInfo = { callId: "call-1", status: "ACCEPTED", staffName: "Оператор" };
const action = vi.fn();

describe("call view model", () => {
  it("keeps accepted call in pre-call until the client starts RTC", () => {
    expect(resolveCallViewMode({ loading: false, invalid: false, call, started: false, connection: "idle", mediaIssue: "none" })).toBe("precall");
  });

  it("shows reconnecting over an already started call", () => {
    expect(resolveCallViewMode({ loading: false, invalid: false, call: { ...call, status: "ACTIVE" }, started: true, connection: "reconnecting", mediaIssue: "none" })).toBe("reconnecting");
  });

  it("exposes baseline actions when media devices are unavailable", () => {
    const status = buildCallViewStatus({ loading: false, invalid: false, call, connection: "idle", mediaIssue: "devices", close: action, retry: action, prepare: action, join: action });
    expect(status?.title).toBe("Нет доступа к камере и микрофону");
    expect(status?.actions?.map((item) => item.label)).toEqual(["Повторить проверку", "Без видео"]);
    expect(isTerminalCall("ENDED")).toBe(true);
  });
});
