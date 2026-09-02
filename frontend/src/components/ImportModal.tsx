import { useRef, useState } from 'react';
import { FileUp, Import, Loader2, Sparkles } from 'lucide-react';
import { api, Chapter, ImportPreview } from '../api';
import { Modal } from '../ui/basics';

const LAYER_OPTIONS: Array<{ value: string; label: string }> = [
  { value: 'chapter', label: '章节正文' },
  { value: 'world', label: '世界观设定' },
  { value: 'character', label: '人物档案' },
  { value: 'outline', label: '大纲' },
];

export function ImportModal({
  projectId,
  chapters,
  onClose,
  onImported,
}: {
  projectId: string;
  chapters: Chapter[];
  onClose: () => void;
  onImported: (message: string, chapterId?: string) => void;
}) {
  const [content, setContent] = useState('');
  const [filename, setFilename] = useState('');
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState('');
  // 片段正文的目标章节：auto=自动匹配 / new=新建章节 / 其他值=指定章节 id
  const [targetChoice, setTargetChoice] = useState('auto');
  // 片段的所属层：''=自动识别
  const [layerChoice, setLayerChoice] = useState('');
  const fileRef = useRef<HTMLInputElement>(null);

  const readFile = (file: File) => {
    setFilename(file.name.replace(/\.(txt|md|markdown)$/i, ''));
    const reader = new FileReader();
    reader.onload = () => setContent(String(reader.result ?? ''));
    reader.readAsText(file);
    setPreview(null);
    setError('');
  };

  const analyze = async () => {
    if (!content.trim()) {
      setError('请先粘贴或选择要导入的内容。');
      return;
    }
    setAnalyzing(true);
    setError('');
    try {
      const result = await api.importPreview(projectId, content);
      setPreview(result);
      if (result.mode === 'fragment' && result.matched_chapter) setTargetChoice('auto');
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : '识别失败');
    } finally {
      setAnalyzing(false);
    }
  };

  const doImport = async () => {
    setImporting(true);
    setError('');
    try {
      const result = await api.importContent(projectId, {
        content,
        filename,
        ...(preview?.mode === 'fragment'
          ? {
              layer: layerChoice || undefined,
              target_chapter_id:
                targetChoice !== 'auto' && targetChoice !== 'new' ? targetChoice : undefined,
            }
          : {}),
      });
      if (result.mode === 'novel') {
        onImported(`已导入 ${result.imported_chapters} 章`, result.chapters?.[0]?.id);
      } else if (result.appended_to) {
        onImported(`片段已追加到「${result.appended_to.title}」`, result.appended_to.id);
      } else if (result.created_chapter) {
        onImported(`片段已保存为新章节「${result.created_chapter.title}」`, result.created_chapter.id);
      } else if (result.layer_label) {
        onImported(`片段已导入到${result.layer_label}「${result.title ?? ''}」`);
      } else {
        onImported('导入完成');
      }
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : '导入失败');
      setImporting(false);
    }
  };

  const fragmentLayer = layerChoice || preview?.layer || 'chapter';

  return (
    <Modal
      title="导入内容"
      onClose={onClose}
      wide
      footer={
        <>
          <span className="spacer muted" style={{ fontSize: 12 }}>{error}</span>
          <button type="button" className="btn" onClick={onClose}>取消</button>
          {!preview ? (
            <button className="btn btn-primary" disabled={analyzing || !content.trim()} onClick={() => void analyze()}>
              {analyzing ? <Loader2 size={13} className="spin" /> : <Sparkles size={13} />}
              {analyzing ? '识别中…' : '自动识别'}
            </button>
          ) : (
            <button className="btn btn-primary" disabled={importing} onClick={() => void doImport()}>
              <Import size={13} />
              {importing ? '导入中…' : preview.mode === 'novel' ? `导入 ${preview.chapter_count} 章` : '确认导入'}
            </button>
          )}
        </>
      }
    >
      {!preview ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <p className="muted" style={{ fontSize: 13, margin: 0 }}>
            支持整本小说（自动按章节标题切分成章节），也支持片段（自动识别属于世界观 / 人物 / 大纲 / 章节正文，并匹配到最合适的章节）。
          </p>
          <div
            className="card"
            style={{
              padding: 18,
              borderStyle: 'dashed',
              display: 'flex',
              alignItems: 'center',
              gap: 12,
              cursor: 'pointer',
            }}
            onClick={() => fileRef.current?.click()}
          >
            <FileUp size={18} />
            <span style={{ fontSize: 13 }}>
              {filename ? <b>{filename}</b> : '点击选择 .txt / .md 文件，或直接在下方粘贴文本'}
            </span>
          </div>
          <input
            ref={fileRef}
            type="file"
            accept=".txt,.md,.markdown,text/plain"
            style={{ display: 'none' }}
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) readFile(file);
              event.target.value = '';
            }}
          />
          <textarea
            value={content}
            onChange={(event) => setContent(event.target.value)}
            rows={10}
            placeholder="在此粘贴小说全文或片段…"
            style={{ fontFamily: 'var(--serif)', lineHeight: 1.8 }}
          />
        </div>
      ) : preview.mode === 'novel' ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <p style={{ fontSize: 13.5, margin: 0 }}>
            识别到 <b>{preview.chapter_count}</b> 章，共约 {preview.total_words} 字。将按顺序导入为章节草稿。
          </p>
          <div className="master-list" style={{ maxHeight: 320, overflow: 'auto' }}>
            {(preview.items ?? []).map((item, index) => (
              <div className="master-item" key={index} style={{ cursor: 'default' }}>
                <span className="avatar">{index + 1}</span>
                <span className="grow">
                  <b>{item.title}</b>
                  <small>{item.words} 字 · {item.preview}…</small>
                </span>
              </div>
            ))}
          </div>
          <button className="btn" style={{ alignSelf: 'flex-start' }} onClick={() => setPreview(null)}>
            ← 重新编辑内容
          </button>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <p style={{ fontSize: 13.5, margin: 0 }}>
            这是一段约 {preview.words} 字的内容，识别为
            <b> {LAYER_OPTIONS.find((option) => option.value === preview.layer)?.label ?? preview.layer_label} </b>。
          </p>
          <label className="field">
            <span>所属层（可调整）</span>
            <select value={fragmentLayer} onChange={(event) => setLayerChoice(event.target.value)}>
              {LAYER_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </label>
          {fragmentLayer === 'chapter' && (
            <label className="field">
              <span>目标章节</span>
              <select value={targetChoice} onChange={(event) => setTargetChoice(event.target.value)}>
                {preview.matched_chapter && (
                  <option value="auto">
                    自动匹配：第 {preview.matched_chapter.chapter_number} 章 {preview.matched_chapter.title}（匹配度
                    {' '}
                    {Math.round(preview.matched_chapter.score * 100)}%）
                  </option>
                )}
                <option value="new">保存为新章节</option>
                {chapters.map((chapter) => (
                  <option key={chapter.id} value={chapter.id}>
                    第 {chapter.chapter_number} 章 {chapter.title}
                  </option>
                ))}
              </select>
            </label>
          )}
          <blockquote className="card" style={{ padding: 12, fontSize: 12.5, color: 'var(--ink-2)', maxHeight: 120, overflow: 'auto' }}>
            {preview.preview}…
          </blockquote>
          <button className="btn" style={{ alignSelf: 'flex-start' }} onClick={() => setPreview(null)}>
            ← 重新编辑内容
          </button>
        </div>
      )}
    </Modal>
  );
}
