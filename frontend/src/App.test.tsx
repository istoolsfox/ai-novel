import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, expect, test, vi } from 'vitest';
import { api, GenericRecord } from './api';
import App from './App';

if (!globalThis.ResizeObserver) {
  globalThis.ResizeObserver = class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
}

const mockProject = {
  id: 'project-1',
  title: '测试项目',
};

const mockChapter = {
  id: 'chapter-1',
  project_id: mockProject.id,
  chapter_number: 1,
  title: '第一章',
  brief: '她发现古籍',
  draft: '',
  summary: '',
  status: 'draft',
};

const secondProject = {
  id: 'project-2',
  title: '第二项目',
};

const secondProjectChapter = {
  ...mockChapter,
  id: 'chapter-2',
  project_id: secondProject.id,
  title: '第二章',
};

function mockProjectApi() {
  vi.spyOn(api, 'authStatus').mockRejectedValue(new Error('local mode'));
  vi.spyOn(api, 'listProjects').mockResolvedValue([mockProject]);
  vi.spyOn(api, 'listChapters').mockResolvedValue([]);
  vi.spyOn(api, 'listRecords').mockResolvedValue([]);
  vi.spyOn(api, 'listVersions').mockResolvedValue([]);
  vi.spyOn(api, 'deleteRecord').mockResolvedValue({ ok: true });
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((resolvePromise) => {
    resolve = resolvePromise;
  });
  return { promise, resolve };
}

afterEach(() => {
  vi.restoreAllMocks();
});

test('renders the local AI novel workbench shell', () => {
  render(<App />);
  expect(screen.getByText('AI 小说创作平台')).toBeInTheDocument();
  expect(screen.getByText('项目库')).toBeInTheDocument();
  expect(screen.getByText(/CLAUDE\.md/)).toBeInTheDocument();
  expect(screen.getAllByText('章节编辑器').length).toBeGreaterThan(0);
  expect(screen.getAllByText('正文写作、AI 续写、章节版本与定稿').length).toBeGreaterThan(0);
  expect(screen.getAllByText('llmwiki 记忆').length).toBeGreaterThan(0);
  expect(screen.getByText('Novel Editor')).toBeInTheDocument();
  expect(screen.getByText('AI 创作副驾驶')).toBeInTheDocument();
  expect(screen.getByText('专注模式')).toBeInTheDocument();
  expect(screen.getByText('续写当前章节')).toBeInTheDocument();
  expect(screen.getByText('插入正文')).toBeInTheDocument();
  expect(screen.getByLabelText('章节选择')).toBeInTheDocument();
  expect(screen.getByLabelText('章节顺序')).toBeInTheDocument();
  expect(screen.getByLabelText('章节搜索')).toBeInTheDocument();
});

test('renders settings entry and model configuration form', () => {
  render(<App />);
  fireEvent.click(screen.getByText('设置'));
  expect(screen.getAllByText('账户与同步').length).toBeGreaterThan(0);
  expect(screen.getAllByText('本地模式').length).toBeGreaterThan(0);
  expect(screen.getByText('继续本地使用')).toBeInTheDocument();
  expect(screen.getByText('OAuth 登录')).toBeInTheDocument();
  expect(screen.getAllByText('模型配置').length).toBeGreaterThan(0);
  fireEvent.click(screen.getByRole('button', { name: /模型配置/ }));
  expect(screen.getByLabelText('配置名称')).toBeInTheDocument();
  expect(screen.getByLabelText('API Key')).toBeInTheDocument();
  expect(screen.getAllByText('任务路由').length).toBeGreaterThan(0);
  fireEvent.click(screen.getByRole('button', { name: /调用状态/ }));
  expect(screen.getByText('测试连接')).toBeInTheDocument();
});

test('renders dedicated style learning workflow', () => {
  render(<App />);
  fireEvent.click(screen.getByRole('button', { name: /风格学习/ }));
  expect(screen.getByText('导入风格样本')).toBeInTheDocument();
  expect(screen.getByText('AI 分析写作语气')).toBeInTheDocument();
  expect(screen.getByText('模拟写作语气')).toBeInTheDocument();
  expect(screen.getByText('保存风格档案')).toBeInTheDocument();
  expect(screen.getByText('章节生成时可调用')).toBeInTheDocument();
  expect(screen.getByLabelText('风格样本文本')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: /章节编辑器/ }));
  expect(screen.getByLabelText('写作风格档案')).toBeInTheDocument();
});

test('ignores stale style profile loads from a previously selected project', async () => {
  const firstProjectProfiles: GenericRecord[] = [
    {
      id: 'old-style-profile',
      title: '旧项目风格',
      category: 'style',
      content: '旧项目内容',
      status: 'active',
    },
  ];
  const secondProjectProfiles: GenericRecord[] = [
    {
      id: 'current-style-profile',
      title: '当前项目风格',
      category: 'style',
      content: '当前项目内容',
      status: 'active',
    },
  ];
  const staleProfiles = deferred<GenericRecord[]>();

  mockProjectApi();
  vi.mocked(api.listProjects).mockResolvedValue([mockProject, secondProject]);
  vi.mocked(api.listChapters).mockImplementation((projectId) => {
    if (projectId === secondProject.id) return Promise.resolve([secondProjectChapter]);
    return Promise.resolve([mockChapter]);
  });
  vi.mocked(api.listRecords).mockImplementation((projectId, resource) => {
    if (resource === 'style-profiles') {
      if (projectId === mockProject.id) return staleProfiles.promise;
      if (projectId === secondProject.id) return Promise.resolve(secondProjectProfiles);
    }
    return Promise.resolve([]);
  });

  render(<App />);

  await screen.findByRole('button', { name: /第二项目/ });
  fireEvent.click(screen.getByRole('button', { name: /第二项目/ }));

  await screen.findByText('当前项目风格');
  await act(async () => {
    staleProfiles.resolve(firstProjectProfiles);
  });

  await waitFor(() => expect(screen.queryByText('旧项目风格')).not.toBeInTheDocument());
  expect(screen.getByText('当前项目风格')).toBeInTheDocument();
});

test('shows a newly saved style profile in the chapter editor selector', async () => {
  const savedStyleProfile: GenericRecord = {
    id: 'new-style-profile',
    title: '新保存风格',
    category: 'style',
    content: '新保存的风格内容',
    status: 'active',
  };
  let saved = false;

  mockProjectApi();
  vi.mocked(api.listRecords).mockImplementation((projectId, resource) => {
    if (projectId === mockProject.id && resource === 'style-profiles') {
      return Promise.resolve(saved ? [savedStyleProfile] : []);
    }
    return Promise.resolve([]);
  });
  vi.spyOn(api, 'createRecord').mockImplementation(async () => {
    saved = true;
    return savedStyleProfile;
  });

  render(<App />);

  await screen.findByRole('button', { name: /测试项目/ });
  fireEvent.click(screen.getByRole('button', { name: /风格学习/ }));
  fireEvent.change(screen.getByLabelText('风格样本文本'), { target: { value: '用于保存的新风格样本' } });
  fireEvent.click(screen.getByText('保存风格档案'));

  await waitFor(() => expect(api.createRecord).toHaveBeenCalled());
  fireEvent.click(screen.getByRole('button', { name: /章节编辑器/ }));

  const styleSelector = screen.getByLabelText('写作风格档案');
  await waitFor(() => {
    expect(within(styleSelector).getByRole('option', { name: '新保存风格' })).toBeInTheDocument();
  });
});

test('does not reload stale project style profiles after switching projects during save', async () => {
  const currentProjectProfile: GenericRecord = {
    id: 'current-style-profile',
    title: '当前项目风格',
    category: 'style',
    content: '当前项目内容',
    status: 'active',
  };
  const savedStyleProfile: GenericRecord = {
    id: 'saved-old-style-profile',
    title: '旧项目保存完成风格',
    category: 'style',
    content: '旧项目保存完成内容',
    status: 'active',
  };
  const saveStyleProfile = deferred<GenericRecord>();

  mockProjectApi();
  vi.mocked(api.listProjects).mockResolvedValue([mockProject, secondProject]);
  vi.mocked(api.listChapters).mockImplementation((projectId) => {
    if (projectId === secondProject.id) return Promise.resolve([secondProjectChapter]);
    return Promise.resolve([mockChapter]);
  });
  vi.mocked(api.listRecords).mockImplementation((projectId, resource) => {
    if (projectId === secondProject.id && resource === 'style-profiles') {
      return Promise.resolve([currentProjectProfile]);
    }
    return Promise.resolve([]);
  });
  vi.spyOn(api, 'createRecord').mockReturnValue(saveStyleProfile.promise);

  render(<App />);

  await screen.findByRole('button', { name: /测试项目/ });
  fireEvent.click(screen.getByRole('button', { name: /风格学习/ }));
  fireEvent.change(screen.getByLabelText('风格样本文本'), { target: { value: '保存期间切换项目的样本' } });
  fireEvent.click(screen.getByText('保存风格档案'));
  await waitFor(() => expect(api.createRecord).toHaveBeenCalled());

  fireEvent.click(await screen.findByRole('button', { name: /第二项目/ }));
  await screen.findByText('当前项目风格');
  const oldProjectStyleLoadsBeforeSaveResolves = vi
    .mocked(api.listRecords)
    .mock.calls.filter(([projectId, resource]) => projectId === mockProject.id && resource === 'style-profiles').length;

  await act(async () => {
    saveStyleProfile.resolve(savedStyleProfile);
  });

  await waitFor(() => {
    const oldProjectStyleLoadsAfterSaveResolves = vi
      .mocked(api.listRecords)
      .mock.calls.filter(([projectId, resource]) => projectId === mockProject.id && resource === 'style-profiles').length;
    expect(oldProjectStyleLoadsAfterSaveResolves).toBe(oldProjectStyleLoadsBeforeSaveResolves);
  });
  expect(screen.getByText('当前项目风格')).toBeInTheDocument();
});

test('passes only the selected full style profile and lightweight profile list to chapter draft generation', async () => {
  const styleProfiles: GenericRecord[] = [
    {
      id: 'style-profile-1',
      title: '冷峻悬疑风',
      category: 'style',
      content: '短句、克制、低温意象',
      payload: { sentence: 'short' },
      status: 'active',
    },
  ];
  const lightweightStyleProfiles = [{ id: 'style-profile-1', title: '冷峻悬疑风' }];
  mockProjectApi();
  vi.mocked(api.listChapters).mockResolvedValue([mockChapter]);
  vi.mocked(api.listRecords).mockImplementation((projectId, resource) => {
    if (projectId === mockProject.id && resource === 'style-profiles') return Promise.resolve(styleProfiles);
    return Promise.resolve([]);
  });
  const runAi = vi.spyOn(api, 'runAi').mockResolvedValue({
    workflow: 'generate_chapter_draft',
    text: '生成正文',
    score: 0,
    items: [],
  });

  render(<App />);

  await waitFor(() => expect(api.listRecords).toHaveBeenCalledWith(mockProject.id, 'style-profiles'));
  fireEvent.change(screen.getByLabelText('写作风格档案'), { target: { value: 'style-profile-1' } });
  fireEvent.click(screen.getByText('一键生成本章正文'));

  await waitFor(() => expect(runAi).toHaveBeenCalled());
  expect(runAi).toHaveBeenCalledWith(
    mockProject.id,
    'generate_chapter_draft',
    expect.objectContaining({
      style_profile_id: 'style-profile-1',
      style_profile: styleProfiles[0],
      style_profiles: lightweightStyleProfiles,
    }),
  );
  const payload = runAi.mock.calls[0][2] as Record<string, unknown>;
  expect(payload.style_profiles).toEqual(lightweightStyleProfiles);
  expect(payload.style_profiles).not.toEqual(
    expect.arrayContaining([expect.objectContaining({ content: expect.anything() })]),
  );
  expect(payload.style_profiles).not.toEqual(
    expect.arrayContaining([expect.objectContaining({ payload: expect.anything() })]),
  );
});

test('clears invalid selected style profile ids before chapter draft generation', async () => {
  const styleProfiles: GenericRecord[] = [
    {
      id: 'style-profile-1',
      title: '冷峻悬疑风',
      category: 'style',
      content: '短句、克制、低温意象',
      payload: { sentence: 'short' },
      status: 'active',
    },
  ];
  let styleProfileLoadCount = 0;

  mockProjectApi();
  vi.mocked(api.listChapters).mockResolvedValue([mockChapter]);
  vi.mocked(api.listRecords).mockImplementation((projectId, resource) => {
    if (projectId === mockProject.id && resource === 'style-profiles') {
      styleProfileLoadCount += 1;
      return Promise.resolve(styleProfileLoadCount === 1 ? styleProfiles : []);
    }
    return Promise.resolve([]);
  });
  vi.spyOn(api, 'createRecord').mockResolvedValue({
    id: 'new-style-profile',
    title: '刷新用风格',
    category: 'style',
    content: '',
    status: 'active',
  });
  const runAi = vi.spyOn(api, 'runAi').mockResolvedValue({
    workflow: 'generate_chapter_draft',
    text: '生成正文',
    score: 0,
    items: [],
  });

  render(<App />);

  await screen.findByText('冷峻悬疑风');
  fireEvent.change(screen.getByLabelText('写作风格档案'), { target: { value: 'style-profile-1' } });
  fireEvent.click(screen.getByRole('button', { name: /风格学习/ }));
  fireEvent.change(screen.getByLabelText('风格样本文本'), { target: { value: '用于触发保存刷新' } });
  fireEvent.click(screen.getByText('保存风格档案'));
  await waitFor(() => expect(api.createRecord).toHaveBeenCalled());
  fireEvent.click(screen.getByRole('button', { name: /章节编辑器/ }));
  await waitFor(() => expect(screen.queryByText('冷峻悬疑风')).not.toBeInTheDocument());

  fireEvent.click(screen.getByText('一键生成本章正文'));

  await waitFor(() => expect(runAi).toHaveBeenCalled());
  expect(runAi).toHaveBeenCalledWith(
    mockProject.id,
    'generate_chapter_draft',
    expect.objectContaining({
      style_profile_id: '',
      style_profile: null,
      style_profiles: [],
    }),
  );
});

test('renders dedicated character workbench from story bible', () => {
  render(<App />);
  fireEvent.click(screen.getByRole('button', { name: /故事圣经/ }));
  expect(screen.getByText('角色工作台')).toBeInTheDocument();
  expect(screen.getByLabelText('姓名')).toBeInTheDocument();
  expect(screen.getByLabelText('欲望目标')).toBeInTheDocument();
  expect(screen.getByText('AI 生成新角色')).toBeInTheDocument();
  expect(screen.getByText('AI 补全角色')).toBeInTheDocument();
  expect(screen.getByText('生成角色对白')).toBeInTheDocument();
});

test('hides the generic record form in the character story bible tab', () => {
  render(<App />);
  fireEvent.click(screen.getByRole('button', { name: /故事圣经/ }));
  expect(screen.queryByText('写入资料')).not.toBeInTheDocument();
});

test('renders dedicated outline workbench', () => {
  render(<App />);
  fireEvent.click(within(screen.getByRole('navigation')).getByRole('button', { name: /大纲/ }));
  expect(screen.getByText('大纲工作台')).toBeInTheDocument();
  expect(screen.getByLabelText('本章目标')).toBeInTheDocument();
  expect(screen.getByLabelText('主要冲突')).toBeInTheDocument();
  expect(screen.getByText('生成 10 章大纲')).toBeInTheDocument();
  expect(screen.getByText('扩展本章梗概')).toBeInTheDocument();
});

test('hides the generic record form in the outline tab', () => {
  render(<App />);
  fireEvent.click(within(screen.getByRole('navigation')).getByRole('button', { name: /大纲/ }));
  expect(screen.queryByText('写入资料')).not.toBeInTheDocument();
});

test('renders dedicated relationship graph workbench', async () => {
  mockProjectApi();

  render(<App />);
  fireEvent.click(screen.getByRole('button', { name: /角色关系图/ }));
  await waitFor(() => expect(api.listChapters).toHaveBeenCalledWith(mockProject.id));

  expect(screen.getByText('关系图工作台')).toBeInTheDocument();
  expect(screen.getByText('新增角色')).toBeInTheDocument();
  expect(screen.getAllByText('新增关系').length).toBeGreaterThan(0);
  expect(screen.getAllByText('AI 提取关系').length).toBeGreaterThan(0);
  expect(screen.getByLabelText('关系类型')).toBeInTheDocument();
  expect(screen.getByLabelText('关系强度')).toBeInTheDocument();
});

test('ignores stale project graph reloads after switching projects', async () => {
  const currentRelationships: GenericRecord[] = [
    {
      id: 'current-relationship',
      title: '当前项目关系',
      category: '同盟',
      content: '这是当前项目的关系',
      payload: {
        source_character: '当前主角',
        target_character: '当前盟友',
        relationship_type: '同盟',
      },
      status: 'active',
    },
  ];
  const currentCharacters: GenericRecord[] = [
    {
      id: 'current-character',
      title: '当前主角',
      category: 'character',
      content: '当前项目角色',
      payload: { name: '当前主角' },
      status: 'active',
    },
  ];
  const staleRelationships: GenericRecord[] = [
    {
      id: 'stale-relationship',
      title: '旧项目关系',
      category: '敌人',
      content: '这是旧项目的关系',
      payload: {
        source_character: '旧项目主角',
        target_character: '旧项目敌人',
        relationship_type: '敌人',
      },
      status: 'active',
    },
  ];
  const staleCharacters: GenericRecord[] = [
    {
      id: 'stale-character',
      title: '旧项目主角',
      category: 'character',
      content: '旧项目角色',
      payload: { name: '旧项目主角' },
      status: 'active',
    },
  ];
  const savedRelationship = deferred<GenericRecord>();

  mockProjectApi();
  vi.mocked(api.listProjects).mockResolvedValue([mockProject, secondProject]);
  vi.mocked(api.listChapters).mockImplementation((projectId) => {
    if (projectId === secondProject.id) return Promise.resolve([secondProjectChapter]);
    return Promise.resolve([mockChapter]);
  });
  vi.mocked(api.listRecords).mockImplementation((projectId, resource) => {
    if (projectId === secondProject.id && resource === 'character-relationships') {
      return Promise.resolve(currentRelationships);
    }
    if (projectId === secondProject.id && resource === 'character-profiles') {
      return Promise.resolve(currentCharacters);
    }
    if (projectId === mockProject.id && resource === 'character-relationships') {
      return Promise.resolve(staleRelationships);
    }
    if (projectId === mockProject.id && resource === 'character-profiles') {
      return Promise.resolve(staleCharacters);
    }
    return Promise.resolve([]);
  });
  vi.spyOn(api, 'createRecord').mockReturnValue(savedRelationship.promise);

  render(<App />);
  fireEvent.click(screen.getByRole('button', { name: /角色关系图/ }));
  await screen.findByText('旧项目关系');

  fireEvent.click(screen.getByRole('button', { name: /新增关系/ }));
  await waitFor(() => expect(api.createRecord).toHaveBeenCalledWith(
    mockProject.id,
    'character-relationships',
    expect.any(Object),
  ));

  fireEvent.click(await screen.findByRole('button', { name: /第二项目/ }));
  expect(await screen.findByText('当前项目关系')).toBeInTheDocument();
  expect(screen.queryByText('旧项目关系')).not.toBeInTheDocument();

  await act(async () => {
    savedRelationship.resolve({
      id: 'saved-stale-relationship',
      title: '保存完成的旧项目关系',
      category: '敌人',
      content: '旧项目保存完成',
      status: 'active',
    });
  });

  await waitFor(() => expect(screen.queryByText('旧项目关系')).not.toBeInTheDocument());
  expect(screen.getByText('当前项目关系')).toBeInTheDocument();
});

test('renders relationship graph workbench when relationships exist without characters', async () => {
  mockProjectApi();
  vi.mocked(api.listRecords).mockImplementation((projectId, resource) => {
    if (projectId === mockProject.id && resource === 'character-relationships') {
      return Promise.resolve([
        {
          id: 'relationship-without-characters',
          title: '孤立关系',
          category: '同盟',
          content: '角色档案尚未创建',
          payload: {
            source_character: '未建档角色 A',
            target_character: '未建档角色 B',
            relationship_type: '同盟',
          },
          status: 'active',
        },
      ]);
    }
    if (projectId === mockProject.id && resource === 'character-profiles') return Promise.resolve([]);
    return Promise.resolve([]);
  });

  render(<App />);
  fireEvent.click(screen.getByRole('button', { name: /角色关系图/ }));

  expect(await screen.findByText('关系图工作台')).toBeInTheDocument();
  expect(await screen.findByText('孤立关系')).toBeInTheDocument();
  expect(screen.getByText('角色 0 个，关系 1 条')).toBeInTheDocument();
});

test('saves a relationship record with structured payload fields', async () => {
  mockProjectApi();
  const createRecord = vi.spyOn(api, 'createRecord').mockResolvedValue({
    id: 'relationship-1',
    title: '沈照夜 → 谢无咎',
    category: '敌人',
    content: '彼此试探',
    status: 'active',
  });

  render(<App />);
  fireEvent.click(screen.getByRole('button', { name: /角色关系图/ }));
  await waitFor(() => expect(api.listChapters).toHaveBeenCalledWith(mockProject.id));

  fireEvent.change(screen.getByLabelText('来源角色'), { target: { value: '沈照夜' } });
  fireEvent.change(screen.getByLabelText('目标角色'), { target: { value: '谢无咎' } });
  fireEvent.change(screen.getByLabelText('关系类型'), { target: { value: '敌人' } });
  fireEvent.change(screen.getByLabelText('关系强度'), { target: { value: '72' } });
  fireEvent.change(screen.getByLabelText('冲突说明'), { target: { value: '彼此试探' } });
  fireEvent.click(screen.getByRole('button', { name: /新增关系/ }));

  await waitFor(() => expect(createRecord).toHaveBeenCalled());
  expect(createRecord).toHaveBeenCalledWith(
    mockProject.id,
    'character-relationships',
    expect.objectContaining({
      title: '沈照夜 → 谢无咎',
      category: '敌人',
      content: '彼此试探',
      payload: expect.objectContaining({
        source_character: '沈照夜',
        target_character: '谢无咎',
        relationship_type: '敌人',
        strength: 72,
        conflict: '彼此试探',
      }),
      status: 'active',
    }),
  );
});

test('creates a character profile from the relationship graph workbench', async () => {
  mockProjectApi();
  const createRecord = vi.spyOn(api, 'createRecord').mockResolvedValue({
    id: 'character-1',
    title: '新角色',
    category: 'character',
    content: '请在角色工作台完善这个角色。',
    status: 'draft',
  });

  render(<App />);
  fireEvent.click(screen.getByRole('button', { name: /角色关系图/ }));
  await waitFor(() => expect(api.listChapters).toHaveBeenCalledWith(mockProject.id));

  fireEvent.click(screen.getByRole('button', { name: /新增角色/ }));

  await waitFor(() => expect(createRecord).toHaveBeenCalled());
  expect(createRecord).toHaveBeenCalledWith(
    mockProject.id,
    'character-profiles',
    expect.objectContaining({
      title: '新角色',
      category: 'character',
      content: '请在角色工作台完善这个角色。',
      status: 'draft',
    }),
  );
});

test('keeps stale shared records from overwriting the current tab after fast tab switches', async () => {
  mockProjectApi();
  const characterRecords: GenericRecord[] = [
    {
      id: 'character-1',
      title: '旧角色记录',
      category: 'character',
      content: '不应出现在大纲页',
      status: 'active',
    },
  ];
  const outlineRecords: GenericRecord[] = [
    {
      id: 'outline-1',
      title: '当前大纲记录',
      category: 'outline',
      content: '大纲页应该显示这条记录',
      status: 'draft',
    },
  ];
  const characters = deferred<GenericRecord[]>();
  const outlines = deferred<GenericRecord[]>();
  vi.mocked(api.listRecords).mockImplementation((projectId, resource) => {
    if (projectId === mockProject.id && resource === 'character-profiles') return characters.promise;
    if (projectId === mockProject.id && resource === 'outlines') return outlines.promise;
    return Promise.resolve([]);
  });

  render(<App />);
  await waitFor(() => expect(api.listChapters).toHaveBeenCalledWith(mockProject.id));

  fireEvent.click(screen.getByRole('button', { name: /故事圣经/ }));
  await waitFor(() => expect(api.listRecords).toHaveBeenCalledWith(mockProject.id, 'character-profiles'));
  fireEvent.click(within(screen.getByRole('navigation')).getByRole('button', { name: /大纲/ }));
  await waitFor(() => expect(api.listRecords).toHaveBeenCalledWith(mockProject.id, 'outlines'));

  await act(async () => {
    characters.resolve(characterRecords);
  });
  expect(screen.queryByText('旧角色记录')).not.toBeInTheDocument();

  await act(async () => {
    outlines.resolve(outlineRecords);
  });
  expect(await screen.findByText('当前大纲记录')).toBeInTheDocument();
  expect(screen.queryByText('旧角色记录')).not.toBeInTheDocument();
});

test('saves an outline chapter board with structured payload fields', async () => {
  mockProjectApi();
  const createRecord = vi.spyOn(api, 'createRecord').mockResolvedValue({
    id: 'outline-1',
    title: '第一章 归京',
    category: 'chapter_outline',
    content: '夺回线索',
    status: 'draft',
  });

  render(<App />);
  fireEvent.click(within(screen.getByRole('navigation')).getByRole('button', { name: /大纲/ }));
  await waitFor(() => expect(api.listChapters).toHaveBeenCalledWith(mockProject.id));

  fireEvent.change(screen.getByLabelText('章节标题'), { target: { value: '第一章 归京' } });
  fireEvent.change(screen.getByLabelText('本章目标'), { target: { value: '夺回线索' } });
  fireEvent.change(screen.getByLabelText('主要冲突'), { target: { value: '旧臣拒绝承认她' } });
  fireEvent.change(screen.getByLabelText('关键事件'), { target: { value: '夜访宗庙，发现记忆裂痕' } });
  fireEvent.click(screen.getByText('保存大纲'));

  await waitFor(() => expect(createRecord).toHaveBeenCalled());
  expect(createRecord).toHaveBeenCalledWith(
    mockProject.id,
    'outlines',
    expect.objectContaining({
      category: 'chapter_outline',
      payload: expect.objectContaining({
        chapter_title: '第一章 归京',
        chapter_goal: '夺回线索',
        main_conflict: '旧臣拒绝承认她',
        key_events: '夜访宗庙，发现记忆裂痕',
        scope: 'chapter',
      }),
    }),
  );
});

test('saving an edited chapter title syncs the chapter outline record', async () => {
  mockProjectApi();
  vi.mocked(api.listChapters).mockResolvedValue([mockChapter]);
  vi.mocked(api.listRecords).mockImplementation((projectId, resource) => {
    if (projectId === mockProject.id && resource === 'outlines') {
      return Promise.resolve([
        {
          id: 'outline-1',
          title: '第一章',
          category: 'chapter_outline',
          content: '她发现古籍',
          status: 'draft',
          payload: {
            chapter_id: mockChapter.id,
            chapter_number: '1',
            chapter_title: '第一章',
            chapter_goal: '她发现古籍',
          },
        },
      ]);
    }
    return Promise.resolve([]);
  });
  const updateChapter = vi.spyOn(api, 'updateChapter').mockResolvedValue({
    ...mockChapter,
    title: '第一章 旧书夜市',
  });
  const updateRecord = vi.spyOn(api, 'updateRecord').mockResolvedValue({
    id: 'outline-1',
    title: '第一章 旧书夜市',
    category: 'chapter_outline',
    content: '她发现古籍',
    status: 'draft',
  });

  render(<App />);
  const titleInput = await screen.findByDisplayValue('第一章');
  fireEvent.change(titleInput, { target: { value: '第一章 旧书夜市' } });
  fireEvent.click(screen.getAllByRole('button', { name: '保存' })[0]);

  await waitFor(() => expect(updateChapter).toHaveBeenCalled());
  await waitFor(() => expect(updateRecord).toHaveBeenCalled());
  expect(updateRecord).toHaveBeenCalledWith(
    mockProject.id,
    'outlines',
    'outline-1',
    expect.objectContaining({
      title: '第一章 旧书夜市',
      category: 'chapter_outline',
      payload: expect.objectContaining({
        chapter_id: mockChapter.id,
        chapter_title: '第一章 旧书夜市',
      }),
    }),
  );
});

test('saves a character card with structured payload fields', async () => {
  mockProjectApi();
  const createRecord = vi.spyOn(api, 'createRecord').mockResolvedValue({
    id: 'character-1',
    title: '沈照夜',
    category: 'character',
    content: '沈照夜',
    status: 'active',
  });

  render(<App />);
  fireEvent.click(screen.getByRole('button', { name: /故事圣经/ }));
  await waitFor(() => expect(api.listChapters).toHaveBeenCalledWith(mockProject.id));

  fireEvent.change(screen.getByLabelText('姓名'), { target: { value: '沈照夜' } });
  fireEvent.change(screen.getByLabelText('身份'), { target: { value: '流亡公主' } });
  fireEvent.change(screen.getByLabelText('欲望目标'), { target: { value: '夺回被篡改的记忆' } });
  fireEvent.change(screen.getByLabelText('口癖 / 说话方式'), { target: { value: '克制，少用疑问句' } });
  fireEvent.change(screen.getByLabelText('备注'), { target: { value: '不信任宫廷术士' } });
  fireEvent.click(screen.getByText('保存角色卡'));

  await waitFor(() => expect(createRecord).toHaveBeenCalled());
  expect(createRecord).toHaveBeenCalledWith(
    mockProject.id,
    'character-profiles',
    expect.objectContaining({
      category: 'character',
      payload: expect.objectContaining({
        name: '沈照夜',
        role: '流亡公主',
        desire: '夺回被篡改的记忆',
        voice: '克制，少用疑问句',
        notes: '不信任宫廷术士',
      }),
    }),
  );
});

test('edits an existing character card and updates llmwiki-backed record instead of creating a duplicate', async () => {
  const characterRecord: GenericRecord = {
    id: 'character-1',
    title: '沈照夜',
    category: 'character',
    content: '前朝公主',
    payload: {
      name: '沈照夜',
      role: '前朝公主',
      faction: '流亡旧臣',
      appearance: '素色斗篷',
      traits: '冷静',
      desire: '夺回记忆',
      fear: '遗忘旧友',
      mainline_relation: '',
      arc: '承担代价',
      voice: '短句克制',
      related_chapters: '第一章',
      notes: '旧版备注',
    },
    status: 'active',
  };

  mockProjectApi();
  vi.mocked(api.listRecords).mockImplementation((projectId, resource) => {
    if (projectId === mockProject.id && resource === 'character-profiles') return Promise.resolve([characterRecord]);
    return Promise.resolve([]);
  });
  const createRecord = vi.spyOn(api, 'createRecord').mockResolvedValue({
    id: 'created-record',
    title: 'created',
    category: 'created',
    content: '',
    status: 'active',
  });
  const updateRecord = vi.spyOn(api, 'updateRecord').mockResolvedValue({
    ...characterRecord,
    payload: { ...characterRecord.payload, notes: '新版备注' },
  });

  render(<App />);
  fireEvent.click(screen.getByRole('button', { name: /故事圣经/ }));
  await screen.findByRole('button', { name: /编辑角色 沈照夜/ });
  fireEvent.click(screen.getByRole('button', { name: /编辑角色 沈照夜/ }));
  fireEvent.change(screen.getByLabelText('备注'), { target: { value: '新版备注' } });
  fireEvent.click(screen.getByText('更新角色卡并同步 llmwiki'));

  await waitFor(() => expect(updateRecord).toHaveBeenCalled());
  expect(updateRecord).toHaveBeenCalledWith(
    mockProject.id,
    'character-profiles',
    'character-1',
    expect.objectContaining({
      payload: expect.objectContaining({ notes: '新版备注' }),
    }),
  );
  expect(createRecord).not.toHaveBeenCalledWith(mockProject.id, 'character-profiles', expect.any(Object));
});

test('saving a character card also creates a relationship graph record from mainline relation', async () => {
  mockProjectApi();
  const createRecord = vi.spyOn(api, 'createRecord').mockImplementation(async (_projectId, resource, payload) => ({
    id: `${resource}-1`,
    title: String(payload.title ?? ''),
    category: String(payload.category ?? ''),
    content: String(payload.content ?? ''),
    payload: payload.payload,
    status: String(payload.status ?? 'active'),
  }));

  render(<App />);
  fireEvent.click(screen.getByRole('button', { name: /故事圣经/ }));
  await waitFor(() => expect(api.listChapters).toHaveBeenCalledWith(mockProject.id));

  fireEvent.change(screen.getByLabelText('姓名'), { target: { value: '沈砚' } });
  fireEvent.change(screen.getByLabelText('身份'), { target: { value: '旧案刑侦顾问' } });
  fireEvent.change(screen.getByLabelText('与主线关系'), { target: { value: '三年前误判旧案，正在追查真相' } });
  fireEvent.change(screen.getByLabelText('相关章节'), { target: { value: '第一章' } });
  fireEvent.click(screen.getByText('保存角色卡'));

  await waitFor(() => expect(createRecord).toHaveBeenCalledWith(mockProject.id, 'character-profiles', expect.any(Object)));
  expect(createRecord).toHaveBeenCalledWith(
    mockProject.id,
    'character-relationships',
    expect.objectContaining({
      title: '沈砚 → 主线剧情',
      category: '主线关联',
      content: '三年前误判旧案，正在追查真相',
      payload: expect.objectContaining({
        source_character: '沈砚',
        target_character: '主线剧情',
        relationship_type: '主线关联',
        conflict: '三年前误判旧案，正在追查真相',
        related_chapters: '第一章',
      }),
      status: 'active',
    }),
  );
});

test('edits an existing relationship and updates the llmwiki-backed relationship record', async () => {
  const relationshipRecord: GenericRecord = {
    id: 'relationship-1',
    title: '沈照夜 → 主线剧情',
    category: '主线关联',
    content: '旧版关系说明',
    payload: {
      source_character: '沈照夜',
      target_character: '主线剧情',
      relationship_type: '主线关联',
      strength: 70,
      conflict: '旧版关系说明',
      change_history: '旧版变化记录',
      related_chapters: '第一章',
    },
    status: 'active',
  };

  mockProjectApi();
  vi.mocked(api.listRecords).mockImplementation((projectId, resource) => {
    if (projectId !== mockProject.id) return Promise.resolve([]);
    if (resource === 'character-relationships') return Promise.resolve([relationshipRecord]);
    if (resource === 'character-profiles') {
      return Promise.resolve([
        {
          id: 'character-1',
          title: '沈照夜',
          category: 'character',
          content: '前朝公主',
          payload: { name: '沈照夜' },
          status: 'active',
        },
      ]);
    }
    return Promise.resolve([]);
  });
  const createRecord = vi.spyOn(api, 'createRecord').mockResolvedValue({
    id: 'created-record',
    title: 'created',
    category: 'created',
    content: '',
    status: 'active',
  });
  const updateRecord = vi.spyOn(api, 'updateRecord').mockResolvedValue({
    ...relationshipRecord,
    content: '新版关系说明',
  });

  render(<App />);
  fireEvent.click(screen.getByRole('button', { name: /角色关系图/ }));
  await screen.findByRole('button', { name: /编辑关系 沈照夜 → 主线剧情/ });
  fireEvent.click(screen.getByRole('button', { name: /编辑关系 沈照夜 → 主线剧情/ }));
  fireEvent.change(screen.getByLabelText('冲突说明'), { target: { value: '新版关系说明' } });
  fireEvent.click(screen.getByText('更新关系并同步 llmwiki'));

  await waitFor(() => expect(updateRecord).toHaveBeenCalled());
  expect(updateRecord).toHaveBeenCalledWith(
    mockProject.id,
    'character-relationships',
    'relationship-1',
    expect.objectContaining({
      content: '新版关系说明',
      payload: expect.objectContaining({ conflict: '新版关系说明' }),
    }),
  );
  expect(createRecord).not.toHaveBeenCalledWith(mockProject.id, 'character-relationships', expect.any(Object));
});

test('shows an explicit character save error when relationship sync fails', async () => {
  mockProjectApi();
  vi.spyOn(api, 'createRecord')
    .mockResolvedValueOnce({
      id: 'character-1',
      title: '沈砚',
      category: 'character',
      content: '角色已保存',
      status: 'active',
    })
    .mockRejectedValueOnce(new Error('{"detail":"Unknown resource"}'));

  render(<App />);
  fireEvent.click(screen.getByRole('button', { name: /故事圣经/ }));
  await waitFor(() => expect(api.listChapters).toHaveBeenCalledWith(mockProject.id));

  fireEvent.change(screen.getByLabelText('姓名'), { target: { value: '沈砚' } });
  fireEvent.change(screen.getByLabelText('与主线关系'), { target: { value: '追查旧案真相' } });
  fireEvent.click(screen.getByText('保存角色卡'));

  expect((await screen.findAllByText(/保存失败/)).length).toBeGreaterThan(0);
  expect(screen.getAllByText(/Unknown resource/).length).toBeGreaterThan(0);
});

test('applies AI character completion result to the current form notes', async () => {
  mockProjectApi();
  vi.spyOn(api, 'runAi').mockResolvedValue({
    workflow: 'generate_characters',
    text: 'AI 建议：她会用旧朝暗语试探盟友。',
    score: 0,
    items: [],
  });

  render(<App />);
  fireEvent.click(screen.getByRole('button', { name: /故事圣经/ }));
  await waitFor(() => expect(api.listChapters).toHaveBeenCalledWith(mockProject.id));

  fireEvent.click(screen.getByText('AI 补全角色'));
  await screen.findByLabelText('角色生成结果 结果内容');
  fireEvent.click(screen.getByText('应用到当前表单'));

  expect(screen.getByLabelText('备注')).toHaveValue('AI 建议：她会用旧朝暗语试探盟友。');
});

test('applies JSON character array results into the editable character card fields', async () => {
  mockProjectApi();
  vi.spyOn(api, 'runAi').mockResolvedValue({
    workflow: 'generate_characters',
    text: JSON.stringify({
      characters: [
        {
          name: '沈照夜',
          role: '前朝公主',
          faction: '流亡旧臣',
          appearance: '素色斗篷，左腕有旧朝玉镯',
          traits: '冷静、警惕、善于试探',
          desire: '夺回被篡改的记忆',
          fear: '忘记最重要的人',
          mainline_relation: '她是记忆古籍的当前持有者',
          arc: '从只想自保到主动承担改写记忆的代价',
          voice: '短句克制，很少直接求助',
          related_chapters: '第一章、第二章',
          notes: 'JSON 结果应拆字段填入角色卡。',
        },
      ],
    }),
    score: 0,
    items: [],
  });

  render(<App />);
  fireEvent.click(screen.getByRole('button', { name: /故事圣经/ }));
  await waitFor(() => expect(api.listChapters).toHaveBeenCalledWith(mockProject.id));

  fireEvent.click(screen.getByText('AI 补全角色'));
  await screen.findByLabelText('角色生成结果 结果内容');
  fireEvent.click(screen.getByText('应用到当前表单'));

  await waitFor(() => expect(screen.getByLabelText('姓名')).toHaveValue('沈照夜'));
  expect(screen.getByLabelText('身份')).toHaveValue('前朝公主');
  expect(screen.getByLabelText('阵营')).toHaveValue('流亡旧臣');
  expect(screen.getByLabelText('欲望目标')).toHaveValue('夺回被篡改的记忆');
  expect(screen.getByLabelText('口癖 / 说话方式')).toHaveValue('短句克制，很少直接求助');
  expect(screen.getByLabelText('备注')).toHaveValue('JSON 结果应拆字段填入角色卡。');
});

test('fills the character card from structured AI character JSON', async () => {
  mockProjectApi();
  vi.spyOn(api, 'runAi').mockResolvedValue({
    workflow: 'generate_characters',
    text: '{"name":"沈照夜"}',
    structured: {
      name: '沈照夜',
      role: '前朝公主',
      faction: '流亡旧臣',
      appearance: '素色斗篷',
      traits: '冷静、警惕',
      desire: '夺回记忆',
      fear: '遗忘旧友',
      mainline_relation: '古籍主线',
      arc: '从流亡到承担代价',
      voice: '短句克制',
      related_chapters: '第一章',
      notes: 'AI 自动填表',
    },
    score: 0,
    items: [],
  });

  render(<App />);
  fireEvent.click(screen.getByRole('button', { name: /故事圣经/ }));
  await waitFor(() => expect(api.listChapters).toHaveBeenCalledWith(mockProject.id));

  fireEvent.click(screen.getByText('AI 生成新角色'));

  await waitFor(() => expect(screen.getByLabelText('姓名')).toHaveValue('沈照夜'));
  expect(screen.getByLabelText('身份')).toHaveValue('前朝公主');
  expect(screen.getByLabelText('欲望目标')).toHaveValue('夺回记忆');
  expect(screen.getByLabelText('口癖 / 说话方式')).toHaveValue('短句克制');
});

test('passes existing character names when generating a new character to avoid duplicates', async () => {
  const existingCharacters: GenericRecord[] = [
    {
      id: 'character-1',
      title: '沈照夜',
      category: 'character',
      content: '前朝公主',
      payload: { name: '沈照夜' },
      status: 'active',
    },
  ];
  mockProjectApi();
  vi.mocked(api.listRecords).mockImplementation((projectId, resource) => {
    if (projectId === mockProject.id && resource === 'character-profiles') return Promise.resolve(existingCharacters);
    return Promise.resolve([]);
  });
  const runAi = vi.spyOn(api, 'runAi').mockResolvedValue({
    workflow: 'generate_characters',
    text: '{"name":"顾临舟"}',
    structured: { name: '顾临舟', role: '旧朝密探' },
    score: 0,
    items: [],
  });

  render(<App />);
  fireEvent.click(screen.getByRole('button', { name: /故事圣经/ }));
  await screen.findByText('沈照夜');
  fireEvent.click(screen.getByText('AI 生成新角色'));

  await waitFor(() => expect(runAi).toHaveBeenCalled());
  expect(runAi).toHaveBeenCalledWith(
    mockProject.id,
    'generate_characters',
    expect.objectContaining({
      existing_character_names: ['沈照夜'],
      generation_contract: expect.objectContaining({
        avoid_duplicate_names: true,
      }),
    }),
  );
});

test('applies AI outline generation result to the current form key events', async () => {
  mockProjectApi();
  vi.spyOn(api, 'runAi').mockResolvedValue({
    workflow: 'generate_chapter_brief',
    text: 'AI 大纲建议：宗庙密谈后，她发现记忆裂痕来自旧盟友。',
    score: 0,
    items: [],
  });

  render(<App />);
  fireEvent.click(within(screen.getByRole('navigation')).getByRole('button', { name: /大纲/ }));
  await waitFor(() => expect(api.listChapters).toHaveBeenCalledWith(mockProject.id));

  fireEvent.click(screen.getByText('扩展本章梗概'));
  await screen.findByLabelText('大纲生成结果 结果内容');
  fireEvent.click(screen.getByText('应用到当前表单'));

  expect(screen.getByLabelText('关键事件')).toHaveValue('AI 大纲建议：宗庙密谈后，她发现记忆裂痕来自旧盟友。');
});

test('splits multi-chapter AI outline JSON into chapter candidate cards', async () => {
  mockProjectApi();
  vi.spyOn(api, 'runAi').mockResolvedValue({
    workflow: 'generate_outline',
    text: JSON.stringify({
      global_outline: {
        chapter_title: '全书总纲 / 主线轨道',
        chapter_goal: '围绕旧书馆和记忆代价推进主线',
      },
      chapter_outlines: [
        {
          chapter_number: 1,
          chapter_title: '旧书夜市',
          chapter_goal: '发现无题古籍',
        },
        {
          chapter_number: 2,
          chapter_title: '缺失的三分钟',
          chapter_goal: '确认交易已经生效',
        },
      ],
    }),
    score: 0,
    items: [],
  });

  render(<App />);
  fireEvent.click(within(screen.getByRole('navigation')).getByRole('button', { name: /大纲/ }));
  await waitFor(() => expect(api.listChapters).toHaveBeenCalledWith(mockProject.id));

  fireEvent.click(screen.getByText('生成 5 章大纲'));

  expect(await screen.findByText('第 1 章 · 旧书夜市')).toBeInTheDocument();
  expect(await screen.findByText('第 2 章 · 缺失的三分钟')).toBeInTheDocument();
  expect(screen.getByLabelText('第 1 章 · 旧书夜市 结果内容')).toHaveTextContent('"chapter_title": "第 1 章 · 旧书夜市"');
  expect(screen.getByLabelText('第 2 章 · 缺失的三分钟 结果内容')).toHaveTextContent('"chapter_title": "第 2 章 · 缺失的三分钟"');
  expect(screen.getAllByText('保存为独立章节大纲')).toHaveLength(2);
  expect(screen.queryByLabelText('大纲生成结果 结果内容')).not.toBeInTheDocument();
});

test('sends chapter title and llmwiki duplicate-avoidance rules when generating an outline', async () => {
  mockProjectApi();
  vi.mocked(api.listChapters).mockResolvedValue([mockChapter]);
  const runAi = vi.spyOn(api, 'runAi').mockResolvedValue({
    workflow: 'generate_chapter_brief',
    text: '{"chapter_title":"第一章","key_events":"不重复的新事件"}',
    score: 0,
    items: [],
  });

  render(<App />);
  fireEvent.click(within(screen.getByRole('navigation')).getByRole('button', { name: /大纲/ }));
  await waitFor(() => expect(screen.getByText(/章节大纲：0 \/ 章节：1/)).toBeInTheDocument());

  fireEvent.click(screen.getByText('扩展本章梗概'));

  await waitFor(() => expect(runAi).toHaveBeenCalled());
  expect(runAi).toHaveBeenCalledWith(
    mockProject.id,
    'generate_chapter_brief',
    expect.objectContaining({
      chapter_id: mockChapter.id,
      selected_chapter: expect.objectContaining({ title: '第一章' }),
      generation_contract: expect.objectContaining({
        use_llmwiki: true,
        avoid_duplicate_events: true,
        focus_chapter_title: '第一章',
        instruction: expect.stringContaining('第一章'),
      }),
    }),
  );
});

test('deletes a selected chapter outline and reloads the outline list', async () => {
  const outlineRecord: GenericRecord = {
    id: 'outline-1',
    title: '第一章大纲',
    category: 'chapter_outline',
    content: '发现古籍',
    status: 'draft',
  };
  mockProjectApi();
  vi.mocked(api.listRecords).mockImplementation((_projectId, resource) =>
    Promise.resolve(resource === 'outlines' ? [outlineRecord] : []),
  );

  render(<App />);
  fireEvent.click(within(screen.getByRole('navigation')).getByRole('button', { name: /大纲/ }));
  const selector = await screen.findByLabelText('选择章节大纲');
  await screen.findByText('第一章大纲');
  fireEvent.change(selector, { target: { value: 'outline-1' } });

  fireEvent.click(screen.getByRole('button', { name: /删除章节大纲/ }));

  await waitFor(() =>
    expect(api.deleteRecord).toHaveBeenCalledWith(mockProject.id, 'outlines', 'outline-1'),
  );
  expect(api.listRecords).toHaveBeenCalledWith(mockProject.id, 'outlines');
});

test('lets backend build llmwiki context for chapter draft generation', async () => {
  mockProjectApi();
  vi.mocked(api.listChapters).mockResolvedValue([mockChapter]);
  vi.mocked(api.listRecords).mockImplementation((projectId, resource) => {
    if (projectId !== mockProject.id) return Promise.resolve([]);
    const recordsByResource: Record<string, GenericRecord[]> = {
      'character-profiles': [{ id: 'char-1', title: '沈照夜', category: 'character', content: '主角', status: 'active' }],
      'character-relationships': [{ id: 'rel-1', title: '沈照夜 -> 谢无咎', category: '同盟', content: '暂时合作', status: 'active' }],
      outlines: [{ id: 'outline-1', title: '第一章大纲', category: 'chapter_outline', content: '发现古籍', status: 'draft' }],
      'timeline-events': [{ id: 'time-1', title: '发现古籍', category: 'event', content: '雨夜发现', status: 'active' }],
      foreshadowings: [{ id: 'foreshadow-1', title: '古籍代价', category: 'open', content: '吞噬记忆', status: 'open' }],
      'taboo-rules': [{ id: 'taboo-1', title: '避免无意义虐主', category: 'high', content: '不能无代价折磨主角', status: 'active' }],
      'knowledge-documents': [{ id: 'knowledge-1', title: '朝代资料', category: 'source', content: '旧朝礼制', status: 'active' }],
      'style-profiles': [],
    };
    return Promise.resolve(recordsByResource[resource] ?? []);
  });
  vi.spyOn(api, 'wikiSearch').mockResolvedValue([{ path: 'global-summary.md', content: '前文摘要' }]);
  const runAi = vi.spyOn(api, 'runAi').mockResolvedValue({
    workflow: 'generate_chapter_draft',
    text: '正文',
    score: 0,
    items: [],
  });

  render(<App />);
  await screen.findByDisplayValue('第一章');
  fireEvent.click(screen.getByText('一键生成本章正文'));

  await waitFor(() => expect(runAi).toHaveBeenCalled());
  expect(runAi).toHaveBeenCalledWith(
    mockProject.id,
    'generate_chapter_draft',
    expect.objectContaining({
      chapter_number: 1,
      generation_contract: expect.objectContaining({
        output: 'single_chapter_prose',
        use_llmwiki: true,
        avoid_multiple_drafts: true,
      }),
    }),
  );
  expect(runAi.mock.calls[0][2]).not.toHaveProperty('generation_context');
});

test('shows local fallback as an error instead of generated chapter prose', async () => {
  mockProjectApi();
  vi.mocked(api.listChapters).mockResolvedValue([mockChapter]);
  vi.spyOn(api, 'runAi').mockResolvedValue({
    workflow: 'generate_chapter_draft',
    text: '## 章节正文\n\n这是本地 MVP 的可编辑 AI 占位结果。',
    status: 'local',
    error: '未找到可用于 generate_chapter_draft 的远程模型配置。',
    score: 0,
    items: [],
  });

  render(<App />);
  await screen.findByDisplayValue('第一章');
  fireEvent.click(screen.getByText('一键生成本章正文'));

  expect((await screen.findAllByText(/当前没有可用于该任务的远程模型/)).length).toBeGreaterThan(0);
  expect(screen.queryByText(/这是本地 MVP 的可编辑 AI 占位结果/)).not.toBeInTheDocument();
});

test('describes timeout fallback as slow generation instead of model failure', async () => {
  mockProjectApi();
  vi.spyOn(api, 'runAi').mockResolvedValue({
    workflow: 'generate_outline',
    text: '{}',
    status: 'fallback',
    error: '远程模型仍可能在生成，但 600 秒内暂未返回结果。原始错误：timed out',
    score: 0,
    items: [],
  });

  render(<App />);
  fireEvent.click(within(screen.getByRole('navigation')).getByRole('button', { name: /大纲/ }));
  await screen.findByText('生成 5 章大纲');
  fireEvent.click(screen.getByText('生成 5 章大纲'));

  expect((await screen.findAllByText(/远程模型仍可能在生成，当前显示本地占位结果/)).length).toBeGreaterThan(0);
  expect(screen.queryByText(/远程模型调用失败，已回退到本地占位结果。错误摘要：远程模型仍可能在生成/)).not.toBeInTheDocument();
});

test('shows a global execution indicator while generating chapter content', async () => {
  mockProjectApi();
  vi.mocked(api.listChapters).mockResolvedValue([mockChapter]);
  const generation = deferred<Awaited<ReturnType<typeof api.runAi>>>();
  vi.spyOn(api, 'runAi').mockReturnValue(generation.promise);

  render(<App />);
  await screen.findByDisplayValue('第一章');
  fireEvent.click(screen.getByText('一键生成本章正文'));

  expect(await screen.findByText('正在执行：生成本章正文')).toBeInTheDocument();
  expect(screen.getAllByText(/请求后端读取章节、大纲、角色和 llmwiki 上下文|统一压缩写作资产/).length).toBeGreaterThan(0);

  await act(async () => {
    generation.resolve({
      workflow: 'generate_chapter_draft',
      text: '真实模型生成的正文',
      score: 0,
      items: [],
    });
  });

  expect(await screen.findByText('执行完成：生成本章正文')).toBeInTheDocument();
});

test('shows a global execution indicator while saving model configuration', async () => {
  mockProjectApi();
  const saveModel = deferred<GenericRecord>();
  vi.spyOn(api, 'createRecord').mockReturnValue(saveModel.promise);

  render(<App />);
  await screen.findByRole('button', { name: /测试项目/ });
  fireEvent.click(screen.getByText('设置'));
  fireEvent.click(screen.getByRole('button', { name: /模型配置/ }));
  fireEvent.change(screen.getByLabelText('Model Name'), { target: { value: 'gpt-test' } });
  fireEvent.click(screen.getByText('保存配置'));

  expect(await screen.findByText('正在执行：保存模型配置')).toBeInTheDocument();
  expect(screen.getAllByText(/正在写入当前项目的模型配置/).length).toBeGreaterThan(0);

  await act(async () => {
    saveModel.resolve({
      id: 'model-1',
      title: 'gpt-test',
      category: 'OpenAI',
      content: 'gpt-test',
      status: 'active',
    });
  });

  expect(await screen.findByText('执行完成：保存模型配置')).toBeInTheDocument();
});

test('connection test uses model connection endpoint and refuses empty model form', async () => {
  mockProjectApi();
  const runAi = vi.spyOn(api, 'runAi').mockResolvedValue({
    workflow: 'analyze_style_sample',
    text: '不应该用普通 AI 工作流测试连接',
    score: 0,
    items: [],
  });
  const testModelConnection = vi.spyOn(api, 'testModelConnection').mockResolvedValue({
    ok: true,
    model: 'gpt-test',
    message: '远程模型连接成功。',
  });

  render(<App />);
  await screen.findByRole('button', { name: /测试项目/ });
  fireEvent.click(screen.getByText('设置'));
  fireEvent.click(screen.getByRole('button', { name: /模型配置/ }));
  fireEvent.change(screen.getByLabelText('配置名称'), { target: { value: '测试模型' } });
  fireEvent.change(screen.getByPlaceholderText('sk-...'), { target: { value: 'sk-test' } });
  fireEvent.change(screen.getByPlaceholderText('gpt-4o-mini'), { target: { value: 'gpt-test' } });
  fireEvent.click(screen.getByRole('button', { name: /测试连接/ }));

  await waitFor(() => expect(testModelConnection).toHaveBeenCalled());
  expect(testModelConnection).toHaveBeenCalledWith(
    mockProject.id,
    expect.objectContaining({
      api_key: 'sk-test',
      model_name: 'gpt-test',
    }),
  );
  expect(runAi).not.toHaveBeenCalled();
  expect((await screen.findAllByText(/连接测试成功/)).length).toBeGreaterThan(0);
});

test('renders dedicated timeline foreshadowing taboo and knowledge workbenches', async () => {
  mockProjectApi();
  render(<App />);

  fireEvent.click(screen.getByRole('button', { name: /时间线/ }));
  expect(await screen.findByText('时间线工作台')).toBeInTheDocument();
  expect(screen.queryByText('写入资料')).not.toBeInTheDocument();

  fireEvent.click(screen.getByRole('button', { name: /伏笔管理/ }));
  expect(await screen.findByText('伏笔工作台')).toBeInTheDocument();
  expect(screen.queryByText('写入资料')).not.toBeInTheDocument();

  fireEvent.click(screen.getByRole('button', { name: /雷点控制/ }));
  expect(await screen.findByText('雷点规则工作台')).toBeInTheDocument();
  expect(screen.queryByText('写入资料')).not.toBeInTheDocument();

  fireEvent.click(screen.getByRole('button', { name: /知识库/ }));
  expect(await screen.findByText('llmwiki 知识库')).toBeInTheDocument();
  expect(screen.queryByText('写入资料')).not.toBeInTheDocument();
});

test('renders fixed AI result actions in the chapter editor', () => {
  render(<App />);
  const editor = screen.getByPlaceholderText('请先创建或选择章节') as HTMLTextAreaElement;
  fireEvent.change(editor, { target: { value: '选中文本' } });
  editor.setSelectionRange(0, 4);
  fireEvent.mouseUp(editor);
  expect(screen.getByText('AI 创作副驾驶')).toBeInTheDocument();
  expect(screen.getByText('插入正文')).toBeInTheDocument();
  expect(screen.getByText('替换选中内容')).toBeInTheDocument();
  expect(screen.getByText('保存为版本')).toBeInTheDocument();
  expect(screen.getByText('收藏到灵感库')).toBeInTheDocument();
});

test('chapter editor exposes real generation and version actions', () => {
  render(<App />);
  expect(screen.getByText('一键生成本章正文')).toBeInTheDocument();
  expect(screen.getByText('续写当前章节')).toBeInTheDocument();
  expect(screen.getByText('保存为版本')).toBeInTheDocument();
});
