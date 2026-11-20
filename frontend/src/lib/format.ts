const TZ = 'Asia/Ho_Chi_Minh';

const dateTime = new Intl.DateTimeFormat('vi-VN', {
  timeZone: TZ,
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
});
const dayMonth = new Intl.DateTimeFormat('vi-VN', { timeZone: TZ, day: '2-digit', month: '2-digit' });
const time = new Intl.DateTimeFormat('vi-VN', { timeZone: TZ, hour: '2-digit', minute: '2-digit' });
const weekday = new Intl.DateTimeFormat('vi-VN', { timeZone: TZ, weekday: 'short' });
const num = new Intl.NumberFormat('vi-VN');

export const fmtDateTime = (iso: string) => dateTime.format(new Date(iso));
export const fmtDay = (iso: string) => {
  const parts = dayMonth.formatToParts(new Date(iso));
  const get = (t: string) => parts.find((p) => p.type === t)?.value ?? '';
  return `${get('day')}/${get('month')}`;
};
export const fmtTime = (iso: string) => time.format(new Date(iso));
export const fmtWeekday = (iso: string) => weekday.format(new Date(iso));
export const fmtNum = (n: number) => num.format(n);

export function fmtDuration(startIso: string, endIso: string | null) {
  if (!endIso) return null;
  const sec = Math.round((Date.parse(endIso) - Date.parse(startIso)) / 1000);
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return m > 0 ? `${m} phút ${s.toString().padStart(2, '0')} giây` : `${s} giây`;
}

export const FREQUENCY_LABEL = {
  daily: 'Mỗi ngày',
  'twice-daily': 'Hai lần mỗi ngày',
  weekly: 'Mỗi tuần',
} as const;

/** Dạng ngắn m:ss cho ô số liệu. */
export function fmtDurationShort(startIso: string, endIso: string | null) {
  if (!endIso) return null;
  const sec = Math.round((Date.parse(endIso) - Date.parse(startIso)) / 1000);
  return `${Math.floor(sec / 60)}:${(sec % 60).toString().padStart(2, '0')}`;
}

export const METRIC_LABEL = {
  'negative-comments': 'Bình luận tiêu cực',
  'negative-posts': 'Bài viết tiêu cực',
} as const;

export const METRIC_UNIT = {
  'negative-comments': 'bình luận',
  'negative-posts': 'bài viết',
} as const;
