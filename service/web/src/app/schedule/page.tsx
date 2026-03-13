"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Play, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import { TopicSummary, TopicUpdate } from "@/types/api";
import { formatDate } from "@/lib/utils";

export default function SchedulePage() {
  const qc = useQueryClient();

  const { data: topics = [], isLoading } = useQuery<TopicSummary[]>({
    queryKey: ["topics"],
    queryFn: () => api.get<TopicSummary[]>("/topics"),
  });

  const runMutation = useMutation({
    mutationFn: (id: string) => api.post(`/topics/${id}/run`),
    onSuccess: () => toast.success("수집 파이프라인이 시작되었습니다."),
    onError: () => toast.error("실행 요청 실패"),
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      api.put(`/topics/${id}`, { enabled } satisfies TopicUpdate),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["topics"] }),
    onError: () => toast.error("상태 변경 실패"),
  });

  return (
    <div className="p-6 space-y-5">
      <div>
        <h1 className="text-lg font-semibold">스케줄 관리</h1>
        <p className="text-sm text-muted-foreground">각 Topic의 수집 스케줄을 관리합니다</p>
      </div>

      {isLoading && <div className="text-sm text-muted-foreground py-8 text-center">불러오는 중...</div>}

      {!isLoading && (
        <div className="rounded-md border border-border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">Topic</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">크론 스케줄</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">우선순위</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">생성일</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">활성화</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">수동 실행</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {topics.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-muted-foreground text-xs">
                    등록된 Topic이 없습니다
                  </td>
                </tr>
              )}
              {topics.map((topic) => (
                <tr key={topic.topic_id} className="hover:bg-muted/30">
                  <td className="px-4 py-3">
                    <div className="font-medium">{topic.name}</div>
                    {topic.description && (
                      <div className="text-xs text-muted-foreground line-clamp-1">{topic.description}</div>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {topic.schedule_cron ? (
                      <code className="text-xs bg-muted px-1.5 py-0.5 rounded">{topic.schedule_cron}</code>
                    ) : (
                      <span className="text-xs text-muted-foreground">수동 전용</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant="secondary">{topic.priority}</Badge>
                  </td>
                  <td className="px-4 py-3 text-xs text-muted-foreground">
                    {formatDate(topic.created_at)}
                  </td>
                  <td className="px-4 py-3">
                    <Switch
                      checked={topic.enabled}
                      onCheckedChange={(v) => toggleMutation.mutate({ id: topic.topic_id, enabled: v })}
                      disabled={toggleMutation.isPending}
                    />
                  </td>
                  <td className="px-4 py-3">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => runMutation.mutate(topic.topic_id)}
                      disabled={runMutation.isPending}
                    >
                      {runMutation.isPending ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <Play className="w-3.5 h-3.5" />
                      )}
                      지금 실행
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
