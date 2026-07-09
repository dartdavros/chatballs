/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_PUBLIC_HUB_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
