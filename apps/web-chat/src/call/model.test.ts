import { describe, expect, it, vi } from "vitest";

import type { CallInfo } from "../api";
import {
  buildAudioCallViewStatus,
  buildCallViewStatus,
  isTerminalCall,
  resolveAudioCallViewMode,
  resolveCallViewMode,
} from "./model";

const call: CallInfo = { callId: "call-1", status: "ACCEPTED", kind: "VIDEO", staffName: "Оператор" };
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

  it("keeps an audio invitation incoming until the customer accepts it", () => {
    expect(resolveAudioCallViewMode({
      loading: false,
      invalid: false,
      call: { ...call, kind: "AUDIO", status: "RINGING" },
      started: false,
      connection: "idle",
      mediaIssue: "none",
    })).toBe("incoming");
  });

  it("keeps a started audio call in reconnecting so the hang-up stays reachable", () => {
    expect(resolveAudioCallViewMode({
      loading: false,
      invalid: false,
      call: { ...call, kind: "AUDIO", status: "ACTIVE" },
      started: true,
      connection: "reconnecting",
      mediaIssue: "none",
    })).toBe("reconnecting");
  });

  it("never offers a call-back the customer cannot make", () => {
    for (const status of ["DECLINED", "MISSED", "EXPIRED", "CANCELLED", "ENDED"]) {
      const view = buildAudioCallViewStatus({
        loading: false,
        invalid: false,
        call: { ...call, kind: "AUDIO", status },
        connection: "idle",
        mediaIssue: "none",
        close: action,
      });
      expect(view?.bar, status).toBe("close");
    }
  });

  it("turns an audio action failure into a classified retry state", () => {
    const status = buildAudioCallViewStatus({
      loading: false,
      invalid: false,
      call: { ...call, kind: "AUDIO" },
      connection: "idle",
      mediaIssue: "none",
      errorText: "Приглашение уже нельзя принять",
      close: action,
    });
    expect(status).toMatchObject({
      icon: "alert",
      tone: "error",
      caption: "Приглашение уже нельзя принять",
      bar: "retryClose",
    });
  });
});
