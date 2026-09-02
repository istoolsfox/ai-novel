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

  const effectiveSelected = selectedChapter ?? chapters[0] ?? null;

  const onSelectChapter = (chapter: Chapter) => {
    setSelectedChapter(chapter);
    setDraft(chapter.draft ?? '');
    setLog('');
    if (projectId) {
      api.listVersions(projectId, chapter.id).then(setVersions).catch(() => undefined);
    }
  };

  const onDraftChange = (value: string) => {
    setDraft(value);
    if (effectiveSelected && projectId) {
      api.updateChapter(projectId, effectiveSelected.id, { draft: value }).catch(() => undefined);
    }
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
      wikiPageCount={0}
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
      onSaveChapter={() => setLog('Saved')}
      onGenerateVariant={() => undefined}
      onGenerateChapterDraft={async () => ''}
      onSaveAiResultAsVersion={async () => undefined}
      onScoreChapter={() => undefined}
      onFinalizeChapter={() => undefined}
      onSelectVersion={() => undefined}
      onOpenResource={() => undefined}
      onLog={setLog}
    />
  );
}
