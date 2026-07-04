import { fireEvent, render, screen } from '@testing-library/react';
import { expect, test, vi } from 'vitest';
import { AIResultCard } from './AIResultCard';

const result = {
  id: 'result-1',
  title: '续写建议',
  content: '她在雨夜里听见了远处的钟声。',
};

test('renders gated AI result actions and triggers callbacks', () => {
  const onInsert = vi.fn();
  const onReplace = vi.fn();
  const onApply = vi.fn();
  const onSaveVersion = vi.fn();
  const onFavorite = vi.fn();
  const onRegenerate = vi.fn();

  render(
    <AIResultCard
      result={result}
      canInsert
      canReplace
      canApply
      canSaveVersion
      canFavorite
      onInsert={onInsert}
      onReplace={onReplace}
      onApply={onApply}
      onSaveVersion={onSaveVersion}
      onFavorite={onFavorite}
      onRegenerate={onRegenerate}
    />
  );

  fireEvent.click(screen.getByRole('button', { name: '插入正文' }));
  fireEvent.click(screen.getByRole('button', { name: '替换选中内容' }));
  fireEvent.click(screen.getByRole('button', { name: '应用到当前表单' }));
  fireEvent.click(screen.getByRole('button', { name: '保存为版本' }));
  fireEvent.click(screen.getByRole('button', { name: '收藏到灵感库' }));
  expect(screen.getByRole('button', { name: '复制' })).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: '重新生成' }));

  expect(onInsert).toHaveBeenCalledTimes(1);
  expect(onReplace).toHaveBeenCalledTimes(1);
  expect(onApply).toHaveBeenCalledTimes(1);
  expect(onSaveVersion).toHaveBeenCalledTimes(1);
  expect(onFavorite).toHaveBeenCalledTimes(1);
  expect(onRegenerate).toHaveBeenCalledTimes(1);
});

test('renders local fallback copy for error results', () => {
  render(
    <AIResultCard
      result={{
        ...result,
        status: 'error',
        error: '网络错误',
      }}
    />
  );

  expect(screen.getByText('远程模型调用失败，已回退到本地占位结果：网络错误')).toBeInTheDocument();
});

test('renders slow generation timeout as still generating copy', () => {
  render(
    <AIResultCard
      result={{
        ...result,
        status: 'error',
        error: '远程模型仍可能在生成，但 600 秒内暂未返回结果。原始错误：timed out',
      }}
    />
  );

  expect(screen.getByText('远程模型仍可能在生成，当前显示本地占位结果：远程模型仍可能在生成，但 600 秒内暂未返回结果。原始错误：timed out')).toBeInTheDocument();
});
