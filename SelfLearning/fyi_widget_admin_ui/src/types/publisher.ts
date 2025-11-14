export type PublisherStatus = 'active' | 'inactive' | 'suspended' | 'trial';

export type PublisherConfig = {
  questions_per_blog: number;
  summary_model: string;
  questions_model: string;
  chat_model: string;
  summary_temperature: number;
  questions_temperature: number;
  chat_temperature: number;
  summary_max_tokens: number;
  questions_max_tokens: number;
  chat_max_tokens: number;
  generate_summary: boolean;
  generate_embeddings: boolean;
  daily_blog_limit: number | null;
  max_total_blogs?: number | null;
  whitelisted_blog_urls?: string[] | null;
  custom_question_prompt?: string | null;
  custom_summary_prompt?: string | null;
  ui_theme_color?: string | null;
  ui_icon_style?: string | null;
};

export type Publisher = {
  id: string;
  name: string;
  domain: string;
  email: string;
  api_key?: string | null;
  status: PublisherStatus;
  config: PublisherConfig;
  created_at?: string | null;
  updated_at?: string | null;
  last_active_at?: string | null;
  total_blogs_processed: number;
  total_questions_generated: number;
  blog_slots_reserved?: number;
  subscription_tier?: string | null;
};

export type PublisherListResponse = {
  success: boolean;
  publishers: Publisher[];
  total: number;
  page: number;
  page_size: number;
};

export type PublisherResponse = {
  success: boolean;
  publisher: Publisher;
  api_key?: string;
  message?: string;
};

export type QueueStats = Record<string, number> & {
  pending?: number;
  processing?: number;
  completed?: number;
  failed?: number;
};
