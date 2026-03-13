"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import TopicForm from "@/components/topics/TopicForm";
import { api } from "@/lib/api";
import { TopicRead, TopicUpdate } from "@/types/api";

export default function EditTopicPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();

  const { data: topic, isLoading } = useQuery<TopicRead>({
    queryKey: ["topic", id],
    queryFn: () => api.get<TopicRead>(`/topics/${id}`),
  });

  const mutation = useMutation({
    mutationFn: (data: TopicUpdate) => api.put(`/topics/${id}`, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["topic", id] });
      qc.invalidateQueries({ queryKey: ["topics"] });
      toast.success("Topic이 수정되었습니다.");
      router.push(`/topics/${id}`);
    },
    onError: () => toast.error("수정 실패"),
  });

  if (isLoading) return <div className="p-6 text-sm text-muted-foreground">불러오는 중...</div>;
  if (!topic) return <div className="p-6 text-sm text-destructive">Topic을 찾을 수 없습니다.</div>;

  return (
    <div className="p-6 max-w-2xl">
      <div className="flex items-center gap-3 mb-6">
        <Link href={`/topics/${id}`}>
          <Button variant="ghost" size="icon"><ArrowLeft className="w-4 h-4" /></Button>
        </Link>
        <div>
          <h1 className="text-lg font-semibold">Topic 편집</h1>
          <p className="text-sm text-muted-foreground">{topic.name}</p>
        </div>
      </div>

      <TopicForm
        defaultValues={topic}
        onSubmit={(data) => mutation.mutate(data as TopicUpdate)}
        isLoading={mutation.isPending}
        submitLabel="저장"
      />
    </div>
  );
}
