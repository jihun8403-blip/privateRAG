"use client";

import { useState, useRef, KeyboardEvent } from "react";
import { Send, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { TopicSummary } from "@/types/api";
import { cn } from "@/lib/utils";

interface ChatInputProps {
  onSend: (query: string, topicIds: string[]) => void;
  loading: boolean;
  topics: TopicSummary[];
}

export default function ChatInput({ onSend, loading, topics }: ChatInputProps) {
  const [query, setQuery] = useState("");
  const [selectedTopics, setSelectedTopics] = useState<string[]>([]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    const trimmed = query.trim();
    if (!trimmed || loading) return;
    onSend(trimmed, selectedTopics);
    setQuery("");
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const toggleTopic = (id: string) => {
    setSelectedTopics((prev) =>
      prev.includes(id) ? prev.filter((t) => t !== id) : [...prev, id]
    );
  };

  return (
    <div className="border-t border-border bg-background p-4 space-y-2">
      {topics.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          <span className="text-xs text-muted-foreground self-center">범위:</span>
          {topics.map((t) => (
            <button
              key={t.topic_id}
              onClick={() => toggleTopic(t.topic_id)}
              className={cn(
                "text-xs px-2.5 py-1 rounded-full border transition-colors",
                selectedTopics.includes(t.topic_id)
                  ? "bg-primary text-primary-foreground border-primary"
                  : "border-border text-muted-foreground hover:border-primary/50"
              )}
            >
              {t.name}
            </button>
          ))}
          {selectedTopics.length > 0 && (
            <button
              onClick={() => setSelectedTopics([])}
              className="text-xs px-2 py-1 text-muted-foreground hover:text-foreground"
            >
              전체
            </button>
          )}
        </div>
      )}

      <div className="flex gap-2 items-end">
        <Textarea
          ref={textareaRef}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="질문을 입력하세요... (Shift+Enter로 줄바꿈)"
          className="resize-none min-h-[44px] max-h-40"
          rows={1}
          disabled={loading}
        />
        <Button
          onClick={handleSend}
          disabled={!query.trim() || loading}
          size="icon"
          className="shrink-0 h-[44px] w-[44px]"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
        </Button>
      </div>
    </div>
  );
}
