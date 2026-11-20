import { Navigate, Route, Routes } from 'react-router-dom';
import { AppShell } from './components/AppShell';
import { useStore } from './lib/store';
import { AlertsPage } from './pages/AlertsPage';
import { AnalysisPage } from './pages/AnalysisPage';
import { BrandLayout } from './pages/BrandLayout';
import { BrandsPage } from './pages/BrandsPage';
import { ContentPage } from './pages/ContentPage';
import { LoginPage } from './pages/LoginPage';
import { NewBrandPage, SettingsPage } from './pages/SettingsPage';
import { OverviewPage } from './pages/OverviewPage';
import { RunDetailPage } from './pages/RunDetailPage';
import { RunsPage } from './pages/RunsPage';

export function App() {
  const { signedIn } = useStore();

  if (!signedIn) {
    return (
      <><p role="status">Chế độ minh họa — tất cả dữ liệu là dữ liệu mẫu.</p><Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes></>
    );
  }

  return (
    <><p role="status">Chế độ minh họa — tất cả dữ liệu là dữ liệu mẫu.</p><Routes>
      <Route path="/login" element={<Navigate to="/brands" replace />} />
      <Route element={<AppShell />}>
        <Route index element={<Navigate to="/brands" replace />} />
        <Route path="brands" element={<BrandsPage />} />
        <Route path="brands/new" element={<NewBrandPage />} />
        <Route path="brands/:brandId" element={<BrandLayout />}>
          <Route index element={<OverviewPage />} />
          <Route path="content" element={<ContentPage />} />
          <Route path="runs" element={<RunsPage />} />
          <Route path="runs/:runId" element={<RunDetailPage />} />
          <Route path="alerts" element={<AlertsPage />} />
          <Route path="analysis" element={<AnalysisPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/brands" replace />} />
      </Route>
    </Routes></>
  );
}
