import { BellRing, ChevronRight, FileText, MessageSquareWarning, Radar, ThumbsDown } from 'lucide-react';
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { CoverageStrip, NegativeTrend } from '../components/charts';
import { EmptyState, Num, Panel, PlatformTag, RunStatusTag, SentimentTag } from '../components/ui';
import { BarList, InfoTip, SentimentDonut, StatTile } from '../components/viz';
import type { Run, SentimentCounts } from '../data/types';
import { useBrandData } from '../lib/store';
import { fmtDateTime, fmtNum } from '../lib/format';
import { useBrandId } from './BrandLayout';

type Metric = 'negative-comments' | 'negative-posts';
const WIN = 7;

const sumOrNull = (xs: (number | null)[]) => (xs.length === 0 || xs.some((v) => v === null) ? null : xs.reduce<number>((a, v) => a + (v ?? 0), 0));
function growth(curr: number | null, prev: number | null) {
  if (curr === null || prev === null || prev === 0) return null;
  return Math.round(((curr - prev) / prev) * 100);
}

export function OverviewPage() {
  const brandId = useBrandId();
  const { brand, runs, posts, alerts } = useBrandData(brandId);
  const [metric, setMetric] = useState<Metric>('negative-comments');
  if (!brand) return null;

  if (runs.length === 0) {
    return (
      <EmptyState
        icon={<Radar size={28} />}
        title="Chưa có phiên tracking nào"
        action={
          <Link to="settings" className="button">
            Xem cấu hình
          </Link>
        }
      >
        {brand.active && brand.nextRunAt ? `Phiên đầu tiên chạy lúc ${fmtDateTime(brand.nextRunAt)}.` : 'Nhãn hàng đang tạm dừng.'}
      </EmptyState>
    );
  }

  const completed = runs.filter((r) => r.status !== 'queued' && r.status !== 'running' && r.status !== 'skipped');
  const recent = completed.slice(-WIN * 2);
  const curRuns = recent.slice(-WIN);
  const prevRuns = recent.length >= WIN * 2 ? recent.slice(0, WIN) : [];

  const series = (pick: (r: Run) => number | null) => {
    const c = sumOrNull(curRuns.map(pick));
    const p = prevRuns.length ? sumOrNull(prevRuns.map(pick)) : null;
    return { c, g: growth(c, p), spark: recent.map(pick) };
  };
  const negC = series((r) => r.negativeComments);
  const negP = series((r) => r.negativePosts);
  const collected = series((r) => r.posts + r.comments);

  const allAttempts = curRuns.flatMap((r) => r.attempts);
  const okAttempts = allAttempts.filter((a) => a.status !== 'failed').length;
  const coverage = allAttempts.length ? Math.round((okAttempts / allAttempts.length) * 100) : null;

  const sentiment = curRuns.reduce<SentimentCounts>(
    (acc, r) => {
      if (!r.sentiment) return acc;
      (Object.keys(acc) as (keyof SentimentCounts)[]).forEach((k) => (acc[k] += r.sentiment![k]));
      return acc;
    },
    { positive: 0, neutral: 0, negative: 0, unknown: 0 },
  );

  const byPlatform = brand.platforms.map((p) => {
    const atts = curRuns.flatMap((r) => r.attempts.filter((a) => a.platform === p));
    const failed = atts.filter((a) => a.status === 'failed').length;
    return {
      label: <PlatformTag id={p} />,
      value: atts.reduce((n, a) => n + a.results, 0),
      note: failed > 0 ? <span className="text-negative">{failed} lỗi</span> : undefined,
      tone: `fill-${p}`,
    };
  });

  const lastRun = runs[runs.length - 1];
  const latestAlert = alerts.find((a) => a.kind === 'triggered' && !a.read);
  const topNegative = posts
    .filter((x) => x.sentiment === 'negative')
    .sort((a, b) => (b.reacts ?? -1) - (a.reacts ?? -1))
    .slice(0, 4);

  return (
    <div className="dash">
      {latestAlert && (
        <Link to="alerts" className="alert-banner">
          <BellRing size={20} aria-hidden="true" />
          <span className="alert-banner-text">
            <strong>Cảnh báo mới:</strong> {latestAlert.reason}
          </span>
          <ChevronRight size={18} aria-hidden="true" />
        </Link>
      )}

      <div className="stats">
        <StatTile icon={MessageSquareWarning} tone="chili" label="Bình luận tiêu cực, 7 ngày" value={negC.c === null ? '—' : fmtNum(negC.c)} delta={negC.g} deltaGood={false} spark={negC.spark} />
        <StatTile icon={ThumbsDown} tone="chili" label="Bài viết tiêu cực, 7 ngày" value={negP.c === null ? '—' : fmtNum(negP.c)} delta={negP.g} deltaGood={false} spark={negP.spark} />
        <StatTile icon={FileText} tone="action" label="Nội dung thu thập, 7 ngày" value={collected.c === null ? '—' : fmtNum(collected.c)} delta={collected.g} deltaGood spark={collected.spark} />
        <StatTile
          icon={Radar}
          tone="leaf"
          label="Lượt thu thập thành công"
          value={coverage === null ? '—' : coverage}
          unit="%"
          foot={
            <span>
              {okAttempts}/{allAttempts.length} lượt
            </span>
          }
        />
      </div>

      <div className="dash-grid">
        <Panel
          className="span-2"
          title="Nội dung tiêu cực theo ngày"
          info={<InfoTip>So sánh 7 ngày gần nhất với 7 ngày trước đó. Đếm nội dung duy nhất. Ngày có lượt lỗi không bị tính là 0.</InfoTip>}
          action={
            <div className="segmented segmented-sm" role="tablist" aria-label="Chỉ số">
              <button type="button" role="tab" aria-selected={metric === 'negative-comments'} onClick={() => setMetric('negative-comments')}>
                Bình luận
              </button>
              <button type="button" role="tab" aria-selected={metric === 'negative-posts'} onClick={() => setMetric('negative-posts')}>
                Bài viết
              </button>
            </div>
          }
        >
          <NegativeTrend
            runs={recent}
            pick={(r) => (metric === 'negative-comments' ? r.negativeComments : r.negativePosts)}
            windowDays={WIN}
            unit={metric === 'negative-comments' ? 'bình luận' : 'bài'}
          />
        </Panel>

        <Panel title="Cảm xúc, 7 ngày" info={<InfoTip>Phân loại bằng AI, là ước lượng. Nội dung chưa phân tích được không tính là tiêu cực.</InfoTip>}>
          <SentimentDonut counts={sentiment} />
        </Panel>

        <Panel
          className="span-2"
          title="Độ bao phủ theo nền tảng"
          info={<InfoTip>Mỗi ô là một phiên trên một nền tảng. Bấm vào ô để xem chi tiết.</InfoTip>}
          action={
            <Link to="runs" className="text-link">
              Tất cả phiên
            </Link>
          }
        >
          <CoverageStrip runs={recent} platforms={brand.platforms} brandId={brand.id} />
        </Panel>

        <Panel title="Bài thu được theo nền tảng">
          <BarList items={byPlatform} />
        </Panel>

        <Panel
          className="span-2"
          title="Bài tiêu cực nổi bật"
          action={
            <Link to="content" className="text-link">
              Xem nội dung
            </Link>
          }
        >
          {topNegative.length === 0 ? (
            <p className="muted">Chưa có bài tiêu cực.</p>
          ) : (
            <ul className="mini-posts">
              {topNegative.map((x) => (
                <li key={x.id}>
                  <Link to={`content#${x.id}`} className="mini-post">
                    <PlatformTag id={x.platform} compact />
                    <span className="mini-post-title">{x.title}</span>
                    <SentimentTag value={x.sentiment} />
                    <span className="mini-post-num">
                      <Num value={x.reacts} />
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <Panel
          title="Phiên gần nhất"
          action={
            <Link to={`runs/${lastRun.id}`} className="text-link">
              Chi tiết
            </Link>
          }
        >
          <div className="last-run">
            <RunStatusTag value={lastRun.status} />
            <span className="muted">{fmtDateTime(lastRun.startedAt)}</span>
          </div>
          <div className="kv-grid">
            <div className="kv">
              <span className="kv-val">{fmtNum(lastRun.posts)}</span>
              <span className="kv-key">bài viết</span>
            </div>
            <div className="kv">
              <span className="kv-val">{fmtNum(lastRun.comments)}</span>
              <span className="kv-key">bình luận</span>
            </div>
            <div className="kv">
              <span className="kv-val">{lastRun.attempts.filter((a) => a.status !== 'failed').length}/{lastRun.attempts.length}</span>
              <span className="kv-key">lượt ổn</span>
            </div>
          </div>
        </Panel>
      </div>
    </div>
  );
}
