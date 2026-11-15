import { useEffect, useState } from 'react';
import { MapContainer, Marker, Popup, Polyline, TileLayer, useMap } from 'react-leaflet';
import { Activity, Route as RouteIcon } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { getCurrentRoute } from '../services/api';

function MapSizeObserver() {
  const map = useMap();

  useEffect(() => {
    let frame = 0;
    const invalidateSize = () => {
      window.cancelAnimationFrame(frame);
      frame = window.requestAnimationFrame(() => map.invalidateSize({ pan: false, debounceMoveend: true }));
    };
    const observer = new ResizeObserver(invalidateSize);
    const container = map.getContainer();
    const parent = container.parentElement;
    observer.observe(container);
    if (parent) observer.observe(parent);
    window.addEventListener('resize', invalidateSize);
    invalidateSize();

    return () => {
      window.cancelAnimationFrame(frame);
      observer.disconnect();
      window.removeEventListener('resize', invalidateSize);
    };
  }, [map]);

  return null;
}

export function LiveMapPage() {
  const [route, setRoute] = useState<any>(null);

  useEffect(() => {
    const loadRoute = async () => {
      try {
        const result = await getCurrentRoute();
        setRoute(result);
      } catch {
        setRoute(null);
      }
    };

    loadRoute();
    const timer = window.setInterval(loadRoute, 10000);
    return () => window.clearInterval(timer);
  }, []);

  const routeCoordinates = route?.geometry || [];
  const depot = route?.sequence?.find((item: any) => item.type === 'depot');
  const stops = route?.sequence?.filter((item: any) => item.type === 'stop') || [];
  const hasRoute = Boolean(route?.sequence?.length && route?.geometry?.length > 1);
  const hasRouteMetrics = [
    route?.metrics?.distance_km,
    route?.metrics?.travel_time_minutes,
    route?.metrics?.fuel_liters,
  ].every((value) => typeof value === 'number' && Number.isFinite(value));

  return (
    <div className="space-y-6">
      <div className="page-header">
        <div>
          <div className="page-kicker">Dispatch center · Live operations</div>
          <h1 className="page-title">Live route map</h1>
          <p className="page-description">Follow the active road route and delivery locations.</p>
        </div>
        <div className="flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-bold text-emerald-800">
          <Activity className="h-3.5 w-3.5" /> Route view
        </div>
      </div>

      <Card className="overflow-hidden p-0">
        <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-fuchsia-50 p-2 text-fuchsia-700"><RouteIcon className="h-4 w-4" /></div>
            <div>
              <div className="text-sm font-bold text-slate-800">{hasRoute ? 'Active route' : 'No active route'}</div>
              <div className="mt-0.5 text-xs text-slate-500">{hasRoute ? `${route.geometry.length} road geometry points` : 'Plan a route to display it on the map.'}</div>
            </div>
          </div>
          <div className="hidden items-center gap-4 text-xs font-semibold text-slate-500 sm:flex">
            <span className="flex items-center gap-1.5"><i className="h-2.5 w-2.5 rounded-full bg-fuchsia-600" /> Depot</span>
            <span className="flex items-center gap-1.5"><i className="h-2.5 w-2.5 rounded-full bg-cyan-500" /> Stops</span>
          </div>
        </div>
        <div className="relative h-[min(70vh,680px)] min-h-[420px] w-full">
          <MapContainer center={[27.1767, 78.0081]} zoom={14} scrollWheelZoom className="h-full w-full">
            <MapSizeObserver />
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              maxZoom={19}
            />
            {depot && <Marker position={[depot.latitude, depot.longitude]}><Popup>Depot</Popup></Marker>}
            {stops.map((stop: any) => (
              <Marker key={`stop-${stop.index}`} position={[stop.latitude, stop.longitude]}>
                <Popup>{stop.label || `Stop ${stop.index + 1}`}</Popup>
              </Marker>
            ))}
            {routeCoordinates.length > 0 && <Polyline positions={routeCoordinates} pathOptions={{ color: '#2dd4bf', weight: 5, opacity: 0.9 }} />}
          </MapContainer>
          {hasRouteMetrics && (
            <div className="absolute bottom-4 left-4 z-[500] w-[min(300px,calc(100%-32px))] rounded-2xl border border-white/80 bg-white/95 p-4 shadow-xl backdrop-blur">
              <div className="mb-3 flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">Route summary</span>
                <span className="rounded-full bg-emerald-50 px-2 py-1 text-[10px] font-bold text-emerald-700">ACTIVE</span>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <div><div className="text-[10px] font-bold uppercase text-slate-400">Distance</div><div className="numeric mt-1 text-sm font-bold">{route.metrics.distance_km.toFixed(1)} km</div></div>
                <div><div className="text-[10px] font-bold uppercase text-slate-400">Time</div><div className="numeric mt-1 text-sm font-bold">{route.metrics.travel_time_minutes.toFixed(0)} min</div></div>
                <div><div className="text-[10px] font-bold uppercase text-slate-400">Fuel</div><div className="numeric mt-1 text-sm font-bold">{route.metrics.fuel_liters.toFixed(1)} L</div></div>
              </div>
            </div>
          )}
          {!hasRoute && (
            <div className="pointer-events-none absolute inset-0 z-[500] flex items-center justify-center bg-slate-900/10 p-4">
              <div className="pointer-events-auto max-w-sm rounded-2xl border border-white/80 bg-white/95 p-6 text-center shadow-xl backdrop-blur">
                <div className="mx-auto mb-3 flex h-11 w-11 items-center justify-center rounded-full bg-fuchsia-50 text-fuchsia-700"><RouteIcon className="h-5 w-5" /></div>
                <div className="font-['Poppins'] text-lg font-semibold text-slate-900">Your map is ready</div>
                <p className="mt-1 text-sm text-slate-500">Create an optimized route to see its road geometry and delivery stops here.</p>
                <Link to="/planner" className="mt-4 inline-flex items-center justify-center rounded-lg bg-fuchsia-600 px-4 py-2 text-sm font-bold text-white transition hover:bg-fuchsia-700">Open route planner</Link>
              </div>
            </div>
          )}
        </div>
      </Card>

      {route && hasRouteMetrics && (
        <Card>
          <CardHeader>
            <CardTitle>Route details</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 sm:grid-cols-3">
              <div>
                <div className="text-xs font-bold uppercase tracking-[0.14em] text-slate-400">Distance</div>
                <div className="numeric mt-2 text-xl font-bold">{route.metrics.distance_km.toFixed(2)} <span className="text-sm font-medium text-slate-500">km</span></div>
              </div>
              <div>
                <div className="text-xs font-bold uppercase tracking-[0.14em] text-slate-400">Travel time</div>
                <div className="numeric mt-2 text-xl font-bold">{route.metrics.travel_time_minutes.toFixed(1)} <span className="text-sm font-medium text-slate-500">min</span></div>
              </div>
              <div>
                <div className="text-xs font-bold uppercase tracking-[0.14em] text-slate-400">Fuel</div>
                <div className="numeric mt-2 text-xl font-bold">{route.metrics.fuel_liters.toFixed(2)} <span className="text-sm font-medium text-slate-500">L</span></div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
