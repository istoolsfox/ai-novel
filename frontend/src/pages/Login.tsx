import { FormEvent, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Feather, LoaderCircle } from 'lucide-react';
import { api, setToken } from '../api';

export function Login() {
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    document.title = '登录 · Novel OS';
  }, []);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!username.trim() || !password || submitting) return;
    setSubmitting(true);
    setError('');
    try {
      const result = await api.accountLogin(username.trim(), password);
      setToken(result.token, result.username);
      navigate('/dashboard', { replace: true });
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : '登录失败');
      setSubmitting(false);
    }
  };

  return (
    <div className="login-page">
      <form className="login-card" onSubmit={submit}>
        <div className="brand" style={{ padding: 0, marginBottom: 18 }}>
          <span className="brand-mark"><Feather size={15} /></span>
          <span className="brand-name">Novel OS</span>
        </div>
        <h1 className="page-title" style={{ fontSize: 21 }}>登录</h1>
        <p className="page-sub" style={{ marginBottom: 18 }}>输入账号密码继续使用创作工作台。</p>
        <div className="stack" style={{ gap: 14 }}>
          <label className="field">
            <span>用户名</span>
            <input value={username} onChange={(event) => setUsername(event.target.value)} autoFocus autoComplete="username" />
          </label>
          <label className="field">
            <span>密码</span>
            <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" />
          </label>
          {error && <div className="notice">{error}</div>}
          <button type="submit" className="btn btn-primary" style={{ justifyContent: 'center', padding: '9px 0' }} disabled={submitting || !username.trim() || !password}>
            {submitting ? <LoaderCircle size={14} className="spin" /> : null}
            {submitting ? '登录中…' : '登录'}
          </button>
        </div>
      </form>
    </div>
  );
}
