import { createContext, ReactNode, useCallback, useContext, useMemo, useState } from 'react';
import { v4 as uuid } from 'uuid';
import clsx from 'clsx';

export type NotificationType = 'success' | 'error' | 'info';

export type Notification = {
  id: string;
  type: NotificationType;
  title: string;
  description?: string;
};

type NotificationContextValue = {
  notify: (notification: Omit<Notification, 'id'>) => void;
};

const NotificationContext = createContext<NotificationContextValue | undefined>(undefined);

export const useNotifications = () => {
  const ctx = useContext(NotificationContext);
  if (!ctx) {
    throw new Error('useNotifications must be used within NotificationProvider');
  }
  return ctx;
};

export const NotificationProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [items, setItems] = useState<Notification[]>([]);

  const notify = useCallback((notification: Omit<Notification, 'id'>) => {
    const id = uuid();
    setItems((previous) => [...previous, { ...notification, id }]);
    setTimeout(() => {
      setItems((previous) => previous.filter((item) => item.id !== id));
    }, 4500);
  }, []);

  const value = useMemo(() => ({ notify }), [notify]);

  return (
    <NotificationContext.Provider value={value}>
      {children}
      <div className="pointer-events-none fixed inset-x-0 top-4 z-[9999] flex flex-col items-center gap-2 px-4">
        {items.map((item) => (
          <div
            key={item.id}
            className={clsx(
              'pointer-events-auto w-full max-w-md rounded-lg border px-4 py-3 shadow-sm backdrop-blur-sm transition-all',
              item.type === 'success' && 'border-green-200 bg-green-50 text-green-900',
              item.type === 'error' && 'border-rose-200 bg-rose-50 text-rose-900',
              item.type === 'info' && 'border-blue-200 bg-blue-50 text-blue-900'
            )}
          >
            <p className="text-sm font-semibold">{item.title}</p>
            {item.description && <p className="mt-1 text-xs opacity-80">{item.description}</p>}
          </div>
        ))}
      </div>
    </NotificationContext.Provider>
  );
};
