"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { ExternalLink, FileText, Sparkles } from "lucide-react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { DocumentRead, TopicSummary } from "@/types/api";
import { formatDate, formatScore } from "@/lib/utils";

const PAGE_SIZE = 20;

export default function DocumentsPage() {
  const [topicId, setTopicId] = useState<string>("all");
  const [isActive, setIsActive] = useState(true);
  const [offset, setOffset] = useState(0);

  const { data: topics = [] } = useQuery<TopicSummary[]>({
    queryKey: ["topics"],
    queryFn: () => api.get<TopicSummary[]>("/topics"),
  });

  const params = new URLSearchParams({
    limit: String(PAGE_SIZE),
    offset: String(offset),
    is_active: String(isActive),
  });
  if (topicId !== "all") params.set("topic_id", topicId);

  const { data: documents = [], isLoading } = useQuery<DocumentRead[]>({
    queryKey: ["documents", topicId, isActive, offset],
    queryFn: () => api.get<DocumentRead[]>(`/documents?${params}`),
  });

  const topicMap = Object.fromEntries(topics.map((t) => [t.topic_id, t.name]));

  return (
    <div className="p-6 space-y-5">
      <div>
        <h1 className="text-lg font-semibold">문서 관리</h1>
        <p className="text-sm text-muted-foreground">수집된 문서를 조회합니다</p>
      </div>

      <div className="flex items-center gap-4 flex-wrap">
        <Select value={topicId} onValueChange={(v) => { setTopicId(v); setOffset(0); }}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="전체 Topic" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">전체 Topic</SelectItem>
            {topics.map((t) => (
              <SelectItem key={t.topic_id} value={t.topic_id}>{t.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        <div className="flex items-center gap-2">
          <Switch checked={isActive} onCheckedChange={(v) => { setIsActive(v); setOffset(0); }} />
          <Label className="text-sm">활성 문서만</Label>
        </div>
      </div>

      {isLoading && <div className="text-sm text-muted-foreground py-8 text-center">불러오는 중...</div>}

      {!isLoading && (
        <div className="rounded-md border border-border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">제목</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">Topic</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">관련도</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">수집일</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">버전</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">티어</th>
                <th className="w-12" />
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {documents.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-10 text-center text-muted-foreground text-xs">
                    <FileText className="w-8 h-8 mx-auto mb-2 opacity-30" />
                    문서가 없습니다
                  </td>
                </tr>
              )}
              {documents.map((doc) => (
                <tr key={doc.doc_id} className="hover:bg-muted/30">
                  <td className="px-4 py-3 max-w-xs">
                    <div className="flex items-center gap-1.5">
                      <Link href={`/documents/${doc.doc_id}`} className="font-medium hover:underline line-clamp-1">
                        {doc.title || "(제목 없음)"}
                      </Link>
                      {doc.summary && (
                        <Sparkles className="w-3 h-3 shrink-0 text-primary opacity-70" title="AI 요약 있음" />
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground truncate">{doc.url}</p>
                  </td>
                  <td className="px-4 py-3 text-xs">
                    <Badge variant="outline">{topicMap[doc.topic_id] || doc.topic_id.slice(0, 8)}</Badge>
                  </td>
                  <td className="px-4 py-3 text-xs font-medium">
                    {formatScore(doc.relevance_score)}
                  </td>
                  <td className="px-4 py-3 text-xs text-muted-foreground">
                    {formatDate(doc.collected_at)}
                  </td>
                  <td className="px-4 py-3 text-xs">v{doc.current_version}</td>
                  <td className="px-4 py-3 text-xs">
                    <Badge variant="secondary">Tier {doc.archive_tier}</Badge>
                  </td>
                  <td className="px-4 py-3">
                    <a href={doc.url} target="_blank" rel="noopener noreferrer">
                      <Button size="icon" variant="ghost" className="h-7 w-7">
                        <ExternalLink className="w-3.5 h-3.5" />
                      </Button>
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="flex items-center gap-3 justify-end text-sm">
        <Button
          variant="outline"
          size="sm"
          disabled={offset === 0}
          onClick={() => setOffset((p) => Math.max(0, p - PAGE_SIZE))}
        >
          이전
        </Button>
        <span className="text-muted-foreground">
          {offset + 1}~{offset + documents.length}
        </span>
        <Button
          variant="outline"
          size="sm"
          disabled={documents.length < PAGE_SIZE}
          onClick={() => setOffset((p) => p + PAGE_SIZE)}
        >
          다음
        </Button>
      </div>
    </div>
  );
}
