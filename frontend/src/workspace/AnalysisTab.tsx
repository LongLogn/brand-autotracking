import { Lightbulb, RefreshCw, Sparkles } from 'lucide-react';
import { useEffect, useState, type FormEvent } from 'react';
import { ApiError, type ApiAnalysis } from '../lib/api';
import { InfoTip } from '../components/viz';
import { Notice, Pager, SectionHead, displayTime, safeLink, type Client } from './shared';

function failureText(code: string | null) {
  if (code === 'owner_budget_exhausted') return 'Tài khoản đã hết lượt gọi Bedrock. Thử lại sau 00:00 UTC.';
  return code === 'empty_data' ? 'Không có nội dung phù hợp.' : code === 'budget_exhausted' ? 'Đã hết hạn mức lượt gọi.'
    : code === 'rate_limited' ? 'Đã hết hạn mức trong phút này, hãy thử lại sau.'
    : code === 'timeout' ? 'Yêu cầu quá thời gian xử lý; kết quả đến muộn không được lưu.' : 'Dịch vụ không trả kết quả có dẫn chứng hợp lệ.';
}

function AnalysisResult({ job }: { job: ApiAnalysis }) {
  const state = job.status === 'success' ? 'ok' : job.status === 'failed' ? 'failed' : 'running';
  return <article className={`panel ws-analysis ws-analysis-${state}`}>
    <header className="ws-analysis-head">
      <h3>{job.status === 'success' ? 'Phân tích hoàn tất' : job.status === 'failed' ? 'Không tạo được phân tích' : 'Đang xử lý'}</h3>
      <span className={`status ${job.status === 'success' ? 'status-success' : job.status === 'failed' ? 'status-failed' : 'status-running'}`}>
        {job.status === 'success' ? `${job.findings?.length ?? 0} chủ đề` : job.status === 'failed' ? 'Lỗi' : 'Đang chạy'}</span>
    </header>
    <p className="ws-muted">Phạm vi thu thập: {displayTime(job.window_start)} – {displayTime(job.window_end)} · Yêu cầu: {displayTime(job.created_at)}</p>
    {job.status === 'running' && <p>Yêu cầu có thể bị gián đoạn nếu trạng thái không thay đổi; kiểm tra lịch sử trước khi yêu cầu lại.</p>}
    {job.status === 'failed' && <p>{failureText(job.error_code)}</p>}
    {job.status === 'success' && <>
      <p className="ws-analysis-scope">Đã dùng {job.sample_count} nội dung{job.sample_truncated ? ' · Mẫu đã giới hạn' : ''}{job.has_undated_comments ? ' · Có bình luận cũ thiếu thời điểm không được đưa vào' : ''}.</p>
      <ol className="ws-findings">{job.findings?.map((finding, index) => <li key={index} className="ws-finding">
        <p className="ws-finding-summary">{finding.summary}</p>
        <p className="ws-finding-tip"><Lightbulb size={15} aria-hidden="true" /><span>Gợi ý: {finding.recommendation}</span></p>
        <div className="ws-evidence"><span>Dẫn chứng:</span>{finding.evidence_ids.map((id) => {
          const source = job.evidence?.find((item) => item.id === id); const link = source && safeLink(source.url);
          // Hiện lời văn của bình luận/bài; chỉ quay về mã khi không còn nội dung khớp bản AI đã đọc.
          const label = source?.text ? `“${source.text.replace(/^\[DỮ LIỆU GIẢ\]\s*/, '')}”` : id;
          return <blockquote key={id} className={source?.text ? 'ws-evidence-quote' : 'ws-evidence-id'}>
            {link ? <a href={link} target="_blank" rel="noreferrer">{label}</a> : label}
            {source?.kind === 'post' ? <span className="ws-muted"> · bài viết</span> : null}
            {source?.text_truncated ? ' (đoạn đã rút ngắn)' : ''}
          </blockquote>;
        })}</div>
      </li>)}</ol>
    </>}
  </article>;
}

export function AnalysisSettings({ api, brandId }: { api: Client; brandId: string }) {
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
  return <section className="ws-split ws-split-aside">
    <div className="panel ws-aside-panel">
      <SectionHead title="Phân tích AI"
        info={<InfoTip>Chọn khoảng thời gian thu thập theo múi giờ thiết bị. Chỉ dùng nội dung có bằng chứng phiên bản hiện tại được quan sát trong khoảng, tối đa 30 nội dung mới nhất; kết quả chỉ để tham khảo và có thể sai, không đại diện toàn thị trường.</InfoTip>} />
      <form className="form" onSubmit={submit}>
        <label className="field"><span className="field-label">Thu thập từ</span><input type="datetime-local" required disabled={busy || !!pending} value={start} onChange={(event) => setStart(event.target.value)} /></label>
        <label className="field"><span className="field-label">Thu thập trước</span><input type="datetime-local" required disabled={busy || !!pending} value={end} onChange={(event) => setEnd(event.target.value)} /></label>
        <button className="button button-primary button-wide" disabled={busy}><Sparkles size={16} aria-hidden="true" />{pending ? 'Kiểm tra lại yêu cầu' : 'Tạo phân tích'}</button>
        {pending && <p className="ws-muted">Yêu cầu có thể đang xử lý. Lịch sử bên cạnh giúp kiểm tra trạng thái; thử lại dùng cùng khóa yêu cầu.</p>}
        {pending && !busy && <button type="button" className="button button-sm" onClick={() => setPending(null)}>Tôi đã kiểm tra lịch sử, tạo yêu cầu mới</button>}
      </form>
      {busy && <Notice>Đang yêu cầu phân tích…</Notice>}
      {error && <Notice tone="error">{error}</Notice>}
      <p className="ws-disclaimer">AI chỉ gợi ý để tham khảo, gắn với dữ liệu và khoảng thời gian đã chọn. Quyết định thuộc về nhãn hàng.</p>
    </div>
    <div className="ws-stack">
      <div className="ws-row-head"><h3>Kết quả phân tích</h3>
        <button className="button button-sm" disabled={loading || busy} onClick={() => { setError(''); setRevision((value) => value + 1); }}><RefreshCw size={15} aria-hidden="true" />Tải lại phân tích</button></div>
      {loading && <Notice>Đang tải phân tích…</Notice>}
      {!loading && jobs.length === 0 && <div className="panel ws-empty"><Sparkles size={22} aria-hidden="true" /><p>Chưa có phân tích trên trang này.</p><p className="ws-muted">Chọn khoảng thời gian bên trái rồi bấm Tạo phân tích.</p></div>}
      {jobs.map((job) => <AnalysisResult key={job.id} job={job} />)}
      <Pager prevLabel="Phân tích trước" nextLabel="Phân tích tiếp" prevDisabled={loading || busy || offset === 0} nextDisabled={loading || busy || jobs.length < 20}
        onPrev={() => setOffset((value) => Math.max(0, value - 20))} onNext={() => setOffset((value) => value + 20)} />
    </div>
  </section>;
}
