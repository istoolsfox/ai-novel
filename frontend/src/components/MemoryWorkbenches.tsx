import { AlertTriangle, BookOpen, GitBranch, Library, Save, Sparkles } from 'lucide-react';
import {
  ForeshadowingPayload,
  GenericRecord,
  KnowledgeDocumentPayload,
  TabooRulePayload,
  TimelineEventPayload,
  WorkbenchAIResult,
} from '../api';
import { AIResultCard } from './AIResultCard';

type TimelineWorkbenchProps = {
  records: GenericRecord[];
  form: TimelineEventPayload;
  aiResults: WorkbenchAIResult[];
  modelLabel: string;
  editingRecordId?: string;
  onFormChange: (field: keyof TimelineEventPayload, value: string) => void;
  onSave: () => void;
  onSelectRecord: (record: GenericRecord) => void;
  onCancelEdit: () => void;
  onExtract: () => void;
  onApplyResult: (content: string) => void;
  onDeleteResult?: (id: string) => void;
};

type ForeshadowingWorkbenchProps = {
  records: GenericRecord[];
  form: ForeshadowingPayload;
  aiResults: WorkbenchAIResult[];
  modelLabel: string;
  editingRecordId?: string;
  onFormChange: (field: keyof ForeshadowingPayload, value: string) => void;
  onSave: () => void;
  onSelectRecord: (record: GenericRecord) => void;
  onCancelEdit: () => void;
  onExtract: () => void;
  onApplyResult: (content: string) => void;
  onDeleteResult?: (id: string) => void;
};

type TabooRulesWorkbenchProps = {
  records: GenericRecord[];
  form: TabooRulePayload;
  aiResults: WorkbenchAIResult[];
  modelLabel: string;
  editingRecordId?: string;
  onFormChange: (field: keyof TabooRulePayload, value: string) => void;
  onSave: () => void;
  onSelectRecord: (record: GenericRecord) => void;
  onCancelEdit: () => void;
  onCheck: () => void;
  onApplyResult: (content: string) => void;
  onDeleteResult?: (id: string) => void;
};

type KnowledgeWikiWorkbenchProps = {
  records: GenericRecord[];
  wikiPages: Array<{ path: string; content: string }>;
  form: KnowledgeDocumentPayload;
  editingRecordId?: string;
  onFormChange: (field: keyof KnowledgeDocumentPayload, value: string) => void;
  onSave: () => void;
  onSelectRecord: (record: GenericRecord) => void;
  onCancelEdit: () => void;
};

export function TimelineWorkbench({
  records,
  form,
  aiResults,
  modelLabel,
  editingRecordId = '',
  onFormChange,
  onSave,
  onSelectRecord,
  onCancelEdit,
  onExtract,
  onApplyResult,
  onDeleteResult,
}: TimelineWorkbenchProps) {
  return (
    <section className="special-workbench memory-workbench">
      <RecordRail
        title="时间线工作台"
        kicker="Timeline"
        count={records.length}
        records={records}
        empty="章节定稿或 AI 提取后，事件会进入这里和 timeline.md。"
        editingRecordId={editingRecordId}
        editLabel="编辑时间线"
        onSelectRecord={onSelectRecord}
      />
      <div className="structured-editor-panel">
        <div className="workbench-panel-head">
          <span>Cause And Effect</span>
          <h3>{editingRecordId ? '编辑事件因果卡' : '事件因果卡'}</h3>
          <small>{editingRecordId ? '保存后会替换当前时间线事件，并同步覆盖 timeline.md。' : '记录事件时间、章节、参与角色和后果，供后续章节生成读取。'}</small>
        </div>
        <div className="structured-grid">
          <label>
            事件时间
            <input aria-label="事件时间" value={form.event_time} onChange={(event) => onFormChange('event_time', event.target.value)} />
          </label>
          <label>
            关联章节
            <input aria-label="关联章节" value={form.chapter} onChange={(event) => onFormChange('chapter', event.target.value)} />
          </label>
          <label>
            参与角色
            <input aria-label="参与角色" value={form.characters} onChange={(event) => onFormChange('characters', event.target.value)} />
          </label>
          <label>
            状态
            <select aria-label="事件状态" value={form.status} onChange={(event) => onFormChange('status', event.target.value)}>
              <option value="待确认">待确认</option>
              <option value="已发生">已发生</option>
              <option value="伏笔中">伏笔中</option>
              <option value="需回收">需回收</option>
            </select>
          </label>
          <label>
            因果说明
            <textarea aria-label="因果说明" value={form.cause} onChange={(event) => onFormChange('cause', event.target.value)} />
          </label>
          <label>
            后续影响
            <textarea aria-label="后续影响" value={form.consequence} onChange={(event) => onFormChange('consequence', event.target.value)} />
          </label>
        </div>
        <button className="primary-action" onClick={onSave}>
          <Save size={16} />
          {editingRecordId ? '更新时间线事件并同步 llmwiki' : '保存时间线事件'}
        </button>
        {editingRecordId && (
          <button className="secondary-action" onClick={onCancelEdit}>
            取消编辑，改为新建事件
          </button>
        )}
      </div>
      <AIWorkbenchRail
        title="AI 时间线提取"
        modelLabel={modelLabel}
        actionLabel="从当前章节提取事件"
        aiResults={aiResults}
        onAction={onExtract}
        onApplyResult={onApplyResult}
        onDeleteResult={onDeleteResult}
      />
    </section>
  );
}

export function ForeshadowingWorkbench({
  records,
  form,
  aiResults,
  modelLabel,
  editingRecordId = '',
  onFormChange,
  onSave,
  onSelectRecord,
  onCancelEdit,
  onExtract,
  onApplyResult,
  onDeleteResult,
}: ForeshadowingWorkbenchProps) {
  return (
    <section className="special-workbench memory-workbench">
      <RecordRail
        title="伏笔工作台"
        kicker="Foreshadowing"
        count={records.length}
        records={records}
        empty="未回收伏笔会在章节生成前作为提醒注入上下文。"
        editingRecordId={editingRecordId}
        editLabel="编辑伏笔"
        onSelectRecord={onSelectRecord}
      />
      <div className="structured-editor-panel">
        <div className="workbench-panel-head">
          <span>Setup And Payoff</span>
          <h3>{editingRecordId ? '编辑埋线 / 回收卡' : '埋线 / 回收卡'}</h3>
          <small>{editingRecordId ? '保存后会替换当前伏笔记录，并同步覆盖 foreshadowing.md。' : '让 AI 知道哪些线索不能忘，哪些悬念需要在后文回收。'}</small>
        </div>
        <div className="structured-grid">
          <label>
            埋设章节
            <input aria-label="埋设章节" value={form.setup_chapter} onChange={(event) => onFormChange('setup_chapter', event.target.value)} />
          </label>
          <label>
            回收章节
            <input aria-label="回收章节" value={form.payoff_chapter} onChange={(event) => onFormChange('payoff_chapter', event.target.value)} />
          </label>
          <label>
            状态
            <select aria-label="伏笔状态" value={form.status} onChange={(event) => onFormChange('status', event.target.value)}>
              <option value="open">未回收</option>
              <option value="planned">计划回收</option>
              <option value="paid_off">已回收</option>
            </select>
          </label>
          <label>
            相关角色
            <input aria-label="相关角色" value={form.related_characters} onChange={(event) => onFormChange('related_characters', event.target.value)} />
          </label>
          <label>
            提示语
            <textarea aria-label="提示语" value={form.hint} onChange={(event) => onFormChange('hint', event.target.value)} />
          </label>
          <label>
            回收计划
            <textarea aria-label="回收计划" value={form.payoff_plan} onChange={(event) => onFormChange('payoff_plan', event.target.value)} />
          </label>
        </div>
        <button className="primary-action" onClick={onSave}>
          <Save size={16} />
          {editingRecordId ? '更新伏笔并同步 llmwiki' : '保存伏笔'}
        </button>
        {editingRecordId && (
          <button className="secondary-action" onClick={onCancelEdit}>
            取消编辑，改为新建伏笔
          </button>
        )}
      </div>
      <AIWorkbenchRail
        title="AI 伏笔提取"
        modelLabel={modelLabel}
        actionLabel="从当前章节提取伏笔"
        aiResults={aiResults}
        onAction={onExtract}
        onApplyResult={onApplyResult}
        onDeleteResult={onDeleteResult}
      />
    </section>
  );
}

export function TabooRulesWorkbench({
  records,
  form,
  aiResults,
  modelLabel,
  editingRecordId = '',
  onFormChange,
  onSave,
  onSelectRecord,
  onCancelEdit,
  onCheck,
  onApplyResult,
  onDeleteResult,
}: TabooRulesWorkbenchProps) {
  return (
    <section className="special-workbench memory-workbench">
      <RecordRail
        title="雷点规则工作台"
        kicker="Taboo Rules"
        count={records.length}
        records={records}
        empty="雷点规则会注入章节生成 prompt，检查结果只提示风险，不自动覆盖正文。"
        editingRecordId={editingRecordId}
        editLabel="编辑雷点规则"
        onSelectRecord={onSelectRecord}
      />
      <div className="structured-editor-panel">
        <div className="workbench-panel-head">
          <span>Reader Safety</span>
          <h3>{editingRecordId ? '编辑禁写 / 慎写规则' : '禁写 / 慎写规则'}</h3>
          <small>{editingRecordId ? '保存后会替换当前雷点规则，并同步覆盖 taboo-rules.md。' : '定义读者雷点、严重程度和适用范围，让 AI 写作时主动避坑。'}</small>
        </div>
        <div className="structured-grid">
          <label>
            规则
            <textarea aria-label="雷点规则" value={form.rule} onChange={(event) => onFormChange('rule', event.target.value)} />
          </label>
          <label>
            严重程度
            <select aria-label="严重程度" value={form.severity} onChange={(event) => onFormChange('severity', event.target.value)}>
              <option value="low">低</option>
              <option value="medium">中</option>
              <option value="high">高</option>
              <option value="blocker">极高</option>
            </select>
          </label>
          <label>
            适用范围
            <input aria-label="适用范围" value={form.scope} onChange={(event) => onFormChange('scope', event.target.value)} />
          </label>
          <label>
            处理方式
            <textarea aria-label="处理方式" value={form.response} onChange={(event) => onFormChange('response', event.target.value)} />
          </label>
        </div>
        <button className="primary-action" onClick={onSave}>
          <AlertTriangle size={16} />
          {editingRecordId ? '更新雷点规则并同步 llmwiki' : '保存雷点规则'}
        </button>
        {editingRecordId && (
          <button className="secondary-action" onClick={onCancelEdit}>
            取消编辑，改为新建规则
          </button>
        )}
      </div>
      <AIWorkbenchRail
        title="AI 雷点检查"
        modelLabel={modelLabel}
        actionLabel="检查当前章节风险"
        aiResults={aiResults}
        onAction={onCheck}
        onApplyResult={onApplyResult}
        onDeleteResult={onDeleteResult}
      />
    </section>
  );
}

export function KnowledgeWikiWorkbench({
  records,
  wikiPages,
  form,
  editingRecordId = '',
  onFormChange,
  onSave,
  onSelectRecord,
  onCancelEdit,
}: KnowledgeWikiWorkbenchProps) {
  return (
    <section className="special-workbench memory-workbench">
      <RecordRail
        title="llmwiki 知识库"
        kicker="Knowledge Wiki"
        count={records.length}
        records={records}
        empty="知识、角色、大纲、风格、时间线等资料会自动同步到 memory/wiki。"
        editingRecordId={editingRecordId}
        editLabel="编辑知识库资料"
        onSelectRecord={onSelectRecord}
      />
      <div className="structured-editor-panel">
        <div className="workbench-panel-head">
          <span>Raw Source</span>
          <h3>{editingRecordId ? '编辑资料索引' : '资料导入与索引'}</h3>
          <small>{editingRecordId ? '保存后会替换当前知识库资料，并同步覆盖对应 llmwiki 页面。' : '外部资料保存在项目知识库，并由后端同步为可检索的 llmwiki 记忆页。'}</small>
        </div>
        <div className="structured-grid">
          <label>
            资料类型
            <select aria-label="资料类型" value={form.source_type} onChange={(event) => onFormChange('source_type', event.target.value)}>
              <option value="reference">参考资料</option>
              <option value="inspiration">灵感</option>
              <option value="research">考据</option>
              <option value="style">风格材料</option>
            </select>
          </label>
          <label>
            标签
            <input aria-label="知识库标签" value={form.tags} onChange={(event) => onFormChange('tags', event.target.value)} />
          </label>
          <label>
            Wiki 路径
            <input aria-label="Wiki 路径" value={form.wiki_path} onChange={(event) => onFormChange('wiki_path', event.target.value)} placeholder="knowledge/source.md" />
          </label>
          <label>
            资料内容
            <textarea aria-label="资料内容" value={form.content} onChange={(event) => onFormChange('content', event.target.value)} />
          </label>
        </div>
        <button className="primary-action" onClick={onSave}>
          <Library size={16} />
          {editingRecordId ? '更新并同步到 llmwiki' : '保存并同步到 llmwiki'}
        </button>
        {editingRecordId && (
          <button className="secondary-action" onClick={onCancelEdit}>
            取消编辑，改为新建资料
          </button>
        )}
      </div>
      <aside className="workbench-ai-panel">
        <div className="workbench-panel-head">
          <span>Wiki Pages</span>
          <h3>自动记忆页面</h3>
          <small>这里显示项目 memory/wiki 中当前可检索的页面。</small>
        </div>
        <div className="entity-list">
          {wikiPages.map((page) => (
            <article key={page.path}>
              <h4>
                <BookOpen size={14} />
                {page.path}
              </h4>
              <p>{page.content.slice(0, 220)}</p>
              <span>memory/wiki</span>
            </article>
          ))}
          {wikiPages.length === 0 && <p className="empty-state">暂无 Wiki 页面。保存资料或定稿章节后会自动出现。</p>}
        </div>
      </aside>
    </section>
  );
}

function RecordRail({
  title,
  kicker,
  count,
  records,
  empty,
  editingRecordId,
  editLabel,
  onSelectRecord,
}: {
  title: string;
  kicker: string;
  count: number;
  records: GenericRecord[];
  empty: string;
  editingRecordId?: string;
  editLabel?: string;
  onSelectRecord?: (record: GenericRecord) => void;
}) {
  return (
    <aside className="workbench-side-list">
      <div className="workbench-panel-head">
        <span>{kicker}</span>
        <h3>{title}</h3>
        <small>已记录：{count}</small>
      </div>
      <div className="entity-list">
        {records.map((record) => (
          <article key={record.id} className={record.id === editingRecordId ? 'selected-record-card' : ''}>
            <h4>{record.title || '未命名条目'}</h4>
            <p>{record.content || '暂无摘要'}</p>
            <span>{record.status || record.category}</span>
            {onSelectRecord && (
              <button className="ghost-action" onClick={() => onSelectRecord(record)}>
                {editLabel || '编辑记录'} {record.title || '未命名条目'}
              </button>
            )}
          </article>
        ))}
        {records.length === 0 && <p className="empty-state">{empty}</p>}
      </div>
    </aside>
  );
}

function AIWorkbenchRail({
  title,
  modelLabel,
  actionLabel,
  aiResults,
  onAction,
  onApplyResult,
  onDeleteResult,
}: {
  title: string;
  modelLabel: string;
  actionLabel: string;
  aiResults: WorkbenchAIResult[];
  onAction: () => void;
  onApplyResult: (content: string) => void;
  onDeleteResult?: (id: string) => void;
}) {
  return (
    <aside className="workbench-ai-panel">
      <div className="workbench-panel-head">
        <span>AI Memory Lab</span>
        <h3>{title}</h3>
        <small>{modelLabel}</small>
      </div>
      <button onClick={onAction}>
        <Sparkles size={15} />
        {actionLabel}
      </button>
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
        {aiResults.length === 0 && <p className="empty-state">AI 结果会固定在这个区域内，可滚动查看，不会把页面撑散。</p>}
      </div>
    </aside>
  );
}
