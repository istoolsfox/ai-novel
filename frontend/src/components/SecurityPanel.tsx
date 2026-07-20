import { useCallback, useEffect, useMemo, useState } from 'react';
import { CheckCircle2, EyeOff, KeyRound, RefreshCw, RotateCcw, ShieldCheck, Trash2, X } from 'lucide-react';
import { controlApi, type ConsoleProject } from '../controlApi';
import {
  securityApi,
  setSecurityAdminToken,
  type EncryptedCredential,
  type SecurityEvent,
  type SecurityStatus,
} from '../securityApi';
import '../unified-console.css';
import '../security-panel.css';

type Props = {
  selectedProjectId?: string;
  onClose: () => void;
};

function formatTime(value: string) {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

export default function SecurityPanel({ selectedProjectId = '', onClose }: Props) {
  const [projects, setProjects] = useState<ConsoleProject[]>([]);
  const [projectId, setProjectId] = useState(selectedProjectId);
  const [status, setStatus] = useState<SecurityStatus | null>(null);
  const [credentials, setCredentials] = useState<EncryptedCredential[]>([]);
  const [events, setEvents] = useState<SecurityEvent[]>([]);
  const [message, setMessage] = useState('正在读取安全状态…');
  const [busy, setBusy] = useState('');
  const [name, setName] = useState('主模型 API Key');
  const [provider, setProvider] = useState('OpenAI');
  const [secret, setSecret] = useState('');
  const [rotationId, setRotationId] = useState('');
  const [rotationSecret, setRotationSecret] = useState('');
  const [testId, setTestId] = useState('');
  const [baseUrl, setBaseUrl] = useState('https://api.openai.com/v1');
  const [modelName, setModelName] = useState('');
  const [adminToken, setAdminToken] = useState(() => sessionStorage.getItem('ai-novel-admin-token') ?? '');

  const selectedProject = useMemo(() => projects.find((project) => project.id === projectId), [projectId, projects]);

  const load = useCallback(async (quiet = false) => {
    if (!quiet) setMessage('正在刷新安全状态…');
    const projectResult = await controlApi.listProjects();
    setProjects(projectResult);
    const nextProjectId = [projectId, selectedProjectId, projectResult[0]?.id].find(
      (candidate) => candidate && projectResult.some((project) => project.id === candidate),
    ) ?? '';
    if (nextProjectId !== projectId) setProjectId(nextProjectId);
    const [statusResult, credentialResult, eventResult] = await Promise.all([
      securityApi.status(),
      nextProjectId ? securityApi.credentials(nextProjectId) : Promise.resolve([]),
      securityApi.events(nextProjectId),
    ]);
    setStatus(statusResult);
    setCredentials(credentialResult);
    setEvents(eventResult);
    if (!quiet) setMessage('安全状态已刷新。');
  }, [projectId, selectedProjectId]);

  useEffect(() => {
    setSecurityAdminToken(adminToken);
    if (adminToken) sessionStorage.setItem('ai-novel-admin-token', adminToken);
    else sessionStorage.removeItem('ai-novel-admin-token');
  }, [adminToken]);

  useEffect(() => {
    void load().catch((error: unknown) => setMessage(`安全状态读取失败：${error instanceof Error ? error.message : '未知错误'}`));
  }, []); // Load only when the lazy panel opens.

  useEffect(() => {
    if (!projectId) return undefined;
    const timer = window.setInterval(() => void load(true).catch(() => undefined), 8000);
    return () => window.clearInterval(timer);
  }, [load, projectId]);

  async function action(nameValue: string, operation: () => Promise<unknown>, success: string) {
    setBusy(nameValue);
    setMessage(`${nameValue}执行中…`);
    try {
      await operation();
      setMessage(success);
      await load(true);
    } catch (error) {
      setMessage(`${nameValue}失败：${error instanceof Error ? error.message : '未知错误'}`);
    } finally {
      setBusy('');
    }
  }

  async function createCredential() {
    if (!projectId || !secret.trim()) return;
    await action(
      '保存加密凭证',
      () => securityApi.createCredential(projectId, { name: name.trim(), provider, secret: secret.trim() }),
      '凭证已加密保存，明文不会返回浏览器。',
    );
    setSecret('');
  }

  async function rotateCredential() {
    if (!projectId || !rotationId || !rotationSecret.trim()) return;
    await action(
      '轮换凭证',
      () => securityApi.updateCredential(projectId, rotationId, { secret: rotationSecret.trim() }),
      '凭证已轮换，旧密文已被替换。',
    );
    setRotationSecret('');
  }

  async function testCredential() {
    if (!projectId || !testId || !modelName.trim()) return;
    await action(
      '测试凭证',
      () => securityApi.testCredential(projectId, testId, { base_url: baseUrl.trim(), model_name: modelName.trim() }),
      '远程模型连接测试成功。',
    );
  }

  return (
    <div className="uc-backdrop" role="presentation">
      <section className="uc-shell security-shell" role="dialog" aria-modal="true" aria-label="安全与凭证中心">
        <header className="uc-header">
          <div>
            <span className="uc-eyebrow">Local Encryption & Credentials</span>
            <h2>安全与凭证中心</h2>
            <p>API Key 只在本机解密，并通过凭证 ID 注入模型配置。</p>
          </div>
          <div className="uc-header-actions">
            <label>当前项目
              <select value={projectId} onChange={(event) => setProjectId(event.target.value)}>
                {projects.map((project) => <option key={project.id} value={project.id}>{project.title}</option>)}
              </select>
            </label>
            <button type="button" onClick={() => void load()} disabled={Boolean(busy)}><RefreshCw size={16} />刷新</button>
            <button className="uc-icon-button" type="button" onClick={onClose} aria-label="关闭安全与凭证中心"><X size={19} /></button>
          </div>
        </header>

        <div className="uc-message" role="status">
          <span className={`uc-dot ${status?.status === 'ok' ? 'ready' : 'error'}`} />
          <strong>{selectedProject?.title ?? '未选择项目'}</strong>
          <span>{message}</span>
        </div>

        <main className="security-content">
          <div className="uc-metrics-grid">
            <article className="uc-metric"><span>加密状态</span><strong>{status?.status ?? 'loading'}</strong><small>{status?.master_key_source ?? '—'} master key</small></article>
            <article className="uc-metric"><span>凭证数量</span><strong>{credentials.length}</strong><small>全库 {status?.credential_count ?? 0}</small></article>
            <article className="uc-metric"><span>无法解密</span><strong>{status?.unreadable_credentials ?? 0}</strong><small>应始终为 0</small></article>
            <article className="uc-metric"><span>密钥指纹</span><strong>{status?.master_key_fingerprint?.slice(0, 8) ?? '—'}</strong><small>用于识别密钥轮换</small></article>
          </div>

          <section className="uc-card security-master-card">
            <div className="uc-card-heading"><div><span>主密钥</span><strong>{status?.master_key_source === 'environment' ? '环境变量托管' : '本地文件托管'}</strong></div><ShieldCheck size={19} /></div>
            <p>{status?.master_key_path || '主密钥来自 AI_NOVEL_MASTER_KEY，不显示实际内容。'}</p>
            <p>文件权限：{status?.master_key_permissions ?? '当前平台不提供权限位'}。主密钥丢失后，现有凭证无法恢复。</p>
            {status?.admin_token_required && (
              <label>运维令牌（仅保存在当前浏览器会话）
                <input type="password" value={adminToken} onChange={(event) => setAdminToken(event.target.value)} aria-label="运维令牌" />
              </label>
            )}
          </section>

          <div className="security-grid">
            <section className="uc-card uc-form-card">
              <div className="uc-card-heading"><div><span>新建凭证</span><strong>加密后写入 SQLite</strong></div><KeyRound size={19} /></div>
              <label>名称<input value={name} onChange={(event) => setName(event.target.value)} /></label>
              <label>提供商<select value={provider} onChange={(event) => setProvider(event.target.value)}><option>OpenAI</option><option>DeepSeek</option><option>MiniMax</option><option>Xiaomi MiMo</option><option>Custom</option></select></label>
              <label>API Key<input aria-label="新凭证 API Key" type="password" value={secret} onChange={(event) => setSecret(event.target.value)} autoComplete="new-password" /></label>
              <button className="uc-primary" type="button" onClick={() => void createCredential()} disabled={!projectId || !secret.trim() || Boolean(busy)}><KeyRound size={16} />加密保存</button>
            </section>

            <section className="uc-card uc-form-card">
              <div className="uc-card-heading"><div><span>轮换与测试</span><strong>不读取旧明文</strong></div><RotateCcw size={19} /></div>
              <label>凭证<select value={rotationId} onChange={(event) => { setRotationId(event.target.value); setTestId(event.target.value); }}><option value="">选择凭证</option>{credentials.map((credential) => <option key={credential.id} value={credential.id}>{credential.name}</option>)}</select></label>
              <label>新 API Key<input aria-label="轮换 API Key" type="password" value={rotationSecret} onChange={(event) => setRotationSecret(event.target.value)} autoComplete="new-password" /></label>
              <button type="button" onClick={() => void rotateCredential()} disabled={!rotationId || !rotationSecret.trim() || Boolean(busy)}><RotateCcw size={16} />轮换密钥</button>
              <label>Base URL<input value={baseUrl} onChange={(event) => setBaseUrl(event.target.value)} /></label>
              <label>Model Name<input aria-label="凭证测试模型" value={modelName} onChange={(event) => setModelName(event.target.value)} /></label>
              <button type="button" onClick={() => void testCredential()} disabled={!testId || !modelName.trim() || Boolean(busy)}><CheckCircle2 size={16} />测试连接</button>
            </section>
          </div>

          <section className="uc-card">
            <div className="uc-card-heading"><div><span>项目凭证</span><strong>{credentials.length} 条</strong></div><EyeOff size={19} /></div>
            <div className="security-list">
              {credentials.map((credential) => (
                <article key={credential.id}>
                  <div><strong>{credential.name}</strong><span>{credential.provider} · {credential.secret_hint}</span><small>更新：{formatTime(credential.updated_at)} · 最近使用：{formatTime(credential.last_used_at)}</small></div>
                  <div className="uc-actions">
                    <span className={`uc-status ${credential.status === 'active' ? 'success' : 'neutral'}`}>{credential.status}</span>
                    <button type="button" onClick={() => void action(
                      credential.status === 'active' ? '停用凭证' : '启用凭证',
                      () => securityApi.updateCredential(projectId, credential.id, { status: credential.status === 'active' ? 'disabled' : 'active' }),
                      '凭证状态已更新。',
                    )}>{credential.status === 'active' ? '停用' : '启用'}</button>
                    <button className="uc-danger" type="button" onClick={() => void action('删除凭证', () => securityApi.deleteCredential(projectId, credential.id), '凭证已删除。')}><Trash2 size={14} />删除</button>
                  </div>
                </article>
              ))}
              {!credentials.length && <p>当前项目还没有加密凭证。旧模型配置中的明文密钥会在后端启动时自动迁移。</p>}
            </div>
          </section>

          <section className="uc-card">
            <div className="uc-card-heading"><div><span>安全事件</span><strong>最近 {events.length} 条</strong></div></div>
            <div className="security-event-list">
              {events.slice(0, 30).map((event) => <article key={event.id}><div><strong>{event.event_type}</strong><span>{event.message}</span></div><small>{formatTime(event.created_at)}</small></article>)}
            </div>
          </section>
        </main>
      </section>
    </div>
  );
}
