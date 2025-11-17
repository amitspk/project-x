import axios, { AxiosError } from 'axios';
import type { AdminConfig } from '@/context/AdminConfigContext';
import type {
  Publisher,
  PublisherConfig,
  PublisherListResponse,
  PublisherResponse,
  QueueStats,
  PublisherStatus
} from '@/types/publisher';
import type { JobStatus } from '@/types/job';

export type ApiSuccess<T> = {
  status: string;
  message?: string;
  result: T;
  request_id?: string;
  metadata?: Record<string, unknown>;
};

export type ApiError = {
  status: string;
  message: string;
  detail?: unknown;
  request_id?: string;
  status_code?: number;
};

export type ListPublishersParams = {
  page?: number;
  pageSize?: number;
  status?: PublisherStatus | '';
};

export type CreatePublisherPayload = {
  name: string;
  domain: string;
  email: string;
  subscription_tier?: string;
  config?: Partial<PublisherConfig>;
};

export type UpdatePublisherPayload = {
  name?: string;
  email?: string;
  status?: PublisherStatus;
  subscription_tier?: string;
  config?: Partial<PublisherConfig>;
};

export type ApiClient = ReturnType<typeof createApiClient>;

function toApiError(error: unknown): ApiError {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<ApiError>;
    const responseData = axiosError.response?.data;
    if (responseData) {
      return {
        status: responseData.status ?? 'error',
        message: responseData.message ?? axiosError.message,
        detail: responseData.detail,
        request_id: responseData.request_id,
        status_code: axiosError.response?.status
      };
    }
    return {
      status: 'error',
      message: axiosError.message,
      status_code: axiosError.response?.status
    };
  }

  if (error instanceof Error) {
    return { status: 'error', message: error.message };
  }

  return { status: 'error', message: 'Unknown error' };
}

export function createApiClient(config: AdminConfig) {
  const client = axios.create({
    baseURL: `${config.baseUrl.replace(/\/$/, '')}/api/v1`,
    timeout: 15000
  });

  client.interceptors.request.use((request) => {
    if (config.adminKey) {
      request.headers = request.headers ?? {};
      request.headers['X-Admin-Key'] = config.adminKey;
    }
    return request;
  });

  return {
    async listPublishers(params: ListPublishersParams = {}): Promise<PublisherListResponse> {
      try {
        const response = await client.get<ApiSuccess<PublisherListResponse>>('/publishers/', {
          params: {
            page: params.page ?? 1,
            page_size: params.pageSize ?? 20,
            status: params.status || undefined
          }
        });
        return response.data.result;
      } catch (error) {
        throw toApiError(error);
      }
    },

    async getPublisher(id: string): Promise<Publisher> {
      try {
        const response = await client.get<ApiSuccess<PublisherResponse>>(`/publishers/${id}`);
        return response.data.result.publisher;
      } catch (error) {
        throw toApiError(error);
      }
    },

    async getPublisherByDomain(domain: string): Promise<Publisher> {
      try {
        const response = await client.get<ApiSuccess<PublisherResponse>>(`/publishers/by-domain/${domain}`);
        return response.data.result.publisher;
      } catch (error) {
        throw toApiError(error);
      }
    },

    async createPublisher(payload: CreatePublisherPayload): Promise<PublisherResponse> {
      try {
        const response = await client.post<ApiSuccess<PublisherResponse>>('/publishers/onboard', payload);
        return response.data.result;
      } catch (error) {
        throw toApiError(error);
      }
    },

    async updatePublisher(publisherId: string, payload: UpdatePublisherPayload): Promise<Publisher> {
      try {
        const response = await client.put<ApiSuccess<PublisherResponse>>(`/publishers/${publisherId}`, payload);
        return response.data.result.publisher;
      } catch (error) {
        throw toApiError(error);
      }
    },

    async deletePublisher(publisherId: string): Promise<void> {
      try {
        await client.delete(`/publishers/${publisherId}`);
      } catch (error) {
        throw toApiError(error);
      }
    },

    async reactivatePublisher(publisherId: string): Promise<Publisher> {
      try {
        const response = await client.post<ApiSuccess<PublisherResponse>>(`/publishers/${publisherId}/reactivate`);
        return response.data.result.publisher;
      } catch (error) {
        throw toApiError(error);
      }
    },

    async regenerateApiKey(publisherId: string): Promise<{ api_key: string; publisher: Publisher }> {
      try {
        const response = await client.post<ApiSuccess<{ api_key: string; publisher: Publisher }>>(
          `/publishers/${publisherId}/regenerate-api-key`
        );
        return response.data.result;
      } catch (error) {
        throw toApiError(error);
      }
    },

    async getQueueStats(): Promise<{ queue_stats: QueueStats; total_jobs: number }> {
      try {
        const response = await client.get<ApiSuccess<{ queue_stats: QueueStats; total_jobs: number }>>('/jobs/stats');
        return response.data.result;
      } catch (error) {
        throw toApiError(error);
      }
    },

    async cancelJob(jobId: string): Promise<void> {
      try {
        await client.post(`/jobs/cancel/${jobId}`);
      } catch (error) {
        throw toApiError(error);
      }
    },

    async getJobStatus(jobId: string): Promise<JobStatus> {
      try {
        const response = await client.get<ApiSuccess<JobStatus>>(`/jobs/status/${jobId}`);
        return response.data.result;
      } catch (error) {
        throw toApiError(error);
      }
    },

    async deleteBlog(blogId: string): Promise<void> {
      try {
        await client.delete(`/questions/${blogId}`);
      } catch (error) {
        throw toApiError(error);
      }
    }
  };
}
