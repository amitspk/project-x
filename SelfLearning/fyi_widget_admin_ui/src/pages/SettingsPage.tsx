import { useEffect, useState } from 'react';
import { useAdminConfig } from '@/context/AdminConfigContext';
import { useNotifications } from '@/components/ui/Notifications';

const ensureProtocol = (value: string) => {
  if (!value) return value;
  const trimmed = value.trim();
  if (/^https?:\/\//i.test(trimmed)) {
    return trimmed;
  }
  return `http://${trimmed}`;
};

const SettingsPage = () => {
  const { config, setConfig, reset } = useAdminConfig();
  const { notify } = useNotifications();
  const [baseUrl, setBaseUrl] = useState(config.baseUrl);
  const [adminKey, setAdminKey] = useState(config.adminKey);
  const [showKey, setShowKey] = useState(false);

  useEffect(() => {
    setBaseUrl(config.baseUrl);
    setAdminKey(config.adminKey);
  }, [config.baseUrl, config.adminKey]);

  const save = () => {
    if (!baseUrl.trim()) {
      notify({ title: 'Base URL is required', type: 'error' });
      return;
    }
    const normalizedBaseUrl = ensureProtocol(baseUrl).replace(/\/$/, '');
    setConfig({ baseUrl: normalizedBaseUrl, adminKey: adminKey.trim() });
    setBaseUrl(normalizedBaseUrl);
    notify({ title: 'Settings saved', type: 'success' });
  };

  const handleReset = () => {
    reset();
    notify({ title: 'Settings reset', description: 'Reverted to defaults. Re-enter your admin key if needed.', type: 'info' });
  };

  return (
    <div className="space-y-6">
      <section className="rounded-xl bg-white p-6 shadow-sm">
        <h2 className="text-xl font-semibold">API configuration</h2>
        <p className="mt-2 text-sm text-slate-500">
          Define where requests should be sent and which admin key to use. Values are stored locally in your browser only.
        </p>
        <form className="mt-4 space-y-4" onSubmit={(event) => event.preventDefault()}>
          <label className="flex flex-col text-sm">
            <span className="mb-1 font-medium">API base URL</span>
            <input
              type="url"
              value={baseUrl}
              placeholder="http://127.0.0.1:8005"
              onChange={(event) => setBaseUrl(event.target.value)}
              className="rounded-md border border-slate-300 px-3 py-2"
              required
            />
          </label>
          <label className="flex flex-col text-sm">
            <span className="mb-1 font-medium">Admin key (X-Admin-Key)</span>
            <div className="flex items-center gap-2">
              <input
                type={showKey ? 'text' : 'password'}
                value={adminKey}
                onChange={(event) => setAdminKey(event.target.value)}
                placeholder="admin_***"
                className="flex-1 rounded-md border border-slate-300 px-3 py-2"
              />
              <button
                type="button"
                className="rounded-md border border-slate-300 px-3 py-2 text-xs font-medium text-slate-600 hover:bg-slate-100"
                onClick={() => setShowKey(!showKey)}
              >
                {showKey ? 'Hide' : 'Show'}
              </button>
            </div>
          </label>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={save}
              className="inline-flex items-center rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
            >
              Save settings
            </button>
            <button
              type="button"
              className="text-sm text-slate-500 hover:text-slate-700"
              onClick={handleReset}
            >
              Reset to defaults
            </button>
          </div>
        </form>
      </section>

      <section className="rounded-xl bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold">Tips</h2>
        <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-slate-600">
          <li>The admin key stays in your browser. Users in other browsers need to enter their own key.</li>
          <li>
            When pointing to production, set the base URL to the Nginx endpoint that fans out to both API instances.
          </li>
          <li>Use the dashboard and jobs pages to validate API connectivity after updating your credentials.</li>
        </ul>
      </section>
    </div>
  );
};

export default SettingsPage;
