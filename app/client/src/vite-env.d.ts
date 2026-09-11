/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_DATA_MODE?: 'mock' | 'integration';
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
