import { Sparkles, UserPlus } from 'lucide-react';
import { CharacterProfilePayload, GenericRecord, WorkbenchAIResult } from '../api';
import { AIResultCard } from './AIResultCard';

type CharacterGenerateMode = 'new' | 'complete' | 'dialogue' | 'consistency';

type CharacterWorkbenchProps = {
  records: GenericRecord[];
  form: CharacterProfilePayload;
  aiResults: WorkbenchAIResult[];
  modelLabel: string;
  saveStatus?: string;
  editingRecordId?: string;
  onFormChange: (field: keyof CharacterProfilePayload, value: string) => void;
  onSave: () => void;
  onSelectRecord: (record: GenericRecord) => void;
  onCancelEdit: () => void;
  onGenerate: (mode: CharacterGenerateMode) => void;
  onApplyResult: (content: string) => void;
  onDeleteResult?: (id: string) => void;
};

const fields: Array<{
  key: keyof CharacterProfilePayload;
  label: string;
  type?: 'input' | 'textarea';
}> = [
  { key: 'name', label: '姓名', type: 'input' },
  { key: 'role', label: '身份', type: 'input' },
  { key: 'faction', label: '阵营', type: 'input' },
  { key: 'appearance', label: '年龄 / 外貌' },
  { key: 'traits', label: '性格关键词' },
  { key: 'desire', label: '欲望目标' },
  { key: 'fear', label: '恐惧 / 弱点' },
  { key: 'mainline_relation', label: '与主线关系' },
  { key: 'arc', label: '人物弧光' },
  { key: 'voice', label: '口癖 / 说话方式' },
  { key: 'related_chapters', label: '相关章节', type: 'input' },
  { key: 'notes', label: '备注' },
];

export function CharacterWorkbench({
  records,
  form,
  aiResults,
  modelLabel,
  saveStatus = '',
  editingRecordId = '',
  onFormChange,
  onSave,
  onSelectRecord,
  onCancelEdit,
  onGenerate,
  onApplyResult,
  onDeleteResult,
}: CharacterWorkbenchProps) {
  return (
    <section className="special-workbench character-workbench">
      <aside className="workbench-side-list">
        <div className="workbench-panel-head">
          <span>Story Bible</span>
          <h3>角色工作台</h3>
          <small>角色数量：{records.length}</small>
        </div>
        <button className="primary-action" onClick={() => onGenerate('new')}>
          <UserPlus size={16} />
          AI 生成新角色
        </button>
        <div className="entity-list" aria-label="角色列表">
          <strong>角色列表</strong>
          {records.map((record) => (
            <article key={record.id} className={record.id === editingRecordId ? 'selected-record-card' : ''}>
              <h4>{record.title || '未命名角色'}</h4>
              <p>{record.content || '暂无角色摘要'}</p>
              <span>{record.status || record.category}</span>
              <button className="ghost-action" onClick={() => onSelectRecord(record)}>
                编辑角色 {record.title || '未命名角色'}
              </button>
            </article>
          ))}
          {records.length === 0 && <p className="empty-state">还没有角色卡，先用 AI 生成或手动保存一个角色。</p>}
        </div>
      </aside>

      <div className="structured-editor-panel">
        <div className="workbench-panel-head">
          <span>Character Card</span>
          <h3>{editingRecordId ? '编辑角色卡' : '可编辑角色卡'}</h3>
          <small>{editingRecordId ? '保存后会替换当前角色资料，并同步覆盖 llmwiki 角色页。' : '结构化资料会进入当前项目的故事圣经。'}</small>
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
          {editingRecordId ? '更新角色卡并同步 llmwiki' : '保存角色卡'}
        </button>
        {editingRecordId && (
          <button className="secondary-action" onClick={onCancelEdit}>
            取消编辑，改为新建角色
          </button>
        )}
        {saveStatus && <p className="form-status-message">{saveStatus}</p>}
      </div>

      <aside className="workbench-ai-panel">
        <div className="workbench-panel-head">
          <span>AI Character Lab</span>
          <h3>角色生成与一致性</h3>
          <small>{modelLabel}</small>
        </div>
        <div className="ai-action-grid">
          <button onClick={() => onGenerate('complete')}>
            <Sparkles size={15} />
            AI 补全角色
          </button>
          <button onClick={() => onGenerate('dialogue')}>
            <Sparkles size={15} />
            生成角色对白
          </button>
          <button onClick={() => onGenerate('consistency')}>
            <Sparkles size={15} />
            检查人物一致性
          </button>
        </div>
        <div className="workbench-result-list">
          {aiResults.map((result) => (
            <AIResultCard
              key={result.id}
              result={result}
              canApply
              canFavorite
              onApply={() => onApplyResult(result.content)}
              onDelete={onDeleteResult ? () => onDeleteResult(result.id) : undefined}
            />
          ))}
          {aiResults.length === 0 && <p className="empty-state">AI 结果会显示在这里，可一键应用到角色备注。</p>}
        </div>
      </aside>
    </section>
  );
}
