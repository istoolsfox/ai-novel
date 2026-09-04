import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Minimize2 } from 'lucide-react';
import { NovelEditorPage } from '../components/NovelEditorPage';
import { ImportModal } from '../components/ImportModal';
import { api, Chapter, ChapterVersion } from '../api';
import { useChapters } from '../shell/useProject';
import { useWorkspace } from '../shell/workspace';

export function Writing() {
  const navigate = useNavigate();
  const { projectId, chapterId } = useParams();
  const { project } = useWorkspace();
  const { chapters, reload } = useChapters(projectId);
  const { immersive, setImmersive } = useWorkspace();
  const [selectedChapter, setSelectedChapter] = useState<Chapter | null>(null);
  const [draft, setDraft] = useState('');
  const [versions, setVersions] = useState<ChapterVersion[]>([]);
  const [log, setLog] = useState('');
  const [wikiPageCount, setWikiPageCount] = useState(0);
  const [importOpen, setImportOpen] = useState(false);

  const effectiveSelected = useMemo(
    () =>
      selectedChapter && chapters.some((chapter) => chapter.id === selectedChapter.id)
        ? selectedChapter
        : chapterId
          ? chapters.find((chapter) => chapter.id === chapterId) ?? null
          : chapters[0] ?? null,
    [selectedChapter, chapters, chapterId],
  );

  const loadChapter = (chapter: Chapter) => {
    setSelectedChapter(chapter);
    setDraft(chapter.draft ?? '');
    setLog('');
    navigate(`/projects/${projectId}/writing/${chapter.id}`, { replace: true });
    if (projectId) {
      api.listVersions(projectId, chapter.id).then(setVersions).catch(() => undefined);
      api.wikiCount(projectId).then((result) => setWikiPageCount(result.count)).catch(() => undefined);
    }
  };

  useEffect(() => {
    if (effectiveSelected && (!selectedChapter || selectedChapter.id !== effectiveSelected.id || draft !== effectiveSelected.draft)) {
      setSelectedChapter(effectiveSelected);
      setDraft(effectiveSelected.draft ?? '');
      if (projectId) {
        api.listVersions(projectId, effectiveSelected.id).then(setVersions).catch(() => undefined);
        api.wikiCount(projectId).then((result) => setWikiPageCount(result.count)).catch(() => undefined);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [effectiveSelected?.id, chapters]);

  const onDraftChange = (value: string) => {
    setDraft(value);
    if (effectiveSelected && projectId) {
      api.updateChapter(projectId, effectiveSelected.id, { draft: value }).catch(() => undefined);
    }
  };

  const createChapter = async () => {
    if (!projectId) return;
    const nextNumber = chapters.reduce((max, chapter) => Math.max(max, chapter.chapter_number), 0) + 1;
    const created = await api.createChapter(projectId, {
      chapter_number: nextNumber,
      title: `第 ${nextNumber} 章`,
      brief: '',
      draft: '',
    });
    await reload();
    setSelectedChapter(created);
    setDraft('');
    navigate(`/projects/${projectId}/writing/${created.id}`, { replace: true });
    setLog(`已创建第 ${nextNumber} 章`);
  };

  const deleteChapter = async (chapter: Chapter) => {
    if (!projectId) return;
    await api.deleteChapter(projectId, chapter.id);
    setSelectedChapter(null);
    await reload();
    setLog(`已删除第 ${chapter.chapter_number} 章`);
  };

  const generateDraft = async (payload: { prompt: string; tone: string; style: string; length: string; viewpoint: string; selectedText: string; emotionalIntent?: string; workflow?: string; mode: 'draft' | 'continue' | 'revise' }) => {
    if (!projectId || !effectiveSelected) return '请先选择章节。';
    const workflow = payload.workflow || (payload.mode === 'revise' ? 'revise_selection' : 'generate_chapter_draft');
    setLog('正在生成…');
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
      setLog(result.status === 'local' ? '本地占位结果（未配置模型）' : '模型已返回正文结果');
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
    setVersions(await api.listVersions(projectId, effectiveSelected.id));
    setLog('已保存为候选版本。');
  };

  const selectVersion = async (versionId: string) => {
    if (!projectId || !effectiveSelected) return;
    const version = versions.find((item) => item.id === versionId);
    if (!version) return;
    const updated = await api.selectVersion(projectId, effectiveSelected.id, versionId);
    setDraft(updated.draft ?? version.content);
    setSelectedChapter({ ...effectiveSelected, draft: updated.draft ?? version.content, selected_version_id: versionId });
    setLog('已切换到该版本。');
  };

  const scoreChapter = async () => {
    if (!projectId || !effectiveSelected) return;
    setLog('正在评分…');
    await api.runAi(projectId, 'score_chapter', {
      chapter_id: effectiveSelected.id,
      chapter_number: effectiveSelected.chapter_number,
      chapter_title: effectiveSelected.title,
      draft,
    });
    setLog('评分完成。');
  };

  const wordCount = draft.trim().length;

  return (
    <>
      {immersive && (
        <button className="immersive-exit" onClick={() => setImmersive(false)} aria-label="退出沉浸模式">
          <Minimize2 size={13} /> 退出沉浸 · Esc
        </button>
      )}
      <NovelEditorPage
        project={project}
        chapters={chapters}
        selectedChapter={effectiveSelected}
        versions={versions}
        draft={draft}
        log={log}
        modelLabel="草稿自动保存"
        wikiPageCount={wikiPageCount}
        immersive={immersive}
        onToggleImmersive={() => setImmersive(!immersive)}
        onCreateChapter={() => void createChapter()}
        onImport={() => setImportOpen(true)}
        onDeleteChapter={(chapter) => void deleteChapter(chapter)}
        onSelectChapter={loadChapter}
        onDraftChange={onDraftChange}
        onChapterTitleChange={(title) => {
          if (effectiveSelected && projectId) {
            api.updateChapter(projectId, effectiveSelected.id, { title }).catch(() => undefined);
            setSelectedChapter({ ...effectiveSelected, title });
          }
        }}
        onSaveChapter={() => {
          if (effectiveSelected && projectId) {
            api.updateChapter(projectId, effectiveSelected.id, { draft }).catch(() => undefined);
            setSelectedChapter({ ...effectiveSelected, draft });
          }
          setLog('已保存');
        }}
        onGenerateVariant={() => setLog('在右侧选择生成动作创建候选版本。')}
        onGenerateChapterDraft={generateDraft}
        onSaveAiResultAsVersion={saveAsVersion}
        onScoreChapter={() => void scoreChapter()}
        onFinalizeChapter={() => {
          if (effectiveSelected && projectId) {
            void api
              .finalizeChapter(projectId, effectiveSelected.id)
              .then(async () => {
                await reload();
                setLog('本章已定稿，并触发记忆编译。');
              })
              .catch((error) => setLog(error instanceof Error ? error.message : '定稿失败'));
          }
        }}
        onSelectVersion={(versionId) => void selectVersion(versionId)}
        onOpenResource={(resource) => {
          const target = resource === 'characters' ? 'characters' : resource === 'outline' ? 'outline' : 'world';
          navigate(`/projects/${projectId}/${target}`);
        }}
        onLog={setLog}
      />
      {importOpen && projectId && (
        <ImportModal
          projectId={projectId}
          chapters={chapters}
          onClose={() => setImportOpen(false)}
          onImported={async (message, importedChapterId) => {
            setImportOpen(false);
            await reload();
            const imported = importedChapterId ? (await api.listChapters(projectId)).find((chapter) => chapter.id === importedChapterId) : null;
            if (imported) loadChapter(imported);
            setLog(message);
          }}
        />
      )}
    </>
  );
}
