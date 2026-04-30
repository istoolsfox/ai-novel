import { useEffect, useMemo } from 'react';
import {
  Background,
  Controls,
  MarkerType,
  ReactFlow,
  useEdgesState,
  useNodesState,
  type Edge,
  type Node,
} from '@xyflow/react';
import { GitBranch, Plus, Sparkles } from 'lucide-react';
import { GenericRecord, RelationshipPayload, WorkbenchAIResult } from '../api';
import { AIResultCard } from './AIResultCard';

type RelationshipGenerateMode = 'extract' | 'conflict' | 'consistency';

type RelationshipGraphWorkbenchProps = {
  relationships: GenericRecord[];
  characters: GenericRecord[];
  form: RelationshipPayload;
  aiResults: WorkbenchAIResult[];
  modelLabel: string;
  editingRecordId?: string;
  onFormChange: (field: keyof RelationshipPayload, value: string | number) => void;
  onSaveRelationship: () => void;
  onSelectRelationship?: (record: GenericRecord) => void;
  onCancelEdit?: () => void;
  onCreateCharacter: () => void;
  onGenerate: (mode: RelationshipGenerateMode) => void;
  onApplyResult: (content: string) => void;
  onDeleteResult?: (id: string) => void;
};

const relationshipTypes = ['朋友', '敌人', '亲属', '师徒', '暧昧', '利用', '背叛', '同盟', '主线关联'];

function payloadString(record: GenericRecord, key: string) {
  return String(record.payload?.[key] ?? '');
}

function characterName(record: GenericRecord) {
  return payloadString(record, 'name') || record.title || '未命名角色';
}

const characterNodeStyle = {
  background: 'linear-gradient(135deg, rgba(30, 42, 70, 0.98), rgba(18, 26, 46, 0.96))',
  border: '1px solid rgba(213, 173, 104, 0.52)',
  borderRadius: 18,
  boxShadow: '0 18px 36px rgba(0, 0, 0, 0.34), inset 0 1px 0 rgba(255, 248, 232, 0.12)',
  color: '#fff7df',
  cursor: 'grab',
  fontSize: 16,
  fontWeight: 800,
  minHeight: 58,
  padding: '14px 18px',
  textAlign: 'center' as const,
  width: 190,
};

const ghostNodeStyle = {
  ...characterNodeStyle,
  background: 'linear-gradient(135deg, rgba(41, 31, 58, 0.96), rgba(17, 24, 42, 0.94))',
  border: '1px dashed rgba(132, 199, 217, 0.55)',
  color: '#dcefff',
};

function makeRelationshipNode(id: string, label: string, index: number, ghost = false): Node {
  return {
    id,
    className: `story-character-node${ghost ? ' ghost-character-node' : ''}`,
    data: { label },
    domAttributes: { 'data-draggable-node': 'true' } as unknown as Node['domAttributes'],
    draggable: true,
    position: {
      x: 90 + (index % 3) * 240,
      y: 82 + Math.floor(index / 3) * 150,
    },
    style: ghost ? ghostNodeStyle : characterNodeStyle,
  };
}

function buildRelationshipGraph(characters: GenericRecord[], relationships: GenericRecord[]) {
  const baseNodes = characters.map((character, index) =>
    makeRelationshipNode(character.id, characterName(character), index),
  );
  const existingNames = new Set(baseNodes.map((node) => String(node.data.label)));
  const relationshipNames = relationships.flatMap((relationship) =>
    [payloadString(relationship, 'source_character'), payloadString(relationship, 'target_character')].filter(Boolean),
  );
  const ghostNodes = [...new Set(relationshipNames)]
    .filter((name) => !existingNames.has(name))
    .map((name, index) => makeRelationshipNode(`ghost-${name}`, name, baseNodes.length + index, true));
  const nodes = [...baseNodes, ...ghostNodes];
  const nodeByName = new Map(nodes.map((node) => [String(node.data.label), node.id]));
  const edges: Edge[] = relationships.flatMap((relationship, index) => {
    const sourceName = payloadString(relationship, 'source_character');
    const targetName = payloadString(relationship, 'target_character');
    const source = nodeByName.get(sourceName) ?? nodes[0]?.id;
    const target = nodeByName.get(targetName) ?? nodes[index % nodes.length]?.id ?? nodes[1]?.id;
    if (!source || !target || source === target) return [];
    return [
      {
        id: `relationship-${relationship.id}`,
        source,
        target,
        label: payloadString(relationship, 'relationship_type') || relationship.category || relationship.title,
        labelBgBorderRadius: 10,
        labelBgPadding: [10, 6],
        labelBgStyle: { fill: 'rgba(8, 13, 25, 0.94)', fillOpacity: 0.96 },
        labelStyle: { fill: '#fff7df', fontSize: 13, fontWeight: 800 },
        markerEnd: { color: 'rgba(213, 173, 104, 0.9)', type: MarkerType.ArrowClosed },
        style: { stroke: 'rgba(213, 173, 104, 0.88)', strokeWidth: 2.4 },
      },
    ];
  });

  return { edges, nodes };
}

export function RelationshipGraphWorkbench({
  relationships,
  characters,
  form,
  aiResults,
  modelLabel,
  editingRecordId = '',
  onFormChange,
  onSaveRelationship,
  onSelectRelationship,
  onCancelEdit,
  onCreateCharacter,
  onGenerate,
  onApplyResult,
  onDeleteResult,
}: RelationshipGraphWorkbenchProps) {
  const graph = useMemo(() => buildRelationshipGraph(characters, relationships), [characters, relationships]);
  const missingEndpointCount = useMemo(
    () =>
      relationships.filter((relationship) => {
        const title = relationship.title || '';
        const source = payloadString(relationship, 'source_character');
        const target = payloadString(relationship, 'target_character');
        return !source || !target || title.includes('未知角色');
      }).length,
    [relationships],
  );
  const [nodes, setNodes, onNodesChange] = useNodesState(graph.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(graph.edges);

  useEffect(() => {
    setNodes(graph.nodes);
  }, [graph.nodes, setNodes]);

  useEffect(() => {
    setEdges(graph.edges);
  }, [graph.edges, setEdges]);

  return (
    <section className="special-workbench relationship-graph-workbench">
      <aside className="workbench-side-list">
        <div className="workbench-panel-head">
          <span>Relationship Graph</span>
          <h3>关系图工作台</h3>
          <small>角色 {characters.length} 个，关系 {relationships.length} 条</small>
        </div>
        <button className="primary-action" onClick={onCreateCharacter}>
          <Plus size={16} />
          新增角色
        </button>
        {missingEndpointCount > 0 && (
          <div className="quality-alert">
            <strong>资料质量提醒</strong>
            <p>有 {missingEndpointCount} 条关系缺少来源或目标角色，建议先补全角色名再让 AI 引用关系图。</p>
          </div>
        )}
        <div className="relationship-flow-panel graph-panel" aria-label="角色关系图画布">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onEdgesChange={onEdgesChange}
            onNodesChange={onNodesChange}
            nodesConnectable={false}
            nodesDraggable
            elementsSelectable
            fitView
            fitViewOptions={{ padding: 0.28 }}
          >
            <Background />
            <Controls />
          </ReactFlow>
        </div>
        <div className="entity-list" aria-label="关系列表">
          <strong>
            <GitBranch size={16} />
            已保存关系
          </strong>
          {relationships.map((relationship) => (
            <article key={relationship.id} className={relationship.id === editingRecordId ? 'selected-record-card' : ''}>
              <h4>{relationship.title || '未命名关系'}</h4>
              <p>{relationship.content || payloadString(relationship, 'change_history') || '暂无关系说明'}</p>
              <span>{relationship.category || relationship.status}</span>
              {onSelectRelationship && (
                <button className="ghost-action" onClick={() => onSelectRelationship(relationship)}>
                  编辑关系 {relationship.title || '未命名关系'}
                </button>
              )}
            </article>
          ))}
          {relationships.length === 0 && <p className="empty-state">还没有关系记录，先新增一条角色关系。</p>}
        </div>
      </aside>

      <div className="structured-editor-panel">
        <div className="workbench-panel-head">
          <span>Relationship Card</span>
          <h3>{editingRecordId ? '编辑关系' : '新增关系'}</h3>
          <small>{editingRecordId ? '保存后会替换当前关系记录，并同步覆盖 relationships.md。' : '结构化记录来源、目标、强度、冲突与章节范围。'}</small>
        </div>
        <div className="structured-grid">
          <label>
            来源角色
            <input
              aria-label="来源角色"
              value={form.source_character}
              onChange={(event) => onFormChange('source_character', event.target.value)}
            />
          </label>
          <label>
            目标角色
            <input
              aria-label="目标角色"
              value={form.target_character}
              onChange={(event) => onFormChange('target_character', event.target.value)}
            />
          </label>
          <label>
            关系类型
            <select
              aria-label="关系类型"
              value={form.relationship_type}
              onChange={(event) => onFormChange('relationship_type', event.target.value)}
            >
              {relationshipTypes.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </label>
          <label>
            关系强度
            <input
              aria-label="关系强度"
              max="100"
              min="0"
              type="number"
              value={form.strength}
              onChange={(event) => onFormChange('strength', Number(event.target.value))}
            />
          </label>
          <label>
            冲突说明
            <textarea
              aria-label="冲突说明"
              value={form.conflict}
              onChange={(event) => onFormChange('conflict', event.target.value)}
            />
          </label>
          <label>
            关系变化记录
            <textarea
              aria-label="关系变化记录"
              value={form.change_history}
              onChange={(event) => onFormChange('change_history', event.target.value)}
            />
          </label>
          <label>
            相关章节
            <input
              aria-label="相关章节"
              value={form.related_chapters}
              onChange={(event) => onFormChange('related_chapters', event.target.value)}
            />
          </label>
        </div>
        <button className="primary-action" onClick={onSaveRelationship}>
          <Plus size={16} />
          {editingRecordId ? '更新关系并同步 llmwiki' : '新增关系'}
        </button>
        {editingRecordId && onCancelEdit && (
          <button className="secondary-action" onClick={onCancelEdit}>
            取消编辑，改为新增关系
          </button>
        )}
      </div>

      <aside className="workbench-ai-panel">
        <div className="workbench-panel-head">
          <span>AI Relationship Lab</span>
          <h3>AI 提取关系</h3>
          <small>{modelLabel}</small>
        </div>
        <div className="ai-action-grid">
          <button onClick={() => onGenerate('extract')}>
            <Sparkles size={15} />
            AI 提取关系
          </button>
          <button onClick={() => onGenerate('conflict')}>
            <Sparkles size={15} />
            冲突建议
          </button>
          <button onClick={() => onGenerate('consistency')}>
            <Sparkles size={15} />
            一致性检查
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
          {aiResults.length === 0 && <p className="empty-state">AI 关系分析会显示在这里，可加入关系变化记录。</p>}
        </div>
      </aside>
    </section>
  );
}
