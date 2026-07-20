import { useCallback, useEffect, useMemo, useState } from 'react';
import { AlertTriangle, CheckCircle2, Circle, RefreshCw, Rocket, ShieldCheck, X } from 'lucide-react';
import { releaseApi, setReleaseAdminToken, type ReleaseInfo, type ReleaseReadiness, type SetupState } from '../releaseApi';
import { securityApi, setSecurityAdminToken, type SecurityStatus } from '../securityApi';
import '../first-run-wizard.css';

type Props = {
  onComplete: () => void;
  onDismiss: () => void;
};

export default function FirstRunWizard({ onComplete, onDismiss }: Props) {
  const [info, setInfo] = useState<ReleaseInfo | null>(null);
  const [readiness, setReadiness] = useState<ReleaseReadiness | null>(null);
  const [state, setState] = useState<SetupState | null>(null);
  const [security, setSecurity] = useState<SecurityStatus | null>(null);
  const [message, setMessage] = useState('正在检查首次启动环境…');
  const [busy, setBusy] = useState(false);
  const [acknowledgeWithoutModel, setAcknowledgeWithoutModel] = useState(false);
  const [adminToken, setAdminToken] = useState(() => sessionStorage.getItem('ai-novel-admin-token') ?? '');

  const modelWarning = useMemo(
    () => readiness?.warnings.find((item) => item.id === 'model') ?? null,
    [readiness],
  );

  const load = useCallback(async () => {
    setMessage('正在检查首次启动环境…');
    const [infoResult, readinessResult, stateResult, securityResult] = await Promise.all([
      releaseApi.info(),
      releaseApi.readiness(),
      releaseApi.setupState(),
      securityApi.status(),
    ]);
    setInfo(infoResult);
    setReadiness(readinessResult);
    setState(stateResult);
    setSecurity(securityResult);
    setMessage(readinessResult.ready ? '核心环境已准备完成。' : '仍有必须处理的启动阻塞项。');
  }, []);

  useEffect(() => {
    setReleaseAdminToken(adminToken);
    setSecurityAdminToken(adminToken);
    if (adminToken) sessionStorage.setItem('ai-novel-admin-token', adminToken);
    else sessionStorage.removeItem('ai-novel-admin-token');
  }, [adminToken]);

  useEffect(() => {
    void load().catch((error: unknown) => setMessage(`环境检查失败：${error instanceof Error ? error.message : '未知错误'}`));
  }, [load]);

  async function complete() {
    setBusy(true);
    setMessage('正在完成首次启动设置…');
    try {
      await releaseApi.updateSetup('review', { acknowledge_without_model: acknowledgeWithoutModel });
      await releaseApi.completeSetup(acknowledgeWithoutModel);
      setMessage('首次启动设置已完成。');
      onComplete();
    } catch (error) {
      setMessage(`首次设置未完成：${error instanceof Error ? error.message : '未知错误'}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="first-run-backdrop" role="presentation">
      <section className="first-run-shell" role="dialog" aria-modal="true" aria-label="AI 小说系统首次启动向导">
        <header>
          <div>
            <span>AI NOVEL WORKBENCH</span>
            <h1>首次启动向导</h1>
            <p>发布候选 {info?.version ?? 'loading'} · Schema {info?.schema_version ?? 0}/{info?.latest_schema_version ?? 0}</p>
          </div>
          <button type="button" onClick={onDismiss} aria-label="稍后完成首次启动设置"><X size={18} /></button>
        </header>

        <div className="first-run-status" role="status">
          <Rocket size={18} />
          <strong>{readiness?.ready ? '核心环境已就绪' : '检查启动条件'}</strong>
          <span>{message}</span>
        </div>

        <main>
          <section className="first-run-intro">
            <div><ShieldCheck size={28} /><h2>本地优先，完整托管</h2><p>正文、记忆、世界线、备份和加密凭证默认保存在本机数据目录。</p></div>
            <dl>
              <div><dt>版本</dt><dd>{info?.version ?? '—'}</dd></div>
              <div><dt>通道</dt><dd>{info?.release_channel ?? '—'}</dd></div>
              <div><dt>数据库</dt><dd>{info?.database_path ?? '—'}</dd></div>
              <div><dt>能力模块</dt><dd>{info?.capabilities.length ?? 0}</dd></div>
            </dl>
          </section>

          <section className="first-run-checks">
            <div className="first-run-heading"><div><span>发布就绪检查</span><h2>{readiness?.checks.length ?? 0} 项环境检查</h2></div><button type="button" onClick={() => void load()} disabled={busy}><RefreshCw size={15} />重新检查</button></div>
            <div className="first-run-check-grid">
              {(readiness?.checks ?? []).map((check) => (
                <article key={check.id} className={check.status}>
                  {check.status === 'pass' ? <CheckCircle2 size={19} /> : check.status === 'warning' ? <AlertTriangle size={19} /> : <Circle size={19} />}
                  <div><strong>{check.label}</strong><span>{check.detail}</span></div>
                  <small>{check.required ? '必须' : '建议'}</small>
                </article>
              ))}
            </div>
          </section>

          {security?.admin_token_required && (
            <section className="first-run-card">
              <h2>运维授权</h2>
              <p>该部署启用了 `AI_NOVEL_ADMIN_TOKEN`。令牌只保存在当前浏览器会话。</p>
              <label>运维令牌<input type="password" aria-label="首次启动运维令牌" value={adminToken} onChange={(event) => setAdminToken(event.target.value)} /></label>
            </section>
          )}

          <section className="first-run-card">
            <h2>模型与 Worker</h2>
            <p>正式生成前，在“安全中心”保存模型 API Key，并在“运行中心”确认独立 Worker 心跳。也可以先使用本地 Stub 模式体验完整流程。</p>
            {modelWarning && (
              <label className="first-run-checkbox">
                <input type="checkbox" checked={acknowledgeWithoutModel} onChange={(event) => setAcknowledgeWithoutModel(event.target.checked)} />
                我确认暂时以 Stub 模式进入，稍后再配置真实模型凭证。
              </label>
            )}
          </section>

          <section className="first-run-actions">
            <button type="button" onClick={onDismiss}>稍后设置</button>
            <button className="primary" type="button" onClick={() => void complete()} disabled={busy || !readiness?.ready || Boolean(modelWarning && !acknowledgeWithoutModel)}><Rocket size={17} />完成首次启动</button>
          </section>
        </main>
      </section>
    </div>
  );
}
