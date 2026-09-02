import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, FileText, Users, Map, Sparkles, FolderOpen, LoaderCircle } from 'lucide-react';

const COMMANDS = [
  { label: 'Create Character', icon: Users, to: '/projects/:id/characters' },
  { label: 'Generate Outline', icon: Map, to: '/projects/:id/outline' },
  { label: 'Continue Writing', icon: FileText, to: '/projects/:id/writing' },
  { label: 'Open AI Studio', icon: Sparkles, to: '/projects/:id/ai' },
  { label: 'Open Projects', icon: FolderOpen, to: '/projects' },
];

export function CommandPage() {
  const navigate = useNavigate();
  const [q, setQ] = useState('');
  const filtered = COMMANDS.filter((c) => c.label.toLowerCase().includes(q.toLowerCase()));
  return (
    <div>
      <h1>Command</h1>
      <p className="os-page-sub">全局命令面板</p>
      <div className="os-card" style={{ maxWidth: '520px' }}>
        <div className="os-topbar-search" style={{ marginBottom: '0.75rem' }}>
          <Search size={14} />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="搜索或执行命令…" autoFocus style={{ border: 'none', flex: 1, outline: 'none' }} />
          <kbd>⌘K</kbd>
        </div>
        <div className="os-ai-actions">
          {filtered.map((c) => {
            const Icon = c.icon;
            return (
              <button key={c.label} className="os-ai-action" onClick={() => navigate('/projects/demo/overview')}>
                <Icon size={14} /> {c.label}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
