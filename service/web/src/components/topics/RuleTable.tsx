"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Plus, Trash2 } from "lucide-react";
import { TopicRuleRead, TopicRuleCreate, RuleType } from "@/types/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api } from "@/lib/api";

interface RuleTableProps {
  topicId: string;
  rules: TopicRuleRead[];
}

const RULE_TYPE_LABELS: Record<RuleType, string> = {
  preferred_domain: "선호 도메인",
  blocked_domain: "차단 도메인",
  include: "포함 키워드",
  exclude: "제외 키워드",
};

export default function RuleTable({ topicId, rules }: RuleTableProps) {
  const qc = useQueryClient();
  const [newRule, setNewRule] = useState<TopicRuleCreate>({
    rule_type: "preferred_domain",
    pattern: "",
    is_regex: false,
    priority: 10,
  });

  const addMutation = useMutation({
    mutationFn: (data: TopicRuleCreate) => api.post(`/topics/${topicId}/rules`, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["topic", topicId] });
      setNewRule({ rule_type: "preferred_domain", pattern: "", is_regex: false, priority: 10 });
      toast.success("규칙이 추가되었습니다.");
    },
    onError: () => toast.error("규칙 추가 실패"),
  });

  const deleteMutation = useMutation({
    mutationFn: (ruleId: string) => api.delete(`/rules/${ruleId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["topic", topicId] });
      toast.success("규칙이 삭제되었습니다.");
    },
    onError: () => toast.error("규칙 삭제 실패"),
  });

  const handleAdd = () => {
    if (!newRule.pattern.trim()) return toast.error("패턴을 입력하세요.");
    addMutation.mutate(newRule);
  };

  return (
    <div className="space-y-3">
      <div className="rounded-md border border-border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted">
            <tr>
              <th className="text-left px-3 py-2 font-medium text-muted-foreground">타입</th>
              <th className="text-left px-3 py-2 font-medium text-muted-foreground">패턴</th>
              <th className="text-left px-3 py-2 font-medium text-muted-foreground">정규식</th>
              <th className="text-left px-3 py-2 font-medium text-muted-foreground">우선순위</th>
              <th className="w-12 px-3 py-2" />
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {rules.length === 0 && (
              <tr>
                <td colSpan={5} className="px-3 py-6 text-center text-muted-foreground text-xs">
                  등록된 규칙이 없습니다
                </td>
              </tr>
            )}
            {rules.map((rule) => (
              <tr key={rule.rule_id} className="hover:bg-muted/30">
                <td className="px-3 py-2">
                  <span className="text-xs text-muted-foreground">{RULE_TYPE_LABELS[rule.rule_type]}</span>
                </td>
                <td className="px-3 py-2 font-mono text-xs">{rule.pattern}</td>
                <td className="px-3 py-2 text-xs">{rule.is_regex ? "✓" : "-"}</td>
                <td className="px-3 py-2 text-xs">{rule.priority}</td>
                <td className="px-3 py-2">
                  <Button
                    size="icon"
                    variant="ghost"
                    className="h-7 w-7"
                    onClick={() => deleteMutation.mutate(rule.rule_id)}
                  >
                    <Trash2 className="w-3.5 h-3.5 text-destructive" />
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex gap-2 items-center">
        <Select
          value={newRule.rule_type}
          onValueChange={(v) => setNewRule((p) => ({ ...p, rule_type: v as RuleType }))}
        >
          <SelectTrigger className="w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {Object.entries(RULE_TYPE_LABELS).map(([v, label]) => (
              <SelectItem key={v} value={v}>{label}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Input
          placeholder="패턴 입력"
          value={newRule.pattern}
          onChange={(e) => setNewRule((p) => ({ ...p, pattern: e.target.value }))}
          className="flex-1"
          onKeyDown={(e) => e.key === "Enter" && handleAdd()}
        />

        <Button size="sm" onClick={handleAdd} disabled={addMutation.isPending}>
          <Plus className="w-3.5 h-3.5" />
          추가
        </Button>
      </div>
    </div>
  );
}
