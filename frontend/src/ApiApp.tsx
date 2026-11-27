import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import { ApiError, createApiClient, type ApiAlert, type ApiAlertRule, type ApiAnalysis, type ApiBrand, type ApiBrandOverview, type ApiComment, type ApiPost, type ApiTimelinePoint, type ApiTrackingConfig, type CommentFilters, type PostFilters } from './lib/api';
import { createBrandWithTracking, retryBrandTracking } from './lib/brand-workflow';
import { loadRunComments, loadRunPage } from './lib/tracking-view';
import { createCognitoTokenProvider, finishCognitoLogin, logoutCognito, startCognitoLogin, type CognitoConfig } from './lib/cognito';

type Client = ReturnType<typeof createApiClient>;
type Page = Awaited<ReturnType<typeof loadRunPage>>;
type Comments = Awaited<ReturnType<typeof loadRunComments>>;
const initialConfig: ApiTrackingConfig = { keywords: [], platforms: ['tiktok'], frequency: 'daily',
  runTime: '08:00', timezone: 'Asia/Ho_Chi_Minh', postLimit: 1, active: true };
const cognitoConfig: CognitoConfig | null = import.meta.env.VITE_COGNITO_DOMAIN && import.meta.env.VITE_COGNITO_CLIENT_ID
  ? { domain: import.meta.env.VITE_COGNITO_DOMAIN, clientId: import.meta.env.VITE_COGNITO_CLIENT_ID,
      redirectUri: `${window.location.origin}/auth/callback`, scope: 'openid email brand-api/access' } : null;
function safeLink(value: string) {
  try { const url = new URL(value); return (url.protocol === 'https:' || url.protocol === 'http:') && !url.hostname.endsWith('.invalid') ? url.href : undefined; }
  catch { return undefined; }
}
function displaySource(value: string) { return value === 'demo' ? 'Dữ liệu giả lập' : value; }
function displayTime(value: string | null) {
  if (!value) return 'Không có số liệu';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Không có số liệu' : date.toLocaleString('vi-VN');
}
function displaySentiment(value: string | undefined) {
  return ({ positive: 'Tích cực', negative: 'Tiêu cực', neutral: 'Trung lập' } as Record<string, string>)[value ?? ''] ?? 'Chưa xác định';
}
function percent(negative: number, total: number) {
  return total > 0 ? `${Math.round((negative * 100) / total)}%` : '—';
}

const deepLinkKey = 'brand-autotracking.deeplink';
const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
interface DeepLink { brand: string; alert: string | null }
/** Liên kết trong email cảnh báo: /?brand=<id>&alert=<id>; giữ qua bước đăng nhập Cognito. */
function captureDeepLink(): DeepLink | null {
  const params = new URLSearchParams(window.location.search);
  const brand = params.get('brand');
  if (window.location.pathname === '/' && brand && uuidPattern.test(brand)) {
    const alert = params.get('alert');
    const link = { brand, alert: alert && uuidPattern.test(alert) ? alert : null };
    sessionStorage.setItem(deepLinkKey, JSON.stringify(link));
    window.history.replaceState(null, '', '/');
    return link;
  }
  try {
    const saved = JSON.parse(sessionStorage.getItem(deepLinkKey) ?? 'null') as DeepLink | null;
    return saved && uuidPattern.test(saved.brand) ? saved : null;
  } catch { return null; }
}

/** Diễn biến tỷ lệ bình luận tiêu cực lũy kế sau từng lần thu thập; tự cập nhật. */
function RunAlertTimeline({ api, brandId, focusAlertId }: { api: Client; brandId: string; focusAlertId: string | null }) {
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
  return <section className="stack" ref={section} id="live-alerts"><h2>Cảnh báo theo lần thu thập</h2>
    {latest && latest.previous_total && latest.current_total && <div role="alert" className="panel">
      <h3>{focusAlertId === latest.id ? 'Bạn mở từ email cảnh báo · ' : ''}Bình luận tiêu cực tăng vượt ngưỡng</h3>
      <p>Tỷ lệ tiêu cực tăng từ {percent(latest.previous_negative, latest.previous_total)} ({latest.previous_negative}/{latest.previous_total}) lên {percent(latest.current_negative, latest.current_total)} ({latest.current_negative}/{latest.current_total}), vượt ngưỡng tăng {latest.growth_percent}%. Phát hiện lúc {displayTime(latest.window_end)}{latest.notified_at ? ' · Đã gửi email' : ''}.</p>
      <p>Có thể dùng phần Phân tích AI bên dưới để xem chủ đề và đề xuất; quyết định xử lý thuộc về nhãn hàng.</p>
    </div>}
    <p>Tỷ lệ = bình luận tiêu cực / tổng bình luận đã thu thập, cộng dồn đến từng lần. Cảnh báo khi tỷ lệ tăng vượt "Ngưỡng tăng (%)" của quy tắc bình luận so với lần trước. Dữ liệu và nhãn của kịch bản demo là giả lập.</p>
    <button className="button" disabled={busy} onClick={() => void reevaluate()}>Đánh giá lại lần thu thập gần nhất</button>
    {feedback && <p role="status">{feedback}</p>}
    {loading && <p role="status">Đang tải diễn biến…</p>}
    {error && <p role="alert">Không tải được diễn biến. Trang sẽ thử lại sau ít giây.</p>}
    {!loading && points.length === 0 && <p>Chưa có lần thu thập thành công.</p>}
    {points.length > 0 && <table><thead><tr><th>Lần</th><th>Thời điểm</th><th>Bình luận mới</th><th>Tiêu cực / tổng</th><th>Tỷ lệ tiêu cực</th><th>Kết quả</th></tr></thead>
      <tbody>{points.map((point, index) => <tr key={point.run_id} aria-current={point.alert_id && point.alert_id === focusAlertId ? 'true' : undefined}>
        <td>{index + 1}{point.demo ? ' (giả lập)' : ''}</td><td>{displayTime(point.finished_at)}</td><td>{point.new_comments}</td>
        <td>{point.negative} / {point.total}{point.unclassified ? ` · ${point.unclassified} chưa phân loại` : ''}</td><td>{percent(point.negative, point.total)}</td>
        <td>{point.alert_id ? <strong>Cảnh báo</strong> : index === 0 ? 'Mốc' : 'Không cảnh báo'}</td></tr>)}</tbody></table>}
  </section>;
}

function AnalysisSettings({ api, brandId }: { api: Client; brandId: string }) {
  const [start, setStart] = useState('');
  const [end, setEnd] = useState('');
  const [jobs, setJobs] = useState<ApiAnalysis[]>([]);
  const [offset, setOffset] = useState(0);
  const [revision, setRevision] = useState(0);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [pending, setPending] = useState<{ key: string; start: string; end: string } | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    void api.listAnalyses(brandId, controller.signal, { limit: 20, offset })
      .then((items) => { if (!controller.signal.aborted) { setJobs(items); setPending((old) => old && items.some((job) => job.request_key === old.key && job.status !== 'running') ? null : old); } })
      .catch(() => { if (!controller.signal.aborted) setError('Không tải được lịch sử phân tích.'); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [api, brandId, offset, revision]);
  const submit = (event: FormEvent) => {
    event.preventDefault();
    const from = new Date(start); const until = new Date(end);
    if (!pending && (!start || !end || !Number.isFinite(from.getTime()) || !Number.isFinite(until.getTime()) ||
        from >= until || until.getTime() > Date.now() || until.getTime() - from.getTime() > 90 * 86400000)) {
      setError('Chọn khoảng thời gian đã qua, tối đa 90 ngày và có thời điểm kết thúc sau thời điểm bắt đầu.'); return;
    }
    const request = pending ?? { key: crypto.randomUUID(), start: from.toISOString(), end: until.toISOString() };
    setPending(request); setBusy(true); setError('');
    void api.createAnalysis(brandId, request.start, request.end, request.key)
      .then((job) => {
        if (job.status !== 'running') setPending(null);
        setOffset(0); setRevision((value) => value + 1);
      })
      .catch((failure) => {
        if (failure instanceof ApiError && (failure.status === 422 || failure.status === 409)) setPending(null);
        setError('Không xác định được kết quả yêu cầu. Tải lại lịch sử hoặc thử lại cùng yêu cầu; phân tích cần được cấu hình trên máy chủ.');
      }).finally(() => setBusy(false));
  };
  return <section className="stack"><h2>Phân tích AI</h2>
    <p>Chọn khoảng thời gian thu thập đầu tiên theo múi giờ thiết bị. Chỉ dùng nội dung có bằng chứng phiên bản hiện tại được quan sát trong khoảng, tối đa 30 nội dung mới nhất; kết quả chỉ để tham khảo và có thể sai, không đại diện toàn thị trường.</p>
    <form className="form" onSubmit={submit}>
      <label className="field">Thu thập từ<input type="datetime-local" required disabled={busy || !!pending} value={start} onChange={(event) => setStart(event.target.value)} /></label>
      <label className="field">Thu thập trước<input type="datetime-local" required disabled={busy || !!pending} value={end} onChange={(event) => setEnd(event.target.value)} /></label>
      <button className="button" disabled={busy}>{pending ? 'Kiểm tra lại yêu cầu' : 'Tạo phân tích'}</button>
      {pending && <p>Yêu cầu có thể đang xử lý. Lịch sử bên dưới giúp kiểm tra trạng thái; thử lại dùng cùng khóa yêu cầu.</p>}
      {pending && !busy && <button type="button" className="button" onClick={() => setPending(null)}>Tôi đã kiểm tra lịch sử, tạo yêu cầu mới</button>}
    </form>
    <button className="button" disabled={loading || busy} onClick={() => { setError(''); setRevision((value) => value + 1); }}>Tải lại phân tích</button>
    {loading && <p role="status">Đang tải phân tích…</p>}{busy && <p role="status">Đang yêu cầu phân tích…</p>}{error && <p role="alert">{error}</p>}
    {!loading && jobs.length === 0 && <p>Chưa có phân tích trên trang này.</p>}
    {jobs.map((job) => <article className="panel" key={job.id}>
      <h3>{job.status === 'success' ? 'Phân tích hoàn tất' : job.status === 'failed' ? 'Không tạo được phân tích' : 'Đang xử lý'}</h3>
      <p>Phạm vi thu thập: {displayTime(job.window_start)} – {displayTime(job.window_end)} · Yêu cầu: {displayTime(job.created_at)}</p>
      {job.status === 'running' && <p>Yêu cầu có thể bị gián đoạn nếu trạng thái không thay đổi; kiểm tra lịch sử trước khi yêu cầu lại.</p>}
      {job.status === 'failed' && <p>{job.error_code === 'empty_data' ? 'Không có nội dung phù hợp.' : job.error_code === 'budget_exhausted' ? 'Đã hết hạn mức lượt gọi.' : job.error_code === 'rate_limited' ? 'Đã hết hạn mức trong phút này, hãy thử lại sau.' : job.error_code === 'timeout' ? 'Yêu cầu quá thời gian xử lý; kết quả đến muộn không được lưu.' : 'Dịch vụ không trả kết quả có dẫn chứng hợp lệ.'}</p>}
      {job.status === 'success' && <><p>Đã dùng {job.sample_count} nội dung{job.sample_truncated ? ' · Mẫu đã giới hạn' : ''}{job.has_undated_comments ? ' · Có bình luận cũ thiếu thời điểm không được đưa vào' : ''}.</p>
        {job.findings?.map((finding, index) => <div key={index}><p>{finding.summary}</p><p>Gợi ý: {finding.recommendation}</p><p>Dẫn chứng: {finding.evidence_ids.map((id) => {
          const source = job.evidence?.find((item) => item.id === id); const link = source && safeLink(source.url);
          return <span key={id}>{' '}{link ? <a href={link} target="_blank" rel="noreferrer">{id}</a> : id}{source?.text_truncated ? ' (đoạn đã rút ngắn)' : ''}</span>;
        })}</p></div>)}</>}
    </article>)}
    <div><button className="button" disabled={loading || busy || offset === 0} onClick={() => setOffset((value) => Math.max(0, value - 20))}>Phân tích trước</button>{' '}
      <button className="button" disabled={loading || busy || jobs.length < 20} onClick={() => setOffset((value) => value + 20)}>Phân tích tiếp</button></div>
  </section>;
}

function AlertSettings({ api, brandId }: { api: Client; brandId: string }) {
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
  return <section className="stack"><h2>Quy tắc cảnh báo</h2>
    <p>Cửa sổ đánh giá kết thúc lúc 00:00 UTC. Kết quả dựa trên dữ liệu đã thu thập và cảm xúc ước tính; dữ liệu thiếu được báo là không đủ cơ sở.</p>
    <button className="button" disabled={loading || saving} onClick={() => setRevision((value) => value + 1)}>Tải lại quy tắc</button>
    {loading && <p role="status">Đang tải quy tắc…</p>}
    {error && <p role="alert">{error}</p>}
    {feedback && <p role="status">{feedback}</p>}
    {!loading && !error && rules.map((rule) => <form key={rule.content_type} className="form panel" onSubmit={(event) => { event.preventDefault(); void save(rule); }}>
      <h3>{rule.content_type === 'post' ? 'Bài viết tiêu cực' : 'Bình luận tiêu cực'}</h3>
      <fieldset className="form api-fields" disabled={saving}>
        <label><input type="checkbox" checked={rule.enabled} onChange={(event) => update(rule.content_type, { enabled: event.target.checked })} /> Bật quy tắc</label>
        <label className="field">Ngưỡng tăng (%)<input type="number" min="0" max="1000" required value={rule.growth_percent} onChange={(event) => update(rule.content_type, { growth_percent: event.target.valueAsNumber })} /></label>
        <label className="field">Độ dài mỗi cửa sổ (ngày)<input type="number" min="1" max="90" required value={rule.window_days} onChange={(event) => update(rule.content_type, { window_days: event.target.valueAsNumber })} /></label>
        <label className="field">Số nội dung tối thiểu<input type="number" min="1" max="1000000" required value={rule.minimum_current} onChange={(event) => update(rule.content_type, { minimum_current: event.target.valueAsNumber })} /></label>
        <label className="field">Ngưỡng tuyệt đối khi kỳ trước bằng 0 (tùy chọn)<input type="number" min="1" max="1000000" value={rule.absolute_threshold ?? ''} onChange={(event) => update(rule.content_type, { absolute_threshold: event.target.value === '' ? null : event.target.valueAsNumber })} /></label>
        <button className="button">Lưu quy tắc</button>
        <button type="button" className="button" disabled={!savedRules.some((saved) => saved.content_type === rule.content_type && saved.enabled === rule.enabled && saved.growth_percent === rule.growth_percent && saved.window_days === rule.window_days && saved.minimum_current === rule.minimum_current && saved.absolute_threshold === rule.absolute_threshold)} onClick={() => void evaluate(rule)}>Đánh giá cửa sổ đã hoàn tất</button>
      </fieldset>
    </form>)}
    <div><h3>Lịch sử cảnh báo</h3>
      {alertsLoading && <p role="status">Đang tải cảnh báo…</p>}
      {alertsError && <p role="alert">Không tải được lịch sử cảnh báo. Hãy tải lại.</p>}
      {!alertsLoading && !alertsError && <>
      {alerts.length === 0 && <p>Không có cảnh báo trên trang này.</p>}
      <ul>{alerts.map((alert) => <li key={alert.id}>{alert.content_type === 'post' ? 'Bài viết' : 'Bình luận'} · {alert.mode === 'run' && alert.previous_total && alert.current_total
        ? `Theo lần thu thập ${displayTime(alert.window_end)} · Tỷ lệ tiêu cực ${percent(alert.previous_negative, alert.previous_total)} → ${percent(alert.current_negative, alert.current_total)}`
        : `${displayTime(alert.window_start)} – ${displayTime(alert.window_end)} · Kỳ trước: ${alert.previous_negative}, kỳ này: ${alert.current_negative}`} · Ngưỡng tăng: {alert.growth_percent}% · Tối thiểu: {alert.minimum_current}{alert.reason === 'absolute_threshold' ? ` · Ngưỡng tuyệt đối: ${alert.absolute_threshold}` : ''}</li>)}</ul>
      <button className="button" disabled={saving || alertOffset === 0} onClick={() => setAlertOffset((value) => Math.max(0, value - 20))}>Cảnh báo trước</button>{' '}
      <button className="button" disabled={saving || alerts.length < 20} onClick={() => setAlertOffset((value) => value + 20)}>Cảnh báo tiếp</button>
      </>}
    </div>
  </section>;
}

function BrandSummary({ api, brandId }: { api: Client; brandId: string }) {
  const [overview, setOverview] = useState<ApiBrandOverview | null>(null);
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
    return () => controller.abort();
  }, [api, brandId, revision]);
  return <section className="stack"><h2>Tổng quan</h2>
    <button className="button" disabled={loading} onClick={() => setRevision((value) => value + 1)}>Tải lại tổng quan</button>
    {loading && <p role="status">Đang tải tổng quan…</p>}
    {error && <p role="alert">Không tải được tổng quan. Hãy thử tải lại.</p>}
    {!loading && overview && <><p>Đã lưu {overview.post_count} bài viết, {overview.comment_count} bình luận và {overview.run_count} phiên tracking.</p>
      <p>{overview.latest_run ? `Phiên gần nhất: ${overview.latest_run.status}, xếp hàng ${new Date(overview.latest_run.queued_at).toLocaleString('vi-VN')}.` : 'Chưa có phiên tracking.'}</p>
      <p>Số liệu phản ánh các bản ghi đã thu thập; nội dung thiếu ID nguồn có thể trùng. Cảm xúc, nếu có, chỉ là ước tính.</p></>}
  </section>;
}

/** Nội dung tổng hợp lấy từ backend, chỉ hiển thị trang đã tải. */
function AggregateContent({ api, brandId }: { api: Client; brandId: string }) {
  const [posts, setPosts] = useState<ApiPost[]>([]);
  const [offset, setOffset] = useState(0);
  const [revision, setRevision] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [comments, setComments] = useState<Record<string, ApiComment[]>>({});
  const [commentOffsets, setCommentOffsets] = useState<Record<string, number>>({});
  const [commentError, setCommentError] = useState<string | null>(null);
  const [commentLoading, setCommentLoading] = useState<string | null>(null);
  const [source, setSource] = useState('');
  const [from, setFrom] = useState('');
  const [until, setUntil] = useState('');
  const [filters, setFilters] = useState<PostFilters>({});
  const [filterError, setFilterError] = useState('');
  const requestId = useRef(0);
  const limit = 20;

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError(false); setPosts([]); setComments({}); setCommentOffsets({}); setCommentError(null); setCommentLoading(null);
    void api.listPosts(brandId, controller.signal, { limit, offset }, filters)
      .then((data) => { if (!controller.signal.aborted) setPosts(data); })
      .catch(() => { if (!controller.signal.aborted) setError(true); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => { controller.abort(); requestId.current += 1; };
  }, [api, brandId, offset, revision, filters]);

  const loadComments = async (postId: string, nextOffset: number) => {
    const id = ++requestId.current;
    setCommentLoading(postId); setCommentError(null);
    try {
      const data = await api.listComments(brandId, postId, undefined, { limit, offset: nextOffset }, {
        postedFrom: filters.postedFrom,
        postedUntil: filters.postedUntil,
      });
      if (id !== requestId.current) return;
      setComments((old) => ({ ...old, [postId]: data }));
      setCommentOffsets((old) => ({ ...old, [postId]: nextOffset }));
    } catch {
      if (id === requestId.current) setCommentError(postId);
    } finally {
      if (id === requestId.current) setCommentLoading(null);
    }
  };

  return <section className="stack"><h2>Nội dung đã thu thập</h2>
    <p>Chỉ số là bản ghi gần nhất có sẵn; cảm xúc là ước tính theo nội dung hiện tại và có thể chưa được phân loại. Dữ liệu có thể chưa đầy đủ.</p>
    <form className="form" onSubmit={(event) => {
      event.preventDefault();
      const fromDate = from ? new Date(from) : null;
      const untilDate = until ? new Date(until) : null;
      if ((fromDate && Number.isNaN(fromDate.getTime())) || (untilDate && Number.isNaN(untilDate.getTime())) ||
          (fromDate && untilDate && fromDate >= untilDate)) {
        setFilterError('Thời điểm kết thúc phải sau thời điểm bắt đầu.'); return;
      }
      setFilterError(''); setOffset(0);
      setFilters({ source: source || undefined, postedFrom: fromDate?.toISOString(), postedUntil: untilDate?.toISOString() });
    }}>
      <label className="field" htmlFor="content-source">Nền tảng</label><select id="content-source" value={source} onChange={(event) => setSource(event.target.value)}><option value="">Tất cả nền tảng</option><option value="tiktok">TikTok</option><option value="demo">Dữ liệu giả lập</option></select>
      <label className="field">Đăng từ<input type="datetime-local" value={from} onChange={(event) => setFrom(event.target.value)} /></label>
      <label className="field">Đăng trước<input type="datetime-local" value={until} onChange={(event) => setUntil(event.target.value)} /></label>
      <p>Thời gian theo múi giờ thiết bị; bài và bình luận thiếu thời gian đăng không hiện khi lọc theo thời gian.</p>
      {filterError && <p role="alert">{filterError}</p>}
      <button className="button" disabled={loading}>Lọc nội dung</button>
    </form>
    <button className="button" disabled={loading} onClick={() => setRevision((value) => value + 1)}>Tải lại nội dung</button>
    {loading && <p role="status">Đang tải nội dung…</p>}
    {error && <p role="alert">Không tải được nội dung. Hãy thử tải lại.</p>}
    {!loading && !error && posts.length === 0 && <p>Chưa có bài viết trên trang này.</p>}
    {posts.map((post) => <article key={post.id} className="panel">
      <h3>{safeLink(post.url) ? <a href={safeLink(post.url)} target="_blank" rel="noreferrer">{post.title || 'Mở bài viết'}</a> : (post.title || (post.source === 'demo' ? 'Bài giả lập' : 'Đường dẫn không hợp lệ'))}</h3>
      <p>{post.content ?? 'Không có nội dung'}</p>
      <p>Nguồn: {displaySource(post.source)} · Đăng: {displayTime(post.posted_at)}</p>
      <p>Cảm xúc ước tính: {displaySentiment(post.sentiment)}</p>
      <p>Thích: {post.metrics?.likes ?? 'Không có số liệu'} · Bình luận: {post.metrics?.comment_count ?? 'Không có số liệu'} {post.maybe_duplicate && '· Có thể trùng'}</p>
      <button className="button" disabled={commentLoading !== null} onClick={() => void loadComments(post.id, 0)}>Bình luận tổng hợp</button>
      {commentLoading === post.id && <p role="status">Đang tải bình luận…</p>}
      {commentError === post.id && <p role="alert">Không tải được bình luận. Hãy thử lại.</p>}
      {comments[post.id] && <><ul>{comments[post.id].map((comment) => <li key={comment.id}>{comment.content} · Thích: {comment.metrics?.likes ?? 'Không có số liệu'} {comment.maybe_duplicate && '· Có thể trùng'} · Đăng: {displayTime(comment.posted_at)} · Cảm xúc ước tính: {displaySentiment(comment.sentiment)}</li>)}</ul>
        {comments[post.id].length === 0 && <p>Không có bình luận trên trang này.</p>}
        <button className="button" disabled={commentLoading !== null || !(commentOffsets[post.id] > 0)} onClick={() => void loadComments(post.id, Math.max(0, commentOffsets[post.id] - limit))}>Bình luận trước</button>{' '}
        <button className="button" disabled={commentLoading !== null || comments[post.id].length < limit} onClick={() => void loadComments(post.id, (commentOffsets[post.id] ?? 0) + limit)}>Bình luận tiếp</button></>}
    </article>)}
    <div><button className="button" disabled={loading || offset === 0} onClick={() => setOffset((value) => Math.max(0, value - limit))}>Bài trước</button>{' '}
      <button className="button" disabled={loading || error || posts.length < limit} onClick={() => setOffset((value) => value + limit)}>Bài tiếp</button></div>
  </section>;
}

/** Giao diện kết nối backend; token chỉ tồn tại trong bộ nhớ trang. */
export function ApiApp() {
  const [token, setToken] = useState('');
  const [client, setClient] = useState<Client | null>(null);
  const [cognitoSignedIn, setCognitoSignedIn] = useState(false);
  const [brands, setBrands] = useState<ApiBrand[]>([]);
  const [selected, setSelected] = useState<ApiBrand | null>(null);
  const [name, setName] = useState('');
  const [keywords, setKeywords] = useState('');
  const [config, setConfig] = useState<ApiTrackingConfig>(initialConfig);
  const [nextRunAt, setNextRunAt] = useState<string | null>(null);
  const [configReady, setConfigReady] = useState(true);
  const [pendingBrand, setPendingBrand] = useState<ApiBrand | null>(null);
  const [uncertainCreate, setUncertainCreate] = useState(false);
  const [runs, setRuns] = useState<Awaited<ReturnType<Client['listRuns']>>>([]);
  const [page, setPage] = useState<Page | null>(null);
  const [comments, setComments] = useState<Record<string, Comments>>({});
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const [brandOffset, setBrandOffset] = useState(0);
  const [runOffset, setRunOffset] = useState(0);
  const [postOffset, setPostOffset] = useState(0);
  const [commentOffsets, setCommentOffsets] = useState<Record<string, number>>({});
  const [runCommentFrom, setRunCommentFrom] = useState('');
  const [runCommentUntil, setRunCommentUntil] = useState('');
  const [runCommentFilters, setRunCommentFilters] = useState<CommentFilters>({});
  const [runCommentFilterError, setRunCommentFilterError] = useState('');
  const callbackStarted = useRef(false);
  const createKey = useRef<string | null>(null);
  const [deepLink, setDeepLink] = useState<DeepLink | null>(captureDeepLink);
  const [focusAlertId, setFocusAlertId] = useState<string | null>(null);
  const autoLoginStarted = useRef(false);
  const limit = 20;

  const fail = (error: unknown) => setMessage(error instanceof ApiError ? `Yêu cầu thất bại (HTTP ${error.status}).` : 'Không kết nối được hoặc yêu cầu bị gián đoạn. Hãy kiểm tra trạng thái trước khi thử lại.');
  const execute = async (task: () => Promise<void>) => {
    setBusy(true); setMessage('');
    try { await task(); } catch (error) { fail(error); } finally { setBusy(false); }
  };
  const listBrands = useCallback(async (api: Client, offset = 0) => {
    setBrands(await api.listBrands(undefined, { limit, offset })); setBrandOffset(offset);
  }, []);
  useEffect(() => {
    if (window.location.pathname !== '/auth/callback' || callbackStarted.current) return;
    callbackStarted.current = true;
    const callbackUrl = window.location.href;
    window.history.replaceState(null, '', '/');
    if (!cognitoConfig) { setMessage('Thiếu cấu hình Cognito.'); return; }
    setBusy(true);
    void (async () => {
      try {
        const tokens = await finishCognitoLogin(cognitoConfig, callbackUrl);
        const api = createApiClient(import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000', createCognitoTokenProvider(cognitoConfig, tokens));
        await listBrands(api);
        setClient(api);
        setCognitoSignedIn(true);
      } catch { setMessage('Đăng nhập hoặc kết nối API thất bại. Vui lòng thử lại.'); }
      finally { setBusy(false); }
    })();
  }, [listBrands]);
  // Mở từ email khi chưa đăng nhập: chuyển thẳng sang Cognito; phiên Cognito còn hạn sẽ quay lại ngay.
  useEffect(() => {
    if (!deepLink || client || !cognitoConfig || autoLoginStarted.current || window.location.pathname === '/auth/callback') return;
    autoLoginStarted.current = true;
    void startCognitoLogin(cognitoConfig).catch(() => setMessage('Không thể bắt đầu đăng nhập.'));
  }, [deepLink, client]);
  const listRuns = async (api: Client, brandId: string, offset = 0) => {
    setRuns(await api.listRuns(brandId, undefined, { limit, offset })); setRunOffset(offset);
  };
  // Cập nhật cả phiên theo lịch mới lẫn trạng thái phiên đang chờ/chạy.
  const hasActiveRun = runs.some((run) => run.status === 'queued' || run.status === 'running');
  useEffect(() => {
    if (!client || !selected) return;
    let cancelled = false;
    const timer = window.setInterval(() => {
      void client.listRuns(selected.id, undefined, { limit, offset: runOffset })
        .then((updated) => { if (!cancelled) setRuns(updated); })
        .catch(() => { /* Nút tải lại cho phép thử tiếp khi mạng phục hồi. */ });
    }, hasActiveRun ? 5000 : 30000);
    return () => { cancelled = true; window.clearInterval(timer); };
  }, [client, selected, hasActiveRun, runOffset]);
  const connect = (event: FormEvent) => {
    event.preventDefault();
    void execute(async () => {
      const accessToken = token.trim();
      if (!accessToken) throw new Error('missing token');
      const api = createApiClient(import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000', async () => accessToken);
      await listBrands(api); setClient(api); setToken('');
    });
  };
  const openBrand = (brand: ApiBrand) => void execute(async () => {
    if (!client) return;
    setSelected(brand); setName(brand.name); setConfig(initialConfig); setNextRunAt(null); setConfigReady(false); setKeywords(''); setPage(null); setComments({}); setRuns([]); setPendingBrand(null);
    try {
      const { nextRunAt: next, ...saved } = await client.getTracking(brand.id);
      setNextRunAt(next ?? null);
      setConfig(saved); setKeywords(saved.keywords.join('\n'));
    } catch (error) {
      if (!(error instanceof ApiError && error.status === 404)) throw error;
      setConfig(initialConfig); setKeywords(''); setMessage('Nhãn hàng chưa có cấu hình tracking.');
    }
    setConfigReady(true); await listRuns(client, brand.id);
  });
  useEffect(() => {
    if (!deepLink || !client || busy || selected) return;
    sessionStorage.removeItem(deepLinkKey);
    setDeepLink(null);
    const brand = brands.find((item) => item.id === deepLink.brand);
    if (!brand) { setMessage('Không tìm thấy nhãn hàng trong liên kết trên trang đầu danh sách.'); return; }
    setFocusAlertId(deepLink.alert);
    openBrand(brand);
  }, [deepLink, client, busy, selected, brands]);
  const currentConfig = () => ({ ...config, keywords: keywords.split('\n').map((k) => k.trim()).filter(Boolean) });
  const saveNew = (event: FormEvent) => {
    event.preventDefault();
    void execute(async () => {
      if (!client) return;
      if (!pendingBrand && !createKey.current) createKey.current = crypto.randomUUID();
      let result;
      try {
        result = pendingBrand
          ? { status: 'complete' as const, brand: pendingBrand, tracking: await retryBrandTracking(client, pendingBrand, currentConfig()) }
          : await createBrandWithTracking(client, name, currentConfig(), undefined, createKey.current ?? undefined);
      } catch (error) {
        if (!pendingBrand && (!(error instanceof ApiError) || error.status >= 500 || error.status === 408)) {
          setUncertainCreate(true);
          setMessage('Chưa xác định được nhãn hàng đã tạo hay chưa. Hãy tải lại và kiểm tra tất cả các trang danh sách trước khi tạo lại.');
          return;
        }
        createKey.current = null;
        throw error;
      }
      createKey.current = null;
      if (result.status === 'tracking-failed') {
        setPendingBrand(result.brand);
        setMessage(`Đã tạo ${result.brand.name}, nhưng lưu cấu hình thất bại. Nhấn thử lại để lưu cấu hình cho nhãn hàng này.`);
        return;
      }
      setPendingBrand(null); setName(''); await listBrands(client); setMessage('Đã lưu nhãn hàng và cấu hình. Lịch hoạt động khi dịch vụ lịch được bật.');
    });
  };
  const showRun = (id: string, offset = 0) => void execute(async () => {
    if (!client || !selected) return;
    const loaded = await loadRunPage(client, selected.id, id, { limit, offset });
    setPage(loaded); setPostOffset(offset); setComments({}); setCommentOffsets({});
  });
  const showComments = (postId: string, offset = 0) => void execute(async () => {
    if (!client || !selected || !page) return;
    const loaded = await loadRunComments(client, selected.id, page.run.id, postId, { limit, offset }, undefined, runCommentFilters);
    setComments((old) => ({ ...old, [postId]: loaded }));
    setCommentOffsets((old) => ({ ...old, [postId]: offset }));
  });

  if (!client) return <main className="api-welcome"><section className="api-welcome-intro"><p className="wordmark"><span className="wordmark-mark" aria-hidden="true" /> Brand Auto-Tracking</p><h1>Theo dõi nhãn hàng, hiểu những cuộc trò chuyện.</h1><p>Tập trung dữ liệu theo từng nhãn hàng, từ khóa và phiên thu thập để bạn nắm được điều khách hàng đang nói.</p><div className="api-coverage" aria-hidden="true"><span /><span /><span /><span /><span /><span /><span /><span /><span /><span /><span /><span /></div><p className="api-coverage-note">Dữ liệu thiếu luôn được hiển thị rõ.</p></section><section className="api-welcome-panel"><h2>Bắt đầu theo dõi</h2><p>Đăng nhập hoặc tạo tài khoản để quản lý nhãn hàng của bạn.</p>{cognitoConfig && <div className="api-login-actions"><button type="button" className="button button-primary" disabled={busy} onClick={() => { void startCognitoLogin(cognitoConfig).catch(() => setMessage('Không thể bắt đầu đăng nhập.')); }}>Đăng nhập với Cognito</button><button type="button" className="button" disabled={busy} onClick={() => { void startCognitoLogin(cognitoConfig, 'signup').catch(() => setMessage('Không thể bắt đầu đăng ký.')); }}>Tạo tài khoản</button></div>}
    {!cognitoConfig && <p role="status">Chưa cấu hình đăng nhập. Cần đặt VITE_COGNITO_DOMAIN và VITE_COGNITO_CLIENT_ID.</p>}{busy && <p role="status">Đang kết nối…</p>}
    <details className="api-developer"><summary>Kết nối bằng access token</summary><form className="form" onSubmit={connect}><label className="field">Access token<input type="password" autoComplete="off" value={token} onChange={(e) => setToken(e.target.value)} /></label>
      <button className="button" disabled={busy}>Kết nối</button></form></details>{message && <p role="alert">{message}</p>}</section></main>;

  return <main className="page stack api-workspace"><header className="page-head"><div><p className="wordmark"><span className="wordmark-mark" aria-hidden="true" /> Brand Auto-Tracking</p><h1>Quản lý nhãn hàng</h1></div><button className="button" disabled={busy} onClick={() => { setClient(null); setSelected(null); setBrands([]); setRuns([]); setPage(null); setComments({}); setPendingBrand(null); setUncertainCreate(false); createKey.current = null; setToken(''); setName(''); setKeywords(''); setConfig(initialConfig); setConfigReady(true); setMessage(''); if (cognitoSignedIn && cognitoConfig) { setCognitoSignedIn(false); logoutCognito(cognitoConfig); } }}>Ngắt kết nối</button></header>
    <p>Đây là dữ liệu từ backend. Lịch hoạt động khi dịch vụ lịch được bật.</p>{busy && <p role="status">Đang tải dữ liệu…</p>}{message && <p role="status">{message}</p>}
    <section className="stack"><h2>Nhãn hàng</h2><button className="button" disabled={busy} onClick={() => void execute(() => listBrands(client, brandOffset))}>Tải lại</button>
      {brands.length === 0 && <p>Không có nhãn hàng trên trang này.</p>}
      <ul>{brands.map((b) => <li key={b.id}><button className="button" disabled={busy || !!pendingBrand} onClick={() => openBrand(b)}>{b.name}</button></li>)}</ul>
      <div><button className="button" disabled={busy || brandOffset === 0} onClick={() => void execute(() => listBrands(client, Math.max(0, brandOffset - limit)))}>Trang trước</button> <button className="button" disabled={busy || brands.length < limit} onClick={() => void execute(() => listBrands(client, brandOffset + limit))}>Trang sau</button></div>
    </section>
    <section className="stack"><h2>{selected ? `Cấu hình: ${selected.name}` : 'Tạo nhãn hàng'}</h2>
      {selected && import.meta.env.VITE_DEMO_TOOLS === 'true' && <p>Mã nhãn hàng cho người vận hành demo: <code>{selected.id}</code></p>}
      {selected && !configReady && !busy && <div><p>Chưa tải được cấu hình. Thử tải lại trước khi chỉnh sửa.</p><button type="button" className="button" onClick={() => openBrand(selected)}>Thử tải lại cấu hình</button></div>}
      <form className="form" onSubmit={selected ? (e) => { e.preventDefault(); void execute(async () => { const renamed = await client.renameBrand(selected.id, name); setSelected(renamed); await listBrands(client, brandOffset); try { await client.setTracking(selected.id, currentConfig()); } catch { setMessage('Đã đổi tên nhưng chưa lưu được cấu hình; hãy thử lưu lại.'); return; } setNextRunAt(null); try { setNextRunAt((await client.getTracking(selected.id)).nextRunAt ?? null); } catch { /* Cấu hình đã lưu; có thể tải lại lịch dự kiến sau. */ } setMessage('Đã lưu. Lịch hoạt động khi dịch vụ lịch được bật.'); }); } : saveNew}>
        <fieldset disabled={busy || !configReady} className="form api-fields">
        <label className="field">Tên<input required maxLength={200} value={name} onChange={(e) => setName(e.target.value)} disabled={!!pendingBrand} /></label>
        <label className="field">Từ khóa (mỗi dòng một từ)<textarea required value={keywords} onChange={(e) => setKeywords(e.target.value)} /></label>
        <label className="field">Số bài mỗi lượt<input type="number" min="1" max="50" required value={config.postLimit} onChange={(e) => setConfig({ ...config, postLimit: Number(e.target.value) })} /></label>
        <label className="field">Tần suất<select value={config.frequency} onChange={(e) => setConfig({ ...config, frequency: e.target.value as ApiTrackingConfig['frequency'] })}><option value="daily">Hằng ngày</option><option value="twice-daily">Hai lần mỗi ngày</option><option value="weekly">Hằng tuần</option></select></label>
        <label className="field">Giờ chạy<input type="time" required value={config.runTime} onChange={(e) => setConfig({ ...config, runTime: e.target.value })} /></label>
        <label><input type="checkbox" checked={config.active} onChange={(e) => setConfig({ ...config, active: e.target.checked })} /> Đang bật</label>
        <p>Nền tảng: {config.platforms.join(', ')} · Múi giờ {config.timezone}. Lịch tuần chạy vào cùng thứ với ngày bật hoặc đổi lịch; lịch hai lần mỗi ngày cách nhau 12 giờ theo giờ địa phương.</p><button className="button button-primary" disabled={busy || !configReady || (!selected && uncertainCreate)}>{pendingBrand ? 'Thử lại lưu cấu hình' : selected ? 'Lưu thay đổi' : 'Tạo nhãn hàng'}</button>
        <p>Worker thử mặc định giới hạn 2 lời gọi mỗi phiên: một lần tìm và một lần lấy bình luận. Nhiều từ khóa hoặc bài cần tăng giới hạn worker và chi phí có thể tăng.</p>
        {selected && nextRunAt && <p>Lịch dự kiến tại lần tải cấu hình: {new Date(nextRunAt).toLocaleString('vi-VN', { timeZone: config.timezone })}. Cần bật dịch vụ lịch để phiên thực sự chạy.</p>}
        </fieldset>
        {uncertainCreate && !selected && <div><p>Yêu cầu tạo trước có thể đã thành công. Kiểm tra danh sách trước khi tiếp tục.</p><button type="button" className="button" disabled={busy} onClick={() => setUncertainCreate(false)}>Tôi đã kiểm tra danh sách</button></div>}
        {selected && <button type="button" className="button" onClick={() => { setSelected(null); setName(''); setKeywords(''); setConfig(initialConfig); setConfigReady(true); setPage(null); setRuns([]); }}>Tạo nhãn hàng khác</button>}
      </form></section>
    {selected && <section className="stack"><h2>Xóa nhãn hàng</h2><p>Xóa vĩnh viễn nhãn hàng và dữ liệu liên quan trong database. Bản sao lưu có thể vẫn chứa dữ liệu sau thao tác này.</p><button type="button" className="button" disabled={busy} onClick={() => {
      if (!window.confirm(`Xóa vĩnh viễn “${selected.name}” và toàn bộ dữ liệu liên quan? Không thể hoàn tác.`)) return;
      void execute(async () => {
        try { await client.deleteBrand(selected.id); }
        catch (error) { if (error instanceof ApiError && error.status === 409) { setMessage('Không thể xóa khi phiên tracking hoặc tác vụ phân tích đang hoạt động. Hãy thử lại sau.'); return; } throw error; }
        setSelected(null); setName(''); setKeywords(''); setConfig(initialConfig); setConfigReady(true); setNextRunAt(null); setPage(null); setRuns([]); setComments({});
        try { await listBrands(client, brandOffset); } catch { setMessage('Đã xóa nhãn hàng, nhưng chưa tải lại được danh sách.'); return; }
        setMessage('Đã xóa nhãn hàng và dữ liệu liên quan.');
      });
    }}>Xóa vĩnh viễn</button></section>}
    {selected && <BrandSummary key={`summary-${selected.id}`} api={client} brandId={selected.id} />}
    {selected && <RunAlertTimeline key={`timeline-${selected.id}`} api={client} brandId={selected.id} focusAlertId={focusAlertId} />}
    {selected && <AlertSettings key={`alerts-${selected.id}`} api={client} brandId={selected.id} />}
    {selected && <AnalysisSettings key={`analysis-${selected.id}`} api={client} brandId={selected.id} />}
    {selected && <AggregateContent key={`content-${selected.id}`} api={client} brandId={selected.id} />}
    {selected && <section className="stack"><h2>Phiên tracking</h2><button className="button" disabled={busy} onClick={() => void execute(async () => { await client.queueRun(selected.id); await listRuns(client, selected.id); setMessage('Đã xếp hàng; phiên sẽ chạy khi worker hoạt động.'); })}>Tạo phiên chờ</button>
      <button className="button" disabled={busy} onClick={() => void execute(() => listRuns(client, selected.id, runOffset))}>Tải lại phiên</button>
      <ul>{runs.map((run) => <li key={run.id}><button className="button" disabled={busy} onClick={() => showRun(run.id)}>{run.status} · Xếp hàng {run.queued_at}</button></li>)}</ul>
      <div><button className="button" disabled={busy || runOffset === 0} onClick={() => void execute(() => listRuns(client, selected.id, Math.max(0, runOffset - limit)))}>Trang trước</button> <button className="button" disabled={busy || runs.length < limit} onClick={() => void execute(() => listRuns(client, selected.id, runOffset + limit))}>Trang sau</button></div>
      {page && <div className="stack"><h3>Phiên {page.run.status}</h3><p>Xếp hàng: {page.run.queuedAt} · Bắt đầu: {page.run.startedAt ?? 'Chưa bắt đầu'} · Kết thúc: {page.run.finishedAt ?? 'Chưa có'}</p>
        {page.run.errorCode && <p>Lỗi: {page.run.errorCode}</p>}
        <ul>{page.attempts.map((a) => <li key={a.id}>{a.source} / {a.keyword}: {a.status} · {a.resultCount ?? 'Không có số liệu'} {a.errorCode && `· ${a.errorCode}`}</li>)}</ul>
        {page.collectionLimits && <p>Giới hạn thu thập: {page.collectionLimits.search_pages} trang tìm kiếm, {page.collectionLimits.comment_pages} trang bình luận.</p>}
        <h3>Bài viết</h3><p>Cảm xúc là ước tính theo nội dung hiện tại, không phải bản chụp tại phiên.</p>
        <form className="form" onSubmit={(event) => {
          event.preventDefault();
          const fromDate = runCommentFrom ? new Date(runCommentFrom) : null;
          const untilDate = runCommentUntil ? new Date(runCommentUntil) : null;
          if ((fromDate && Number.isNaN(fromDate.getTime())) || (untilDate && Number.isNaN(untilDate.getTime())) ||
              (fromDate && untilDate && fromDate >= untilDate)) {
            setRunCommentFilterError('Thời điểm kết thúc phải sau thời điểm bắt đầu.'); return;
          }
          setRunCommentFilterError('');
          setRunCommentFilters({ postedFrom: fromDate?.toISOString(), postedUntil: untilDate?.toISOString() });
          setComments({}); setCommentOffsets({});
        }}>
          <h4>Lọc bình luận của phiên</h4>
          <label className="field">Bình luận từ<input type="datetime-local" value={runCommentFrom} onChange={(event) => setRunCommentFrom(event.target.value)} /></label>
          <label className="field">Bình luận trước<input type="datetime-local" value={runCommentUntil} onChange={(event) => setRunCommentUntil(event.target.value)} /></label>
          <p>Thời gian theo múi giờ thiết bị; bình luận thiếu thời gian đăng không hiện khi lọc. Mở lại bình luận sau khi áp dụng.</p>
          {runCommentFilterError && <p role="alert">{runCommentFilterError}</p>}
          <button className="button" disabled={busy}>Áp dụng lọc bình luận</button>
        </form>
        {page.posts.length === 0 && <p>Không có bài trên trang này.</p>}
        {page.posts.map((post) => <article key={post.id} className="panel"><h4>{safeLink(post.url) ? <a href={safeLink(post.url)} target="_blank" rel="noreferrer">{post.title || 'Mở bài viết'}</a> : (post.title || (post.source === 'demo' ? 'Bài giả lập' : 'Đường dẫn không hợp lệ'))}</h4><p>{post.content ?? 'Không có nội dung'}</p><p>Nguồn: {displaySource(post.source)} · Đăng: {displayTime(post.postedAt)}</p><p>Cảm xúc ước tính: {displaySentiment(post.sentiment)}</p><p>Thích: {post.likes ?? 'Không có số liệu'} · Bình luận: {post.commentCount ?? 'Không có số liệu'} {post.maybeDuplicate && '· Có thể trùng'}</p>
          <button className="button" disabled={busy} onClick={() => showComments(post.id)}>Xem bình luận</button>
          {comments[post.id] && <><ul>{comments[post.id].map((c) => <li key={c.id}>{c.content} · Thích: {c.likes ?? 'Không có số liệu'} {c.maybeDuplicate && '· Có thể trùng'} · Đăng: {displayTime(c.postedAt)} · Cảm xúc ước tính: {displaySentiment(c.sentiment)}</li>)}</ul><button className="button" disabled={busy || !(commentOffsets[post.id] > 0)} onClick={() => showComments(post.id, Math.max(0, commentOffsets[post.id] - limit))}>Trang trước</button> <button className="button" disabled={busy || comments[post.id].length < limit} onClick={() => showComments(post.id, (commentOffsets[post.id] ?? 0) + limit)}>Trang sau</button></>}
        </article>)}
        <div><button className="button" disabled={busy || postOffset === 0} onClick={() => showRun(page.run.id, Math.max(0, postOffset - limit))}>Trang trước</button> <button className="button" disabled={busy || page.posts.length < limit} onClick={() => showRun(page.run.id, postOffset + limit)}>Trang sau</button></div>
      </div>}
    </section>}
  </main>;
}
