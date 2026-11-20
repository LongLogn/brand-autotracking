import { CalendarClock, Copy, ExternalLink, Heart, History, MessageCircle } from 'lucide-react';
import type { Post } from '../data/types';
import { fmtDateTime } from '../lib/format';
import { Num, PlatformTag, SentimentTag, Unavailable } from './ui';

export function PostItem({ post, highlight }: { post: Post; highlight?: boolean }) {
  // Bình luận nổi bật: sắp theo react giảm dần, bình luận thiếu react xếp cuối (SRS 10.1).
  const comments = [...post.comments].sort((a, b) => (b.reacts ?? -1) - (a.reacts ?? -1));

  return (
    <article id={post.id} className={`post post-${post.sentiment}${highlight ? ' post-highlight' : ''}`}>
      <header className="post-head">
        <PlatformTag id={post.platform} />
        <SentimentTag value={post.sentiment} />
        {post.maybeDuplicate && (
          <span className="flag" title="Nguồn không có định danh ổn định, bài này có thể bị trùng.">
            <Copy size={13} aria-hidden="true" />
            Có thể trùng
          </span>
        )}
        <a href={post.url} target="_blank" rel="noreferrer noopener" className="icon-button post-open" aria-label="Mở bài gốc" title="Mở bài gốc">
          <ExternalLink size={16} aria-hidden="true" />
        </a>
      </header>
      <h3 className="post-title">{post.title}</h3>
      <p className="post-text">{post.text}</p>

      <ul className="post-stats">
        <li title="Số react">
          <Heart size={15} aria-hidden="true" />
          <Num value={post.reacts} />
        </li>
        <li title="Số bình luận">
          <MessageCircle size={15} aria-hidden="true" />
          <Num value={post.commentCount} />
        </li>
        <li title="Thời gian đăng">
          <CalendarClock size={15} aria-hidden="true" />
          {post.postedAt ? fmtDateTime(post.postedAt) : <Unavailable />}
        </li>
        <li title={`Từ khóa: ${post.keywords.join(', ')}`}>
          <History size={15} aria-hidden="true" />
          {post.runIds.length} phiên
        </li>
      </ul>

      {comments.length > 0 && (
        <details className="comments">
          <summary>{comments.length} bình luận nổi bật</summary>
          <ol className="comment-list">
            {comments.map((c) => (
              <li key={c.id} id={c.id} className={`comment comment-${c.sentiment}`}>
                <p className="comment-text">{c.text}</p>
                <p className="comment-meta">
                  <SentimentTag value={c.sentiment} />
                  <span className="meta-item">
                    <Heart size={13} aria-hidden="true" />
                    <Num value={c.reacts} />
                  </span>
                </p>
              </li>
            ))}
          </ol>
        </details>
      )}
    </article>
  );
}
