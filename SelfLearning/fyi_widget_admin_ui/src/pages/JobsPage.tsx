import { useEffect, useState } from 'react';
import dayjs from 'dayjs';
import { useAdminApi } from '@/hooks/useAdminApi';
import { useNotifications } from '@/components/ui/Notifications';
import type { JobStatus } from '@/types/job';

const JobsPage = () => {
  const api = useAdminApi();
  const { notify } = useNotifications();
  const [loadingStats, setLoadingStats] = useState(false);
  const [stats, setStats] = useState<{ queue_stats: Record<string, number>; total_jobs: number } | null>(null);
  const [jobId, setJobId] = useState('');
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [jobLoading, setJobLoading] = useState(false);

  const refreshStats = async () => {
    setLoadingStats(true);
    try {
      const data = await api.getQueueStats();
      setStats(data);
    } catch (error: any) {
      notify({ title: 'Failed to load queue stats', description: error.message ?? String(error), type: 'error' });
    } finally {
      setLoadingStats(false);
    }
  };

  useEffect(() => {
    void refreshStats();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const lookupJob = async () => {
    if (!jobId.trim()) {
      notify({ title: 'Enter a job ID', type: 'info' });
      return;
    }
    setJobLoading(true);
    try {
      const status = await api.getJobStatus(jobId.trim());
      setJobStatus(status);
    } catch (error: any) {
      setJobStatus(null);
      notify({ title: 'Failed to fetch job status', description: error.message ?? String(error), type: 'error' });
    } finally {
      setJobLoading(false);
    }
  };

  const cancelJob = async () => {
    if (!jobId.trim()) {
      notify({ title: 'Enter a job ID first', type: 'info' });
      return;
    }
    try {
      await api.cancelJob(jobId.trim());
      notify({ title: `Job ${jobId.trim()} cancelled`, type: 'success' });
      await refreshStats();
      await lookupJob();
    } catch (error: any) {
      notify({ title: 'Failed to cancel job', description: error.message ?? String(error), type: 'error' });
    }
  };

  return (
    <div className="space-y-6">
      <section className="rounded-xl bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <div>
            <h2 className="text-xl font-semibold">Queue statistics</h2>
            <p className="text-sm text-slate-500">
              Snapshot across all statuses. Use it to monitor backlog and confirm worker health.
            </p>
          </div>
          <button
            type="button"
            onClick={() => void refreshStats()}
            disabled={loadingStats}
            className="inline-flex items-center rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-40"
          >
            {loadingStats ? 'Refreshing…' : 'Refresh stats'}
          </button>
        </div>
        <div className="mt-6 grid gap-3 md:grid-cols-4">
          {stats ? (
            Object.entries(stats.queue_stats).map(([status, count]) => (
              <div key={status} className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                <p className="text-xs uppercase tracking-wide text-slate-500">{status}</p>
                <p className="mt-2 text-2xl font-semibold text-slate-900">{count}</p>
              </div>
            ))
          ) : (
            <p className="col-span-full text-sm text-slate-500">Stats will appear once data is available.</p>
          )}
          {stats && (
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
              <p className="text-xs uppercase tracking-wide text-slate-500">Total jobs (sum)</p>
              <p className="mt-2 text-2xl font-semibold text-slate-900">{stats.total_jobs}</p>
            </div>
          )}
        </div>
      </section>

      <section className="rounded-xl bg-white p-6 shadow-sm">
        <h2 className="text-xl font-semibold">Inspect or cancel a job</h2>
        <p className="mt-2 max-w-2xl text-sm text-slate-500">
          Provide a job ID to see its latest status, timestamps, and any failure reason. You can cancel pending jobs from
          here.
        </p>
        <div className="mt-4 flex flex-col gap-3 md:flex-row md:items-center">
          <input
            type="text"
            value={jobId}
            onChange={(event) => setJobId(event.target.value)}
            placeholder="job-uuid"
            className="w-full rounded-md border border-slate-300 px-3 py-2 md:w-72"
          />
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => void lookupJob()}
              disabled={jobLoading}
              className="inline-flex items-center rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 disabled:opacity-40"
            >
              {jobLoading ? 'Fetching…' : 'Get status'}
            </button>
            <button
              type="button"
              onClick={() => void cancelJob()}
              className="inline-flex items-center rounded-md bg-rose-600 px-4 py-2 text-sm font-medium text-white hover:bg-rose-500"
            >
              Cancel job
            </button>
          </div>
        </div>

        {jobStatus && (
          <dl className="mt-6 grid gap-4 rounded-xl border border-slate-200 bg-slate-50 p-4 font-mono text-xs text-slate-700 md:grid-cols-2">
            <div>
              <dt className="text-slate-500">Job ID</dt>
              <dd className="mt-1 break-words text-slate-900">{jobStatus.job_id}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Status</dt>
              <dd className="mt-1 uppercase tracking-wide text-slate-900">{jobStatus.status}</dd>
            </div>
            {jobStatus.publisher_domain && (
              <div>
                <dt className="text-slate-500">Publisher domain</dt>
                <dd className="mt-1 text-slate-900">{jobStatus.publisher_domain}</dd>
              </div>
            )}
            {jobStatus.blog_url && (
              <div>
                <dt className="text-slate-500">Blog URL</dt>
                <dd className="mt-1 break-words text-slate-900">{jobStatus.blog_url}</dd>
              </div>
            )}
            <div>
              <dt className="text-slate-500">Created</dt>
              <dd className="mt-1 text-slate-900">{formatDate(jobStatus.created_at)}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Started</dt>
              <dd className="mt-1 text-slate-900">{formatDate(jobStatus.started_at)}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Completed</dt>
              <dd className="mt-1 text-slate-900">{formatDate(jobStatus.completed_at)}</dd>
            </div>
            {jobStatus.failure_reason && (
              <div className="md:col-span-2">
                <dt className="text-slate-500">Failure reason</dt>
                <dd className="mt-1 whitespace-pre-wrap break-words text-rose-700">{jobStatus.failure_reason}</dd>
              </div>
            )}
          </dl>
        )}
      </section>
    </div>
  );
};

const formatDate = (value?: string | null) => {
  if (!value) return '—';
  return dayjs(value).format('YYYY-MM-DD HH:mm:ss');
};

export default JobsPage;
