import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useStore } from '../lib/store';

// Bản thật sẽ chuyển sang Cognito (OAuth 2.0 authorization code + PKCE) theo docs/architecture_aws.md mục 5.
export function LoginPage() {
  const { signIn } = useStore();
  const navigate = useNavigate();
  const [mode, setMode] = useState<'signin' | 'signup'>('signin');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!/^\S+@\S+\.\S+$/.test(email)) return setError('Nhập email hợp lệ, ví dụ ten@congty.vn.');
    if (password.length < 8) return setError('Mật khẩu cần ít nhất 8 ký tự.');
    setError(null);
    signIn();
    navigate('/brands');
  };

  return (
    <div className="login">
      <section className="login-intro">
        <p className="wordmark wordmark-static">
          <span className="wordmark-mark" aria-hidden="true" />
          Brand Auto-Tracking
        </p>
        <h1 className="login-title">Biết người ta đang nói gì về nhãn hàng của bạn, và dữ liệu đó đủ tin đến đâu.</h1>
        <p className="login-lead">
          Tự động tìm bài viết và bình luận theo từ khóa, báo khi nội dung tiêu cực tăng, và nhờ AI tổng hợp góp ý kèm dẫn chứng.
        </p>
        <div className="login-sample" aria-hidden="true">
          {['data', 'data', 'empty', 'data', 'failed', 'data', 'data', 'partial', 'data', 'data', 'data', 'empty', 'data', 'data'].map((c, i) => (
            <i key={i} className={`cell cell-${c}`} />
          ))}
        </div>
        <p className="login-sample-caption">Ô vân gạch là phiên không lấy được dữ liệu, không bị tính là 0.</p>
      </section>

      <section className="login-panel">
        <div className="segmented" role="tablist" aria-label="Chọn thao tác">
          <button type="button" role="tab" aria-selected={mode === 'signin'} onClick={() => setMode('signin')}>
            Đăng nhập
          </button>
          <button type="button" role="tab" aria-selected={mode === 'signup'} onClick={() => setMode('signup')}>
            Tạo tài khoản
          </button>
        </div>
        <form onSubmit={submit} noValidate className="form">
          <label className="field">
            <span className="field-label">Email</span>
            <input type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          </label>
          <label className="field">
            <span className="field-label">Mật khẩu</span>
            <input
              type="password"
              autoComplete={mode === 'signin' ? 'current-password' : 'new-password'}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            {mode === 'signup' && <span className="field-hint">Ít nhất 8 ký tự.</span>}
          </label>
          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
          <button type="submit" className="button button-primary button-wide">
            {mode === 'signin' ? 'Đăng nhập' : 'Tạo tài khoản'}
          </button>
          <p className="field-hint">Bản demo: nhập email và mật khẩu bất kỳ đủ định dạng để vào bằng dữ liệu mẫu.</p>
        </form>
      </section>
    </div>
  );
}
