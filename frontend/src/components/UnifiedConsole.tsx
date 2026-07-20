import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  Archive,
  BookOpenCheck,
  BrainCircuit,
  Database,
  Download,
  GitFork,
  Lock,
  Network,
  Pause,
  Play,
  RefreshCw,
  RotateCcw,
  ShieldCheck,
  Square,
  Unlock,
  Workflow,
  X,
} from 'lucide-react';
import {
  AutopilotSnapshot,
  ConsoleChapter,
  ConsoleProject,
  ContinuityCheck,
  ImpactRun,
  JsonRecord,
  MemoryContext,
  ObsidianStatus,
  RollingPlanItem,
  StoryGraph,
  Worldline,
  WorldlineFamily,
  controlApi,
} from '../controlApi';
import '../unified-console.css';

type ConsoleSection =
  | 'overview'
  | 'autopilot'
  | 'continuity'
  | 'memory'
  | 'graph'
  | 'planning'
  | 'worldlines'
  | 'obsidian';

type LoadState = 'idle' | 'loading' | 'ready' | 'error';

const EMPTY_AUTOPILOT: AutopilotSnapshot = {
  job: null,
  steps: [],
  events: [],
  progress: { completed: 0, total: 0, percent: 0 },
};

const sectionOptions: Array<{
  key: ConsoleSection;
  label: string;
  description: string;
  icon: typeof Activity;
}> = [
  { key: 'overview', label: '总览', description: '全书运行状态', icon: Activity },
  { key: 'autopilot', label: '托管任务', description: '启动、暂停与重试', icon: Workflow },
  { key: 'continuity', label: '连续性', description: '章节检查与风险', icon: ShieldCheck },
  { key: 'memory', label: '分层记忆', description: '事实、关系、物品与债务', icon: BrainCircuit },
  { key: 'graph', label: '剧情图谱', description: '剧情线、节点与停滞', icon: Network },
  { key: 'planning', label: '滚动计划', description: '未来章节安排与锁定', icon: BookOpenCheck },
  { key: 'worldlines', label: '世界线', description: '分叉、激活与主线', icon: GitFork },
  { key: 'obsidian', label: 'Obsidian', description: '知识库导出与下载', icon: Database },
];

function recordList(value: unknown): JsonRecord[] {
  return Array.isArray(value) ? value.filter((item): item is JsonRecord => Boolean(item) && typeof item === 'object') : [];
}

function text(value: unknown, fallback = '—'): string {
  if (typeof value === 'string' && value.trim()) return value;
  if (typeof value === 'number') return String(value);
  return fallback;
}

function numberValue(value: unknown): number {
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (typeof value === 'string') {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) return parsed;
  }
  return 0;
}

function statusTone(status: string): string {
  const normalized = status.toLowerCase();
  if (['completed', 'success', 'pass', 'active', 'committed'].includes(normalized)) return 'success';
  if (['running', 'queued', 'planned', 'warning', 'paused'].includes(normalized)) return 'warning';
  if (['failed', 'critical', 'cancelled', 'blocked', 'archived'].includes(normalized)) return 'danger';
  return 'neutral';
}

function StatusBadge({ value }: { value: string }) {
  return <span className={`uc-status ${statusTone(value)}`}>{value || 'unknown'}</span>;
}

function EmptyState({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="uc-empty">
      <Database size={24} />
      <strong>{title}</strong>
      <span>{detail}</span>
    </div>
  );
}

function MetricCard({ label, value, detail }: { label: string; value: string | number; detail: string }) {
  return (
    <article className="uc-metric">
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </article>
  );
}

function RowList({ items, empty }: { items: Array<{ title: string; detail: string; status?: string }>; empty: string }) {
  if (!items.length) return <EmptyState title={empty} detail="当前项目还没有可展示的记录。" />;
  return (
    <div className="uc-row-list">
      {items.map((item, index) => (
        <article key={`${item.title}-${index}`}>
          <div>
            <strong>{item.title}</strong>
            <span>{item.detail}</span>
          </div>
          {item.status && <StatusBadge value={item.status} />}
        </article>
      ))}
    </div>
  );
}

export function UnifiedConsole() {
  const [open, setOpen] = useState(false);
  const [section, setSection] = useState<ConsoleSection>('overview');
  const [projects, setProjects] = useState<ConsoleProject[]>([]);
  const [projectId, setProjectId] = useState('');
  const [chapters, setChapters] = useState<ConsoleChapter[]>([]);
  const [autopilot, setAutopilot] = useState<AutopilotSnapshot>(EMPTY_AUTOPILOT);
  const [continuity, setContinuity] = useState<ContinuityCheck[]>([]);
  const [memory, setMemory] = useState<MemoryContext>({});
  const [graph, setGraph] = useState<StoryGraph>({});
  const [plan, setPlan] = useState<RollingPlanItem[]>([]);
  const [impacts, setImpacts] = useState<ImpactRun[]>([]);
  const [worldlines, setWorldlines] = useState<WorldlineFamily | null>(null);
  const [obsidian, setObsidian] = useState<ObsidianStatus>({});
  const [loadState, setLoadState] = useState<LoadState>('idle');
  const [message, setMessage] = useState('控制台准备就绪');
  const [busyAction, setBusyAction] = useState('');
  const [startChapter, setStartChapter] = useState(1);
  const [endChapter, setEndChapter] = useState(1);
  const [mode, setMode] = useState<'full_autopilot' | 'chapter_checkpoint' | 'smart_checkpoint'>('full_autopilot');
  const [maxRetries, setMaxRetries] = useState(2);
  const [forkName, setForkName] = useState('新的剧情分支');
  const [forkChapter, setForkChapter] = useState(1);
  const [forkDescription, setForkDescription] = useState('从当前章节尝试另一种剧情方向。');
  const [includeDrafts, setIncludeDrafts] = useState(true);
  const [forceRebuild, setForceRebuild] = useState(false);

  const selectedProject = useMemo(
    () => projects.find((project) => project.id === projectId) ?? null,
    [projectId, projects],
  );
  const latestChapter = chapters[chapters.length - 1] ?? null;
  const job = autopilot.job;
  const activeJob = Boolean(job && ['queued', 'running', 'paused'].includes(job.status));

  const loadProjects = useCallback(async (preferredProjectId = '') => {
    const result = await controlApi.listProjects();
    setProjects(result);
    setProjectId((current) => {
      const preferred = preferredProjectId || current;
      if (preferred && result.some((project) => project.id === preferred)) return preferred;
      return result[0]?.id ?? '';
    });
    return result;
  }, []);

  const loadDashboard = useCallback(async (targetProjectId: string, quiet = false) => {
    if (!targetProjectId) return;
    if (!quiet) setLoadState('loading');
    const results = await Promise.allSettled([
      controlApi.listChapters(targetProjectId),
      controlApi.autopilotStatus(targetProjectId),
      controlApi.memoryContext(targetProjectId),
      controlApi.storyGraph(targetProjectId),
      controlApi.currentPlan(targetProjectId),
      controlApi.impactRuns(targetProjectId),
      controlApi.worldlines(targetProjectId),
      controlApi.obsidianStatus(targetProjectId),
    ]);

    const [chapterResult, autopilotResult, memoryResult, graphResult, planResult, impactResult, worldlineResult, obsidianResult] = results;
    const nextChapters = chapterResult.status === 'fulfilled' ? chapterResult.value : [];
    setChapters(nextChapters);
    if (autopilotResult.status === 'fulfilled') setAutopilot(autopilotResult.value);
    if (memoryResult.status === 'fulfilled') setMemory(memoryResult.value);
    if (graphResult.status === 'fulfilled') setGraph(graphResult.value);
    if (planResult.status === 'fulfilled') setPlan(planResult.value);
    if (impactResult.status === 'fulfilled') setImpacts(impactResult.value);
    if (worldlineResult.status === 'fulfilled') setWorldlines(worldlineResult.value);
    if (obsidianResult.status === 'fulfilled') setObsidian(obsidianResult.value);

    const newest = nextChapters[nextChapters.length - 1];
    if (newest) {
      try {
        setContinuity(await controlApi.continuityChecks(targetProjectId, newest.id));
      } catch {
        setContinuity([]);
      }
    } else {
      setContinuity([]);
    }

    const highestChapter = newest?.chapter_number ?? 0;
    setStartChapter((current) => (current > highestChapter + 1 ? current : highestChapter + 1));
    setEndChapter((current) => {
      const target = projects.find((project) => project.id === targetProjectId)?.target_chapter_count ?? highestChapter + 1;
      return Math.max(current, highestChapter + 1, target || 1);
    });
    setForkChapter((current) => Math.max(0, Math.min(current || highestChapter, highestChapter)));

    const failed = results.filter((result) => result.status === 'rejected').length;
    setLoadState(failed === results.length ? 'error' : 'ready');
    if (!quiet) setMessage(failed ? `已加载控制台，${failed} 个模块暂不可用。` : '控制台数据已刷新。');
  }, [projects]);

  useEffect(() => {
    void loadProjects().catch((error: unknown) => {
      setLoadState('error');
      setMessage(`项目列表加载失败：${error instanceof Error ? error.message : '未知错误'}`);
    });
  }, [loadProjects]);

  useEffect(() => {
    if (open && projectId) void loadDashboard(projectId);
  }, [open, projectId, loadDashboard]);

  useEffect(() => {
    if (!open || !projectId || typeof EventSource === 'undefined') return undefined;
    const source = new EventSource(controlApi.autopilotStreamUrl(projectId));
    source.onmessage = (event) => {
      try {
        setAutopilot(JSON.parse(event.data) as AutopilotSnapshot);
      } catch {
        // Ignore malformed transient events and keep the last valid snapshot.
      }
    };
    source.addEventListener('end', () => {
      source.close();
      void loadDashboard(projectId, true);
    });
    source.onerror = () => source.close();
    return () => source.close();
  }, [open, projectId, loadDashboard]);

  useEffect(() => {
    if (!open || !projectId || !activeJob) return undefined;
    const timer = window.setInterval(() => {
      void controlApi.autopilotStatus(projectId).then(setAutopilot).catch(() => undefined);
    }, 4000);
    return () => window.clearInterval(timer);
  }, [activeJob, open, projectId]);

  async function runAction<T>(name: string, action: () => Promise<T>, success: string): Promise<T | undefined> {
    setBusyAction(name);
    setMessage(`${name}执行中...`);
    try {
      const result = await action();
      setMessage(success);
      return result;
    } catch (error) {
      setMessage(`${name}失败：${error instanceof Error ? error.message : '未知错误'}`);
      return undefined;
    } finally {
      setBusyAction('');
    }
  }

  async function startAutopilot() {
    if (!projectId) return;
    const result = await runAction(
      '启动托管',
      () => controlApi.startAutopilot(projectId, {
        start_chapter: Math.max(1, startChapter),
        end_chapter: Math.max(startChapter, endChapter),
        mode,
        max_retries: maxRetries,
      }),
      `已创建第 ${startChapter}—${Math.max(startChapter, endChapter)} 章托管任务。`,
    );
    if (result) setAutopilot(result);
  }

  async function controlJob(action: 'pause' | 'resume' | 'stop') {
    if (!projectId || !job) return;
    const handlers = {
      pause: () => controlApi.pauseAutopilot(projectId, job.id),
      resume: () => controlApi.resumeAutopilot(projectId, job.id),
      stop: () => controlApi.stopAutopilot(projectId, job.id),
    };
    const labels = { pause: '暂停托管', resume: '恢复托管', stop: '停止托管' };
    const result = await runAction(labels[action], handlers[action], `${labels[action]}已完成。`);
    if (result) setAutopilot(result);
  }

  async function retryStep(stepId: string) {
    if (!projectId || !job) return;
    const result = await runAction(
      '重试失败步骤',
      () => controlApi.retryAutopilotStep(projectId, job.id, stepId),
      '失败步骤已重新进入执行队列。',
    );
    if (result) setAutopilot(result);
  }

  async function togglePlanLock(item: RollingPlanItem) {
    if (!projectId) return;
    const updated = await runAction(
      item.locked ? '解锁章节计划' : '锁定章节计划',
      () => controlApi.lockPlan(projectId, item.chapter_number, !item.locked),
      `第 ${item.chapter_number} 章计划已${item.locked ? '解锁' : '锁定'}。`,
    );
    if (updated) setPlan((items) => items.map((entry) => entry.chapter_number === updated.chapter_number ? updated : entry));
  }

  async function refreshWorldlineFamily(preferredProjectId = projectId) {
    await loadProjects(preferredProjectId);
    if (preferredProjectId) {
      setWorldlines(await controlApi.worldlines(preferredProjectId));
      await loadDashboard(preferredProjectId, true);
    }
  }

  async function forkWorldline() {
    if (!projectId || !forkName.trim()) return;
    const created = await runAction(
      '创建世界线',
      () => controlApi.forkWorldline(projectId, {
        name: forkName.trim(),
        fork_chapter_number: forkChapter,
        description: forkDescription.trim(),
      }),
      `世界线“${forkName.trim()}”已创建。`,
    );
    if (created) await refreshWorldlineFamily(created.project_id);
  }

  async function worldlineAction(line: Worldline, action: 'activate' | 'promote' | 'archive') {
    if (!projectId) return;
    const handlers = {
      activate: () => controlApi.activateWorldline(projectId, line.id),
      promote: () => controlApi.promoteWorldline(projectId, line.id),
      archive: () => controlApi.archiveWorldline(projectId, line.id),
    };
    const labels = { activate: '激活世界线', promote: '提升为主线', archive: '归档世界线' };
    const updated = await runAction(labels[action], handlers[action], `${labels[action]}已完成。`);
    if (!updated) return;
    const nextProjectId = action === 'archive' ? projectId : updated.project_id;
    await refreshWorldlineFamily(nextProjectId);
  }

  async function exportObsidian() {
    if (!projectId) return;
    const result = await runAction(
      '导出 Obsidian',
      () => controlApi.exportObsidian(projectId, {
        include_drafts: includeDrafts,
        force_rebuild: forceRebuild,
        create_archive: true,
      }),
      'Obsidian Vault 和 ZIP 已生成。',
    );
    if (result) setObsidian(await controlApi.obsidianStatus(projectId));
  }

  const threads = recordList(graph.all_threads ?? graph.story_threads);
  const nodes = recordList(graph.all_nodes ?? graph.story_nodes);
  const edges = recordList(graph.story_edges ?? graph.edges);
  const stalled = recordList(graph.stalled_threads);
  const hardFacts = recordList(memory.hard_facts);
  const relationships = recordList(memory.relationship_states);
  const items = recordList(memory.item_ownership);
  const debts = recordList(memory.narrative_debts);
  const foreshadowings = recordList(memory.active_foreshadowings);
  const latestCheck = continuity[continuity.length - 1];

  return (
    <>
      <button className="uc-launcher" type="button" onClick={() => setOpen(true)} aria-label="打开统一托管控制台">
        <Activity size={20} />
        <span>托管控制台</span>
        {activeJob && <i />}
      </button>

      {open && (
        <div className="uc-backdrop" role="presentation">
          <section className="uc-shell" role="dialog" aria-modal="true" aria-label="统一托管控制台">
            <header className="uc-header">
              <div>
                <span className="uc-eyebrow">Autonomous Novel Control Center</span>
                <h2>统一托管控制台</h2>
                <p>在一个界面中查看生成任务、记忆、剧情图谱、计划、世界线和知识库导出。</p>
              </div>
              <div className="uc-header-actions">
                <label>
                  当前项目
                  <select value={projectId} onChange={(event) => setProjectId(event.target.value)} aria-label="控制台项目选择">
                    {projects.map((project) => (
                      <option key={project.id} value={project.id}>{project.title}</option>
                    ))}
                  </select>
                </label>
                <button type="button" onClick={() => projectId && void loadDashboard(projectId)} disabled={!projectId || loadState === 'loading'}>
                  <RefreshCw size={16} className={loadState === 'loading' ? 'uc-spin' : ''} />
                  刷新
                </button>
                <button className="uc-icon-button" type="button" onClick={() => setOpen(false)} aria-label="关闭统一托管控制台">
                  <X size={19} />
                </button>
              </div>
            </header>

            <div className="uc-message" role="status">
              <span className={`uc-dot ${loadState}`} />
              <strong>{selectedProject?.title ?? '未选择项目'}</strong>
              <span>{message}</span>
            </div>

            <div className="uc-body">
              <nav className="uc-nav" aria-label="统一控制台模块">
                {sectionOptions.map((item) => {
                  const Icon = item.icon;
                  return (
                    <button key={item.key} className={section === item.key ? 'active' : ''} type="button" onClick={() => setSection(item.key)}>
                      <Icon size={17} />
                      <span><strong>{item.label}</strong><small>{item.description}</small></span>
                    </button>
                  );
                })}
              </nav>

              <main className="uc-content">
                {!projectId && <EmptyState title="还没有项目" detail="先在主工作台创建一本小说，再打开统一控制台。" />}

                {projectId && section === 'overview' && (
                  <div className="uc-section-stack">
                    <div className="uc-metrics-grid">
                      <MetricCard label="托管进度" value={`${Math.round(autopilot.progress.percent)}%`} detail={job ? `${job.status} · 第 ${job.current_chapter || job.start_chapter} 章` : '尚未启动'} />
                      <MetricCard label="章节" value={chapters.length} detail={latestChapter ? `最新：第 ${latestChapter.chapter_number} 章` : '暂无章节'} />
                      <MetricCard label="硬事实" value={hardFacts.length} detail={`${relationships.length} 条关系状态`} />
                      <MetricCard label="剧情图谱" value={`${threads.length}/${nodes.length}`} detail="剧情线 / 剧情节点" />
                      <MetricCard label="滚动计划" value={plan.length} detail={`${plan.filter((item) => item.locked).length} 章已锁定`} />
                      <MetricCard label="世界线" value={worldlines?.worldlines.length ?? 0} detail={worldlines?.isolation_model ?? '尚未初始化'} />
                    </div>
                    <div className="uc-overview-grid">
                      <section className="uc-card">
                        <div className="uc-card-heading"><div><span>当前任务</span><strong>{job ? `第 ${job.start_chapter}—${job.end_chapter} 章` : '未启动托管'}</strong></div>{job && <StatusBadge value={job.status} />}</div>
                        {job ? (
                          <>
                            <div className="uc-progress"><i style={{ width: `${autopilot.progress.percent}%` }} /></div>
                            <p>当前步骤：{job.current_step || '等待执行'} · 已完成 {autopilot.progress.completed}/{autopilot.progress.total}</p>
                          </>
                        ) : <p>设置章节范围后，可让系统自动生成、检查、修复、编译记忆并定稿。</p>}
                      </section>
                      <section className="uc-card">
                        <div className="uc-card-heading"><div><span>最近连续性检查</span><strong>{latestChapter ? `第 ${latestChapter.chapter_number} 章` : '暂无章节'}</strong></div>{latestCheck && <StatusBadge value={latestCheck.status} />}</div>
                        <p>{latestCheck ? `评分 ${latestCheck.score} · ${latestCheck.stage}` : '章节定稿后会显示时间、地点、人物状态、知识边界和情绪连续性检查。'}</p>
                      </section>
                      <section className="uc-card">
                        <div className="uc-card-heading"><div><span>剧情风险</span><strong>{stalled.length + impacts.length}</strong></div><AlertTriangle size={18} /></div>
                        <p>{stalled.length ? `${stalled.length} 条剧情线处于停滞提醒。` : '没有检测到停滞剧情线。'} 最近记录了 {impacts.length} 次影响分析。</p>
                      </section>
                      <section className="uc-card">
                        <div className="uc-card-heading"><div><span>Obsidian</span><strong>{text(obsidian.status, 'not_exported')}</strong></div><Database size={18} /></div>
                        <p>{text(obsidian.vault_path, '尚未导出，可在 Obsidian 模块生成独立世界线知识库。')}</p>
                      </section>
                    </div>
                  </div>
                )}

                {projectId && section === 'autopilot' && (
                  <div className="uc-section-stack">
                    <section className="uc-card uc-form-card">
                      <div className="uc-card-heading"><div><span>新建托管任务</span><strong>自动完成章节全流程</strong></div><Workflow size={19} /></div>
                      <div className="uc-form-grid">
                        <label>起始章节<input type="number" min="1" value={startChapter} onChange={(event) => setStartChapter(Number(event.target.value))} /></label>
                        <label>结束章节<input type="number" min={startChapter} value={endChapter} onChange={(event) => setEndChapter(Number(event.target.value))} /></label>
                        <label>托管模式<select value={mode} onChange={(event) => setMode(event.target.value as typeof mode)}><option value="full_autopilot">全自动</option><option value="chapter_checkpoint">逐章确认</option><option value="smart_checkpoint">智能检查点</option></select></label>
                        <label>最大重试<input type="number" min="0" max="10" value={maxRetries} onChange={(event) => setMaxRetries(Number(event.target.value))} /></label>
                      </div>
                      <div className="uc-actions"><button className="uc-primary" type="button" onClick={() => void startAutopilot()} disabled={Boolean(busyAction) || activeJob}><Play size={16} />启动托管</button>{job?.status === 'running' && <button type="button" onClick={() => void controlJob('pause')}><Pause size={16} />暂停</button>}{job?.status === 'paused' && <button type="button" onClick={() => void controlJob('resume')}><Play size={16} />恢复</button>}{activeJob && <button className="uc-danger" type="button" onClick={() => void controlJob('stop')}><Square size={16} />停止</button>}</div>
                    </section>
                    {job ? (
                      <section className="uc-card">
                        <div className="uc-card-heading"><div><span>任务 {job.id.slice(0, 8)}</span><strong>第 {job.start_chapter}—{job.end_chapter} 章</strong></div><StatusBadge value={job.status} /></div>
                        <div className="uc-progress large"><i style={{ width: `${autopilot.progress.percent}%` }} /></div>
                        <div className="uc-step-grid">
                          {autopilot.steps.map((step) => (
                            <article key={step.id} className={`uc-step ${statusTone(step.status)}`}>
                              <span>第 {step.chapter_number} 章</span><strong>{step.workflow}</strong><small>尝试 {step.attempt_count}/{step.max_retries + 1}</small><StatusBadge value={step.status} />
                              {step.status === 'failed' && <button type="button" onClick={() => void retryStep(step.id)}><RotateCcw size={14} />重试</button>}
                            </article>
                          ))}
                        </div>
                      </section>
                    ) : <EmptyState title="尚未创建托管任务" detail="设置章节范围并点击启动托管。" />}
                    <section className="uc-card"><div className="uc-card-heading"><div><span>运行事件</span><strong>最近 {autopilot.events.length} 条</strong></div></div><RowList empty="暂无运行事件" items={autopilot.events.slice(0, 20).map((event) => ({ title: event.event_type, detail: event.message, status: event.event_type.includes('failed') ? 'failed' : 'completed' }))} /></section>
                  </div>
                )}

                {projectId && section === 'continuity' && (
                  <div className="uc-section-stack">
                    <section className="uc-card"><div className="uc-card-heading"><div><span>最新章节</span><strong>{latestChapter ? `第 ${latestChapter.chapter_number} 章 · ${latestChapter.title}` : '暂无章节'}</strong></div>{latestCheck && <StatusBadge value={latestCheck.status} />}</div><p>系统在定稿前检查时间、地点、人物状态、知识边界、情绪、剧情衔接与重复内容。</p></section>
                    <div className="uc-check-grid">
                      {continuity.map((check) => (
                        <article className="uc-card" key={check.id}><div className="uc-card-heading"><div><span>{check.stage}</span><strong>{check.score} 分</strong></div><StatusBadge value={check.status} /></div><pre>{JSON.stringify(check.payload ?? {}, null, 2)}</pre></article>
                      ))}
                    </div>
                    {!continuity.length && <EmptyState title="暂无连续性检查" detail="完成一章托管或章节定稿后，这里会显示初检、修复和复检结果。" />}
                  </div>
                )}

                {projectId && section === 'memory' && (
                  <div className="uc-section-stack">
                    <div className="uc-metrics-grid"><MetricCard label="硬事实" value={hardFacts.length} detail="当前有效事实" /><MetricCard label="人物关系" value={relationships.length} detail="动态关系状态" /><MetricCard label="物品归属" value={items.length} detail="当前持有人与地点" /><MetricCard label="叙事债务" value={debts.length} detail="未解决承诺与问题" /><MetricCard label="活跃伏笔" value={foreshadowings.length} detail="待深化或回收" /></div>
                    <div className="uc-memory-grid">
                      <section className="uc-card"><div className="uc-card-heading"><strong>硬事实</strong></div><RowList empty="暂无硬事实" items={hardFacts.slice(0, 30).map((item) => ({ title: text(item.fact_text ?? item.fact_key), detail: `置信度 ${text(item.confidence, '0')}`, status: text(item.fact_status, 'confirmed') }))} /></section>
                      <section className="uc-card"><div className="uc-card-heading"><strong>人物关系</strong></div><RowList empty="暂无关系状态" items={relationships.slice(0, 30).map((item) => ({ title: `${text(item.source_character_name ?? item.source_character_key)} → ${text(item.target_character_name ?? item.target_character_key)}`, detail: `${text(item.relation_type)} · ${text(item.reason)}`, status: text(item.status, 'active') }))} /></section>
                      <section className="uc-card"><div className="uc-card-heading"><strong>物品归属</strong></div><RowList empty="暂无物品状态" items={items.slice(0, 30).map((item) => ({ title: text(item.item_name ?? item.item_key), detail: `${text(item.owner_name ?? item.owner_key)} · ${text(item.location)}`, status: text(item.status, 'held') }))} /></section>
                      <section className="uc-card"><div className="uc-card-heading"><strong>叙事债务与伏笔</strong></div><RowList empty="暂无开放债务或伏笔" items={[...debts.map((item) => ({ title: text(item.description ?? item.debt_key), detail: `截止第 ${text(item.deadline_chapter, '未设')} 章`, status: text(item.status, 'open') })), ...foreshadowings.map((item) => ({ title: text(item.title ?? item.foreshadowing_key), detail: `计划第 ${text(item.payoff_chapter, '未设')} 章回收`, status: text(item.status, 'planted') }))].slice(0, 40)} /></section>
                    </div>
                  </div>
                )}

                {projectId && section === 'graph' && (
                  <div className="uc-section-stack">
                    <div className="uc-metrics-grid"><MetricCard label="剧情线" value={threads.length} detail={`${stalled.length} 条停滞提醒`} /><MetricCard label="剧情节点" value={nodes.length} detail={`${nodes.filter((item) => text(item.status, '') === 'completed').length} 个已完成`} /><MetricCard label="剧情边" value={edges.length} detail="因果、依赖与回收关系" /></div>
                    <div className="uc-graph-columns">
                      <section className="uc-card"><div className="uc-card-heading"><strong>剧情线</strong></div><RowList empty="暂无剧情线" items={threads.map((item) => ({ title: text(item.title ?? item.thread_key), detail: `${text(item.current_stage)} → ${text(item.next_target)}`, status: text(item.status, 'active') }))} /></section>
                      <section className="uc-card"><div className="uc-card-heading"><strong>剧情节点</strong></div><RowList empty="暂无剧情节点" items={nodes.slice(0, 60).map((item) => ({ title: text(item.title ?? item.node_key), detail: `${text(item.thread_key)} · 第 ${text(item.planned_chapter, '未定')} 章`, status: text(item.status, 'planned') }))} /></section>
                      <section className="uc-card"><div className="uc-card-heading"><strong>节点关系</strong></div><RowList empty="暂无剧情边" items={edges.slice(0, 60).map((item) => ({ title: `${text(item.source_node_key)} → ${text(item.target_node_key)}`, detail: `${text(item.relation_type)} · 权重 ${text(item.weight, '1')}`, status: text(item.status, 'active') }))} /></section>
                    </div>
                  </div>
                )}

                {projectId && section === 'planning' && (
                  <div className="uc-section-stack">
                    <section className="uc-card"><div className="uc-card-heading"><div><span>未来章节滚动计划</span><strong>{plan.length} 个计划项</strong></div><BookOpenCheck size={19} /></div><p>锁定的计划不会被后续影响传播自动重排，已定稿章节也不会被改写。</p></section>
                    <div className="uc-plan-list">
                      {plan.map((item) => (
                        <article className="uc-card" key={item.chapter_number}><div className="uc-card-heading"><div><span>第 {item.chapter_number} 章</span><strong>{item.goal || '承接上一章并推进当前最高优先级剧情线'}</strong></div><StatusBadge value={item.status} /></div><div className="uc-plan-meta"><span>主线：{item.primary_thread_key || '未指定'}</span><span>风险：{Math.round(numberValue(item.risk_score) * 100)}%</span><span>版本：{item.revision ?? 1}</span></div>{item.must_address.length > 0 && <ul>{item.must_address.map((entry) => <li key={entry}>{entry}</li>)}</ul>}<button type="button" onClick={() => void togglePlanLock(item)}>{item.locked ? <Unlock size={15} /> : <Lock size={15} />}{item.locked ? '解锁计划' : '锁定计划'}</button></article>
                      ))}
                    </div>
                    {!plan.length && <EmptyState title="暂无滚动计划" detail="章节定稿后，影响传播会为未来 3—10 章生成滚动计划。" />}
                  </div>
                )}

                {projectId && section === 'worldlines' && (
                  <div className="uc-section-stack">
                    <section className="uc-card uc-form-card"><div className="uc-card-heading"><div><span>创建剧情分支</span><strong>从任意已存在章节分叉</strong></div><GitFork size={19} /></div><div className="uc-form-grid"><label>世界线名称<input value={forkName} onChange={(event) => setForkName(event.target.value)} /></label><label>分叉章节<input type="number" min="0" max={latestChapter?.chapter_number ?? 0} value={forkChapter} onChange={(event) => setForkChapter(Number(event.target.value))} /></label><label className="uc-wide">说明<textarea value={forkDescription} onChange={(event) => setForkDescription(event.target.value)} /></label></div><button className="uc-primary" type="button" onClick={() => void forkWorldline()} disabled={!forkName.trim() || Boolean(busyAction)}><GitFork size={16} />创建隔离世界线</button></section>
                    <div className="uc-worldline-list">
                      {(worldlines?.worldlines ?? []).map((line) => (
                        <article className={`uc-card ${line.is_active ? 'uc-current-line' : ''}`} key={line.id}><div className="uc-card-heading"><div><span>{line.is_primary ? '正式主线' : line.is_active ? '当前激活' : '剧情分支'}</span><strong>{line.name}</strong></div><StatusBadge value={line.status} /></div><p>{line.description || `从第 ${line.fork_chapter_number} 章分叉`}</p><div className="uc-plan-meta"><span>项目：{line.project_title || line.project_id.slice(0, 8)}</span><span>分叉：第 {line.fork_chapter_number} 章</span></div><div className="uc-actions">{!line.is_active && line.status === 'active' && <button type="button" onClick={() => void worldlineAction(line, 'activate')}><Play size={15} />激活</button>}{!line.is_primary && line.status === 'active' && <button type="button" onClick={() => void worldlineAction(line, 'promote')}><ShieldCheck size={15} />提升主线</button>}{!line.is_primary && !line.is_active && line.status === 'active' && <button className="uc-danger" type="button" onClick={() => void worldlineAction(line, 'archive')}><Archive size={15} />归档</button>}</div></article>
                      ))}
                    </div>
                  </div>
                )}

                {projectId && section === 'obsidian' && (
                  <div className="uc-section-stack">
                    <section className="uc-card uc-form-card"><div className="uc-card-heading"><div><span>Obsidian 知识库</span><strong>按当前世界线独立导出</strong></div><Database size={19} /></div><div className="uc-checkbox-row"><label><input type="checkbox" checked={includeDrafts} onChange={(event) => setIncludeDrafts(event.target.checked)} />包含草稿章节</label><label><input type="checkbox" checked={forceRebuild} onChange={(event) => setForceRebuild(event.target.checked)} />强制全量重建</label></div><div className="uc-actions"><button className="uc-primary" type="button" onClick={() => void exportObsidian()} disabled={Boolean(busyAction)}><Database size={16} />生成 Vault 与 ZIP</button>{text(obsidian.status, '') !== 'not_exported' && <a href={controlApi.obsidianDownloadUrl(projectId)}><Download size={16} />下载 ZIP</a>}</div></section>
                    <section className="uc-card"><div className="uc-card-heading"><div><span>导出状态</span><strong>{text(obsidian.status, 'not_exported')}</strong></div><StatusBadge value={text(obsidian.status, 'not_exported')} /></div><div className="uc-detail-grid"><div><span>Vault</span><strong>{text(obsidian.vault_path, '尚未生成')}</strong></div><div><span>ZIP</span><strong>{text(obsidian.archive_path, '尚未生成')}</strong></div><div><span>文件数</span><strong>{text(obsidian.file_count, '0')}</strong></div><div><span>世界线</span><strong>{worldlines?.worldlines.find((line) => line.project_id === projectId)?.name ?? '主世界线'}</strong></div></div></section>
                  </div>
                )}
              </main>
            </div>
          </section>
        </div>
      )}
    </>
  );
}
