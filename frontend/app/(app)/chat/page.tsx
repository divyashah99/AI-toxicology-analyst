"use client";
import { useState } from "react";
import { Topbar } from "@/components/topbar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { chatStream } from "@/lib/api";

interface Msg {
  role: "user" | "assistant";
  content: string;
}

interface Citation {
  n: number;
  paper_id: string;
  page: number;
  snippet: string;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [citations, setCitations] = useState<Citation[]>([]);

  const send = async () => {
    if (!input.trim() || streaming) return;
    const next: Msg[] = [...messages, { role: "user", content: input }];
    setMessages(next);
    setInput("");
    setStreaming(true);
    setCitations([]);

    let buf = "";
    setMessages((m) => [...m, { role: "assistant", content: "" }]);

    try {
      for await (const { event, data } of chatStream({ messages: next })) {
        if (event === "delta") {
          buf += data.text;
          setMessages((m) => {
            const copy = [...m];
            copy[copy.length - 1] = { role: "assistant", content: buf };
            return copy;
          });
        } else if (event === "citations") {
          setCitations(data.citations ?? []);
        } else if (event === "end") break;
      }
    } finally {
      setStreaming(false);
    }
  };

  return (
    <>
      <Topbar
        title="Chat"
        subtitle="Ask questions; answers cite the uploaded papers."
      />
      <div className="grid flex-1 gap-4 p-4 md:grid-cols-[1fr_320px] md:p-6">
        <Card className="flex h-[calc(100vh-9rem)] flex-col">
          <CardContent className="flex-1 space-y-3 overflow-y-auto pt-5">
            {messages.length === 0 && (
              <p className="text-sm text-muted-foreground">
                Try: <em>"What pathways does aflatoxin B1 affect?"</em>
              </p>
            )}
            {messages.map((m, i) => (
              <div
                key={i}
                className={
                  m.role === "user"
                    ? "ml-auto max-w-[85%] rounded-lg bg-primary px-3 py-2 text-sm text-primary-foreground"
                    : "max-w-[85%] rounded-lg bg-secondary px-3 py-2 text-sm"
                }
              >
                <pre className="whitespace-pre-wrap font-sans">{m.content}</pre>
              </div>
            ))}
          </CardContent>
          <div className="border-t p-3">
            <form
              className="flex gap-2"
              onSubmit={(e) => {
                e.preventDefault();
                send();
              }}
            >
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask about a compound, mechanism, or paper…"
                disabled={streaming}
              />
              <Button type="submit" disabled={streaming}>
                Send
              </Button>
            </form>
          </div>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Citations</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {citations.length === 0 ? (
              <p className="text-muted-foreground">
                Citations from the latest answer will appear here.
              </p>
            ) : (
              citations.map((c) => (
                <div key={c.n}>
                  <span className="mr-2 inline-block rounded-full bg-secondary px-2 py-0.5 text-xs">
                    [{c.n}]
                  </span>
                  <span className="text-muted-foreground">
                    paper {c.paper_id.slice(0, 8)} · p.{c.page}
                  </span>
                  <p className="mt-1 italic text-muted-foreground">{c.snippet}</p>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>
    </>
  );
}
