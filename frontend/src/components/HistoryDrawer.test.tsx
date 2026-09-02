import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { expect, test, vi } from 'vitest';
import { api, GenericRecord, RecordRevision } from '../api';
import { HistoryDrawer } from './HistoryDrawer';

const record: GenericRecord = { id: 'rec-1', title: '沈照夜', category: '主角', content: '当前设定', status: 'active' };

const revisions: RecordRevision[] = [
  {
    id: 'rev-3',
    resource: 'character-profiles',
    record_id: 'rec-1',
    title: '沈照夜',
    category: '主角',
    content: '第三版设定',
    status: 'active',
    origin: 'update',
    created_at: '2026-09-02T10:00:00+00:00',
  },
  {
    id: 'rev-1',
    resource: 'character-profiles',
    record_id: 'rec-1',
    title: '沈照夜',
    category: '主角',
    content: '初版设定',
    status: 'active',
    origin: 'create',
    created_at: '2026-09-01T09:00:00+00:00',
  },
];

test('历史抽屉列出全部版本并标记当前', async () => {
  vi.spyOn(api, 'listRecordRevisions').mockResolvedValue(revisions);

  render(<HistoryDrawer projectId="p1" resource="character-profiles" record={record} onClose={() => undefined} onRestored={() => undefined} />);

  expect(await screen.findByText('第三版设定')).toBeInTheDocument();
  expect(screen.getByText('初版设定')).toBeInTheDocument();
  expect(screen.getByText('当前')).toBeInTheDocument();
  expect(screen.getByText('创建')).toBeInTheDocument();
});

test('点击恢复会调用 API 并回调更新后的记录', async () => {
  vi.spyOn(api, 'listRecordRevisions').mockResolvedValue(revisions);
  const restored: GenericRecord = { ...record, content: '初版设定' };
  vi.spyOn(api, 'restoreRecordRevision').mockResolvedValue(restored);
  const onRestored = vi.fn();

  render(<HistoryDrawer projectId="p1" resource="character-profiles" record={record} onClose={() => undefined} onRestored={onRestored} />);

  await screen.findByText('初版设定');
  fireEvent.click(screen.getAllByRole('button', { name: /恢复此版本/ })[0]);

  await waitFor(() => expect(api.restoreRecordRevision).toHaveBeenCalledWith('p1', 'character-profiles', 'rec-1', 'rev-1'));
  await waitFor(() => expect(onRestored).toHaveBeenCalledWith(restored));
});
