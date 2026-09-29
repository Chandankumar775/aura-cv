import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  BookOpen, CirclePlus, Database, FileText, FlaskConical, KeyRound, LayoutDashboard, Link2, ListChecks,
  LogOut, ScrollText, Settings, ShieldCheck, Wifi, WifiOff, FolderKanban, Menu, Search, X,
} from "lucide-react";
import TerrainScene from "./TerrainScene";
import { CommandPalette, Toasts } from "./CommandPalette";
import { api } from "../lib/api";
import { useApp } from "../lib/app";
import { relTime } from "../lib/format";
import { cx } from "./ui";
import FindingDrawer from "./FindingDrawer";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/assessments/new", label: "New assessment", icon: CirclePlus },
  { to: "/assessments", label: "Assessments", icon: FolderKanban, end: true },
  { to: "/assets/dataset", label: "Assets", icon: Database },
  { to: "/findings", label: "Findings", icon: ListChecks },
  { to: "/reports", label: "Reports", icon: FileText },
  { to: "/audit", label: "Audit log", icon: ScrollText },
];
const ADMIN_NAV = [
  { to: "/attack-lab", label: "Attack Lab", icon: FlaskConical },
  { to: "/settings/users", label: "Settings", icon: Settings },
];

export function Mark({ size = 30 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden>
      <rect width="32" height="32" rx="8" fill="#101826" stroke="#27405f" />
      <path d="M16 5.5 25.5 10v6.6c0 5.3-4 9-9.5 10.4C10.5 25.6 6.5 21.9 6.5 16.6V10z" fill="none" stroke="#8db7ff" strokeWidth="1.8" strokeLinejoin="round" />
      <path d="m11.8 16.3 3 3 5.6-6" fill="none" stroke="#8db7ff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function StripItem({ ok, warn, icon, label, value, title }: { ok?: boolean; warn?: boolean; icon: React.ReactNode; label: string; value: React.ReactNode; title?: string }) {
  return (
    <div className="flex items-center gap-2 whitespace-nowrap" title={title}>
      <span className={cx(ok ? "text-accept" : warn ? "text-review" : "text-quarantine")}>{icon}</span>
      <span className="text-ink-3">{label}</span>
      <span className="font-medium text-ink-2">{value}</span>
    </div>
  );
}

function StatusStrip({ onMenu }: { onMenu: () => void }) {
  const { status, user, setUser, setPaletteOpen } = useApp();
  const nav = useNavigate();
  const logout = async () => {
    await api.post("/auth/logout").catch(() => {});
    setUser(null);
    nav("/login");
  };
  return (
    <div className="no-print glass-strong relative z-10 flex h-12 items-center gap-6 overflow-hidden px-4 text-[12px] lg:px-6">
      <button onClick={onMenu} className="rounded-md p-1.5 text-ink-2 hover:bg-raised lg:hidden" aria-label="Open navigation"><Menu size={17} /></button>
      <button onClick={() => setPaletteOpen(true)} className="glass-inset flex h-8 w-[240px] shrink-0 items-center gap-2 rounded-lg px-2.5 text-[12.5px] text-ink-3 transition-colors hover:text-ink-2">
        <Search size={14} /> Search or run a command
        <kbd className="ml-auto rounded border border-line px-1 font-mono text-[10px]">Ctrl K</kbd>
      </button>
      {status ? (
        <>
          {status.hosted ? (
            <StripItem warn icon={<Wifi size={14} />} label="Hosted demo" value="not air-gapped · production runs offline"
              title="This public deployment runs on a cloud host for demonstration. The production build is installed on an air-gapped machine." />
          ) : <StripItem
            ok={status.network.air_gapped} warn={!status.network.air_gapped && status.network.guard_active}
            icon={status.network.air_gapped ? <WifiOff size={14} /> : <Wifi size={14} />}
            label={status.network.air_gapped ? "OFFLINE" : "Guard"}
            value={status.network.air_gapped ? "air-gapped ✓" : "active · host has network route"}
            title={status.network.detail}
          />}
          <div className="hidden xl:block"><StripItem ok={status.keys.active >= 3} icon={<KeyRound size={14} />} label="Keys" value={`${status.keys.active} active`} /></div>
          <div className="hidden 2xl:block"><StripItem ok={!!status.reference} icon={<Database size={14} />} label="Reference" value={status.reference?.name ?? "none"} /></div>
          <div className="hidden md:block"><StripItem ok={status.audit.valid} icon={<Link2 size={14} />} label="Audit chain"
            value={status.audit.valid ? `valid · ${status.audit.entries} entries · ${relTime(status.audit.verified_at)}` : "BROKEN"} title={status.audit.head_hash} /></div>
        </>
      ) : (
        <span className="text-ink-3">Checking system status…</span>
      )}
      <div className="ml-auto flex items-center gap-4">
        {status?.demo && (
          <span className="whitespace-nowrap rounded border border-review/40 bg-review/10 px-2 py-0.5 text-[10.5px] font-semibold tracking-[0.1em] text-review" title={status.demo_notice}>
            DEMO DATA
          </span>
        )}
        {user && (
          <div className="flex items-center gap-3">
            <div className="text-right leading-tight">
              <div className="whitespace-nowrap text-[12.5px] font-medium text-ink">{user.display.replace(/ \((Admin|Analyst)\)$/, "")}</div>
              <div className="text-[10.5px] tracking-wider text-ink-3">{user.role}</div>
            </div>
            <button onClick={logout} className="rounded-md p-1.5 text-ink-3 hover:bg-raised hover:text-ink" title="Sign out">
              <LogOut size={15} />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function SideNav({ items, onNavigate }: { items: { to: string; label: string; icon: typeof LayoutDashboard; end?: boolean }[]; onNavigate?: () => void }) {
  return (
    <>
      <div className="flex items-center gap-3 px-5 pb-6 pt-5">
        <Mark />
        <div className="leading-tight">
          <div className="text-[15px] font-semibold tracking-[0.04em] text-ink">AURA-CV</div>
          <div className="text-[10.5px] text-ink-3">Assurance Console</div>
        </div>
      </div>
      <nav className="flex flex-1 flex-col gap-0.5 px-3">
        {items.map(({ to, label, icon: Icon, end }) => (
          <NavLink key={to} to={to} end={end} onClick={onNavigate}
            className={({ isActive }) => cx("group relative flex items-center gap-3 rounded-lg px-3 py-2 text-[13.5px] transition-colors duration-150",
              isActive ? "bg-brand/[0.10] font-medium text-ink" : "text-ink-2 hover:bg-raised hover:text-ink")}>
            {({ isActive }) => (
              <>
                <span className={cx("absolute left-0 top-1/2 h-5 w-[2px] -translate-y-1/2 rounded-full bg-brand transition-opacity duration-200", isActive ? "opacity-100" : "opacity-0")} />
                <Icon size={16} strokeWidth={1.8} className={isActive ? "text-brand" : ""} />
                {label}
              </>
            )}
          </NavLink>
        ))}
      </nav>
      <div className="px-3 pb-2">
        <NavLink to="/coverage" onClick={onNavigate} className={({ isActive }) => cx("flex items-center gap-3 rounded-lg px-3 py-2 text-[13.5px]", isActive ? "bg-brand/[0.10] text-ink" : "text-ink-2 hover:bg-raised hover:text-ink")}>
          <BookOpen size={16} strokeWidth={1.8} /> Coverage &amp; limits
        </NavLink>
      </div>
      <div className="glass-inset m-3 rounded-xl p-3 text-[11.5px] leading-relaxed text-ink-3">
        <div className="mb-1 flex items-center gap-1.5 font-medium text-ink-2"><ShieldCheck size={13} className="text-accept" /> Offline by design</div>
        No cloud services, no external APIs. Every action is recorded in a signed, tamper-evident audit log.
      </div>
    </>
  );
}

export default function Layout() {
  const { user } = useApp();
  const [mobileNav, setMobileNav] = useState(false);
  const loc = useLocation();
  useEffect(() => setMobileNav(false), [loc.pathname]);
  const items: { to: string; label: string; icon: typeof LayoutDashboard; end?: boolean }[] = [...NAV, ...(user?.role === "ADMIN" ? ADMIN_NAV : [])];
  return (
    <div className="relative flex h-full">
      <TerrainScene intensity={0.55} className="-z-0 opacity-90" />
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(120%_90%_at_60%_40%,transparent_30%,rgb(6_9_13/0.72)_100%)]" />
      <aside className="no-print glass-strong relative z-10 hidden w-[236px] shrink-0 flex-col lg:flex">
        <SideNav items={items} />
      </aside>
      {mobileNav && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-black/50" onClick={() => setMobileNav(false)} />
          <aside className="slide-in glass-strong relative flex h-full w-[260px] flex-col">
            <button onClick={() => setMobileNav(false)} className="absolute right-3 top-4 rounded p-1.5 text-ink-3 hover:text-ink" aria-label="Close navigation"><X size={16} /></button>
            <SideNav items={items} onNavigate={() => setMobileNav(false)} />
          </aside>
        </div>
      )}
      <div className="relative z-10 flex min-w-0 flex-1 flex-col">
        <StatusStrip onMenu={() => setMobileNav(true)} />
        <main className="min-h-0 flex-1 overflow-y-auto">
          <div className="mx-auto max-w-[1400px] px-4 py-8 sm:px-6 lg:px-8">
            <Outlet />
          </div>
        </main>
      </div>
      <FindingDrawer />
      <CommandPalette />
      <Toasts />
    </div>
  );
}
