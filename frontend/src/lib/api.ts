import type { ChatMessage, DocumentDetail, DocumentSummary, RiskDetail } from "./types";

const BASE = "/api";

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let message = res.statusText;
    try {
      const body = await res.json();
      message = body.detail || message;
    } catch {
      /* response wasn't JSON */
    }
    throw new ApiError(res.status, message);
  }
  return res.json();
}

export const api = {
  async listDocuments(): Promise<DocumentSummary[]> {
    return handle(await fetch(`${BASE}/documents`));
  },

  async uploadDocument(file: File): Promise<{ id: string }> {
    const form = new FormData();
    form.append("file", file);
    return handle(await fetch(`${BASE}/documents/upload`, { method: "POST", body: form }));
  },

  async getStatus(id: string): Promise<DocumentSummary> {
    return handle(await fetch(`${BASE}/documents/${id}/status`));
  },

  async getDetail(id: string): Promise<DocumentDetail> {
    return handle(await fetch(`${BASE}/documents/${id}`));
  },

  async getRisk(id: string): Promise<RiskDetail> {
    return handle(await fetch(`${BASE}/documents/${id}/risk`));
  },

  async deleteDocument(id: string): Promise<void> {
    await handle(await fetch(`${BASE}/documents/${id}`, { method: "DELETE" }));
  },

  fileUrl(id: string): string {
    return `${BASE}/documents/${id}/file`;
  },

  async chat(id: string, query: string): Promise<ChatMessage> {
    const res = await fetch(`${BASE}/documents/${id}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });
    if (!res.ok) {
      let message = res.statusText;
      try {
        const body = await res.json();
        message = body.detail || message;
      } catch {
        /* ignore */
      }
      return { role: "assistant", content: message, error: true };
    }
    const data = await res.json();
    return { role: "assistant", content: data.answer, chunks: data.retrieved_chunks };
  },
};

export { ApiError };
