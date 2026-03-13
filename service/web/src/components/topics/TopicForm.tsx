"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { TopicCreate, TopicUpdate } from "@/types/api";

const schema = z.object({
  name: z.string().min(1, "이름을 입력하세요").max(200),
  description: z.string().optional(),
  language: z.string().default("ko,en"),
  priority: z.coerce.number().min(1).max(10).default(5),
  schedule_cron: z.string().optional(),
  relevance_threshold: z.coerce.number().min(0).max(1).default(0.6),
  enabled: z.boolean().default(true),
});

type FormValues = z.infer<typeof schema>;

interface TopicFormProps {
  defaultValues?: Partial<FormValues>;
  onSubmit: (data: TopicCreate | TopicUpdate) => void;
  isLoading?: boolean;
  submitLabel?: string;
}

export default function TopicForm({ defaultValues, onSubmit, isLoading, submitLabel = "저장" }: TopicFormProps) {
  const { register, handleSubmit, watch, setValue, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: "",
      language: "ko,en",
      priority: 5,
      relevance_threshold: 0.6,
      enabled: true,
      ...defaultValues,
    },
  });

  const enabled = watch("enabled");

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
      <div className="space-y-1.5">
        <Label>이름 *</Label>
        <Input {...register("name")} placeholder="예: AI 뉴스" />
        {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
      </div>

      <div className="space-y-1.5">
        <Label>설명</Label>
        <Textarea {...register("description")} placeholder="주제 설명 (선택)" rows={2} />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-1.5">
          <Label>언어</Label>
          <Input {...register("language")} placeholder="ko,en" />
        </div>
        <div className="space-y-1.5">
          <Label>우선순위 (1~10)</Label>
          <Input {...register("priority")} type="number" min={1} max={10} />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-1.5">
          <Label>크론 스케줄</Label>
          <Input {...register("schedule_cron")} placeholder="0 */6 * * *" />
          <p className="text-xs text-muted-foreground">cron 5필드 (비워두면 수동 실행만)</p>
        </div>
        <div className="space-y-1.5">
          <Label>관련성 임계값 (0~1)</Label>
          <Input {...register("relevance_threshold")} type="number" step={0.05} min={0} max={1} />
        </div>
      </div>

      <div className="flex items-center gap-3">
        <Switch
          checked={enabled}
          onCheckedChange={(v) => setValue("enabled", v)}
        />
        <Label>활성화</Label>
      </div>

      <Button type="submit" disabled={isLoading}>
        {isLoading ? "처리 중..." : submitLabel}
      </Button>
    </form>
  );
}
