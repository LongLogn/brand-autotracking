import { Activity, Bell, FileText, History, MessageCircle, RefreshCw, Tag } from 'lucide-react';
import { useEffect, useState, type ReactNode } from 'react';
import type { ApiBrandOverview, ApiTimelinePoint, ApiTrackingConfig } from '../lib/api';
import { RunStatusTag } from '../components/ui';
import { InfoTip } from '../components/viz';
import { RatioChart } from './AlertsTab';
import { Notice, SectionHead, displayTime, percent, type Client } from './shared';

export const FREQUENCY: Record<ApiTrackingConfig['frequency'], string> = { daily: 'Hằng ngày', 'twice-daily': 'Hai lần mỗi ngày', weekly: 'Hằng tuần' };

function Stat({ icon, tone, label, value, foot }: { icon: ReactNode; tone: 'ink' | 'chili' | 'leaf' | 'action' | 'amber'; label: string; value: ReactNode; foot?: ReactNode }) {
  return <div className={`stat stat-${tone}`}>
    <div className="stat-top"><span className="stat-icon" aria-hidden="true">{icon}</span><span className="stat-label">{label}</span></div>
    <div className="stat-main"><span className="stat-value">{value}</span></div>
    {foot && <div className="stat-foot">{foot}</div>}
  </div>;
}

export function BrandSummary({ api, brandId, config, nextRunAt, onOpenAlerts }: {
  api: Client; brandId: string; config: ApiTrackingConfig; nextRunAt: string | null; onOpenAlerts: () => void;
}) {
  const [overview, setOverview] = useState<ApiBrandOverview | null>(null);
  const [points, setPoints] = useState<ApiTimelinePoint[]>([]);
  const [limited, setLimited] = useState(false);
  const [revision, setRevision] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError(false);
    void api.getOverview(brandId, controller.signal)
      .then((data) => { if (!controller.signal.aborted) setOverview(data); })
      .catch(() => { if (!controller.signal.aborted) { setOverview(null); setError(true); } })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    // Biểu đồ là phần phụ: lỗi không chặn tổng quan.
    void api.getSentimentTimeline(brandId, controller.signal)
      .then((timeline) => { if (!controller.signal.aborted) { setPoints(timeline.points); setLimited(timeline.truncated || !!timeline.history_limited); } })
      .catch(() => { if (!controller.signal.aborted) { setPoints([]); setLimited(false); } });
    return () => controller.abort();
  }, [api, brandId, revision]);
  const last = points[points.length - 1];
  const alertCount = points.filter((point) => point.alert_id).length;
  return <section className="ws-stack">
    <SectionHead title="Tổng quan"
      info={<InfoTip>Số liệu phản ánh các bản ghi đã thu thập; nội dung thiếu ID nguồn có thể trùng. Cảm xúc, nếu có, chỉ là ước tính.</InfoTip>}
      actions={<button className="button button-sm" disabled={loading} onClick={() => setRevision((value) => value + 1)}><RefreshCw size={15} aria-hidden="true" />Tải lại tổng quan</button>} />
    {loading && <Notice>Đang tải tổng quan…</Notice>}
    {error && <Notice tone="error">Không tải được tổng quan. Hãy thử tải lại.</Notice>}
    {!loading && overview && <>
      <p className="ws-lead">Đã lưu {overview.post_count} bài viết, {overview.comment_count} bình luận và {overview.run_count} phiên tracking.</p>
      <div className="ws-stats">
        <Stat tone="ink" icon={<FileText size={17} />} label="Bài viết đã lưu" value={overview.post_count.toLocaleString('vi-VN')} />
        <Stat tone="action" icon={<MessageCircle size={17} />} label="Bình luận đã lưu" value={overview.comment_count.toLocaleString('vi-VN')} />
        <Stat tone={last?.alert_id ? 'chili' : 'leaf'} icon={<Activity size={17} />} label="Tỷ lệ tiêu cực hiện tại"
          value={last ? percent(last.negative, last.total) : <span className="na">Chưa có</span>}
          foot={last ? `${last.negative} / ${last.total} bình luận${limited ? ' trong phần dữ liệu hiển thị' : ''}` : 'Cần ít nhất một lần thu thập'} />
        <Stat tone={alertCount ? 'chili' : 'ink'} icon={<Bell size={17} />} label="Lần có cảnh báo" value={alertCount}
          foot={`${points.length} lần thu thập`} />
      </div>
      <div className="ws-overview-grid">
        <div className="panel ws-overview-chart">
          <SectionHead level={3} title="Tỷ lệ bình luận tiêu cực theo lần thu thập"
            actions={<button type="button" className="button button-sm" onClick={onOpenAlerts}><Bell size={15} aria-hidden="true" />Xem cảnh báo</button>} />
          {limited && <Notice>Biểu đồ chỉ tính trên một phần dữ liệu đã thu thập.</Notice>}
          {points.length > 0 ? <RatioChart points={points} compact /> : <div className="ws-empty-chart"><p>Chưa có lần thu thập thành công.</p></div>}
        </div>
        <div className="ws-stack">
          <div className="panel ws-facts">
            <h3><History size={16} aria-hidden="true" />Phiên gần nhất</h3>
            {overview.latest_run ? <>
              <RunStatusTag value={overview.latest_run.status} />
              <p className="ws-muted">Xếp hàng {displayTime(overview.latest_run.queued_at)}</p>
            </> : <p className="ws-muted">Chưa có phiên tracking.</p>}
          </div>
          <div className="panel ws-facts">
            <h3><Tag size={16} aria-hidden="true" />Đang theo dõi</h3>
            <div className="ws-keywords">{config.keywords.length ? config.keywords.map((keyword) => <span key={keyword} className="ws-keyword">{keyword}</span>) : <span className="ws-muted">Chưa có từ khóa</span>}</div>
            <p className="ws-muted">{config.active ? `${FREQUENCY[config.frequency]} lúc ${config.runTime}` : 'Lịch đang tắt'}{nextRunAt && config.active ? ` · Kế tiếp ${new Date(nextRunAt).toLocaleString('vi-VN', { timeZone: config.timezone })}` : ''}</p>
          </div>
        </div>
      </div>
    </>}
  </section>;
}
