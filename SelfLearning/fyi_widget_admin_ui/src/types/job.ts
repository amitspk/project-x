export type JobStatus = {
  job_id: string;
  status: string;
  publisher_id?: string;
  publisher_domain?: string;
  blog_url?: string;
  created_at?: string;
  started_at?: string | null;
  completed_at?: string | null;
  updated_at?: string | null;
  attempts?: number;
  failure_reason?: string | null;
  metadata?: Record<string, unknown> | null;
};
