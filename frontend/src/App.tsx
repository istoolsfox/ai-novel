import { useEffect, useState } from 'react';
import { Background, Controls, Edge, Node, ReactFlow } from '@xyflow/react';
import {
  BookOpen,
  Brain,
  CheckCircle2,
  Download,
  FileText,
  GitBranch,
  Library,
  Network,
  PenLine,
  Plus,
  ShieldAlert,
  Sparkles,
  Star,
} from 'lucide-react';
import { api, Chapter, ChapterVersion, GenericRecord, Project } from './api';

type TabKey =
  | 'chapters'
  | 'bible'
  | 'graph'
  | 'timeline'
  | 'foreshadowing'
  | 'style'
  | 'taboo'
  | 'knowledge'
  | 'wiki'
  | 'export';

const tabs: Array<{ key: TabKey; label: string; icon: typeof BookOpen }> = [
  { key: 'chapters', label: '章节编辑器', icon: PenLine },
  { key: 'bible', label: '故事圣经', icon: BookOpen },
  { key: 'graph', label: '角色关系图', icon: Network },
  { key: 'timeline', label: '时间线', icon: GitBranch },
  { key: 'foreshadowing', label: '伏笔管理', icon: Sparkles },
  { key: 'style', label: '风格学习', icon: Star },
  { key: 'taboo', label: '雷点控制', icon: ShieldAlert },
  { key: 'knowledge', label: '知识库', icon: Library },
  { key: 'wiki', label: 'llmwiki 记忆', icon: Brain },
  { key: 'export', label: '导出', icon: Download },
];

const resourceMap: Record<TabKey, string | null> = {
  chapters: null,
  bible: 'characters',
  graph: 'character-relationships',
  timeline: 'timeline-events',
  foreshadowing: 'foreshadowings',
  style: 'style-profiles',
  taboo: 'taboo-rules',
  knowledge: 'knowledge-documents',
  wiki: null,
  export: null,
};

export default function App() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [selectedChapter, setSelectedChapter] = useState<Chapter | null>(null);
  const [versions, setVersions] = useState<ChapterVersion[]>([]);
  const [records, setRecords] = useState<GenericRecord[]>([]);
  const [wikiPages, setWikiPages] = useState<Array<{ path: string; content: string }>>([]);
  const [activeTab, setActiveTab] = useState<TabKey>('chapters');
  const [log, setLog] = useState('准备就绪');
  const [projectTitle, setProjectTitle] = useState('前朝公主');
  const [recordTitle, setRecordTitle] = useState('');
  const [recordContent, setRecordContent] = useState('');
  const [draft, setDraft] = useState('');

  useEffect(() => {
    void loadProjects();
  }, []);

  useEffect(() => {
    if (selectedProject) {
      void loadChapters(selectedProject.id);
      void loadTabData(activeTab, selectedProject.id);
    }
  }, [selectedProject, activeTab]);

  useEffect(() => {
    setDraft(selectedChapter?.draft ?? '');
    if (selectedProject && selectedChapter) {
      void loadVersions(selectedProject.id, selectedChapter.id);
    }
  }, [selectedChapter, selectedProject]);

  async function loadProjects() {
    try {
      const result = await api.listProjects();
      setProjects(result);
      setSelectedProject((current) => current ?? result[0] ?? null);
    } catch {
      setLog('后端未启动时，界面会保持空状态。');
    }
  }

  async function loadChapters(projectId: string) {
    const result = await api.listChapters(projectId);
    setChapters(result);
    setSelectedChapter((current) => {
      if (current && result.some((chapter) => chapter.id === current.id)) return current;
      return result[0] ?? null;
    });
  }

  async function loadVersions(projectId: string, chapterId: string) {
    setVersions(await api.listVersions(projectId, chapterId));
  }

  async function loadTabData(tab: TabKey, projectId: string) {
    if (tab === 'wiki') {
      setWikiPages(await api.wikiSearch(projectId));
      return;
    }
    const resource = resourceMap[tab];
    if (resource) setRecords(await api.listRecords(projectId, resource));
  }

  async function createProject() {
    const project = await api.createProject({
      title: projectTitle,
      topic: '一个被流放的前朝公主发现能改写记忆的古籍',
      genre: '奇幻',
      audience: '网文读者',
      tone: '克制、悬疑',
      target_chapter_count: 5,
      target_words_per_chapter: 3000,
    });
    setProjects([project, ...projects]);
    setSelectedProject(project);
    setLog(`已创建项目：${project.title}`);
  }

  async function createChapter() {
    if (!selectedProject) return;
    const chapter = await api.createChapter(selectedProject.id, {
      chapter_number: chapters.length + 1,
      title: `第 ${chapters.length + 1} 章`,
      brief: '本章目标：推进主角发现古籍代价。',
      draft: '',
    });
    setChapters([...chapters, chapter]);
    setSelectedChapter(chapter);
    setLog('章节已创建并自动归属当前项目。');
  }

  async function saveChapter() {
    if (!selectedProject || !selectedChapter) return;
    const updated = await api.updateChapter(selectedProject.id, selectedChapter.id, {
      ...selectedChapter,
      draft,
    });
    setSelectedChapter(updated);
    await loadChapters(selectedProject.id);
    setLog('章节正文已保存。');
  }

  async function generateVariant() {
    if (!selectedProject || !selectedChapter) return;
    const result = await api.runAi(selectedProject.id, 'generate_chapter_variants', {
      chapter_id: selectedChapter.id,
      prompt: selectedChapter.brief,
      count: 2,
    });
    await loadVersions(selectedProject.id, selectedChapter.id);
    setLog(result.text);
  }

  async function scoreChapter() {
    if (!selectedProject || !selectedChapter) return;
    const result = await api.runAi(selectedProject.id, 'score_chapter', {
      chapter_id: selectedChapter.id,
      content: draft,
    });
    setLog(`章节评分：${result.score}。${result.text}`);
  }

  async function finalizeChapter() {
    if (!selectedProject || !selectedChapter) return;
    const updated = await api.finalizeChapter(selectedProject.id, selectedChapter.id);
    setSelectedChapter(updated);
    await loadTabData('wiki', selectedProject.id);
    setLog('章节已定稿，摘要已进入结构化记忆和 llmwiki 页面。');
  }

  async function selectVersion(versionId: string) {
    if (!selectedProject || !selectedChapter) return;
    const updated = await api.selectVersion(selectedProject.id, selectedChapter.id, versionId);
    setSelectedChapter(updated);
    setDraft(updated.draft);
    setLog('已将候选版本设为当前正文。');
  }

  async function createRecord() {
    if (!selectedProject) return;
    const resource = resourceMap[activeTab];
    if (!resource) return;
    await api.createRecord(selectedProject.id, resource, {
      title: recordTitle || '未命名资料',
      content: recordContent,
      category: activeTab,
    });
    setRecordTitle('');
    setRecordContent('');
    await loadTabData(activeTab, selectedProject.id);
    setLog('资料已保存到当前项目。');
  }

  async function createWikiPage() {
    if (!selectedProject) return;
    await api.wikiWrite(selectedProject.id, recordTitle || 'notes/index.md', recordContent || '# 新记忆页');
    await loadTabData('wiki', selectedProject.id);
    setLog('Wiki 页面已写入当前项目 memory/wiki。');
  }

  const relationshipNodes: Node[] = records.slice(0, 6).map((record, index) => ({
    id: record.id,
    data: { label: record.title || `关系 ${index + 1}` },
    position: { x: 80 + (index % 3) * 180, y: 80 + Math.floor(index / 3) * 130 },
  }));
  const relationshipEdges: Edge[] = relationshipNodes.slice(1).map((node, index) => ({
    id: `edge-${node.id}`,
    source: relationshipNodes[0]?.id ?? node.id,
    target: node.id,
    label: index % 2 === 0 ? '同盟' : '冲突',
  }));

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            <Brain size={28} />
          </div>
          <div>
            <h1>AI 小说创作平台</h1>
            <p>本地优先 / 长篇记忆 / 项目隔离</p>
          </div>
        </div>

        <div className="create-project">
          <div className="section-title">
            <span>项目库</span>
            <small>{projects.length} 本小说</small>
          </div>
          <input value={projectTitle} onChange={(event) => setProjectTitle(event.target.value)} aria-label="项目标题" />
          <button className="primary-action" onClick={() => void createProject()}>
            <Plus size={16} />
            新建项目
          </button>
        </div>

        <div className="project-list">
          {projects.map((project) => (
            <button
              className={project.id === selectedProject?.id ? 'selected' : ''}
              key={project.id}
              onClick={() => setSelectedProject(project)}
            >
              <strong>{project.title}</strong>
              <span>{project.genre || '本地项目'} · {project.target_chapter_count || 0} 章计划</span>
            </button>
          ))}
          {projects.length === 0 && (
            <div className="empty-project">
              <strong>从侧栏创建第一本小说</strong>
              <span>后续章节、记忆、导出都会自动归属这里选中的项目。</span>
            </div>
          )}
        </div>
      </aside>

      <main className="workspace">
        <header className="topbar">
          <div>
            <span className="eyebrow">当前项目</span>
            <h2>{selectedProject?.title ?? '还没有项目'}</h2>
            <p className="project-context">
              {selectedProject
                ? `所有操作写入 ${selectedProject.title} 的项目目录`
                : '先从左侧项目库创建或选择小说项目'}
            </p>
          </div>
          <div className="topbar-stack">
            <div className="claude-note">
              <CheckCircle2 size={16} />
              执行计划前读取并遵循 CLAUDE.md
            </div>
            <div className="status-pill">
              <span>{log}</span>
            </div>
          </div>
        </header>

        <nav className="tabs">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button className={activeTab === tab.key ? 'active' : ''} key={tab.key} onClick={() => setActiveTab(tab.key)}>
                <Icon size={16} />
                {tab.label}
              </button>
            );
          })}
        </nav>

        {activeTab === 'chapters' && (
          <section className="chapter-grid">
            <div className="chapter-list">
              <div className="panel-heading">
                <span>章节目录</span>
                <small>{chapters.length} 章</small>
              </div>
              <button className="secondary-action" onClick={() => void createChapter()}>
                <Plus size={15} />
                新建章节
              </button>
              {chapters.map((chapter) => (
                <button
                  className={chapter.id === selectedChapter?.id ? 'selected' : ''}
                  key={chapter.id}
                  onClick={() => setSelectedChapter(chapter)}
                >
                  <strong>第 {chapter.chapter_number} 章</strong>
                  <span>{chapter.title}</span>
                </button>
              ))}
            </div>
            <div className="editor-panel">
              <div className="panel-heading">
                <span>正文工作台</span>
                <small>{selectedChapter ? selectedChapter.status : '未选择章节'}</small>
              </div>
              <input
                className="title-input"
                value={selectedChapter?.title ?? ''}
                readOnly
                placeholder="请选择或创建章节"
              />
              <textarea value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="在这里写章节正文..." />
              <div className="action-row">
                <button onClick={() => void saveChapter()}>保存正文</button>
                <button onClick={() => void generateVariant()}>生成多版本</button>
                <button onClick={() => void scoreChapter()}>独立评分</button>
                <button className="primary-action" onClick={() => void finalizeChapter()}>定稿并更新记忆</button>
              </div>
            </div>
            <div className="side-panel">
              <div className="panel-heading">
                <span>候选版本</span>
                <small>{versions.length} 个</small>
              </div>
              {versions.map((version) => (
                <article key={version.id}>
                  <strong>{version.label}</strong>
                  <p>{version.content.slice(0, 120)}</p>
                  <button onClick={() => void selectVersion(version.id)}>设为当前正文</button>
                </article>
              ))}
              {versions.length === 0 && <p className="muted">生成多版本后，这里会展示候选正文。</p>}
            </div>
          </section>
        )}

        {activeTab === 'graph' && (
          <section className="graph-panel">
            <ReactFlow nodes={relationshipNodes} edges={relationshipEdges} fitView>
              <Background />
              <Controls />
            </ReactFlow>
          </section>
        )}

        {activeTab !== 'chapters' && activeTab !== 'graph' && activeTab !== 'export' && activeTab !== 'wiki' && (
          <section className="records-layout">
            <div className="record-form">
              <div className="panel-heading">
                <span>写入资料</span>
                <small>当前项目</small>
              </div>
              <input value={recordTitle} onChange={(event) => setRecordTitle(event.target.value)} placeholder="标题" />
              <textarea value={recordContent} onChange={(event) => setRecordContent(event.target.value)} placeholder="内容" />
              <button onClick={() => void createRecord()}>保存到当前项目</button>
            </div>
            <div className="record-list">
              {records.map((record) => (
                <article key={record.id}>
                  <h3>{record.title}</h3>
                  <p>{record.content}</p>
                  <span>{record.status}</span>
                </article>
              ))}
            </div>
          </section>
        )}

        {activeTab === 'wiki' && (
          <section className="records-layout">
            <div className="record-form">
              <div className="panel-heading">
                <span>Wiki 页面</span>
                <small>memory/wiki</small>
              </div>
              <input value={recordTitle} onChange={(event) => setRecordTitle(event.target.value)} placeholder="characters/heroine.md" />
              <textarea value={recordContent} onChange={(event) => setRecordContent(event.target.value)} placeholder="# Wiki 记忆页" />
              <button onClick={() => void createWikiPage()}>写入 llmwiki 记忆</button>
            </div>
            <div className="record-list">
              {wikiPages.map((page) => (
                <article key={page.path}>
                  <h3>{page.path}</h3>
                  <p>{page.content.slice(0, 260)}</p>
                </article>
              ))}
            </div>
          </section>
        )}

        {activeTab === 'export' && selectedProject && (
          <section className="export-panel">
            <FileText size={42} />
            <h3>导出当前项目</h3>
            <p>导出接口只读取当前项目章节，避免不同小说串稿。</p>
            <div className="action-row">
              <a href={`/api/projects/${selectedProject.id}/export/markdown`}>Markdown</a>
              <a href={`/api/projects/${selectedProject.id}/export/txt`}>TXT</a>
              <a href={`/api/projects/${selectedProject.id}/export/docx`}>DOCX</a>
              <a href={`/api/projects/${selectedProject.id}/export/pdf`}>PDF</a>
              <a href={`/api/projects/${selectedProject.id}/export/epub`}>EPUB</a>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
