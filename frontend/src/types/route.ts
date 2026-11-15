export type RouteMetric = {
  distance_km: number;
  travel_time_minutes: number;
  fuel_liters: number;
  combined_cost?: number;
};

export type RouteResult = {
  route: number[];
  route_nodes?: number[];
  metrics: RouteMetric;
  history: number[];
  mode: string;
  geometry: number[][][];
  sequence: Array<{
    position: number;
    type: string;
    index?: number;
    latitude: number;
    longitude: number;
    label?: string;
  }>;
};

export type NetworkStatus = {
  city: string;
  nodes: number;
  edges: number;
  loaded: boolean;
};

export type TrafficStatus = {
  source: string;
  available: boolean;
  status: string;
  message?: string;
};
