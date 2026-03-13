"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Play, Edit } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import RuleTable from "@/components/topics/RuleTable";
import { api } from "@/lib/api";
import { TopicRead } from "@/types/api";
import { formatDate } from "@/lib/utils";

export default function TopicDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();

  const { data: topic, isLoading } = useQuery<TopicRead>({
    queryKey: ["topic", id],
    queryFn: () => api.get<TopicRead>(`/topics/${id}`),
  });

  const runMutation = useMutation({
    mutationFn: () => api.post(`/topics/${id}/run`),
    onSuccess: () => toast.success("수집 파이프라인이 시작되었습니다."),
    onError: () => toast.error("실행 요청 실패"),
  });

  if (isLoading) return <div className="p-6 text-sm text-muted-foreground">불러오는 중...</div>;
  if (!topic) return <div className="p-6 text-sm text-destructive">Topic을 찾을 수 없습니다.</div>;

  return (
    <div className="p-6 space-y-6 max-w-3xl">
      <div className="flex items-center gap-3">
        <Link href="/topics">
          <Button variant="ghost" size="icon"><ArrowLeft className="w-4 h-4" /></Button>
        </Link>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-semibold">{topic.name}</h1>
            <Badge variant={topic.enabled ? "success" : "outline"}>
              {topic.enabled ? "활성" : "비활성"}
            </Badge>
          </div>
          {topic.description && <p className="text-sm text-muted-foreground">{topic.description}</p>}
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => runMutation.mutate()} disabled={runMutation.isPending}>
            <Play className="w-3.5 h-3.5" />
            지금 실행
          </Button>
          <Link href={`/topics/${id}/edit`}>
            <Button variant="outline" size="sm"><Edit className="w-3.5 h-3.5" />편집</Button>
          </Link>
        </div>
      </div>

      <Card>
        <CardHeader><CardTitle className="text-sm">기본 정보</CardTitle></CardHeader>
        <CardContent>
          <dl className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
            <div>
              <dt className="text-muted-foreground text-xs">언어</dt>
              <dd>{topic.language}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground text-xs">우선순위</dt>
              <dd>{topic.priority}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground text-xs">크론 스케줄</dt>
              <dd className="font-mono text-xs">{topic.schedule_cron || "없음"}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground text-xs">관련성 임계값</dt>
              <dd>{topic.relevance_threshold}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground text-xs">생성일</dt>
              <dd>{formatDate(topic.created_at)}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground text-xs">수정일</dt>
              <dd>{formatDate(topic.updated_at)}</dd>
            </div>
          </dl>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">URL 규칙 ({topic.rules.length}개)</CardTitle>
        </CardHeader>
        <CardContent>
          <RuleTable topicId={id} rules={topic.rules} />
        </CardContent>
      </Card>
    </div>
  );
}
