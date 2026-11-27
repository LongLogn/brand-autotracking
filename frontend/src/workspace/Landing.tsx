import { BellRing, Mail, MessageCircle, Search, ShieldCheck, Sparkles } from 'lucide-react';
import { useId, type FormEvent, type ReactNode } from 'react';
import './landing.css';

/** Logo: bong bóng bình luận có nhịp tín hiệu và chấm đỏ thông báo. */
export function LogoMark({ size = 32 }: { size?: number }) {
  const gid = `logo-${useId().replace(/:/g, '')}`;
  return <svg className="lp-mark" width={size} height={size} viewBox="0 0 64 64" aria-hidden="true">
    <defs><linearGradient id={gid} x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#8FE0B3" /><stop offset="1" stopColor="#4FB884" /></linearGradient></defs>
    <rect width="64" height="64" rx="18" fill={`url(#${gid})`} />
    <path d="M32 12c11 0 20 8 20 18.5S43 49 32 49c-2.6 0-5-.4-7.3-1.2L15 52l3-8.4c-3.2-3.4-6-8-6-13.1C12 20 21 12 32 12z" fill="#13261F" />
    <polyline points="20,31 26,31 29.5,24.5 34,37 37.5,28 40,31 44,31" fill="none" stroke="#8FE0B3" strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round" />
    <circle cx="48" cy="17" r="6" fill="#E5574D" stroke="#ffffff" strokeWidth="2.5" />
  </svg>;
}

const COMMENTS = [
  { who: 'Ngọc Anh', text: 'Gà hôm nay bị khô, vỏ không còn giòn nữa 😕', tone: 'negative', label: 'Tiêu cực' },
  { who: 'Minh Khoa', text: 'Đợi 40 phút mới có đồ, giờ trưa quá đông', tone: 'negative', label: 'Tiêu cực' },
  { who: 'Thu Hà', text: 'Combo gà sốt cay mới ngon xuất sắc!', tone: 'positive', label: 'Tích cực' },
] as const;
const BARS = [18, 20, 19, 22, 30, 24];

/** Ảnh sản phẩm dựng bằng HTML: bình luận đi vào, tỷ lệ tiêu cực vượt ngưỡng, email cảnh báo và gợi ý AI. Thương hiệu KFCC và số liệu chỉ để minh họa. */
function HeroVisual() {
  return <div className="lp-visual" aria-hidden="true">
    <div className="lp-stage">
      <div className="lp-card lp-chart">
        <div className="lp-chart-head">
          <span className="lp-avatar">KF</span>
          <div><p className="lp-chart-title">KFCC</p><p className="lp-chart-sub">Tỷ lệ tiêu cực theo lần thu thập · ngưỡng tăng 50%</p></div>
          <span className="lp-alert-pill"><BellRing size={13} />Vượt ngưỡng</span>
        </div>
        <div className="lp-bars">{BARS.map((value, index) => <div key={index} className={index === 4 ? 'lp-bar lp-bar-hot' : 'lp-bar'} style={{ height: `${value * 3}%`, animationDelay: `${0.25 + index * 0.07}s` }}>
          <span>{value}%</span></div>)}</div>
      </div>
      {COMMENTS.map((comment, index) => <div key={comment.who} className={`lp-card lp-comment lp-comment-${index}`}>
        <span className={`lp-comment-avatar lp-tone-${comment.tone}`}>{comment.who.split(' ').map((w) => w[0]).join('')}</span>
        <div><p className="lp-comment-text">{comment.text}</p><span className={`lp-chip lp-chip-${comment.tone}`}>{comment.label}</span></div>
      </div>)}
      <div className="lp-card lp-mail">
        <span className="lp-mail-icon"><Mail size={18} /></span>
        <div><p className="lp-mail-title">Cảnh báo: bình luận tiêu cực tăng</p><p className="lp-mail-sub">KFCC · 20% → <strong>30%</strong></p></div>
      </div>
      <div className="lp-card lp-ai">
        <p className="lp-ai-title"><Sparkles size={15} />AI tóm tắt 3 chủ đề</p>
        <ul><li><i className="lp-dot lp-dot-neg" />Gà bị khô, kém giòn</li><li><i className="lp-dot lp-dot-neg" />Phục vụ chậm giờ cao điểm</li><li><i className="lp-dot lp-dot-pos" />Thích combo gà sốt cay</li></ul>
      </div>
    </div>
  </div>;
}

function Step({ index, icon, title, children }: { index: number; icon: ReactNode; title: string; children: ReactNode }) {
  return <li className="lp-step">
    <div className="lp-step-top"><span className="lp-step-num">{index}</span><span className="lp-step-icon">{icon}</span></div>
    <h3>{title}</h3>
    <p>{children}</p>
  </li>;
}

export function Landing({ canLogin, busy, message, token, onToken, onConnect, onLogin, onSignup }: {
  canLogin: boolean; busy: boolean; message: string; token: string; onToken: (value: string) => void;
  onConnect: (event: FormEvent) => void; onLogin: () => void; onSignup: () => void;
}) {
  return <div className="lp">
    <header className="lp-nav">
      <p className="lp-brand"><LogoMark />Brand Auto-Tracking</p>
      {canLogin && <nav className="lp-nav-actions" aria-label="Tài khoản">
        <button type="button" className="lp-btn lp-btn-ghost" disabled={busy} onClick={onLogin}>Đăng nhập</button>
        <button type="button" className="lp-btn lp-btn-dark" disabled={busy} onClick={onSignup}>Tạo tài khoản</button>
      </nav>}
    </header>

    <main className="lp-main">
      <section className="lp-hero">
        <div className="lp-copy">
          <h1>Nghe thấy lời phàn nàn trước khi nó lan rộng.</h1>
          <p className="lp-lead">Theo dõi bài viết và bình luận về nhãn hàng của bạn. Hệ thống đo tỷ lệ tiêu cực sau mỗi lần thu thập, gửi email khi vượt ngưỡng và để AI tóm tắt nguyên nhân kèm dẫn chứng.</p>
          {canLogin
            ? <div className="lp-cta"><button type="button" className="lp-btn lp-btn-primary lp-btn-lg" disabled={busy} onClick={onSignup}>Dùng thử ngay</button>
              <a className="lp-link" href="#cach-hoat-dong">Xem cách hoạt động</a></div>
            : <p role="status" className="lp-warning">Chưa cấu hình đăng nhập. Cần đặt VITE_COGNITO_DOMAIN và VITE_COGNITO_CLIENT_ID.</p>}
          {busy && <p role="status" className="lp-status">Đang kết nối…</p>}
          {message && <p role="alert" className="lp-error">{message}</p>}
          <ul className="lp-proof">
            <li><BellRing size={16} />Cảnh báo qua email</li>
            <li><Sparkles size={16} />Gợi ý AI có dẫn chứng</li>
            <li><ShieldCheck size={16} />Tài khoản tách biệt dữ liệu</li>
          </ul>
        </div>
        <HeroVisual />
      </section>

      <section className="lp-how" id="cach-hoat-dong">
        <h2>Ba bước để không bỏ lỡ phản hồi xấu</h2>
        <ol className="lp-steps">
          <Step index={1} icon={<Search size={20} />} title="Thêm nhãn hàng và từ khóa">Nhập tên và những từ khách hàng hay dùng khi nhắc tới bạn. Hệ thống thu thập theo lịch đã chọn.</Step>
          <Step index={2} icon={<MessageCircle size={20} />} title="Theo dõi tỷ lệ tiêu cực">Mỗi lần thu thập, bình luận được phân loại cảm xúc và cộng dồn thành một cột trên biểu đồ.</Step>
          <Step index={3} icon={<BellRing size={20} />} title="Nhận cảnh báo và gợi ý">Khi tỷ lệ tăng vượt ngưỡng, bạn nhận email. AI tóm tắt chủ đề chính để bạn quyết định cách xử lý.</Step>
        </ol>
      </section>
    </main>

    <footer className="lp-footer">
      <p>Bài tập lớn môn Cloud. Thương hiệu KFCC và số liệu trên trang này là minh họa; dữ liệu trong buổi demo là giả lập, gợi ý AI chỉ để tham khảo.</p>
      <details className="lp-dev"><summary>Kết nối bằng access token</summary>
        <form className="lp-dev-form" onSubmit={onConnect}><label>Access token<input type="password" autoComplete="off" value={token} onChange={(e) => onToken(e.target.value)} /></label>
          <button className="lp-btn lp-btn-ghost" disabled={busy}>Kết nối</button></form>
      </details>
    </footer>
  </div>;
}
