export function SideNav() {
  return (
    <nav className="fixed left-0 top-14 flex flex-col justify-between py-6 z-40 h-[calc(100vh-3.5rem)] bg-[#FBFBFA] font-serif text-sm tracking-wide w-16 hover:w-60 border-r border-[#E5E5E1] transition-all duration-300 group overflow-hidden flat no shadows">
      <div className="flex flex-col gap-2 w-full mt-4">
        <a
          className="flex items-center gap-4 px-4 py-3 text-slate-500 border-l-2 border-transparent hover:text-slate-900 hover:bg-[#F1F1EF] w-full whitespace-nowrap overflow-hidden"
          href="#"
        >
          <span className="material-symbols-outlined flex-shrink-0">description</span>
          <span className="opacity-0 group-hover:opacity-100 transition-opacity font-ui-label text-ui-label">
            AI Docs
          </span>
        </a>
        <a
          className="flex items-center gap-4 px-4 py-3 border-l-2 border-blue-700 text-blue-700 bg-[#F1F1EF] w-full whitespace-nowrap overflow-hidden"
          href="#"
        >
          <span className="material-symbols-outlined flex-shrink-0">account_tree</span>
          <span className="opacity-0 group-hover:opacity-100 transition-opacity font-ui-label text-ui-label">
            DocGraph
          </span>
        </a>
      </div>
      <div className="flex flex-col gap-2 w-full mb-4">
        <a
          className="flex items-center gap-4 px-4 py-3 text-slate-500 border-l-2 border-transparent hover:text-slate-900 hover:bg-[#F1F1EF] w-full whitespace-nowrap overflow-hidden"
          href="#"
        >
          <span className="material-symbols-outlined flex-shrink-0">person</span>
          <span className="opacity-0 group-hover:opacity-100 transition-opacity font-ui-label text-ui-label">
            Profile
          </span>
        </a>
      </div>
    </nav>
  );
}
