import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { getTrafficStatus, type TrafficStatus } from './api';

type TrafficStatusContextValue = {
  status: TrafficStatus | null;
  updateStatus: (status: TrafficStatus) => void;
  refreshStatus: () => Promise<void>;
};

const TrafficStatusContext = createContext<TrafficStatusContextValue | null>(null);

export function TrafficStatusProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<TrafficStatus | null>(null);
  const revision = useRef(0);

  const refreshStatus = useCallback(async () => {
    const requestRevision = revision.current;
    try {
      const currentStatus = await getTrafficStatus();
      if (requestRevision === revision.current) setStatus(currentStatus);
    } catch {
      // Keep the last confirmed backend status when a refresh fails.
    }
  }, []);

  const updateStatus = useCallback((currentStatus: TrafficStatus) => {
    revision.current += 1;
    setStatus(currentStatus);
  }, []);

  useEffect(() => {
    void refreshStatus();
    const timer = window.setInterval(() => void refreshStatus(), 15000);
    return () => window.clearInterval(timer);
  }, [refreshStatus]);

  const value = useMemo(() => ({ status, updateStatus, refreshStatus }), [status, updateStatus, refreshStatus]);
  return <TrafficStatusContext.Provider value={value}>{children}</TrafficStatusContext.Provider>;
}

export function useTrafficStatus() {
  const context = useContext(TrafficStatusContext);
  if (!context) {
    throw new Error('useTrafficStatus must be used within TrafficStatusProvider.');
  }
  return context;
}
