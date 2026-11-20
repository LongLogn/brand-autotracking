import { Bell, Clock, FileText, History, LayoutDashboard, Pause, Play, Settings, Sparkles } from 'lucide-react';
import { NavLink, Navigate, Outlet, useParams } from 'react-router-dom';
import { initials } from '../components/AppShell';
import { PlatformTag, SampleBadge } from '../components/ui';
import { useBrandData, useStore } from '../lib/store';
import { fmtDateTime, FREQUENCY_LABEL } from '../lib/format';

export function useBrandId() {
  return useParams().brandId ?? '';
}

export function BrandLayout() {
  const brandId = useBrandId();
  const { setActive, notify, brands } = useStore();
  const { brand, alerts } = useBrandData(brandId);

  if (!brand) return <Navigate to="/brands" replace />;

  const unread = alerts.filter((a) => !a.read && a.kind === 'triggered').length;
  const tabs = [
    { to: '', label: 'Tổng quan', icon: LayoutDashboard, end: true },
    { to: 'content', label: 'Nội dung', icon: FileText },
    { to: 'runs', label: 'Phiên tracking', icon: History },
    { to: 'alerts', label: 'Cảnh báo', icon: Bell, count: unread },
    { to: 'analysis', label: 'Phân tích AI', icon: Sparkles },
    { to: 'settings', label: 'Cấu hình', icon: Settings },
  ];

  const toggle = () => {
    setActive(brand.id, !brand.active);
    notify(brand.active ? 'Đã tạm dừng theo dõi.' : 'Đã bật lại theo dõi.');
  };

  return (
    <div className="brand">
      <header className="brand-head">
        <span className={`avatar avatar-lg avatar-${brands.findIndex((b) => b.id === brand.id) % 4}`} aria-hidden="true">
          {initials(brand.name)}
        </span>
        <div className="brand-head-text">
          <div className="brand-title-row">
            <h1 className="brand-title">{brand.name}</h1>
            <span className={brand.active ? 'pill pill-on' : 'pill'}>{brand.active ? 'Đang theo dõi' : 'Tạm dừng'}</span>
            <SampleBadge />
          </div>
          <div className="brand-meta">
            <span className="meta-item">
              <Clock size={14} aria-hidden="true" />
              {brand.active && brand.nextRunAt ? `${FREQUENCY_LABEL[brand.frequency]}, kế tiếp ${fmtDateTime(brand.nextRunAt)}` : 'Không có lịch chạy'}
            </span>
            <span className="meta-item">
              {brand.platforms.map((p) => (
                <PlatformTag key={p} id={p} compact />
              ))}
            </span>
            <span className="meta-item">{brand.keywords.length} từ khóa</span>
          </div>
        </div>
        <button type="button" className={brand.active ? 'button' : 'button button-primary'} onClick={toggle}>
          {brand.active ? <Pause size={16} aria-hidden="true" /> : <Play size={16} aria-hidden="true" />}
          {brand.active ? 'Tạm dừng' : 'Bật lại'}
        </button>
      </header>

      <nav className="tabs" aria-label={`Mục của ${brand.name}`}>
        {tabs.map((t) => (
          <NavLink key={t.to} to={t.to} end={t.end} className="tab">
            <t.icon size={16} aria-hidden="true" />
            {t.label}
            {t.count ? <span className="tab-count">{t.count}</span> : null}
          </NavLink>
        ))}
      </nav>

      <div className="brand-body">
        <Outlet />
      </div>
    </div>
  );
}
