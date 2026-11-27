import { AlertTriangle, CheckCircle2, CircleDashed, Loader2, MinusCircle, XCircle } from 'lucide-react';
import type { ReactNode } from 'react';
import { platformName } from '../data/mock';
import type { AttemptStatus, PlatformId, RunStatus, Sentiment } from '../data/types';
import { fmtNum } from '../lib/format';

/** Giá trị nguồn không cung cấp. Luôn hiển thị khác với 0 (SRS FR-21, kiểm chứng 4). */
export function Unavailable({ label = 'Không có' }: { label?: string }) {
  return (
    <span className="na" title="Nguồn không cung cấp dữ liệu này">
      {label}
    </span>
  );
}

export function Num({ value, unit }: { value: number | null; unit?: string }) {
  if (value === null) return <Unavailable />;
  return (
    <span className="num">
      {fmtNum(value)}
      {unit ? ` ${unit}` : ''}
    </span>
  );
}

const PLATFORM_LETTER: Record<PlatformId, string> = { reddit: 'R', threads: '@', facebook: 'f', tiktok: 'T' };

export function PlatformTag({ id, compact }: { id: PlatformId; compact?: boolean }) {
  if (compact) {
    return (
      <span className={`pf-dot pf-${id}`} title={platformName(id)} aria-label={platformName(id)}>
        {PLATFORM_LETTER[id]}
      </span>
    );
  }
  return (
    <span className={`platform pf-${id}`}>
      <span className="platform-letter" aria-hidden="true">
        {PLATFORM_LETTER[id]}
      </span>
      {platformName(id)}
    </span>
  );
}

const SENTIMENT: Record<Sentiment, string> = {
  positive: 'Tích cực',
  negative: 'Tiêu cực',
  neutral: 'Trung lập',
  unknown: 'Chưa rõ',
};

export function SentimentTag({ value }: { value: Sentiment }) {
  return <span className={`sentiment sentiment-${value}`}>{SENTIMENT[value]}</span>;
}

const RUN: Record<RunStatus, { label: string; icon: typeof CheckCircle2 }> = {
  queued: { label: 'Đang chờ', icon: CircleDashed },
  running: { label: 'Đang chạy', icon: Loader2 },
  success: { label: 'Thành công', icon: CheckCircle2 },
  partial: { label: 'Một phần', icon: AlertTriangle },
  failed: { label: 'Thất bại', icon: XCircle },
  skipped: { label: 'Bỏ qua', icon: MinusCircle },
  cancelled: { label: 'Đã hủy', icon: MinusCircle },
};

export function RunStatusTag({ value }: { value: RunStatus }) {
  const { label, icon: Icon } = RUN[value];
  return (
    <span className={`status status-${value}`}>
      <Icon size={14} strokeWidth={2.4} aria-hidden="true" />
      {label}
    </span>
  );
}

const ATTEMPT: Record<AttemptStatus, { label: string; icon: typeof CheckCircle2 }> = {
  success: { label: 'Có kết quả', icon: CheckCircle2 },
  empty: { label: 'Rỗng', icon: CircleDashed },
  failed: { label: 'Lỗi', icon: XCircle },
};

export function AttemptStatusTag({ value }: { value: AttemptStatus }) {
  const { label, icon: Icon } = ATTEMPT[value];
  return (
    <span className={`status attempt-${value}`}>
      <Icon size={14} strokeWidth={2.4} aria-hidden="true" />
      {label}
    </span>
  );
}

export function EmptyState({ title, children, action, icon }: { title: string; children?: ReactNode; action?: ReactNode; icon?: ReactNode }) {
  return (
    <div className="empty">
      {icon && <span className="empty-icon">{icon}</span>}
      <p className="empty-title">{title}</p>
      {children && <div className="empty-body">{children}</div>}
      {action}
    </div>
  );
}

export function SampleBadge() {
  return (
    <span className="sample-badge" title="Dữ liệu mẫu để trình diễn giao diện. Chưa kết nối backend và Firecrawl.">
      Dữ liệu mẫu
    </span>
  );
}

export function Panel({ title, action, info, children, className }: { title?: ReactNode; action?: ReactNode; info?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`panel ${className ?? ''}`}>
      {(title || action) && (
        <header className="panel-head">
          <h2 className="panel-title">
            {title}
            {info}
          </h2>
          {action}
        </header>
      )}
      {children}
    </section>
  );
}
