import { ChangeEvent, useMemo } from 'react';
import { FileText, Library, PenLine, Sparkles } from 'lucide-react';
import { GenericRecord } from '../api';

type StyleLearningPanelProps = {
  records: GenericRecord[];
  sampleTitle: string;
  sampleText: string;
  writingGoal: string;
  analysis: string;
  imitation: string;
  modelLabel: string;
  onSampleTitleChange: (value: string) => void;
  onSampleTextChange: (value: string) => void;
  onWritingGoalChange: (value: string) => void;
  onImportText: (text: string, fileName: string) => void;
  onAnalyze: () => void;
  onImitate: () => void;
  onSaveProfile: () => void;
};

export function StyleLearningPanel({
  records,
  sampleTitle,
  sampleText,
  writingGoal,
  analysis,
  imitation,
  modelLabel,
  onSampleTitleChange,
  onSampleTextChange,
  onWritingGoalChange,
  onImportText,
  onAnalyze,
  onImitate,
  onSaveProfile,
}: StyleLearningPanelProps) {
  const qualityIssues = useMemo(() => {
    const unnamedCount = records.filter((record) => !record.title.trim() || record.title === '未命名风格样本').length;
    const titleCounts = records.reduce<Record<string, number>>((acc, record) => {
      const title = record.title.trim();
      if (!title) return acc;
      acc[title] = (acc[title] ?? 0) + 1;
      return acc;
    }, {});
    const duplicateTitleCount = Object.values(titleCounts).filter((count) => count > 1).length;
    return { duplicateTitleCount, unnamedCount };
  }, [records]);

  function importFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => onImportText(String(reader.result ?? ''), file.name);
    reader.readAsText(file, 'utf-8');
  }

  return (
    <section className="style-learning-workspace">
      <div className="style-lab-hero">
        <div>
          <span className="eyebrow">Style Lab</span>
          <h3>风格学习</h3>
          <p>导入一段参考文本，让 AI 分析句式、节奏、意象、叙述距离和情绪密度，再用于模拟写作语气。</p>
        </div>
        <div className="model-hints">
          <span>{modelLabel}</span>
        </div>
      </div>

      <div className="style-lab-grid">
        <div className="style-lab-panel">
          <div className="panel-heading">
            <span>导入风格样本</span>
            <small>txt / 粘贴文本</small>
          </div>
          <label>
            样本名称
            <input
              value={sampleTitle}
              onChange={(event) => onSampleTitleChange(event.target.value)}
              placeholder="例如：悬疑克制样本 / 某作者对白节奏"
            />
          </label>
          <label>
            风格样本文本
            <textarea
              aria-label="风格样本文本"
              value={sampleText}
              onChange={(event) => onSampleTextChange(event.target.value)}
              placeholder="粘贴你想学习的文本片段。建议 800-3000 字，越完整越容易分析语气。"
            />
          </label>
          <label className="file-import-button">
            <FileText size={15} />
            导入文本文件
            <input type="file" accept=".txt,.md,text/plain,text/markdown" onChange={importFile} />
          </label>
          <label>
            模拟写作要求
            <textarea
              value={writingGoal}
              onChange={(event) => onWritingGoalChange(event.target.value)}
              placeholder="例如：用这种风格写一段女主发现记忆被篡改后的心理变化。"
            />
          </label>
          <div className="action-row">
            <button className="primary-action" onClick={onAnalyze} disabled={!sampleText.trim()}>
              <Sparkles size={15} />
              AI 分析写作语气
            </button>
            <button onClick={onImitate} disabled={!sampleText.trim()}>
              <PenLine size={15} />
              模拟写作语气
            </button>
            <button onClick={onSaveProfile} disabled={!analysis.trim() && !sampleText.trim()}>
              <Library size={15} />
              保存风格档案
            </button>
          </div>
        </div>

        <div className="style-lab-panel">
          <div className="panel-heading">
            <span>AI 分析结果</span>
            <small>语气画像</small>
          </div>
          <article className="style-result-card">
            <strong>写作语气分析</strong>
            <p>{analysis || '分析后会显示：句式长度、节奏、情绪张力、常用意象、叙述视角、对白习惯和可模仿规则。'}</p>
          </article>
          <article className="style-result-card">
            <strong>模拟写作片段</strong>
            <p>{imitation || '点击“模拟写作语气”后，会基于样本文风和你的写作要求生成一段可插入正文的试写。'}</p>
          </article>
        </div>

        <div className="style-lab-panel style-profile-list">
          <div className="panel-heading">
            <span>已保存风格档案</span>
            <small>章节生成时可调用</small>
            <small>{records.length} 个</small>
          </div>
          {(qualityIssues.unnamedCount > 0 || qualityIssues.duplicateTitleCount > 0) && (
            <div className="quality-alert">
              <strong>风格档案质量提醒</strong>
              <p>
                {qualityIssues.unnamedCount > 0 && `有 ${qualityIssues.unnamedCount} 个档案仍使用未命名标题。`}
                {qualityIssues.duplicateTitleCount > 0 && ` 有 ${qualityIssues.duplicateTitleCount} 组档案标题重复。`}
                建议重命名后再作为章节生成的风格来源。
              </p>
            </div>
          )}
          {records.map((record) => (
            <article key={record.id}>
              <strong>{record.title}</strong>
              <p>{record.content.slice(0, 180)}</p>
              <span>{record.status}</span>
            </article>
          ))}
          {records.length === 0 && <p className="empty-state">还没有保存风格档案。导入样本并分析后，可以保存为当前项目的文风资产。</p>}
        </div>
      </div>
    </section>
  );
}
