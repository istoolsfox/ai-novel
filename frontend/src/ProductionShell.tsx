import { lazy, Suspense, useCallback, useEffect, useState } from 'react';
import App from './App';
import { UnifiedConsole } from './components/UnifiedConsole';
import { releaseApi } from './releaseApi';
import {
  getPreferredProjectId,
  installProjectSelectionBridge,
  setPreferredProjectId,
  subscribeProjectSelection,
} from './projectSelectionBridge';

const FirstRunWizard = lazy(() => import('./components/FirstRunWizard'));

installProjectSelectionBridge();

export function ProductionShell() {
  const [selectedProjectId, setSelectedProjectId] = useState(getPreferredProjectId());
  const [editorRevision, setEditorRevision] = useState(0);
  const [setupRequired, setSetupRequired] = useState(false);

  useEffect(() => {
    const synchronize = (projectId: string) => {
      setSelectedProjectId((current) => (current === projectId ? current : projectId));
    };
    const unsubscribe = subscribeProjectSelection(synchronize);
    const current = getPreferredProjectId();
    if (current) synchronize(current);
    return unsubscribe;
  }, []);

  useEffect(() => {
    if (sessionStorage.getItem('ai-novel-setup-dismissed') === '1') return;
    void releaseApi.info()
      .then((info) => setSetupRequired(!info.setup_completed))
      .catch(() => undefined);
  }, []);

  const selectFromConsole = useCallback((projectId: string) => {
    if (!projectId) return;
    setPreferredProjectId(projectId);
    setSelectedProjectId(projectId);
    setEditorRevision((current) => current + 1);
  }, []);

  return (
    <>
      <App key={`editor-${editorRevision}`} />
      <UnifiedConsole
        selectedProjectId={selectedProjectId}
        onSelectedProjectIdChange={selectFromConsole}
      />
      {setupRequired && (
        <Suspense fallback={null}>
          <FirstRunWizard
            onComplete={() => {
              sessionStorage.removeItem('ai-novel-setup-dismissed');
              setSetupRequired(false);
            }}
            onDismiss={() => {
              sessionStorage.setItem('ai-novel-setup-dismissed', '1');
              setSetupRequired(false);
            }}
          />
        </Suspense>
      )}
    </>
  );
}
