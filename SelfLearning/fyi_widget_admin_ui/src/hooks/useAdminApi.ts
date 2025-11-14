import { useMemo } from 'react';
import { useAdminConfig } from '@/context/AdminConfigContext';
import { createApiClient } from '@/utils/apiClient';

export const useAdminApi = () => {
  const { config } = useAdminConfig();

  return useMemo(() => createApiClient(config), [config]);
};
