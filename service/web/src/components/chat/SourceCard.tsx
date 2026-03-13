import { ExternalLink } from "lucide-react";
import { RagSource } from "@/types/api";
import { formatScore } from "@/lib/utils";

export default function SourceCard({ source, index }: { source: RagSource; index: number }) {
  return (
    <a
      href={source.url}
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-start gap-2 p-3 rounded-md border border-border bg-muted/40 hover:bg-muted transition-colors text-xs group"
    >
      <span className="shrink-0 w-5 h-5 rounded-full bg-primary/10 text-primary flex items-center justify-center font-semibold text-[10px]">
        {index + 1}
      </span>
      <div className="flex-1 min-w-0">
        <p className="font-medium text-foreground truncate group-hover:underline">
          {source.title || new URL(source.url).hostname}
        </p>
        <p className="text-muted-foreground truncate">{source.url}</p>
      </div>
      <span className="shrink-0 text-muted-foreground font-medium">{formatScore(source.relevance_score)}</span>
      <ExternalLink className="shrink-0 w-3 h-3 text-muted-foreground mt-0.5" />
    </a>
  );
}
