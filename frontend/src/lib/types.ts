// Mirrors the Pydantic models in backend/app/main.py

export type UploadResponse = {
  doc_id: string;
  filename: string;
  pages: number;
  chunks: number;
};

export type Source = {
  n: number; // the [n] number used in the answer
  page: number;
  chunk_index: number;
  score: number; // cosine similarity, higher = more relevant
  content: string;
  cited: boolean; // did the answer reference [n]?
};

export type AskResponse = {
  answer: string;
  grounded: boolean; // false = score gate refused without calling the LLM
  sources: Source[];
};
