import { useEffect, useMemo, useState } from 'react';
import { ArrowLeftRight, GitCompare, LoaderCircle } from 'lucide-react';
import {
  controlApi,
  type Worldline,
  type WorldlineComparison,
  type WorldlineMapDiff,
} from '../controlApi';

type Props = {
  projectId: string;
  worldlines: Worldline[];
};

function DiffGroup({ title, diff }: { title: string; diff: WorldlineMapDiff }) {
  const total = diff.only_left.length + diff.only_right.length + diff.changed.length;
  return (
    <article className="worldline-diff-card">
      <header>
        <strong>{title}</strong>
        <span>{total} 项差异</span>
      </header>
      <div className="worldline-diff-columns">
        <div>
          <span>仅左侧</span>
          {diff.only_left.length ? diff.only_left.map((item) => <code key={item}>{item}</code>) : <small>无</small>}
        </div>
        <div>
          <span>状态变化</span>
          {diff.changed.length ? diff.changed.map((item) => <code key={item}>{item}</code>) : <small>无</small>}
        </div>
        <div>
          <span>仅右侧</span>
          {diff.only_right.length ? diff.only_right.map((item) => <code key={item}>{item}</code>) : <small>无</small>}
        </div>
      </div>
    </article>
  );
}

function defaultPair(worldlines: Worldline[]) {
  const active = worldlines.filter((line) => line.status === 'active');
  const primary = active.find((line) => line.is_primary) ?? active[0];
  const alternative = active.find((line) => line.id !== primary?.id);
  return { left: primary?.id ?? '', right: alternative?.id ?? '' };
}

export default function WorldlineComparePanel({ projectId, worldlines }: Props) {
  const defaults = useMemo(() => defaultPair(worldlines), [worldlines]);
  const [leftId, setLeftId] = useState(defaults.left);
  const [rightId, setRightId] = useState(defaults.right);
  const [comparison, setComparison] = useState<WorldlineComparison | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    setLeftId(defaults.left);
    setRightId(defaults.right);
    setComparison(null);
  }, [defaults.left, defaults.right, projectId]);

  async function compare() {
    if (!leftId || !rightId || leftId === rightId) return;
    setLoading(true);
    setError('');
    try {
      setComparison(await controlApi.compareWorldlines(projectId, leftId, rightId));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '世界线比较失败');
    } finally {
      setLoading(false);
    }
  }

  const activeLines = worldlines.filter((line) => line.status === 'active');
  if (activeLines.length < 2) {
    return (
      <section className="uc-card worldline-compare-empty">
        <GitCompare size={20} />
        <div>
          <strong>需要至少两条有效世界线</strong>
          <p>创建剧情分支后，可比较章节、事实、剧情线、节点和滚动计划差异。</p>
        </div>
      </section>
    );
  }

  return (
    <section className="uc-card worldline-compare-panel">
      <div className="uc-card-heading">
        <div>
          <span>世界线差异</span>
          <strong>并排比较两个故事方向</strong>
        </div>
        <ArrowLeftRight size={19} />
      </div>
      <div className="worldline-compare-controls">
        <label>
          左侧世界线
          <select value={leftId} onChange={(event) => setLeftId(event.target.value)} aria-label="左侧世界线">
            {activeLines.map((line) => <option key={line.id} value={line.id}>{line.name}</option>)}
          </select>
        </label>
        <label>
          右侧世界线
          <select value={rightId} onChange={(event) => setRightId(event.target.value)} aria-label="右侧世界线">
            {activeLines.map((line) => <option key={line.id} value={line.id}>{line.name}</option>)}
          </select>
        </label>
        <button className="uc-primary" type="button" onClick={() => void compare()} disabled={loading || !leftId || !rightId || leftId === rightId}>
          {loading ? <LoaderCircle className="uc-spin" size={16} /> : <GitCompare size={16} />}
          开始比较
        </button>
      </div>

      {error && <p className="worldline-compare-error">{error}</p>}
      {comparison && (
        <div className="worldline-compare-results">
          <div className="worldline-compare-summary">
            <article>
              <span>左侧</span>
              <strong>{comparison.left.name}</strong>
              <small>{comparison.left.chapter_count ?? comparison.left.latest_chapter_number ?? 0} 章</small>
            </article>
            <article>
              <span>共同前缀</span>
              <strong>第 {comparison.shared_prefix_chapter} 章</strong>
              <small>{comparison.chapter_differences.length} 个章节差异</small>
            </article>
            <article>
              <span>右侧</span>
              <strong>{comparison.right.name}</strong>
              <small>{comparison.right.chapter_count ?? comparison.right.latest_chapter_number ?? 0} 章</small>
            </article>
          </div>

          <div className="worldline-chapter-diffs">
            {comparison.chapter_differences.map((difference) => (
              <article key={difference.chapter_number}>
                <span>第 {difference.chapter_number} 章</span>
                <strong>{difference.change}</strong>
                <div>
                  <small>{String(difference.left?.title ?? '左侧无此章')}</small>
                  <small>{String(difference.right?.title ?? '右侧无此章')}</small>
                </div>
              </article>
            ))}
            {!comparison.chapter_differences.length && <p>两条世界线的章节正文和状态目前一致。</p>}
          </div>

          <div className="worldline-diff-grid">
            <DiffGroup title="记忆事实" diff={comparison.memory_facts} />
            <DiffGroup title="剧情线" diff={comparison.story_threads} />
            <DiffGroup title="剧情节点" diff={comparison.story_nodes} />
            <DiffGroup title="滚动计划" diff={comparison.rolling_plan} />
          </div>
        </div>
      )}
    </section>
  );
}
