/// <reference types="vite/client" />

interface ImportMetaEnv {
  // Dev-only: empty в production -> API/realtime на same-origin (ADR-CHATBALLS-0028 §10).
  readonly VITE_API_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
