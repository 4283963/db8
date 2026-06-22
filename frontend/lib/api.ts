export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface Source {
  content: string;
  source: string;
  score: number;
}

export interface ChatRequest {
  question: string;
  chat_history?: ChatMessage[];
}

export interface ChatResponse {
  answer: string;
  sources: Source[];
}

export interface IndexResponse {
  message: string;
  files_processed: string[];
  chunks_count: number;
}

export interface DocumentsResponse {
  files: string[];
  indexed_chunks: number;
}

const API_BASE = "/api";

export async function healthCheck(): Promise<{ status: string }> {
  const response = await fetch(`${API_BASE}/health`);
  if (!response.ok) {
    throw new Error("Health check failed");
  }
  return response.json();
}

export async function getDocuments(): Promise<DocumentsResponse> {
  const response = await fetch(`${API_BASE}/documents`);
  if (!response.ok) {
    throw new Error("Failed to fetch documents");
  }
  return response.json();
}

export async function indexDocuments(): Promise<IndexResponse> {
  const response = await fetch(`${API_BASE}/index`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to index documents");
  }
  return response.json();
}

export async function chat(
  question: string,
  chatHistory: ChatMessage[] = []
): Promise<ChatResponse> {
  const request: ChatRequest = {
    question,
    chat_history: chatHistory,
  };

  const response = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to chat");
  }

  return response.json();
}
