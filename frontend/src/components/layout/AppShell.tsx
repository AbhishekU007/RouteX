import { useEffect, useState, type ReactNode } from 'react';
import { Menu } from 'lucide-react';
import { AppSidebar } from './AppSidebar';
import { TopBar } from './TopBar';

export function AppShell({ children, city, trafficStatus }: { children: ReactNode; city: string; trafficStatus?: string }) {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const mediaQuery = window.matchMedia('(max-width: 767px)');
    const updateViewport = () => setIsMobile(mediaQuery.matches);
    updateViewport();
    mediaQuery.addEventListener('change', updateViewport);
    return () => mediaQuery.removeEventListener('change', updateViewport);
  }, []);

  return (
    <div className="app-shell flex">
      {isMobile && mobileOpen && <button className="sidebar-backdrop" onClick={() => setMobileOpen(false)} aria-label="Close navigation" />}
      <AppSidebar
        collapsed={!isMobile && collapsed}
        mobileOpen={isMobile && mobileOpen}
        onNavigate={() => setMobileOpen(false)}
      />
      <div className="app-main flex min-h-screen flex-col">
        <div className="app-topline">
          <button
            className="rounded-lg p-2 text-slate-500 transition hover:bg-fuchsia-50 hover:text-fuchsia-700"
            onClick={() => isMobile ? setMobileOpen((value) => !value) : setCollapsed((value) => !value)}
            aria-label="Toggle navigation"
          >
            <Menu className="h-5 w-5" />
          </button>
          <span className="ml-2 text-xs font-semibold tracking-wide text-slate-400 sm:hidden">ROUTEX OPERATIONS</span>
        </div>
        <TopBar city={city} trafficStatus={trafficStatus} />
        <main className="flex-1 overflow-y-auto">
          <div className="app-content">{children}</div>
        </main>
      </div>
    </div>
  );
}
