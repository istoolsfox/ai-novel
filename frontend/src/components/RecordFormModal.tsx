import { FormEvent, useState } from 'react';
import { GenericRecord } from '../api';
import { Modal } from '../ui/basics';

export type FieldDef = {
  key: string; // 'title' | 'category' | 'content' | 'payload.xxx'
  label: string;
  type?: 'text' | 'textarea' | 'select' | 'range';
  options?: string[];
  placeholder?: string;
  rows?: number;
  required?: boolean;
};

type FormValues = Record<string, string>;

function readValue(record: Partial<GenericRecord> | null, key: string): string {
  if (!record) return '';
  if (key.startsWith('payload.')) {
    const payloadKey = key.slice('payload.'.length);
    const value = record.payload?.[payloadKey];
    return value === undefined || value === null ? '' : String(value);
  }
  const value = (record as Record<string, unknown>)[key];
  return value === undefined || value === null ? '' : String(value);
}

export function valuesToRecord(values: FormValues, base?: Partial<GenericRecord>): Partial<GenericRecord> {
  const result: Partial<GenericRecord> = { ...base };
  const payload: Record<string, unknown> = { ...(base?.payload ?? {}) };
  for (const [key, value] of Object.entries(values)) {
    if (key.startsWith('payload.')) {
      payload[key.slice('payload.'.length)] = value;
    } else {
      (result as Record<string, unknown>)[key] = value;
    }
  }
  result.payload = payload;
  return result;
}

export function RecordFormModal({
  modalTitle,
  fields,
  record,
  extraValues,
  onClose,
  onSave,
  saveLabel,
}: {
  modalTitle: string;
  fields: FieldDef[];
  record?: GenericRecord | null;
  extraValues?: Partial<GenericRecord>;
  onClose: () => void;
  onSave: (values: Partial<GenericRecord>) => Promise<void> | void;
  saveLabel?: string;
}) {
  const [values, setValues] = useState<FormValues>(() => {
    const initial: FormValues = {};
    for (const field of fields) initial[field.key] = readValue(record ?? extraValues ?? null, field.key);
    return initial;
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const set = (key: string, value: string) => setValues((prev) => ({ ...prev, [key]: value }));

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (saving) return;
    const missing = fields.find((field) => field.required && !values[field.key]?.trim());
    if (missing) {
      setError(`请填写「${missing.label}」`);
      return;
    }
    setSaving(true);
    setError('');
    try {
      await onSave(valuesToRecord(values, { ...(extraValues ?? {}), ...(record ? { id: record.id } : {}) }));
      onClose();
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : '保存失败');
      setSaving(false);
    }
  };

  return (
    <Modal
      title={modalTitle}
      onClose={onClose}
      footer={
        <>
          <span className="spacer">{error}</span>
          <button type="button" className="btn" onClick={onClose}>取消</button>
          <button type="submit" form="record-form" className="btn btn-primary" disabled={saving}>
            {saving ? '保存中…' : saveLabel ?? (record ? '保存修改' : '创建')}
          </button>
        </>
      }
    >
      <form id="record-form" onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {fields.map((field) => {
          const id = `record-field-${field.key.replace('.', '-')}`;
          if (field.type === 'select') {
            return (
              <label className="field" key={field.key}>
                <span>{field.label}{field.required ? ' *' : ''}</span>
                <select id={id} value={values[field.key] ?? ''} onChange={(event) => set(field.key, event.target.value)}>
                  {(field.options ?? []).map((option) => (
                    <option key={option} value={option}>{option}</option>
                  ))}
                </select>
              </label>
            );
          }
          if (field.type === 'range') {
            return (
              <label className="field" key={field.key}>
                <span>{field.label} · {values[field.key] || '0'}</span>
                <input
                  id={id}
                  type="range"
                  min={0}
                  max={100}
                  value={Number(values[field.key] || 0)}
                  onChange={(event) => set(field.key, event.target.value)}
                />
              </label>
            );
          }
          if (field.type === 'textarea') {
            return (
              <label className="field" key={field.key}>
                <span>{field.label}{field.required ? ' *' : ''}</span>
                <textarea
                  id={id}
                  value={values[field.key] ?? ''}
                  onChange={(event) => set(field.key, event.target.value)}
                  rows={field.rows ?? 4}
                  placeholder={field.placeholder}
                />
              </label>
            );
          }
          return (
            <label className="field" key={field.key}>
              <span>{field.label}{field.required ? ' *' : ''}</span>
              <input
                id={id}
                value={values[field.key] ?? ''}
                onChange={(event) => set(field.key, event.target.value)}
                placeholder={field.placeholder}
              />
            </label>
          );
        })}
      </form>
    </Modal>
  );
}
