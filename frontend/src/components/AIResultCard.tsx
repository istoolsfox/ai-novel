import { Copy, RefreshCw, Save, Sparkles, Trash2 } from 'lucide-react';
import { WorkbenchAIResult } from '../api';

type AIResultCardProps = {
  result: WorkbenchAIResult;
  canInsert?: boolean;
  canReplace?: boolean;
  canApply?: boolean;
  canSaveVersion?: boolean;
  canFavorite?: boolean;
  loading?: boolean;
  onInsert?: () => void;
  onReplace?: () => void;
  onApply?: () => void;
  onSaveVersion?: () => void;
  onFavorite?: () => void;
  onRegenerate?: () => void;
  onDelete?: () => void;
};

export function AIResultCard({
  result,
  canInsert = false,
  canReplace = false,
  canApply = false,
  canSaveVersion = false,
  canFavorite = false,
  loading = false,
  onInsert,
  onReplace,
  onApply,
  onSaveVersion,
  onFavorite,
  onRegenerate,
  onDelete,
}: AIResultCardProps) {
  const isError = result.status === 'error';
  const className = ['ai-result-card', 'fixed-result-card', isError ? 'error' : ''].join(' ');
  const isSlowGenerationTimeout = Boolean(result.error?.includes('仍可能在生成') || result.error?.includes('暂未返回结果'));
  const errorText = result.error
    ? isSlowGenerationTimeout
      ? `远程模型仍可能在生成，当前显示本地占位结果：${result.error}`
      : `远程模型调用失败，已回退到本地占位结果：${result.error}`
    : '';

  function copyResult() {
    void navigator.clipboard?.writeText(result.content);
  }

  return (
    <article className={className}>
      <header>
        <div>
          <strong>{result.title}</strong>
          {result.sourceWorkflow && <span>{result.sourceWorkflow}</span>}
        </div>
        <Sparkles size={16} />
      </header>
      {isError && errorText && <p className="ai-error-text">{errorText}</p>}
      <div className="ai-result-scroll" aria-label={`${result.title} 结果内容`}>
        {result.content}
      </div>
      <div className="compact-actions">
        {canInsert && <button onClick={onInsert}>插入正文</button>}
        {canReplace && <button onClick={onReplace}>替换选中内容</button>}
        {canApply && <button onClick={onApply}>应用到当前表单</button>}
        {canSaveVersion && (
          <button onClick={onSaveVersion}>
            <Save size={14} />
            保存为版本
          </button>
        )}
        {canFavorite && <button onClick={onFavorite}>收藏到灵感库</button>}
        <button onClick={copyResult}>
          <Copy size={14} />
          复制
        </button>
        <button disabled={loading} onClick={onRegenerate}>
          <RefreshCw size={14} />
          重新生成
        </button>
        {onDelete && (
          <button className="danger-action" onClick={onDelete}>
            <Trash2 size={14} />
            删除结果
          </button>
        )}
      </div>
    </article>
  );
}
