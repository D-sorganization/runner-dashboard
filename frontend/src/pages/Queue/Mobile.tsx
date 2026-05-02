import { useCallback, useEffect, useMemo, useState } from "react";
import { SegmentedControl } from "../../primitives/SegmentedControl";
import { Badge } from "../../primitives/Badge";
import { TouchButton } from "../../primitives/TouchButton";
import { SkeletonCard, SkeletonLine } from "../../primitives/Skeleton";
import { PullToRefresh } from "../../primitives/PullToRefresh";
import { BottomSheet } from "../../primitives/BottomSheet";
import { useHaptic } from "../../hooks/useHaptic";

// -- Types -----------------------------------------------------------------------

interface WorkflowRun {
  id: string | number;
  name?: string;
  head_branch?: string;
  html_url?: string;
  run_started_at?: string;
  created_at?: string;
  runner_name?: string;
  runner?: { name?: string };
  triggering_actor?: { login?: string };
  actor?: { login?: string };
  repository?: { name?: string };
}

interface QueueData {
  in_progress?: WorkflowRun[];
  queued?: WorkflowRun[];
  total?: number;
}

type FilterValue = "all" | "running" | "queued" | "failed";

interface RunDetail {
  run: WorkflowRun;
  status: FilterValue;
  repo: string;
  elapsed: string;
}

// -- Constants -------------------------------------------------------------------

const FILTER_OPTIONS = [
  { label: "All", value: "all" },
  { label: "Running", value: "running" },
  { label: "Queued", value: "queued" },
  { label: "Failed", value: "failed" },
];

const POLL_INTERVAL_MS = 15_000;

// -- Helpers ---------------------------------------------------------------------

function formatDuration(seconds: number): string {
  if (!seconds || seconds < 0) return "-";
  if (seconds < 60) return `${seconds}s`;
  return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
}

function elapsedSeconds(run: WorkflowRun): number {
  const start = run.run_started_at ?? run.created_at;
  if (!start) return 0;
  return Math.round((Date.now() - new Date(start).getTime()) / 1000);
}

function elapsedLabel(run: WorkflowRun): string {
  return formatDuration(elapsedSeconds(run));
}

function runRepo(run: WorkflowRun): string {
  return run.repository?.name ?? "";
}

function triggeredBy(run: WorkflowRun): string {
  return run.triggering_actor?.login ?? run.actor?.login ?? "unknown";
}

function runnerName(run: WorkflowRun): string {
  return run.runner_name ?? run.runner?.name ?? "-";
}

function statusTone(
  status: FilterValue,
): "warning" | "info" | "danger" | "neutral" {
  if (status === "running") return "warning";
  if (status === "queued") return "info";
  if (status === "failed") return "danger";
  return "neutral";
}

function statusLabel(status: FilterValue): string {
  if (status === "running") return "running";
  if (status === "queued") return "queued";
  if (status === "failed") return "failed";
  return "unknown";
}

// -- Sub-components --------------------------------------------------------------

interface RunCardProps {
  elapsed: string;
  repo: string;
  run: WorkflowRun;
  status: FilterValue;
  onClick: () => void;
}

function RunCard({ elapsed, repo, run, status, onClick }: RunCardProps) {
  return (
    <button
      aria-label={`${run.name ?? "Workflow run"} in ${repo}, ${statusLabel(status)}, ${elapsed}`}
      className="queue-mobile-run-card"
      onClick={onClick}
      style={{
        background: "var(--bg-secondary)",
        border: "1px solid var(--border)",
        borderRadius: 10,
        cursor: "pointer",
        display: "block",
        marginBottom: 10,
        padding: "12px 14px",
        textAlign: "left",
        width: "100%",
      }}
      type="button"
    >
      <div
        style={{
          alignItems: "center",
          display: "flex",
          justifyContent: "space-between",
          marginBottom: 6,
        }}
      >
        <span
          style={{
            color: "var(--text-primary)",
            fontSize: 13,
            fontWeight: 600,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
            maxWidth: "60%",
          }}
        >
          {run.name ?? "Workflow run"}
        </span>
        <Badge tone={statusTone(status)} size="sm">
          {statusLabel(status)}
        </Badge>
      </div>
      <div
        style={{
          color: "var(--text-secondary)",
          display: "flex",
          fontSize: 12,
          gap: 8,
          flexWrap: "wrap",
        }}
      >
        <span>{repo || "unknown repo"}</span>
        {run.head_branch && (
          <span style={{ color: "var(--text-muted)" }}>{run.head_branch}</span>
        )}
        <span style={{ color: "var(--text-muted)", marginLeft: "auto" }}>
          {elapsed}
        </span>
      </div>
    </button>
  );
}

// -- Main component --------------------------------------------------------------

export function QueueMobile() {
  const [queueData, setQueueData] = useState<QueueData>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<FilterValue>("all");
  const [refreshing, setRefreshing] = useState(false);
  const [selectedRun, setSelectedRun] = useState<RunDetail | null>(null);
  const [cancelling, setCancelling] = useState<Record<string, boolean>>({});
  const [cancelDone, setCancelDone] = useState<Record<string, boolean>>({});

  const haptic = useHaptic();

  const fetchQueue = useCallback(async () => {
    try {
      const resp = await fetch("/api/queue/status");
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const json: QueueData = await resp.json();
      setQueueData(json);
      setError(null);
    } catch (e: unknown) {
      const message =
        e instanceof Error ? e.message : "Failed to load queue data";
      setError(message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchQueue();
    const interval = setInterval(fetchQueue, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [fetchQueue]);

  const handleRefresh = useCallback(async () => {
    haptic.medium();
    setRefreshing(true);
    await fetchQueue();
    haptic.success();
  }, [fetchQueue, haptic]);

  // Flatten in_progress and queued into a unified list with status tags.
  const allRuns: RunDetail[] = useMemo(() => {
    const inProgress = (queueData.in_progress ?? []).map((run) => ({
      run,
      status: "running" as FilterValue,
      repo: runRepo(run),
      elapsed: elapsedLabel(run),
    }));
    const queued = (queueData.queued ?? []).map((run) => ({
      run,
      status: "queued" as FilterValue,
      repo: runRepo(run),
      elapsed: elapsedLabel(run),
    }));
    // "failed" would require a separate API call; we surface the concept in the
    // filter but show an empty state since the queue endpoint only returns active runs.
    return [...inProgress, ...queued];
  }, [queueData]);

  const filtered = useMemo(() => {
    if (filter === "all") return allRuns;
    if (filter === "failed") return []; // not in this endpoint's data
    return allRuns.filter((item) => item.status === filter);
  }, [allRuns, filter]);

  const handleCancelRun = useCallback(
    async (detail: RunDetail) => {
      const key = `${detail.repo}/${detail.run.id}`;
      if (!detail.repo) return;
      setCancelling((prev) => ({ ...prev, [key]: true }));
      try {
        const resp = await fetch(
          `/api/runs/${detail.repo}/cancel/${detail.run.id}`,
          {
            method: "POST",
            headers: { "X-Requested-With": "XMLHttpRequest" },
          },
        );
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        setCancelDone((prev) => ({ ...prev, [key]: true }));
        haptic.success();
        setTimeout(fetchQueue, 1500);
      } catch {
        haptic.error();
      } finally {
        setCancelling((prev) => ({ ...prev, [key]: false }));
      }
    },
    [fetchQueue, haptic],
  );

  const handleRerunRun = useCallback(
    async (detail: RunDetail) => {
      if (!detail.repo || !detail.run.id) return;
      try {
        const resp = await fetch(
          `/api/runs/${detail.repo}/rerun/${detail.run.id}`,
          {
            method: "POST",
            headers: { "X-Requested-With": "XMLHttpRequest" },
          },
        );
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        haptic.success();
        setTimeout(fetchQueue, 1500);
      } catch {
        haptic.error();
      }
    },
    [fetchQueue, haptic],
  );

  // Loading skeleton
  if (loading) {
    return (
      <div
        aria-busy="true"
        aria-label="Loading queue"
        aria-live="polite"
        className="queue-mobile-loading"
        role="status"
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 12,
          padding: 16,
        }}
      >
        <SkeletonLine height={20} width="50%" />
        <SkeletonLine height={36} width="100%" />
        <SkeletonCard lines={3} />
        <SkeletonCard lines={3} />
        <SkeletonCard lines={3} />
      </div>
    );
  }

  // Error state (only if no data at all)
  if (error && allRuns.length === 0) {
    return (
      <div
        aria-live="assertive"
        className="queue-mobile-error"
        role="alert"
        style={{
          color: "var(--accent-red)",
          padding: "24px",
          textAlign: "center",
        }}
      >
        <div style={{ marginBottom: 12 }}>{error}</div>
        <TouchButton onClick={fetchQueue} variant="primary">
          Retry
        </TouchButton>
      </div>
    );
  }

  const selectedKey = selectedRun
    ? `${selectedRun.repo}/${selectedRun.run.id}`
    : null;

  return (
    <section
      aria-label="Queue and Workflows"
      className="queue-mobile"
      style={{ padding: "12px 12px 24px" }}
    >
      {/* KPI strip */}
      <div
        aria-label="Queue summary"
        className="queue-mobile-kpi-strip"
        style={{
          display: "flex",
          gap: 8,
          justifyContent: "space-around",
          marginBottom: 14,
          padding: "10px 0",
          borderBottom: "1px solid var(--border)",
        }}
      >
        {[
          {
            label: "Running",
            value: queueData.in_progress?.length ?? 0,
            color: "var(--accent-yellow)",
          },
          {
            label: "Queued",
            value: queueData.queued?.length ?? 0,
            color: "var(--accent-blue)",
          },
          {
            label: "Total",
            value: queueData.total ?? allRuns.length,
            color: "var(--text-secondary)",
          },
        ].map(({ label, value, color }) => (
          <div key={label} style={{ textAlign: "center" }}>
            <div
              style={{
                color,
                fontSize: 22,
                fontVariantNumeric: "tabular-nums",
                fontWeight: 700,
                lineHeight: 1,
              }}
            >
              {value}
            </div>
            <div
              style={{
                color: "var(--text-muted)",
                fontSize: 11,
                marginTop: 2,
                textTransform: "uppercase",
              }}
            >
              {label}
            </div>
          </div>
        ))}
      </div>

      {/* Filter tabs */}
      <SegmentedControl
        ariaLabel="Filter workflow runs"
        onChange={(v) => setFilter(v as FilterValue)}
        options={FILTER_OPTIONS}
        value={filter}
      />

      {/* Run list */}
      <div aria-live="polite" style={{ marginTop: 14 }}>
        <PullToRefresh onRefresh={handleRefresh} disabled={refreshing}>
          {filtered.length === 0 ? (
            <div
              aria-label={
                filter === "failed"
                  ? "No failed runs in queue view"
                  : `No ${filter === "all" ? "" : filter + " "}runs at this time`
              }
              className="queue-mobile-empty"
              style={{
                color: "var(--text-muted)",
                padding: "40px 0",
                textAlign: "center",
              }}
            >
              {filter === "failed"
                ? "Failed runs are not tracked in the live queue. Check the Workflows tab for run history."
                : filter === "all"
                  ? "No active workflow runs. All runners are idle."
                  : `No ${filter} runs right now.`}
            </div>
          ) : (
            filtered.map((item) => (
              <RunCard
                key={`${item.repo}/${item.run.id}`}
                elapsed={item.elapsed}
                repo={item.repo}
                run={item.run}
                status={item.status}
                onClick={() => {
                  haptic.light();
                  setSelectedRun(item);
                }}
              />
            ))
          )}
        </PullToRefresh>
      </div>

      {/* Detail BottomSheet */}
      <BottomSheet
        isOpen={!!selectedRun}
        onClose={() => setSelectedRun(null)}
        title={selectedRun?.run.name ?? "Workflow run"}
      >
        {selectedRun && (
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            {/* Meta rows */}
            <div
              style={{
                background: "var(--bg-tertiary)",
                borderRadius: 8,
                display: "flex",
                flexDirection: "column",
                gap: 8,
                padding: "12px 14px",
              }}
            >
              {[
                { label: "Repo", value: selectedRun.repo || "-" },
                {
                  label: "Branch",
                  value: selectedRun.run.head_branch || "-",
                },
                {
                  label: "Triggered by",
                  value: triggeredBy(selectedRun.run),
                },
                { label: "Runner", value: runnerName(selectedRun.run) },
                { label: "Elapsed", value: selectedRun.elapsed },
                { label: "Status", value: statusLabel(selectedRun.status) },
              ].map(({ label, value }) => (
                <div
                  key={label}
                  style={{
                    alignItems: "center",
                    display: "flex",
                    justifyContent: "space-between",
                  }}
                >
                  <span
                    style={{ color: "var(--text-muted)", fontSize: 12 }}
                  >
                    {label}
                  </span>
                  <span
                    style={{
                      color: "var(--text-primary)",
                      fontSize: 13,
                      fontWeight: 500,
                    }}
                  >
                    {value}
                  </span>
                </div>
              ))}
            </div>

            {/* Action buttons */}
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {selectedRun.run.html_url && (
                <TouchButton
                  aria-label="View run on GitHub"
                  onClick={() => {
                    window.open(
                      selectedRun.run.html_url,
                      "_blank",
                      "noopener,noreferrer",
                    );
                  }}
                  variant="default"
                  style={{ minHeight: 48, width: "100%" }}
                >
                  View on GitHub
                </TouchButton>
              )}

              <TouchButton
                aria-label="Re-run workflow"
                disabled={
                  !selectedRun.repo ||
                  cancelDone[selectedKey!] === true
                }
                onClick={() => handleRerunRun(selectedRun)}
                variant="primary"
                style={{ minHeight: 48, width: "100%" }}
              >
                Re-run
              </TouchButton>

              {selectedRun.status === "running" && selectedRun.repo && (
                <TouchButton
                  aria-label="Cancel run"
                  disabled={
                    cancelling[selectedKey!] === true ||
                    cancelDone[selectedKey!] === true
                  }
                  onClick={() => handleCancelRun(selectedRun)}
                  variant="danger"
                  style={{ minHeight: 48, width: "100%" }}
                >
                  {cancelDone[selectedKey!]
                    ? "Cancelled"
                    : cancelling[selectedKey!]
                      ? "Cancelling..."
                      : "Cancel"}
                </TouchButton>
              )}
            </div>
          </div>
        )}
      </BottomSheet>
    </section>
  );
}
