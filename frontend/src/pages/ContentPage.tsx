import { SearchX } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { PostItem } from '../components/PostItem';
import { EmptyState, PlatformTag } from '../components/ui';
import { InfoTip } from '../components/viz';
import { NOW } from '../data/mock';
import type { PlatformId, Sentiment } from '../data/types';
import { useBrandData } from '../lib/store';
import { useBrandId } from './BrandLayout';

const RANGES = [
  { id: '7', label: '7 ngày', days: 7 },
  { id: '14', label: '14 ngày', days: 14 },
  { id: 'all', label: 'Tất cả', days: Infinity },
] as const;

const SENTIMENTS: { id: Sentiment | 'all'; label: string }[] = [
  { id: 'all', label: 'Tất cả' },
  { id: 'negative', label: 'Tiêu cực' },
  { id: 'neutral', label: 'Trung lập' },
  { id: 'positive', label: 'Tích cực' },
  { id: 'unknown', label: 'Chưa rõ' },
];

type SortKey = 'reacts' | 'recent';

export function ContentPage() {
  const brandId = useBrandId();
  const { brand, posts } = useBrandData(brandId);
  const location = useLocation();
  const targetId = location.hash.slice(1);

  const [range, setRange] = useState<(typeof RANGES)[number]['id']>('14');
  const [platforms, setPlatforms] = useState<PlatformId[]>(brand?.platforms ?? []);
  const [sentiment, setSentiment] = useState<Sentiment | 'all'>('all');
  const [sort, setSort] = useState<SortKey>('reacts');

  useEffect(() => {
    if (!targetId) return;
    const el = document.getElementById(targetId);
    el?.closest('.post')?.querySelector('details')?.setAttribute('open', '');
    el?.scrollIntoView({ block: 'center' });
  }, [targetId]);

  const inRange = useMemo(() => {
    const days = RANGES.find((r) => r.id === range)!.days;
    const since = Date.parse(NOW) - days * 86_400_000;
    return posts.filter((p) => Date.parse(p.firstSeenAt) >= since);
  }, [posts, range]);

  const visible = useMemo(
    () =>
      inRange
        .filter((p) => platforms.includes(p.platform))
        .filter((p) => sentiment === 'all' || p.sentiment === sentiment)
        .sort((a, b) => (sort === 'reacts' ? (b.reacts ?? -1) - (a.reacts ?? -1) : b.firstSeenAt.localeCompare(a.firstSeenAt))),
    [inRange, platforms, sentiment, sort],
  );

  if (!brand) return null;

  const count = (s: Sentiment | 'all') => inRange.filter((p) => platforms.includes(p.platform) && (s === 'all' || p.sentiment === s)).length;
  const togglePlatform = (id: PlatformId) => setPlatforms((list) => (list.includes(id) ? list.filter((x) => x !== id) : [...list, id]));

  return (
    <div className="with-aside">
      <aside className="filter-panel" aria-label="Bộ lọc">
        <div className="filter-group">
          <p className="filter-title">Thời gian thu thập</p>
          <div className="segmented segmented-full">
            {RANGES.map((r) => (
              <button key={r.id} type="button" aria-pressed={range === r.id} onClick={() => setRange(r.id)}>
                {r.label}
              </button>
            ))}
          </div>
        </div>

        <div className="filter-group">
          <p className="filter-title">Nền tảng</p>
          <div className="option-list">
            {brand.platforms.map((p) => (
              <label key={p} className="option">
                <input type="checkbox" checked={platforms.includes(p)} onChange={() => togglePlatform(p)} />
                <PlatformTag id={p} />
                <span className="option-count">{inRange.filter((x) => x.platform === p).length}</span>
              </label>
            ))}
          </div>
        </div>

        <div className="filter-group">
          <p className="filter-title">Cảm xúc</p>
          <div className="option-list">
            {SENTIMENTS.map((s) => (
              <label key={s.id} className={`option option-radio sent-opt-${s.id}`}>
                <input type="radio" name="sentiment" checked={sentiment === s.id} onChange={() => setSentiment(s.id)} />
                <span className="option-label">{s.label}</span>
                <span className="option-count">{count(s.id)}</span>
              </label>
            ))}
          </div>
        </div>
      </aside>

      <div className="with-aside-main">
        <div className="list-head">
          <p className="list-count">
            <strong>{visible.length}</strong> bài viết
            <InfoTip>Mỗi bài chỉ hiện một lần dù xuất hiện ở nhiều phiên. Chỉ số lấy theo lần thu thập mới nhất. Ô gạch chéo là dữ liệu nguồn không cung cấp.</InfoTip>
          </p>
          <label className="inline-select">
            <span>Sắp xếp</span>
            <select value={sort} onChange={(e) => setSort(e.target.value as SortKey)}>
              <option value="reacts">Nhiều react</option>
              <option value="recent">Mới nhất</option>
            </select>
          </label>
        </div>

        {visible.length === 0 ? (
          <EmptyState icon={<SearchX size={28} />} title="Không có bài phù hợp">
            Thử mở rộng thời gian hoặc chọn thêm nền tảng.
          </EmptyState>
        ) : (
          <div className="post-grid">
            {visible.map((p) => (
              <PostItem key={p.id} post={p} highlight={p.id === targetId || p.comments.some((c) => c.id === targetId)} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
