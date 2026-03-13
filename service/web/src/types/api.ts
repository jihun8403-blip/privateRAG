// ========== Topic ==========

export type RuleType = "preferred_domain" | "blocked_domain" | "include" | "exclude";

export interface TopicRuleRead {
  rule_id: string;
  topic_id: string;
  rule_type: RuleType;
  pattern: string;
  is_regex: boolean;
  enabled: boolean;
  priority: number;
  created_at: string;
  updated_at: string;
}

export interface TopicRead {
  topic_id: string;
  name: string;
  description: string | null;
  language: string;
  priority: number;
  enabled: boolean;
  schedule_cron: string | null;
  relevance_threshold: number;
  must_include: string[];
  must_exclude: string[];
  created_at: string;
  updated_at: string;
  rules: TopicRuleRead[];
}

export interface TopicSummary {
  topic_id: string;
  name: string;
  description: string | null;
  priority: number;
  enabled: boolean;
  schedule_cron: string | null;
  created_at: string;
}

export interface TopicCreate {
  name: string;
  description?: string;
  language?: string;
  priority?: number;
  schedule_cron?: string;
  relevance_threshold?: number;
  must_include?: string[];
  must_exclude?: string[];
  enabled?: boolean;
  rules?: TopicRuleCreate[];
}

export interface TopicUpdate {
  name?: string;
  description?: string;
  language?: string;
  priority?: number;
  schedule_cron?: string;
  relevance_threshold?: number;
  must_include?: string[];
  must_exclude?: string[];
  enabled?: boolean;
}

export interface TopicRuleCreate {
  rule_type: RuleType;
  pattern: string;
  is_regex?: boolean;
  enabled?: boolean;
  priority?: number;
}

export interface TopicRuleUpdate {
  rule_type?: RuleType;
  pattern?: string;
  is_regex?: boolean;
  enabled?: boolean;
  priority?: number;
}

// ========== Document ==========

export interface DocumentRead {
  doc_id: string;
  topic_id: string;
  url: string;
  title: string | null;
  author: string | null;
  published_at: string | null;
  collected_at: string;
  language: string | null;
  summary: string | null;
  relevance_score: number | null;
  relevance_reason: string | null;
  current_version: number;
  is_active: boolean;
  archive_tier: number;
  created_at: string;
  updated_at: string;
}

export interface DocumentVersionRead {
  version_id: string;
  doc_id: string;
  version_no: number;
  content_hash: string;
  summary: string | null;
  relevance_score: number | null;
  created_at: string;
  change_type: string;
}

// ========== Model Registry ==========

export type Provider = "openai" | "ollama" | "anthropic" | "gemini" | "google";

export interface ModelRegistryRead {
  model_id: string;
  provider: Provider;
  model_name: string;
  capability_tags: string[];
  max_context: number | null;
  cost_input_per_1k: number;
  cost_output_per_1k: number;
  daily_budget_tokens: number;
  priority: number;
  fallback_order: number;
  enabled: boolean;
  used_tokens_today: number;
  last_reset_date: string | null;
  call_interval_seconds: number;
}

export interface ModelRegistryCreate {
  provider: Provider;
  model_name: string;
  capability_tags: string[];
  api_key?: string;
  max_context?: number;
  cost_input_per_1k?: number;
  cost_output_per_1k?: number;
  daily_budget_tokens?: number;
  priority?: number;
  fallback_order?: number;
  enabled?: boolean;
  call_interval_seconds?: number;
}

export interface ModelRegistryUpdate {
  provider?: Provider;
  model_name?: string;
  capability_tags?: string[];
  api_key?: string;
  max_context?: number;
  cost_input_per_1k?: number;
  cost_output_per_1k?: number;
  daily_budget_tokens?: number;
  priority?: number;
  fallback_order?: number;
  enabled?: boolean;
  call_interval_seconds?: number;
}

export interface ModelUsageLogRead {
  usage_id: string;
  model_id: string;
  task_type: string;
  input_tokens: number;
  output_tokens: number;
  cost_estimate: number;
  executed_at: string;
  status: string;
}

export interface UsageSummary {
  model_id: string;
  model_name: string;
  provider: Provider;
  used_tokens_today: number;
  daily_budget_tokens: number;
  budget_remaining: number;
  last_reset_date: string | null;
}

// ========== RAG ==========

export interface RagQueryRequest {
  query: string;
  topic_ids?: string[];
  top_k?: number;
  model_id?: string;
}

export interface RagSource {
  doc_id: string;
  url: string;
  title: string | null;
  collected_at: string;
  relevance_score: number;
}

export interface RagQueryResponse {
  answer: string;
  sources: RagSource[];
  model_used: string;
  query: string;
}

export interface ChunkRead {
  chunk_id: string;
  doc_id: string;
  chunk_index: number;
  chunk_text: string;
  token_count: number | null;
  score: number | null;
}

// ========== Document Summary ==========

export interface RelatedDocItem {
  doc_id: string;
  url: string;
  title: string | null;
  relevance_score: number;
}

export interface DocSummaryResponse {
  summary: string;
  related_docs: RelatedDocItem[];
}

// ========== Chat UI ==========

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: RagSource[];
  model_used?: string;
  timestamp: Date;
}
