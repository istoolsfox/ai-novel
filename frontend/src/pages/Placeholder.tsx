import { Feather } from 'lucide-react';
import { EmptyState, PageHeader } from '../ui/basics';

export function Placeholder({ title, desc }: { title: string; desc?: string }) {
  return (
    <div className="page-inner">
      <PageHeader title={title} sub={desc ?? '该模块将在后续阶段完善。'} />
      <EmptyState icon={<Feather size={26} />} title="建设中" hint="这一页的交互与视觉将遵循当前的墨纸设计系统逐步落地。" />
    </div>
  );
}
