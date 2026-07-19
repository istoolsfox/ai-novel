import { useEffect, useMemo, useState } from 'react';
import {
  Background,
  Controls,
  MarkerType,
  MiniMap,
  Position,
  ReactFlow,
  useEdgesState,
  useNodesState,
  type Edge,
  type Node,
  type NodeMouseHandler,
} from '@xyflow/react';
import type { JsonRecord } from '../controlApi';

export type StoryGraphCanvasProps = {
  projectId: string;
  threads: JsonRecord[];
  storyNodes: JsonRecord[];
  storyEdges: JsonRecord[];
};

type FlowData = {
  label: string;
  kind: 'thread' | 'story-node';
  status: string;
  detail: string;
};

type StoryFlowNode = Node<FlowData>;

function text(value: unknown, fallback = ''): string {
  if (typeof value === 'string' && value.trim()) return value;
  if (typeof value === 'number') return String(value);
  return fallback;
}

function positionStorageKey(projectId: string) {
  return `ai-novel:story-graph-positions:${projectId}`;
}

function savedPositions(projectId: string): Record<string, { x: number; y: number }> {
  if (typeof window === 'undefined') return {};
  try {
    const parsed = JSON.parse(window.localStorage.getItem(positionStorageKey(projectId)) ?? '{}') as unknown;
    return parsed && typeof parsed === 'object' ? parsed as Record<string, { x: number; y: number }> : {};
  } catch {
    return {};
  }
}

function persistPositions(projectId: string, nodes: StoryFlowNode[]) {
  if (typeof window === 'undefined') return;
  const positions = Object.fromEntries(nodes.map((node) => [node.id, node.position]));
  window.localStorage.setItem(positionStorageKey(projectId), JSON.stringify(positions));
}

function nodeStatusClass(status: string, kind: FlowData['kind']) {
  const normalized = status.toLowerCase();
  if (kind === 'thread') return 'story-flow-thread';
  if (['completed', 'resolved', 'paid_off'].includes(normalized)) return 'story-flow-completed';
  if (['blocked', 'abandoned', 'failed'].includes(normalized)) return 'story-flow-blocked';
  if (['active', 'in_progress'].includes(normalized)) return 'story-flow-active';
  return 'story-flow-planned';
}

export function buildStoryFlow(
  projectId: string,
  threads: JsonRecord[],
  storyNodes: JsonRecord[],
  storyEdges: JsonRecord[],
): { nodes: StoryFlowNode[]; edges: Edge[] } {
  const stored = savedPositions(projectId);
  const threadKeys = threads.map((thread, index) => text(thread.thread_key, `thread-${index + 1}`));
  const columnByThread = new Map(threadKeys.map((key, index) => [key, index]));
  const nodesByThread = new Map<string, JsonRecord[]>();

  storyNodes.forEach((node) => {
    const key = text(node.thread_key, 'unassigned');
    nodesByThread.set(key, [...(nodesByThread.get(key) ?? []), node]);
    if (!columnByThread.has(key)) columnByThread.set(key, columnByThread.size);
  });

  const flowNodes: StoryFlowNode[] = [];
  threads.forEach((thread, index) => {
    const threadKey = text(thread.thread_key, `thread-${index + 1}`);
    const id = `thread:${threadKey}`;
    const fallback = { x: (columnByThread.get(threadKey) ?? index) * 340, y: 0 };
    const status = text(thread.status, 'active');
    flowNodes.push({
      id,
      position: stored[id] ?? fallback,
      data: {
        label: text(thread.title, threadKey),
        kind: 'thread',
        status,
        detail: `${text(thread.current_stage, '未设阶段')} → ${text(thread.next_target, '未设下一目标')}`,
      },
      className: nodeStatusClass(status, 'thread'),
      sourcePosition: Position.Bottom,
      targetPosition: Position.Top,
    });
  });

  Array.from(nodesByThread.entries()).forEach(([threadKey, entries]) => {
    const column = columnByThread.get(threadKey) ?? 0;
    entries
      .sort((left, right) => Number(left.planned_chapter ?? 0) - Number(right.planned_chapter ?? 0))
      .forEach((node, index) => {
        const nodeKey = text(node.node_key, `${threadKey}-${index + 1}`);
        const id = `node:${nodeKey}`;
        const status = text(node.status, 'planned');
        flowNodes.push({
          id,
          position: stored[id] ?? { x: column * 340, y: 145 + index * 145 },
          data: {
            label: text(node.title, nodeKey),
            kind: 'story-node',
            status,
            detail: `${threadKey} · 计划第 ${text(node.planned_chapter, '未定')} 章`,
          },
          className: nodeStatusClass(status, 'story-node'),
          sourcePosition: Position.Bottom,
          targetPosition: Position.Top,
        });
      });
  });

  const existingNodeIds = new Set(flowNodes.map((node) => node.id));
  const flowEdges: Edge[] = storyEdges.flatMap((edge, index) => {
    const source = `node:${text(edge.source_node_key)}`;
    const target = `node:${text(edge.target_node_key)}`;
    if (!existingNodeIds.has(source) || !existingNodeIds.has(target)) return [];
    return [{
      id: text(edge.id, `edge-${index + 1}`),
      source,
      target,
      label: text(edge.relation_type, 'continues'),
      markerEnd: { type: MarkerType.ArrowClosed },
      animated: ['causes', 'reveals', 'pays_off'].includes(text(edge.relation_type)),
      data: { weight: Number(edge.weight ?? 1) },
    }];
  });

  storyNodes.forEach((node, index) => {
    const threadKey = text(node.thread_key, 'unassigned');
    const nodeKey = text(node.node_key, `${threadKey}-${index + 1}`);
    const source = `thread:${threadKey}`;
    const target = `node:${nodeKey}`;
    if (existingNodeIds.has(source) && existingNodeIds.has(target)) {
      flowEdges.unshift({
        id: `membership:${threadKey}:${nodeKey}`,
        source,
        target,
        type: 'smoothstep',
        selectable: false,
      });
    }
  });

  return { nodes: flowNodes, edges: flowEdges };
}

export default function StoryGraphCanvas({ projectId, threads, storyNodes, storyEdges }: StoryGraphCanvasProps) {
  const initial = useMemo(
    () => buildStoryFlow(projectId, threads, storyNodes, storyEdges),
    [projectId, storyEdges, storyNodes, threads],
  );
  const [nodes, setNodes, onNodesChange] = useNodesState<StoryFlowNode>(initial.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initial.edges);
  const [selected, setSelected] = useState<StoryFlowNode | null>(null);

  useEffect(() => {
    setNodes(initial.nodes);
    setEdges(initial.edges);
    setSelected(null);
  }, [initial, setEdges, setNodes]);

  const onNodeClick: NodeMouseHandler<StoryFlowNode> = (_, node) => setSelected(node);

  if (!nodes.length) {
    return <div className="uc-empty story-canvas-empty">当前项目还没有可视化剧情节点。</div>;
  }

  return (
    <div className="story-canvas-layout">
      <div className="story-canvas" aria-label="可拖拽剧情图谱">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={onNodeClick}
          onNodeDragStop={() => persistPositions(projectId, nodes)}
          fitView
          minZoom={0.2}
          maxZoom={1.8}
        >
          <MiniMap pannable zoomable />
          <Controls />
          <Background gap={20} size={1} />
        </ReactFlow>
      </div>
      <aside className="story-canvas-detail">
        <span>节点详情</span>
        {selected ? (
          <>
            <strong>{selected.data.label}</strong>
            <p>{selected.data.detail}</p>
            <small>{selected.data.kind} · {selected.data.status}</small>
          </>
        ) : (
          <p>点击节点查看详情；拖拽后的位置会按当前项目保存在本机。</p>
        )}
      </aside>
    </div>
  );
}
