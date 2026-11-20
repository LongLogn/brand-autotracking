import { useRef, useState, type FormEvent, type KeyboardEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { NOW, PLATFORMS } from '../data/mock';
import type { Brand, Frequency, PlatformId } from '../data/types';
import { useBrandData, useStore } from '../lib/store';
import { FREQUENCY_LABEL } from '../lib/format';
import { useBrandId } from './BrandLayout';

const MAX_POSTS = 50;
const SUPPORT_LABEL = { verified: 'Đã kiểm chứng', experimental: 'Thử nghiệm', unsupported: 'Chưa hỗ trợ' } as const;

type Errors = Partial<Record<'name' | 'keywords' | 'platforms' | 'postLimit' | 'runTime', string>>;

function validate(b: Brand): Errors {
  const e: Errors = {};
  if (!b.name.trim()) e.name = 'Nhập tên nhãn hàng.';
  if (b.keywords.length === 0) e.keywords = 'Thêm ít nhất một từ khóa.';
  if (b.platforms.length === 0) e.platforms = 'Chọn ít nhất một nền tảng.';
  if (!Number.isInteger(b.postLimit) || b.postLimit < 1 || b.postLimit > MAX_POSTS)
    e.postLimit = `Nhập số nguyên từ 1 đến ${MAX_POSTS}.`;
  if (!/^\d{2}:\d{2}$/.test(b.runTime)) e.runTime = 'Chọn giờ chạy.';
  return e;
}

function slug(s: string) {
  return (
    s
      .normalize('NFD')
      .replace(/[̀-ͯ]/g, '')
      .replace(/đ/gi, 'd')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '') || 'nhan-hang'
  );
}

function BrandForm({ initial, isNew }: { initial: Brand; isNew: boolean }) {
  const { saveBrand, deleteBrand, notify, brands } = useStore();
  const navigate = useNavigate();
  const [b, setB] = useState(initial);
  const [kw, setKw] = useState('');
  const [errors, setErrors] = useState<Errors>({});
  const dialog = useRef<HTMLDialogElement>(null);
  const set = <K extends keyof Brand>(k: K, v: Brand[K]) => setB((x) => ({ ...x, [k]: v }));

  const addKeyword = () => {
    const v = kw.trim().replace(/\s+/g, ' ');
    if (!v) return;
    if (b.keywords.some((k) => k.toLowerCase() === v.toLowerCase())) {
      notify(`Từ khóa “${v}” đã có trong danh sách.`, 'error');
      return;
    }
    set('keywords', [...b.keywords, v]);
    setKw('');
  };
  const onKwKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      addKeyword();
    }
  };

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const errs = validate(b);
    setErrors(errs);
    if (Object.keys(errs).length) {
      notify('Cấu hình chưa hợp lệ. Sửa các ô được đánh dấu rồi lưu lại.', 'error');
      return;
    }
    // Trạng thái bật/tạm dừng của nhãn hàng có sẵn được đổi ở đầu trang, không ghi đè từ form.
    const current = brands.find((x) => x.id === b.id);
    let saved = current ? { ...b, active: current.active, nextRunAt: current.nextRunAt } : b;
    if (isNew) {
      let id = slug(b.name);
      while (brands.some((x) => x.id === id)) id += '-2';
      saved = { ...b, id, nextRunAt: b.active ? new Date(Date.parse(NOW) + 86_400_000).toISOString() : null };
    }
    saveBrand(saved);
    notify(isNew ? `Đã tạo ${saved.name}. Phiên đầu tiên chạy theo lịch đã chọn.` : 'Đã lưu cấu hình. Thay đổi áp dụng từ phiên bắt đầu sau thời điểm này.');
    if (isNew) navigate(`/brands/${saved.id}`);
  };

  return (
    <form className="form settings" onSubmit={submit} noValidate>
      <section className="settings-group" aria-labelledby="g-brand">
        <h2 id="g-brand" className="subsection-title">
          Nhãn hàng
        </h2>
        <label className="field">
          <span className="field-label">Tên nhãn hàng</span>
          <input value={b.name} onChange={(e) => set('name', e.target.value)} aria-invalid={!!errors.name} placeholder="Ví dụ: Gà rán ABC" />
          {errors.name && <span className="field-error">{errors.name}</span>}
        </label>
        <label className="field">
          <span className="field-label">Mô tả ngắn</span>
          <input value={b.description} onChange={(e) => set('description', e.target.value)} placeholder="Không bắt buộc" />
        </label>
      </section>

      <section className="settings-group" aria-labelledby="g-kw">
        <h2 id="g-kw" className="subsection-title">
          Từ khóa
        </h2>
        <p className="field-hint">Thêm cả bản có dấu, không dấu và tên viết tắt.</p>
        <ul className="keyword-list" aria-label="Từ khóa đã thêm">
          {b.keywords.map((k) => (
            <li key={k} className="keyword">
              {k}
              <button type="button" className="keyword-remove" aria-label={`Xóa từ khóa ${k}`} onClick={() => set('keywords', b.keywords.filter((x) => x !== k))}>
                ×
              </button>
            </li>
          ))}
        </ul>
        <div className="inline-add">
          <label className="visually-hidden" htmlFor="kw-input">
            Từ khóa mới
          </label>
          <input id="kw-input" value={kw} onChange={(e) => setKw(e.target.value)} onKeyDown={onKwKey} placeholder="Gõ từ khóa rồi nhấn Enter" aria-invalid={!!errors.keywords} />
          <button type="button" className="button" onClick={addKeyword}>
            Thêm từ khóa
          </button>
        </div>
        {errors.keywords && <span className="field-error">{errors.keywords}</span>}
      </section>

      <section className="settings-group" aria-labelledby="g-pf">
        <h2 id="g-pf" className="subsection-title">
          Nền tảng
        </h2>
        <ul className="platform-options">
          {PLATFORMS.map((p) => {
            const disabled = p.support === 'unsupported';
            const checked = b.platforms.includes(p.id);
            return (
              <li key={p.id}>
                <label className={disabled ? 'platform-option platform-option-off' : 'platform-option'}>
                  <input
                    type="checkbox"
                    checked={checked}
                    disabled={disabled}
                    onChange={() => set('platforms', checked ? b.platforms.filter((x) => x !== p.id) : ([...b.platforms, p.id] as PlatformId[]))}
                  />
                  <span className="platform-option-text">
                    <span className="platform-option-name">
                      {p.name}
                      <span className={`support support-${p.support}`}>{SUPPORT_LABEL[p.support]}</span>
                    </span>
                    <span className="platform-option-note">{p.note}</span>
                  </span>
                </label>
              </li>
            );
          })}
        </ul>
        {errors.platforms && <span className="field-error">{errors.platforms}</span>}
      </section>

      <section className="settings-group" aria-labelledby="g-sched">
        <h2 id="g-sched" className="subsection-title">
          Lịch và giới hạn
        </h2>
        <div className="form-grid">
          <label className="field">
            <span className="field-label">Tần suất</span>
            <select value={b.frequency} onChange={(e) => set('frequency', e.target.value as Frequency)}>
              {(Object.keys(FREQUENCY_LABEL) as Frequency[]).map((f) => (
                <option key={f} value={f}>
                  {FREQUENCY_LABEL[f]}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span className="field-label">Giờ chạy</span>
            <input type="time" value={b.runTime} onChange={(e) => set('runTime', e.target.value)} aria-invalid={!!errors.runTime} />
            {errors.runTime && <span className="field-error">{errors.runTime}</span>}
          </label>
          <label className="field">
            <span className="field-label">Múi giờ</span>
            <select value={b.timezone} onChange={(e) => set('timezone', e.target.value)}>
              <option value="Asia/Ho_Chi_Minh">Giờ Việt Nam (UTC+7)</option>
            </select>
          </label>
          <label className="field">
            <span className="field-label">Số bài nổi bật mỗi lượt</span>
            <input
              type="number"
              min={1}
              max={MAX_POSTS}
              inputMode="numeric"
              value={Number.isNaN(b.postLimit) ? '' : b.postLimit}
              onChange={(e) => set('postLimit', e.target.value === '' ? NaN : Number(e.target.value))}
              aria-invalid={!!errors.postLimit}
            />
            {errors.postLimit ? (
              <span className="field-error">{errors.postLimit}</span>
            ) : (
              <span className="field-hint">
                Mỗi cặp nền tảng × từ khóa, tối đa {Number.isInteger(b.postLimit) ? b.postLimit * b.keywords.length * b.platforms.length : 0} bài mỗi phiên.
              </span>
            )}
          </label>
        </div>
        {isNew && (
          <label className="switch">
            <input type="checkbox" role="switch" checked={b.active} onChange={(e) => set('active', e.target.checked)} />
            <span>{b.active ? 'Bắt đầu theo dõi ngay sau khi tạo' : 'Tạo ở trạng thái tạm dừng'}</span>
          </label>
        )}
      </section>

      <div className="form-actions sticky-actions">
        <button type="submit" className="button button-primary">
          {isNew ? 'Tạo nhãn hàng' : 'Lưu cấu hình'}
        </button>
        {!isNew && <span className="field-hint">Áp dụng từ phiên kế tiếp.</span>}
      </div>

      {!isNew && (
        <section className="settings-group danger" aria-labelledby="g-danger">
          <h2 id="g-danger" className="subsection-title">
            Xóa nhãn hàng
          </h2>
          <p className="field-hint">Dừng lịch và xóa khỏi danh sách. Chính sách xóa lịch sử chờ nhóm chốt.</p>
          <button type="button" className="button button-danger" onClick={() => dialog.current?.showModal()}>
            Xóa {initial.name}
          </button>
          <dialog ref={dialog} className="dialog" aria-labelledby="dlg-title">
            <h2 id="dlg-title" className="section-title">
              Xóa {initial.name}?
            </h2>
            <p>Lịch theo dõi sẽ dừng ngay. Thao tác này không hoàn tác được.</p>
            <div className="form-actions">
              <button
                type="button"
                className="button button-danger"
                onClick={() => {
                  dialog.current?.close();
                  deleteBrand(initial.id);
                  notify(`Đã xóa ${initial.name}.`);
                  navigate('/brands');
                }}
              >
                Xóa nhãn hàng
              </button>
              <button type="button" className="button" onClick={() => dialog.current?.close()}>
                Giữ lại
              </button>
            </div>
          </dialog>
        </section>
      )}
    </form>
  );
}

export function SettingsPage() {
  const { brand } = useBrandData(useBrandId());
  if (!brand) return null;
  return <BrandForm key={brand.id} initial={brand} isNew={false} />;
}

export function NewBrandPage() {
  const blank: Brand = {
    id: '',
    name: '',
    description: '',
    keywords: [],
    platforms: ['reddit'],
    frequency: 'daily',
    runTime: '08:00',
    timezone: 'Asia/Ho_Chi_Minh',
    postLimit: 10,
    active: true,
    nextRunAt: null,
  };
  return (
    <div className="page">
      <header className="page-head">
        <h1 className="page-title">Thêm nhãn hàng</h1>
      </header>
      <BrandForm initial={blank} isNew />
    </div>
  );
}
