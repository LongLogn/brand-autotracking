import { LogOut, Plus } from 'lucide-react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { SAMPLE_USER } from '../data/mock';
import { useStore } from '../lib/store';

export function initials(name: string) {
  const words = name.trim().split(/\s+/);
  return ((words[0]?.[0] ?? '') + (words[words.length - 1]?.[0] ?? '')).toUpperCase();
}

export function AppShell() {
  const { brands, alerts, signOut, toast } = useStore();
  const navigate = useNavigate();

  return (
    <div className="shell">
      <a className="skip" href="#main">
        Bỏ qua tới nội dung
      </a>
      <aside className="rail">
        <NavLink to="/brands" end className="wordmark">
          <span className="wordmark-mark" aria-hidden="true" />
          Brand Auto-Tracking
        </NavLink>

        <nav aria-label="Nhãn hàng" className="rail-nav">
          <p className="rail-heading">Nhãn hàng</p>
          <ul className="rail-list">
            {brands.map((b, i) => {
              const unread = alerts.filter((a) => a.brandId === b.id && !a.read && a.kind === 'triggered').length;
              return (
                <li key={b.id}>
                  <NavLink to={`/brands/${b.id}`} className="rail-link">
                    <span className={`avatar avatar-${i % 4}`} aria-hidden="true">
                      {initials(b.name)}
                      <span className={b.active ? 'avatar-dot avatar-dot-on' : 'avatar-dot'} />
                    </span>
                    <span className="rail-name">{b.name}</span>
                    {unread > 0 && (
                      <span className="rail-badge" aria-label={`${unread} cảnh báo chưa xem`}>
                        {unread}
                      </span>
                    )}
                  </NavLink>
                </li>
              );
            })}
          </ul>
          <NavLink to="/brands/new" className="rail-add">
            <Plus size={16} aria-hidden="true" />
            Thêm nhãn hàng
          </NavLink>
        </nav>

        <div className="rail-user">
          <span className="avatar avatar-user" aria-hidden="true">
            {initials(SAMPLE_USER.name)}
          </span>
          <span className="rail-user-text">
            <span className="rail-user-name">{SAMPLE_USER.name}</span>
            <span className="rail-user-mail">{SAMPLE_USER.email}</span>
          </span>
          <button
            type="button"
            className="icon-button"
            aria-label="Đăng xuất"
            title="Đăng xuất"
            onClick={() => {
              signOut();
              navigate('/login');
            }}
          >
            <LogOut size={17} aria-hidden="true" />
          </button>
        </div>
      </aside>

      <main id="main" className="main">
        <Outlet />
      </main>

      <div className="toast-region" aria-live="polite">
        {toast && (
          <p key={toast.id} className={`toast toast-${toast.tone}`}>
            {toast.text}
          </p>
        )}
      </div>
    </div>
  );
}
