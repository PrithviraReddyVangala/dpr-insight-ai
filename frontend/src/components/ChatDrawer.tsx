import { useEffect, useRef, useState } from "react";
import { MessageSquareText, Send, X } from "lucide-react";
import { api } from "../lib/api";
import type { ChatMessage } from "../lib/types";

export function ChatDrawer({ documentId, docName }: { documentId: string; docName: string }) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [pending, setPending] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, pending]);

  async function send() {
    const query = input.trim();
    if (!query || pending) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", content: query }]);
    setPending(true);
    const reply = await api.chat(documentId, query);
    setMessages((m) => [...m, reply]);
    setPending(false);
  }

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-6 right-6 flex items-center gap-2 rounded-full bg-accent px-4 py-3 text-sm font-medium text-white shadow-lg shadow-accent/25 transition-transform hover:scale-[1.03]"
      >
        <MessageSquareText size={16} />
        Ask this document
      </button>
    );
  }

  return (
    <div className="fixed bottom-6 right-6 flex h-[560px] w-[380px] flex-col overflow-hidden rounded-card border border-border bg-surface-raised shadow-panel">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <div className="min-w-0">
          <p className="text-[13px] font-medium text-ink">Ask this document</p>
          <p className="truncate text-[11px] text-ink-faint">{docName}</p>
        </div>
        <button onClick={() => setOpen(false)} className="rounded p-1 text-ink-faint hover:bg-canvas hover:text-ink">
          <X size={16} />
        </button>
      </div>

      <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
        {messages.length === 0 && (
          <p className="text-[12.5px] leading-relaxed text-ink-faint">
            Ask about costs, timelines, clearances, or scope — answers are grounded only in this document's
            extracted content, with sources cited.
          </p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[85%] rounded-lg px-3 py-2 text-[13px] leading-relaxed ${
                m.role === "user"
                  ? "bg-accent text-white"
                  : m.error
                  ? "bg-risk-high-soft text-risk-high"
                  : "bg-canvas text-ink"
              }`}
            >
              <p className="whitespace-pre-wrap">{m.content}</p>
              {m.chunks && m.chunks.length > 0 && (
                <div className="mt-2 space-y-1 border-t border-border/60 pt-2">
                  {m.chunks.slice(0, 3).map((c, ci) => (
                    <p key={ci} className="text-[10.5px] text-ink-faint">
                      {c.heading_text || "Untitled section"} · p{c.page_start + 1}
                    </p>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        {pending && (
          <div className="flex justify-start">
            <div className="rounded-lg bg-canvas px-3 py-2 text-[13px] text-ink-faint">Thinking…</div>
          </div>
        )}
      </div>

      <div className="flex items-center gap-2 border-t border-border p-3">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="Ask a question…"
          className="flex-1 rounded-lg border border-border bg-canvas px-3 py-2 text-[13px] text-ink outline-none focus:border-accent"
        />
        <button
          onClick={send}
          disabled={pending || !input.trim()}
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-accent text-white disabled:opacity-40"
        >
          <Send size={15} />
        </button>
      </div>
    </div>
  );
}
