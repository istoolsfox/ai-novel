import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock3,
  DatabaseBackup,
  Download,
  HardDrive,
  RefreshCw,
  RotateCcw,
  ServerCog,
  ShieldCheck,
  Trash2,
  X,
} from 'lucide-react';
import {
  controlApi,
  type BackupSchedule,
  type DatabaseBackup,
  type RuntimeEvent,
  type RuntimeHealth,
  type RuntimeTask,
  type RuntimeWorker,
} from '../controlApi';
import '../unified-console.css';
import '../operations-panel.css';

const EMPTY_SCHEDULE: BackupSchedule = {
  id: 'default',
  enabled: false,
  interval_hours: 24,
  retention_count: 7,
  next_run_at: '',
  last_run_at: '',
  last_backup_id: '',
  last_error: '',
  claimed_by: '',
  lease_expires_at: '',
};

type Props = { onClose: () => void };

type Tab = 'health' | 'tasks' | 'backups' | 'logs' | 'deploy';

function formatTime(value: string) {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function formatBytes(value: number) {
  if (!value) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  let size = value;
  let index = 0;
  while (size >= 1024 && index < units.length - 1) {
    size /= 1024;
    index += 1;
  }
  return `${size.toFixed(index ? 1 : 0)} ${units[index]}`;
}

function Badge({ value }: { value: string }) {
  const tone = ['ok', 'active', 'completed', 'success'].includes(value) ? 'success'
    : ['queued', 'running', 'degraded', 'warning'].includes(value) ? 'warning'
      : ['failed', 'stopped', 'cancelled'].includes(value) ? 'danger' : 'neutral';
  return <span className={`uc-status ${tone}`}>{value || 'unknown'}</span>;
}

export default function OperationsPanel({ onClose }: Props) {
  const [tab, setTab] = useState<Tab>('health');
  const [health, setHealth] = useState<RuntimeHealth | null>(null);
  const [workers, setWorkers] = useState<RuntimeWorker[]>([]);
  const [tasks, setTasks] = useState<RuntimeTask[]>([]);
  const [events, setEvents] = useState<RuntimeEvent[]>([]);
  const [backups, setBackups] = useState<DatabaseBackup[]>([]);
  const [schedule, setSchedule] = useState<BackupSchedule>(EMPTY_SCHEDULE);
  const [message, setMessage] = useState('正在读取运行状态…');
  const [busy, setBusy] = useState('');
  const [backupNote, setBackupNote] = useState('手动运维备份');
  const [restoreId, setRestoreId] = useState('');
  const [restoreConfirmation, setRestoreConfirmation] = useState('');

  const load = useCallback(async (quiet = false) => {
    if (!quiet) setMessage('正在刷新运行状态…');
    const results = await Promise.allSettled([
      controlApi.runtimeHealth(),
      controlApi.runtimeWorkers(),
      controlApi.runtimeTasks(),
      controlApi.runtimeEvents(),
      controlApi.backups(),
      controlApi.backupSchedule(),
    ]);
    const [healthResult, workerResult, taskResult, eventResult, backupResult, scheduleResult] = results;
    if (healthResult.status === 'fulfilled') setHealth(healthResult.value);
    if (workerResult.status === 'fulfilled') setWorkers(workerResult.value);
    if (taskResult.status === 'fulfilled') setTasks(taskResult.value);
    if (eventResult.status === 'fulfilled') setEvents(eventResult.value);
    if (backupResult.status === 'fulfilled') setBackups(backupResult.value);
    if (scheduleResult.status === 'fulfilled') setSchedule(scheduleResult.value);
    const failed = results.filter((result) => result.status === 'rejected').length;
    if (!quiet) setMessage(failed ? `${failed} 个运维模块暂时无法读取。` : '运行状态已刷新。');
  }, []);

  useEffect(() => {
    void load();
    const timer = window.setInterval(() => void load(true), 5000);
    return () => window.clearInterval(timer);
  }, [load]);

  async function action<T>(name: string, operation: () => Promise<T>, success: string) {
    setBusy(name);
    setMessage(`${name}执行中…`);
    try {
      const result = await operation();
      setMessage(success);
      await load(true);
      return result;
    } catch (error) {
      setMessage(`${name}失败：${error instanceof Error ? error.message : '未知错误'}`);
      return undefined;
    } finally {
      setBusy('');
    }
  }

  const activeWorkers = workers.filter((worker) => worker.healthy);
  const queuedTasks = tasks.filter((task) => ['queued', 'running'].includes(task.status));
  const counts = useMemo(() => health?.runtime ?? {}, [health]);

  return (
    <div className="uc-backdrop" role="presentation">
      <section className="uc-shell ops-shell" role="dialog" aria-modal="true" aria-label="运行与部署中心">
        <header className="uc-header">
          <div>
            <span className="uc-eyebrow">Deployment & Operations</span>
            <h2>运行与部署中心</h2>
            <p>查看独立 Worker、租约队列、自动备份、运行日志和部署命令。</p>
          </div>
          <div className="uc-header-actions">
            <button type="button" onClick={() => void load()} disabled={Boolean(busy)}><RefreshCw size={16} />刷新</button>
            <button className="uc-icon-button" type="button" onClick={onClose} aria-label="关闭运行与部署中心"><X size={19} /></button>
          </div>
        </header>

        <div className="uc-message" role="status">
          <span className={`uc-dot ${health?.status === 'ok' ? 'ready' : 'error'}`} />
          <strong>{health?.status === 'ok' ? '运行正常' : '需要关注'}</strong>
          <span>{message}</span>
        </div>

        <div className="ops-tabs">
          {([
            ['health', '健康状态', Activity],
            ['tasks', 'Worker 与任务', ServerCog],
            ['backups', '备份恢复', DatabaseBackup],
            ['logs', '运行日志', Clock3],
            ['deploy', '部署命令', HardDrive],
          ] as const).map(([key, label, Icon]) => (
            <button type="button" key={key} className={tab === key ? 'active' : ''} onClick={() => setTab(key)}>
              <Icon size={16} />{label}
            </button>
          ))}
        </div>

        <main className="ops-content">
          {tab === 'health' && (
            <div className="uc-section-stack">
              <div className="uc-metrics-grid">
                <article className="uc-metric"><span>系统状态</span><strong>{health?.status ?? 'loading'}</strong><small>{formatTime(health?.checked_at ?? '')}</small></article>
                <article className="uc-metric"><span>健康 Worker</span><strong>{activeWorkers.length}</strong><small>注册记录 {workers.length}</small></article>
                <article className="uc-metric"><span>活动任务</span><strong>{queuedTasks.length}</strong><small>异步队列</small></article>
                <article className="uc-metric"><span>托管队列</span><strong>{Object.values(counts.generation_jobs ?? {}).reduce((sum, value) => sum + Number(value), 0)}</strong><small>全部状态</small></article>
                <article className="uc-metric"><span>自动备份</span><strong>{schedule.enabled ? '开启' : '关闭'}</strong><small>{schedule.enabled ? `每 ${schedule.interval_hours} 小时` : '仅手动'}</small></article>
              </div>
              <div className="ops-grid">
                <section className="uc-card">
                  <div className="uc-card-heading"><div><span>数据库</span><strong>{String(health?.database.quick_check ?? '—')}</strong></div><ShieldCheck size={18} /></div>
                  <p>{String(health?.database.path ?? '尚未读取')}</p>
                </section>
                <section className="uc-card">
                  <div className="uc-card-heading"><div><span>存储目录</span><strong>{health?.storage.ok ? '可写' : '异常'}</strong></div><HardDrive size={18} /></div>
                  <p>{String(health?.storage.path ?? '尚未读取')}</p>
                </section>
              </div>
              {(health?.warnings ?? []).length > 0 && (
                <section className="uc-card ops-warning"><div className="uc-card-heading"><strong>运行警告</strong><AlertTriangle size={18} /></div>
                  <ul>{health?.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul>
                </section>
              )}
              <button type="button" onClick={() => void action('恢复过期租约', controlApi.recoverRuntime, '过期任务检查完成。')} disabled={Boolean(busy)}><RotateCcw size={16} />恢复过期租约</button>
            </div>
          )}

          {tab === 'tasks' && (
            <div className="uc-section-stack">
              <section className="uc-card">
                <div className="uc-card-heading"><div><span>独立 Worker</span><strong>{activeWorkers.length} 个健康</strong></div><ServerCog size={19} /></div>
                <div className="ops-table">
                  {workers.map((worker) => <article key={worker.id}><div><strong>{worker.id}</strong><span>{worker.hostname} · PID {worker.pid} · {worker.worker_type}</span></div><div><Badge value={worker.healthy ? 'active' : worker.status} /><small>{formatTime(worker.heartbeat_at)}</small></div></article>)}
                  {!workers.length && <p>尚未检测到 Worker。请在部署命令页启动 Worker。</p>}
                </div>
              </section>
              <section className="uc-card">
                <div className="uc-card-heading"><div><span>异步任务</span><strong>最近 {tasks.length} 条</strong></div></div>
                <div className="ops-table">
                  {tasks.map((task) => <article key={task.id}><div><strong>{task.task_type}</strong><span>{task.id.slice(0, 12)} · 尝试 {task.attempts}/{task.max_attempts}</span>{task.error_message && <em>{task.error_message}</em>}</div><div><Badge value={task.status} /><small>{formatTime(task.updated_at)}</small></div></article>)}
                  {!tasks.length && <p>暂无异步任务。</p>}
                </div>
              </section>
            </div>
          )}

          {tab === 'backups' && (
            <div className="uc-section-stack">
              <section className="uc-card uc-form-card">
                <div className="uc-card-heading"><div><span>自动备份计划</span><strong>{schedule.enabled ? '已启用' : '未启用'}</strong></div><Clock3 size={19} /></div>
                <div className="uc-form-grid">
                  <label>状态<select value={schedule.enabled ? 'enabled' : 'disabled'} onChange={(event) => setSchedule((current) => ({ ...current, enabled: event.target.value === 'enabled' }))}><option value="enabled">启用</option><option value="disabled">停用</option></select></label>
                  <label>间隔小时<input aria-label="备份间隔小时" type="number" min="1" max="720" value={schedule.interval_hours} onChange={(event) => setSchedule((current) => ({ ...current, interval_hours: Number(event.target.value) }))} /></label>
                  <label>保留份数<input aria-label="备份保留份数" type="number" min="1" max="100" value={schedule.retention_count} onChange={(event) => setSchedule((current) => ({ ...current, retention_count: Number(event.target.value) }))} /></label>
                </div>
                <p>下次执行：{formatTime(schedule.next_run_at)} · 最近执行：{formatTime(schedule.last_run_at)}</p>
                {schedule.last_error && <p className="ops-error">{schedule.last_error}</p>}
                <div className="uc-actions">
                  <button className="uc-primary" type="button" onClick={() => void action('保存备份计划', () => controlApi.updateBackupSchedule({ enabled: schedule.enabled, interval_hours: schedule.interval_hours, retention_count: schedule.retention_count }), '自动备份计划已保存。')} disabled={Boolean(busy)}><CheckCircle2 size={16} />保存计划</button>
                  <button type="button" onClick={() => void action('请求立即备份', controlApi.triggerBackupSchedule, 'Worker 将立即执行计划备份。')} disabled={Boolean(busy)}><Clock3 size={16} />立即计划备份</button>
                </div>
              </section>

              <section className="uc-card uc-form-card">
                <div className="uc-card-heading"><div><span>手动备份</span><strong>SQLite 在线快照</strong></div><DatabaseBackup size={19} /></div>
                <label>备注<input aria-label="备份备注" value={backupNote} onChange={(event) => setBackupNote(event.target.value)} /></label>
                <button type="button" onClick={() => void action('创建数据库备份', () => controlApi.createBackup(backupNote), '数据库备份已创建。')} disabled={Boolean(busy)}><DatabaseBackup size={16} />立即备份</button>
              </section>

              <section className="uc-card">
                <div className="uc-card-heading"><div><span>备份文件</span><strong>{backups.length} 份</strong></div></div>
                <div className="ops-backups">
                  {backups.map((backup) => <article key={backup.id} className={restoreId === backup.id ? 'selected' : ''}>
                    <button className="ops-backup-main" type="button" onClick={() => setRestoreId(backup.id)}><strong>{backup.id}</strong><span>{backup.kind} · {formatBytes(backup.size_bytes)} · {formatTime(backup.created_at)}</span><small>{backup.note || backup.sha256.slice(0, 18)}</small></button>
                    <div className="uc-actions"><a href={controlApi.backupDownloadUrl(backup.id)}><Download size={15} />下载</a><button type="button" onClick={() => void action('校验备份', () => controlApi.verifyBackup(backup.id), '备份校验通过。')}><ShieldCheck size={15} />校验</button><button type="button" onClick={() => void action('删除备份', () => controlApi.deleteBackup(backup.id), '备份已删除。')}><Trash2 size={15} />删除</button></div>
                  </article>)}
                  {!backups.length && <p>暂无数据库备份。</p>}
                </div>
              </section>

              <section className="uc-card ops-danger-zone">
                <div className="uc-card-heading"><div><span>危险操作</span><strong>恢复数据库</strong></div><AlertTriangle size={19} /></div>
                <p>恢复前必须停止所有 Worker，并清空排队、运行和暂停中的任务。系统会先创建恢复前安全备份。</p>
                <div className="uc-form-grid"><label>所选备份<input value={restoreId} readOnly placeholder="先从上方选择备份" /></label><label>输入 RESTORE<input aria-label="恢复确认" value={restoreConfirmation} onChange={(event) => setRestoreConfirmation(event.target.value)} /></label></div>
                <button className="uc-danger" type="button" disabled={!restoreId || restoreConfirmation !== 'RESTORE' || Boolean(busy)} onClick={() => void action('恢复数据库', () => controlApi.restoreBackup(restoreId), '数据库已经恢复，请重新刷新应用。')}><RotateCcw size={16} />恢复所选备份</button>
              </section>
            </div>
          )}

          {tab === 'logs' && (
            <section className="uc-card">
              <div className="uc-card-heading"><div><span>运行事件</span><strong>最近 {events.length} 条</strong></div><Clock3 size={18} /></div>
              <div className="ops-log-list">{events.map((event) => <article key={event.id}><time>{formatTime(event.created_at)}</time><div><strong>{event.event_type}</strong><span>{event.message}</span><small>{event.worker_id || event.task_id || event.project_id}</small></div></article>)}</div>
              {!events.length && <p>暂无运行日志。</p>}
            </section>
          )}

          {tab === 'deploy' && (
            <div className="uc-section-stack">
              <section className="uc-card"><div className="uc-card-heading"><strong>Docker Compose</strong><HardDrive size={18} /></div><pre>docker compose up -d --build{`\n`}docker compose logs -f worker{`\n`}docker compose down</pre><p>默认访问地址：http://127.0.0.1:8080</p></section>
              <section className="uc-card"><div className="uc-card-heading"><strong>Windows PowerShell</strong><HardDrive size={18} /></div><pre>powershell -ExecutionPolicy Bypass -File scripts/windows/start-docker.ps1{`\n`}powershell -ExecutionPolicy Bypass -File scripts/windows/stop-docker.ps1</pre></section>
              <section className="uc-card"><div className="uc-card-heading"><strong>本地三进程</strong><ServerCog size={18} /></div><pre>powershell -ExecutionPolicy Bypass -File scripts/windows/start-local.ps1{`\n`}powershell -ExecutionPolicy Bypass -File scripts/windows/stop-local.ps1</pre></section>
              <section className="uc-card"><div className="uc-card-heading"><strong>Linux systemd</strong><ServerCog size={18} /></div><pre>sudo systemctl enable --now ai-novel-web ai-novel-worker{`\n`}sudo journalctl -u ai-novel-worker -f</pre></section>
            </div>
          )}
        </main>
      </section>
    </div>
  );
}
