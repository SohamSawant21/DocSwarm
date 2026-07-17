export function SideNav() {
  return (
    <nav className="fixed left-0 top-14 flex flex-col justify-between py-6 z-40 h-[calc(100vh-3.5rem)] bg-surface text-sm tracking-wide w-16 hover:w-60 border-r border-outline-variant transition-all duration-300 group overflow-hidden">
      <div className="flex flex-col gap-2 w-full mt-4">
        <a
          className="flex items-center gap-4 px-4 py-3 text-on-surface-variant border-l-2 border-transparent hover:text-on-surface hover:bg-surface-variant w-full whitespace-nowrap overflow-hidden transition-colors"
          href="#"
        >
          <span className="material-symbols-outlined flex-shrink-0">description</span>
          <span className="opacity-0 group-hover:opacity-100 group-hover:translate-x-1 transition-all duration-200 font-ui-label text-ui-label transform -translate-x-2">
            AI Docs
          </span>
        </a>
        <a
          className="flex items-center gap-4 px-4 py-3 border-l-2 border-primary text-primary bg-surface-container w-full whitespace-nowrap overflow-hidden transition-colors"
          href="#"
        >
          <span className="material-symbols-outlined flex-shrink-0">account_tree</span>
          <span className="opacity-0 group-hover:opacity-100 group-hover:translate-x-1 transition-all duration-200 font-ui-label text-ui-label transform -translate-x-2">
            DocGraph
          </span>
        </a>
      </div>
      <div className="flex flex-col gap-2 w-full mb-4">
        <a
          className="flex items-center gap-4 px-4 py-3 text-on-surface-variant border-l-2 border-transparent hover:text-on-surface hover:bg-surface-variant w-full whitespace-nowrap overflow-hidden transition-colors"
          href="#"
        >
          <span className="material-symbols-outlined flex-shrink-0">person</span>
          <span className="opacity-0 group-hover:opacity-100 group-hover:translate-x-1 transition-all duration-200 font-ui-label text-ui-label transform -translate-x-2">
            Profile
          </span>
        </a>
      </div>
    </nav>
  );
}
