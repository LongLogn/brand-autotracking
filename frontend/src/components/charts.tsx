import { Link } from 'react-router-dom';
import type { PlatformId, Run } from '../data/types';
import { platformName } from '../data/mock';
import { fmtDay, fmtWeekday } from '../lib/format';

type Cell = 'data' | 'empty' | 'partial' | 'failed' | 'none';

const CELL_LABEL: Record<Cell, string> = {
  data: 'có dữ liệu',
  empty: 'chạy xong, không có kết quả',
  partial: 'một số từ khóa bị lỗi',
  failed: 'lỗi, không có dữ liệu',
  none: 'không chạy',
};

function cellFor(run: Run, platform: PlatformId): Cell {
  const attempts = run.attempts.filter((a) => a.platform === platform);
  if (attempts.length === 0) return 'none';
  const failed = attempts.filter((a) => a.status === 'failed').length;
  if (failed === attempts.length) return 'failed';
  if (failed > 0) return 'partial';
  return attempts.some((a) => a.status === 'success') ? 'data' : 'empty';
}

/** Dải bao phủ: mỗi cột là một phiên, mỗi hàng là một nền tảng. */
export function CoverageStrip({ runs, platforms, brandId }: { runs: Run[]; platforms: PlatformId[]; brandId: string }) {
  return (
    <figure className="coverage">
      <div className="coverage-grid" style={{ ['--cols' as string]: runs.length }}>
        {platforms.map((p) => (
          <div className="coverage-row" key={p} role="row">
            <span className="coverage-platform">{platformName(p)}</span>
            {runs.map((r) => {
              const c = cellFor(r, p);
              return (
                <Link
                  key={r.id}
                  to={`/brands/${brandId}/runs/${r.id}`}
                  className={`cell cell-${c}`}
                  aria-label={`${platformName(p)} ngày ${fmtDay(r.startedAt)}: ${CELL_LABEL[c]}`}
                  title={`${platformName(p)}, ${fmtDay(r.startedAt)}: ${CELL_LABEL[c]}`}
                />
              );
            })}
          </div>
        ))}
        <div className="coverage-row coverage-days" aria-hidden="true">
          <span />
          {runs.map((r, i) => (
            <span key={r.id} className={i % 2 === 1 ? 'day day-odd' : 'day'}>
              {fmtDay(r.startedAt)}
            </span>
          ))}
        </div>
      </div>
      <figcaption className="legend">
        <span><i className="swatch cell-data" /> Có dữ liệu</span>
        <span><i className="swatch cell-empty" /> Không có kết quả</span>
        <span><i className="swatch cell-partial" /> Lỗi một phần</span>
        <span><i className="swatch cell-failed" /> Lỗi, không có dữ liệu</span>
      </figcaption>
    </figure>
  );
}

/** Cột số nội dung tiêu cực theo phiên, chia làm hai cửa sổ so sánh. Phiên không có số liệu được vẽ vân gạch. */
export function NegativeTrend({ runs, pick, windowDays, unit }: { runs: Run[]; pick: (r: Run) => number | null; windowDays: number; unit: string }) {
  const values = runs.map(pick);
  const max = Math.max(1, ...values.map((v) => v ?? 0));
  const split = Math.max(0, runs.length - windowDays);
  const sum = (from: number, to: number) => {
    const slice = values.slice(from, to);
    return slice.some((v) => v === null) ? null : slice.reduce<number>((a, v) => a + (v ?? 0), 0);
  };
  const prev = split > 0 ? sum(Math.max(0, split - windowDays), split) : null;
  const curr = sum(split, runs.length);

  return (
    <figure className="trend">
      <div className="trend-windows" style={{ gridTemplateColumns: `minmax(0, ${split}fr) minmax(0, ${runs.length - split}fr)` }}>
        {split > 0 && (
          <div className="trend-window">
            <span className="trend-window-label">{windowDays} ngày trước đó</span>
            <span className="trend-window-total">{prev === null ? 'Thiếu dữ liệu' : `${prev} ${unit}`}</span>
          </div>
        )}
        <div className="trend-window trend-window-current">
          <span className="trend-window-label">{windowDays} ngày gần nhất</span>
          <span className="trend-window-total">{curr === null ? 'Thiếu dữ liệu' : `${curr} ${unit}`}</span>
        </div>
      </div>
      <div className="trend-bars" role="list">
        {runs.map((r, i) => {
          const v = values[i];
          return (
            <div key={r.id} className={`trend-col${i < split ? ' trend-col-prev' : ''}${i === split ? ' trend-col-split' : ''}`} role="listitem" aria-label={`${fmtDay(r.startedAt)}: ${v === null ? 'không có số liệu' : `${v} ${unit}`}`}>
              <span className="trend-value">{v ?? ''}</span>
              <span className={v === null ? 'trend-bar trend-bar-na' : 'trend-bar'} style={{ height: v === null ? '100%' : `${(v / max) * 100}%` }} />
              <span className="trend-day">
                <span className="trend-weekday">{fmtWeekday(r.startedAt)}</span>
                {fmtDay(r.startedAt)}
              </span>
            </div>
          );
        })}
      </div>
    </figure>
  );
}
