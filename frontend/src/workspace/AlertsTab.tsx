import { BellRing, FileText, MessageSquareWarning, RefreshCw } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import type { ApiAlert, ApiAlertRule, ApiTimelinePoint } from '../lib/api';
import { InfoTip } from '../components/viz';
import { Notice, Pager, SectionHead, displayTime, percent, shortTime, type Client } from './shared';

/** Cột tỷ lệ tiêu cực lũy kế sau từng lần thu thập; vân gạch là phần chưa phân loại. */
export function RatioChart({ points, compact = false }: { points: ApiTimelinePoint[]; compact?: boolean }) {
  const ratios = points.map((point) => (point.total > 0 ? point.negative / point.total : 0));
  const top = Math.max(0.4, ...ratios.map((ratio, index) => ratio + (points[index].total > 0 ? points[index].unclassified / points[index].total : 0))) * 1.15;
  return <div className={compact ? 'ws-ratio ws-ratio-compact' : 'ws-ratio'} aria-hidden="true">
    <div className="ws-ratio-plot">
      {points.map((point, index) => {
        const ratio = ratios[index];
        const unknown = point.total > 0 ? point.unclassified / point.total : 0;
        const kind = point.alert_id ? 'alert' : index === 0 ? 'base' : 'calm';
        return <div key={point.run_id} className={`ws-ratio-col ws-ratio-${kind}`}>
          <span className="ws-ratio-value">{percent(point.negative, point.total)}</span>
          <span className="ws-ratio-unknown" style={{ height: `${(unknown / top) * 100}%` }} />
          <span className="ws-ratio-bar" style={{ height: `${Math.max(ratio / top, 0.012) * 100}%` }} />
        </div>;
      })}
    </div>
    <div className="ws-ratio-axis">
      {points.map((point, index) => <div key={point.run_id} className="ws-ratio-tick">
        <span className="ws-ratio-tag">{point.alert_id ? 'Cảnh báo' : index === 0 ? 'Mốc' : `Lần ${index + 1}`}</span>
        {!compact && <span className="ws-ratio-time">{shortTime(point.finished_at)}</span>}
      </div>)}
    </div>
  </div>;
}

/** Diễn biến tỷ lệ bình luận tiêu cực lũy kế sau từng lần thu thập; tự cập nhật. */
export function RunAlertTimeline({ api, brandId, focusAlertId }: { api: Client; brandId: string; focusAlertId: string | null }) {
  const [points, setPoints] = useState<ApiTimelinePoint[]>([]);
  const [alerts, setAlerts] = useState<ApiAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [feedback, setFeedback] = useState('');
  const [busy, setBusy] = useState(false);
  const [revision, setRevision] = useState(0);
  const section = useRef<HTMLElement | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    const load = () => Promise.all([api.getSentimentTimeline(brandId, controller.signal), api.listAlerts(brandId, controller.signal, { limit: 20, offset: 0 })])
      .then(([timeline, history]) => { if (!controller.signal.aborted) { setPoints(timeline.points); setAlerts(history.filter((item) => item.mode === 'run')); setError(false); } })
      .catch(() => { if (!controller.signal.aborted) setError(true); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    void load();
    const timer = window.setInterval(() => void load(), 10000);
    return () => { controller.abort(); window.clearInterval(timer); };
  }, [api, brandId, revision]);
  useEffect(() => { if (focusAlertId && !loading) section.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }); }, [focusAlertId, loading]);
  const latest = alerts[0];
  const last = points[points.length - 1];
  const reevaluate = async () => {
    setBusy(true); setFeedback('');
    try {
      const result = await api.evaluateLatestRun(brandId);
      const labels = { triggered: 'Lần thu thập gần nhất đã có cảnh báo; không tạo cảnh báo trùng.', not_triggered: 'Lần thu thập gần nhất chưa vượt ngưỡng.',
        insufficient_data: result.reason === 'baseline' ? 'Đây là lần thu thập mốc, chưa có lần trước để so sánh.' : 'Không đủ dữ liệu để so sánh.',
        disabled: 'Quy tắc bình luận tiêu cực đang tắt.', not_applicable: 'Chưa có lần thu thập demo nào.' };
      setFeedback(`${labels[result.status]}${result.previous_total && result.current_total ? ` Lần trước: ${percent(result.previous_negative ?? 0, result.previous_total)}; lần này: ${percent(result.current_negative ?? 0, result.current_total)}.` : ''}`);
      setRevision((value) => value + 1);
    } catch { setFeedback('Không đánh giá lại được. Hãy thử sau.'); }
    finally { setBusy(false); }
  };
  return <section className="panel ws-live" ref={section} id="live-alerts">
    <SectionHead title="Cảnh báo theo lần thu thập"
      info={<InfoTip>Tỷ lệ = bình luận tiêu cực / tổng bình luận đã thu thập, cộng dồn đến từng lần. Cảnh báo khi tỷ lệ tăng vượt "Ngưỡng tăng (%)" của quy tắc bình luận so với lần trước. Dữ liệu và nhãn của kịch bản demo là giả lập. Tự cập nhật mỗi 10 giây.</InfoTip>}
      actions={<button className="button button-sm" disabled={busy} onClick={() => void reevaluate()}><RefreshCw size={15} aria-hidden="true" />Đánh giá lại lần thu thập gần nhất</button>} />
    {latest && latest.previous_total && latest.current_total && <div role="alert" className="ws-alert-banner">
      <BellRing size={22} aria-hidden="true" className="ws-alert-icon" />
      <div className="ws-alert-text">
        <h3>{focusAlertId === latest.id ? 'Bạn mở từ email cảnh báo · ' : ''}Bình luận tiêu cực tăng vượt ngưỡng</h3>
        <p>Tỷ lệ tiêu cực tăng từ {percent(latest.previous_negative, latest.previous_total)} ({latest.previous_negative}/{latest.previous_total}) lên {percent(latest.current_negative, latest.current_total)} ({latest.current_negative}/{latest.current_total}), vượt ngưỡng tăng {latest.growth_percent}%. Phát hiện lúc {displayTime(latest.window_end)}{latest.notified_at ? ' · Đã xử lý thông báo email' : ''}.</p>
        <p className="ws-muted">Xem tab Phân tích AI để biết chủ đề và gợi ý; quyết định xử lý thuộc về nhãn hàng.</p>
      </div>
      <div className="ws-alert-jump" aria-hidden="true">
        <span>{percent(latest.previous_negative, latest.previous_total)}</span><span className="ws-alert-arrow" /><strong>{percent(latest.current_negative, latest.current_total)}</strong>
      </div>
    </div>}
    {feedback && <Notice tone="success">{feedback}</Notice>}
    {loading && <Notice>Đang tải diễn biến…</Notice>}
    {error && <Notice tone="error">Không tải được diễn biến. Trang sẽ thử lại sau ít giây.</Notice>}
    {!loading && points.length === 0 && <div className="ws-empty-chart"><p>Chưa có lần thu thập thành công.</p><p className="ws-muted">Biểu đồ hiện sau lần thu thập đầu tiên (lần mốc).</p></div>}
    {points.length > 0 && <div className="ws-live-body">
      <div className="ws-live-chart">
        <div className="ws-live-now">
          <span className="ws-live-now-label">Tỷ lệ tiêu cực hiện tại</span>
          <span className={last.alert_id ? 'ws-live-now-value ws-text-chili' : 'ws-live-now-value'}>{percent(last.negative, last.total)}</span>
          <span className="ws-muted">{last.negative} / {last.total} bình luận</span>
        </div>
        <RatioChart points={points} />
        <div className="ws-legend" aria-hidden="true">
          <span><i className="ws-swatch ws-swatch-base" />Mốc / không cảnh báo</span>
          <span><i className="ws-swatch ws-swatch-alert" />Lần có cảnh báo</span>
          <span><i className="ws-swatch ws-swatch-unknown" />Chưa phân loại</span>
        </div>
      </div>
      <div className="ws-stack ws-live-table">{points.some((point) => point.demo) && <p className="ws-muted">Các lần thu thập dưới đây dùng dữ liệu giả lập.</p>}
      <div className="table-wrap ws-flat"><table className="table"><thead><tr><th>Lần</th><th>Thời điểm</th><th className="right">Mới</th><th className="right">Tiêu cực / tổng</th><th className="right">Tỷ lệ</th><th>Kết quả</th></tr></thead>
        <tbody>{points.map((point, index) => <tr key={point.run_id} className={point.alert_id ? 'ws-row-alert' : undefined} aria-current={point.alert_id && point.alert_id === focusAlertId ? 'true' : undefined}>
          <td>{index + 1}{point.run_status === 'partial' && <small> · Thu thập một phần</small>}</td><td title={displayTime(point.finished_at)}>{shortTime(point.finished_at)}</td><td className="right num">{point.new_comments}</td>
          <td className="right num">{point.negative} / {point.total}{point.unclassified ? ` · ${point.unclassified} chưa phân loại` : ''}</td><td className="right num"><strong>{percent(point.negative, point.total)}</strong></td>
          <td>{point.alert_id ? <span className="status status-failed">Cảnh báo</span> : index === 0 ? <span className="status status-skipped">Mốc</span> : <span className="status status-success">Không cảnh báo</span>}</td></tr>)}</tbody></table></div></div>
    </div>}
  </section>;
}

function ruleMatches(saved: ApiAlertRule[], rule: ApiAlertRule) {
  return saved.some((item) => item.content_type === rule.content_type && item.enabled === rule.enabled && item.growth_percent === rule.growth_percent &&
    item.window_days === rule.window_days && item.minimum_current === rule.minimum_current && item.absolute_threshold === rule.absolute_threshold);
}

export function AlertRecipients({ api, brandId }: { api: Client; brandId: string }) {
  const [value, setValue] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState('');
  const [error, setError] = useState('');
  useEffect(() => {
    const controller = new AbortController();
    void api.getAlertRecipients(brandId, controller.signal)
      .then((result) => { if (!controller.signal.aborted) setValue(result.emails.join('\n')); })
      .catch(() => { if (!controller.signal.aborted) setError('Không tải được danh sách email. Hãy tải lại trang.'); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [api, brandId]);
  const save = async () => {
    const emails = value.split(/[\n,;]+/).map((item) => item.trim()).filter(Boolean);
    if (emails.length > 10 || emails.some((email) => !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) || new Set(emails.map((email) => email.toLowerCase())).size !== emails.length) {
      setError('Nhập tối đa 10 email hợp lệ, không trùng nhau.'); return;
    }
    setSaving(true); setError(''); setFeedback('');
    try { const result = await api.setAlertRecipients(brandId, emails); setValue(result.emails.join('\n')); setFeedback('Đã lưu danh sách người nhận.'); }
    catch { setError('Không lưu được danh sách email. Hãy kiểm tra và thử lại.'); }
    finally { setSaving(false); }
  };
  return <section className="panel ws-stack">
    <h3>Email nhận cảnh báo</h3>
    <p className="ws-muted">Nhập tối đa 10 địa chỉ, mỗi địa chỉ một dòng. Để trống để tắt gửi email cho nhãn hàng này. Email áp dụng cho cảnh báo demo theo lần thu thập; cần cấu hình dịch vụ gửi trước.</p>
    {loading ? <Notice>Đang tải danh sách…</Notice> : <form onSubmit={(event) => { event.preventDefault(); void save(); }}>
      <label className="field"><span className="field-label">Địa chỉ email</span><textarea rows={4} value={value} onChange={(event) => setValue(event.target.value)} disabled={saving || !!error && error.startsWith('Không tải')} placeholder="ten@congty.vn" /></label>
      <button className="button button-primary button-sm" disabled={saving || !!error && error.startsWith('Không tải')}>Lưu người nhận</button>
    </form>}
    {error && <Notice tone="error">{error}</Notice>}{feedback && <Notice tone="success">{feedback}</Notice>}
  </section>;
}

export function AlertSettings({ api, brandId }: { api: Client; brandId: string }) {
  const empty = (content_type: ApiAlertRule['content_type']): ApiAlertRule => ({
    content_type, enabled: false, growth_percent: 50, window_days: 7, minimum_current: 5, absolute_threshold: null,
  });
  const [rules, setRules] = useState<ApiAlertRule[]>([empty('post'), empty('comment')]);
  const [savedRules, setSavedRules] = useState<ApiAlertRule[]>([]);
  const [alerts, setAlerts] = useState<ApiAlert[]>([]);
  const [alertOffset, setAlertOffset] = useState(0);
  const [alertsLoading, setAlertsLoading] = useState(true);
  const [alertsError, setAlertsError] = useState(false);
  const [feedback, setFeedback] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError('');
    void api.listAlertRules(brandId, controller.signal).then((saved) => {
      if (!controller.signal.aborted) {
        const merged = (['post', 'comment'] as const).map((kind) => saved.find((rule) => rule.content_type === kind) ?? empty(kind));
        setRules(merged); setSavedRules(saved);
      }
    }).catch(() => { if (!controller.signal.aborted) setError('Không tải được quy tắc. Hãy thử lại.'); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [api, brandId, revision]);
  useEffect(() => {
    const controller = new AbortController();
    setAlertsLoading(true); setAlertsError(false);
    void api.listAlerts(brandId, controller.signal, { limit: 20, offset: alertOffset })
      .then((history) => { if (!controller.signal.aborted) setAlerts(history); })
      .catch(() => { if (!controller.signal.aborted) { setAlerts([]); setAlertsError(true); } })
      .finally(() => { if (!controller.signal.aborted) setAlertsLoading(false); });
    return () => controller.abort();
  }, [api, brandId, revision, alertOffset]);
  const update = (kind: ApiAlertRule['content_type'], changes: Partial<ApiAlertRule>) =>
    setRules((old) => old.map((rule) => rule.content_type === kind ? { ...rule, ...changes } : rule));
  const save = async (rule: ApiAlertRule) => {
    setSaving(true); setError(''); setFeedback('');
    try { const saved = await api.setAlertRule(brandId, rule); update(rule.content_type, saved); setSavedRules((old) => [...old.filter((item) => item.content_type !== saved.content_type), saved]); setFeedback('Đã lưu quy tắc.'); }
    catch { setError('Không lưu được quy tắc. Hãy tải lại để kiểm tra trước khi thử tiếp.'); }
    finally { setSaving(false); }
  };
  const evaluate = async (rule: ApiAlertRule) => {
    setSaving(true); setError(''); setFeedback('');
    try {
      const end = `${new Date().toISOString().slice(0, 10)}T00:00:00Z`;
      const result = await api.evaluateAlert(brandId, rule.content_type, end);
      const labels = { triggered: 'Đã có cảnh báo cho cửa sổ này.', not_triggered: 'Chưa vượt ngưỡng.',
        insufficient_data: 'Không đủ dữ liệu để so sánh.', disabled: 'Quy tắc đang tắt.' };
      setFeedback(`${labels[result.status]}${result.previous_negative !== null && result.current_negative !== null ? ` Kỳ trước: ${result.previous_negative}; kỳ này: ${result.current_negative}.` : ''}`);
      setAlertOffset(0);
      setAlerts(await api.listAlerts(brandId, undefined, { limit: 20, offset: 0 }));
    } catch { setError('Không đánh giá được quy tắc. Hãy tải lại và thử sau.'); }
    finally { setSaving(false); }
  };
  return <section className="ws-rules">
    <div className="ws-rules-main">
      <SectionHead title="Quy tắc cảnh báo"
        info={<InfoTip>Cửa sổ đánh giá kết thúc lúc 00:00 UTC. Kết quả dựa trên dữ liệu đã thu thập và cảm xúc ước tính; dữ liệu thiếu được báo là không đủ cơ sở. Kịch bản demo theo phút dùng quy tắc bình luận tiêu cực.</InfoTip>}
        actions={<button className="button button-sm" disabled={loading || saving} onClick={() => setRevision((value) => value + 1)}><RefreshCw size={15} aria-hidden="true" />Tải lại quy tắc</button>} />
      {loading && <Notice>Đang tải quy tắc…</Notice>}
      {error && <Notice tone="error">{error}</Notice>}
      {feedback && <Notice tone="success">{feedback}</Notice>}
      {!loading && !error && <div className="ws-rule-grid">{rules.map((rule) => {
        const Icon = rule.content_type === 'post' ? FileText : MessageSquareWarning;
        return <form key={rule.content_type} className={rule.enabled ? 'panel ws-rule ws-rule-on' : 'panel ws-rule'} onSubmit={(event) => { event.preventDefault(); void save(rule); }}>
          <fieldset className="ws-rule-fields" disabled={saving}>
            <div className="ws-rule-top">
              <span className="ws-rule-icon" aria-hidden="true"><Icon size={18} /></span>
              <h3>{rule.content_type === 'post' ? 'Bài viết tiêu cực' : 'Bình luận tiêu cực'}</h3>
              <label className="switch"><input type="checkbox" checked={rule.enabled} onChange={(event) => update(rule.content_type, { enabled: event.target.checked })} />Bật quy tắc</label>
            </div>
            <div className="ws-grid-2">
              <label className="field"><span className="field-label">Ngưỡng tăng (%)</span><input type="number" min="0" max="1000" required value={rule.growth_percent} onChange={(event) => update(rule.content_type, { growth_percent: event.target.valueAsNumber })} /></label>
              <label className="field"><span className="field-label">Số nội dung tối thiểu</span><input type="number" min="1" max="1000000" required value={rule.minimum_current} onChange={(event) => update(rule.content_type, { minimum_current: event.target.valueAsNumber })} /></label>
              <label className="field"><span className="field-label">Độ dài mỗi cửa sổ (ngày)</span><input type="number" min="1" max="90" required value={rule.window_days} onChange={(event) => update(rule.content_type, { window_days: event.target.valueAsNumber })} /></label>
              <label className="field"><span className="field-label">Ngưỡng tuyệt đối khi kỳ trước bằng 0 (tùy chọn)</span><input type="number" min="1" max="1000000" value={rule.absolute_threshold ?? ''} onChange={(event) => update(rule.content_type, { absolute_threshold: event.target.value === '' ? null : event.target.valueAsNumber })} /></label>
            </div>
            <div className="ws-actions">
              <button className="button button-primary button-sm">Lưu quy tắc</button>
              <button type="button" className="button button-sm" disabled={!ruleMatches(savedRules, rule)} title="Cần lưu quy tắc trước khi đánh giá" onClick={() => void evaluate(rule)}>Đánh giá cửa sổ đã hoàn tất</button>
            </div>
          </fieldset>
        </form>;
      })}</div>}
    </div>
    <div className="panel ws-history"><h3>Lịch sử cảnh báo</h3>
      {alertsLoading && <Notice>Đang tải cảnh báo…</Notice>}
      {alertsError && <Notice tone="error">Không tải được lịch sử cảnh báo. Hãy tải lại.</Notice>}
      {!alertsLoading && !alertsError && <>
        {alerts.length === 0 && <p className="ws-muted">Không có cảnh báo trên trang này.</p>}
        <ul className="ws-history-list">{alerts.map((alert) => <li key={alert.id}>
          <span className="ws-history-dot" aria-hidden="true" />
          <div>
            <p className="ws-history-main">{alert.content_type === 'post' ? 'Bài viết' : 'Bình luận'} · {alert.mode === 'run' && alert.previous_total && alert.current_total
              ? `Tỷ lệ tiêu cực ${percent(alert.previous_negative, alert.previous_total)} → ${percent(alert.current_negative, alert.current_total)}`
              : `Kỳ trước: ${alert.previous_negative}, kỳ này: ${alert.current_negative}`}</p>
            <p className="ws-muted">{alert.mode === 'run' ? `Theo lần thu thập ${displayTime(alert.window_end)}` : `${displayTime(alert.window_start)} – ${displayTime(alert.window_end)}`} · Ngưỡng tăng: {alert.growth_percent}% · Tối thiểu: {alert.minimum_current}{alert.reason === 'absolute_threshold' ? ` · Ngưỡng tuyệt đối: ${alert.absolute_threshold}` : ''}{alert.notified_at ? ' · Đã xử lý thông báo email' : ''}</p>
          </div>
        </li>)}</ul>
        <Pager prevLabel="Cảnh báo trước" nextLabel="Cảnh báo tiếp" prevDisabled={saving || alertOffset === 0} nextDisabled={saving || alerts.length < 20}
          onPrev={() => setAlertOffset((value) => Math.max(0, value - 20))} onNext={() => setAlertOffset((value) => value + 20)} />
      </>}
    </div>
  </section>;
}
