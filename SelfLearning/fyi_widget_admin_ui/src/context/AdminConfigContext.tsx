import { createContext, useContext, useMemo } from 'react';
import { useLocalStorage } from '@/hooks/useLocalStorage';

export type AdminConfig = {
  baseUrl: string;
  adminKey: string;
};

type AdminConfigContextValue = {
  config: AdminConfig;
  setConfig: (config: AdminConfig) => void;
  reset: () => void;
};

const defaultConfig: AdminConfig = {
  baseUrl: import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8005',
  adminKey: ''
};

const AdminConfigContext = createContext<AdminConfigContextValue | undefined>(undefined);

export const AdminConfigProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [storedConfig, setStoredConfig] = useLocalStorage<AdminConfig>('fyi-admin-config', defaultConfig, {
    read: (value) => {
      if (!value) {
        return defaultConfig;
      }
      try {
        return JSON.parse(value) as AdminConfig;
      } catch (error) {
        console.warn('Failed to parse stored config, falling back to default.', error);
        return defaultConfig;
      }
    },
    write: (config) => JSON.stringify(config ?? defaultConfig)
  });

  const value = useMemo<AdminConfigContextValue>(
    () => ({
      config: storedConfig,
      setConfig: (config: AdminConfig) => setStoredConfig({ ...storedConfig, ...config }),
      reset: () => setStoredConfig(defaultConfig)
    }),
    [setStoredConfig, storedConfig]
  );

  return <AdminConfigContext.Provider value={value}>{children}</AdminConfigContext.Provider>;
};

export const useAdminConfig = (): AdminConfigContextValue => {
  const ctx = useContext(AdminConfigContext);
  if (!ctx) {
    throw new Error('useAdminConfig must be used within AdminConfigProvider');
  }
  return ctx;
};
