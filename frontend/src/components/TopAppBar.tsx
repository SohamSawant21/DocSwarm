export function TopAppBar({ onReset }: { onReset?: () => void }) {
  return (
    <header className="fixed top-0 inset-x-0 border-b border-[#E5E5E1] flex justify-between items-center w-full px-8 h-14 bg-[#FBFBFA] z-50">
      <div className="flex items-center gap-4">
        <div className="text-xl font-semibold font-serif tracking-tight text-slate-900">
          DocSwarm
        </div>
      </div>
      <div className="flex items-center gap-2">
        {onReset && (
          <button
            onClick={onReset}
            className="mr-2 bg-primary text-on-primary hover:bg-[#002d94] transition-colors ease-in-out duration-200 px-4 py-1.5 rounded-md font-ui-label text-[13px] flex items-center gap-2 shadow-sm"
          >
            <span className="material-symbols-outlined text-[16px]">upload_file</span>
            Upload New Repository
          </button>
        )}
        <button className="text-slate-500 hover:bg-[#F1F1EF] transition-colors ease-in-out duration-200 p-2 rounded-full flex items-center justify-center">
          <span className="material-symbols-outlined text-[20px]">help</span>
        </button>
        <button className="text-slate-500 hover:bg-[#F1F1EF] transition-colors ease-in-out duration-200 p-2 rounded-full flex items-center justify-center">
          <span className="material-symbols-outlined text-[20px]">settings</span>
        </button>
      </div>
    </header>
  );
}
