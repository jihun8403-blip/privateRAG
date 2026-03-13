import Link from "next/link";
import { Play, Edit, Trash2 } from "lucide-react";
import { TopicSummary } from "@/types/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { formatDate } from "@/lib/utils";

interface TopicCardProps {
  topic: TopicSummary;
  onRun: (id: string) => void;
  onDelete: (id: string) => void;
}

export default function TopicCard({ topic, onRun, onDelete }: TopicCardProps) {
  return (
    <Card>
      <CardContent className="p-4 flex items-start gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <Link href={`/topics/${topic.topic_id}`} className="font-medium hover:underline">
              {topic.name}
            </Link>
            <Badge variant={topic.enabled ? "success" : "outline"}>
              {topic.enabled ? "활성" : "비활성"}
            </Badge>
            <Badge variant="secondary">우선순위 {topic.priority}</Badge>
          </div>
          {topic.description && (
            <p className="text-sm text-muted-foreground mt-1 line-clamp-1">{topic.description}</p>
          )}
          <div className="flex gap-3 mt-2 text-xs text-muted-foreground">
            <span>크론: {topic.schedule_cron || "없음"}</span>
            <span>생성: {formatDate(topic.created_at)}</span>
          </div>
        </div>

        <div className="flex gap-1 shrink-0">
          <Button size="sm" variant="outline" onClick={() => onRun(topic.topic_id)}>
            <Play className="w-3.5 h-3.5" />
            실행
          </Button>
          <Link href={`/topics/${topic.topic_id}/edit`}>
            <Button size="icon" variant="ghost">
              <Edit className="w-4 h-4" />
            </Button>
          </Link>
          <Button size="icon" variant="ghost" onClick={() => onDelete(topic.topic_id)}>
            <Trash2 className="w-4 h-4 text-destructive" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
