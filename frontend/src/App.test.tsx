import { render, screen } from '@testing-library/react';
import { expect, test } from 'vitest';
import App from './App';

test('renders the local AI novel workbench shell', () => {
  render(<App />);
  expect(screen.getByText('AI 小说创作平台')).toBeInTheDocument();
  expect(screen.getByText('项目库')).toBeInTheDocument();
  expect(screen.getByText(/CLAUDE\.md/)).toBeInTheDocument();
  expect(screen.getByText('章节编辑器')).toBeInTheDocument();
  expect(screen.getByText('llmwiki 记忆')).toBeInTheDocument();
});
