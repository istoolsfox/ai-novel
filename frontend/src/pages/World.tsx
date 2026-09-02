import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { Globe, History, Pencil, Plus, Sparkles, Trash2 } from 'lucide-react';
import { GenericRecord } from '../api';
import { useRecords } from '../shell/useRecords';
import { ConfirmDialog, EmptyState, PageHeader } from '../ui/basics';
import { AIGenerateModal } from '../components/AIGenerateModal';
import { HistoryDrawer } from '../components/HistoryDrawer';
import { FieldDef, RecordFormModal } from '../components/RecordFormModal';

const RESOURCE = 'world-settings';

const CATEGORIES = [
  { value: 'Locations', label: '地点' },
  { value: 'Organizations', label: '组织' },
  { value: 'Companies', label: '企业' },
  { value: 'Families', label: '家族' },
  { value: 'Countries', label: '国家 / 势力' },
  { value: 'Rules', label: '世界运行逻辑' },
  { value: 'Objects', label: '关键物品' },
];

const WORLD_FIELDS: FieldDef[] = [
  { key: 'title', label: '名称', required: true, placeholder: '如：灰塔旧城区' },
  { key: 'category', label: '类别', type: 'select', options: CATEGORIES.map((item) => item.value) },
  { key: 'content', label: '设定说明', type: 'textarea', rows: 6, placeholder: '这个地方/组织/规则如何运作？与主线有什么关系？' },
];

export function World() {
  const { projectId } = useParams();
  const { records, create, update, remove, reload } = useRecords(projectId, RESOURCE);
  const [activeCategory, setActiveCategory] = useState('Locations');
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<GenericRecord | null>(null);
  const [aiOpen, setAiOpen] = useState(false);
  const [historyFor, setHistoryFor] = useState<GenericRecord | null>(null);
  const [deleting, setDeleting] = useState<GenericRecord | null>(null);

  const categoryLabel = (value: string) => CATEGORIES.find((item) => item.value === value)?.label ?? value;
  const scoped = records.filter((record) => record.category === activeCategory);

  const saveForm = async (values: Partial<GenericRecord>) => {
    if (values.id) {
      await update(String(values.id), values);
      return;
    }
    await create(values);
  };

  return (
    <div className="page-inner wide">
      <PageHeader
        title="世界观"
        sub="地点、组织、家族、国家、关键物品，以及世界运行逻辑（Rules）——它们共同支撑小说的可信度。"
        actions={
          <>
            <button className="btn" onClick={() => { setEditing(null); setFormOpen(true); }}>
              <Plus size={14} /> 新建实体
            </button>
            <button className="btn btn-ai" onClick={() => setAiOpen(true)}>
              <Sparkles size={14} /> AI 生成设定
            </button>
          </>
        }
      />

      <div className="tabs" role="tablist" aria-label="世界观分类">
        {CATEGORIES.map((category) => (
          <button
            key={category.value}
            role="tab"
            aria-selected={activeCategory === category.value}
            className={activeCategory === category.value ? 'tab active' : 'tab'}
            onClick={() => setActiveCategory(category.value)}
          >
            {category.label}
            <span className="muted" style={{ marginLeft: 4 }}>
              {records.filter((record) => record.category === category.value).length || ''}
            </span>
          </button>
        ))}
      </div>

      <section className="section" style={{ marginTop: 20 }}>
        {scoped.length === 0 ? (
          <EmptyState
            icon={<Globe size={26} />}
            title={`暂无「${categoryLabel(activeCategory)}」`}
            hint="手动添加，或让 AI 围绕你的故事概念生成一批设定。"
            action={
              <div className="row-flex">
                <button className="btn" onClick={() => { setEditing(null); setFormOpen(true); }}>
                  <Plus size={14} /> 新建
                </button>
                <button className="btn btn-ai" onClick={() => setAiOpen(true)}>
                  <Sparkles size={14} /> AI 生成
                </button>
              </div>
            }
          />
        ) : (
          <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))' }}>
            {scoped.map((record) => (
              <article key={record.id} className="card" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                <div className="row-flex">
                  <b style={{ fontFamily: 'var(--serif)', fontSize: 15.5, flex: 1 }}>{record.title}</b>
                  <button className="icon-btn" aria-label={`编辑 ${record.title}`} onClick={() => { setEditing(record); setFormOpen(true); }}>
                    <Pencil size={13} />
                  </button>
                  <button className="icon-btn" aria-label={`${record.title} 历史`} onClick={() => setHistoryFor(record)}>
                    <History size={13} />
                  </button>
                  <button className="icon-btn" aria-label={`删除 ${record.title}`} onClick={() => setDeleting(record)}>
                    <Trash2 size={13} />
                  </button>
                </div>
                <p className="muted" style={{ fontSize: 12.5, lineHeight: 1.75, flex: 1 }}>
                  {record.content || '暂无说明'}
                </p>
                <span className="badge" style={{ alignSelf: 'flex-start' }}>{categoryLabel(record.category)}</span>
              </article>
            ))}
          </div>
        )}
      </section>

      {formOpen && (
        <RecordFormModal
          modalTitle={editing ? `编辑 · ${editing.title}` : `新建${categoryLabel(activeCategory)}`}
          fields={WORLD_FIELDS}
          record={editing}
          extraValues={editing ? undefined : { category: activeCategory }}
          onClose={() => setFormOpen(false)}
          onSave={saveForm}
        />
      )}

      {aiOpen && projectId && (
        <AIGenerateModal
          projectId={projectId}
          title="AI 生成世界观设定"
          intro="AI 会生成地点、组织、规则、物品等一组设定；保存后可逐条修改，修改会自动保留版本。"
          workflow="generate_setting"
          buildPayload={(prompt) => ({
            prompt: prompt || `围绕当前项目生成${categoryLabel(activeCategory)}相关的设定`,
            existing_world: records.map((record) => ({ title: record.title, category: record.category })),
          })}
          onSave={async (items) => {
            for (const item of items) {
              const payload = (item.payload ?? {}) as Record<string, unknown>;
              await create({
                title: item.title,
                category: typeof payload.category === 'string' && payload.category ? payload.category : activeCategory,
                content: item.content,
                payload,
                status: 'active',
              });
            }
            await reload();
          }}
          onClose={() => setAiOpen(false)}
        />
      )}

      {historyFor && projectId && (
        <HistoryDrawer
          projectId={projectId}
          resource={RESOURCE}
          record={historyFor}
          onClose={() => setHistoryFor(null)}
          onRestored={(updated) => {
            void reload();
            setHistoryFor((prev) => (prev ? { ...prev, ...updated } : prev));
          }}
        />
      )}

      {deleting && (
        <ConfirmDialog
          title="删除实体"
          danger
          confirmLabel="删除"
          message={<>将删除「<b>{deleting.title}</b>」及其全部历史版本。</>}
          onConfirm={() => {
            void remove(deleting.id);
            setDeleting(null);
          }}
          onCancel={() => setDeleting(null)}
        />
      )}
    </div>
  );
}
