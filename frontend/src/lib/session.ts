import type { AskResponse, UploadResponse } from "./types";

export type UserMessage = { id: string; role: "user"; text: string; at: number };
export type AssistantMessage = {
  id: string;
  role: "assistant";
  at: number;
  status: "loading" | "done" | "error";
  question: string; // kept so a failed question can be retried
  response?: AskResponse;
  error?: string;
};
export type Message = UserMessage | AssistantMessage;

export type ActiveCitation = { messageId: string; n: number; nonce: number } | null;

export type State = {
  doc: UploadResponse | null;
  uploading: boolean;
  uploadError: string | null;
  messages: Message[];
  selectedMessageId: string | null; // whose sources the side panel shows
  activeCitation: ActiveCitation; // last clicked [n] chip (nonce re-triggers the flash)
};

export const initialState: State = {
  doc: null,
  uploading: false,
  uploadError: null,
  messages: [],
  selectedMessageId: null,
  activeCitation: null,
};

export type Action =
  | { type: "upload_started" }
  | { type: "upload_succeeded"; doc: UploadResponse }
  | { type: "upload_failed"; error: string }
  | { type: "question_asked"; userId: string; assistantId: string; text: string; at: number }
  | { type: "retry"; assistantId: string }
  | { type: "answer_received"; assistantId: string; response: AskResponse }
  | { type: "answer_failed"; assistantId: string; error: string }
  | { type: "select_message"; messageId: string }
  | { type: "cite_clicked"; messageId: string; n: number }
  | { type: "reset" };

export function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "upload_started":
      return { ...state, uploading: true, uploadError: null };
    case "upload_succeeded":
      // A new document starts a fresh conversation.
      return { ...initialState, doc: action.doc };
    case "upload_failed":
      return { ...state, uploading: false, uploadError: action.error };
    case "question_asked":
      return {
        ...state,
        messages: [
          ...state.messages,
          { id: action.userId, role: "user", text: action.text, at: action.at },
          { id: action.assistantId, role: "assistant", status: "loading", question: action.text, at: action.at },
        ],
      };
    case "retry":
      return updateAssistant(state, action.assistantId, { status: "loading", error: undefined });
    case "answer_received":
      return {
        ...updateAssistant(state, action.assistantId, { status: "done", response: action.response, at: Date.now() }),
        selectedMessageId: action.assistantId, // newest answer's sources show in the panel
      };
    case "answer_failed":
      return updateAssistant(state, action.assistantId, { status: "error", error: action.error });
    case "select_message":
      return { ...state, selectedMessageId: action.messageId };
    case "cite_clicked":
      return {
        ...state,
        selectedMessageId: action.messageId,
        activeCitation: { messageId: action.messageId, n: action.n, nonce: (state.activeCitation?.nonce ?? 0) + 1 },
      };
    case "reset":
      return initialState;
  }
}

function updateAssistant(state: State, id: string, patch: Partial<AssistantMessage>): State {
  return {
    ...state,
    messages: state.messages.map((m) => (m.id === id && m.role === "assistant" ? { ...m, ...patch } : m)),
  };
}

export function selectedResponse(state: State): AskResponse | undefined {
  const m = state.messages.find((x) => x.id === state.selectedMessageId);
  return m?.role === "assistant" ? m.response : undefined;
}

export function citedCount(r: AskResponse | undefined): number {
  return r ? r.sources.filter((s) => s.cited).length : 0;
}
