export type AttentionStatus = "NORMAL" | "ATTENTION" | "CRITICAL";

export type HubApplication = "internal-ui" | "web-chat";

export const defaultApiBaseUrl = "http://localhost:8000/api/v1";

export {
  CallRtcClient,
  type CallRtcHandlers,
  type CallSide,
  type PublicCallState,
  type RtcConnectionPhase,
} from "./callRtc";
