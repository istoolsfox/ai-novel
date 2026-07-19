import { lazy, Suspense, useState } from 'react';
import { Activity, DatabaseZap, KeyRound, LoaderCircle, ServerCog } from 'lucide-react';
import '../operations-panel.css';
import '../security-panel.css';
import '../upgrade-panel.css';

const UnifiedConsolePanel = lazy(() => import('./UnifiedConsolePanel'));
const OperationsPanel = lazy(() => import('./OperationsPanel'));
const SecurityPanel = lazy(() => import('./SecurityPanel'));
const UpgradePanel = lazy(() => import('./UpgradePanel'));

export type UnifiedConsoleProps = {
  selectedProjectId?: string;
  onSelectedProjectIdChange?: (projectId: string) => void;
};

export function UnifiedConsole({ selectedProjectId = '', onSelectedProjectIdChange }: UnifiedConsoleProps) {
  const [open, setOpen] = useState(false);
  const [operationsOpen, setOperationsOpen] = useState(false);
  const [securityOpen, setSecurityOpen] = useState(false);
  const [upgradeOpen, setUpgradeOpen] = useState(false);

  const fallback = (
    <div className="uc-backdrop" role="presentation">
      <div className="uc-console-loading" role="status">
        <LoaderCircle className="uc-spin" size={24} />
        正在加载控制台…
      </div>
    </div>
  );

  return (
    <>
      <div className="uc-launcher-stack">
        <button className="uc-launcher upgrade-launcher" type="button" onClick={() => setUpgradeOpen(true)} aria-label="打开升级与回滚中心">
          <DatabaseZap size={20} />
          <span>升级中心</span>
        </button>
        <button className="uc-launcher security-launcher" type="button" onClick={() => setSecurityOpen(true)} aria-label="打开安全与凭证中心">
          <KeyRound size={20} />
          <span>安全中心</span>
        </button>
        <button className="uc-launcher ops-launcher" type="button" onClick={() => setOperationsOpen(true)} aria-label="打开运行与部署中心">
          <ServerCog size={20} />
          <span>运行中心</span>
        </button>
        <button className="uc-launcher" type="button" onClick={() => setOpen(true)} aria-label="打开统一托管控制台">
          <Activity size={20} />
          <span>托管控制台</span>
        </button>
      </div>
      {open && (
        <Suspense fallback={fallback}>
          <UnifiedConsolePanel
            selectedProjectId={selectedProjectId}
            onSelectedProjectIdChange={onSelectedProjectIdChange}
            onClose={() => setOpen(false)}
          />
        </Suspense>
      )}
      {operationsOpen && (
        <Suspense fallback={fallback}>
          <OperationsPanel onClose={() => setOperationsOpen(false)} />
        </Suspense>
      )}
      {securityOpen && (
        <Suspense fallback={fallback}>
          <SecurityPanel selectedProjectId={selectedProjectId} onClose={() => setSecurityOpen(false)} />
        </Suspense>
      )}
      {upgradeOpen && (
        <Suspense fallback={fallback}>
          <UpgradePanel onClose={() => setUpgradeOpen(false)} />
        </Suspense>
      )}
    </>
  );
}
