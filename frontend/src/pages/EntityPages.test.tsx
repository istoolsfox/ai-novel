import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { expect, test, vi } from 'vitest';
import { api, GenericRecord } from '../api';
import { Characters } from './Characters';
import { World } from './World';

const character: GenericRecord = {
  id: 'char-1',
  title: '沈照夜',
  category: '主角',
  content: '前朝公主，流亡中。',
  payload: { role: '前朝公主', traits: '冷静、警惕', desire: '夺回真相' },
  status: 'active',
};

const worldEntity: GenericRecord = {
  id: 'loc-1',
  title: '灰塔旧城',
  category: 'Locations',
  content: '档案楼阁层层叠叠。',
  status: 'active',
};

function mockRecords(records: Partial<Record<'character-profiles' | 'world-settings', GenericRecord[]>>) {
  vi.spyOn(api, 'listRecords').mockImplementation((_projectId, resource) => {
    return Promise.resolve(records[resource as 'character-profiles' | 'world-settings'] ?? []);
  });
  vi.spyOn(api, 'createRecord').mockResolvedValue(character);
  vi.spyOn(api, 'updateRecord').mockResolvedValue(character);
  vi.spyOn(api, 'deleteRecord').mockResolvedValue({ ok: true });
  vi.spyOn(api, 'listRecordRevisions').mockResolvedValue([]);
  vi.spyOn(api, 'listChapters').mockResolvedValue([]);
  vi.spyOn(api, 'wikiCount').mockResolvedValue({ count: 0 });
  vi.spyOn(api, 'runAi').mockResolvedValue({
    workflow: 'generate_characters',
    text: '[]',
    structured: [],
    score: 0,
    items: [],
  });
}

function renderPage(page: React.ReactElement, path: string, url: string) {
  return render(
    <MemoryRouter initialEntries={[url]}>
      <Routes>
        <Route path={path} element={page} />
      </Routes>
    </MemoryRouter>,
  );
}

test('人物页展示列表与详情字段', async () => {
  mockRecords({ 'character-profiles': [character] });
  renderPage(<Characters />, '/projects/:projectId/characters', '/projects/p1/characters');

  expect((await screen.findAllByText('沈照夜')).length).toBeGreaterThan(0);
  expect(screen.getAllByText('前朝公主').length).toBeGreaterThan(0);
  expect(screen.getAllByText('夺回真相').length).toBeGreaterThan(0);
});

test('人物页编辑保存调用 updateRecord', async () => {
  mockRecords({ 'character-profiles': [character] });
  renderPage(<Characters />, '/projects/:projectId/characters', '/projects/p1/characters');

  await screen.findAllByText('沈照夜');
  fireEvent.click(screen.getAllByRole('button', { name: /编辑/ })[0]);
  const nameInput = await screen.findByDisplayValue('沈照夜');
  fireEvent.change(nameInput, { target: { value: '沈照夜·改' } });
  fireEvent.click(screen.getByRole('button', { name: '保存修改' }));

  await waitFor(() => expect(api.updateRecord).toHaveBeenCalledTimes(1));
  const [projectId, resource, recordId] = vi.mocked(api.updateRecord).mock.calls[0];
  expect([projectId, resource, recordId]).toEqual(['p1', 'character-profiles', 'char-1']);
  expect(vi.mocked(api.updateRecord).mock.calls[0][3].title).toBe('沈照夜·改');
});

test('人物页删除需确认并调用 deleteRecord', async () => {
  mockRecords({ 'character-profiles': [character] });
  renderPage(<Characters />, '/projects/:projectId/characters', '/projects/p1/characters');

  await screen.findAllByText('沈照夜');
  fireEvent.click(screen.getByRole('button', { name: '删除人物' }));
  fireEvent.click(screen.getByRole('button', { name: '删除' }));
  await waitFor(() => expect(api.deleteRecord).toHaveBeenCalledWith('p1', 'character-profiles', 'char-1'));
});

test('人物页历史按钮打开版本抽屉', async () => {
  mockRecords({ 'character-profiles': [character] });
  renderPage(<Characters />, '/projects/:projectId/characters', '/projects/p1/characters');

  await screen.findAllByText('沈照夜');
  fireEvent.click(screen.getByRole('button', { name: '历史' }));
  await waitFor(() => expect(api.listRecordRevisions).toHaveBeenCalledWith('p1', 'character-profiles', 'char-1'));
  expect(await screen.findByText('版本历史 · 沈照夜')).toBeInTheDocument();
});

test('人物页 AI 生成弹窗使用 generate_characters 工作流', async () => {
  mockRecords({});
  renderPage(<Characters />, '/projects/:projectId/characters', '/projects/p1/characters');

  await screen.findByText('还没有人物');
  fireEvent.click(screen.getAllByRole('button', { name: /AI 生成人物/ })[0]);
  fireEvent.click(screen.getByRole('button', { name: '生成' }));
  await waitFor(() => {
    const [projectId, workflow] = vi.mocked(api.runAi).mock.calls[0];
    expect([projectId, workflow]).toEqual(['p1', 'generate_characters']);
  });
});

test('世界观页按分类切换并新建实体', async () => {
  mockRecords({ 'world-settings': [worldEntity] });
  renderPage(<World />, '/projects/:projectId/world', '/projects/p1/world');

  expect(await screen.findByText('灰塔旧城')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('tab', { name: /组织/ }));
  expect(screen.getByText(/暂无「组织」/)).toBeInTheDocument();

  fireEvent.click(screen.getByRole('tab', { name: /地点/ }));
  fireEvent.click(screen.getByRole('button', { name: /新建实体/ }));
  fireEvent.change(await screen.findByPlaceholderText('如：灰塔旧城区'), { target: { value: '雨城码头' } });
  fireEvent.click(screen.getByRole('button', { name: '创建' }));

  await waitFor(() => expect(api.createRecord).toHaveBeenCalledTimes(1));
  const [projectId, resource, payload] = vi.mocked(api.createRecord).mock.calls[0];
  expect([projectId, resource]).toEqual(['p1', 'world-settings']);
  expect(payload.title).toBe('雨城码头');
});
