import { useCallback, useEffect, useMemo, useState } from 'react';
import { useForm } from 'react-hook-form';
import clsx from 'clsx';
import { useAdminApi } from '@/hooks/useAdminApi';
import { useNotifications } from '@/components/ui/Notifications';
import type { Publisher, PublisherStatus, PublisherConfig } from '@/types/publisher';

const statusOptions: { label: string; value: PublisherStatus | '' }[] = [
  { label: 'All statuses', value: '' },
  { label: 'Active', value: 'active' },
  { label: 'Inactive', value: 'inactive' },
  { label: 'Suspended', value: 'suspended' },
  { label: 'Trial', value: 'trial' }
];

const modelOptions = [
  { label: 'GPT-4o Mini', value: 'gpt-4o-mini' },
  { label: 'GPT-4o', value: 'gpt-4o' },
  { label: 'GPT-3.5 Turbo', value: 'gpt-3.5-turbo' },
  { label: 'Claude 3.5 Sonnet', value: 'claude-3-5-sonnet-20241022' },
  { label: 'Claude 3.5 Haiku', value: 'claude-3-5-haiku-20241022' },
  { label: 'Gemini 2.5 Pro', value: 'gemini-2.5-pro' },
  { label: 'Gemini 1.5 Pro', value: 'gemini-1.5-pro' },
  { label: 'Gemini 1.5 Flash', value: 'gemini-1.5-flash' }
];

type CreatePublisherFormValues = {
  name: string;
  domain: string;
  email: string;
  subscription_tier: string;
  questions_per_blog: number;
  use_grounding: boolean;
  summary_model: string;
  questions_model: string;
  chat_model: string;
  daily_blog_limit?: string;
  max_total_blogs?: string;
  threshold_before_processing_blog: number;
  whitelisted_blog_urls: string;
  custom_question_prompt?: string;
  custom_summary_prompt?: string;
  widget_config: string;
};

type UpdatePublisherFormValues = {
  name?: string;
  email?: string;
  status?: PublisherStatus;
  subscription_tier?: string;
  config_json?: string;
};

const safeParseJson = (value?: string) => {
  if (!value || !value.trim()) return undefined;
  try {
    const parsed = JSON.parse(value);
    return parsed;
  } catch (error) {
    throw new Error('Config JSON is invalid');
  }
};

const PublisherCard: React.FC<{
  publisher: Publisher;
  onRefresh: () => void;
  onRegenerate: (publisherId: string) => Promise<void>;
  onDeactivate: (publisherId: string) => Promise<void>;
  onReactivate: (publisherId: string) => Promise<void>;
  onUpdate: (publisherId: string, values: UpdatePublisherFormValues) => Promise<void>;
}> = ({ publisher, onRefresh, onDeactivate, onReactivate, onRegenerate, onUpdate }) => {
  const { register, handleSubmit, reset, formState } = useForm<UpdatePublisherFormValues>({
    defaultValues: {
      name: publisher.name,
      email: publisher.email,
      status: publisher.status,
      subscription_tier: publisher.subscription_tier ?? 'free'
    }
  });

  const handleUpdate = handleSubmit(async (values: UpdatePublisherFormValues) => {
    try {
      await onUpdate(publisher.id, values);
      reset(values);
    } catch (error) {
      // error handled upstream via notifications
    }
  });

  return (
    <article className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <header className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
        <div>
          <h3 className="text-lg font-semibold text-slate-900">
            {publisher.name}
            <span className="ml-2 text-sm font-normal text-slate-500">{publisher.domain}</span>
          </h3>
          <p className="text-sm text-slate-500">{publisher.email}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs uppercase tracking-wide text-slate-600">
          <span className={clsx('rounded-full px-2 py-1', statusBadgeColor(publisher.status))}>{publisher.status}</span>
          <span className="rounded-full bg-slate-100 px-2 py-1 text-slate-500">Tier: {publisher.subscription_tier ?? 'free'}</span>
          <span className="rounded-full bg-slate-100 px-2 py-1 text-slate-500">
            Blogs processed: {publisher.total_blogs_processed ?? 0}
          </span>
          <span className="rounded-full bg-slate-100 px-2 py-1 text-slate-500">
            Questions generated: {publisher.total_questions_generated ?? 0}
          </span>
          <span className="rounded-full bg-slate-100 px-2 py-1 text-slate-500">
            Slots reserved: {publisher.blog_slots_reserved ?? 0}
          </span>
        </div>
      </header>

      <dl className="mt-4 grid grid-cols-1 gap-4 text-sm md:grid-cols-2">
        <div className="rounded-lg border border-slate-200 p-3">
          <dt className="text-xs uppercase tracking-wide text-slate-500">Config</dt>
          <dd className="mt-2 max-h-32 overflow-auto whitespace-pre-wrap rounded bg-slate-50 p-2 text-xs text-slate-700">
            {JSON.stringify(publisher.config, null, 2)}
          </dd>
        </div>
        <div className="rounded-lg border border-slate-200 p-3">
          <dt className="text-xs uppercase tracking-wide text-slate-500">Metadata</dt>
          <dd className="mt-2 space-y-1 text-xs text-slate-600">
            <p>Created: {publisher.created_at ?? '—'}</p>
            <p>Updated: {publisher.updated_at ?? '—'}</p>
            <p>Last active: {publisher.last_active_at ?? '—'}</p>
          </dd>
        </div>
      </dl>

      <form onSubmit={handleUpdate} className="mt-6 space-y-4">
        <div className="grid gap-4 md:grid-cols-2">
          <label className="flex flex-col text-sm">
            <span className="mb-1 font-medium">Name</span>
            <input
              type="text"
              {...register('name')}
              className="rounded-md border border-slate-300 px-3 py-2 text-sm"
              placeholder="Publisher name"
            />
          </label>
          <label className="flex flex-col text-sm">
            <span className="mb-1 font-medium">Email</span>
            <input
              type="email"
              {...register('email')}
              className="rounded-md border border-slate-300 px-3 py-2 text-sm"
              placeholder="admin@example.com"
            />
          </label>
          <label className="flex flex-col text-sm">
            <span className="mb-1 font-medium">Status</span>
            <select {...register('status')} className="rounded-md border border-slate-300 px-3 py-2 text-sm">
              {statusOptions
                .filter((option) => option.value !== '')
                .map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
            </select>
          </label>
          <label className="flex flex-col text-sm">
            <span className="mb-1 font-medium">Subscription tier</span>
            <input
              type="text"
              {...register('subscription_tier')}
              className="rounded-md border border-slate-300 px-3 py-2 text-sm"
              placeholder="free / basic / pro"
            />
          </label>
        </div>
        <label className="flex flex-col text-sm">
          <span className="mb-1 font-medium">Config override (JSON, optional)</span>
          <textarea
            {...register('config_json')}
            className="min-h-[140px] rounded-md border border-slate-300 px-3 py-2 font-mono text-xs"
            placeholder='{"max_total_blogs": 100, "whitelisted_blog_urls": ["https://example.com"]}'
          />
        </label>
        <div className="flex flex-wrap gap-2">
          <button
            type="submit"
            disabled={formState.isSubmitting}
            className="inline-flex items-center rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-slate-700 disabled:opacity-40"
          >
            {formState.isSubmitting ? 'Saving…' : 'Save changes'}
          </button>
          <button
            type="button"
            className="inline-flex items-center rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100"
            onClick={() => reset()}
          >
            Reset
          </button>
          <button
            type="button"
            className="inline-flex items-center rounded-md border border-rose-200 px-4 py-2 text-sm font-medium text-rose-600 hover:bg-rose-50"
            onClick={() => onDeactivate(publisher.id)}
          >
            Mark inactive
          </button>
          <button
            type="button"
            className="inline-flex items-center rounded-md border border-emerald-200 px-4 py-2 text-sm font-medium text-emerald-600 hover:bg-emerald-50"
            onClick={() => onReactivate(publisher.id)}
          >
            Reactivate
          </button>
          <button
            type="button"
            className="inline-flex items-center rounded-md border border-indigo-200 px-4 py-2 text-sm font-medium text-indigo-600 hover:bg-indigo-50"
            onClick={() => onRegenerate(publisher.id)}
          >
            Regenerate API key
          </button>
          <button
            type="button"
            className="inline-flex items-center rounded-md border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100"
            onClick={onRefresh}
          >
            Refresh
          </button>
        </div>
      </form>
    </article>
  );
};

const statusBadgeColor = (status: PublisherStatus) => {
  switch (status) {
    case 'active':
      return 'bg-emerald-100 text-emerald-700';
    case 'inactive':
      return 'bg-slate-200 text-slate-700';
    case 'suspended':
      return 'bg-rose-100 text-rose-700';
    case 'trial':
      return 'bg-amber-100 text-amber-700';
    default:
      return 'bg-slate-200 text-slate-700';
  }
};

const PublishersPage = () => {
  const api = useAdminApi();
  const { notify } = useNotifications();
  const [publishers, setPublishers] = useState<Publisher[]>([]);
  const [statusFilter, setStatusFilter] = useState<PublisherStatus | ''>('');
  const [page] = useState(1);
  const [loading, setLoading] = useState(false);
  const [domainSearch, setDomainSearch] = useState('');
  const [lastCreated, setLastCreated] = useState<{ publisher: Publisher; apiKey?: string } | null>(null);
  const [lastRegenerated, setLastRegenerated] = useState<{ publisher: Publisher; apiKey: string } | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    formState,
    watch,
    setValue
  } = useForm<CreatePublisherFormValues>({
    defaultValues: {
      name: '',
      domain: '',
      email: '',
      subscription_tier: 'free',
      questions_per_blog: 5,
      use_grounding: false,
      summary_model: 'gpt-4o-mini',
      questions_model: 'gpt-4o-mini',
      chat_model: 'gpt-4o-mini',
      daily_blog_limit: '',
      max_total_blogs: '',
      threshold_before_processing_blog: 0,
      whitelisted_blog_urls: '',
      custom_question_prompt: '',
      custom_summary_prompt: '',
      widget_config: ''
    }
  });
  const questionsModel = watch('questions_model');
  
  // Check if the selected questions model is a Gemini model
  const isGeminiModel = Boolean(questionsModel && typeof questionsModel === 'string' && questionsModel.toLowerCase().includes('gemini'));
  
  // Reset use_grounding to false if a non-Gemini model is selected
  useEffect(() => {
    if (!isGeminiModel && questionsModel) {
      setValue('use_grounding', false, { shouldDirty: false });
    }
  }, [questionsModel, isGeminiModel, setValue]);
  
  // Register questions_model and create a custom onChange handler
  const questionsModelField = register('questions_model', { required: 'Questions model is required' });
  const { onChange: questionsModelOnChange, ...questionsModelRestProps } = questionsModelField;
  
  // Handle questions_model change to trigger watch() re-render
  const handleQuestionsModelChange = useCallback((e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    questionsModelOnChange(e);
    setValue('questions_model', value, { shouldValidate: true, shouldDirty: true });
  }, [questionsModelOnChange, setValue]);
  
  // Memoize select props to avoid re-creating on every render
  const questionsModelSelectProps = useMemo(() => ({
    ...questionsModelRestProps,
    onChange: handleQuestionsModelChange
  }), [questionsModelRestProps, handleQuestionsModelChange]);

  const fetchPublishers = useCallback(async () => {
    setLoading(true);
    try {
      if (domainSearch.trim()) {
        const publisher = await api.getPublisherByDomain(domainSearch.trim());
        setPublishers(publisher ? [publisher] : []);
      } else {
        const result = await api.listPublishers({ page, status: statusFilter || undefined, pageSize: 50 });
        setPublishers(result.publishers);
      }
    } catch (error: any) {
      notify({ title: 'Failed to load publishers', description: error.message ?? String(error), type: 'error' });
      setPublishers([]);
    } finally {
      setLoading(false);
    }
  }, [api, domainSearch, notify, page, statusFilter]);

  useEffect(() => {
    void fetchPublishers();
  }, [fetchPublishers]);

  const onCreatePublisher = handleSubmit(async (values: CreatePublisherFormValues) => {
    try {
      const toNumberOrUndefined = (input?: string) => {
        if (!input || !input.trim()) return undefined;
        const parsed = Number(input.trim());
        return Number.isFinite(parsed) ? parsed : undefined;
      };

      const whitelistEntries = values.whitelisted_blog_urls
        .split(/\r?\n|,/)
        .map((entry: string) => entry.trim())
        .filter(Boolean);

      // Check if the questions model is a Gemini model
      const isGemini = values.questions_model?.toLowerCase().includes('gemini') ?? false;

      const config: Partial<PublisherConfig> = {
        questions_per_blog: values.questions_per_blog,
        // generate_summary and generate_embeddings default to true, no need to send
        // Only enable use_grounding if a Gemini model is selected and checkbox is checked
        use_grounding: isGemini && values.use_grounding ? true : false,
        summary_model: values.summary_model,
        questions_model: values.questions_model,
        chat_model: values.chat_model,
        daily_blog_limit: toNumberOrUndefined(values.daily_blog_limit),
        max_total_blogs: toNumberOrUndefined(values.max_total_blogs),
        threshold_before_processing_blog: values.threshold_before_processing_blog ?? 0,
        whitelisted_blog_urls: whitelistEntries.length > 0 ? whitelistEntries : undefined,
        custom_question_prompt: values.custom_question_prompt?.trim() || undefined,
        custom_summary_prompt: values.custom_summary_prompt?.trim() || undefined
      };
      const cleanedConfig = Object.fromEntries(
        Object.entries(config).filter(([, value]) => value !== undefined)
      ) as Partial<PublisherConfig>;

      // Parse widget_config (required)
      if (!values.widget_config?.trim()) {
        notify({
          title: 'Widget config required',
          description: 'Widget config is required. Please provide a valid JSON configuration.',
          type: 'error'
        });
        return;
      }
      
      let widgetConfig: Record<string, any>;
      try {
        widgetConfig = JSON.parse(values.widget_config.trim());
      } catch (error) {
        notify({
          title: 'Invalid widget config JSON',
          description: 'Please check the widget config JSON format.',
          type: 'error'
        });
        return;
      }

      const payload = {
        name: values.name.trim(),
        domain: values.domain.trim(),
        email: values.email.trim(),
        subscription_tier: values.subscription_tier.trim(),
        config: cleanedConfig,
        widget_config: widgetConfig
      };
      const result = await api.createPublisher(payload);
      setLastCreated({
        publisher: result.publisher,
        apiKey: result.api_key ?? undefined
      });
      notify({
        title: 'Publisher created',
        description: 'Review the new publisher details below and copy the API key before closing.',
        type: 'success'
      });
      reset();
      setDomainSearch('');
      await fetchPublishers();
    } catch (error: any) {
      notify({ title: 'Failed to create publisher', description: error.message ?? String(error), type: 'error' });
    }
  });

  const handleRegenerateApiKey = async (publisherId: string) => {
    try {
      const result = await api.regenerateApiKey(publisherId);
      // Find the publisher to display in the banner
      const publisher = publishers.find(p => p.id === publisherId);
      if (publisher && result.api_key) {
        setLastRegenerated({
          publisher,
          apiKey: result.api_key
        });
        notify({
          title: 'API key regenerated',
          description: 'Review the new API key below and copy it before closing.',
          type: 'success'
        });
      }
      await fetchPublishers();
    } catch (error: any) {
      notify({
        title: 'Failed to regenerate API key',
        description: error.message ?? String(error),
        type: 'error'
      });
    }
  };

  const handleDeactivate = async (publisherId: string) => {
    try {
      await api.updatePublisher(publisherId, { status: 'inactive' });
      notify({ title: 'Publisher marked inactive', type: 'success' });
      await fetchPublishers();
    } catch (error: any) {
      notify({ title: 'Failed to update publisher', description: error.message ?? String(error), type: 'error' });
    }
  };

  const handleReactivate = async (publisherId: string) => {
    try {
      await api.reactivatePublisher(publisherId);
      notify({ title: 'Publisher reactivated', type: 'success' });
      await fetchPublishers();
    } catch (error: any) {
      notify({ title: 'Failed to reactivate publisher', description: error.message ?? String(error), type: 'error' });
    }
  };

  const handleUpdatePublisher = async (publisherId: string, values: UpdatePublisherFormValues) => {
    try {
      const payload = {
        name: values.name?.trim() || undefined,
        email: values.email?.trim() || undefined,
        status: values.status,
        subscription_tier: values.subscription_tier?.trim() || undefined,
        config: safeParseJson(values.config_json)
      };
      await api.updatePublisher(publisherId, payload);
      notify({ title: 'Publisher updated', type: 'success' });
      await fetchPublishers();
    } catch (error: any) {
      notify({ title: 'Failed to update publisher', description: error.message ?? String(error), type: 'error' });
      throw error;
    }
  };

  return (
    <div className="space-y-6">
      {lastCreated && (
        <section className="rounded-xl border border-emerald-200 bg-emerald-50/60 p-6 shadow-sm">
          <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
            <div>
              <h3 className="text-lg font-semibold text-emerald-900">Publisher created successfully</h3>
              <p className="mt-1 text-sm text-emerald-800">
                {lastCreated.publisher.name} · {lastCreated.publisher.domain}
              </p>
            </div>
            <button
              type="button"
              className="self-start rounded-md border border-emerald-300 px-3 py-1 text-xs font-medium text-emerald-800 hover:bg-emerald-100"
              onClick={() => setLastCreated(null)}
            >
              Close
            </button>
          </div>
          {lastCreated.apiKey ? (
            <div className="mt-4 space-y-2">
              <p className="text-xs uppercase tracking-wide text-emerald-800">API key</p>
              <div className="flex flex-col gap-2 md:flex-row md:items-center">
                <code className="flex-1 break-all rounded-md bg-white px-3 py-2 text-sm text-emerald-900 shadow-sm">
                  {lastCreated.apiKey}
                </code>
                <button
                  type="button"
                  className="rounded-md border border-emerald-300 px-3 py-2 text-sm font-medium text-emerald-800 hover:bg-emerald-100"
                  onClick={() => navigator.clipboard.writeText(lastCreated.apiKey ?? '')}
                >
                  Copy key
                </button>
              </div>
              <p className="text-xs text-emerald-700">
                Store this securely. The key will be hidden once you close this banner.
              </p>
            </div>
          ) : (
            <p className="mt-4 text-sm text-emerald-800">Publisher onboarded successfully (no new key issued).</p>
          )}
        </section>
      )}

      {lastRegenerated && (
        <section className="rounded-xl border border-indigo-200 bg-indigo-50/60 p-6 shadow-sm">
          <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
            <div>
              <h3 className="text-lg font-semibold text-indigo-900">API key regenerated successfully</h3>
              <p className="mt-1 text-sm text-indigo-800">
                {lastRegenerated.publisher.name} · {lastRegenerated.publisher.domain}
              </p>
            </div>
            <button
              type="button"
              className="self-start rounded-md border border-indigo-300 px-3 py-1 text-xs font-medium text-indigo-800 hover:bg-indigo-100"
              onClick={() => setLastRegenerated(null)}
            >
              Close
            </button>
          </div>
          <div className="mt-4 space-y-2">
            <p className="text-xs uppercase tracking-wide text-indigo-800">New API key</p>
            <div className="flex flex-col gap-2 md:flex-row md:items-center">
              <code className="flex-1 break-all rounded-md bg-white px-3 py-2 text-sm text-indigo-900 shadow-sm">
                {lastRegenerated.apiKey}
              </code>
              <button
                type="button"
                className="rounded-md border border-indigo-300 px-3 py-2 text-sm font-medium text-indigo-800 hover:bg-indigo-100"
                onClick={() => navigator.clipboard.writeText(lastRegenerated.apiKey)}
              >
                Copy key
              </button>
            </div>
            <p className="text-xs text-indigo-700">
              Store this securely. The old key was invalidated and this key will be hidden once you close this banner.
            </p>
          </div>
        </section>
      )}

      <section className="rounded-xl bg-white p-6 shadow-sm">
        <h2 className="text-xl font-semibold">Create publisher</h2>
        <p className="mt-2 text-sm text-slate-500">
          Provide the baseline information. Optional config overrides let you set limits, whitelisted URLs, and LLM
          options on day one.
        </p>
        <form onSubmit={onCreatePublisher} className="mt-4 space-y-6">
          <div className="grid gap-4 md:grid-cols-2">
            <label className="flex flex-col text-sm">
              <span className="mb-1 font-medium">
                Name <span className="text-rose-600">*</span>
              </span>
              <input
                type="text"
                {...register('name', { required: 'Name is required' })}
                className="rounded-md border border-slate-300 px-3 py-2"
                placeholder="Tech Blog Inc"
              />
              {formState.errors.name && (
                <span className="mt-1 text-xs text-rose-600">{formState.errors.name.message}</span>
              )}
            </label>
            <label className="flex flex-col text-sm">
              <span className="mb-1 font-medium">
                Domain <span className="text-rose-600">*</span>
              </span>
              <input
                type="text"
                {...register('domain', { required: 'Domain is required' })}
                className="rounded-md border border-slate-300 px-3 py-2"
                placeholder="example.com"
              />
              {formState.errors.domain && (
                <span className="mt-1 text-xs text-rose-600">{formState.errors.domain.message}</span>
              )}
            </label>
            <label className="flex flex-col text-sm">
              <span className="mb-1 font-medium">
                Admin email <span className="text-rose-600">*</span>
              </span>
              <input
                type="email"
                {...register('email', { required: 'Admin email is required' })}
                className="rounded-md border border-slate-300 px-3 py-2"
                placeholder="admin@example.com"
              />
              {formState.errors.email && (
                <span className="mt-1 text-xs text-rose-600">{formState.errors.email.message}</span>
              )}
            </label>
            <label className="flex flex-col text-sm">
              <span className="mb-1 font-medium">
                Subscription tier <span className="text-rose-600">*</span>
              </span>
              <input
                type="text"
                {...register('subscription_tier', { required: 'Subscription tier is required' })}
                className="rounded-md border border-slate-300 px-3 py-2"
                placeholder="free / basic / pro"
              />
              {formState.errors.subscription_tier && (
                <span className="mt-1 text-xs text-rose-600">{formState.errors.subscription_tier.message}</span>
              )}
            </label>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            <label className="flex flex-col text-sm">
              <span className="mb-1 font-medium">
                Questions per blog <span className="text-rose-600">*</span>
              </span>
              <input
                type="number"
                min={1}
                max={20}
                {...register('questions_per_blog', { 
                  required: 'Questions per blog is required',
                  valueAsNumber: true, 
                  min: { value: 1, message: 'Must be at least 1' }, 
                  max: { value: 20, message: 'Must be at most 20' }
                })}
                className="rounded-md border border-slate-300 px-3 py-2"
              />
              <span className="mt-1 text-xs text-slate-500">Default is 5. Choose between 1 and 20.</span>
              {formState.errors.questions_per_blog && (
                <span className="mt-1 text-xs text-rose-600">{formState.errors.questions_per_blog.message}</span>
              )}
            </label>
            <label className="flex flex-col text-sm">
              <span className="mb-1 font-medium">
                Summary model <span className="text-rose-600">*</span>
              </span>
              <select 
                {...register('summary_model', { required: 'Summary model is required' })} 
                className="rounded-md border border-slate-300 px-3 py-2"
              >
                {modelOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              {formState.errors.summary_model && (
                <span className="mt-1 text-xs text-rose-600">{formState.errors.summary_model.message}</span>
              )}
            </label>
            <label className="flex flex-col text-sm">
              <span className="mb-1 font-medium">
                Questions model <span className="text-rose-600">*</span>
              </span>
              <select 
                {...questionsModelSelectProps}
                className="rounded-md border border-slate-300 px-3 py-2"
              >
                {modelOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              {questionsModel && (
                <span className="mt-1 text-xs text-slate-500">
                  Selected: {questionsModel} {isGeminiModel ? '(Gemini - grounding available)' : '(Grounding not available)'}
                </span>
              )}
              {formState.errors.questions_model && (
                <span className="mt-1 text-xs text-rose-600">{formState.errors.questions_model.message}</span>
              )}
            </label>
            <label className="flex flex-col text-sm">
              <span className="mb-1 font-medium">
                Chat model <span className="text-rose-600">*</span>
              </span>
              <select 
                {...register('chat_model', { required: 'Chat model is required' })} 
                className="rounded-md border border-slate-300 px-3 py-2"
              >
                {modelOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              {formState.errors.chat_model && (
                <span className="mt-1 text-xs text-rose-600">{formState.errors.chat_model.message}</span>
              )}
            </label>
            <label
              className={clsx(
                'flex items-center gap-2 text-sm',
                isGeminiModel ? 'text-slate-700' : 'text-slate-400 cursor-not-allowed'
              )}
            >
              <input
                type="checkbox"
                {...register('use_grounding')}
                disabled={!isGeminiModel}
                className={clsx(
                  'cursor-pointer disabled:cursor-not-allowed disabled:opacity-50'
                )}
              />
              <span>
                Use grounding (Gemini only)
                {isGeminiModel ? (
                  <span className="ml-1 text-xs text-slate-500">Real-time info via Google Search</span>
                ) : (
                  <span className="ml-1 text-xs text-slate-400">Select a Gemini model for questions to enable</span>
                )}
              </span>
            </label>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            <label className="flex flex-col text-sm">
              <span className="mb-1 font-medium">Daily blog limit (optional)</span>
              <input
                type="number"
                min={1}
                {...register('daily_blog_limit')}
                className="rounded-md border border-slate-300 px-3 py-2"
                placeholder="Leave blank for unlimited"
              />
            </label>
            <label className="flex flex-col text-sm">
              <span className="mb-1 font-medium">Max total blogs (optional)</span>
              <input
                type="number"
                min={1}
                {...register('max_total_blogs')}
                className="rounded-md border border-slate-300 px-3 py-2"
                placeholder="Leave blank for unlimited"
              />
            </label>
            <label className="flex flex-col text-sm">
              <span className="mb-1 font-medium">Threshold before processing blog</span>
              <input
                type="number"
                min={0}
                {...register('threshold_before_processing_blog', { valueAsNumber: true, min: 0 })}
                className="rounded-md border border-slate-300 px-3 py-2"
                placeholder="0"
              />
              <span className="mt-1 text-xs text-slate-500">
                Number of triggers required before processing (default: 0)
              </span>
            </label>
          </div>

          <label className="flex flex-col text-sm">
            <span className="mb-1 font-medium">Whitelisted URLs (optional)</span>
            <textarea
              {...register('whitelisted_blog_urls')}
              className="min-h-[120px] rounded-md border border-slate-300 px-3 py-2 font-mono text-xs"
              placeholder={'https://example.com\nhttps://example.com/blog'}
            />
            <span className="mt-1 text-xs text-slate-500">
              Enter one URL or prefix per line. Leave blank to allow all URLs.
            </span>
          </label>

          <div className="grid gap-4 md:grid-cols-2">
            <label className="flex flex-col text-sm">
              <span className="mb-1 font-medium">Custom question prompt (optional)</span>
              <textarea
                {...register('custom_question_prompt')}
                className="min-h-[120px] rounded-md border border-slate-300 px-3 py-2 text-sm"
                placeholder="Instructions for generated questions..."
              />
              <span className="mt-1 text-xs text-slate-500">
                Tailor the tone, structure, or focus of generated Q&A pairs.
              </span>
            </label>
            <label className="flex flex-col text-sm">
              <span className="mb-1 font-medium">Custom summary prompt (optional)</span>
              <textarea
                {...register('custom_summary_prompt')}
                className="min-h-[120px] rounded-md border border-slate-300 px-3 py-2 text-sm"
                placeholder="Instructions for summaries..."
              />
              <span className="mt-1 text-xs text-slate-500">
                Provide guidance for summary style or priorities.
              </span>
            </label>
          </div>

          <label className="flex flex-col text-sm">
            <span className="mb-1 font-medium">
              Widget config <span className="text-rose-600">*</span>
            </span>
            <textarea
              {...register('widget_config', { required: 'Widget config is required' })}
              className="min-h-[200px] rounded-md border border-slate-300 px-3 py-2 font-mono text-xs"
              placeholder={`{\n  "theme": "light",\n  "useDummyData": false,\n  "gaTrackingId": "G-XXXXXXXXXX",\n  "gaEnabled": true,\n  "adsenseForSearch": {\n    "enabled": true,\n    "pubId": "partner-pub-XXXXX"\n  }\n}`}
            />
            <span className="mt-1 text-xs text-slate-500">
              JSON configuration for widget settings (theme, GA, ads, etc.). Required field.
            </span>
            {formState.errors.widget_config && (
              <span className="mt-1 text-xs text-rose-600">{formState.errors.widget_config.message}</span>
            )}
          </label>

          <div className="flex items-center gap-2">
            <button
              type="submit"
              disabled={formState.isSubmitting}
              className="inline-flex items-center rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-40"
            >
              {formState.isSubmitting ? 'Creating…' : 'Create publisher'}
            </button>
            <button
              type="button"
              className="text-sm text-slate-500 hover:text-slate-700"
              onClick={() => reset()}
            >
              Clear form
            </button>
          </div>
        </form>
      </section>

      <section className="rounded-xl bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <h2 className="text-xl font-semibold">Publishers</h2>
            <p className="mt-2 text-sm text-slate-500">Search by domain or filter by status to narrow down the list.</p>
          </div>
          <div className="flex flex-col gap-3 md:flex-row md:items-center">
            <label className="text-sm">
              <span className="mb-1 block font-medium">Status</span>
              <select
                value={statusFilter}
                onChange={(event) => setStatusFilter(event.target.value as PublisherStatus | '')}
                className="rounded-md border border-slate-300 px-3 py-2"
              >
                {statusOptions.map((option) => (
                  <option key={option.label} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-sm">
              <span className="mb-1 block font-medium">Search by domain</span>
              <input
                type="text"
                value={domainSearch}
                placeholder="publisher-domain.com"
                onChange={(event) => setDomainSearch(event.target.value)}
                className="w-full rounded-md border border-slate-300 px-3 py-2 md:w-64"
              />
            </label>
            <button
              type="button"
              onClick={() => void fetchPublishers()}
              className="inline-flex items-center rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
            >
              Apply filters
            </button>
          </div>
        </div>

        {loading && <p className="mt-6 text-sm text-slate-500">Loading publishers…</p>}
        {!loading && publishers.length === 0 && (
          <p className="mt-6 text-sm text-slate-500">No publishers found. Try a different filter.</p>
        )}
        <div className="mt-6 grid gap-6">
          {publishers.map((publisher) => (
            <PublisherCard
              key={publisher.id}
              publisher={publisher}
              onRefresh={() => void fetchPublishers()}
              onRegenerate={handleRegenerateApiKey}
              onDeactivate={handleDeactivate}
              onReactivate={handleReactivate}
              onUpdate={handleUpdatePublisher}
            />
          ))}
        </div>
      </section>
    </div>
  );
};

export default PublishersPage;
