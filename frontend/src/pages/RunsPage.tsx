import { AlertTriangle, CheckCircle2, History, XCircle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { EmptyState, RunStatusTag } from '../components/ui';
import { AttemptBar, StatTile } from '../components/viz';
import { useBrandData } from '../lib/store';
import { fmtDateTime, fmtDurationShort, fmtNum } from '../lib/format';
import { useBrandId } from './BrandLayout';

export function RunsPage() {
  const brandId = useBrandId();
  const navigate = useNavigate();
  const { runs } = useBrandData(brandId);
  const list = [...runs].reverse();

  if (list.length === 0) {
    return <EmptyState icon={<History size={28} />} title="Chưa có phiên tracking nào" />;
  }

  const n = (s: string) => runs.filter((r) => r.status === s).length;

  return (
    <div className="stack">
      <div className="stats">
        <StatTile icon={History} tone="ink" label="Tổng số phiên" value={runs.length} />
        <StatTile icon={CheckCircle2} tone="leaf" label="Thành công" value={n('success')} />
        <StatTile icon={AlertTriangle} tone="amber" label="Thành công một phần" value={n('partial')} />
        <StatTile icon={XCircle} tone="chili" label="Thất bại hoặc bỏ qua" value={n('failed') + n('skipped')} />
      </div>

      <div className="table-wrap">
        <table className="table table-click">
          <caption className="visually-hidden">Lịch sử phiên tracking, mới nhất trước</caption>
          <thead>
            <tr>
              <th scope="col">Thời gian</th>
              <th scope="col">Trạng thái</th>
              <th scope="col">Lượt có kết quả</th>
              <th scope="col" className="right">Bài viết</th>
              <th scope="col" className="right">Bình luận</th>
              <th scope="col" className="right">Tiêu cực</th>
              <th scope="col" className="right">Thời lượng</th>
            </tr>
          </thead>
          <tbody>
            {list.map((r) => {
              const hasData = r.status === 'success' || r.status === 'partial';
              return (
                <tr key={r.id} onClick={() => navigate(r.id)}>
                  <td>
                    <a
                      href={r.id}
                      className="row-link"
                      onClick={(e) => {
                        e.preventDefault();
                        navigate(r.id);
                      }}
                    >
                      {fmtDateTime(r.startedAt)}
                    </a>
                  </td>
                  <td>
                    <RunStatusTag value={r.status} />
                  </td>
                  <td>{r.attempts.length ? <AttemptBar attempts={r.attempts} /> : <span className="muted">{r.note ? 'Đã tạm dừng' : '—'}</span>}</td>
                  <td className="right num">{hasData ? fmtNum(r.posts) : '—'}</td>
                  <td className="right num">{hasData ? fmtNum(r.comments) : '—'}</td>
                  <td className="right num">{r.negativePosts === null || r.negativeComments === null ? '—' : <span className="text-negative">{r.negativePosts + r.negativeComments}</span>}</td>
                  <td className="right muted">{fmtDurationShort(r.startedAt, r.finishedAt) ?? '—'}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="legend">
        <span><i className="swatch attbar-ok" /> Có kết quả</span>
        <span><i className="swatch attbar-empty" /> Rỗng</span>
        <span><i className="swatch attbar-failed" /> Lỗi</span>
      </p>
    </div>
  );
}
