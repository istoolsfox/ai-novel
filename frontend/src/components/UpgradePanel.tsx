import { useCallback, useEffect, useMemo, useState } from 'react';
import { AlertTriangle, CheckCircle2, DatabaseZap, KeyRound, RefreshCw, RotateCcw, ShieldCheck, X } from 'lucide-react';
import { securityApi, setSecurityAdminToken, type SecurityStatus } from '../securityApi';
import { setUpgradeAdminToken, upgradeApi, type KeyRotation, type MigrationPlan, type MigrationRun } from '../upgradeApi';
import '../unified-console.css';
import '../upgrade-panel.css';

type Props = { onClose: () => void };

function formatTime(value: string) {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

export default function UpgradePanel({ onClose }: Props) {
  const [plan, setPlan] = useState<MigrationPlan | null>(null);
  const [runs, setRuns] = useState<MigrationRun[]>([]);
  const [rotations, setRotations] = useState<KeyRotation[]>([]);
  const [security, setSecurity] = useState<SecurityStatus | null>(null);
  const [message, setMessage] = useState('正在读取升级状态…');
  const [busy, setBusy] = useState('');
  const [applyConfirmation, setApplyConfirmation] = useState('');
  const [rollbackBackupId, setRollbackBackupId] = useState('');
  const [rollbackConfirmation, setRollbackConfirmation] = useState('');
  const [rotateConfirmation, setRotateConfirmation] = useState('');
  const [newMasterKey, setNewMasterKey] = useState('');
  const [restoreRotationId, setRestoreRotationId] = useState('');
  const [restoreKeyConfirmation, setRestoreKeyConfirmation] = useState('');
  const [adminToken, setAdminToken] = useState(() => sessionStorage.getItem('ai-novel-admin-token') ?? '');

  const rollbackOptions = useMemo(() => runs.filter((run) => run.backup_id), [runs]);

  const load = useCallback(async (quiet = false) => {
    if (!quiet) setMessage('正在刷新升级状态…');
    const [planResult, runResult, rotationResult, securityResult] = await Promise.all([
      upgradeApi.plan(),
      upgradeApi.runs(),
      upgradeApi.rotations(),
      securityApi.status(),
    ]);
    setPlan(planResult);
    setRuns(runResult);
    setRotations(rotationResult);
    setSecurity(securityResult);
    if (!quiet) setMessage('升级状态已刷新。');
  }, []);

  useEffect(() => {
    setUpgradeAdminToken(adminToken);
    setSecurityAdminToken(adminToken);
    if (adminToken) sessionStorage.setItem('ai-novel-admin-token', adminToken);
    else sessionStorage.removeItem('ai-novel-admin-token');
  }, [adminToken]);

  useEffect(() => {
    void load().catch((error: unknown) => setMessage(`升级状态读取失败：${error instanceof Error ? error.message : '未知错误'}`));
  }, [load]);

  async function action(name: string, operation: () => Promise<unknown>, success: string) {
    setBusy(name);
    setMessage(`${name}执行中…`);
    try {
      await operation();
      setMessage(success);
      await load(true);
    } catch (error) {
      setMessage(`${name}失败：${error instanceof Error ? error.message : '未知错误'}`);
    } finally {
      setBusy('');
    }
  }

  return (
    <div className="uc-backdrop" role="presentation">
      <section className="uc-shell upgrade-shell" role="dialog" aria-modal="true" aria-label="升级与回滚中心">
        <header className="uc-header">
          <div>
            <span className="uc-eyebrow">Migrations & Recovery</span>
            <h2>升级与回滚中心</h2>
            <p>迁移前自动创建快照，校验和漂移会阻止升级，失败时自动恢复旧库。</p>
          </div>
          <div className="uc-header-actions">
            <button type="button" onClick={() => void load()} disabled={Boolean(busy)}><RefreshCw size={16} />刷新</button>
            <button className="uc-icon-button" type="button" onClick={onClose} aria-label="关闭升级与回滚中心"><X size={19} /></button>
          </div>
        </header>

        <div className="uc-message" role="status">
          <span className={`uc-dot ${plan?.status === 'current' ? 'ready' : 'loading'}`} />
          <strong>Schema {plan?.current_version ?? 0} / {plan?.latest_version ?? 0}</strong>
          <span>{message}</span>
        </div>

        <main className="upgrade-content">
          <div className="uc-metrics-grid">
            <article className="uc-metric"><span>迁移状态</span><strong>{plan?.status ?? 'loading'}</strong><small>{plan?.pending.length ?? 0} 个待执行</small></article>
            <article className="uc-metric"><span>校验漂移</span><strong>{plan?.drift.length ?? 0}</strong><small>{plan?.unknown_versions.length ?? 0} 个未知版本</small></article>
            <article className="uc-metric"><span>升级记录</span><strong>{runs.length}</strong><small>含失败与回滚</small></article>
            <article className="uc-metric"><span>密钥轮换</span><strong>{rotations.length}</strong><small>{security?.master_key_source ?? '—'} source</small></article>
          </div>

          {security?.admin_token_required && (
            <section className="uc-card">
              <div className="uc-card-heading"><div><span>运维授权</span><strong>敏感操作令牌</strong></div><ShieldCheck size={18} /></div>
              <label>运维令牌（当前浏览器会话）<input type="password" aria-label="升级运维令牌" value={adminToken} onChange={(event) => setAdminToken(event.target.value)} /></label>
            </section>
          )}

          {(plan?.blockers.length ?? 0) > 0 && (
            <section className="uc-card upgrade-warning">
              <div className="uc-card-heading"><strong>升级阻塞项</strong><AlertTriangle size={18} /></div>
              <ul>{plan?.blockers.map((blocker) => <li key={blocker}>{blocker}</li>)}</ul>
            </section>
          )}

          <div className="upgrade-grid">
            <section className="uc-card uc-form-card">
              <div className="uc-card-heading"><div><span>数据库升级</span><strong>{plan?.pending.length ? `${plan.pending.length} 个迁移待执行` : '已是最新'}</strong></div><DatabaseZap size={19} /></div>
              <div className="upgrade-migration-list">
                {plan?.pending.map((migration) => <article key={migration.version}><strong>v{migration.version} · {migration.name}</strong><span>{migration.description}</span><small>{migration.checksum.slice(0, 16)}</small></article>)}
                {!plan?.pending.length && <p>当前数据库已应用全部已知迁移。</p>}
              </div>
              <label>输入 APPLY 确认<input aria-label="迁移确认" value={applyConfirmation} onChange={(event) => setApplyConfirmation(event.target.value)} /></label>
              <button className="uc-primary" type="button" disabled={!plan?.can_apply || !plan.pending.length || applyConfirmation !== 'APPLY' || Boolean(busy)} onClick={() => void action('应用数据库迁移', upgradeApi.apply, '数据库迁移已完成并验证。')}><CheckCircle2 size={16} />应用全部迁移</button>
            </section>

            <section className="uc-card uc-form-card">
              <div className="uc-card-heading"><div><span>升级回滚</span><strong>恢复升级前快照</strong></div><RotateCcw size={19} /></div>
              <label>升级快照<select aria-label="回滚快照" value={rollbackBackupId} onChange={(event) => setRollbackBackupId(event.target.value)}><option value="">选择备份</option>{rollbackOptions.map((run) => <option key={run.id} value={run.backup_id}>{run.backup_id} · {run.status}</option>)}</select></label>
              <label>输入 ROLLBACK 确认<input aria-label="回滚确认" value={rollbackConfirmation} onChange={(event) => setRollbackConfirmation(event.target.value)} /></label>
              <button className="uc-danger" type="button" disabled={!rollbackBackupId || rollbackConfirmation !== 'ROLLBACK' || Boolean(busy)} onClick={() => void action('回滚数据库升级', () => upgradeApi.rollback(rollbackBackupId), '数据库已恢复到升级前快照。')}><RotateCcw size={16} />执行回滚</button>
            </section>
          </div>

          <div className="upgrade-grid">
            <section className="uc-card uc-form-card">
              <div className="uc-card-heading"><div><span>主密钥轮换</span><strong>{security?.master_key_fingerprint ?? '未读取'}</strong></div><KeyRound size={19} /></div>
              <p>留空新密钥时由后端生成。环境变量托管的主密钥必须在外部 Secret Manager 中轮换。</p>
              <label>可选 Fernet 新密钥<input type="password" aria-label="新主密钥" value={newMasterKey} onChange={(event) => setNewMasterKey(event.target.value)} /></label>
              <label>输入 ROTATE 确认<input aria-label="密钥轮换确认" value={rotateConfirmation} onChange={(event) => setRotateConfirmation(event.target.value)} /></label>
              <button type="button" disabled={rotateConfirmation !== 'ROTATE' || Boolean(busy)} onClick={() => void action('轮换主密钥', () => upgradeApi.rotateKey(newMasterKey), '主密钥和全部凭证已完成轮换与复检。')}><KeyRound size={16} />轮换主密钥</button>
            </section>

            <section className="uc-card uc-form-card">
              <div className="uc-card-heading"><div><span>密钥回退</span><strong>恢复轮换前密钥与数据库</strong></div><ShieldCheck size={19} /></div>
              <label>轮换记录<select aria-label="密钥轮换记录" value={restoreRotationId} onChange={(event) => setRestoreRotationId(event.target.value)}><option value="">选择记录</option>{rotations.filter((item) => item.backup_id && item.key_backup_path).map((item) => <option key={item.id} value={item.id}>{item.id.slice(0, 12)} · {item.status}</option>)}</select></label>
              <label>输入 RESTORE_KEY 确认<input aria-label="密钥恢复确认" value={restoreKeyConfirmation} onChange={(event) => setRestoreKeyConfirmation(event.target.value)} /></label>
              <button className="uc-danger" type="button" disabled={!restoreRotationId || restoreKeyConfirmation !== 'RESTORE_KEY' || Boolean(busy)} onClick={() => void action('恢复旧主密钥', () => upgradeApi.restoreKey(restoreRotationId), '旧主密钥与对应数据库快照已恢复。')}><ShieldCheck size={16} />恢复旧密钥</button>
            </section>
          </div>

          <section className="uc-card">
            <div className="uc-card-heading"><div><span>迁移历史</span><strong>{runs.length} 次运行</strong></div></div>
            <div className="upgrade-history">
              {runs.map((run) => <article key={run.id}><div><strong>{run.status} · v{run.from_version} → v{run.to_version}</strong><span>应用：{run.applied_versions.join(', ') || '无'} · 快照：{run.backup_id || '无'}</span>{run.error_message && <em>{run.error_message}</em>}</div><small>{formatTime(run.started_at)}</small></article>)}
              {!runs.length && <p>尚无迁移运行记录。</p>}
            </div>
          </section>
        </main>
      </section>
    </div>
  );
}
