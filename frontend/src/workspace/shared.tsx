import { AlertCircle, CheckCircle2, ChevronLeft, ChevronRight, ExternalLink, Heart, Loader2, MessageCircle } from 'lucide-react';
import type { ReactNode } from 'react';
import type { ApiMetrics, createApiClient } from '../lib/api';
import { SentimentTag } from '../components/ui';

export type Client = ReturnType<typeof createApiClient>;

/** Chỉ mở liên kết http(s) thật; liên kết `.invalid` của dữ liệu giả không mở được. */
export function safeLink(value: string) {
  try {
    const url = new URL(value);
    return (url.protocol === 'https:' || url.protocol === 'http:') && !url.hostname.endsWith('.invalid') ? url.href : undefined;
  } catch { return undefined; }
}
export function displaySource(value: string) { return value === 'demo' ? 'Dữ liệu giả lập' : value === 'tiktok' ? 'TikTok' : value; }
export function displayTime(value: string | null | undefined) {
  if (!value) return 'Không có số liệu';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Không có số liệu' : date.toLocaleString('vi-VN');
}
export function shortTime(value: string | null | undefined) {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
}
export function displaySentiment(value: string | undefined) {
  return ({ positive: 'Tích cực', negative: 'Tiêu cực', neutral: 'Trung lập' } as Record<string, string>)[value ?? ''] ?? 'Chưa xác định';
}
export function percent(negative: number, total: number) {
  return total > 0 ? `${Math.round((negative * 100) / total)}%` : '—';
}
export function initials(name: string) {
  const words = name.trim().split(/\s+/);
  return ((words[0]?.[0] ?? '') + (words.length > 1 ? words[words.length - 1][0] : '')).toUpperCase();
}
/** Chuỗi ổn định cho cùng một nhãn hàng để chọn màu avatar. */
export function avatarTone(id: string) {
  let sum = 0;
  for (const char of id) sum = (sum + char.charCodeAt(0)) % 997;
  return sum % 4;
}

export type Tone = 'info' | 'error' | 'success';
/** Thông báo ngắn: lỗi dùng role="alert", còn lại role="status". */
export function Notice({ tone = 'info', children, action }: { tone?: Tone; children: ReactNode; action?: ReactNode }) {
  const Icon = tone === 'error' ? AlertCircle : tone === 'success' ? CheckCircle2 : Loader2;
  return <div className={`ws-notice ws-notice-${tone}`}>
    <Icon size={16} aria-hidden="true" className={tone === 'info' ? 'spin' : undefined} />
    <p role={tone === 'error' ? 'alert' : 'status'}>{children}</p>
    {action}
  </div>;
}

export function Pager({ onPrev, onNext, prevDisabled, nextDisabled, prevLabel = 'Trang trước', nextLabel = 'Trang sau' }: {
  onPrev: () => void; onNext: () => void; prevDisabled: boolean; nextDisabled: boolean; prevLabel?: string; nextLabel?: string;
}) {
  if (prevDisabled && nextDisabled) return null;
  return <div className="ws-pager">
    <button type="button" className="button button-sm" disabled={prevDisabled} onClick={onPrev}><ChevronLeft size={15} aria-hidden="true" />{prevLabel}</button>
    <button type="button" className="button button-sm" disabled={nextDisabled} onClick={onNext}>{nextLabel}<ChevronRight size={15} aria-hidden="true" /></button>
  </div>;
}

export function Sentiment({ value }: { value: string | undefined }) {
  const known = value === 'positive' || value === 'negative' || value === 'neutral' ? value : 'unknown';
  return <SentimentTag value={known} />;
}

/** Số liệu có thể không khả dụng: hiển thị vân gạch thay vì số 0. */
export function Metric({ icon, value, label }: { icon: 'likes' | 'comments'; value: number | null | undefined; label: string }) {
  const Icon = icon === 'likes' ? Heart : MessageCircle;
  return <span className="ws-metric" title={label}>
    <Icon size={14} aria-hidden="true" />
    <span className="visually-hidden">{label}: </span>
    {value === null || value === undefined ? <span className="na">Không có số liệu</span> : <span className="num">{value.toLocaleString('vi-VN')}</span>}
  </span>;
}

export function PostLink({ url, title, source }: { url: string; title: string | null; source: string }) {
  const link = safeLink(url);
  const label = title || (link ? 'Mở bài viết' : source === 'demo' ? 'Bài giả lập' : 'Đường dẫn không hợp lệ');
  return link
    ? <a href={link} target="_blank" rel="noreferrer" className="ws-post-link">{label}<ExternalLink size={13} aria-hidden="true" /></a>
    : <>{label}</>;
}

export function metricsOf(metrics: ApiMetrics | null) {
  return { likes: metrics?.likes ?? null, comments: metrics?.comment_count ?? null };
}

/** Nhóm tiêu đề vùng: tiêu đề, giải thích trong ⓘ và nút thao tác bên phải. */
export function SectionHead({ title, info, actions, level = 2 }: { title: string; info?: ReactNode; actions?: ReactNode; level?: 2 | 3 }) {
  const Heading = level === 2 ? 'h2' : 'h3';
  return <header className="ws-section-head">
    <div className="ws-section-title"><Heading>{title}</Heading>{info}</div>
    {actions && <div className="ws-section-actions">{actions}</div>}
  </header>;
}
