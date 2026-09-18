"use client";
import { useEffect, useState } from "react";
import { deleteDoc, listDocs, sendChat, uploadDocument, type ChatResponse, type DocInfo } from "../lib/api";

interface Msg {
  role: "user" | "ai";
  text: string;
  sources?: ChatResponse["sources"];
}

export default function Page() {
  const [docs, setDocs] = useState<DocInfo[]>([]);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");

  async function refresh() {
    try {
      setDocs(await listDocs());
    } catch {
      /* backend may be down */
    }
  }
  useEffect(() => {
    refresh();
  }, []);

  async function onUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (!f) return;
    setBusy(true);
    setStatus(`Uploading ${f.name}...`);
    try {
      const r = await uploadDocument(f);
      setStatus(`Ingested ${r.filename}: ${r.chunks} chunks`);
      await refresh();
    } catch (err) {
      setStatus(`Upload failed: ${String(err)}`);
    } finally {
      setBusy(false);
      e.target.value = "";
    }
  }

  async function onSend() {
    const q = input.trim();
    if (!q || busy) return;
    setInput("");
    setMsgs((m) => [...m, { role: "user", text: q }]);
    setBusy(true);
    try {
      const r = await sendChat(q, 5);
      setMsgs((m) => [...m, { role: "ai", text: `${r.answer}\n\n— ${r.model}`, sources: r.sources }]);
    } catch (err) {
      setMsgs((m) => [...m, { role: "ai", text: `Error: ${String(err)}` }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="container">
      <h1>RAG Chatbot (Sonnet 4.6)</h1>
      <p className="small">Upload a PDF / TXT / MD, then ask questions. Backend: FastAPI + Chroma + Anthropic.</p>

      <div className="card">
        <h3>1. Upload document</h3>
        <input type="file" accept=".pdf,.txt,.md" onChange={onUpload} disabled={busy} />
        <p className="small">{status}</p>
        <ul>
          {docs.map((d) => (
            <li key={d.doc_id}>
              {d.filename} <span className="small">({d.doc_id})</span>{" "}
              <button
                onClick={async () => {
                  await deleteDoc(d.doc_id);
                  await refresh();
                }}
              >
                delete
              </button>
            </li>
          ))}
        </ul>
      </div>

      <div className="card">
        <h3>2. Chat</h3>
        <div>
          {msgs.map((m, i) => (
            <div key={i} className={m.role === "user" ? "msg-user" : "msg-ai"}>
              {m.text}
              {m.sources && m.sources.length > 0 && (
                <div className="small" style={{ marginTop: 8 }}>
                  Sources: {m.sources.map((s) => `${s.filename} #${s.chunk}`).join(", ")}
                </div>
              )}
            </div>
          ))}
        </div>
        <div className="row" style={{ marginTop: 12 }}>
          <input
            type="text"
            placeholder="Ask about your document..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") onSend();
            }}
          />
          <button onClick={onSend} disabled={busy}>
            {busy ? "..." : "Send"}
          </button>
        </div>
      </div>
    </main>
  );
}
