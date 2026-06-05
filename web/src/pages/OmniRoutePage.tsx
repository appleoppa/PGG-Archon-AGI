import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Activity,
  AlertTriangle,
  Cpu,
  GitBranch,
  RotateCw,
  Shield,
  SlidersHorizontal,
  Zap,
} from "lucide-react";
import { Badge } from "@nous-research/ui/ui/components/badge";
import { Button } from "@nous-research/ui/ui/components/button";
import { Card, CardContent } from "@nous-research/ui/ui/components/card";
import { Select, SelectOption } from "@nous-research/ui/ui/components/select";
import { H2 } from "@nous-research/ui/ui/components/typography/h2";
import { api, HERMES_BASE_PATH } from "@/lib/api";
import type { OmniRouteSnapshot } from "@/lib/api";

function fmt(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : value.toFixed(3);
  return String(value);
}

function formatTime(epoch?: number | null): string {
  if (!epoch) return "—";
  return new Date(epoch * 1000).toLocaleString();
}

function toneFor(status: string | undefined): "success" | "warning" | "destructive" | "secondary" {
  const s = (status || "").toLowerCase();
  if (["pass", "healthy", "ok", "selected"].some((x) => s.includes(x))) return "success";
  if (["blocked", "cooldown", "unhealthy", "error", "fail"].some((x) => s.includes(x))) return "destructive";
  if (["watch", "partial", "unknown"].some((x) => s.includes(x))) return "warning";
  return "secondary";
}

export default function OmniRoutePage() {
  const [snapshot, setSnapshot] = useState<OmniRouteSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [streamState, setStreamState] = useState<"connecting" | "live" | "fallback" | "error">("connecting");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);

  const providers = useMemo(() => snapshot?.provider_cards ?? [], [snapshot]);
  const selected = snapshot?.selected_provider || "";
  const effectiveSelected = snapshot?.effective_selected_provider || selected;
  const health = snapshot?.provider_health_snapshot ?? {};
  const summary = snapshot?.summary ?? {};

  const loadSnapshot = useCallback(async () => {
    try {
      const data = await api.getOmniRouteSnapshot();
      setSnapshot(data);
      setError(null);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSnapshot();
  }, [loadSnapshot]);

  useEffect(() => {
    const token = window.__HERMES_SESSION_TOKEN__;
    if (!token || typeof EventSource === "undefined") {
      setStreamState("fallback");
      const timer = window.setInterval(() => void loadSnapshot(), 3000);
      return () => window.clearInterval(timer);
    }
    const url = `${HERMES_BASE_PATH}/api/omniroute/stream?token=${encodeURIComponent(token)}`;
    const es = new EventSource(url);
    eventSourceRef.current = es;
    es.addEventListener("snapshot", (event) => {
      try {
        setSnapshot(JSON.parse((event as MessageEvent).data));
        setStreamState("live");
        setError(null);
        setLoading(false);
      } catch (exc) {
        setError(exc instanceof Error ? exc.message : String(exc));
      }
    });
    es.onerror = () => {
      setStreamState("error");
    };
    return () => {
      es.close();
      eventSourceRef.current = null;
    };
  }, [loadSnapshot]);

  const setAuto = async () => {
    setSaving(true);
    try {
      const res = await api.setOmniRouteControl({ mode: "auto", selected_provider: "" });
      setSnapshot(res.snapshot);
    } finally {
      setSaving(false);
    }
  };

  const setManualProvider = async (provider: string) => {
    setSaving(true);
    try {
      const res = await api.setOmniRouteControl({ mode: "manual", selected_provider: provider });
      setSnapshot(res.snapshot);
    } finally {
      setSaving(false);
    }
  };

  const forceRefresh = async () => {
    setSaving(true);
    try {
      const res = await api.setOmniRouteControl({ force_refresh: true });
      setSnapshot(res.snapshot);
    } finally {
      setSaving(false);
    }
  };

  if (loading && !snapshot) {
    return <div className="p-6 text-sm text-muted-foreground">Loading OmniRoute…</div>;
  }

  return (
    <div className="p-6 space-y-5">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Zap className="h-5 w-5 text-primary" />
            <H2>PGG OmniRoute / 河图洛书</H2>
          </div>
          <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
            本地量子路由、河图洛书与 provider health 的统一实时面板。实时显示不等于 provider 已参与正式任务。
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone={streamState === "live" ? "success" : streamState === "error" ? "destructive" : "warning"}>
            {streamState === "live" ? "SSE live" : streamState}
          </Badge>
          <Button size="sm" ghost onClick={() => void loadSnapshot()}>
            <RotateCw className="h-4 w-4" /> Refresh
          </Button>
          <Button size="sm" onClick={() => void forceRefresh()} disabled={saving}>
            <SlidersHorizontal className="h-4 w-4" /> Force flag
          </Button>
        </div>
      </div>

      {error ? (
        <Card>
          <CardContent className="py-4 text-sm text-destructive flex gap-2">
            <AlertTriangle className="h-4 w-4" /> {error}
          </CardContent>
        </Card>
      ) : null}

      <div className="grid gap-4 md:grid-cols-4">
        <Card><CardContent className="py-4"><div className="text-xs text-muted-foreground">Selected</div><div className="text-2xl font-semibold">{fmt(selected)}</div></CardContent></Card>
        <Card><CardContent className="py-4"><div className="text-xs text-muted-foreground">Effective</div><div className="text-2xl font-semibold">{fmt(effectiveSelected)}</div></CardContent></Card>
        <Card><CardContent className="py-4"><div className="text-xs text-muted-foreground">Score</div><div className="text-2xl font-semibold">{fmt(summary.score)}</div></CardContent></Card>
        <Card><CardContent className="py-4"><div className="text-xs text-muted-foreground">Order</div><div className="text-2xl font-semibold">{fmt(summary.order_status)}</div></CardContent></Card>
      </div>

      <Card>
        <CardContent className="py-4 space-y-3">
          <div className="flex items-center gap-2 font-medium"><GitBranch className="h-4 w-4" /> Unified entry / 自由切换</div>
          <div className="flex flex-col gap-3 md:flex-row md:items-center">
            <Button size="sm" ghost={snapshot?.control.mode !== "auto"} onClick={() => void setAuto()} disabled={saving}>
              Auto router
            </Button>
            <Select value={effectiveSelected || ""} onValueChange={(v) => void setManualProvider(v)}>
              <SelectOption value="">Choose provider…</SelectOption>
              {providers.map((p) => (
                <SelectOption key={p.provider} value={p.provider}>{p.provider}</SelectOption>
              ))}
            </Select>
            <Badge tone={snapshot?.control.mode === "manual" ? "warning" : "success"}>{snapshot?.control.mode ?? "auto"}</Badge>
            <span className="text-xs text-muted-foreground">updated: {formatTime(snapshot?.control.updated_at)}</span>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-3">
        {providers.map((p) => (
          <Card key={p.provider}>
            <CardContent className="py-4 space-y-2">
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2 font-medium"><Cpu className="h-4 w-4" /> {p.provider || "unknown"}</div>
                <Badge tone={toneFor(p.status)}>{p.status || "unknown"}</Badge>
              </div>
              <div className="text-sm text-muted-foreground">score: {fmt(p.score)}</div>
              {p.blocked ? <div className="text-sm text-destructive">blocked</div> : null}
              {p.blocked_reasons?.length ? <div className="text-xs text-muted-foreground">{p.blocked_reasons.join(" / ")}</div> : null}
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardContent className="py-4 space-y-2">
          <div className="flex items-center gap-2 font-medium"><Activity className="h-4 w-4" /> TTL cache / health</div>
          <div className="grid gap-2 text-sm md:grid-cols-4">
            <div>cache: {fmt(health.cache_status)}</div>
            <div>age: {fmt(health.age_sec)}s</div>
            <div>ttl: {fmt(health.ttl_sec)}s</div>
            <div>force: {fmt(health.force_refresh)}</div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="py-4 space-y-2">
          <div className="flex items-center gap-2 font-medium"><Shield className="h-4 w-4" /> Boundary</div>
          <p className="text-sm text-muted-foreground">{snapshot?.boundary}</p>
          <div className="text-xs text-muted-foreground break-all">dashboard: {snapshot?.paths.dashboard}</div>
        </CardContent>
      </Card>
    </div>
  );
}
