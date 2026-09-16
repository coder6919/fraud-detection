import { useEffect, useState } from "react";

const DEFAULT_DELAY_MS = 4000;

// The Render free tier spins the backend down after 15 min idle and can take
// up to ~60s to wake on the next request. A plain "Loading..." that never
// resolves for that long reads as broken — this surfaces an explanation once
// the wait has gone on long enough to actually need one.
export function useSlowLoadHint(isLoading, delayMs = DEFAULT_DELAY_MS) {
  const [showHint, setShowHint] = useState(false);

  useEffect(() => {
    if (!isLoading) {
      setShowHint(false);
      return;
    }
    const timer = setTimeout(() => setShowHint(true), delayMs);
    return () => clearTimeout(timer);
  }, [isLoading, delayMs]);

  return showHint;
}
