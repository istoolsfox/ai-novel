import { useCallback, useEffect, useState } from 'react';
import { api, GenericRecord } from '../api';

export function useRecords(projectId: string | undefined, resource: string | null) {
  const [records, setRecords] = useState<GenericRecord[]>([]);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(() => {
    if (!projectId || !resource) {
      setRecords([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    api.listRecords(projectId, resource).then((items) => {
      setRecords(items);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [projectId, resource]);

  useEffect(() => {
    reload();
  }, [reload]);

  const create = useCallback(async (payload: Partial<GenericRecord>) => {
    if (!projectId || !resource) return;
    const created = await api.createRecord(projectId, resource, payload);
    setRecords((items) => [created, ...items]);
    return created;
  }, [projectId, resource]);

  const update = useCallback(async (id: string, payload: Partial<GenericRecord>) => {
    if (!projectId || !resource) return;
    const updated = await api.updateRecord(projectId, resource, id, payload);
    setRecords((items) => items.map((item) => (item.id === id ? { ...item, ...updated } : item)));
    return updated;
  }, [projectId, resource]);

  const remove = useCallback(async (id: string) => {
    if (!projectId || !resource) return;
    await api.deleteRecord(projectId, resource, id);
    setRecords((items) => items.filter((item) => item.id !== id));
  }, [projectId, resource]);

  return { records, loading, reload, create, update, remove };
}
