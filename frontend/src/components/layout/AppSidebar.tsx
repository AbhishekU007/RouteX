import { BarChart3, Gauge, Map, Navigation, Settings, Truck, Waves } from 'lucide-react';
import { NavLink } from 'react-router-dom';
import { cn } from '../../lib/utils';

const items = [
  { label: 'Overview', to: '/', icon: Gauge },
  { label: 'Route Planner', to: '/planner', icon: Navigation },
  { label: 'Live Map', to: '/map', icon: Map },
  { label: 'Traffic Simulator', to: '/traffic', icon: Waves },
  { label: 'Analytics', to: '/analytics', icon: BarChart3 },
  { label: 'Settings', to: '/settings', icon: Settings },
];

export function AppSidebar({ collapsed, mobileOpen, onNavigate }: { collapsed: boolean; mobileOpen: boolean; onNavigate: () => void }) {
  return (
    <aside className={cn('app-sidebar', collapsed ? 'w-[76px]' : 'w-[252px]', mobileOpen && 'mobile-open')}>
      <div className={cn('flex min-h-[88px] items-center gap-3 border-b border-slate-100 px-5', collapsed && 'justify-center px-3')}>
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[14px] bg-fuchsia-100 text-fuchsia-700">
          <Truck className="h-5 w-5" strokeWidth={2.5} />
        </div>
        {!collapsed && <div><div className="font-['Poppins'] text-[17px] font-bold tracking-tight">Route<span className="text-fuchsia-600">X</span></div><div className="text-[11px] font-semibold tracking-wide text-slate-400">LOGISTICS CONTROL</div></div>}
      </div>

      {!collapsed && <div className="px-5 pb-2 pt-6 font-mono text-[9px] font-bold tracking-[0.16em] text-slate-400">WORKSPACE</div>}
      <nav className={cn('flex-1 space-y-1 px-3 py-2', collapsed && 'pt-5')}>
        {items.map(({ label, to, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            title={collapsed ? label : undefined}
            onClick={onNavigate}
            className={({ isActive }) => cn('nav-link', isActive && 'nav-link-active', collapsed && 'justify-center px-0')}
          >
            <Icon className="h-[18px] w-[18px] shrink-0" strokeWidth={2.1} />
            {!collapsed && <span>{label}</span>}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-slate-100 p-4 text-xs text-slate-500">
        {!collapsed ? (
          <div className="rounded-xl bg-slate-50 p-3">
            <div className="mb-2 font-semibold text-slate-600">Application status</div>
            <div className="flex items-center gap-2 font-semibold text-slate-700"><span className="h-2 w-2 rounded-full bg-emerald-500" />Operational</div>
            <div className="mt-2 font-mono text-[10px] text-slate-400">ROUTEX · v0.1.0</div>
          </div>
        ) : (
          <div className="flex justify-center"><span className="h-2 w-2 rounded-full bg-emerald-500" title="Operational" /></div>
        )}
      </div>
    </aside>
  );
}
