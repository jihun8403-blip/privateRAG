"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import TopicForm from "@/components/topics/TopicForm";
import { api } from "@/lib/api";
import { TopicCreate, TopicRead } from "@/types/api";

export default function NewTopicPage() {
  const router = useRouter();
  const qc = useQueryClient();

  const mutation = useMutation({
    mutationFn: (data: TopicCreate) => api.post<TopicRead>("/topics", data),
    onSuccess: (topic) => {
      qc.invalidateQueries({ queryKey: ["topics"] });
      toast.success("Topic이 생성되었습니다.");
      router.push(`/topics/${topic.topic_id}`);
    },
    onError: () => toast.error("생성 실패"),
  });

  return (
    <div className="p-6 max-w-2xl">
      <div className="flex items-center gap-3 mb-6">
        <Link href="/topics">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="w-4 h-4" />
          </Button>
        </Link>
        <div>
          <h1 className="text-lg font-semibold">새 Topic 만들기</h1>
          <p className="text-sm text-muted-foreground">수집할 주제를 등록합니다</p>
        </div>
      </div>

      <TopicForm
        onSubmit={(data) => mutation.mutate(data as TopicCreate)}
        isLoading={mutation.isPending}
        submitLabel="생성"
      />
    </div>
  );
}
