export function Placeholder({ title, desc }: { title: string; desc?: string }) {
  return (
    <div>
      <h1>{title}</h1>
      <p className="os-page-sub">{desc ?? '该模块将在后续阶段完善。'}</p>
      <div className="os-empty">建设中…</div>
    </div>
  );
}
