import { useEffect, useState, type ChangeEvent } from 'react';
import Papa from 'papaparse';
import { AlertCircle, CheckCircle2, ChevronDown, ChevronRight, LoaderCircle, MapPinPlus, PackagePlus, Trash2, Upload } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { getNetworkStatus, loadNetwork, optimizeRoute, pollJob, saveLocations, type NetworkStatus } from '../services/api';
import { useTrafficStatus } from '../services/TrafficStatusContext';

const defaultConfig = {
  num_ants: 20,
  alpha: 1,
  beta: 3,
  evaporation_rate: 0.2,
  iterations: 40,
  distance_weight: 0.5,
  time_weight: 0.3,
  fuel_weight: 0.2,
  mileage_km_per_litre: 12,
  traffic_factor: 1,
  congestion_multiplier: 1,
};

const advancedGroups = [
  {
    title: 'ACO algorithm',
    fields: [
      { key: 'num_ants', label: 'Ant count', description: 'Number of candidate routes explored in each iteration.' },
      { key: 'alpha', label: 'Alpha', description: 'Influence of pheromone strength when choosing the next location.' },
      { key: 'beta', label: 'Beta', description: 'Influence of route desirability when choosing the next location.' },
      { key: 'evaporation_rate', label: 'Evaporation rate', description: 'Share of pheromone strength removed each iteration.' },
      { key: 'iterations', label: 'Iteration count', description: 'Number of optimization cycles to run.' },
    ],
  },
  {
    title: 'Objective weights',
    fields: [
      { key: 'distance_weight', label: 'Distance weight', description: 'Relative importance of route distance in the objective.' },
      { key: 'time_weight', label: 'Travel-time weight', description: 'Relative importance of estimated travel time in the objective.' },
      { key: 'fuel_weight', label: 'Fuel weight', description: 'Relative importance of estimated fuel consumption in the objective.' },
    ],
  },
  {
    title: 'Traffic model',
    fields: [
      { key: 'traffic_factor', label: 'Traffic factor', description: 'Multiplier applied to travel time for traffic conditions.' },
      { key: 'congestion_multiplier', label: 'Congestion multiplier', description: 'Additional travel-time effect for congested roads.' },
    ],
  },
];

export function RoutePlannerPage() {
  const [city, setCity] = useState('Agra, Uttar Pradesh, India');
  const [depot, setDepot] = useState<[number, number]>([27.1767, 78.0081]);
  const [stops, setStops] = useState<[number, number][]>([
    [27.1779, 78.0101],
    [27.1754, 78.0130],
    [27.1733, 78.0076],
  ]);
  const [config, setConfig] = useState(defaultConfig);
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState('');
  const [networkStatus, setNetworkStatus] = useState<NetworkStatus | null>(null);
  const [networkError, setNetworkError] = useState('');
  const { refreshStatus } = useTrafficStatus();

  useEffect(() => {
    let active = true;
    getNetworkStatus()
      .then((status) => {
        if (active) setNetworkStatus(status);
      })
      .catch((error: unknown) => {
        if (active) setNetworkError(error instanceof Error ? error.message : 'Unable to check the loaded road network.');
      });
    return () => {
      active = false;
    };
  }, []);

  const handleLoadNetwork = async () => {
    setNetworkError('');
    try {
      const loadedNetwork = await loadNetwork(city, true);
      setNetworkStatus(loadedNetwork);
      await refreshStatus();
    } catch (error) {
      setNetworkError(error instanceof Error ? error.message : 'Unable to load road network');
    }
  };

  const updateStops = (index: number, next: [number, number]) => {
    setStops((current) => current.map((stop, i) => (i === index ? next : stop)));
  };

  const removeStop = (index: number) => {
    setStops((current) => current.filter((_, i) => i !== index));
  };

  const handleCsvImport = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    const text = await file.text();
    Papa.parse<Record<string, string>>(text, {
      header: true,
      skipEmptyLines: true,
      complete: (parsed: Papa.ParseResult<Record<string, string>>) => {
        const rows = parsed.data
          .map((row: Record<string, string>) => {
            const latitude = Number(row.latitude ?? row.lat ?? row.Latitude ?? row.Lat);
            const longitude = Number(row.longitude ?? row.lon ?? row.Longitude ?? row.Lng ?? row.Lon);
            if (Number.isFinite(latitude) && Number.isFinite(longitude)) return [latitude, longitude] as [number, number];
            return null;
          })
          .filter(Boolean) as [number, number][];
        if (rows.length > 0) setStops(rows);
      },
    });
  };

  const handleOptimize = async () => {
    if (
      networkStatus?.status !== 'ready'
      || networkStatus.city.trim().toLowerCase() !== city.trim().toLowerCase()
    ) {
      setMessage('Load the road network for the selected city before optimizing.');
      setProgress(0);
      return;
    }

    setLoading(true);
    setProgress(0);
    setMessage('Validating route inputs...');
    try {
      await saveLocations(depot, stops);
      const response = await optimizeRoute({
        city,
        depot,
        stops,
        config,
      });
      setMessage('Optimization queued...');
      let jobStatus = await pollJob(response.job_id);
      while (jobStatus.status === 'queued' || jobStatus.status === 'running') {
        setProgress(jobStatus.progress || 0);
        setMessage(jobStatus.message || 'Optimizing route...');
        await new Promise((resolve) => window.setTimeout(resolve, 1200));
        jobStatus = await pollJob(response.job_id);
      }
      if (jobStatus.status === 'completed') {
        setResult(jobStatus.result);
        setProgress(100);
        setMessage('Route optimized successfully.');
      } else {
        setMessage(jobStatus.message || 'Optimization failed');
      }
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Unable to optimize route');
    } finally {
      setLoading(false);
    }
  };

  const networkMatchesCity = networkStatus?.city.trim().toLowerCase() === city.trim().toLowerCase();
  const networkSource = networkStatus?.source === 'openstreetmap'
    ? 'OpenStreetMap'
    : networkStatus?.source === 'offline_fallback'
      ? 'offline fallback'
      : 'unknown source';

  return (
    <div className="space-y-6">
      <div className="page-header">
        <div>
          <div className="page-kicker">Dispatch center · Planning</div>
          <h1 className="page-title">Route planner</h1>
          <p className="page-description">Set your locations and vehicle details, then let RouteX plan the most efficient sequence.</p>
        </div>
        <div className="hidden items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-bold text-emerald-800 sm:flex">
          <span className="h-2 w-2 rounded-full bg-emerald-500" /> Python optimizer ready
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1fr_0.7fr]">
        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="rounded-xl bg-fuchsia-50 p-2.5 text-fuchsia-700"><MapPinPlus className="h-4 w-4" /></div>
              <div><div className="page-kicker mb-1">Step 01</div><CardTitle>Locations</CardTitle></div>
            </div>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="flex gap-3">
              <Input className="app-input" value={city} onChange={(event) => setCity(event.target.value)} placeholder="Operating city" />
              <Button variant="secondary" className="shrink-0" onClick={() => void handleLoadNetwork()}>
                Load network
              </Button>
            </div>
            <div
              role={networkError ? 'alert' : 'status'}
              aria-live="polite"
              className={`rounded-xl border p-3 text-xs ${
                networkError
                  ? 'border-red-100 bg-red-50/60 text-red-700'
                  : 'border-slate-100 bg-slate-50/80 text-slate-600'
              }`}
            >
              {networkError || (networkStatus
                ? `Loaded ${networkSource} network for ${networkStatus.city} · ${networkStatus.nodes} nodes · ${networkStatus.edges} road segments.`
                : 'Checking the loaded road network…')}
              {!networkError && networkStatus?.fallback_message && (
                <span className="mt-1 block">{networkStatus.fallback_message}</span>
              )}
              {!networkError && networkStatus && !networkMatchesCity && (
                <span className="mt-1 block font-semibold text-amber-700">
                  Load the selected city’s network before optimizing.
                </span>
              )}
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              <div className="space-y-2">
                <label className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">Depot latitude</label>
                <Input type="number" value={depot[0]} step="0.000001" onChange={(event) => setDepot([Number(event.target.value), depot[1]])} />
              </div>
              <div className="space-y-2">
                <label className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">Depot longitude</label>
                <Input type="number" value={depot[1]} step="0.000001" onChange={(event) => setDepot([depot[0], Number(event.target.value)])} />
              </div>
            </div>

            <div className="space-y-3 rounded-2xl bg-slate-50/80 p-4">
              <div className="flex items-center justify-between gap-2">
                <div>
                  <div className="font-bold text-slate-800">Delivery stops</div>
                  <p className="mt-0.5 text-xs text-slate-500">{stops.length} location{stops.length === 1 ? '' : 's'} added</p>
                </div>
                <Button variant="outline" size="sm" onClick={() => setStops((current) => [...current, [27.1750, 78.0090]])}>
                  <PackagePlus className="mr-2 h-4 w-4" /> Add stop
                </Button>
              </div>

              {stops.map((stop, index) => (
                <div key={`${index}-${stop[0]}-${stop[1]}`} className="grid gap-3 rounded-xl border border-slate-100 bg-white p-3 md:grid-cols-[auto_1fr_1fr_auto]">
                  <div className="flex h-9 w-9 items-center justify-center self-end rounded-full bg-fuchsia-100 font-mono text-xs font-bold text-fuchsia-800">{String(index + 1).padStart(2, '0')}</div>
                  <div>
                    <label className="mb-1 block text-[10px] font-bold uppercase tracking-[0.14em] text-slate-400">Latitude</label>
                    <Input type="number" value={stop[0]} step="0.000001" onChange={(event) => updateStops(index, [Number(event.target.value), stop[1]])} />
                  </div>
                  <div>
                    <label className="mb-1 block text-[10px] font-bold uppercase tracking-[0.14em] text-slate-400">Longitude</label>
                    <Input type="number" value={stop[1]} step="0.000001" onChange={(event) => updateStops(index, [stop[0], Number(event.target.value)])} />
                  </div>
                  <button type="button" className="self-end rounded-lg border border-slate-200 p-2 text-slate-400 transition hover:border-red-200 hover:bg-red-50 hover:text-red-600" onClick={() => removeStop(index)} aria-label={`Remove stop ${index + 1}`}>
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>

            <div className="flex items-center gap-3">
              <label className="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-bold text-slate-700 transition hover:border-fuchsia-200 hover:bg-fuchsia-50">
                <Upload className="h-4 w-4" /> Import CSV
                <input type="file" accept=".csv" className="hidden" onChange={handleCsvImport} />
              </label>
              <span className="text-xs text-slate-500">Columns: latitude, longitude</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="rounded-xl bg-cyan-50 p-2.5 text-cyan-700"><MapPinPlus className="h-4 w-4" /></div>
              <div><div className="page-kicker mb-1">Step 02</div><CardTitle>Vehicle & optimization</CardTitle></div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="rounded-2xl border border-cyan-100 bg-cyan-50/40 p-4">
              <div className="mb-3 text-sm font-bold text-slate-800">Vehicle configuration</div>
              <label className="mb-1.5 block text-xs font-bold uppercase tracking-[0.12em] text-slate-500">Fuel efficiency · km per litre</label>
              <Input
                type="number"
                min="0.1"
                value={config.mileage_km_per_litre}
                onChange={(event) => setConfig((current) => ({ ...current, mileage_km_per_litre: Number(event.target.value) }))}
              />
            </div>
            <details className="group rounded-xl border border-slate-200">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-3 p-4 text-sm font-bold text-slate-700">
                <span className="min-w-0">
                  <span className="block">Advanced optimization settings</span>
                  <span className="mt-1 block text-xs font-medium text-slate-400">ACO controls, objective weights, and traffic model</span>
                </span>
                <span className="flex shrink-0 items-center gap-2">
                  <span className="rounded-full bg-slate-100 px-2 py-1 text-[10px] font-bold text-slate-500">10 controls</span>
                  <ChevronDown className="h-4 w-4 transition group-open:rotate-180" />
                </span>
              </summary>
              <div className="space-y-5 border-t border-slate-100 p-4">
                {advancedGroups.map((group) => (
                  <section key={group.title}>
                    <h4 className="mb-2 text-[10px] font-bold uppercase tracking-[0.14em] text-slate-400">{group.title}</h4>
                    <div className="grid gap-3 sm:grid-cols-2">
                      {group.fields.map(({ key, label, description }) => (
                        <div key={key} className="space-y-1">
                          <label className="text-[10px] font-bold uppercase tracking-[0.12em] text-slate-500" title={description}>{label}</label>
                          <Input
                            type="number"
                            value={config[key as keyof typeof config]}
                            title={description}
                            aria-label={label}
                            onChange={(event) => setConfig((current) => ({ ...current, [key]: Number(event.target.value) }))}
                          />
                        </div>
                      ))}
                    </div>
                  </section>
                ))}
              </div>
            </details>

            <div className="pt-3">
              <Button className="brand-button h-12 w-full gap-2 text-[15px]" onClick={() => void handleOptimize()} disabled={loading}>
                {loading ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <MapPinPlus className="h-4 w-4" />}
                {loading ? 'Optimizing...' : 'Optimize Delivery Route'}
              </Button>
              {message && (
                <div
                  role={loading ? 'status' : progress === 100 ? 'status' : 'alert'}
                  aria-live="polite"
                  className={`mt-3 rounded-xl border p-3 ${loading ? 'border-fuchsia-100 bg-fuchsia-50/60' : progress === 100 ? 'border-emerald-100 bg-emerald-50/60' : 'border-red-100 bg-red-50/60'}`}
                >
                  <div className="flex items-center gap-2 text-sm text-slate-700">
                    {loading ? <LoaderCircle className="h-4 w-4 animate-spin text-fuchsia-600" /> : progress === 100 ? <CheckCircle2 className="h-4 w-4 text-emerald-600" /> : <AlertCircle className="h-4 w-4 text-red-600" />}
                    <span className="min-w-0 flex-1">{message}</span>
                    {loading && <span className="numeric text-xs font-bold text-fuchsia-700">{progress}%</span>}
                  </div>
                  {loading && (
                    <div
                      className="mt-3 h-1.5 overflow-hidden rounded-full bg-fuchsia-100"
                      role="progressbar"
                      aria-label="Optimization progress"
                      aria-valuemin={0}
                      aria-valuemax={100}
                      aria-valuenow={progress}
                    >
                      <div className="h-full rounded-full bg-fuchsia-500 transition-all" style={{ width: `${progress}%` }} />
                    </div>
                  )}
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {result && (
        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="rounded-xl bg-emerald-50 p-2.5 text-emerald-700"><MapPinPlus className="h-4 w-4" /></div>
              <div><div className="page-kicker mb-1">Optimization complete</div><CardTitle>Generated route summary</CardTitle></div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-3">
              <div>
                <div className="text-xs font-bold uppercase tracking-[0.14em] text-slate-400">Distance</div>
                <div className="numeric mt-2 text-2xl font-bold">{result.metrics.distance_km.toFixed(2)} <span className="text-sm font-medium text-slate-500">km</span></div>
              </div>
              <div>
                <div className="text-xs font-bold uppercase tracking-[0.14em] text-slate-400">Travel time</div>
                <div className="numeric mt-2 text-2xl font-bold">{result.metrics.travel_time_minutes.toFixed(1)} <span className="text-sm font-medium text-slate-500">min</span></div>
              </div>
              <div>
                <div className="text-xs font-bold uppercase tracking-[0.14em] text-slate-400">Fuel</div>
                <div className="numeric mt-2 text-2xl font-bold">{result.metrics.fuel_liters.toFixed(2)} <span className="text-sm font-medium text-slate-500">L</span></div>
              </div>
            </div>
            <div className="mt-6 rounded-2xl border border-slate-100 bg-slate-50 p-4">
              <div className="mb-3 flex items-center justify-between gap-2">
                <div className="text-xs font-bold uppercase tracking-[0.14em] text-slate-500">Delivery sequence</div>
                <div className="text-xs font-semibold text-slate-400">{result.sequence?.filter((entry: any) => entry.type === 'stop').length || 0} stops</div>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                {result.sequence?.map((entry: any, index: number) => (
                  <div key={`${entry.position}-${entry.type}`} className="flex items-center gap-2">
                    <span className={`rounded-full px-3 py-1.5 text-xs font-bold ${entry.type === 'depot' ? 'bg-fuchsia-100 text-fuchsia-800' : 'bg-white text-slate-700 ring-1 ring-slate-200'}`}>
                      {entry.type === 'depot' ? 'Depot' : entry.type === 'current' ? 'Current position' : `Stop ${entry.index + 1}`}
                    </span>
                    {index < result.sequence.length - 1 && <ChevronRight className="h-3.5 w-3.5 text-slate-300" />}
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
