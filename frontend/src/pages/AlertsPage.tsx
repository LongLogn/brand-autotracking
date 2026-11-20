import { BellOff, BellRing, CircleSlash, MessageSquareWarning, Pencil, Plus, ThumbsDown, TrendingUp } from 'lucide-react';
import { useEffect, useState, type FormEvent } from 'react';
import { EmptyState, Panel } from '../components/ui';
import { InfoTip } from '../components/viz';
import type { AlertMetric, AlertRule } from '../data/types';
import { useBrandData, useStore } from '../lib/store';
import { fmtDateTime, METRIC_LABEL, METRIC_UNIT } from '../lib/format';
import { useBrandId } from './BrandLayout';

function RuleChips({ rule }: { rule: AlertRule }) {
  const unit = METRIC_UNIT[rule.metric];
  return (
    <ul className="rule-chips">
      <li title="Mức tăng tối thiểu so với kỳ trước">
        <TrendingUp size={14} aria-hidden="true" />
        Tăng từ {rule.growthPercent}%
      </li>
      <li title="Số lượng tối thiểu trong kỳ này">Ít nhất {rule.minCount} {unit}</li>
      <li title="Độ dài mỗi cửa sổ so sánh">Cửa sổ {rule.windowDays} ngày</li>
      <li title="Khi kỳ trước bằng 0" className={rule.absoluteThreshold === null ? 'chip-off' : ''}>
        Kỳ trước = 0: {rule.absoluteThreshold === null ? 'bỏ qua' : `báo khi đạt ${rule.absoluteThreshold}`}
      </li>
    </ul>
  );
}

function RuleForm({ initial, onDone }: { initial: AlertRule; onDone: () => void }) {
  const { saveRule, notify } = useStore();
  const [r, setR] = useState(initial);
  const [error, setError] = useState<string | null>(null);
  const set = <K extends keyof AlertRule>(k: K, v: AlertRule[K]) => setR((x) => ({ ...x, [k]: v }));
  const num = (s: string) => (s.trim() === '' ? NaN : Number(s));
  const show = (n: number) => (Number.isNaN(n) ? '' : n);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if ([r.windowDays, r.growthPercent, r.minCount].some((n) => !Number.isInteger(n) || n <= 0)) return setError('Các ô số phải là số nguyên dương.');
    if (r.absoluteThreshold !== null && (!Number.isInteger(r.absoluteThreshold) || r.absoluteThreshold <= 0)) return setError('Ngưỡng khi kỳ trước bằng 0 phải là số nguyên dương hoặc để trống.');
    saveRule(r);
    notify('Đã lưu quy tắc.');
    onDone();
  };

  return (
    <form className="rule-form form" onSubmit={submit} noValidate>
      <div className="form-grid form-grid-tight">
        <label className="field">
          <span className="field-label">Chỉ số</span>
          <select value={r.metric} onChange={(e) => set('metric', e.target.value as AlertMetric)}>
            <option value="negative-comments">{METRIC_LABEL['negative-comments']}</option>
            <option value="negative-posts">{METRIC_LABEL['negative-posts']}</option>
          </select>
        </label>
        <label className="field">
          <span className="field-label">Tăng từ (%)</span>
          <input type="number" min={1} inputMode="numeric" value={show(r.growthPercent)} onChange={(e) => set('growthPercent', num(e.target.value))} />
        </label>
        <label className="field">
          <span className="field-label">Ít nhất</span>
          <input type="number" min={1} inputMode="numeric" value={show(r.minCount)} onChange={(e) => set('minCount', num(e.target.value))} />
        </label>
        <label className="field">
          <span className="field-label">Cửa sổ (ngày)</span>
          <input type="number" min={1} inputMode="numeric" value={show(r.windowDays)} onChange={(e) => set('windowDays', num(e.target.value))} />
        </label>
        <label className="field">
          <span className="field-label">
            Khi kỳ trước = 0
            <InfoTip>Không thể tính phần trăm khi kỳ trước bằng 0. Đặt số lượng để vẫn báo, hoặc để trống để chỉ ghi nhận là không đủ cơ sở.</InfoTip>
          </span>
          <input type="number" min={1} inputMode="numeric" placeholder="Bỏ qua" value={r.absoluteThreshold ?? ''} onChange={(e) => set('absoluteThreshold', e.target.value === '' ? null : Number(e.target.value))} />
        </label>
      </div>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      <div className="form-actions">
        <button type="submit" className="button button-primary">
          Lưu
        </button>
        <button type="button" className="button" onClick={onDone}>
          Hủy
        </button>
      </div>
    </form>
  );
}

export function AlertsPage() {
  const brandId = useBrandId();
  const { rules, alerts } = useBrandData(brandId);
  const { saveRule, markAlertsRead, notify } = useStore();
  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState<AlertRule | null>(null);

  useEffect(() => {
    const t = window.setTimeout(() => markAlertsRead(brandId), 1500);
    return () => window.clearTimeout(t);
  }, [brandId]);

  const history = [...alerts].sort((a, b) => b.createdAt.localeCompare(a.createdAt));

  return (
    <div className="two-col">
      <Panel
        title="Quy tắc"
        info={<InfoTip>Đánh giá sau mỗi phiên, chỉ khi hai cửa sổ có độ bao phủ tương đương. Mỗi cửa sổ tạo tối đa một cảnh báo. Hiện chỉ báo trong ứng dụng.</InfoTip>}
        action={
          <button
            type="button"
            className="button button-sm"
            onClick={() => {
              setEditing(null);
              setDraft({ id: `rule-${Date.now()}`, brandId, metric: 'negative-comments', windowDays: 7, growthPercent: 50, minCount: 5, absoluteThreshold: null, enabled: true });
            }}
          >
            <Plus size={15} aria-hidden="true" />
            Thêm
          </button>
        }
      >
        {draft && (
          <div className="rule rule-editing">
            <RuleForm initial={draft} onDone={() => setDraft(null)} />
          </div>
        )}
        {rules.length === 0 && !draft ? (
          <EmptyState icon={<BellOff size={28} />} title="Chưa có quy tắc nào" />
        ) : (
          <ul className="rule-list">
            {rules.map((r) => {
              const Icon = r.metric === 'negative-comments' ? MessageSquareWarning : ThumbsDown;
              return (
                <li key={r.id} className={`rule${r.enabled ? '' : ' rule-off'}${editing === r.id ? ' rule-editing' : ''}`}>
                  {editing === r.id ? (
                    <RuleForm initial={r} onDone={() => setEditing(null)} />
                  ) : (
                    <>
                      <div className="rule-top">
                        <span className="rule-icon">
                          <Icon size={18} aria-hidden="true" />
                        </span>
                        <span className="rule-name">{METRIC_LABEL[r.metric]}</span>
                        <label className="switch" title={r.enabled ? 'Đang bật' : 'Đang tắt'}>
                          <input
                            type="checkbox"
                            role="switch"
                            aria-label={`Bật quy tắc ${METRIC_LABEL[r.metric]}`}
                            checked={r.enabled}
                            onChange={() => {
                              saveRule({ ...r, enabled: !r.enabled });
                              notify(r.enabled ? 'Đã tắt quy tắc.' : 'Đã bật quy tắc.');
                            }}
                          />
                        </label>
                        <button type="button" className="icon-button" aria-label="Sửa quy tắc" title="Sửa" onClick={() => setEditing(r.id)}>
                          <Pencil size={16} aria-hidden="true" />
                        </button>
                      </div>
                      <RuleChips rule={r} />
                    </>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </Panel>

      <Panel title="Lịch sử">
        {history.length === 0 ? (
          <EmptyState icon={<BellOff size={28} />} title="Chưa có cảnh báo nào" />
        ) : (
          <ol className="timeline">
            {history.map((a) => (
              <li key={a.id} className={`tl-item tl-${a.kind}${a.read ? '' : ' tl-unread'}`}>
                <span className="tl-icon" aria-hidden="true">
                  {a.kind === 'triggered' ? <BellRing size={16} /> : <CircleSlash size={16} />}
                </span>
                <div className="tl-body">
                  <div className="tl-head">
                    <span className="tl-kind">{a.kind === 'triggered' ? 'Đã cảnh báo' : 'Không đủ cơ sở'}</span>
                    <span className="muted">{fmtDateTime(a.createdAt)}</span>
                    {!a.read && <span className="tab-count">Mới</span>}
                  </div>
                  <p className="tl-reason">{a.reason}</p>
                  <div className="compare">
                    <div className="compare-box">
                      <span className="compare-key">Kỳ trước</span>
                      <span className="compare-val">{a.previous ?? <span className="na">Không có</span>}</span>
                    </div>
                    <TrendingUp size={18} className="compare-arrow" aria-hidden="true" />
                    <div className="compare-box compare-now">
                      <span className="compare-key">Kỳ này</span>
                      <span className="compare-val">{a.current ?? <span className="na">Không có</span>}</span>
                    </div>
                    <div className={`compare-growth${a.kind === 'triggered' ? ' is-hot' : ''}`}>
                      {a.growthPercent === null ? 'Không tính %' : `+${a.growthPercent}%`}
                    </div>
                  </div>
                  <p className="tl-foot muted">
                    {METRIC_LABEL[a.metric]}, {a.windowLabel}
                  </p>
                </div>
              </li>
            ))}
          </ol>
        )}
      </Panel>
    </div>
  );
}
