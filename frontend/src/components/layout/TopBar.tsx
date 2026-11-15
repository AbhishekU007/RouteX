import { Activity, Bell, MapPin } from 'lucide-react';

export function TopBar({ city, trafficStatus }: { city: string; trafficStatus?: string }) {
  const isHeavy = Boolean(trafficStatus && /heavy|severe/i.test(trafficStatus));
  return (
    <header className="app-topbar">
      <div className="flex min-w-0 items-center gap-2 text-sm text-slate-500">
        <MapPin className="h-4 w-4 shrink-0 text-fuchsia-600" />
        <span className="max-w-[34vw] truncate font-bold text-slate-800 sm:max-w-none">{city}</span>
      </div>

      <div className="flex shrink-0 items-center gap-2 sm:gap-3">
        <div className={`flex items-center gap-1.5 rounded-full border px-2 py-1.5 text-[10px] font-bold sm:gap-2 sm:px-3 sm:text-xs ${isHeavy ? 'border-amber-200 bg-amber-50 text-amber-800' : 'border-emerald-200 bg-emerald-50 text-emerald-800'}`}>
          <Activity className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">{trafficStatus || 'Simulation mode'}</span>
          <span className="capitalize sm:hidden">{trafficStatus?.split('·').pop()?.replace('traffic', '').trim() || 'Traffic'}</span>
        </div>
        <button className="rounded-full border border-slate-200 p-2 text-slate-500 transition hover:border-fuchsia-200 hover:bg-fuchsia-50 hover:text-fuchsia-700" aria-label="Notifications">
          <Bell className="h-4 w-4" />
        </button>
        <div className="hidden h-9 w-9 items-center justify-center rounded-full bg-fuchsia-100 font-['Poppins'] text-xs font-bold text-fuchsia-800 sm:flex" aria-label="Profile placeholder">RX</div>
      </div>
    </header>
  );
}
