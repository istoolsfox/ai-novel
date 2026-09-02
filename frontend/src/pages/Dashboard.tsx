import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Feather, FolderOpen, Plus, Sparkles } from 'lucide-react';
import { api } from '../api';
import { useWorkspace } from '../shell/workspace';
import { EmptyState, PageHeader } from '../ui/basics';
import { ProjectsManagerModal } from '../components/ProjectsManagerModal';

type ProjectCard = { id: string; title: string; genre: string; topic: string; chapters: number; words: number };

export function Dashboard() {
  const navigate = useNavigate();
  const { projects, projectsLoading } = useWorkspace();
  const [cards, setCards] = useState<ProjectCard[]>([]);
  const [managing, setManaging] = useState(false);

  useEffect(() => {
    let alive = true;
    const recent = projects.slice(0, 6);
    Promise.all(
      recent.map(async (project) => {
        try {
          const chapters = await api.listChapters(project.id);
          return {
            id: project.id,
            title: project.title,
            genre: project.genre ?? '',
            topic: project.topic ?? '',
            chapters: chapters.length,
            words: chapters.reduce((sum, chapter) => sum + (chapter.draft?.length ?? 0), 0),
          };
        } catch {
          return { id: project.id, title: project.title, genre: project.genre ?? '', topic: project.topic ?? '', chapters: 0, words: 0 };
        }
      }),
    ).then((items) => {
      if (alive) setCards(items);
    });
    return () => {
      alive = false;
    };
  }, [projects]);

  const totalWords = cards.reduce((sum, card) => sum + card.words, 0);
  const totalChapters = cards.reduce((sum, card) => sum + card.chapters, 0);

  return (
    <div className="page-inner">
      <PageHeader
        title="继续你的故事。"
        sub="从世界观与人物开始搭建，或直接进入写作——AI 会基于你的设定续写。"
        actions={
          <>
            <button className="btn" onClick={() => setManaging(true)}>
              <Plus size={14} /> 新建项目
            </button>
            {cards[0] && (
              <button className="btn btn-primary" onClick={() => navigate(`/projects/${cards[0].id}/writing`)}>
                <Feather size={14} /> 继续写作
              </button>
            )}
          </>
        }
      />

      <div className="grid" style={{ gridTemplateColumns: 'repeat(3, minmax(0, 1fr))' }}>
        <div className="card">
          <div className="stat-value">{projects.length}</div>
          <div className="stat-label">项目</div>
        </div>
        <div className="card">
          <div className="stat-value">{totalChapters}</div>
          <div className="stat-label">章节（最近项目）</div>
        </div>
        <div className="card">
          <div className="stat-value">{totalWords.toLocaleString()}</div>
          <div className="stat-label">累计字数</div>
        </div>
      </div>

      <section className="section">
        <h2 className="section-title">
          最近项目 <small>RECENT PROJECTS</small>
          <span className="spacer" />
          <button className="btn btn-ghost" onClick={() => navigate('/projects')}>全部项目</button>
        </h2>
        {projectsLoading ? (
          <p className="muted">加载中…</p>
        ) : cards.length === 0 ? (
          <EmptyState
            icon={<FolderOpen size={26} />}
            title="还没有项目"
            hint="创建第一个项目，开始搭建你的故事世界。"
            action={
              <button className="btn btn-primary" onClick={() => setManaging(true)}>
                <Plus size={14} /> 新建项目
              </button>
            }
          />
        ) : (
          <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))' }}>
            {cards.map((card) => (
              <button key={card.id} className="card card-click" onClick={() => navigate(`/projects/${card.id}/overview`)}>
                <div className="row-flex" style={{ marginBottom: 10 }}>
                  <span className="avatar accent">{card.title.slice(0, 1)}</span>
                  <span className="grow ellip">
                    <b style={{ fontFamily: 'var(--serif)', fontSize: 15 }}>{card.title}</b>
                  </span>
                </div>
                <p className="muted ellip" style={{ fontSize: 12.5, marginBottom: 12 }}>{card.topic || card.genre || '暂无简介'}</p>
                <div className="row-flex" style={{ gap: 6 }}>
                  <span className="badge">{card.chapters} 章</span>
                  <span className="badge">{card.words.toLocaleString()} 字</span>
                </div>
              </button>
            ))}
          </div>
        )}
      </section>

      <section className="section">
        <h2 className="section-title">
          <Sparkles size={15} style={{ color: 'var(--ai)' }} /> AI 提示
        </h2>
        <div className="card" style={{ display: 'flex', gap: 14, alignItems: 'flex-start' }}>
          <span className="avatar ai"><Sparkles size={14} /></span>
          <div>
            <b style={{ fontSize: 13.5 }}>用 AI 工作室冷启动一个新故事</b>
            <p className="muted" style={{ fontSize: 12.5, marginTop: 4, lineHeight: 1.7 }}>
              在 AI 工作室输入一句话概念，依次生成故事圣经、人物、世界观与大纲；每一步都可以手动修改、回退版本后再继续。
            </p>
          </div>
        </div>
      </section>

      {managing && <ProjectsManagerModal onClose={() => setManaging(false)} />}
    </div>
  );
}
