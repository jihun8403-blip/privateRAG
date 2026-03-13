"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import Link from "next/link";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import TopicCard from "@/components/topics/TopicCard";
import { api } from "@/lib/api";
import { TopicSummary } from "@/types/api";

export default function TopicsPage() {
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

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/topics/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["topics"] });
      toast.success("Topic이 삭제되었습니다.");
    },
    onError: () => toast.error("삭제 실패"),
  });

  const handleDelete = (id: string) => {
    if (!confirm("정말 삭제하시겠습니까?")) return;
    deleteMutation.mutate(id);
  };

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold">키워드 관리</h1>
          <p className="text-sm text-muted-foreground">수집 주제(Topic)를 등록하고 관리합니다</p>
        </div>
        <Link href="/topics/new">
          <Button>
            <Plus className="w-4 h-4" />
            새 Topic
          </Button>
        </Link>
      </div>

      {isLoading && (
        <div className="text-sm text-muted-foreground py-8 text-center">불러오는 중...</div>
      )}

      {!isLoading && topics.length === 0 && (
        <div className="text-sm text-muted-foreground py-12 text-center border border-dashed rounded-lg">
          등록된 Topic이 없습니다.{" "}
          <Link href="/topics/new" className="text-primary underline">새 Topic 만들기</Link>
        </div>
      )}

      <div className="space-y-3">
        {topics.map((topic) => (
          <TopicCard
            key={topic.topic_id}
            topic={topic}
            onRun={(id) => runMutation.mutate(id)}
            onDelete={handleDelete}
          />
        ))}
      </div>
    </div>
  );
}
