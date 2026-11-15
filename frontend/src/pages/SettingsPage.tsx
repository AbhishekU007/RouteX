import { Bell, CheckCircle2, ShieldCheck, SlidersHorizontal } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';

export function SettingsPage() {
  return (
    <div className="space-y-6">
      <div className="page-header">
        <div>
          <div className="page-kicker">Workspace · Configuration</div>
          <h1 className="page-title">Settings</h1>
          <p className="page-description">Review the defaults and connected capabilities for this RouteX workspace.</p>
        </div>
        <div className="flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-bold text-emerald-800">
          <CheckCircle2 className="h-3.5 w-3.5" /> System operational
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <div className="page-kicker mb-1">Preferences</div>
            <CardTitle>Operational defaults</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between rounded-xl border border-slate-100 bg-slate-50/70 p-4">
              <div className="flex items-center gap-3">
                <SlidersHorizontal className="h-4 w-4 text-slate-500" />
                <span>Advanced optimization defaults</span>
              </div>
              <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-bold text-emerald-700">Enabled</span>
            </div>
            <div className="flex items-center justify-between rounded-xl border border-slate-100 bg-slate-50/70 p-4">
              <div className="flex items-center gap-3">
                <Bell className="h-4 w-4 text-slate-500" />
                <span>Traffic alerts</span>
              </div>
              <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-bold text-emerald-700">On</span>
            </div>
            <div className="flex items-center justify-between rounded-xl border border-slate-100 bg-slate-50/70 p-4">
              <div className="flex items-center gap-3">
                <ShieldCheck className="h-4 w-4 text-slate-500" />
                <span>Simulation fallback</span>
              </div>
              <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-bold text-emerald-700">Active</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="page-kicker mb-1">Connected capabilities</div>
            <CardTitle>Environment status</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm text-slate-600">
            <div className="rounded-xl border border-amber-100 bg-amber-50/40 p-4"><span className="font-bold text-slate-800">Live traffic</span><p className="mt-1">TomTom traffic-to-road integration is not implemented; simulation is available.</p></div>
            <div className="rounded-xl border border-emerald-100 bg-emerald-50/40 p-4"><span className="font-bold text-slate-800">Optimization engine</span><p className="mt-1">Python-based Ant Colony Optimization backend.</p></div>
            <div className="rounded-xl border border-cyan-100 bg-cyan-50/40 p-4"><span className="font-bold text-slate-800">Map tiles</span><p className="mt-1">OpenStreetMap tiles are used for route visualization.</p></div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
