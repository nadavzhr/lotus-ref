/**
 * Edit Store — manages the state of the right-side editing sheet.
 *
 * Isolated from the document store per the plan's state-isolation
 * principle. Tracks which document/line is being edited, the current
 * session data, hydration state, and validation results.
 */

import { create } from "zustand";

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

/** AF session data as returned by hydrate_session */
export interface AfSessionData {
  template: string | null;
  net: string;
  af_value: number;
  is_template_regex: boolean;
  is_net_regex: boolean;
  is_em_enabled: boolean;
  is_sh_enabled: boolean;
  is_sch_enabled: boolean;
}

/** A single mutex entry with full metadata */
export interface MutexEntryData {
  net_name: string;
  template_name: string | null;
  regex_mode: boolean;
  match_count: number;
}

/** Mutex session data — rich format matching the backend session response */
export interface MutexSessionData {
  template: string | null;
  regex_mode: boolean | null;
  num_active: number;
  fev: string;
  mutexed_entries: MutexEntryData[];
  active_entries: MutexEntryData[];
}

export type SessionData = AfSessionData | MutexSessionData;

export interface EditState {
  /** Is the edit sheet currently open? */
  isOpen: boolean;
  /** Document being edited */
  docId: string | null;
  /** Line position being edited */
  position: number | null;
  /** Document type of the line being edited */
  docType: "af" | "mutex" | null;
  /** Viewport-Y of the row that triggered the edit (for dialog animation) */
  originY: number | null;
  /** Current session data from the backend */
  sessionData: SessionData | null;
  /** Whether hydration is in progress */
  loading: boolean;
  /** Whether a commit is in progress */
  committing: boolean;
  /** Validation errors from the last commit attempt */
  errors: string[];
  /** Validation warnings */
  warnings: string[];
}

interface EditStoreActions {
  /** Open the edit sheet for a specific line */
  openEdit: (
    docId: string,
    position: number,
    docType: "af" | "mutex",
    originY?: number,
  ) => void;
  /** Close the edit sheet without committing */
  closeEdit: () => void;
  /** Set session data (from hydrate response) */
  setSessionData: (data: SessionData) => void;
  /** Set loading state */
  setLoading: (loading: boolean) => void;
  /** Set committing state */
  setCommitting: (committing: boolean) => void;
  /** Set validation results */
  setValidation: (errors: string[], warnings: string[]) => void;
  /** Clear validation */
  clearValidation: () => void;
  /** Update a single field in the session data */
  updateField: (field: string, value: unknown) => void;
}

type EditStore = EditState & EditStoreActions;

const initialState: EditState = {
  isOpen: false,
  docId: null,
  position: null,
  docType: null,
  originY: null,
  sessionData: null,
  loading: false,
  committing: false,
  errors: [],
  warnings: [],
};

export const useEditStore = create<EditStore>((set) => ({
  ...initialState,

  openEdit: (docId, position, docType, originY) => {
    set({
      isOpen: true,
      docId,
      position,
      docType,
      originY: originY ?? null,
      sessionData: null,
      loading: true,
      committing: false,
      errors: [],
      warnings: [],
    });
  },

  closeEdit: () => {
    set(initialState);
  },

  setSessionData: (data) => {
    set({ sessionData: data, loading: false });
  },

  setLoading: (loading) => {
    set({ loading });
  },

  setCommitting: (committing) => {
    set({ committing });
  },

  setValidation: (errors, warnings) => {
    set({ errors, warnings });
  },

  clearValidation: () => {
    set({ errors: [], warnings: [] });
  },

  updateField: (field, value) => {
    set((s) => {
      if (!s.sessionData) return s;
      return {
        sessionData: { ...s.sessionData, [field]: value },
      };
    });
  },
}));
