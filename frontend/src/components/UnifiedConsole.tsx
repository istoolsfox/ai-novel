import { lazy, Suspense, useState } from 'react';
import { Activity, LoaderCircle } from 'lucide-react';

const UnifiedConsolePanel = lazy(() => import('./UnifiedConsolePanel'));

export type UnifiedConsoleProps = {
  selectedProjectId?: string;
  onSelectedProjectIdChange?: (projectId: string) => void;
};

export function UnifiedConsole({ selectedProjectId = '', onSelectedProjectIdChange }: UnifiedConsoleProps) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button className="uc-launcher" type="button" onClick={() => setOpen(true)} aria-label="打开统一托管控制台">
        <Activity size={20} />
        <span>托管控制台</span>
      </button>
      {open && (
        <Suspense
          fallback={(
            <div className="uc-backdrop" role="presentation">
              <div className="uc-console-loading" role="status">
                <LoaderCircle className="uc-spin" size={24} />
                正在加载托管控制台…
              </div>
            </div>
          )}
        >
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
