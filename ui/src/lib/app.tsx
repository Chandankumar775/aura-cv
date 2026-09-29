import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api, type User } from "./api";

export interface SystemStatus {
  demo: boolean;
  demo_notice: string;
  version: string;
  hosted?: boolean;
  network: { guard_active: boolean; air_gapped: boolean; detail: string };
  keys: { active: number; total: number };
  reference: { id: string; name: string } | null;
  audit: { valid: boolean; entries: number; verified_at: string; head_hash: string };
  battery: { version: string; digest: string };
}

interface DrawerState {
  id: string;
  ids: string[];
}

export interface Toast {
  id: number;
  tone: "ok" | "warn" | "danger" | "info";
  title: string;
  detail?: string;
}

interface Ctx {
  user: User | null;
  setUser: (u: User | null) => void;
  status: SystemStatus | null;
  refreshStatus: () => void;
  drawer: DrawerState | null;
  openFinding: (id: string, ids?: string[]) => void;
  closeFinding: () => void;
  version: number; // bumps after a decision so views refresh
  bump: () => void;
  toasts: Toast[];
  toast: (t: Omit<Toast, "id">) => void;
  dismiss: (id: number) => void;
  paletteOpen: boolean;
  setPaletteOpen: (v: boolean) => void;
}

const AppCtx = createContext<Ctx>(null as unknown as Ctx);
export const useApp = () => useContext(AppCtx);

export function AppProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [drawer, setDrawer] = useState<DrawerState | null>(null);
  const [version, setVersion] = useState(0);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const dismiss = useCallback((id: number) => setToasts((ts) => ts.filter((t) => t.id !== id)), []);
  const toast = useCallback((t: Omit<Toast, "id">) => {
    const id = Date.now() + Math.random();
    setToasts((ts) => [...ts.slice(-3), { ...t, id }]);
    window.setTimeout(() => dismiss(id), 5200);
  }, [dismiss]);

  const refreshStatus = useCallback(() => {
    api.get<SystemStatus>("/system/status").then(setStatus).catch(() => {});
  }, []);

  useEffect(() => {
    if (!user) return;
    refreshStatus();
    const t = window.setInterval(refreshStatus, 20000);
    return () => window.clearInterval(t);
  }, [user, refreshStatus]);

  return (
    <AppCtx.Provider
      value={{
        user, setUser, status, refreshStatus, drawer,
        openFinding: (id, ids) => setDrawer({ id, ids: ids ?? [id] }),
        closeFinding: () => setDrawer(null),
        version,
        bump: () => { setVersion((v) => v + 1); refreshStatus(); },
        toasts, toast, dismiss, paletteOpen, setPaletteOpen,
      }}
    >
      {children}
    </AppCtx.Provider>
  );
}
