import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import { ApiError, createApiClient, type ApiBrand, type ApiBrandOverview, type ApiComment, type ApiPost, type ApiTrackingConfig, type PostFilters } from './lib/api';
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
  try { const url = new URL(value); return url.protocol === 'https:' || url.protocol === 'http:' ? url.href : undefined; }
  catch { return undefined; }
}
function displayTime(value: string | null) {
  if (!value) return 'Không có số liệu';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Không có số liệu' : date.toLocaleString('vi-VN');
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
      <p>Số liệu phản ánh các bản ghi đã thu thập; nội dung thiếu ID nguồn có thể trùng. Chưa có phân tích cảm xúc.</p></>}
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
    <p>Chỉ số là bản ghi gần nhất có sẵn; dữ liệu có thể chưa đầy đủ.</p>
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
      <label className="field" htmlFor="content-source">Nền tảng</label><select id="content-source" value={source} onChange={(event) => setSource(event.target.value)}><option value="">Tất cả nền tảng</option><option value="tiktok">TikTok</option></select>
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
      <h3>{safeLink(post.url) ? <a href={safeLink(post.url)} target="_blank" rel="noreferrer">{post.title || 'Mở bài viết'}</a> : (post.title || 'Đường dẫn không hợp lệ')}</h3>
      <p>{post.content ?? 'Không có nội dung'}</p>
      <p>Nguồn: {post.source} · Đăng: {displayTime(post.posted_at)}</p>
      <p>Thích: {post.metrics?.likes ?? 'Không có số liệu'} · Bình luận: {post.metrics?.comment_count ?? 'Không có số liệu'} {post.maybe_duplicate && '· Có thể trùng'}</p>
      <button className="button" disabled={commentLoading !== null} onClick={() => void loadComments(post.id, 0)}>Bình luận tổng hợp</button>
      {commentLoading === post.id && <p role="status">Đang tải bình luận…</p>}
      {commentError === post.id && <p role="alert">Không tải được bình luận. Hãy thử lại.</p>}
      {comments[post.id] && <><ul>{comments[post.id].map((comment) => <li key={comment.id}>{comment.content} · Thích: {comment.metrics?.likes ?? 'Không có số liệu'} {comment.maybe_duplicate && '· Có thể trùng'} · Đăng: {displayTime(comment.posted_at)}</li>)}</ul>
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
  const callbackStarted = useRef(false);
  const createKey = useRef<string | null>(null);
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
    const loaded = await loadRunComments(client, selected.id, page.run.id, postId, { limit, offset });
    setComments((old) => ({ ...old, [postId]: loaded }));
    setCommentOffsets((old) => ({ ...old, [postId]: offset }));
  });

  if (!client) return <main className="api-welcome"><section className="api-welcome-intro"><p className="wordmark"><span className="wordmark-mark" aria-hidden="true" /> Brand Auto-Tracking</p><h1>Theo dõi nhãn hàng, hiểu những cuộc trò chuyện.</h1><p>Tập trung dữ liệu theo từng nhãn hàng, từ khóa và phiên thu thập để bạn nắm được điều khách hàng đang nói.</p><div className="api-coverage" aria-hidden="true"><span /><span /><span /><span /><span /><span /><span /><span /><span /><span /><span /><span /></div><p className="api-coverage-note">Dữ liệu thiếu luôn được hiển thị rõ.</p></section><section className="api-welcome-panel"><h2>Bắt đầu theo dõi</h2><p>Đăng nhập hoặc tạo tài khoản để quản lý nhãn hàng của bạn.</p>{cognitoConfig && <div className="api-login-actions"><button type="button" className="button button-primary" disabled={busy} onClick={() => { void startCognitoLogin(cognitoConfig).catch(() => setMessage('Không thể bắt đầu đăng nhập.')); }}>Đăng nhập với Cognito</button><button type="button" className="button" disabled={busy} onClick={() => { void startCognitoLogin(cognitoConfig, 'signup').catch(() => setMessage('Không thể bắt đầu đăng ký.')); }}>Tạo tài khoản</button></div>}
    {!cognitoConfig && <p role="status">Chưa cấu hình đăng nhập. Cần đặt VITE_COGNITO_DOMAIN và VITE_COGNITO_CLIENT_ID.</p>}{busy && <p role="status">Đang kết nối…</p>}
    <details className="api-developer"><summary>Kết nối bằng access token</summary><form className="form" onSubmit={connect}><label className="field">Access token<input type="password" autoComplete="off" value={token} onChange={(e) => setToken(e.target.value)} /></label>
      <button className="button" disabled={busy}>Kết nối</button></form></details>{message && <p role="alert">{message}</p>}</section></main>;

  return <main className="page stack api-workspace"><header className="page-head"><div><p className="wordmark"><span className="wordmark-mark" aria-hidden="true" /> Brand Auto-Tracking</p><h1>Quản lý nhãn hàng</h1></div><button className="button" disabled={busy} onClick={() => { setClient(null); setSelected(null); setBrands([]); setRuns([]); setPage(null); setComments({}); setPendingBrand(null); setUncertainCreate(false); createKey.current = null; setToken(''); setName(''); setKeywords(''); setConfig(initialConfig); setConfigReady(true); setMessage(''); if (cognitoSignedIn && cognitoConfig) { setCognitoSignedIn(false); logoutCognito(cognitoConfig); } }}>Ngắt kết nối</button></header>
    <p>Đây là dữ liệu từ backend. Lịch hoạt động khi dịch vụ lịch được bật; cảnh báo và AI chưa được kết nối.</p>{busy && <p role="status">Đang tải dữ liệu…</p>}{message && <p role="status">{message}</p>}
    <section className="stack"><h2>Nhãn hàng</h2><button className="button" disabled={busy} onClick={() => void execute(() => listBrands(client, brandOffset))}>Tải lại</button>
      {brands.length === 0 && <p>Không có nhãn hàng trên trang này.</p>}
      <ul>{brands.map((b) => <li key={b.id}><button className="button" disabled={busy || !!pendingBrand} onClick={() => openBrand(b)}>{b.name}</button></li>)}</ul>
      <div><button className="button" disabled={busy || brandOffset === 0} onClick={() => void execute(() => listBrands(client, Math.max(0, brandOffset - limit)))}>Trang trước</button> <button className="button" disabled={busy || brands.length < limit} onClick={() => void execute(() => listBrands(client, brandOffset + limit))}>Trang sau</button></div>
    </section>
    <section className="stack"><h2>{selected ? `Cấu hình: ${selected.name}` : 'Tạo nhãn hàng'}</h2>
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
    {selected && <BrandSummary key={`summary-${selected.id}`} api={client} brandId={selected.id} />}
    {selected && <AggregateContent key={`content-${selected.id}`} api={client} brandId={selected.id} />}
    {selected && <section className="stack"><h2>Phiên tracking</h2><button className="button" disabled={busy} onClick={() => void execute(async () => { await client.queueRun(selected.id); await listRuns(client, selected.id); setMessage('Đã xếp hàng; phiên sẽ chạy khi worker hoạt động.'); })}>Tạo phiên chờ</button>
      <button className="button" disabled={busy} onClick={() => void execute(() => listRuns(client, selected.id, runOffset))}>Tải lại phiên</button>
      <ul>{runs.map((run) => <li key={run.id}><button className="button" disabled={busy} onClick={() => showRun(run.id)}>{run.status} · Xếp hàng {run.queued_at}</button></li>)}</ul>
      <div><button className="button" disabled={busy || runOffset === 0} onClick={() => void execute(() => listRuns(client, selected.id, Math.max(0, runOffset - limit)))}>Trang trước</button> <button className="button" disabled={busy || runs.length < limit} onClick={() => void execute(() => listRuns(client, selected.id, runOffset + limit))}>Trang sau</button></div>
      {page && <div className="stack"><h3>Phiên {page.run.status}</h3><p>Xếp hàng: {page.run.queuedAt} · Bắt đầu: {page.run.startedAt ?? 'Chưa bắt đầu'} · Kết thúc: {page.run.finishedAt ?? 'Chưa có'}</p>
        {page.run.errorCode && <p>Lỗi: {page.run.errorCode}</p>}
        <ul>{page.attempts.map((a) => <li key={a.id}>{a.source} / {a.keyword}: {a.status} · {a.resultCount ?? 'Không có số liệu'} {a.errorCode && `· ${a.errorCode}`}</li>)}</ul>
        {page.collectionLimits && <p>Giới hạn thu thập: {page.collectionLimits.search_pages} trang tìm kiếm, {page.collectionLimits.comment_pages} trang bình luận.</p>}
        <h3>Bài viết</h3>{page.posts.length === 0 && <p>Không có bài trên trang này.</p>}
        {page.posts.map((post) => <article key={post.id} className="panel"><h4>{safeLink(post.url) ? <a href={safeLink(post.url)} target="_blank" rel="noreferrer">{post.title || 'Mở bài viết'}</a> : (post.title || 'Đường dẫn không hợp lệ')}</h4><p>{post.content ?? 'Không có nội dung'}</p><p>Nguồn: {post.source} · Đăng: {displayTime(post.postedAt)}</p><p>Thích: {post.likes ?? 'Không có số liệu'} · Bình luận: {post.commentCount ?? 'Không có số liệu'} {post.maybeDuplicate && '· Có thể trùng'}</p>
          <button className="button" disabled={busy} onClick={() => showComments(post.id)}>Xem bình luận</button>
          {comments[post.id] && <><ul>{comments[post.id].map((c) => <li key={c.id}>{c.content} · Thích: {c.likes ?? 'Không có số liệu'} {c.maybeDuplicate && '· Có thể trùng'} · Đăng: {displayTime(c.postedAt)}</li>)}</ul><button className="button" disabled={busy || !(commentOffsets[post.id] > 0)} onClick={() => showComments(post.id, Math.max(0, commentOffsets[post.id] - limit))}>Trang trước</button> <button className="button" disabled={busy || comments[post.id].length < limit} onClick={() => showComments(post.id, (commentOffsets[post.id] ?? 0) + limit)}>Trang sau</button></>}
        </article>)}
        <div><button className="button" disabled={busy || postOffset === 0} onClick={() => showRun(page.run.id, Math.max(0, postOffset - limit))}>Trang trước</button> <button className="button" disabled={busy || page.posts.length < limit} onClick={() => showRun(page.run.id, postOffset + limit)}>Trang sau</button></div>
      </div>}
    </section>}
  </main>;
}
