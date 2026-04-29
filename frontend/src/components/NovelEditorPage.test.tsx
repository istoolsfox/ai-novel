import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { expect, test, vi } from 'vitest';
import { NovelEditorPage } from './NovelEditorPage';

const previewContent =
  '她合上古籍时，窗外的雨声忽然停了。不是雨停了，而是整座城像被某种看不见的手按住了呼吸。';

function renderNovelEditorPage(draft = '重复 目标 重复 目标') {
  const onDraftChange = vi.fn();
  const onGenerateChapterDraft = vi.fn().mockResolvedValue('生成结果');
  const onLog = vi.fn();
  const onOpenResource = vi.fn();
  const onDeleteChapter = vi.fn();

  const view = render(
    <NovelEditorPage
      project={null}
      chapters={[]}
      selectedChapter={null}
      versions={[]}
      draft={draft}
      log=""
      modelLabel="本地模型"
      wikiPageCount={0}
      onCreateChapter={vi.fn()}
      onDeleteChapter={onDeleteChapter}
      onSelectChapter={vi.fn()}
      onDraftChange={onDraftChange}
      onChapterTitleChange={vi.fn()}
      onSaveChapter={vi.fn()}
      onGenerateVariant={vi.fn()}
      onGenerateChapterDraft={onGenerateChapterDraft}
      onSaveAiResultAsVersion={vi.fn().mockResolvedValue(undefined)}
      onScoreChapter={vi.fn()}
      onFinalizeChapter={vi.fn()}
      onSelectVersion={vi.fn()}
      onOpenSettings={vi.fn()}
      onOpenResource={onOpenResource}
      onLog={onLog}
    />
  );

  return { ...view, onDeleteChapter, onDraftChange, onGenerateChapterDraft, onLog, onOpenResource };
}

test('replaces the exact selected range when duplicate selected text appears in the draft', () => {
  const draft = '重复 目标 重复 目标';
  const { onDraftChange } = renderNovelEditorPage(draft);
  const editor = screen.getByPlaceholderText('请先创建或选择章节') as HTMLTextAreaElement;
  const secondTargetStart = draft.lastIndexOf('目标');

  editor.setSelectionRange(secondTargetStart, secondTargetStart + '目标'.length);
  fireEvent.mouseUp(editor);
  fireEvent.click(screen.getByRole('button', { name: '替换选中内容' }));

  expect(onDraftChange).toHaveBeenCalledWith(`重复 目标 重复 ${previewContent}`);
});

test('appends AI result instead of replacing a stale selected range after draft changes', () => {
  const draft = '甲 目标 乙';
  const { onDraftChange, rerender } = renderNovelEditorPage(draft);
  const editor = screen.getByPlaceholderText('请先创建或选择章节') as HTMLTextAreaElement;
  const targetStart = draft.indexOf('目标');

  editor.setSelectionRange(targetStart, targetStart + '目标'.length);
  fireEvent.mouseUp(editor);

  rerender(
    <NovelEditorPage
      project={null}
      chapters={[]}
      selectedChapter={null}
      versions={[]}
      draft="新的正文"
      log=""
      modelLabel="本地模型"
      wikiPageCount={0}
      onCreateChapter={vi.fn()}
      onDeleteChapter={vi.fn()}
      onSelectChapter={vi.fn()}
      onDraftChange={onDraftChange}
      onChapterTitleChange={vi.fn()}
      onSaveChapter={vi.fn()}
      onGenerateVariant={vi.fn()}
      onGenerateChapterDraft={vi.fn().mockResolvedValue('生成结果')}
      onSaveAiResultAsVersion={vi.fn().mockResolvedValue(undefined)}
      onScoreChapter={vi.fn()}
      onFinalizeChapter={vi.fn()}
      onSelectVersion={vi.fn()}
      onOpenSettings={vi.fn()}
      onOpenResource={vi.fn()}
      onLog={vi.fn()}
    />
  );

  fireEvent.click(screen.getByRole('button', { name: '替换选中内容' }));

  expect(onDraftChange).toHaveBeenCalledWith(`新的正文\n\n${previewContent}`);
  expect(onDraftChange).not.toHaveBeenCalledWith(`新的${previewContent}文`);
});

test('appends AI result when external draft changes but same range still has same selected text', () => {
  const draft = '甲 目标 乙';
  const { onDraftChange, onLog, rerender } = renderNovelEditorPage(draft);
  const editor = screen.getByPlaceholderText('请先创建或选择章节') as HTMLTextAreaElement;
  const targetStart = draft.indexOf('目标');

  editor.setSelectionRange(targetStart, targetStart + '目标'.length);
  fireEvent.mouseUp(editor);

  rerender(
    <NovelEditorPage
      project={null}
      chapters={[]}
      selectedChapter={null}
      versions={[]}
      draft="丙 目标 丁"
      log=""
      modelLabel="本地模型"
      wikiPageCount={0}
      onCreateChapter={vi.fn()}
      onDeleteChapter={vi.fn()}
      onSelectChapter={vi.fn()}
      onDraftChange={onDraftChange}
      onChapterTitleChange={vi.fn()}
      onSaveChapter={vi.fn()}
      onGenerateVariant={vi.fn()}
      onGenerateChapterDraft={vi.fn().mockResolvedValue('生成结果')}
      onSaveAiResultAsVersion={vi.fn().mockResolvedValue(undefined)}
      onScoreChapter={vi.fn()}
      onFinalizeChapter={vi.fn()}
      onSelectVersion={vi.fn()}
      onOpenSettings={vi.fn()}
      onOpenResource={vi.fn()}
      onLog={onLog}
    />
  );

  fireEvent.click(screen.getByRole('button', { name: '替换选中内容' }));

  expect(onDraftChange).toHaveBeenCalledWith(`丙 目标 丁\n\n${previewContent}`);
  expect(onDraftChange).not.toHaveBeenCalledWith(`丙 ${previewContent} 丁`);
  expect(onLog).toHaveBeenCalledWith('选区已失效，AI 结果已追加到正文。');
});

test('uses revise mode for floating toolbar polish action on selected text', async () => {
  const draft = '第一句需要润色，第二句保留。';
  const { onGenerateChapterDraft } = renderNovelEditorPage(draft);
  const editor = screen.getByPlaceholderText('请先创建或选择章节') as HTMLTextAreaElement;
  const selectedText = '需要润色';
  const selectionStart = draft.indexOf(selectedText);

  editor.setSelectionRange(selectionStart, selectionStart + selectedText.length);
  fireEvent.mouseUp(editor);
  fireEvent.click(screen.getByRole('button', { name: '润色' }));

  await waitFor(() => expect(onGenerateChapterDraft).toHaveBeenCalled());
  expect(onGenerateChapterDraft).toHaveBeenCalledWith(
    expect.objectContaining({
      mode: 'revise',
      selectedText,
    })
  );
});

test('displays and inserts only clean chapter prose from structured draft JSON', async () => {
  const onDraftChange = vi.fn();
  const onGenerateChapterDraft = vi.fn().mockResolvedValue(JSON.stringify({
    chapter_id: '82e6ece9e96a46e8a598901be20ee198',
    drafts: [
      {
        index: 1,
        title: '第八十二章 雨夜归人',
        content: '林澈推开档案室的门。\n\n灯同时灭了。',
      },
      {
        index: 2,
        title: '备用版本',
        content: '不应该一次展示多个版本。',
      },
    ],
  }));

  render(
    <NovelEditorPage
      project={{ id: 'project-1', title: '前朝公主' }}
      chapters={[{
        id: 'chapter-1',
        project_id: 'project-1',
        chapter_number: 1,
        title: '第 1 章',
        brief: '',
        draft: '',
        summary: '',
        status: 'draft',
      }]}
      selectedChapter={{
        id: 'chapter-1',
        project_id: 'project-1',
        chapter_number: 1,
        title: '第 1 章',
        brief: '',
        draft: '',
        summary: '',
        status: 'draft',
      }}
      versions={[]}
      draft=""
      log=""
      modelLabel="本地模型"
      wikiPageCount={3}
      onCreateChapter={vi.fn()}
      onDeleteChapter={vi.fn()}
      onSelectChapter={vi.fn()}
      onDraftChange={onDraftChange}
      onChapterTitleChange={vi.fn()}
      onSaveChapter={vi.fn()}
      onGenerateVariant={vi.fn()}
      onGenerateChapterDraft={onGenerateChapterDraft}
      onSaveAiResultAsVersion={vi.fn().mockResolvedValue(undefined)}
      onScoreChapter={vi.fn()}
      onFinalizeChapter={vi.fn()}
      onSelectVersion={vi.fn()}
      onOpenSettings={vi.fn()}
      onOpenResource={vi.fn()}
      onLog={vi.fn()}
    />,
  );

  fireEvent.click(screen.getByRole('button', { name: '一键生成本章正文' }));
  expect(await screen.findByText(/林澈推开档案室的门[\s\S]*灯同时灭了/)).toBeInTheDocument();
  expect(screen.queryByText(/chapter_id/)).not.toBeInTheDocument();
  expect(screen.queryByText(/第八十二章/)).not.toBeInTheDocument();

  fireEvent.click(screen.getAllByRole('button', { name: '插入正文' })[0]);

  expect(onDraftChange).toHaveBeenCalledWith('林澈推开档案室的门。\n\n灯同时灭了。');
});

test('offers richer tone and style choices for chapter generation', () => {
  renderNovelEditorPage();

  expect(screen.getByRole('option', { name: '悬疑' })).toBeInTheDocument();
  expect(screen.getByRole('option', { name: '暗黑' })).toBeInTheDocument();
  expect(screen.getByRole('option', { name: '群像史诗' })).toBeInTheDocument();
  expect(screen.getByRole('option', { name: '古风权谋' })).toBeInTheDocument();
  expect(screen.getByRole('option', { name: '意识流' })).toBeInTheDocument();
});

test('deletes an AI result card from the assistant panel', () => {
  renderNovelEditorPage();

  expect(screen.getByText('AI 续写建议')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: '删除结果' }));

  expect(screen.queryByText('AI 续写建议')).not.toBeInTheDocument();
});

test('resource buttons in the editor sidebar navigate to their workbenches', () => {
  const { onOpenResource } = renderNovelEditorPage();

  fireEvent.click(screen.getByRole('button', { name: '角色' }));
  fireEvent.click(screen.getByRole('button', { name: '大纲' }));
  fireEvent.click(screen.getByRole('button', { name: '灵感库' }));

  expect(onOpenResource).toHaveBeenCalledWith('characters');
  expect(onOpenResource).toHaveBeenCalledWith('outline');
  expect(onOpenResource).toHaveBeenCalledWith('knowledge');
});

test('deletes the selected chapter from the chapter tree after confirmation', () => {
  vi.spyOn(window, 'confirm').mockReturnValue(true);
  const onDeleteChapter = vi.fn();

  render(
    <NovelEditorPage
      project={{ id: 'project-1', title: '前朝公主' }}
      chapters={[{
        id: 'chapter-1',
        project_id: 'project-1',
        chapter_number: 1,
        title: '第 1 章',
        brief: '',
        draft: '',
        summary: '',
        status: 'draft',
      }]}
      selectedChapter={{
        id: 'chapter-1',
        project_id: 'project-1',
        chapter_number: 1,
        title: '第 1 章',
        brief: '',
        draft: '',
        summary: '',
        status: 'draft',
      }}
      versions={[]}
      draft=""
      log=""
      modelLabel="本地模型"
      wikiPageCount={0}
      onCreateChapter={vi.fn()}
      onDeleteChapter={onDeleteChapter}
      onSelectChapter={vi.fn()}
      onDraftChange={vi.fn()}
      onChapterTitleChange={vi.fn()}
      onSaveChapter={vi.fn()}
      onGenerateVariant={vi.fn()}
      onGenerateChapterDraft={vi.fn().mockResolvedValue('生成结果')}
      onSaveAiResultAsVersion={vi.fn().mockResolvedValue(undefined)}
      onScoreChapter={vi.fn()}
      onFinalizeChapter={vi.fn()}
      onSelectVersion={vi.fn()}
      onOpenSettings={vi.fn()}
      onOpenResource={vi.fn()}
      onLog={vi.fn()}
    />,
  );

  fireEvent.click(screen.getByRole('button', { name: /删除章节 第 1 章/ }));

  expect(onDeleteChapter).toHaveBeenCalledWith(expect.objectContaining({ id: 'chapter-1' }));
});
