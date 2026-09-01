import { lazy, Suspense, useState } from 'react';
import { createPortal } from 'react-dom';
import { Activity, LoaderCircle } from 'lucide-react';

const UnifiedConsolePanel = lazy(() => import('./UnifiedConsolePanel'));

export type UnifiedConsoleProps = {
  selectedProjectId?: string;
  onSelectedProjectIdChange?: (projectId: string) => void;
};

export function UnifiedConsole({ selectedProjectId = '', onSelectedProjectIdChange }: UnifiedConsoleProps) {
  const [open, setOpen] = useState(false);

  const fallback = (
    <div className="uc-backdrop" role="presentation">
      <div className="uc-console-loading" role="status">
        <LoaderCircle className="uc-spin" size={24} />
        正在加载控制台…
      </div>
    </div>
  );

  const launchers = (
    <div className="uc-launcher-stack">
      <button className="uc-launcher" type="button" onClick={() => setOpen(true)} aria-label="打开托管控制台">
        <Activity size={18} />
        <span>托管控制台</span>
      </button>
    </div>
  );

  const headerSlot = document.getElementById('app-header-actions');

  return (
    <>
      {headerSlot ? createPortal(launchers, headerSlot) : launchers}
      {open && (
        <Suspense fallback={fallback}>
          <UnifiedConsolePanel
            selectedProjectId={selectedProjectId}
            onSelectedProjectIdChange={onSelectedProjectIdChange}
            onClose={() => setOpen(false)}
          />
        </Suspense>
      )}
    </>
  );
}
