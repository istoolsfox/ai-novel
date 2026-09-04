/** 历史数据里有些记录的 content 存的是整段 JSON。展示时把它还原成「每行一条字符串字段」的可读文本。 */
export function readableContent(text: string | null | undefined): string {
  const trimmed = (text ?? '').trim();
  if (!trimmed.startsWith('{') || !trimmed.endsWith('}')) return text ?? '';
  try {
    const parsed = JSON.parse(trimmed) as unknown;
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return text ?? '';
    const lines = Object.values(parsed as Record<string, unknown>)
      .filter((value) => typeof value === 'string' && value.trim())
      .map((value) => String(value).trim());
    return lines.length ? lines.join('\n') : text ?? '';
  } catch {
    return text ?? '';
  }
}
