import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { expect, test, vi } from 'vitest';
import { Chapter, ChapterVersion, Project } from '../api';
import { WorkspaceProvider } from '../shell/workspace';
import { NovelEditorPage } from './NovelEditorPage';

const project: Project = { id: 'p1', title: '雨夜玫瑰' };
const chapter: Chapter = {
  id: 'ch-1',
  project_id: 'p1',
  chapter_number: 1,
  title: '第一章 · 暴雨',
  brief: '',
  draft: '雨夜的开头。',
  summary: '',
  status: 'draft',
};
const versions: ChapterVersion[] = [{ id: 'v1', label: '初稿', content: '初稿内容', created_at: '2026-09-01' }];

function renderEditor(immersive: boolean, onToggleImmersive = vi.fn()) {
  return {
    onToggleImmersive,
    ...render(
      <MemoryRouter initialEntries={['/projects/p1/writing/ch-1']}>
        <WorkspaceProvider projectId="p1">
          <Routes>
            <Route
              path="/projects/:projectId/writing/:chapterId"
              element={
                <NovelEditorPage
                  project={project}
                  chapters={[chapter]}
                  selectedChapter={chapter}
                  versions={versions}
                  draft={chapter.draft}
                  log=""
                  modelLabel="测试模型"
                  wikiPageCount={3}
                  immersive={immersive}
                  onToggleImmersive={onToggleImmersive}
                  onCreateChapter={() => undefined}
                  onDeleteChapter={() => undefined}
                  onSelectChapter={() => undefined}
                  onDraftChange={() => undefined}
                  onChapterTitleChange={() => undefined}
                  onSaveChapter={() => undefined}
                  onGenerateVariant={() => undefined}
                  onGenerateChapterDraft={() => Promise.resolve('')}
                  onSaveAiResultAsVersion={() => Promise.resolve()}
                  onScoreChapter={() => undefined}
                  onFinalizeChapter={() => undefined}
                  onSelectVersion={() => undefined}
                  onOpenResource={() => undefined}
                  onLog={() => undefined}
                />
              }
            />
          </Routes>
        </WorkspaceProvider>
      </MemoryRouter>,
    ),
  };
}

test('普通模式提供进入沉浸模式按钮，点击触发回调', () => {
  const { onToggleImmersive } = renderEditor(false);
  fireEvent.click(screen.getByRole('button', { name: '沉浸' }));
  expect(onToggleImmersive).toHaveBeenCalledTimes(1);
});

test('沉浸模式下按钮变为退出且默认折叠两侧栏', () => {
  renderEditor(true);
  expect(screen.getByRole('button', { name: '退出沉浸' })).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: '退出沉浸' })).not.toBeNull();
  const editor = document.querySelector('.novel-editor-page');
  expect(editor?.className).not.toContain('has-left');
  expect(editor?.className).not.toContain('has-right');
});

test('非沉浸模式下不显示退出按钮', () => {
  renderEditor(false);
  expect(screen.queryByRole('button', { name: '退出沉浸' })).toBeNull();
});

test('编辑器渲染章节标题与字数', () => {
  renderEditor(false);
  expect(screen.getByDisplayValue('第一章 · 暴雨')).toBeInTheDocument();
  expect(screen.getAllByText(/6 字/).length).toBeGreaterThan(0);
});

test('选中文本后出现 AI 浮动工具栏并可执行润色动作', async () => {
  const draftSpy = vi.fn();
  const generate = vi.fn().mockResolvedValue('润色后的句子');
  render(
    <MemoryRouter>
      <WorkspaceProvider projectId="p1">
        <NovelEditorPage
          project={project}
          chapters={[chapter]}
          selectedChapter={chapter}
          versions={versions}
          draft="她合上古籍。"
          log=""
          modelLabel="测试模型"
          wikiPageCount={0}
          onCreateChapter={() => undefined}
          onDeleteChapter={() => undefined}
          onSelectChapter={() => undefined}
          onDraftChange={draftSpy}
          onChapterTitleChange={() => undefined}
          onSaveChapter={() => undefined}
          onGenerateVariant={() => undefined}
          onGenerateChapterDraft={generate}
          onSaveAiResultAsVersion={() => Promise.resolve()}
          onScoreChapter={() => undefined}
          onFinalizeChapter={() => undefined}
          onSelectVersion={() => undefined}
          onOpenResource={() => undefined}
          onLog={() => undefined}
        />
      </WorkspaceProvider>
    </MemoryRouter>,
  );

  const editor = screen.getByPlaceholderText('在这里写下这一章...') as HTMLTextAreaElement;
  editor.setSelectionRange(0, 5);
  fireEvent.mouseUp(editor);
  expect(screen.getByRole('button', { name: '润色' })).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: '润色' }));
  await vi.waitFor(() => expect(generate).toHaveBeenCalled());
});
