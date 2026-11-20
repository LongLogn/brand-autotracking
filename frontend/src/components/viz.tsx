import { Info, type LucideIcon } from 'lucide-react';
import { useId, type ReactNode } from 'react';
import type { Attempt, SentimentCounts } from '../data/types';
import { fmtNum } from '../lib/format';

/** Giải thích ngắn chỉ hiện khi rê chuột hoặc focus, thay cho đoạn văn dài. */
export function InfoTip({ children }: { children: ReactNode }) {
  const id = useId();
  return (
    <span className="infotip">
      <button type="button" className="infotip-btn" aria-describedby={id} aria-label="Giải thích">
        <Info size={15} strokeWidth={2.2} aria-hidden="true" />
      </button>
      <span role="tooltip" id={id} className="infotip-body">
        {children}
      </span>
    </span>
  );
}

export function Sparkline({ values, tone = 'ink' }: { values: (number | null)[]; tone?: 'ink' | 'chili' | 'leaf' | 'action' }) {
  const w = 120;
  const h = 32;
  const nums = values.map((v) => v ?? 0);
  const max = Math.max(1, ...nums);
  const step = values.length > 1 ? w / (values.length - 1) : w;
  const pts = values.map((v, i) => (v === null ? null : [i * step, h - 3 - ((v / max) * (h - 6))] as const));
  const d = pts.reduce((acc, p, i) => {
    if (!p) return acc;
    const prev = pts[i - 1];
    return `${acc}${prev ? 'L' : 'M'}${p[0].toFixed(1)},${p[1].toFixed(1)}`;
  }, '');
  const last = [...pts].reverse().find(Boolean);
  return (
    <svg className={`spark spark-${tone}`} viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" aria-hidden="true">
      <path d={`${d}L${w},${h}L0,${h}Z`} className="spark-area" />
      <path d={d} className="spark-line" vectorEffect="non-scaling-stroke" />
      {last && <circle cx={last[0]} cy={last[1]} r="2.5" className="spark-dot" />}
    </svg>
  );
}

export function StatTile({
  icon: Icon,
  label,
  value,
  unit,
  delta,
  deltaGood,
  tone,
  spark,
  foot,
}: {
  icon: LucideIcon;
  label: string;
  value: ReactNode;
  unit?: string;
  delta?: number | null;
  /** Tăng là tốt (true) hay xấu (false). */
  deltaGood?: boolean;
  tone: 'ink' | 'chili' | 'leaf' | 'action' | 'amber';
  spark?: (number | null)[];
  foot?: ReactNode;
}) {
  const deltaTone = delta == null || delta === 0 ? 'flat' : (delta > 0) === deltaGood ? 'good' : 'bad';
  return (
    <div className={`stat stat-${tone}`}>
      <div className="stat-top">
        <span className="stat-icon">
          <Icon size={18} strokeWidth={2.2} aria-hidden="true" />
        </span>
        <span className="stat-label">{label}</span>
      </div>
      <div className="stat-main">
        <span className="stat-value">
          {value}
          {unit && <span className="stat-unit">{unit}</span>}
        </span>
        {delta !== undefined && (
          <span className={`delta delta-${deltaTone}`}>
            {delta === null ? 'Chưa so sánh' : `${delta > 0 ? '+' : ''}${delta}%`}
          </span>
        )}
      </div>
      {spark && <Sparkline values={spark} tone={tone === 'amber' ? 'ink' : tone} />}
      {foot && <div className="stat-foot">{foot}</div>}
    </div>
  );
}

const SENT_ORDER: { key: keyof SentimentCounts; label: string }[] = [
  { key: 'negative', label: 'Tiêu cực' },
  { key: 'neutral', label: 'Trung lập' },
  { key: 'positive', label: 'Tích cực' },
  { key: 'unknown', label: 'Chưa phân tích' },
];

export function SentimentDonut({ counts }: { counts: SentimentCounts }) {
  const total = SENT_ORDER.reduce((n, s) => n + counts[s.key], 0);
  const r = 42;
  const c = 2 * Math.PI * r;
  let offset = 0;
  return (
    <div className="donut-wrap">
      <svg viewBox="0 0 120 120" className="donut" role="img" aria-label={SENT_ORDER.map((s) => `${s.label} ${counts[s.key]}`).join(', ')}>
        <defs>
          <pattern id="hatch" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <rect width="5" height="5" fill="var(--hatch-bg)" />
            <line x1="0" y1="0" x2="0" y2="5" stroke="var(--hatch)" strokeWidth="2" />
          </pattern>
        </defs>
        <circle cx="60" cy="60" r={r} className="donut-track" />
        {SENT_ORDER.map((s) => {
          const len = total ? (counts[s.key] / total) * c : 0;
          const el = (
            <circle
              key={s.key}
              cx="60"
              cy="60"
              r={r}
              className={`donut-seg donut-${s.key}`}
              strokeDasharray={`${Math.max(0, len - 1.5)} ${c}`}
              strokeDashoffset={-offset}
            />
          );
          offset += len;
          return el;
        })}
        <text x="60" y="57" className="donut-total">
          {fmtNum(total)}
        </text>
        <text x="60" y="73" className="donut-caption">
          nội dung
        </text>
      </svg>
      <ul className="donut-legend">
        {SENT_ORDER.map((s) => (
          <li key={s.key}>
            <i className={`swatch sw-${s.key}`} />
            <span className="donut-legend-label">{s.label}</span>
            <span className="donut-legend-val">{total ? Math.round((counts[s.key] / total) * 100) : 0}%</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** Thanh ngang tỷ lệ, dùng cho phân bố theo nền tảng. */
export function BarList({ items }: { items: { label: ReactNode; value: number; note?: ReactNode; tone?: string }[] }) {
  const max = Math.max(1, ...items.map((i) => i.value));
  return (
    <ul className="barlist">
      {items.map((it, i) => (
        <li key={i} className="barlist-row">
          <span className="barlist-label">{it.label}</span>
          <span className="barlist-track">
            <span className={`barlist-fill ${it.tone ?? ''}`} style={{ width: `${(it.value / max) * 100}%` }} />
          </span>
          <span className="barlist-val">{fmtNum(it.value)}</span>
          {it.note && <span className="barlist-note">{it.note}</span>}
        </li>
      ))}
    </ul>
  );
}

/** Thanh phân đoạn số lượt có kết quả / rỗng / lỗi của một phiên. */
export function AttemptBar({ attempts }: { attempts: Attempt[] }) {
  const ok = attempts.filter((a) => a.status === 'success').length;
  const empty = attempts.filter((a) => a.status === 'empty').length;
  const failed = attempts.length - ok - empty;
  if (attempts.length === 0) return <span className="attbar attbar-none" aria-label="Không có lượt nào" />;
  return (
    <span className="attbar-wrap" aria-label={`${ok} có kết quả, ${empty} rỗng, ${failed} lỗi`}>
      <span className="attbar" aria-hidden="true">
        {ok > 0 && <span className="attbar-ok" style={{ flexGrow: ok }} />}
        {empty > 0 && <span className="attbar-empty" style={{ flexGrow: empty }} />}
        {failed > 0 && <span className="attbar-failed" style={{ flexGrow: failed }} />}
      </span>
      <span className="attbar-text">
        {ok}/{attempts.length}
      </span>
    </span>
  );
}
