import { ArrowLeft, Clock, FileText, MessageCircle, Target, XCircle } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { PostItem } from '../components/PostItem';
import { EmptyState, Panel, PlatformTag, RunStatusTag } from '../components/ui';
import { InfoTip, StatTile } from '../components/viz';
import { useBrandData } from '../lib/store';
import { fmtDateTime, fmtDurationShort } from '../lib/format';
import { useBrandId } from './BrandLayout';

export function RunDetailPage() {
  const brandId = useBrandId();
  const { runId } = useParams();
  const { runs, posts } = useBrandData(brandId);
  const run = runs.find((r) => r.id === runId);

  if (!run) {
    return (
      <EmptyState title="Không tìm thấy phiên này" action={<Link to=".." relative="path" className="button">Về danh sách phiên</Link>} />
    );
  }

  const found = posts.filter((p) => p.runIds.includes(run.id));
  const platforms = [...new Set(run.attempts.map((a) => a.platform))];
  const keywords = [...new Set(run.attempts.map((a) => a.keyword))];
  const errors = [...new Set(run.attempts.filter((a) => a.error).map((a) => `${a.platform}|${a.error}`))].map((k) => {
    const [platform, msg] = k.split('|');
    return { platform: platform as (typeof platforms)[number], msg, count: run.attempts.filter((a) => a.platform === platform && a.error === msg).length };
  });

  return (
    <div className="stack">
      <div className="run-head">
        <Link to=".." relative="path" className="icon-button" aria-label="Về danh sách phiên" title="Về danh sách phiên">
          <ArrowLeft size={18} aria-hidden="true" />
        </Link>
        <h2 className="section-title">Phiên {fmtDateTime(run.startedAt)}</h2>
        <RunStatusTag value={run.status} />
      </div>

      <div className="stats">
        <StatTile icon={FileText} tone="action" label="Bài viết" value={run.posts} />
        <StatTile icon={MessageCircle} tone="action" label="Bình luận" value={run.comments} />
        <StatTile icon={Target} tone="ink" label="Giới hạn mỗi lượt" value={run.postLimit} unit=" bài" />
        <StatTile icon={Clock} tone="ink" label="Thời lượng" value={fmtDurationShort(run.startedAt, run.finishedAt) ?? '—'} unit=" phút" />
      </div>

      {run.note && <p className="callout">{run.note}</p>}

      {run.attempts.length > 0 && (
        <Panel title="Kết quả từng lượt" info={<InfoTip>Mỗi ô là một lượt tìm kiếm: một nền tảng với một từ khóa. Số trong ô là số bài lấy được trên giới hạn. Ô viền đứt là lượt chạy xong nhưng không có bài, khác với ô lỗi.</InfoTip>}>
          <div className="matrix-wrap">
            <table className="matrix">
              <thead>
                <tr>
                  <th scope="col">
                    <span className="visually-hidden">Nền tảng</span>
                  </th>
                  {keywords.map((k) => (
                    <th key={k} scope="col">
                      “{k}”
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {platforms.map((p) => (
                  <tr key={p}>
                    <th scope="row">
                      <PlatformTag id={p} />
                    </th>
                    {keywords.map((k) => {
                      const a = run.attempts.find((x) => x.platform === p && x.keyword === k);
                      if (!a) return <td key={k} />;
                      return (
                        <td key={k}>
                          <span className={`mcell mcell-${a.status}`} title={a.error ?? undefined}>
                            {a.status === 'failed' ? (
                              <>
                                <XCircle size={16} aria-hidden="true" /> Lỗi
                              </>
                            ) : (
                              <>
                                <strong>{a.results}</strong>/{run.postLimit}
                              </>
                            )}
                            <span className="mcell-bar" style={{ width: `${a.status === 'failed' ? 0 : (a.results / run.postLimit) * 100}%` }} />
                          </span>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {errors.length > 0 && (
            <ul className="error-list">
              {errors.map((e) => (
                <li key={e.platform + e.msg}>
                  <XCircle size={16} aria-hidden="true" />
                  <PlatformTag id={e.platform} compact />
                  <span>
                    {e.msg} <span className="muted">({e.count} lượt)</span>
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      )}

      <Panel title={`Nội dung tìm thấy (${found.length})`}>
        {found.length === 0 ? (
          <p className="muted">Dữ liệu mẫu không có bài chi tiết cho phiên này.</p>
        ) : (
          <div className="post-grid">
            {found.map((p) => (
              <PostItem key={p.id} post={p} />
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}
