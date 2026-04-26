import {
  ConceptDetail,
  ConceptExpandResponse,
  ConceptState,
  DocumentDetail,
  DocumentSummary,
  KeywordDetail,
  MasteredConceptListResponse
} from "@/types";


const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api";

export type PreferredLanguage = "en" | "zh";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    cache: "no-store"
  });

  if (!response.ok) {
    const payload = await response.text();
    throw new Error(payload || `Request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export async function uploadPdf(file: File, preferredLanguage: PreferredLanguage): Promise<DocumentSummary> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("preferred_language", preferredLanguage);
  return request<DocumentSummary>("/upload", {
    method: "POST",
    body: formData
  });
}

export async function parseDocument(documentId: number): Promise<DocumentSummary> {
  return request<DocumentSummary>(`/documents/${documentId}/parse`, {
    method: "POST"
  });
}

export async function annotateDocument(documentId: number): Promise<DocumentSummary> {
  return request<DocumentSummary>(`/documents/${documentId}/annotate`, {
    method: "POST"
  });
}

export async function getDocument(documentId: number): Promise<DocumentDetail> {
  return request<DocumentDetail>(`/documents/${documentId}`);
}

export async function getConcept(conceptId: number, documentId?: number): Promise<ConceptDetail> {
  const query = documentId ? `?document_id=${documentId}` : "";
  return request<ConceptDetail>(`/concepts/${conceptId}${query}`);
}

export async function getKeyword(keywordId: number, documentId?: number): Promise<KeywordDetail> {
  const query = documentId ? `?document_id=${documentId}` : "";
  return request<KeywordDetail>(`/keywords/${keywordId}${query}`);
}

export async function retryKeyword(keywordId: number, documentId?: number): Promise<KeywordDetail> {
  const query = documentId ? `?document_id=${documentId}` : "";
  return request<KeywordDetail>(`/keywords/${keywordId}/retry${query}`, {
    method: "POST"
  });
}

export async function expandConcept(conceptId: number, documentId?: number): Promise<ConceptExpandResponse> {
  const query = documentId ? `?document_id=${documentId}` : "";
  return request<ConceptExpandResponse>(`/concepts/${conceptId}/expand${query}`, {
    method: "POST"
  });
}

export async function updateConceptState(conceptId: number, status: ConceptState) {
  return request<{ concept_id: number; status: ConceptState }>(`/concepts/${conceptId}/state`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ status })
  });
}

export async function getMasteredConcepts(): Promise<MasteredConceptListResponse> {
  return request<MasteredConceptListResponse>("/concepts/mastered");
}
