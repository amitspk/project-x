import { useState } from 'react';
import { useAdminApi } from '@/hooks/useAdminApi';
import { useNotifications } from '@/components/ui/Notifications';

const ContentCleanupPage = () => {
  const api = useAdminApi();
  const { notify } = useNotifications();
  const [blogId, setBlogId] = useState('');
  const [working, setWorking] = useState(false);
  const [confirm, setConfirm] = useState(false);

  const handleDelete = async () => {
    if (!blogId.trim()) {
      notify({ title: 'Enter a blog ID', type: 'info' });
      return;
    }

    if (!confirm) {
      notify({
        title: 'Confirm deletion',
        description: 'Check the confirmation box to proceed. This action cannot be undone.',
        type: 'info'
      });
      return;
    }

    setWorking(true);
    try {
      await api.deleteBlog(blogId.trim());
      notify({ title: 'Blog deleted', description: `All content removed for blog ${blogId.trim()}`, type: 'success' });
      setBlogId('');
      setConfirm(false);
    } catch (error: any) {
      notify({ title: 'Failed to delete blog', description: error.message ?? String(error), type: 'error' });
    } finally {
      setWorking(false);
    }
  };

  return (
    <div className="space-y-6">
      <section className="rounded-xl bg-white p-6 shadow-sm">
        <h2 className="text-xl font-semibold text-rose-700">Danger zone</h2>
        <p className="mt-2 max-w-2xl text-sm text-slate-600">
          Use this tool to purge a blog, its questions, summary, and embeddings. The deletion is immediate and
          irreversible. Double-check the blog ID before proceeding.
        </p>
        <div className="mt-6 flex flex-col gap-4 md:flex-row md:items-end">
          <label className="flex-1 text-sm">
            <span className="mb-1 block font-medium">Blog ID (Mongo ObjectId)</span>
            <input
              type="text"
              value={blogId}
              onChange={(event) => setBlogId(event.target.value)}
              placeholder="655c3b1d0f6c18c534b1a123"
              className="w-full rounded-md border border-slate-300 px-3 py-2"
            />
          </label>
          <label className="flex items-center gap-2 text-sm text-slate-600">
            <input type="checkbox" checked={confirm} onChange={(event) => setConfirm(event.target.checked)} />
            I understand this cannot be undone.
          </label>
          <button
            type="button"
            onClick={() => void handleDelete()}
            disabled={working}
            className="inline-flex items-center rounded-md bg-rose-600 px-4 py-2 text-sm font-medium text-white hover:bg-rose-500 disabled:opacity-40"
          >
            {working ? 'Deleting…' : 'Delete blog'}
          </button>
        </div>
      </section>
    </div>
  );
};

export default ContentCleanupPage;
