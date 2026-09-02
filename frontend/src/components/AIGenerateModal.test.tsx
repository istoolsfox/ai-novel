import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { expect, test, vi } from 'vitest';
import { AiResult, api } from '../api';
import { AIGenerateModal } from './AIGenerateModal';

const stubResult: AiResult = {
  workflow: 'generate_setting',
  model: 'local-stub',
  text: '[{"name":"灰塔","category":"Locations","description":"档案楼阁"},{"name":"守夜人议会","category":"Organizations","description":"中立联盟"}]',
  structured: [
    { name: '灰塔', category: 'Locations', description: '档案楼阁' },
    { name: '守夜人议会', category: 'Organizations', description: '中立联盟' },
  ],
  score: 0,
  status: 'local',
  items: [],
};

test('生成 → 预览结果 → 保存时回传解析后的条目', async () => {
  vi.spyOn(api, 'runAi').mockResolvedValue(stubResult);
  const onSave = vi.fn().mockResolvedValue(undefined);
  const onClose = vi.fn();

  render(
    <AIGenerateModal
      projectId="p1"
      title="AI 生成世界观设定"
      workflow="generate_setting"
      buildPayload={(prompt) => ({ prompt })}
      onSave={onSave}
      onClose={onClose}
    />,
  );

  fireEvent.change(screen.getByPlaceholderText('描述你想要的风格、侧重和约束…'), { target: { value: '雨城与记忆规则' } });
  fireEvent.click(screen.getByRole('button', { name: '生成' }));

  expect(await screen.findByText(/AI Generated · 2 条/)).toBeInTheDocument();
  expect(screen.getByText(/守夜人议会/)).toBeInTheDocument();

  fireEvent.click(screen.getByRole('button', { name: '保存到项目' }));
  await waitFor(() => expect(onSave).toHaveBeenCalledTimes(1));
  const items = onSave.mock.calls[0][0];
  expect(items).toHaveLength(2);
  expect(items[0]).toMatchObject({ title: '灰塔', content: '档案楼阁' });
  await waitFor(() => expect(onClose).toHaveBeenCalled());
});

test('AI 调用失败时展示错误且不关闭弹窗', async () => {
  vi.spyOn(api, 'runAi').mockRejectedValue(new Error('远程模型调用失败'));
  const onSave = vi.fn();
  const onClose = vi.fn();

  render(
    <AIGenerateModal
      projectId="p1"
      title="AI 生成人物"
      workflow="generate_characters"
      buildPayload={() => ({})}
      onSave={onSave}
      onClose={onClose}
    />,
  );

  fireEvent.click(screen.getByRole('button', { name: '生成' }));
  expect(await screen.findByText(/远程模型调用失败/)).toBeInTheDocument();
  expect(onSave).not.toHaveBeenCalled();
  expect(onClose).not.toHaveBeenCalled();
});
