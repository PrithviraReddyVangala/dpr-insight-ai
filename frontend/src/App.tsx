import { useCallback, useEffect, useRef, useState } from "react";
import { Sidebar } from "./components/Sidebar";
import { Workspace } from "./components/Workspace";
import { EmptyState } from "./components/EmptyState";
import { api } from "./lib/api";
import type { DocumentSummary } from "./lib/types";

const ACTIVE_STATUSES = new Set(["uploaded", "extracting", "analyzing", "indexing"]);

export default function App() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [dark, setDark] = useState(true);
  const pollingRef = useRef<number | null>(null);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
  }, [dark]);

  const refresh = useCallback(async () => {
    const docs = await api.listDocuments();
    setDocuments(docs);
    return docs;
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // Poll while any document is still processing — this drives the live
  // progress bars in the sidebar and workspace without a websocket.
  useEffect(() => {
    const hasActive = documents.some((d) => ACTIVE_STATUSES.has(d.status));
    if (!hasActive) return;
    pollingRef.current = window.setInterval(refresh, 1200);
    return () => {
      if (pollingRef.current) window.clearInterval(pollingRef.current);
    };
  }, [documents, refresh]);

  async function handleUpload(file: File) {
    const { id } = await api.uploadDocument(file);
    await refresh();
    setActiveId(id);
  }

  async function handleDelete(id: string) {
    await api.deleteDocument(id);
    if (activeId === id) setActiveId(null);
    await refresh();
  }

  const active = documents.find((d) => d.id === activeId) ?? null;

  return (
    <div className="flex h-screen bg-canvas">
      <Sidebar
        documents={documents}
        activeId={activeId}
        onSelect={setActiveId}
        onUpload={handleUpload}
        onDelete={handleDelete}
        dark={dark}
        onToggleDark={() => setDark((d) => !d)}
      />
      <main className="flex-1 overflow-hidden">
        {active ? <Workspace key={active.id} summary={active} /> : <EmptyState />}
      </main>
    </div>
  );
}
