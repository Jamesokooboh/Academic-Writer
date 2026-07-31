const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const TOKEN_KEY = "academic_writer_token";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  window.localStorage.removeItem(TOKEN_KEY);
}

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new ApiError(response.status, body?.detail ?? response.statusText);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface UserOut {
  id: number;
  email: string;
  created_at: string;
}

export function login(email: string, password: string): Promise<TokenResponse> {
  return apiFetch<TokenResponse>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function getMe(): Promise<UserOut> {
  return apiFetch<UserOut>("/api/auth/me");
}

export function logout(): Promise<void> {
  return apiFetch<void>("/api/auth/logout", { method: "POST" });
}

export interface DocumentOut {
  id: number;
  title: string;
  writing_mode: string;
  word_count_mode: string;
  rewrite_strength: string;
  created_at: string;
  updated_at: string;
}

export interface DocumentWithContent extends DocumentOut {
  content: string;
}

export interface DocumentSettingsPayload {
  title: string;
  content: string;
  writing_mode: string;
  word_count_mode: string;
  rewrite_strength: string;
}

export function createDocument(payload: DocumentSettingsPayload): Promise<DocumentOut> {
  return apiFetch<DocumentOut>("/api/documents", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function importDocument(
  file: File,
  settings: Omit<DocumentSettingsPayload, "title" | "content"> & { title?: string }
): Promise<DocumentWithContent> {
  const form = new FormData();
  form.append("file", file);
  if (settings.title) form.append("title", settings.title);
  form.append("writing_mode", settings.writing_mode);
  form.append("word_count_mode", settings.word_count_mode);
  form.append("rewrite_strength", settings.rewrite_strength);

  const token = getToken();
  const response = await fetch(`${API_URL}/api/documents/import`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form,
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new ApiError(response.status, body?.detail ?? response.statusText);
  }
  return response.json();
}

export type ExportFormat = "md" | "docx" | "pdf";

export async function exportDocument(documentId: number, format: ExportFormat): Promise<Blob> {
  const token = getToken();
  const response = await fetch(`${API_URL}/api/documents/${documentId}/export?format=${format}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!response.ok) {
    throw new ApiError(response.status, response.statusText);
  }
  return response.blob();
}

export type SentenceStatus = "GOOD" | "NEEDS_IMPROVEMENT" | "REWRITTEN";

export interface SentenceOut {
  id: number;
  order_index: number;
  original_text: string;
  rewritten_text: string | null;
  status: SentenceStatus;
  quality_score: number | null;
  quality_breakdown: Record<string, number> | null;
}

export interface ChunkOut {
  id: number;
  order_index: number;
  sentences: SentenceOut[];
}

export interface AnalyzeResult {
  document_id: number;
  chunks: ChunkOut[];
  good_count: number;
  needs_improvement_count: number;
}

export function analyzeDocument(documentId: number): Promise<AnalyzeResult> {
  return apiFetch<AnalyzeResult>(`/api/documents/${documentId}/analyze`, { method: "POST" });
}

export interface RewriteResultOut {
  sentence_id: number;
  original_text: string;
  rewritten_text: string;
  stage_a_score: number;
  stage_b_score: number | null;
  passed_validation: boolean;
}

export interface RewriteRunResult {
  document_id: number;
  results: RewriteResultOut[];
  total_input_tokens: number;
  total_output_tokens: number;
  total_cost_usd: number;
}

export function rewriteDocument(documentId: number): Promise<RewriteRunResult> {
  return apiFetch<RewriteRunResult>(`/api/documents/${documentId}/rewrite`, { method: "POST" });
}

export function acceptChange(documentId: number, sentenceId: number): Promise<{ detail: string }> {
  return apiFetch(`/api/documents/${documentId}/changes/${sentenceId}/accept`, { method: "POST" });
}

export function rejectChange(documentId: number, sentenceId: number): Promise<{ detail: string }> {
  return apiFetch(`/api/documents/${documentId}/changes/${sentenceId}/reject`, { method: "POST" });
}

export interface DocumentMetrics {
  good_count: number;
  needs_improvement_count: number;
  rewritten_count: number;
  average_stage_a_score: number | null;
  average_stage_b_score: number | null;
  original_word_count: number;
  rewritten_word_count: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_cost_usd: number;
}

export function getMetrics(documentId: number): Promise<DocumentMetrics> {
  return apiFetch<DocumentMetrics>(`/api/documents/${documentId}/metrics`);
}
