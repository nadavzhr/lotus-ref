/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_WARD: string;
  readonly VITE_CELL: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
