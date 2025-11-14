import { Routes, Route } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { AdminConfigProvider } from '@/context/AdminConfigContext';
import { NotificationProvider } from '@/components/ui/Notifications';
import DashboardPage from '@/pages/DashboardPage';
import PublishersPage from '@/pages/PublishersPage';
import JobsPage from '@/pages/JobsPage';
import ContentCleanupPage from '@/pages/ContentCleanupPage';
import SettingsPage from '@/pages/SettingsPage';

const App = () => {
  return (
    <NotificationProvider>
      <AdminConfigProvider>
        <Layout>
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/publishers" element={<PublishersPage />} />
            <Route path="/jobs" element={<JobsPage />} />
            <Route path="/cleanup" element={<ContentCleanupPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </Layout>
      </AdminConfigProvider>
    </NotificationProvider>
  );
};

export default App;
