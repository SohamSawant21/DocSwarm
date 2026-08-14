import Link from 'next/link';
import { usePathname } from 'next/navigation';

export function SideNav() {
  const pathname = usePathname();

  return (
    <nav className="fixed left-0 top-14 flex flex-col justify-between py-6 z-40 h-[calc(100vh-3.5rem)] bg-surface text-sm tracking-wide w-16 hover:w-60 border-r border-outline-variant transition-all duration-300 group overflow-hidden">
      <div className="flex flex-col gap-2 w-full mt-4">
        <Link
          href="/docs"
          className={`flex items-center gap-4 px-4 py-3 border-l-2 w-full whitespace-nowrap overflow-hidden transition-colors ${pathname === '/docs' ? 'border-primary text-primary bg-surface-container' : 'text-on-surface-variant border-transparent hover:text-on-surface hover:bg-surface-variant'}`}
        >
          <span className="material-symbols-outlined flex-shrink-0">description</span>
          <span className="opacity-0 group-hover:opacity-100 group-hover:translate-x-1 transition-all duration-200 font-ui-label text-ui-label transform -translate-x-2">
            AI Docs
          </span>
        </Link>
        <Link
          href="/dashboard"
          className={`flex items-center gap-4 px-4 py-3 border-l-2 w-full whitespace-nowrap overflow-hidden transition-colors ${pathname === '/dashboard' ? 'border-primary text-primary bg-surface-container' : 'text-on-surface-variant border-transparent hover:text-on-surface hover:bg-surface-variant'}`}
        >
          <span className="material-symbols-outlined flex-shrink-0">account_tree</span>
          <span className="opacity-0 group-hover:opacity-100 group-hover:translate-x-1 transition-all duration-200 font-ui-label text-ui-label transform -translate-x-2">
            DocGraph
          </span>
        </Link>
      </div>
    </nav>
  );
}
