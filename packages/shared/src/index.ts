export type AttentionStatus = "NORMAL" | "ATTENTION" | "CRITICAL";

export type HubApplication = "internal-ui" | "web-chat";

export const defaultApiBaseUrl = "http://localhost:8000/api/v1";

export {
  DEFAULT_LANGUAGE,
  LANGUAGES,
  LANGUAGE_CODES,
  browserLanguage,
  createFormats,
  createI18n,
  createTranslator,
  currentLanguage,
  normalizeLanguage,
  onLanguageChange,
  setCurrentLanguage,
  resolveLanguage,
  type ByteUnitKey,
  type Catalog,
  type Formats,
  type I18n,
  type LanguageCode,
  type Message,
  type Params,
  type PluralCategory,
} from "./i18n";

export {
  CallRtcClient,
  type CallRtcHandlers,
  type CallSide,
  type PublicCallState,
  type RtcConnectionPhase,
} from "./callRtc";
