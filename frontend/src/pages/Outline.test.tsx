import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, expect, test, vi } from 'vitest';
import { api, Chapter, GenericRecord } from '../api';
import { Outline } from './Outline';

vi.mock('../shell/workspace', () => ({
  useWorkspace: () => ({ project: { id: 'p1', title: '测试小说' }, immersive: false, setImmersive: vi.fn() }),
}));

const bookOutline: GenericRecord = {
  id: 'book-1',
  title: '全书大纲',
  category: 'book_outline',
  content: '',
  payload: {
    premise: '猎雾少年打破灰雾囚笼',
    core_conflict: '少年 vs 雾影会',
    main_arc: '起承转合',
    ending_direction: '破笼',
  },
  status: 'active',
};

const volume: GenericRecord = {
  id: 'vol-1',
  title: '第一卷 · 灰雾之城',
  category: 'volume_outline',
  content: '',
  payload: { volume_number: 1, start_chapter: 1, end_chapter: 10, volume_goal: '揭开圈养真相' },
  status: 'active',
};

const chapter: Chapter = {
  id: 'ch-1',
  project_id: 'p1',
  chapter_number: 1,
  title: '第一章 夜航',
  brief: '少年初次出猎',
  summary: '',
  draft: '',
  status: 'draft',
};

function mockApi(records: GenericRecord[], chapters: Chapter[]) {
  vi.spyOn(api, 'listRecords').mockImplementation((_projectId, resource) =>
    Promise.resolve(resource === 'outlines' ? records : []),
  );
  vi.spyOn(api, 'createRecord').mockResolvedValue(volume);
  vi.spyOn(api, 'updateRecord').mockResolvedValue(volume);
  vi.spyOn(api, 'deleteRecord').mockResolvedValue({ ok: true });
  vi.spyOn(api, 'listRecordRevisions').mockResolvedValue([]);
  vi.spyOn(api, 'listChapters').mockResolvedValue(chapters);
  vi.spyOn(api, 'createChapter').mockResolvedValue(chapter);
  vi.spyOn(api, 'wikiCount').mockResolvedValue({ count: 0 });
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/projects/p1/outline']}>
      <Routes>
        <Route path="/projects/:projectId/outline" element={<Outline />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

test('全书 tab 展示全书大纲字段', async () => {
  mockApi([bookOutline, volume], []);
  renderPage();

  expect((await screen.findAllByText('猎雾少年打破灰雾囚笼')).length).toBeGreaterThan(0);
  expect(screen.getAllByText('少年 vs 雾影会').length).toBeGreaterThan(0);
});

test('卷 tab 列出卷卡片并显示章节范围', async () => {
  mockApi([bookOutline, volume], [chapter]);
  renderPage();

  fireEvent.click(await screen.findByRole('button', { name: /卷大纲/ }));
  expect(await screen.findByText('第一卷 · 灰雾之城')).toBeInTheDocument();
  expect(screen.getByText(/CH 1–10/)).toBeInTheDocument();
  expect(screen.getByText(/揭开圈养真相/)).toBeInTheDocument();
});

test('章节 tab 按卷分组显示章节', async () => {
  mockApi([bookOutline, volume], [chapter]);
  renderPage();

  fireEvent.click(await screen.findByRole('button', { name: /章节大纲/ }));
  expect(await screen.findByText('第一章 夜航')).toBeInTheDocument();
  expect(screen.getByText(/第一卷 · 灰雾之城/)).toBeInTheDocument();
});

test('新建卷默认预填卷号与章节范围', async () => {
  mockApi([bookOutline, volume], []);
  renderPage();

  fireEvent.click(await screen.findByRole('button', { name: /卷大纲/ }));
  fireEvent.click(await screen.findByRole('button', { name: /新建卷/ }));

  const volumeNumber = await screen.findByDisplayValue('2');
  expect(volumeNumber).toBeInTheDocument();
  expect(screen.getByDisplayValue('11')).toBeInTheDocument();
});

test('保存全书大纲写入 book_outline 分类', async () => {
  mockApi([], []);
  const createRecord = vi.spyOn(api, 'createRecord').mockResolvedValue(bookOutline);
  renderPage();

  fireEvent.click(await screen.findByRole('button', { name: /手动创建/ }));
  fireEvent.change(await screen.findByDisplayValue('全书大纲'), { target: { value: '全书大纲' } });
  fireEvent.change(screen.getByLabelText('一句话故事'), { target: { value: '少年破笼' } });
  fireEvent.click(screen.getByRole('button', { name: '创建' }));

  await waitFor(() =>
    expect(createRecord).toHaveBeenCalledWith(
      'p1',
      'outlines',
      expect.objectContaining({ category: 'book_outline' }),
    ),
  );
});
