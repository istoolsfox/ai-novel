import { render, screen } from '@testing-library/react';
import { expect, test, vi } from 'vitest';
import { RelationshipGraphWorkbench } from './RelationshipGraphWorkbench';

if (!globalThis.ResizeObserver) {
  globalThis.ResizeObserver = class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
}

test('renders relationship nodes with dedicated polished graph styling', async () => {
  render(
    <RelationshipGraphWorkbench
      relationships={[
        {
          id: 'relationship-1',
          title: '沈照夜 → 主线剧情',
          category: '主线关联',
          content: '推动记忆古籍主线',
          payload: {
            source_character: '沈照夜',
            target_character: '主线剧情',
            relationship_type: '主线关联',
          },
          status: 'active',
        },
      ]}
      characters={[
        {
          id: 'character-1',
          title: '沈照夜',
          category: 'character',
          content: '前朝公主',
          payload: { name: '沈照夜' },
          status: 'active',
        },
      ]}
      form={{
        source_character: '',
        target_character: '',
        relationship_type: '朋友',
        strength: 50,
        conflict: '',
        change_history: '',
        related_chapters: '',
      }}
      aiResults={[]}
      modelLabel="本地模型"
      onFormChange={vi.fn()}
      onSaveRelationship={vi.fn()}
      onCreateCharacter={vi.fn()}
      onGenerate={vi.fn()}
      onApplyResult={vi.fn()}
    />,
  );

  const characterNode = (await screen.findByText('沈照夜')).closest('.react-flow__node');

  expect(characterNode).toHaveClass('story-character-node');
  expect(characterNode).toHaveAttribute('data-draggable-node', 'true');
});
