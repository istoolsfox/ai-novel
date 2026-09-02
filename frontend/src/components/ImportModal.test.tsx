import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { expect, test, vi } from 'vitest';
import { api, ImportPreview } from '../api';
import { ImportModal } from './ImportModal';

const chapterStub = { id: 'ch1', project_id: 'p1', chapter_number: 1, title: '风起', brief: '', draft: '', summary: '', status: 'draft' };

const novelPreview: ImportPreview = {
  mode: 'novel',
  chapter_count: 2,
  total_words: 5200,
  items: [
    { title: '第一章 风起', words: 2600, preview: '少年推开门，风雪灌了进来。' },
    { title: '第二章 旧友', words: 2600, preview: '茶馆里，故人早已等候多时。' },
  ],
};

test('整本识别 → 展示章节列表 → 导入时调用 importContent', async () => {
  vi.spyOn(api, 'importPreview').mockResolvedValue(novelPreview);
  const importSpy = vi.spyOn(api, 'importContent').mockResolvedValue({
    mode: 'novel',
    imported_chapters: 2,
    chapters: [{ id: 'c1', chapter_number: 1, title: '第一章 风起' }],
  });
  const onImported = vi.fn().mockResolvedValue(undefined);

  render(<ImportModal projectId="p1" chapters={[chapterStub]} onClose={vi.fn()} onImported={onImported} />);

  fireEvent.change(screen.getByPlaceholderText('在此粘贴小说全文或片段…'), { target: { value: '第一章 风起\n\n正文……' } });
  fireEvent.click(screen.getByRole('button', { name: '自动识别' }));

  expect(await screen.findByText(/识别到/)).toBeInTheDocument();
  expect(screen.getByText('第一章 风起')).toBeInTheDocument();

  fireEvent.click(screen.getByRole('button', { name: '导入 2 章' }));
  await waitFor(() => expect(importSpy).toHaveBeenCalledWith('p1', expect.objectContaining({ content: '第一章 风起\n\n正文……' })));
  await waitFor(() => expect(onImported).toHaveBeenCalled());
});

test('片段识别为正文 → 显示匹配章节与目标选择 → 导入时回传 target', async () => {
  vi.spyOn(api, 'importPreview').mockResolvedValue({
    mode: 'fragment',
    layer: 'chapter',
    layer_label: '章节正文',
    words: 40,
    preview: '风雪更急了……',
    matched_chapter: { id: 'ch1', chapter_number: 1, title: '风起', score: 0.42 },
  });
  const importSpy = vi.spyOn(api, 'importContent').mockResolvedValue({
    mode: 'fragment',
    layer: 'chapter',
    appended_to: { id: 'ch1', chapter_number: 1, title: '风起' },
  });
  const onImported = vi.fn().mockResolvedValue(undefined);

  render(<ImportModal projectId="p1" chapters={[chapterStub]} onClose={vi.fn()} onImported={onImported} />);

  fireEvent.change(screen.getByPlaceholderText('在此粘贴小说全文或片段…'), { target: { value: '风雪更急了……' } });
  fireEvent.click(screen.getByRole('button', { name: '自动识别' }));

  expect(await screen.findByText(/识别为/)).toBeInTheDocument();
  expect(screen.getByText(/自动匹配：第 1 章 风起/)).toBeInTheDocument();

  fireEvent.click(screen.getByRole('button', { name: '确认导入' }));
  await waitFor(() => expect(importSpy).toHaveBeenCalledWith('p1', expect.objectContaining({ content: '风雪更急了……' })));
  // auto 模式由后端自动匹配章节，不应显式传 target_chapter_id
  const payload = importSpy.mock.calls[0][1];
  expect(payload.target_chapter_id).toBeUndefined();
});

test('片段识别为人物档案 → 导入时不带 target_chapter_id', async () => {
  vi.spyOn(api, 'importPreview').mockResolvedValue({
    mode: 'fragment',
    layer: 'character',
    layer_label: '人物档案',
    words: 60,
    preview: '姓名：沈照夜……',
    matched_chapter: null,
  });
  const importSpy = vi.spyOn(api, 'importContent').mockResolvedValue({
    mode: 'fragment',
    layer: 'character',
    layer_label: '人物档案',
    record_id: 'r1',
    title: '沈照夜',
  });

  render(<ImportModal projectId="p1" chapters={[chapterStub]} onClose={vi.fn()} onImported={vi.fn()} />);

  fireEvent.change(screen.getByPlaceholderText('在此粘贴小说全文或片段…'), { target: { value: '姓名：沈照夜' } });
  fireEvent.click(screen.getByRole('button', { name: '自动识别' }));
  expect(await screen.findByText(/识别为/)).toHaveTextContent('人物档案');

  fireEvent.click(screen.getByRole('button', { name: '确认导入' }));
  await waitFor(() =>
    expect(importSpy).toHaveBeenCalledWith('p1', expect.not.objectContaining({ target_chapter_id: expect.anything() })),
  );
});
