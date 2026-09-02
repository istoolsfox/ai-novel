import { useEffect, useState } from 'react';
import { History, RotateCcw, Sparkles } from 'lucide-react';
import { api, GenericRecord, RecordRevision } from '../api';
import { Drawer, EmptyState } from '../ui/basics';

const ORIGIN_LABEL: Record<string, string> = {
  create: '创建',
  update: '修改',
  restore: '恢复版本',
  manual: '手动',
};

function formatTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
}

export function HistoryDrawer({
  projectId,
  resource,
  record,
  onClose,
  onRestored,
}: {
  projectId: string;
  resource: string;
  record: Pick<GenericRecord, 'id' | 'title'>;
  onClose: () => void;
  onRestored: (updated: GenericRecord) => void;
}) {
  const [revisions, setRevisions] = useState<RecordRevision[]>([]);
  const [loading, setLoading] = useState(true);
  const [restoring, setRestoring] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    let alive = true;
    setLoading(true);
    api
      .listRecordRevisions(projectId, resource, record.id)
      .then((items) => {
        if (alive) setRevisions(items);
      })
      .catch(() => {
        if (alive) setError('版本历史加载失败');
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [projectId, resource, record.id]);

  const restore = async (revision: RecordRevision) => {
    if (restoring) return;
    setRestoring(revision.id);
    setError('');
    try {
      const updated = await api.restoreRecordRevision(projectId, resource, record.id, revision.id);
      setRevisions((items) => [{ ...revision, id: `${revision.id}`, origin: 'restore' }, ...items]);
      onRestored(updated);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : '恢复失败');
    } finally {
      setRestoring('');
    }
  };

  return (
    <Drawer
      title={
        <span className="row-flex">
          <History size={15} /> 版本历史 · {record.title || '未命名'}
        </span>
      }
      onClose={onClose}
    >
      {error && <div className="notice">{error}</div>}
      {loading && <p className="muted">加载中…</p>}
      {!loading && revisions.length === 0 && (
        <EmptyState title="暂无历史版本" hint="每次创建或修改都会自动记录一个版本。" />
      )}
      {revisions.map((revision, index) => (
        <article key={revision.id} className={index === 0 ? 'revision current' : 'revision'}>
          <div className="revision-head">
            <b>{formatTime(revision.created_at)}</b>
            <span className={revision.origin === 'create' ? 'badge' : 'badge accent'}>
              {ORIGIN_LABEL[revision.origin] ?? revision.origin}
            </span>
            {index === 0 && <span className="badge ok">当前</span>}
            <span className="spacer" />
            {index !== 0 && (
              <button className="btn" style={{ fontSize: 12, padding: '3px 9px' }} disabled={Boolean(restoring)} onClick={() => void restore(revision)}>
                <RotateCcw size={12} /> {restoring === revision.id ? '恢复中…' : '恢复此版本'}
              </button>
            )}
          </div>
          {revision.title && <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 4 }}>{revision.title}</div>}
          <div className="revision-content">{revision.content || '（无内容）'}</div>
        </article>
      ))}
      {!loading && revisions.length > 0 && (
        <p className="muted" style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12 }}>
          <Sparkles size={12} /> 每次修改都会自动留档，可随时回退。
        </p>
      )}
    </Drawer>
  );
}
