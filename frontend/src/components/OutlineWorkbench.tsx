import { BookMarked, GitBranch, Sparkles, Trash2 } from 'lucide-react';
import { Chapter, GenericRecord, OutlinePayload, WorkbenchAIResult } from '../api';
import { AIResultCard } from './AIResultCard';

type OutlineGenerateMode = 'five' | 'ten' | 'twenty' | 'expand' | 'rhythm';

type OutlineWorkbenchProps = {
  records: GenericRecord[];
  chapters: Chapter[];
  form: OutlinePayload;
  scope: 'global' | 'chapter';
  aiResults: WorkbenchAIResult[];
  modelLabel: string;
  editingRecordId?: string;
  onScopeChange: (scope: 'global' | 'chapter') => void;
  onFormChange: (field: keyof OutlinePayload, value: string) => void;
  onSave: () => void;
  onSelectRecord: (record: GenericRecord) => void;
  onCancelEdit: () => void;
  onGenerate: (mode: OutlineGenerateMode) => void;
  onApplyResult: (content: string) => void;
  onSaveResult: (content: string) => void;
  onCreateGlobalOutline: () => void;
  onDeleteRecord: (recordId: string) => void;
  onDeleteResult?: (id: string) => void;
};

const fields: Array<{
  key: keyof OutlinePayload;
  label: string;
  type?: 'input' | 'textarea';
}> = [
  { key: 'volume', label: '分卷', type: 'input' },
  { key: 'chapter_title', label: '章节标题', type: 'input' },
  { key: 'chapter_goal', label: '本章目标' },
  { key: 'main_conflict', label: '主要冲突' },
  { key: 'key_events', label: '关键事件' },
  { key: 'emotional_rhythm', label: '情绪节奏' },
  { key: 'foreshadowing', label: '伏笔' },
  { key: 'hook', label: '结尾钩子' },
  { key: 'related_characters', label: '关联角色', type: 'input' },
  { key: 'completion_status', label: '完成状态', type: 'input' },
];

export function OutlineWorkbench({
  records,
  chapters,
  form,
  scope,
  aiResults,
  modelLabel,
  editingRecordId = '',
  onScopeChange,
  onFormChange,
  onSave,
  onSelectRecord,
  onCancelEdit,
  onGenerate,
  onApplyResult,
  onSaveResult,
  onCreateGlobalOutline,
  onDeleteRecord,
  onDeleteResult,
}: OutlineWorkbenchProps) {
  const globalOutline = records.find((record) => record.category === 'global_outline');
  const chapterOutlines = records.filter((record) => record.category !== 'global_outline');
  const selectedOutline = chapterOutlines.find((record) => record.id === editingRecordId);
  const editingRecord = records.find((record) => record.id === editingRecordId);

  return (
    <section className="special-workbench outline-workbench">
      <aside className="workbench-side-list">
        <div className="workbench-panel-head">
          <span>Outline Board</span>
          <h3>大纲工作台</h3>
          <small>章节大纲：{chapterOutlines.length} / 章节：{chapters.length}</small>
        </div>
        <div className="global-outline-card">
          <span>全书总纲 / 主线轨道</span>
          <p>{globalOutline?.content || '还没有贯穿整本书的总纲。先创建主线轨道，后续章节生成会围绕它防偏航。'}</p>
          <button className="ghost-action" onClick={() => (globalOutline ? onSelectRecord(globalOutline) : onCreateGlobalOutline())}>
            {globalOutline ? '编辑全书总纲' : '创建全书总纲'}
          </button>
        </div>
        <div className="entity-list compact-entity-selector" aria-label="分卷与章节">
          <strong>
            <BookMarked size={16} />
            选择章节大纲
          </strong>
          <select
            aria-label="选择章节大纲"
            value={selectedOutline?.id ?? ''}
            onChange={(event) => {
              const record = chapterOutlines.find((item) => item.id === event.target.value);
              if (record) onSelectRecord(record);
            }}
          >
            <option value="">选择要编辑的章节大纲</option>
            {chapterOutlines.map((record) => (
              <option key={record.id} value={record.id}>
                {record.title || '未命名章节'}
              </option>
            ))}
          </select>
          {selectedOutline ? (
            <article className="selected-record-card outline-preview-card">
              <h4>{selectedOutline.title || '未命名章节'}</h4>
              <p>{selectedOutline.content || '暂无章节目标与关键事件'}</p>
              <span>{selectedOutline.status || selectedOutline.category}</span>
            </article>
          ) : (
            <p className="empty-state">{chapterOutlines.length === 0 ? '还没有章节大纲，先让 AI 生成多章大纲或手动保存一章。' : '选择一个章节大纲后在中间编辑。'}</p>
          )}
        </div>
      </aside>

      <div className="structured-editor-panel">
        <div className="workbench-panel-head">
          <span>Chapter Outline</span>
          <h3>{scope === 'global' ? '全书总纲 / 主线轨道' : editingRecordId ? '编辑章节剧情板' : '章节剧情板'}</h3>
          <small>{scope === 'global' ? '定义整本书的主线承诺、终局方向和大伏笔，防止章节越写越偏。' : editingRecordId ? '保存后会替换当前大纲记录，并同步覆盖 llmwiki 大纲页。' : '把目标、冲突、事件、伏笔和钩子拆开管理，方便后续写正文。'}</small>
        </div>
        <div className="scope-switch">
          <button className={scope === 'chapter' ? 'active' : ''} onClick={() => onScopeChange('chapter')}>章节大纲</button>
          <button className={scope === 'global' ? 'active' : ''} onClick={() => onScopeChange('global')}>全书总纲</button>
        </div>
        <div className="structured-grid">
          {fields.map((field) => (
            <label key={field.key}>
              {field.label}
              {field.type === 'input' ? (
                <input
                  aria-label={field.label}
                  value={form[field.key]}
                  onChange={(event) => onFormChange(field.key, event.target.value)}
                />
              ) : (
                <textarea
                  aria-label={field.label}
                  value={form[field.key]}
                  onChange={(event) => onFormChange(field.key, event.target.value)}
                />
              )}
            </label>
          ))}
        </div>
        <button className="primary-action" onClick={onSave}>
          <GitBranch size={16} />
          {scope === 'global' ? '保存全书总纲并同步 llmwiki' : editingRecordId ? '更新大纲并同步 llmwiki' : '保存大纲'}
        </button>
        {scope === 'chapter' && (
          <button className="secondary-action" onClick={() => onGenerate('expand')}>
            <Sparkles size={15} />
            重新生成本章大纲
          </button>
        )}
        {editingRecordId && (
          <button className="secondary-action" onClick={onCancelEdit}>
            取消编辑，改为新建大纲
          </button>
        )}
        {editingRecord && (
          <button className="danger-action outline-delete-action" onClick={() => onDeleteRecord(editingRecord.id)}>
            <Trash2 size={15} />
            {editingRecord.category === 'global_outline' ? '删除全书总纲' : '删除章节大纲'}
          </button>
        )}
      </div>

      <aside className="workbench-ai-panel">
        <div className="workbench-panel-head">
          <span>AI Outline Lab</span>
          <h3>AI 大纲候选</h3>
          <small>{modelLabel}</small>
        </div>
        <div className="ai-action-grid">
          <button onClick={() => onGenerate('five')}>
            <Sparkles size={15} />
            生成 5 章大纲
          </button>
          <button onClick={() => onGenerate('ten')}>
            <Sparkles size={15} />
            生成 10 章大纲
          </button>
          <button onClick={() => onGenerate('twenty')}>
            <Sparkles size={15} />
            生成 20 章大纲
          </button>
          <button onClick={() => onGenerate('expand')}>
            <Sparkles size={15} />
            扩展本章梗概
          </button>
          <button onClick={() => onGenerate('rhythm')}>
            <Sparkles size={15} />
            检查节奏断点
          </button>
        </div>
        <div className="workbench-result-list">
          {aiResults.length > 0 && <strong className="result-section-title">多章大纲候选，可逐章保存</strong>}
          {aiResults.map((result) => (
            <div className="outline-candidate-card" key={result.id}>
              <AIResultCard
                result={result}
                canApply
                canFavorite
                onApply={() => onApplyResult(result.content)}
                onDelete={onDeleteResult ? () => onDeleteResult(result.id) : undefined}
              />
              <button className="secondary-action" onClick={() => onSaveResult(result.content)}>
                保存为独立章节大纲
              </button>
            </div>
          ))}
          {aiResults.length === 0 && <p className="empty-state">AI 生成的大纲候选会显示在这里，可加入关键事件。</p>}
        </div>
      </aside>
    </section>
  );
}
