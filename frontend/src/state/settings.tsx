import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import type { Mode } from "../api/types";
import { clearApiKey, getApiKey, getMode, looksLikeApiKey, setApiKey as storeKey, setMode as storeMode } from "../lib/storage";

interface Settings {
  mode: Mode;
  apiKey: string;
  /** Live mode is only usable when a plausible key is present. */
  liveReady: boolean;
  setMode: (m: Mode) => void;
  setApiKey: (k: string) => void;
  forgetKey: () => void;
}

const Ctx = createContext<Settings | null>(null);

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<Mode>(getMode);
  const [apiKey, setKeyState] = useState<string>(getApiKey);

  const setMode = useCallback((m: Mode) => {
    storeMode(m);
    setModeState(m);
  }, []);
  const setApiKey = useCallback((k: string) => {
    storeKey(k);
    setKeyState(k.trim());
  }, []);
  const forgetKey = useCallback(() => {
    clearApiKey();
    setKeyState("");
  }, []);

  const value = useMemo<Settings>(
    () => ({ mode, apiKey, liveReady: looksLikeApiKey(apiKey), setMode, setApiKey, forgetKey }),
    [mode, apiKey, setMode, setApiKey, forgetKey],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useSettings(): Settings {
  const v = useContext(Ctx);
  if (!v) throw new Error("useSettings must be used inside <SettingsProvider>");
  return v;
}
