import { useEffect, useState } from 'react';
import { AlertTriangle, RotateCcw, Waves } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { getCurrentRoute, replanRoute, simulateTraffic, resetTraffic } from '../services/api';
import { useTrafficStatus } from '../services/TrafficStatusContext';

const metricFields = [
  { key: 'distance_km', label: 'Distance', unit: 'km', digits: 2 },
  { key: 'travel_time_minutes', label: 'Travel time', unit: 'min', digits: 1 },
  { key: 'fuel_liters', label: 'Fuel', unit: 'L', digits: 2 },
] as const;

function formatMetric(value: unknown, digits: number) {
  return typeof value === 'number' && Number.isFinite(value) ? value.toFixed(digits) : '—';
}

export function TrafficSimulatorPage() {
  const [level, setLevel] = useState('moderate');
  const [fraction, setFraction] = useState(0.25);
  const [route, setRoute] = useState<any>(null);
  const [completed, setCompleted] = useState<number[]>([]);
  const [replannedMetrics, setReplannedMetrics] = useState<any>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { status, updateStatus } = useTrafficStatus();

  useEffect(() => {
    const loadStatus = async () => {
      try {
        const currentRoute = await getCurrentRoute();
        if (currentRoute.status === 'empty') {
          setRoute(null);
          setCompleted([]);
        } else {
          setRoute(currentRoute);
          setCompleted(currentRoute.completed_stop_indices || []);
          if (currentRoute.mode === 'dynamic') setReplannedMetrics(currentRoute);
        }
      } catch (requestError) {
        setError(requestError instanceof Error ? requestError.message : 'Unable to load current route');
      }
    };
    void loadStatus();
  }, []);

  const applyTraffic = async () => {
    setLoading(true);
    setError('');
    try {
      const trafficResult = await simulateTraffic(level, fraction);
      updateStatus(trafficResult);
      if (route && route.sequence?.some((entry: any) => entry.type === 'stop')) {
        const result = await replanRoute(completed, {
          mileage_km_per_litre: 12,
          traffic_factor: 1,
          congestion_multiplier: 1,
        });
        setRoute({ status: 'ready', ...result });
        setCompleted(result.completed_stop_indices || completed);
        setReplannedMetrics(result);
      }
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Unable to apply traffic changes');
    } finally {
      setLoading(false);
    }
  };

  const reset = async () => {
    setError('');
    try {
      const result = await resetTraffic();
      updateStatus(result);
      if (route && route.sequence?.some((entry: any) => entry.type === 'stop')) {
        const replanned = await replanRoute(completed, {
          mileage_km_per_litre: 12,
          traffic_factor: 1,
          congestion_multiplier: 1,
        });
        setRoute({ status: 'ready', ...replanned });
        setCompleted(replanned.completed_stop_indices || completed);
        setReplannedMetrics(replanned);
      }
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Unable to reset traffic');
    }
  };

  const allDeliveries = route?.original_route?.sequence?.filter((entry: any) => entry.type === 'stop')
    || route?.sequence?.filter((entry: any) => entry.type === 'stop')
    || [];

  return (
    <div className="space-y-6">
      <div className="page-header">
        <div>
          <div className="page-kicker">Dispatch center · Scenario testing</div>
          <h1 className="page-title">Traffic simulator</h1>
          <p className="page-description">Model road congestion and see its effect on your active route.</p>
        </div>
        <div className="flex items-center gap-2 rounded-full border border-cyan-200 bg-cyan-50 px-3 py-1.5 text-xs font-bold text-cyan-800">
          <Waves className="h-3.5 w-3.5" /> Simulation available
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1fr_0.8fr]">
        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="rounded-xl bg-amber-50 p-2.5 text-amber-700"><Waves className="h-4 w-4" /></div>
              <div><div className="page-kicker mb-1">Road conditions</div><CardTitle>Traffic controls</CardTitle></div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <label className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">Traffic severity</label>
              <select value={level} onChange={(event) => setLevel(event.target.value)} className="app-input h-11 w-full border px-3 text-sm">
                <option value="normal">Normal</option>
                <option value="moderate">Moderate</option>
                <option value="heavy">Heavy</option>
                <option value="severe">Severe</option>
              </select>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">Road share affected</label>
              <Input type="number" min={0.05} max={1} step={0.05} value={fraction} onChange={(event) => setFraction(Number(event.target.value))} />
              <p className="text-xs text-slate-400">Choose the share of the road network to simulate.</p>
            </div>

            <div className="flex flex-col gap-3 sm:flex-row">
              <Button className="brand-button min-h-11 flex-1" onClick={() => void applyTraffic()} disabled={loading}>
                Apply Traffic Changes & Recalculate Route
              </Button>
              <Button variant="outline" className="min-h-11" onClick={() => void reset()} disabled={loading}>
                <RotateCcw className="mr-2 h-4 w-4" /> Reset
              </Button>
            </div>
            {allDeliveries.length > 0 && (
              <div className="space-y-2 rounded-2xl border border-slate-100 bg-slate-50/70 p-4">
                <div className="flex items-center justify-between">
                  <div className="text-sm font-bold text-slate-800">Delivery progress</div>
                  <span className="text-xs font-semibold text-slate-500">{completed.length} of {allDeliveries.length} complete</span>
                </div>
                {allDeliveries.map((entry: any) => {
                  const isCompleted = completed.includes(entry.index);
                  return (
                    <label
                      key={entry.index}
                      className={`flex items-center gap-2 rounded-md p-2 text-sm ${
                        isCompleted
                          ? 'bg-emerald-50 text-emerald-800 line-through'
                            : 'bg-white text-slate-600'
                      }`}
                    >
                      <input
                        type="checkbox"
                        aria-label={`${entry.label || `Stop ${entry.index + 1}`} completed`}
                        checked={isCompleted}
                        disabled={isCompleted || loading}
                        onChange={(event) => setCompleted((current) => event.target.checked
                          ? [...current, entry.index]
                          : current.filter((index) => index !== entry.index))}
                      />
                      {entry.label || `Stop ${entry.index + 1}`}
                      {isCompleted && <span className="ml-auto font-medium no-underline">Completed</span>}
                    </label>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="rounded-xl bg-fuchsia-50 p-2.5 text-fuchsia-700"><AlertTriangle className="h-4 w-4" /></div>
              <div><div className="page-kicker mb-1">Current conditions</div><CardTitle>Traffic status</CardTitle></div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="rounded-2xl border border-slate-100 bg-slate-50/80 p-5">
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2 text-sm font-semibold text-slate-500">
                  <span className={`h-2.5 w-2.5 rounded-full ${status?.status && /heavy|severe/i.test(status.status) ? 'bg-amber-500' : 'bg-emerald-500'}`} />
                  <span>{status?.source === 'TomTom' && status.available ? 'Live traffic · TomTom' : 'Simulated traffic'}</span>
                </div>
                <span className="rounded-full bg-white px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide text-slate-500">Backend status</span>
              </div>
              <div className="mt-4 font-['Poppins'] text-3xl font-semibold capitalize">{status?.status || 'Loading…'}</div>
              <p className="mt-2 text-sm text-slate-500">{status?.message || (status ? 'Traffic state is synchronized with the backend.' : 'Traffic status is loading from the backend.')}</p>
            </div>
            {error && <div role="alert" className="mt-4 text-sm text-red-600">{error}</div>}
            {replannedMetrics?.metrics && (
              <div className="mt-4 rounded-2xl border border-slate-100 bg-white p-4 text-sm">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="font-bold text-slate-800">Replanned route comparison</div>
                  <span className="text-[10px] font-bold uppercase tracking-wide text-slate-400">Backend results</span>
                </div>
                {replannedMetrics.previous_metrics ? (
                  <>
                    <div className="mt-3 grid gap-3 sm:grid-cols-2">
                      {[
                        { label: 'Previous route', metrics: replannedMetrics.previous_metrics },
                        { label: 'Updated route', metrics: replannedMetrics.metrics },
                      ].map(({ label, metrics }) => (
                        <div key={label} className={`rounded-xl border p-3 ${label === 'Updated route' ? 'border-fuchsia-100 bg-fuchsia-50/40' : 'border-slate-100 bg-slate-50/70'}`}>
                          <div className="mb-2 text-xs font-bold text-slate-600">{label}</div>
                          <div className="grid grid-cols-3 gap-2">
                            {metricFields.map((field) => (
                              <div key={field.key}>
                                <div className="text-[9px] font-bold uppercase tracking-wide text-slate-400">{field.label}</div>
                                <div className="numeric mt-1 text-xs font-bold text-slate-800">{formatMetric(metrics[field.key], field.digits)} <span className="font-sans font-medium text-slate-500">{field.unit}</span></div>
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                    <div className="mt-3 grid gap-2 sm:grid-cols-3">
                      {metricFields.map((field) => {
                        const previous = replannedMetrics.previous_metrics[field.key];
                        const updated = replannedMetrics.metrics[field.key];
                        const delta = typeof previous === 'number' && typeof updated === 'number'
                          ? updated - previous
                          : null;
                        const deltaLabel = delta == null
                          ? 'Change unavailable'
                          : delta === 0
                            ? 'No change'
                            : `${delta > 0 ? '+' : '−'}${Math.abs(delta).toFixed(field.digits)} ${field.unit} vs previous`;
                        return (
                          <div key={field.key} className="rounded-lg bg-slate-50 px-3 py-2">
                            <div className="text-[9px] font-bold uppercase tracking-wide text-slate-400">{field.label} change</div>
                            <div className="numeric mt-1 text-xs font-bold text-fuchsia-800">{deltaLabel}</div>
                          </div>
                        );
                      })}
                    </div>
                  </>
                ) : (
                  <div className="mt-3 grid grid-cols-3 gap-2 rounded-xl bg-fuchsia-50/40 p-3">
                    {metricFields.map((field) => (
                      <div key={field.key}>
                        <div className="text-[9px] font-bold uppercase tracking-wide text-slate-400">{field.label}</div>
                        <div className="numeric mt-1 text-xs font-bold">{formatMetric(replannedMetrics.metrics[field.key], field.digits)} {field.unit}</div>
                      </div>
                    ))}
                  </div>
                )}
                {completed.length > 0 && (
                  <div className="mt-3 rounded-lg border border-emerald-100 bg-emerald-50/60 px-3 py-2">
                    <div className="text-xs font-bold text-emerald-800">{completed.length} {completed.length === 1 ? 'completed delivery excluded' : 'completed deliveries excluded'}</div>
                    <div className="mt-1 text-[11px] text-emerald-700">{completed.map((index) => `Stop ${index + 1}`).join(', ')}</div>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
