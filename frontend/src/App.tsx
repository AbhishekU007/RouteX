import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AppShell } from './components/layout/AppShell';
import { OverviewPage } from './pages/OverviewPage';
import { RoutePlannerPage } from './pages/RoutePlannerPage';
import { LiveMapPage } from './pages/LiveMapPage';
import { TrafficSimulatorPage } from './pages/TrafficSimulatorPage';
import { AnalyticsPage } from './pages/AnalyticsPage';
import { SettingsPage } from './pages/SettingsPage';
import { TrafficStatusProvider, useTrafficStatus } from './services/TrafficStatusContext';

export default function App() {
  return (
    <TrafficStatusProvider>
      <BrowserRouter>
        <ApplicationRoutes />
      </BrowserRouter>
    </TrafficStatusProvider>
  );
}

function ApplicationRoutes() {
  const { status } = useTrafficStatus();
  const source = status?.source === 'TomTom' && status.available ? 'Live' : 'Simulated';
  const trafficStatus = status ? `${source} · ${status.status} traffic` : 'Loading traffic status…';
  return (
    <AppShell city={status?.city || 'Agra, Uttar Pradesh, India'} trafficStatus={trafficStatus}>
      <Routes>
        <Route path="/" element={<OverviewPage />} />
        <Route path="/planner" element={<RoutePlannerPage />} />
        <Route path="/map" element={<LiveMapPage />} />
        <Route path="/traffic" element={<TrafficSimulatorPage />} />
        <Route path="/analytics" element={<AnalyticsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppShell>
  );
}
