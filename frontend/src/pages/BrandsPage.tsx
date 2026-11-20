import { Clock, Plus, Store } from 'lucide-react';
import { Link } from 'react-router-dom';
import { initials } from '../components/AppShell';
import { EmptyState, PlatformTag, RunStatusTag, SampleBadge } from '../components/ui';
import { Sparkline } from '../components/viz';
import { useStore } from '../lib/store';
import { fmtDateTime, FREQUENCY_LABEL } from '../lib/format';

export function BrandsPage() {
  const { brands, runs, alerts } = useStore();

  return (
    <div className="page">
      <header className="page-head">
        <div className="page-title-row">
          <h1 className="page-title">Nhãn hàng</h1>
          <SampleBadge />
        </div>
        <Link to="/brands/new" className="button button-primary">
          <Plus size={16} aria-hidden="true" />
          Thêm nhãn hàng
        </Link>
      </header>

      {brands.length === 0 ? (
        <EmptyState
          icon={<Store size={28} />}
          title="Chưa có nhãn hàng nào"
          action={
            <Link to="/brands/new" className="button button-primary">
              Thêm nhãn hàng đầu tiên
            </Link>
          }
        />
      ) : (
        <ul className="brand-cards">
          {brands.map((b, i) => {
            const own = runs.filter((r) => r.brandId === b.id).sort((x, y) => x.startedAt.localeCompare(y.startedAt));
            const last = own[own.length - 1];
            const unread = alerts.filter((a) => a.brandId === b.id && !a.read && a.kind === 'triggered').length;
            const neg = own.slice(-14).map((r) => r.negativeComments);
            return (
              <li key={b.id}>
                <Link to={`/brands/${b.id}`} className="brand-card">
                  <div className="brand-card-head">
                    <span className={`avatar avatar-lg avatar-${i % 4}`} aria-hidden="true">
                      {initials(b.name)}
                    </span>
                    <span className="brand-card-name">
                      {b.name}
                      <span className="brand-card-desc">{b.description}</span>
                    </span>
                    {unread > 0 && <span className="rail-badge">{unread}</span>}
                  </div>

                  <div className="brand-card-spark">
                    {neg.length > 1 ? (
                      <>
                        <span className="brand-card-spark-label">Bình luận tiêu cực</span>
                        <Sparkline values={neg} tone="chili" />
                      </>
                    ) : (
                      <span className="muted">Chưa có dữ liệu</span>
                    )}
                  </div>

                  <div className="brand-card-foot">
                    <span className={b.active ? 'pill pill-on' : 'pill'}>{b.active ? 'Đang theo dõi' : 'Tạm dừng'}</span>
                    <span className="brand-card-platforms">
                      {b.platforms.map((p) => (
                        <PlatformTag key={p} id={p} compact />
                      ))}
                    </span>
                  </div>
                  <div className="brand-card-foot muted">
                    <span className="meta-item">
                      <Clock size={14} aria-hidden="true" />
                      {FREQUENCY_LABEL[b.frequency]} {b.runTime}
                    </span>
                    {last ? (
                      <span className="meta-item">
                        <RunStatusTag value={last.status} />
                        {fmtDateTime(last.startedAt).split(' ')[1]}
                      </span>
                    ) : (
                      <span>Chưa chạy</span>
                    )}
                  </div>
                </Link>
              </li>
            );
          })}
          <li>
            <Link to="/brands/new" className="brand-card brand-card-add">
              <Plus size={28} aria-hidden="true" />
              Thêm nhãn hàng
            </Link>
          </li>
        </ul>
      )}
    </div>
  );
}
