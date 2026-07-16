export default function LoadingSpinner({
  message = "Processing...",
  progress,
}: {
  message?: string;
  progress?: string;
}) {
  return (
    <div className="flex flex-col items-center gap-5 py-12">
      <div className="relative w-12 h-12">
        <div className="absolute inset-0 border-[3px] border-surface-200 rounded-full" />
        <div className="absolute inset-0 border-[3px] border-transparent border-t-brand-600 rounded-full animate-spin" />
      </div>
      <div className="text-center">
        <p className="font-semibold text-surface-800">{message}</p>
        {progress && <p className="text-sm text-surface-400 mt-1">{progress}</p>}
      </div>
    </div>
  );
}
