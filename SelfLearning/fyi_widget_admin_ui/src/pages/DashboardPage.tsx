import { useEffect, useState } from 'react';
import { useAdminApi } from '@/hooks/useAdminApi';
import { useNotifications } from '@/components/ui/Notifications';
import { useAdminConfig } from '@/context/AdminConfigContext';

const DashboardPage = () => {
  const api = useAdminApi();
  const { notify } = useNotifications();
  const { config } = useAdminConfig();
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState<{ queue_stats: Record<string, number>; total_jobs: number } | null>(null);

  useEffect(() => {
    const fetchStats = async () => {
      setLoading(true);
      try {
        const data = await api.getQueueStats();
        setStats(data);
      } catch (error: any) {
        notify({ title: 'Failed to load queue stats', description: error.message ?? String(error), type: 'error' });
      } finally {
        setLoading(false);
      }
    };

    if (config.adminKey) {
      void fetchStats();
    }
  }, [api, config.adminKey, notify]);

  return (
    <div className="space-y-6">
      <section className="rounded-xl bg-white p-6 shadow-sm">
        <h2 className="text-xl font-semibold">Welcome back</h2>
        <p className="mt-2 text-sm text-slate-600">
          Use this dashboard to manage publishers, monitor the processing queue, and maintain content safely.
        </p>
        {!config.adminKey && (
          <p className="mt-4 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
            Add your admin key in Settings to enable API calls.
          </p>
        )}
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        <div className="rounded-xl bg-white p-6 shadow-sm">
          <h3 className="text-lg font-semibold">Queue Snapshot</h3>
          <p className="mt-1 text-sm text-slate-500">
            Current counts by status. Refresh the page to get the latest snapshot.
          </p>
          {loading && <p className="mt-4 text-sm text-slate-500">Loading queue stats…</p>}
          {!loading && stats && (
            <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
              {Object.entries(stats.queue_stats).map(([status, count]) => (
                <div key={status} className="rounded-lg border border-slate-200 p-3">
                  <dt className="text-xs uppercase tracking-wide text-slate-500">{status}</dt>
                  <dd className="mt-2 text-2xl font-semibold text-slate-900">{count}</dd>
                </div>
              ))}
              <div className="rounded-lg border border-slate-200 p-3">
                <dt className="text-xs uppercase tracking-wide text-slate-500">Total Jobs (all time)</dt>
                <dd className="mt-2 text-2xl font-semibold text-slate-900">{stats.total_jobs}</dd>
              </div>
            </dl>
          )}
          {!loading && !stats && (
            <p className="mt-4 text-sm text-slate-500">Queue stats will appear after you configure the admin key.</p>
          )}
        </div>

        <div className="rounded-xl bg-white p-6 shadow-sm">
          <h3 className="text-lg font-semibold">Common admin tasks</h3>
          <ul className="mt-4 space-y-3 text-sm">
            <li>
              <span className="font-medium text-slate-800">Onboard a new publisher</span>
              <p className="text-slate-500">Navigate to the Publishers tab &raquo; Create Publisher.</p>
            </li>
            <li>
              <span className="font-medium text-slate-800">Rotate a publisher API key</span>
              <p className="text-slate-500">Open a publisher record and choose “Regenerate API key”.</p>
            </li>
            <li>
              <span className="font-medium text-slate-800">Delete test content</span>
              <p className="text-slate-500">Use the Content Cleanup screen to remove blogs safely.</p>
            </li>
          </ul>
        </div>
      </section>
    </div>
  );
};

export default DashboardPage;
