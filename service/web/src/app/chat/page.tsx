"use client";

import { useState, useRef, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { MessageSquare, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import ChatMessage from "@/components/chat/ChatMessage";
import ChatInput from "@/components/chat/ChatInput";
import { api } from "@/lib/api";
import { ChatMessage as ChatMsg, RagQueryResponse, TopicSummary } from "@/types/api";

const STORAGE_KEY = "chat_history";

function loadMessages(): ChatMsg[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as (Omit<ChatMsg, "timestamp"> & { timestamp: string })[];
    return parsed.map((m) => ({ ...m, timestamp: new Date(m.timestamp) }));
  } catch {
    return [];
  }
}

let msgId = 0;
const nextId = () => String(++msgId);

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMsg[]>(() => loadMessages());
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const { data: topics = [] } = useQuery<TopicSummary[]>({
    queryKey: ["topics"],
    queryFn: () => api.get<TopicSummary[]>("/topics"),
  });

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
  }, [messages]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleClear = () => {
    setMessages([]);
  };

  const handleSend = async (query: string, topicIds: string[]) => {
    setMessages((prev) => [
      ...prev,
      { id: nextId(), role: "user", content: query, timestamp: new Date() },
    ]);
    setLoading(true);

    try {
      const res = await api.post<RagQueryResponse>("/rag/query", {
        query,
        topic_ids: topicIds.length > 0 ? topicIds : undefined,
        top_k: 5,
      });

      setMessages((prev) => [
        ...prev,
        {
          id: nextId(),
          role: "assistant",
          content: res.answer,
          sources: res.sources,
          model_used: res.model_used,
          timestamp: new Date(),
        },
      ]);
    } catch (e) {
      toast.error("질문 처리 중 오류가 발생했습니다.");
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="px-6 py-4 border-b border-border flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold">챗봇</h1>
          <p className="text-sm text-muted-foreground">수집된 문서를 기반으로 질문에 답합니다</p>
        </div>
        {messages.length > 0 && (
          <Button variant="ghost" size="sm" onClick={handleClear} className="text-muted-foreground hover:text-destructive">
            <Trash2 className="w-3.5 h-3.5 mr-1" />
            대화 초기화
          </Button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto px-6">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full gap-3 text-muted-foreground">
            <MessageSquare className="w-12 h-12 opacity-30" />
            <p className="text-sm">아래에 질문을 입력하세요</p>
          </div>
        ) : (
          <div className="divide-y divide-border/40">
            {messages.map((msg) => (
              <ChatMessage key={msg.id} message={msg} />
            ))}
            {loading && (
              <div className="flex gap-3 py-4">
                <div className="shrink-0 w-8 h-8 rounded-full bg-muted flex items-center justify-center">
                  <span className="text-xs text-muted-foreground">AI</span>
                </div>
                <div className="flex items-center gap-1 px-4 py-3 bg-muted/60 border border-border rounded-lg">
                  <span className="w-1.5 h-1.5 bg-muted-foreground rounded-full animate-bounce [animation-delay:0ms]" />
                  <span className="w-1.5 h-1.5 bg-muted-foreground rounded-full animate-bounce [animation-delay:150ms]" />
                  <span className="w-1.5 h-1.5 bg-muted-foreground rounded-full animate-bounce [animation-delay:300ms]" />
                </div>
              </div>
            )}
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <ChatInput onSend={handleSend} loading={loading} topics={topics} />
    </div>
  );
}
