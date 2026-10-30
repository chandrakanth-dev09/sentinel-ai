import { useCallback, useEffect, useRef, useState } from "react";
import { getErrorMessage } from "../services/api";

interface ResourceState<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
  reload: () => void;
}

export function useAsyncResource<T>(
  key: string,
  loader: () => Promise<T>,
  refreshInterval = 0
): ResourceState<T> {
  const loaderRef = useRef(loader);
  loaderRef.current = loader;
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshVersion, setRefreshVersion] = useState(0);

  const reload = useCallback(() => setRefreshVersion((version) => version + 1), []);

  useEffect(() => {
    let active = true;
    setData(null);
    setError(null);
    setLoading(true);

    const load = () => {
      loaderRef.current()
        .then((result) => {
          if (!active) return;
          setData(result);
          setError(null);
        })
        .catch((reason: unknown) => {
          if (!active) return;
          setError(getErrorMessage(reason));
        })
        .finally(() => {
          if (active) setLoading(false);
        });
    };

    load();
    const timer = refreshInterval > 0 ? window.setInterval(load, refreshInterval) : undefined;
    return () => {
      active = false;
      if (timer !== undefined) window.clearInterval(timer);
    };
  }, [key, refreshInterval, refreshVersion]);

  return { data, error, loading, reload };
}
