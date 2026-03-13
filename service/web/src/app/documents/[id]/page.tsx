"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ArrowLeft, ExternalLink, Sparkles, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import { DocumentRead, DocumentVersionRead, DocSummaryResponse } from "@/types/api";
import { formatDate, formatScore } from "@/lib/utils";

export default function DocumentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();

  const { data: doc, isLoading } = useQuery<DocumentRead>({
    queryKey: ["document", id],
    queryFn: () => api.get<DocumentRead>(`/documents/${id}`),
  });

  const { data: versions = [] } = useQuery<DocumentVersionRead[]>({
    queryKey: ["document-versions", id],
    queryFn: () => api.get<DocumentVersionRead[]>(`/documents/${id}/versions`),
    enabled: !!doc,
  });

  // 로컬 요약 상태 (API 응답 우선, 없으면 doc.summary 사용)
  const [summaryData, setSummaryData] = useState<DocSummaryResponse | null>(null);

  const summaryMd = summaryData?.summary ?? doc?.summary ?? null;
  const relatedDocs = summaryData?.related_docs ?? [];

  const summaryMutation = useMutation({
    mutationFn: () => api.post<DocSummaryResponse>(`/documents/${id}/summary`, {}),
    onSuccess: (data) => {
      setSummaryData(data);
      qc.invalidateQueries({ queryKey: ["document", id] });
      toast.success("요약이 생성되었습니다.");
    },
    onError: () => toast.error("요약 생성에 실패했습니다."),
  });

  if (isLoading) return <div className="p-6 text-sm text-muted-foreground">불러오는 중...</div>;
  if (!doc) return <div className="p-6 text-sm text-destructive">문서를 찾을 수 없습니다.</div>;

  return (
    <div className="p-6 space-y-6 max-w-3xl">
      <div className="flex items-center gap-3">
        <Link href="/documents">
          <Button variant="ghost" size="icon"><ArrowLeft className="w-4 h-4" /></Button>
        </Link>
        <div className="flex-1 min-w-0">
          <h1 className="text-lg font-semibold line-clamp-1">{doc.title || "(제목 없음)"}</h1>
          <a
            href={doc.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-muted-foreground hover:underline flex items-center gap-1"
          >
            {doc.url}
            <ExternalLink className="w-3 h-3 shrink-0" />
          </a>
        </div>
        <Button
          size="sm"
          variant={summaryMd ? "outline" : "default"}
          onClick={() => summaryMutation.mutate()}
          disabled={summaryMutation.isPending}
        >
          {summaryMutation.isPending ? (
            <><RefreshCw className="w-3.5 h-3.5 mr-1.5 animate-spin" />요약 중...</>
          ) : summaryMd ? (
            <><RefreshCw className="w-3.5 h-3.5 mr-1.5" />재요약</>
          ) : (
            <><Sparkles className="w-3.5 h-3.5 mr-1.5" />요약 실행</>
          )}
        </Button>
      </div>

      {summaryMd && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-primary" />
              AI 요약
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-sm space-y-3
              [&_h2]:font-semibold [&_h2]:text-base [&_h2]:mt-4 [&_h2]:mb-1
              [&_h3]:font-medium [&_h3]:mt-3 [&_h3]:mb-1
              [&_p]:leading-relaxed
              [&_code]:bg-muted [&_code]:px-1 [&_code]:py-0.5 [&_code]:rounded [&_code]:text-xs [&_code]:font-mono
              [&_ul]:list-disc [&_ul]:pl-4 [&_ul]:space-y-1
              [&_ol]:list-decimal [&_ol]:pl-4 [&_ol]:space-y-1
              [&_table]:w-full [&_table]:text-xs [&_table]:border-collapse
              [&_th]:border [&_th]:border-border [&_th]:bg-muted [&_th]:px-2 [&_th]:py-1 [&_th]:text-left
              [&_td]:border [&_td]:border-border [&_td]:px-2 [&_td]:py-1
              [&_a]:text-primary hover:[&_a]:underline
              [&_hr]:border-border [&_hr]:my-4">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {summaryMd}
              </ReactMarkdown>
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader><CardTitle className="text-sm">메타데이터</CardTitle></CardHeader>
        <CardContent>
          <dl className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
            <div>
              <dt className="text-muted-foreground text-xs">수집일</dt>
              <dd>{formatDate(doc.collected_at)}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground text-xs">언어</dt>
              <dd>{doc.language || "-"}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground text-xs">관련도</dt>
              <dd className="font-medium">{formatScore(doc.relevance_score)}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground text-xs">버전</dt>
              <dd>v{doc.current_version}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground text-xs">아카이브 티어</dt>
              <dd><Badge variant="secondary">Tier {doc.archive_tier}</Badge></dd>
            </div>
            <div>
              <dt className="text-muted-foreground text-xs">상태</dt>
              <dd>
                <Badge variant={doc.is_active ? "success" : "outline"}>
                  {doc.is_active ? "활성" : "비활성"}
                </Badge>
              </dd>
            </div>
            {doc.author && (
              <div>
                <dt className="text-muted-foreground text-xs">저자</dt>
                <dd>{doc.author}</dd>
              </div>
            )}
            {doc.published_at && (
              <div>
                <dt className="text-muted-foreground text-xs">발행일</dt>
                <dd>{formatDate(doc.published_at)}</dd>
              </div>
            )}
          </dl>

          {doc.relevance_reason && (
            <div className="mt-4 pt-4 border-t border-border">
              <p className="text-xs text-muted-foreground mb-1">관련성 판단 근거</p>
              <p className="text-sm text-muted-foreground">{doc.relevance_reason}</p>
            </div>
          )}
        </CardContent>
      </Card>

      {versions.length > 0 && (
        <Card>
          <CardHeader><CardTitle className="text-sm">버전 이력 ({versions.length}개)</CardTitle></CardHeader>
          <CardContent>
            <div className="relative">
              <div className="absolute left-3 top-0 bottom-0 w-px bg-border" />
              <div className="space-y-4">
                {versions.map((v) => (
                  <div key={v.version_id} className="flex gap-4 pl-8 relative">
                    <div className="absolute left-2 top-1 w-2 h-2 rounded-full bg-primary border-2 border-background" />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-medium text-sm">v{v.version_no}</span>
                        <Badge variant="outline" className="text-xs">{v.change_type}</Badge>
                        {v.relevance_score != null && (
                          <span className="text-xs text-muted-foreground">
                            관련도 {formatScore(v.relevance_score)}
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground mt-0.5">{formatDate(v.created_at)}</p>
                      {v.summary && <p className="text-xs mt-1">{v.summary}</p>}
                      <p className="text-[10px] text-muted-foreground font-mono mt-1">{v.content_hash}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
