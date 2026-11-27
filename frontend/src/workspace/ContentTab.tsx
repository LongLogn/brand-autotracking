import { ChevronDown, Filter, Inbox, MessageCircle, RefreshCw } from 'lucide-react';
import { useEffect, useRef, useState, type ReactNode } from 'react';
import type { ApiComment, ApiPost, PostFilters } from '../lib/api';
import { InfoTip } from '../components/viz';
import { Metric, Notice, Pager, PostLink, SectionHead, Sentiment, displaySource, displayTime, metricsOf, type Client } from './shared';

export interface PostView {
  id: string; url: string; title: string | null; content: string | null; source: string; postedAt: string | null;
  sentiment?: string; likes: number | null; comments: number | null; maybeDuplicate: boolean;
}
export interface CommentView { id: string; content: string; postedAt: string | null; sentiment?: string; likes: number | null; maybeDuplicate: boolean }

export function fromApiPost(post: ApiPost): PostView {
  const metrics = metricsOf(post.metrics);
  return { id: post.id, url: post.url, title: post.title, content: post.content, source: post.source, postedAt: post.posted_at,
    sentiment: post.sentiment, likes: metrics.likes, comments: metrics.comments, maybeDuplicate: post.maybe_duplicate };
}
export function fromApiComment(comment: ApiComment): CommentView {
  return { id: comment.id, content: comment.content, postedAt: comment.posted_at, sentiment: comment.sentiment,
    likes: comment.metrics?.likes ?? null, maybeDuplicate: comment.maybe_duplicate };
}

export function CommentList({ comments }: { comments: CommentView[] }) {
  if (comments.length === 0) return <p className="ws-muted">Không có bình luận trên trang này.</p>;
  return <ul className="ws-comments">{comments.map((comment) => <li key={comment.id} className={`ws-comment ws-comment-${comment.sentiment ?? 'unknown'}`}>
    <p className="ws-comment-text">{comment.content}</p>
    <p className="ws-comment-meta"><Sentiment value={comment.sentiment} /><Metric icon="likes" value={comment.likes} label="Thích" />
      <span>{displayTime(comment.postedAt)}</span>{comment.maybeDuplicate && <span className="flag">Có thể trùng</span>}</p>
  </li>)}</ul>;
}

/** Thẻ bài viết dùng chung cho nội dung tổng hợp và chi tiết phiên. */
export function PostCard({ post, commentButton, children }: { post: PostView; commentButton: ReactNode; children?: ReactNode }) {
  return <article className={`panel ws-post ws-post-${post.sentiment ?? 'unknown'}`}>
    <header className="ws-post-head">
      <span className="ws-source">{displaySource(post.source)}</span>
      <Sentiment value={post.sentiment} />
      {post.maybeDuplicate && <span className="flag" title="Nội dung thiếu ID nguồn có thể trùng">Có thể trùng</span>}
      <span className="ws-post-time">{displayTime(post.postedAt)}</span>
    </header>
    <h3 className="ws-post-title"><PostLink url={post.url} title={post.title} source={post.source} /></h3>
    <p className="ws-post-text">{post.content ?? 'Không có nội dung'}</p>
    <footer className="ws-post-foot">
      <Metric icon="likes" value={post.likes} label="Thích" />
      <Metric icon="comments" value={post.comments} label="Bình luận" />
      <span className="ws-post-action">{commentButton}</span>
    </footer>
    {children}
  </article>;
}

/** Nội dung tổng hợp lấy từ backend, chỉ hiển thị trang đã tải. */
export function AggregateContent({ api, brandId }: { api: Client; brandId: string }) {
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

  const counts = posts.reduce((acc, post) => { acc[post.sentiment ?? 'unknown'] = (acc[post.sentiment ?? 'unknown'] ?? 0) + 1; return acc; }, {} as Record<string, number>);

  return <section className="ws-split ws-split-aside">
    <form className="panel ws-aside-panel form" onSubmit={(event) => {
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
      <SectionHead level={3} title="Bộ lọc" info={<InfoTip>Thời gian theo múi giờ thiết bị; bài và bình luận thiếu thời gian đăng không hiện khi lọc theo thời gian.</InfoTip>} />
      <div className="field"><label className="field-label" htmlFor="content-source">Nền tảng</label>
        <select id="content-source" value={source} onChange={(event) => setSource(event.target.value)}><option value="">Tất cả nền tảng</option><option value="tiktok">TikTok</option><option value="demo">Dữ liệu giả lập</option></select></div>
      <label className="field"><span className="field-label">Đăng từ</span><input type="datetime-local" value={from} onChange={(event) => setFrom(event.target.value)} /></label>
      <label className="field"><span className="field-label">Đăng trước</span><input type="datetime-local" value={until} onChange={(event) => setUntil(event.target.value)} /></label>
      {filterError && <Notice tone="error">{filterError}</Notice>}
      <button className="button button-primary button-wide" disabled={loading}><Filter size={15} aria-hidden="true" />Lọc nội dung</button>
      {posts.length > 0 && <div className="ws-mix" aria-label="Cảm xúc của các bài trên trang này">
        <p className="field-label">Cảm xúc trên trang này</p>
        <div className="ws-mix-bar">{(['negative', 'neutral', 'positive', 'unknown'] as const).map((key) => counts[key] ? <span key={key} className={`ws-mix-${key}`} style={{ flexGrow: counts[key] }} title={`${counts[key]}`} /> : null)}</div>
        <p className="ws-mix-legend"><span className="text-negative">{counts.negative ?? 0} tiêu cực</span> · {counts.neutral ?? 0} trung lập · <span className="ws-text-leaf">{counts.positive ?? 0} tích cực</span>{counts.unknown ? ` · ${counts.unknown} chưa rõ` : ''}</p>
      </div>}
    </form>
    <div className="ws-stack">
      <SectionHead title="Nội dung đã thu thập"
        info={<InfoTip>Chỉ số là bản ghi gần nhất có sẵn; cảm xúc là ước tính theo nội dung hiện tại và có thể chưa được phân loại. Dữ liệu có thể chưa đầy đủ.</InfoTip>}
        actions={<button className="button button-sm" disabled={loading} onClick={() => setRevision((value) => value + 1)}><RefreshCw size={15} aria-hidden="true" />Tải lại nội dung</button>} />
      {loading && <Notice>Đang tải nội dung…</Notice>}
      {error && <Notice tone="error">Không tải được nội dung. Hãy thử tải lại.</Notice>}
      {!loading && !error && posts.length === 0 && <div className="panel ws-empty"><Inbox size={22} aria-hidden="true" /><p>Chưa có bài viết trên trang này.</p><p className="ws-muted">Bài viết xuất hiện sau khi phiên tracking thu thập xong.</p></div>}
      <div className="ws-post-grid">{posts.map((post) => <PostCard key={post.id} post={fromApiPost(post)}
        commentButton={<button className="button button-sm" disabled={commentLoading !== null} onClick={() => void loadComments(post.id, 0)}><MessageCircle size={15} aria-hidden="true" />Bình luận tổng hợp<ChevronDown size={14} aria-hidden="true" /></button>}>
        {commentLoading === post.id && <Notice>Đang tải bình luận…</Notice>}
        {commentError === post.id && <Notice tone="error">Không tải được bình luận. Hãy thử lại.</Notice>}
        {comments[post.id] && <div className="ws-comment-box"><CommentList comments={comments[post.id].map(fromApiComment)} />
          <Pager prevLabel="Bình luận trước" nextLabel="Bình luận tiếp" prevDisabled={commentLoading !== null || !(commentOffsets[post.id] > 0)} nextDisabled={commentLoading !== null || comments[post.id].length < limit}
            onPrev={() => void loadComments(post.id, Math.max(0, commentOffsets[post.id] - limit))} onNext={() => void loadComments(post.id, (commentOffsets[post.id] ?? 0) + limit)} /></div>}
      </PostCard>)}</div>
      <Pager prevLabel="Bài trước" nextLabel="Bài tiếp" prevDisabled={loading || offset === 0} nextDisabled={loading || error || posts.length < limit}
        onPrev={() => setOffset((value) => Math.max(0, value - limit))} onNext={() => setOffset((value) => value + limit)} />
    </div>
  </section>;
}
