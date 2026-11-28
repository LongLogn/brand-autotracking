import { useCallback, useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react';
import { Bell, Clock, FileText, History, LayoutDashboard, LogOut, Play, Plus, RefreshCw, Settings, Sparkles, Trash2 } from 'lucide-react';
import { ApiError, createApiClient, type ApiBrand, type ApiTrackingConfig, type CommentFilters } from './lib/api';
import { createBrandWithTracking, retryBrandTracking } from './lib/brand-workflow';
import { loadRunComments, loadRunPage } from './lib/tracking-view';
import { createCognitoTokenProvider, finishCognitoLogin, logoutCognito, startCognitoLogin, type CognitoConfig } from './lib/cognito';
import { AttemptStatusTag, RunStatusTag } from './components/ui';
import { InfoTip } from './components/viz';
import { AlertRecipients, AlertSettings, RunAlertTimeline } from './workspace/AlertsTab';
import { AnalysisSettings } from './workspace/AnalysisTab';
import { AggregateContent, CommentList, PostCard } from './workspace/ContentTab';
import { BrandSummary, FREQUENCY } from './workspace/OverviewTab';
import './workspace/workspace.css';
import { Landing, LogoMark } from './workspace/Landing';
import { Notice, Pager, SectionHead, avatarTone, displayTime, initials, type Client } from './workspace/shared';

type Page = Awaited<ReturnType<typeof loadRunPage>>;
type Comments = Awaited<ReturnType<typeof loadRunComments>>;
type TabId = 'overview' | 'alerts' | 'analysis' | 'content' | 'runs' | 'settings';
const TABS: Array<{ id: TabId; label: string; icon: typeof Bell }> = [
  { id: 'overview', label: 'Tổng quan', icon: LayoutDashboard },
  { id: 'alerts', label: 'Cảnh báo', icon: Bell },
  { id: 'analysis', label: 'Phân tích AI', icon: Sparkles },
  { id: 'content', label: 'Nội dung', icon: FileText },
  { id: 'runs', label: 'Phiên tracking', icon: History },
  { id: 'settings', label: 'Cấu hình', icon: Settings },
];
const initialConfig: ApiTrackingConfig = { keywords: [], platforms: ['tiktok'], frequency: 'daily',
  runTime: '08:00', timezone: 'Asia/Ho_Chi_Minh', postLimit: 1, active: true };
const cognitoConfig: CognitoConfig | null = import.meta.env.VITE_COGNITO_DOMAIN && import.meta.env.VITE_COGNITO_CLIENT_ID
  ? { domain: import.meta.env.VITE_COGNITO_DOMAIN, clientId: import.meta.env.VITE_COGNITO_CLIENT_ID,
      redirectUri: `${window.location.origin}/auth/callback`, scope: 'openid email brand-api/access' } : null;
/** Thông báo chung của trang: lỗi hiện màu đỏ, vẫn giữ role="status" như trước. */
const failurePattern = /thất bại|Không |Chưa xác định|Thiếu|chưa lưu được/;

/** Mã lỗi phiên thường gặp → câu tiếng Việt; mã khác giữ nguyên để tra log. */
function runErrorText(code: string) {
  if (code === 'collector_disabled') return 'Môi trường này chưa bật thu thập thật (chỉ chạy dữ liệu demo), nên phiên không thể chạy.';
  if (code === 'demo_brand_manual_run') return 'Nhãn hàng này đang chạy dữ liệu mô phỏng nên không thu thập thật; dữ liệu đến từ kịch bản demo.';
  if (code === 'worker_timeout') return 'Phiên chạy quá thời gian cho phép và đã dừng.';
  return `Lỗi: ${code}`;
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
    sessionStorage.removeItem(`${deepLinkKey}.login`);
    window.history.replaceState(null, '', '/');
    return link;
  }
  try {
    const saved = JSON.parse(sessionStorage.getItem(deepLinkKey) ?? 'null') as DeepLink | null;
    return saved && uuidPattern.test(saved.brand) ? saved : null;
  } catch { return null; }
}

function Wordmark() {
  return <p className="wordmark"><LogoMark size={26} /> Brand Auto-Tracking</p>;
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
  const [tab, setTab] = useState<TabId>('overview');
  const [visited, setVisited] = useState<Set<TabId>>(() => new Set(['overview']));
  const [copied, setCopied] = useState(false);
  const callbackStarted = useRef(false);
  const createKey = useRef<string | null>(null);
  const [deepLink, setDeepLink] = useState<DeepLink | null>(captureDeepLink);
  const [focusAlertId, setFocusAlertId] = useState<string | null>(null);
  const autoLoginStarted = useRef(false);
  const limit = 20;

  const openTab = (id: TabId) => { setTab(id); setVisited((old) => (old.has(id) ? old : new Set(old).add(id))); };
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
  // Callback đã đổi URL về "/" nên phải kiểm tra cờ callback; cờ trong sessionStorage chặn vòng lặp giữa các lần tải trang.
  useEffect(() => {
    if (!deepLink || client || !cognitoConfig || autoLoginStarted.current || callbackStarted.current ||
        window.location.pathname === '/auth/callback' || sessionStorage.getItem(`${deepLinkKey}.login`) === deepLink.brand) return;
    autoLoginStarted.current = true;
    sessionStorage.setItem(`${deepLinkKey}.login`, deepLink.brand);
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
  const openBrand = (brand: ApiBrand, startTab: TabId = 'overview') => void execute(async () => {
    if (!client) return;
    setSelected(brand); setName(brand.name); setConfig(initialConfig); setNextRunAt(null); setConfigReady(false); setKeywords(''); setPage(null); setComments({}); setRuns([]); setPendingBrand(null);
    setTab(startTab); setVisited(new Set([startTab])); setCopied(false);
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
    sessionStorage.removeItem(`${deepLinkKey}.login`);
    setDeepLink(null);
    const brand = brands.find((item) => item.id === deepLink.brand);
    if (!brand) { setMessage('Không tìm thấy nhãn hàng trong liên kết trên trang đầu danh sách.'); return; }
    setFocusAlertId(deepLink.alert);
    openBrand(brand, 'alerts');
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
      const savedConfig = currentConfig();
      setPendingBrand(null); setName(''); setKeywords(''); setConfig(initialConfig); await listBrands(client);
      setMessage(savedConfig.active
        ? 'Đã lưu nhãn hàng và cấu hình. Lịch hoạt động khi dịch vụ lịch được bật.'
        : 'Đã lưu nhãn hàng ở trạng thái tạm dừng.');
    });
  };
  const saveSelected = (event: FormEvent) => {
    event.preventDefault();
    void execute(async () => {
      if (!client || !selected) return;
      const renamed = await client.renameBrand(selected.id, name); setSelected(renamed); await listBrands(client, brandOffset);
      try { await client.setTracking(selected.id, currentConfig()); } catch { setMessage('Đã đổi tên nhưng chưa lưu được cấu hình; hãy thử lưu lại.'); return; }
      setNextRunAt(null);
      try { setNextRunAt((await client.getTracking(selected.id)).nextRunAt ?? null); } catch { /* Cấu hình đã lưu; có thể tải lại lịch dự kiến sau. */ }
      const savedConfig = currentConfig();
      setConfig(savedConfig); setKeywords(savedConfig.keywords.join('\n'));
      setMessage(savedConfig.active ? 'Đã lưu. Lịch hoạt động khi dịch vụ lịch được bật.' : 'Đã lưu. Đã tạm dừng lịch thu thập của nhãn hàng này.');
    });
  };
  const startNew = () => { setSelected(null); setName(''); setKeywords(''); setConfig(initialConfig); setConfigReady(true); setNextRunAt(null); setPage(null); setRuns([]); setComments({}); setMessage(''); };
  const removeSelected = () => {
    if (!client || !selected) return;
    if (!window.confirm(`Xóa vĩnh viễn “${selected.name}” và toàn bộ dữ liệu liên quan? Không thể hoàn tác.`)) return;
    void execute(async () => {
      try { await client.deleteBrand(selected.id); }
      catch (error) { if (error instanceof ApiError && error.status === 409) { setMessage('Không thể xóa khi phiên tracking hoặc tác vụ phân tích đang hoạt động. Hãy thử lại sau.'); return; } throw error; }
      setSelected(null); setName(''); setKeywords(''); setConfig(initialConfig); setConfigReady(true); setNextRunAt(null); setPage(null); setRuns([]); setComments({});
      try { await listBrands(client, brandOffset); } catch { setMessage('Đã xóa nhãn hàng, nhưng chưa tải lại được danh sách.'); return; }
      setMessage('Đã xóa nhãn hàng và dữ liệu liên quan.');
    });
  };
  const disconnect = () => {
    setClient(null); setSelected(null); setBrands([]); setRuns([]); setPage(null); setComments({}); setPendingBrand(null); setUncertainCreate(false);
    createKey.current = null; setToken(''); setName(''); setKeywords(''); setConfig(initialConfig); setConfigReady(true); setMessage('');
    if (cognitoSignedIn && cognitoConfig) { setCognitoSignedIn(false); logoutCognito(cognitoConfig); }
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

  if (!client) return <Landing canLogin={!!cognitoConfig} busy={busy} message={message} token={token} onToken={setToken} onConnect={connect}
    onLogin={() => { if (cognitoConfig) void startCognitoLogin(cognitoConfig).catch(() => setMessage('Không thể bắt đầu đăng nhập.')); }}
    onSignup={() => { if (cognitoConfig) void startCognitoLogin(cognitoConfig, 'signup').catch(() => setMessage('Không thể bắt đầu đăng ký.')); }} />;

  const configForm = <form className="ws-config" onSubmit={selected ? saveSelected : saveNew}>
    <fieldset disabled={busy || !configReady} className="ws-config-fields">
      <label className="field"><span className="field-label">Tên</span><input required maxLength={200} value={name} onChange={(e) => setName(e.target.value)} disabled={!!pendingBrand} placeholder="Ví dụ: KFCC" /></label>
      <label className="field"><span className="field-label">Từ khóa (mỗi dòng một từ)</span><textarea required value={keywords} onChange={(e) => setKeywords(e.target.value)} placeholder={'KFCC\ngà rán KFCC'} /></label>
      <div className="ws-grid-3">
        <label className="field"><span className="field-label">Số bài mỗi lượt</span><input type="number" min="1" max="50" required value={config.postLimit} onChange={(e) => setConfig({ ...config, postLimit: Number(e.target.value) })} /></label>
        <label className="field"><span className="field-label">Tần suất</span><select value={config.frequency} onChange={(e) => setConfig({ ...config, frequency: e.target.value as ApiTrackingConfig['frequency'] })}><option value="daily">Hằng ngày</option><option value="twice-daily">Hai lần mỗi ngày</option><option value="weekly">Hằng tuần</option></select></label>
        <label className="field"><span className="field-label">Giờ chạy</span><input type="time" required value={config.runTime} onChange={(e) => setConfig({ ...config, runTime: e.target.value })} /></label>
      </div>
      <div className="ws-config-row">
        <label className="switch"><input type="checkbox" checked={config.active} onChange={(e) => setConfig({ ...config, active: e.target.checked })} />Đang bật</label>
        <span className="ws-muted">Nền tảng: {config.platforms.join(', ')} · Múi giờ {config.timezone}
          <InfoTip>Lịch tuần chạy vào cùng thứ với ngày bật hoặc đổi lịch; lịch hai lần mỗi ngày cách nhau 12 giờ theo giờ địa phương. Worker thử mặc định giới hạn 2 lời gọi mỗi phiên: một lần tìm và một lần lấy bình luận. Nhiều từ khóa hoặc bài cần tăng giới hạn worker và chi phí có thể tăng. Lịch chỉ hoạt động khi dịch vụ lịch được bật.</InfoTip></span>
      </div>
      {selected && nextRunAt && <p className="ws-muted"><Clock size={14} aria-hidden="true" /> Lịch dự kiến tại lần tải cấu hình: {new Date(nextRunAt).toLocaleString('vi-VN', { timeZone: config.timezone })}. Cần bật dịch vụ lịch để phiên thực sự chạy.</p>}
      <div className="ws-actions">
        <button className="button button-primary" disabled={busy || !configReady || (!selected && uncertainCreate)}>{pendingBrand ? 'Thử lại lưu cấu hình' : selected ? 'Lưu thay đổi' : 'Tạo nhãn hàng'}</button>
      </div>
    </fieldset>
    {uncertainCreate && !selected && <Notice tone="error" action={<button type="button" className="button button-sm" disabled={busy} onClick={() => setUncertainCreate(false)}>Tôi đã kiểm tra danh sách</button>}>Yêu cầu tạo trước có thể đã thành công. Kiểm tra danh sách trước khi tiếp tục.</Notice>}
  </form>;

  const runsTab = selected && <section className="ws-split ws-split-aside">
    <div className="panel ws-aside-panel">
      <SectionHead level={2} title="Phiên tracking" actions={<button className="icon-button" disabled={busy} aria-label="Tải lại phiên" title="Tải lại phiên" onClick={() => void execute(() => listRuns(client, selected.id, runOffset))}><RefreshCw size={16} aria-hidden="true" /></button>} />
      <button className="button button-primary button-wide" disabled={busy} onClick={() => void execute(async () => { await client.queueRun(selected.id); await listRuns(client, selected.id); setMessage('Đã gửi yêu cầu thu thập; kết quả hiện sau vài phút, danh sách phiên tự cập nhật.'); })}><Play size={15} aria-hidden="true" />Thu thập ngay</button>
      {runs.length === 0 && <p className="ws-muted">Chưa có phiên tracking.</p>}
      <ul className="ws-run-list">{runs.map((run) => <li key={run.id}><button className={page?.run.id === run.id ? 'ws-run ws-run-active' : 'ws-run'} disabled={busy} onClick={() => showRun(run.id)}>
        <RunStatusTag value={run.status} /><span className="ws-run-time">Xếp hàng {displayTime(run.queued_at)}</span></button>
        {run.status === 'queued' && <button className="button button-sm" disabled={busy} onClick={() => void execute(async () => {
          try {
            await client.cancelRun(selected.id, run.id);
            await listRuns(client, selected.id, runOffset);
            if (page?.run.id === run.id) { setPage(null); setComments({}); }
            setMessage('Đã hủy phiên đang chờ.');
          } catch (error) {
            if (error instanceof ApiError && error.status === 409) {
              await listRuns(client, selected.id, runOffset);
              setPage(null); setComments({});
              setMessage('Phiên không còn đang chờ nên không thể hủy. Đã tải lại trạng thái.');
            } else throw error;
          }
        })}>Hủy phiên</button>}</li>)}</ul>
      <Pager prevDisabled={busy || runOffset === 0} nextDisabled={busy || runs.length < limit}
        onPrev={() => void execute(() => listRuns(client, selected.id, Math.max(0, runOffset - limit)))} onNext={() => void execute(() => listRuns(client, selected.id, runOffset + limit))} />
    </div>
    <div className="ws-stack">
      {!page && <div className="panel ws-empty"><History size={22} aria-hidden="true" /><p>Chọn một phiên để xem chi tiết.</p><p className="ws-muted">Mỗi phiên gồm các lượt tìm theo nền tảng và từ khóa, cùng bài viết thu được.</p></div>}
      {page && <>
        <div className="panel ws-run-detail">
          <div className="ws-row-head"><h3>Chi tiết phiên</h3><RunStatusTag value={page.run.status} /></div>
          <p className="ws-muted">Xếp hàng: {displayTime(page.run.queuedAt)} · Bắt đầu: {page.run.startedAt ? displayTime(page.run.startedAt) : 'Chưa bắt đầu'} · Kết thúc: {page.run.finishedAt ? displayTime(page.run.finishedAt) : 'Chưa có'}</p>
          {page.run.errorCode && <Notice tone="error">{runErrorText(page.run.errorCode)}</Notice>}
          <ul className="ws-attempts">{page.attempts.map((a) => <li key={a.id}><AttemptStatusTag value={a.status} /><span className="ws-attempt-name">{a.source} / {a.keyword}</span>
            <span className="num">{a.resultCount ?? <span className="na">Không có số liệu</span>} kết quả</span>{a.errorCode && <span className="ws-text-chili">{a.errorCode}</span>}</li>)}</ul>
          {page.collectionLimits && <p className="ws-muted">Giới hạn thu thập: {page.collectionLimits.search_pages} trang tìm kiếm, {page.collectionLimits.comment_pages} trang bình luận.</p>}
        </div>
        <form className="panel ws-inline-filter" onSubmit={(event) => {
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
          <h4>Lọc bình luận của phiên<InfoTip>Thời gian theo múi giờ thiết bị; bình luận thiếu thời gian đăng không hiện khi lọc. Mở lại bình luận sau khi áp dụng. Cảm xúc là ước tính theo nội dung hiện tại, không phải bản chụp tại phiên.</InfoTip></h4>
          <div className="ws-inline-fields"><label className="field"><span className="field-label">Bình luận từ</span><input type="datetime-local" value={runCommentFrom} onChange={(event) => setRunCommentFrom(event.target.value)} /></label>
          <label className="field"><span className="field-label">Bình luận trước</span><input type="datetime-local" value={runCommentUntil} onChange={(event) => setRunCommentUntil(event.target.value)} /></label>
          <button className="button" disabled={busy}>Áp dụng lọc bình luận</button></div>
          {runCommentFilterError && <Notice tone="error">{runCommentFilterError}</Notice>}
        </form>
        <h3>Bài viết</h3>
        {page.posts.length === 0 && <p className="ws-muted">Không có bài trên trang này.</p>}
        <div className="ws-post-grid">{page.posts.map((post) => <PostCard key={post.id}
          post={{ ...post, comments: post.commentCount }}
          commentButton={<button className="button button-sm" disabled={busy} onClick={() => showComments(post.id)}>Xem bình luận</button>}>
          {comments[post.id] && <div className="ws-comment-box"><CommentList comments={comments[post.id]} postUrl={post.url} />
            <Pager prevDisabled={busy || !(commentOffsets[post.id] > 0)} nextDisabled={busy || comments[post.id].length < limit}
              onPrev={() => showComments(post.id, Math.max(0, commentOffsets[post.id] - limit))} onNext={() => showComments(post.id, (commentOffsets[post.id] ?? 0) + limit)} /></div>}
        </PostCard>)}</div>
        <Pager prevDisabled={busy || postOffset === 0} nextDisabled={busy || page.posts.length < limit}
          onPrev={() => showRun(page.run.id, Math.max(0, postOffset - limit))} onNext={() => showRun(page.run.id, postOffset + limit)} />
      </>}
    </div>
  </section>;

  const tone = avatarTone(selected?.id ?? '');
  const panel = (id: TabId, content: ReactNode) => visited.has(id) &&
    <div role="tabpanel" id={`panel-${id}`} aria-labelledby={`tab-${id}`} hidden={tab !== id} className="ws-tabpanel">{content}</div>;

  return <div className="shell ws-shell">
    <aside className="rail">
      <Wordmark />
      <nav aria-label="Nhãn hàng" className="rail-nav">
        <div className="ws-rail-head"><p className="rail-heading">Nhãn hàng</p>
          <button type="button" className="icon-button ws-rail-icon" disabled={busy} aria-label="Tải lại" title="Tải lại danh sách" onClick={() => void execute(() => listBrands(client, brandOffset))}><RefreshCw size={15} aria-hidden="true" /></button></div>
        {brands.length === 0 && <p className="ws-rail-empty">Không có nhãn hàng trên trang này.</p>}
        <ul className="rail-list">{brands.map((b) => <li key={b.id}>
          <button type="button" className={selected?.id === b.id ? 'rail-link ws-rail-button active' : 'rail-link ws-rail-button'} aria-current={selected?.id === b.id ? 'page' : undefined}
            disabled={busy || !!pendingBrand} onClick={() => openBrand(b)}>
            <span className={`avatar avatar-${avatarTone(b.id)}`} aria-hidden="true">{initials(b.name)}</span>
            <span className="rail-name">{b.name}</span>
          </button></li>)}</ul>
        {(brandOffset > 0 || brands.length >= limit) && <div className="ws-rail-pager">
          <button type="button" disabled={busy || brandOffset === 0} onClick={() => void execute(() => listBrands(client, Math.max(0, brandOffset - limit)))}>Trang trước</button>
          <button type="button" disabled={busy || brands.length < limit} onClick={() => void execute(() => listBrands(client, brandOffset + limit))}>Trang sau</button></div>}
        <button type="button" className={selected ? 'rail-add ws-rail-button' : 'rail-add ws-rail-button active'} disabled={busy || !!pendingBrand} onClick={startNew}><Plus size={16} aria-hidden="true" />Thêm nhãn hàng</button>
      </nav>
      <div className="rail-user ws-rail-user">
        <span className="rail-user-text"><span className="rail-user-name">Đã đăng nhập</span><span className="rail-user-mail">{cognitoSignedIn ? 'Qua Cognito' : 'Bằng access token'}</span></span>
        <button type="button" className="button button-sm ws-logout" disabled={busy} onClick={disconnect}><LogOut size={15} aria-hidden="true" />Ngắt kết nối</button>
      </div>
    </aside>

    <main id="main" className="main ws-main">
      <h1 className="visually-hidden">Quản lý nhãn hàng</h1>
      {(busy || message) && <div className="ws-toast">
        {busy && <Notice>Đang tải dữ liệu…</Notice>}
        {message && <div className={`ws-notice ${failurePattern.test(message) ? 'ws-notice-error' : 'ws-notice-success'}`}><p role="status">{message}</p>
          <button type="button" className="icon-button" aria-label="Đóng thông báo" onClick={() => setMessage('')}>×</button></div>}
      </div>}

      {!selected && <div className="ws-create">
        <div className="panel ws-create-form">
          <SectionHead title="Tạo nhãn hàng" />
          <p className="ws-muted">Đặt tên và từ khóa; hệ thống thu thập bài viết, bình luận theo lịch bạn chọn.</p>
          {configForm}
        </div>
        <ol className="ws-steps">
          <li><strong>Tạo nhãn hàng</strong><span>Tên và từ khóa khách hàng hay dùng.</span></li>
          <li><strong>Bật quy tắc cảnh báo</strong><span>Đặt ngưỡng tăng của bình luận tiêu cực.</span></li>
          <li><strong>Theo dõi và phân tích</strong><span>Xem tỷ lệ tiêu cực sau mỗi lần thu thập, rồi để AI tóm tắt chủ đề.</span></li>
        </ol>
      </div>}

      {selected && <>
        <header className="ws-brand-head">
          {/* Công cụ vận hành demo ẩn: nháy đúp ô chữ cái để chép mã nhãn hàng, không hiện mã trên màn hình. */}
          <span className={`avatar avatar-lg avatar-${tone}`} aria-hidden="true"
            onDoubleClick={import.meta.env.VITE_DEMO_TOOLS === 'true'
              ? () => { void navigator.clipboard?.writeText(selected.id).then(() => { setCopied(true); window.setTimeout(() => setCopied(false), 2000); }); }
              : undefined}>{initials(selected.name)}</span>
          <div className="ws-brand-text">
            <div className="brand-title-row"><h2 className="brand-title">{selected.name}</h2>
              <span className={config.active ? 'pill pill-on' : 'pill'}>{config.active ? 'Đang theo dõi' : 'Tạm dừng'}</span></div>
            <div className="brand-meta">
              <span className="meta-item"><Clock size={14} aria-hidden="true" />{config.active ? `${FREQUENCY[config.frequency]} lúc ${config.runTime}` : 'Không có lịch chạy'}</span>
              <span className="meta-item">{config.keywords.length} từ khóa</span>
              <span className="meta-item">Nguồn: {config.platforms.map((p) => (p === 'tiktok' ? 'TikTok' : p)).join(', ')}</span>
            </div>
          </div>
          {copied && <span className="ws-text-leaf">Đã chép mã</span>}
        </header>
        {!configReady && !busy && <Notice tone="error" action={<button type="button" className="button button-sm" onClick={() => openBrand(selected, tab)}>Thử tải lại cấu hình</button>}>Chưa tải được cấu hình. Thử tải lại trước khi chỉnh sửa.</Notice>}

        <div className="tabs ws-tabs" role="tablist" aria-label={`Mục của ${selected.name}`}>
          {TABS.map((item) => <button key={item.id} type="button" role="tab" id={`tab-${item.id}`} aria-controls={`panel-${item.id}`} aria-selected={tab === item.id}
            className={tab === item.id ? 'tab active' : 'tab'} onClick={() => openTab(item.id)}><item.icon size={16} aria-hidden="true" />{item.label}</button>)}
        </div>

        {panel('overview', <BrandSummary key={`summary-${selected.id}`} api={client} brandId={selected.id} config={config} nextRunAt={nextRunAt} onOpenAlerts={() => openTab('alerts')} />)}
        {panel('alerts', <div className="ws-stack">
          <RunAlertTimeline key={`timeline-${selected.id}`} api={client} brandId={selected.id} focusAlertId={focusAlertId} />
          <AlertRecipients key={`recipients-${selected.id}`} api={client} brandId={selected.id} />
          <AlertSettings key={`alerts-${selected.id}`} api={client} brandId={selected.id} />
        </div>)}
        {panel('analysis', <AnalysisSettings key={`analysis-${selected.id}`} api={client} brandId={selected.id} />)}
        {panel('content', <AggregateContent key={`content-${selected.id}`} api={client} brandId={selected.id} />)}
        {panel('runs', runsTab)}
        {panel('settings', <div className="ws-split ws-split-wide">
          <div className="panel"><SectionHead title={`Cấu hình: ${selected.name}`} />{configForm}</div>
          <div className="panel ws-danger"><h3><Trash2 size={16} aria-hidden="true" />Xóa nhãn hàng</h3>
            <p className="ws-muted">Xóa vĩnh viễn nhãn hàng và dữ liệu liên quan trong database. Bản sao lưu có thể vẫn chứa dữ liệu sau thao tác này.</p>
            <button type="button" className="button button-danger" disabled={busy} onClick={removeSelected}>Xóa vĩnh viễn</button></div>
        </div>)}
      </>}
    </main>
  </div>;
}
