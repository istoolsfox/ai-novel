import { useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { NovelEditorPage } from '../components/NovelEditorPage';
import { api, Chapter, ChapterVersion } from '../api';
import { useChapters, useProject } from '../shell/useProject';

export function Writing() {
  const { projectId } = useParams();
  const { project } = useProject(projectId);
  const { chapters, loading } = useChapters(projectId);
  const [selectedChapter, setSelectedChapter] = useState<Chapter | null>(null);
  const [draft, setDraft] = useState('');
  const [versions, setVersions] = useState<ChapterVersion[]>([]);
  const [log, setLog] = useState('');
  const [wikiPageCount, setWikiPageCount] = useState(0);

  const effectiveSelected = selectedChapter ?? chapters[0] ?? null;

  const onSelectChapter = (chapter: Chapter) => {
    setSelectedChapter(chapter);
    setDraft(chapter.draft ?? '');
    setLog('');
    if (projectId) {
      api.listVersions(projectId, chapter.id).then(setVersions).catch(() => undefined);
      api.wikiCount(projectId).then((r) => setWikiPageCount(r.count)).catch(() => undefined);
    }
  };

  const onDraftChange = (value: string) => {
    setDraft(value);
    if (effectiveSelected && projectId) {
      api.updateChapter(projectId, effectiveSelected.id, { draft: value }).catch(() => undefined);
    }
  };

  const generateDraft = async (payload: { prompt: string; tone: string; style: string; length: string; viewpoint: string; selectedText: string; mode: 'draft' | 'continue' | 'revise'; emotionalIntent?: string; workflow?: string }) => {
    if (!projectId || !effectiveSelected) return '请先选择章节。';
    const workflow = payload.workflow || (payload.mode === 'revise' ? 'revise_selection' : 'generate_chapter_draft');
    setLog('正在生成本章正文…');
    try {
      const result = await api.runAi(projectId, workflow, {
        chapter_id: effectiveSelected.id,
        chapter_number: effectiveSelected.chapter_number,
        chapter_title: effectiveSelected.title,
        current_draft: draft,
        selected_text: payload.selectedText,
        prompt: payload.prompt,
        generation_contract: {
          output: 'single_chapter_prose',
          use_llmwiki: true,
          avoid_multiple_drafts: true,
          instruction: `只生成当前第 ${effectiveSelected.chapter_number} 章《${effectiveSelected.title}》的单篇中文小说正文。不要输出 JSON、drafts 数组或多个版本。`,
        },
        tone: payload.tone,
        style: payload.style,
        length: payload.length,
        viewpoint: payload.viewpoint,
        emotional_intent: payload.emotionalIntent ?? '',
        mode: payload.mode,
      });
      setLog(result.status === 'fallback' ? '模型已回退到本地占位结果' : '模型已返回正文结果');
      return result.text;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'AI 生成失败';
      setLog(message);
      throw error;
    }
  };

  const saveAsVersion = async (title: string, content: string) => {
    if (!projectId || !effectiveSelected) return;
    await api.createVersion(projectId, effectiveSelected.id, title, content);
    setLog('已保存为候选版本。');
  };

  const scoreChapter = async () => {
    if (!projectId || !effectiveSelected) return;
    setLog('正在评分…');
    await api.runAi(projectId, 'score_chapter', { chapter_id: effectiveSelected.id, chapter_number: effectiveSelected.chapter_number, chapter_title: effectiveSelected.title, draft });
    setLog('评分完成。');
  };

  const wordCount = useMemo(() => draft.trim().length, [draft]);

  if (loading) return <div className="os-empty">加载中…</div>;

  return (
    <NovelEditorPage
      project={project}
      chapters={chapters}
      selectedChapter={effectiveSelected}
      versions={versions}
      draft={draft}
      log={log}
      modelLabel="AI Model"
      wikiPageCount={wikiPageCount}
      onCreateChapter={() => undefined}
      onDeleteChapter={() => undefined}
      onSelectChapter={onSelectChapter}
      onDraftChange={onDraftChange}
      onChapterTitleChange={(title) => {
        if (effectiveSelected && projectId) {
          api.updateChapter(projectId, effectiveSelected.id, { title }).catch(() => undefined);
          setSelectedChapter({ ...effectiveSelected, title });
        }
      }}
      onSaveChapter={() => setLog('已保存 (Saved)')}
      onGenerateVariant={() => undefined}
      onGenerateChapterDraft={generateDraft}
      onSaveAiResultAsVersion={saveAsVersion}
      onScoreChapter={() => void scoreChapter()}
      onFinalizeChapter={() => setLog('已定稿')}
      onSelectVersion={() => undefined}
      onOpenResource={() => undefined}
      onLog={setLog}
    />
  );
}
