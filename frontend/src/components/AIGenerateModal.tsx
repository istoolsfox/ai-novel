import { useState } from 'react';
import { Check, LoaderCircle, RefreshCw, Sparkles, X } from 'lucide-react';
import { AiResult, api } from '../api';
import { Modal } from '../ui/basics';

export type AiDraftItem = {
  title: string;
  content: string;
  payload?: Record<string, unknown>;
};

/** 从 AI 结果里提取结构化条目：优先 structured 数组，其次解析文本中的 JSON 数组，最后整段文本。 */
export function parseAiItems(result: AiResult): AiDraftItem[] {
  const structured = result.structured;
  if (Array.isArray(structured)) {
    return structured.map((item, index) => normalizeStructuredItem(item, index, result));
  }
  if (structured && typeof structured === 'object') {
    return [normalizeStructuredItem(structured, 0, result)];
  }
  const fromText = tryParseJsonArray(result.text);
  if (fromText.length > 0) {
    return fromText.map((item, index) => normalizeStructuredItem(item, index, result));
  }
  return [{ title: 'AI 生成结果', content: result.text.trim() }];
}

function normalizeStructuredItem(item: unknown, index: number, result: AiResult): AiDraftItem {
  if (item && typeof item === 'object') {
    const record = item as Record<string, unknown>;
    const title = firstString(record, ['name', 'title', 'chapter_title', 'event_time', 'source_character']) || `条目 ${index + 1}`;
    const description = firstString(record, ['description', 'summary', 'content', 'chapter_goal', 'cause', 'conflict']);
    return {
      title: String(title),
      content: description || JSON.stringify(record, null, 2),
      payload: record,
    };
  }
  return { title: `条目 ${index + 1}`, content: String(item ?? result.text) };
}

function firstString(record: Record<string, unknown>, keys: string[]): string {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === 'string' && value.trim()) return value.trim();
  }
  return '';
}

function tryParseJsonArray(text: string): unknown[] {
  const match = text.match(/\[[\s\S]*\]/);
  if (!match) return [];
  try {
    const parsed = JSON.parse(match[0]) as unknown;
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function AIGenerateModal({
  projectId,
  title,
  intro,
  workflow,
  buildPayload,
  onSave,
  onClose,
  saveLabel = '保存到项目',
}: {
  projectId: string;
  title: string;
  intro?: string;
  workflow: string;
  buildPayload: (prompt: string) => Record<string, unknown>;
  onSave: (items: AiDraftItem[]) => Promise<void>;
  onClose: () => void;
  saveLabel?: string;
}) {
  const [prompt, setPrompt] = useState('');
  const [result, setResult] = useState<AiResult | null>(null);
  const [running, setRunning] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const generate = async () => {
    if (running) return;
    setRunning(true);
    setError('');
    try {
      const output = await api.runAi(projectId, workflow, buildPayload(prompt));
      setResult(output);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : 'AI 生成失败，请检查模型配置。');
    } finally {
      setRunning(false);
    }
  };

  const save = async () => {
    if (!result || saving) return;
    setSaving(true);
    setError('');
    try {
      await onSave(parseAiItems(result));
      onClose();
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : '保存失败');
      setSaving(false);
    }
  };

  const items = result ? parseAiItems(result) : [];

  return (
    <Modal
      title={
        <span className="row-flex">
          <Sparkles size={15} style={{ color: 'var(--ai)' }} /> {title}
        </span>
      }
      onClose={onClose}
      footer={
        <>
          <span className="spacer">{result?.status === 'local' ? '本地占位结果 · 配置模型后可获得真实生成' : ''}</span>
          <button className="btn" onClick={onClose}>取消</button>
          {result ? (
            <>
              <button className="btn" onClick={() => void generate()} disabled={running}>
                <RefreshCw size={13} /> 重新生成
              </button>
              <button className="btn btn-ai" onClick={() => void save()} disabled={saving || items.length === 0}>
                <Check size={13} /> {saving ? '保存中…' : saveLabel}
              </button>
            </>
          ) : (
            <button className="btn btn-ai" onClick={() => void generate()} disabled={running}>
              {running ? <LoaderCircle size={13} className="spin" /> : <Sparkles size={13} />}
              {running ? '生成中…' : '生成'}
            </button>
          )}
        </>
      }
    >
      {intro && <p className="muted" style={{ fontSize: 13, lineHeight: 1.7 }}>{intro}</p>}
      <label className="field">
        <span>生成要求（可留空）</span>
        <textarea
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
          rows={3}
          placeholder="描述你想要的风格、侧重和约束…"
        />
      </label>
      {error && <div className="notice">{error}</div>}
      {result && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div className="ai-panel-block-head">
            <Sparkles size={12} /> AI Generated · {items.length} 条 · 模型 {result.model}
            {result.status === 'local' && <span className="badge ai">本地占位</span>}
          </div>
          <div className="ai-generated-text">{result.text}</div>
        </div>
      )}
    </Modal>
  );
}
