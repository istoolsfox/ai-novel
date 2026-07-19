import { useCallback, useEffect, useState } from 'react';
import App from './App';
import { UnifiedConsole } from './components/UnifiedConsole';
import {
  getPreferredProjectId,
  installProjectSelectionBridge,
  setPreferredProjectId,
  subscribeProjectSelection,
} from './projectSelectionBridge';

installProjectSelectionBridge();

export function ProductionShell() {
  const [selectedProjectId, setSelectedProjectId] = useState(getPreferredProjectId());
  const [editorRevision, setEditorRevision] = useState(0);

  useEffect(() => subscribeProjectSelection((projectId) => {
    setSelectedProjectId((current) => (current === projectId ? current : projectId));
  }), []);

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
    </>
  );
}
