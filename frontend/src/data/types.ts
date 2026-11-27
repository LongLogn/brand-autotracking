// Kiểu dữ liệu phía giao diện, bám theo SRS mục 5 và bảng dữ liệu trong docs/architecture_aws.md mục 7.
// `null` luôn nghĩa là nguồn không cung cấp (không khả dụng), không bao giờ được hiểu là 0.

export type PlatformId = 'reddit' | 'threads' | 'facebook' | 'tiktok';
export type PlatformSupport = 'verified' | 'experimental' | 'unsupported';

export interface Platform {
  id: PlatformId;
  name: string;
  support: PlatformSupport;
  /** Ghi chú về khả năng lấy dữ liệu qua Firecrawl. */
  note: string;
}

export type Sentiment = 'positive' | 'negative' | 'neutral' | 'unknown';

export interface Comment {
  id: string;
  text: string;
  postedAt: string | null;
  reacts: number | null;
  sentiment: Sentiment;
}

export interface Post {
  id: string;
  brandId: string;
  platform: PlatformId;
  url: string;
  title: string;
  text: string;
  postedAt: string | null;
  reacts: number | null;
  commentCount: number | null;
  sentiment: Sentiment;
  keywords: string[];
  runIds: string[];
  firstSeenAt: string;
  /** Không có định danh ổn định từ nguồn, nên không bảo đảm khử trùng. */
  maybeDuplicate?: boolean;
  comments: Comment[];
}

export type Frequency = 'daily' | 'twice-daily' | 'weekly';

export interface Brand {
  id: string;
  name: string;
  description: string;
  keywords: string[];
  platforms: PlatformId[];
  frequency: Frequency;
  runTime: string; // HH:mm theo múi giờ
  timezone: string;
  postLimit: number;
  active: boolean;
  nextRunAt: string | null;
}

export type AttemptStatus = 'success' | 'empty' | 'failed';
export type RunStatus = 'queued' | 'running' | 'success' | 'partial' | 'failed' | 'skipped' | 'cancelled';

export interface Attempt {
  platform: PlatformId;
  keyword: string;
  status: AttemptStatus;
  results: number;
  error?: string;
}

export interface Run {
  id: string;
  brandId: string;
  startedAt: string;
  finishedAt: string | null;
  status: RunStatus;
  postLimit: number;
  attempts: Attempt[];
  posts: number;
  comments: number;
  negativePosts: number | null;
  negativeComments: number | null;
  /** Phân bố cảm xúc của bài viết và bình luận thu được trong phiên. `null` khi phiên không có dữ liệu. */
  sentiment: SentimentCounts | null;
  note?: string;
}

export type SentimentCounts = Record<Sentiment, number>;

export type AlertMetric = 'negative-comments' | 'negative-posts';

export interface AlertRule {
  id: string;
  brandId: string;
  metric: AlertMetric;
  windowDays: number;
  growthPercent: number;
  minCount: number;
  /** Áp dụng khi cửa sổ trước bằng 0. `null` nghĩa là chưa đặt. */
  absoluteThreshold: number | null;
  enabled: boolean;
}

export interface Alert {
  id: string;
  brandId: string;
  ruleId: string;
  createdAt: string;
  kind: 'triggered' | 'insufficient';
  metric: AlertMetric;
  windowLabel: string;
  previous: number | null;
  current: number | null;
  growthPercent: number | null;
  threshold: string;
  reason: string;
  read: boolean;
}

export interface Evidence {
  kind: 'post' | 'comment';
  id: string;
}

export interface Insight {
  text: string;
  evidence: Evidence[];
}

export interface AnalysisResult {
  id: string;
  brandId: string;
  createdAt: string;
  status: 'done' | 'no-data' | 'error';
  from: string;
  to: string;
  platforms: PlatformId[];
  postCount: number;
  commentCount: number;
  dataAsOf: string;
  gaps: string[];
  findings: Insight[];
  suggestions: Insight[];
  model: string;
  message?: string;
}
