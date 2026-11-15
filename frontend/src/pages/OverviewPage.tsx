import { useEffect, useState, type CSSProperties } from 'react';
import { Activity, ArrowRight, Clock3, Route, Truck, Waves } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { getAnalytics, getCurrentRoute } from '../services/api';
import { useTrafficStatus } from '../services/TrafficStatusContext';

export function OverviewPage() {
  const [route, setRoute] = useState<any>(null);
  const [analytics, setAnalytics] = useState<any>(null);
  const { status: traffic } = useTrafficStatus();

  useEffect(() => {
    const loadOverview = async () => {
      try {
        const [currentRoute, analyticsData] = await Promise.all([
          getCurrentRoute(),
          getAnalytics(),
        ]);
        setRoute(currentRoute);
        setAnalytics(analyticsData);
      } catch {
        // keep empty states if backend is not ready yet
      }
    };

    loadOverview();
    const timer = window.setInterval(loadOverview, 10000);
    return () => window.clearInterval(timer);
  }, []);

  const metrics = route?.metrics || {};
  const hasRouteResult = [
    metrics.distance_km,
    metrics.travel_time_minutes,
    metrics.fuel_liters,
  ].every((value) => typeof value === 'number' && Number.isFinite(value));
  const stopCount = hasRouteResult ? route?.sequence?.filter((item: any) => item.type === 'stop').length || 0 : 0;
  const isHeavy = Boolean(traffic?.status && /heavy|severe/i.test(traffic.status));

  return (
    <div className="space-y-6">
      <div className="page-header">
        <div>
          <div className="page-kicker">Dispatch center · Overview</div>
          <h1 className="page-title">Operations overview</h1>
          <p className="page-description">A clear view of your routes, deliveries, and traffic conditions.</p>
        </div>
        <Link to="/planner">
          <Button className="brand-button gap-2">
            Plan new route <ArrowRight className="h-4 w-4" />
          </Button>
        </Link>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card className="metric-card" style={{ '--metric-tint': 'rgba(217,70,239,.10)' } as CSSProperties}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-500">Delivery locations</CardTitle>
            <div className="rounded-xl bg-fuchsia-50 p-2 text-fuchsia-700"><Route className="h-4 w-4" /></div>
          </CardHeader>
          <CardContent>
            <div className="numeric text-2xl font-bold">{hasRouteResult ? stopCount : '—'}</div>
            <p className="mt-1 text-xs text-slate-500">{hasRouteResult ? 'Stops on the active route' : 'No route generated yet'}</p>
          </CardContent>
        </Card>

        <Card className="metric-card" style={{ '--metric-tint': 'rgba(34,211,238,.12)' } as CSSProperties}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-500">Vehicle status</CardTitle>
            <div className="rounded-xl bg-cyan-50 p-2 text-cyan-700"><Truck className="h-4 w-4" /></div>
          </CardHeader>
          <CardContent>
            <div className="text-xl font-bold">{hasRouteResult ? 'Route active' : 'Awaiting route'}</div>
            <p className="mt-1 text-xs text-slate-500">{hasRouteResult ? 'Single vehicle · route assigned' : 'Plan a route to get started'}</p>
          </CardContent>
        </Card>

        <Card className="metric-card" style={{ '--metric-tint': 'rgba(250,204,21,.14)' } as CSSProperties}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-500">Last optimized route</CardTitle>
            <div className="rounded-xl bg-amber-50 p-2 text-amber-700"><Activity className="h-4 w-4" /></div>
          </CardHeader>
          <CardContent>
            <div className="numeric text-xl font-bold">{metrics.distance_km ? `${metrics.distance_km.toFixed(1)} km` : '—'}</div>
            <p className="mt-1 text-xs text-slate-500">{metrics.distance_km ? 'Latest total distance' : 'No optimization yet'}</p>
          </CardContent>
        </Card>

        <Card className="metric-card" style={{ '--metric-tint': isHeavy ? 'rgba(251,191,36,.18)' : 'rgba(16,185,129,.10)' } as CSSProperties}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-500">Traffic condition</CardTitle>
            <div className={`rounded-xl p-2 ${isHeavy ? 'bg-amber-50 text-amber-700' : 'bg-emerald-50 text-emerald-700'}`}><Waves className="h-4 w-4" /></div>
          </CardHeader>
          <CardContent>
            <div className="text-xl font-bold capitalize">{traffic?.status || 'Loading'}</div>
            <p className="mt-1 text-xs text-slate-500">{traffic?.source === 'TomTom' && traffic.available ? 'Live traffic source' : 'Simulated traffic source'}</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.3fr_0.7fr]">
        <Card className="overflow-hidden">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div><div className="page-kicker mb-1">Route performance</div><CardTitle>Latest optimization</CardTitle></div>
              <Clock3 className="h-5 w-5 text-fuchsia-500" />
            </div>
          </CardHeader>
          <CardContent>
            {hasRouteResult ? (
              <div className="space-y-5">
                <div className="grid gap-4 sm:grid-cols-3">
                  <div>
                    <div className="text-xs font-bold uppercase tracking-[0.14em] text-slate-400">Distance</div>
                    <div className="numeric mt-2 text-2xl font-bold">{metrics.distance_km?.toFixed(2) || '0.00'} <span className="text-sm font-medium text-slate-500">km</span></div>
                  </div>
                  <div>
                    <div className="text-xs font-bold uppercase tracking-[0.14em] text-slate-400">Travel time</div>
                    <div className="numeric mt-2 text-2xl font-bold">{metrics.travel_time_minutes?.toFixed(1) || '0.0'} <span className="text-sm font-medium text-slate-500">min</span></div>
                  </div>
                  <div>
                    <div className="text-xs font-bold uppercase tracking-[0.14em] text-slate-400">Fuel</div>
                    <div className="numeric mt-2 text-2xl font-bold">{metrics.fuel_liters?.toFixed(2) || '0.00'} <span className="text-sm font-medium text-slate-500">L</span></div>
                  </div>
                </div>
                {route.sequence?.length > 1 && (
                  <div className="border-t border-slate-100 pt-4">
                    <div className="mb-3 flex items-center justify-between gap-2">
                      <span className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">Active route sequence</span>
                      <span className="text-xs font-semibold text-slate-400">{stopCount} {stopCount === 1 ? 'delivery' : 'deliveries'}</span>
                    </div>
                    <div className="flex overflow-x-auto pb-1">
                      {route.sequence.map((entry: any, index: number) => {
                        const isDepot = entry.type === 'depot';
                        const isCurrent = entry.type === 'current';
                        const label = isDepot ? 'Depot' : isCurrent ? 'Current' : `Stop ${entry.index + 1}`;
                        return (
                          <div key={`${entry.position}-${entry.type}`} className="flex min-w-[74px] flex-1 items-start">
                            <div className="flex shrink-0 flex-col items-center gap-1.5">
                              <span className={`flex h-7 w-7 items-center justify-center rounded-full text-[10px] font-bold ${isDepot ? 'bg-fuchsia-100 text-fuchsia-800' : isCurrent ? 'bg-amber-100 text-amber-800' : 'bg-cyan-100 text-cyan-800'}`}>
                                {isDepot ? 'D' : isCurrent ? '•' : entry.index + 1}
                              </span>
                              <span className="text-[10px] font-semibold text-slate-500">{label}</span>
                            </div>
                            {index < route.sequence.length - 1 && <span className="mx-2 mt-3.5 h-px min-w-5 flex-1 bg-slate-200" />}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
                <Link to="/map" className="inline-flex items-center gap-2 text-sm font-bold text-fuchsia-700 hover:text-fuchsia-900">
                  View active route <ArrowRight className="h-4 w-4" />
                </Link>
              </div>
            ) : (
              <div className="rounded-2xl border border-dashed border-fuchsia-200 bg-fuchsia-50/40 p-8 text-center">
                <div className="mx-auto mb-3 flex h-11 w-11 items-center justify-center rounded-full bg-white text-fuchsia-600 shadow-sm"><Route className="h-5 w-5" /></div>
                <div className="font-bold text-slate-800">Your route activity will appear here</div>
                <p className="mt-1 text-sm text-slate-500">Create a route to see distance, estimated time, and fuel metrics.</p>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="page-kicker mb-1">Recent</div>
            <CardTitle>Route activity</CardTitle>
          </CardHeader>
          <CardContent>
            {analytics?.history?.length ? (
              <ul className="space-y-2.5">
                {analytics.history.slice(-4).reverse().map((entry: any, index: number) => (
                  <li key={`${entry.mode}-${index}`} className="rounded-xl border border-slate-100 bg-slate-50/70 p-3.5">
                    <div className="flex items-center justify-between">
                      <span className="font-medium capitalize">{entry.mode || 'route'}</span>
                      <span className="text-[11px] text-slate-400">{entry.timestamp || 'Recent'}</span>
                    </div>
                    <div className="numeric mt-2 text-xs text-slate-600">{entry.metrics?.distance_km?.toFixed(2) || '0.00'} km <span className="px-1 text-slate-300">/</span> {entry.metrics?.fuel_liters?.toFixed(2) || '0.00'} L</div>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="rounded-xl border border-dashed border-slate-200 p-6 text-sm text-slate-500">No route activity yet. Your completed optimizations will be listed here.</div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
