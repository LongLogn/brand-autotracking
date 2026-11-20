import { AlertOctagon, CalendarRange, Database, FileQuestion, Lightbulb, Loader2, MessageCircle, FileText, Search, Sparkles } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { Panel, PlatformTag } from '../components/ui';
import { InfoTip } from '../components/viz';
import { INITIAL_ANALYSES, NOW, PLATFORMS, platformName } from '../data/mock';
import type { AnalysisResult, Evidence, Insight, PlatformId, Post } from '../data/types';
import { useBrandData, useStore } from '../lib/store';
import { fmtDateTime, fmtDay } from '../lib/format';
import { useBrandId } from './BrandLayout';

const toDateInput = (iso: string) => iso.slice(0, 10);
const DAY = 86_400_000;

function EvidenceLinks({ items }: { items: Evidence[] }) {
  return (
    <span className="evidence">
      {items.map((e) => (
        <Link key={e.id} to={`../content#${e.id}`} relative="path" className="evidence-link" title={e.kind === 'post' ? 'Mở bài viết' : 'Mở bình luận'}>
          {e.kind === 'post' ? <FileText size={12} aria-hidden="true" /> : <MessageCircle size={12} aria-hidden="true" />}
          {e.id}
        </Link>
      ))}
    </span>
  );
}

function InsightCards({ items, kind }: { items: Insight[]; kind: 'finding' | 'suggestion' }) {
  const Icon = kind === 'finding' ? Search : Lightbulb;
  return (
    <ul className={`insight-grid insight-${kind}`}>
      {items.map((x, i) => (
        <li key={i} className="insight-card">
          <span className="insight-icon">
            <Icon size={18} aria-hidden="true" />
          </span>
          <p className="insight-text">{x.text}</p>
          <div className="insight-basis">
            <span className="insight-count">{x.evidence.length} căn cứ</span>
            <EvidenceLinks items={x.evidence} />
          </div>
        </li>
      ))}
    </ul>
  );
}

/** Mô phỏng job phân tích: chỉ giữ nhận định có căn cứ nằm trong phạm vi dữ liệu được chọn. */
function simulate(brandId: string, posts: Post[], from: string, to: string, platforms: PlatformId[], fail: boolean): AnalysisResult {
  const start = Date.parse(from);
  const end = Date.parse(to) + DAY;
  const inScope = posts.filter((p) => platforms.includes(p.platform) && Date.parse(p.firstSeenAt) >= start && Date.parse(p.firstSeenAt) < end);
  const ids = new Set(inScope.flatMap((p) => [p.id, ...p.comments.map((c) => c.id)]));
  const base: AnalysisResult = {
    id: `an-${Date.now()}`,
    brandId,
    createdAt: NOW,
    status: 'done',
    from,
    to,
    platforms,
    postCount: inScope.length,
    commentCount: inScope.reduce((n, p) => n + p.comments.length, 0),
    dataAsOf: NOW,
    gaps: [],
    findings: [],
    suggestions: [],
    model: INITIAL_ANALYSES[0].model,
  };
  if (fail) return { ...base, status: 'error', message: 'Dịch vụ AI không phản hồi sau 60 giây.' };
  if (inScope.length < 3) return { ...base, status: 'no-data', message: `Chỉ có ${inScope.length} bài trong phạm vi, chưa đủ để có nhận định có căn cứ.` };

  const keep = (list: Insight[]) =>
    list.map((x) => ({ ...x, evidence: x.evidence.filter((e) => ids.has(e.id)) })).filter((x) => x.evidence.length > 0);
  const template = INITIAL_ANALYSES[0];
  const gaps = template.gaps.filter((g) => platforms.some((p) => g.includes(platformName(p))));
  const missing = PLATFORMS.filter((p) => !platforms.includes(p.id) && posts.some((x) => x.platform === p.id));
  if (missing.length) gaps.push(`Không gồm ${missing.map((m) => m.name).join(', ')}.`);
  return { ...base, findings: keep(template.findings), suggestions: keep(template.suggestions), gaps };
}

export function AnalysisPage() {
  const brandId = useBrandId();
  const { brand, posts, analyses } = useBrandData(brandId);
  const { addAnalysis, notify } = useStore();
  const [from, setFrom] = useState(toDateInput(new Date(Date.parse(NOW) - 13 * DAY).toISOString()));
  const [to, setTo] = useState(toDateInput(NOW));
  const [platforms, setPlatforms] = useState<PlatformId[]>(brand?.platforms ?? []);
  const [simulateFail, setSimulateFail] = useState(false);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  if (!brand) return null;
  const selected = analyses.find((a) => a.id === selectedId) ?? analyses[0];

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!from || !to || from > to) return setError('Ngày bắt đầu phải trước ngày kết thúc.');
    if (platforms.length === 0) return setError('Chọn ít nhất một nền tảng.');
    setError(null);
    setRunning(true);
    window.setTimeout(() => {
      const result = simulate(brandId, posts, from, to, platforms, simulateFail);
      addAnalysis(result);
      setSelectedId(result.id);
      setRunning(false);
      notify(result.status === 'done' ? 'Đã có kết quả phân tích.' : 'Không tạo được phân tích.', result.status === 'done' ? 'ok' : 'error');
    }, 1600);
  };

  return (
    <div className="with-aside with-aside-wide">
      <aside className="stack">
        <Panel title="Phân tích mới" info={<InfoTip>AI đọc bài và bình luận đã thu thập trong phạm vi chọn, tổng hợp vấn đề nổi bật và gợi ý. Mỗi nhận định dẫn tới nội dung gốc.</InfoTip>}>
          <form className="form" onSubmit={submit} noValidate>
            <div className="form-grid form-grid-2">
              <label className="field">
                <span className="field-label">Từ ngày</span>
                <input type="date" value={from} max={to} onChange={(e) => setFrom(e.target.value)} />
              </label>
              <label className="field">
                <span className="field-label">Đến ngày</span>
                <input type="date" value={to} min={from} onChange={(e) => setTo(e.target.value)} />
              </label>
            </div>
            <div className="chips">
              {brand.platforms.map((p) => (
                <label key={p} className="chip">
                  <input type="checkbox" checked={platforms.includes(p)} onChange={() => setPlatforms((l) => (l.includes(p) ? l.filter((x) => x !== p) : [...l, p]))} />
                  {platformName(p)}
                </label>
              ))}
            </div>
            <label className="check demo-toggle">
              <input type="checkbox" checked={simulateFail} onChange={(e) => setSimulateFail(e.target.checked)} />
              Demo: giả lập AI lỗi
            </label>
            {error && (
              <p className="form-error" role="alert">
                {error}
              </p>
            )}
            <button type="submit" className="button button-primary button-wide" disabled={running}>
              {running ? <Loader2 size={16} className="spin" aria-hidden="true" /> : <Sparkles size={16} aria-hidden="true" />}
              {running ? 'Đang phân tích...' : 'Phân tích'}
            </button>
          </form>
        </Panel>

        {analyses.length > 0 && (
          <Panel title="Đã lưu">
            <ul className="history">
              {analyses.map((a) => (
                <li key={a.id}>
                  <button type="button" className={a.id === selected?.id ? 'history-item is-active' : 'history-item'} onClick={() => setSelectedId(a.id)}>
                    <span className={`history-dot dot-${a.status}`} aria-hidden="true" />
                    <span className="history-range">
                      {fmtDay(a.from)} – {fmtDay(a.to)}
                    </span>
                    <span className="history-time muted">{fmtDateTime(a.createdAt)}</span>
                  </button>
                </li>
              ))}
            </ul>
          </Panel>
        )}
      </aside>

      <div className="with-aside-main">{selected && <Report a={selected} />}</div>
    </div>
  );
}

function Report({ a }: { a: AnalysisResult }) {
  return (
    <article className="stack" aria-label="Kết quả phân tích">
      <div className="scope-bar">
        <div className="scope-item">
          <CalendarRange size={18} aria-hidden="true" />
          <span>
            <span className="scope-key">Thời gian</span>
            <span className="scope-val">
              {fmtDay(a.from)} – {fmtDay(a.to)}
            </span>
          </span>
        </div>
        <div className="scope-item">
          <Database size={18} aria-hidden="true" />
          <span>
            <span className="scope-key">Đầu vào</span>
            <span className="scope-val">
              {a.postCount} bài, {a.commentCount} bình luận
            </span>
          </span>
        </div>
        <div className="scope-item">
          <span className="scope-platforms">
            {a.platforms.map((p) => (
              <PlatformTag key={p} id={p} compact />
            ))}
          </span>
          <span>
            <span className="scope-key">Dữ liệu đến</span>
            <span className="scope-val">{fmtDateTime(a.dataAsOf)}</span>
          </span>
        </div>
        {a.gaps.length > 0 && (
          <div className="scope-item scope-gaps">
            <span className="scope-missing">Thiếu {a.gaps.length} mục dữ liệu</span>
            <InfoTip>
              <ul className="tip-list">
                {a.gaps.map((g) => (
                  <li key={g}>{g}</li>
                ))}
              </ul>
            </InfoTip>
          </div>
        )}
      </div>

      {a.status !== 'done' ? (
        <div className={`state-card ${a.status === 'error' ? 'state-error' : 'state-warn'}`} role="alert">
          {a.status === 'error' ? <AlertOctagon size={32} aria-hidden="true" /> : <FileQuestion size={32} aria-hidden="true" />}
          <div>
            <p className="state-title">{a.status === 'error' ? 'Dịch vụ AI không khả dụng' : 'Chưa đủ dữ liệu'}</p>
            <p>{a.message}</p>
            <p className="muted">{a.status === 'error' ? 'Thử lại sau ít phút.' : 'Mở rộng thời gian hoặc thêm nền tảng.'}</p>
          </div>
        </div>
      ) : (
        <>
          <Panel title={`Nhận định nổi bật (${a.findings.length})`}>
            {a.findings.length ? <InsightCards items={a.findings} kind="finding" /> : <p className="muted">Không có nhận định đủ căn cứ.</p>}
          </Panel>
          <Panel title={`Gợi ý để cân nhắc (${a.suggestions.length})`} info={<InfoTip>Gợi ý do AI tạo từ mẫu dữ liệu, có thể sai hoặc thiên lệch. Hệ thống không tự thực hiện gợi ý nào.</InfoTip>}>
            {a.suggestions.length ? <InsightCards items={a.suggestions} kind="suggestion" /> : <p className="muted">Không có gợi ý đủ căn cứ.</p>}
          </Panel>
        </>
      )}
    </article>
  );
}
