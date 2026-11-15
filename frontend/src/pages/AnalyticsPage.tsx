import { useEffect, useState } from 'react';
import { BarChart3 } from 'lucide-react';
import { Area, AreaChart, Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { getAnalytics } from '../services/api';

export function AnalyticsPage() {
  const [analytics, setAnalytics] = useState<any>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    const loadAnalytics = async () => {
      try {
        const result = await getAnalytics();
        setAnalytics(result);
        setError('');
      } catch (requestError) {
        setError(requestError instanceof Error ? requestError.message : 'Unable to load analytics');
      }
    };
    loadAnalytics();
    const timer = window.setInterval(loadAnalytics, 12000);
    return () => window.clearInterval(timer);
  }, []);

  const chartData = analytics?.history?.map((entry: any, index: number) => ({
    name: `Run ${index + 1}`,
    distance: entry.metrics?.distance_km,
    time: entry.metrics?.travel_time_minutes,
    fuel: entry.metrics?.fuel_liters,
  })).filter((entry: any) => [entry.distance, entry.time, entry.fuel].every(
    (value) => typeof value === 'number' && Number.isFinite(value),
  )) || [];
  const convergenceData = analytics?.active_route?.history?.map((cost: number, index: number) => ({
    iteration: index + 1,
    cost,
  })) || [];
  const original = analytics?.original_complete_route;
  const active = analytics?.active_route;
  const replanned = analytics?.replanned_route;
  const normal = analytics?.normal_traffic_baseline;
  const congested = analytics?.simulated_congestion_scenario;

  const RouteMetrics = ({ route }: { route: any }) => route?.metrics ? (
    <div className="mt-2 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
      {route.metrics.distance_km != null && <div><span className="text-slate-500">Distance</span><div className="font-medium">{route.metrics.distance_km.toFixed(2)} km</div></div>}
      {route.metrics.travel_time_minutes != null && <div><span className="text-slate-500">Time</span><div className="font-medium">{route.metrics.travel_time_minutes.toFixed(1)} min</div></div>}
      {route.metrics.fuel_liters != null && <div><span className="text-slate-500">Fuel</span><div className="font-medium">{route.metrics.fuel_liters.toFixed(2)} L</div></div>}
      {route.metrics.combined_cost != null && <div><span className="text-slate-500">Objective</span><div className="font-medium">{route.metrics.combined_cost.toFixed(3)}</div></div>}
    </div>
  ) : <div className="mt-2 text-sm text-slate-500">No stored result.</div>;

  return (
    <div className="space-y-6">
      <div className="page-header">
        <div>
          <div className="page-kicker">Dispatch center · Performance</div>
          <h1 className="page-title">Analytics</h1>
          <p className="page-description">Compare stored route outcomes and review optimization progress.</p>
        </div>
        <div className="rounded-full border border-fuchsia-100 bg-fuchsia-50 px-3 py-1.5 text-xs font-bold text-fuchsia-800">Backend results only</div>
      </div>

      {error && <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}

      <Card>
        <CardHeader>
          <div className="page-kicker mb-1">Route comparisons</div>
          <CardTitle>Stored route scenarios</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-2xl border border-fuchsia-100 bg-fuchsia-50/30 p-4">
            <div className="font-medium">Original complete route</div>
            <RouteMetrics route={original} />
          </div>
          <div className="rounded-2xl border border-slate-100 bg-white p-4">
            <div className="font-medium">Active remaining route</div>
            <RouteMetrics route={active} />
            {active?.completed_stop_indices?.length > 0 && (
              <p className="mt-2 text-xs text-slate-500">Completed deliveries: {active.completed_stop_indices.map((index: number) => index + 1).join(', ')}</p>
            )}
          </div>
          <div className="rounded-2xl border border-cyan-100 bg-cyan-50/20 p-4">
            <div className="font-medium">Replanned route</div>
            <RouteMetrics route={replanned} />
          </div>
          <div className="rounded-2xl border border-slate-100 bg-white p-4">
            <div className="font-medium">Normal traffic baseline</div>
            <RouteMetrics route={normal} />
          </div>
          <div className="rounded-2xl border border-amber-100 bg-amber-50/30 p-4">
            <div className="font-medium">
              Simulated congestion scenario
              {congested?.traffic_status?.status && <span className="ml-2 text-xs font-normal capitalize text-slate-500">{congested.traffic_status.status}</span>}
            </div>
            <RouteMetrics route={congested?.route} />
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-500">Distance</CardTitle>
            <BarChart3 className="h-4 w-4 text-slate-500" />
          </CardHeader>
          <CardContent>
            <div className="numeric text-2xl font-bold">{analytics?.distance_km != null ? `${analytics.distance_km.toFixed(2)} km` : '—'}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-500">Travel time</CardTitle>
            <BarChart3 className="h-4 w-4 text-slate-500" />
          </CardHeader>
          <CardContent>
            <div className="numeric text-2xl font-bold">{analytics?.travel_time_minutes != null ? `${analytics.travel_time_minutes.toFixed(1)} min` : '—'}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-500">Fuel</CardTitle>
            <BarChart3 className="h-4 w-4 text-slate-500" />
          </CardHeader>
          <CardContent>
            <div className="numeric text-2xl font-bold">{analytics?.fuel_liters != null ? `${analytics.fuel_liters.toFixed(2)} L` : '—'}</div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <div className="page-kicker mb-1">Optimization process</div>
            <CardTitle>ACO objective convergence</CardTitle>
          </CardHeader>
          <CardContent className={convergenceData.length ? 'h-80' : ''}>
            {convergenceData.length ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={convergenceData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#eeeaf3" />
                  <XAxis dataKey="iteration" tickLine={false} axisLine={false} tick={{ fill: '#8a8797', fontSize: 11 }} />
                  <YAxis tickLine={false} axisLine={false} tick={{ fill: '#8a8797', fontSize: 11 }} />
                  <Tooltip contentStyle={{ borderRadius: 12, borderColor: '#eceaf1', boxShadow: '0 12px 32px rgba(38,22,56,.08)' }} />
                  <Area type="monotone" dataKey="cost" name="Best objective cost" stroke="#d946ef" fill="#f5d0fe" strokeWidth={2.5} />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-start gap-3 rounded-xl border border-dashed border-fuchsia-200 bg-fuchsia-50/40 p-4">
                <div className="rounded-lg bg-white p-2 text-fuchsia-700"><BarChart3 className="h-4 w-4" /></div>
                <div>
                  <div className="text-sm font-bold text-slate-700">No convergence history yet</div>
                  <p className="mt-1 text-xs leading-relaxed text-slate-500">Run an optimization to see the backend’s objective cost across ACO iterations.</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="page-kicker mb-1">History</div>
            <CardTitle>Stored route performance</CardTitle>
          </CardHeader>
          <CardContent className={chartData.length ? 'h-80' : ''}>
            {chartData.length ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#eeeaf3" />
                  <XAxis dataKey="name" tickLine={false} axisLine={false} tick={{ fill: '#8a8797', fontSize: 11 }} />
                  <YAxis tickLine={false} axisLine={false} tick={{ fill: '#8a8797', fontSize: 11 }} />
                  <Tooltip contentStyle={{ borderRadius: 12, borderColor: '#eceaf1', boxShadow: '0 12px 32px rgba(38,22,56,.08)' }} />
                  <Bar dataKey="time" name="Travel time" fill="#22d3ee" radius={[5, 5, 0, 0]} />
                  <Bar dataKey="fuel" name="Fuel" fill="#facc15" radius={[5, 5, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-start gap-3 rounded-xl border border-dashed border-cyan-200 bg-cyan-50/40 p-4">
                <div className="rounded-lg bg-white p-2 text-cyan-700"><BarChart3 className="h-4 w-4" /></div>
                <div>
                  <div className="text-sm font-bold text-slate-700">No route comparisons yet</div>
                  <p className="mt-1 text-xs leading-relaxed text-slate-500">After optimization runs, this chart compares stored travel time and fuel results.</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
