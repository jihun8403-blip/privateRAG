"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Bot, User } from "lucide-react";
import { ChatMessage as ChatMsg } from "@/types/api";
import SourceCard from "./SourceCard";
import { cn } from "@/lib/utils";

export default function ChatMessage({ message }: { message: ChatMsg }) {
  const isUser = message.role === "user";

  return (
    <div className={cn("flex gap-3 py-4", isUser && "flex-row-reverse")}>
      <div className={cn(
        "shrink-0 w-8 h-8 rounded-full flex items-center justify-center",
        isUser ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"
      )}>
        {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
      </div>

      <div className={cn("flex-1 min-w-0 max-w-[85%]", isUser && "flex flex-col items-end")}>
        <div className={cn(
          "rounded-lg px-4 py-3",
          isUser
            ? "bg-primary text-primary-foreground text-sm"
            : "bg-muted/60 border border-border"
        )}>
          {isUser ? (
            <p className="whitespace-pre-wrap text-sm">{message.content}</p>
          ) : (
            <div className="prose">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.content}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="mt-3 w-full space-y-1.5">
            <p className="text-xs text-muted-foreground font-medium px-1">출처 ({message.sources.length}건)</p>
            {message.sources.map((src, i) => (
              <SourceCard key={src.doc_id} source={src} index={i} />
            ))}
          </div>
        )}

        {!isUser && message.model_used && (
          <p className="text-[10px] text-muted-foreground mt-1.5 px-1">{message.model_used}</p>
        )}
      </div>
    </div>
  );
}
