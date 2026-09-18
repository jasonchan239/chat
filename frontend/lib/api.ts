const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface Source {
  text: string;
  filename: string;
  chunk: number;
}

export interface ChatResponse {
  answer: string;
  model: string;
  sources: Source[];
}

export interface DocInfo {
  doc_id: string;
  filename: string;
}

export async function uploadDocument(file: File): Promise<DocInfo & { chunks: number }> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_URL}/upload`, { method: "POST", body: form });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function sendChat(message: string, top_k = 5): Promise<ChatResponse> {
  const res = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, top_k }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function listDocs(): Promise<DocInfo[]> {
  const res = await fetch(`${API_URL}/documents`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function deleteDoc(doc_id: string): Promise<void> {
  const res = await fetch(`${API_URL}/documents/${doc_id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(await res.text());
}
