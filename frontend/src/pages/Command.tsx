import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Compass, Feather, Globe, Map, Search, Sparkles, Users } from 'lucide-react';
import { useWorkspace } from '../shell/workspace';
import { PageHeader } from '../ui/basics';

export function CommandPage() {
  const navigate = useNavigate();
  const { projectId, project } = useWorkspace();
  const [query, setQuery] = useState('');

  const base = projectId ? `/projects/${projectId}` : '/projects';
  const commands = [
    { label: '进入写作', hint: '打开章节编辑器', icon: Feather, to: `${base}/writing` },
    { label: 'AI 工作室', hint: '生成人物 / 世界观 / 大纲', icon: Sparkles, to: `${base}/ai` },
    { label: '人物', hint: '管理角色档案', icon: Users, to: `${base}/characters` },
    { label: '世界观', hint: '地点 / 组织 / 规则', icon: Globe, to: `${base}/world` },
    { label: '大纲', hint: '章节板', icon: Map, to: `${base}/outline` },
    { label: '项目库', hint: '切换与管理项目', icon: Compass, to: '/projects' },
  ];
  const filtered = commands.filter((command) => `${command.label}${command.hint}`.toLowerCase().includes(query.toLowerCase()));

  return (
    <div className="page-inner" style={{ maxWidth: 640 }}>
      <PageHeader title="命令" sub={project ? `当前项目：${project.title}` : '快速跳转到任意工作区'} />
      <div className="topbar-search" style={{ width: '100%', cursor: 'text', padding: '10px 14px' }}>
        <Search size={14} />
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="输入命令名…"
          autoFocus
          style={{ border: 'none', padding: 0, background: 'transparent' }}
        />
        <kbd>⌘K</kbd>
      </div>
      <div className="card" style={{ marginTop: 12, padding: 8 }}>
        {filtered.map((command) => {
          const Icon = command.icon;
          return (
            <button key={command.label} className="row" onClick={() => navigate(command.to)}>
              <Icon size={15} style={{ color: 'var(--accent)' }} />
              <span className="grow">
                <b style={{ display: 'block' }}>{command.label}</b>
                <small>{command.hint}</small>
              </span>
            </button>
          );
        })}
        {filtered.length === 0 && <p className="muted" style={{ padding: 14 }}>没有匹配的命令</p>}
      </div>
    </div>
  );
}
