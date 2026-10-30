import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  type Edge,
  type Node
} from "@xyflow/react";
import { EmptyState, ErrorState, LoadingState, PageHeader, StatusPill } from "../components/Feedback";
import { getDependencyGraph } from "../services/api";
import { useAsyncResource } from "../hooks/useAsyncResource";

export function DependencyMapPage() {
  const graph = useAsyncResource("dependency-graph", getDependencyGraph, 15000);
  const navigate = useNavigate();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const nodes = useMemo<Node[]>(() => (graph.data?.nodes ?? []).map((item, index) => ({
    id: item.id,
    position: { x: (index % 3) * 250, y: Math.floor(index / 3) * 150 },
    data: { label: `${item.name}\n${item.health_status}` },
    style: {
      background: "#111a28",
      color: "#e5edf6",
      border: `1px solid ${item.health_status === "CRITICAL" ? "#f17883" : item.health_status === "DEGRADED" ? "#f0b970" : "#33445b"}`,
      borderRadius: 10,
      width: 180,
      padding: 14,
      whiteSpace: "pre-line"
    }
  })), [graph.data]);
  const edges = useMemo<Edge[]>(() => (graph.data?.edges ?? []).map((item) => ({
    id: `${item.upstream_service_id}-${item.downstream_service_id}`,
    source: item.upstream_service_id,
    target: item.downstream_service_id,
    animated: false,
    style: { stroke: "#51627a", strokeWidth: 1.5 }
  })), [graph.data]);
  const selected = graph.data?.nodes.find((item) => item.id === selectedId);

  if (graph.loading) return <LoadingState label="Loading service dependency graph…" />;
  if (graph.error) return <ErrorState message={graph.error} onRetry={graph.reload} />;

  return (
    <div className="page-stack">
      <PageHeader title="Service dependency map" subtitle="Explore upstream and downstream relationships backed by registered services." action={<span className="panel-meta">{nodes.length} nodes · {edges.length} edges</span>} />
      {nodes.length === 0 ? <EmptyState title="No dependency graph is available" children="Register services or start the simulator to create a sample service graph." /> : (
        <div className="dependency-layout">
          <section className="panel graph-panel">
            <ReactFlow
              nodes={nodes}
              edges={edges}
              fitView
              onNodeClick={(_, node) => setSelectedId(node.id)}
              onNodeDoubleClick={(_, node) => navigate(`/services/${node.id}`)}
              proOptions={{ hideAttribution: true }}
            >
              <Background color="#243246" gap={24} />
              <Controls />
              <MiniMap nodeColor={(node) => String(node.style?.border ?? "#33445b")} maskColor="rgba(5, 10, 18, 0.7)" />
            </ReactFlow>
          </section>
          <aside className="panel graph-inspector">
            <div className="panel-heading"><h2>Service details</h2></div>
            {!selected ? <EmptyState title="Select a service node" children="Double-click a node to open its monitoring detail." /> : (
              <div className="inspector-content">
                <h3>{selected.name}</h3>
                <StatusPill value={selected.health_status} />
                <div className="inspector-row"><span>Data source</span><strong>{selected.is_simulated ? "SIMULATED" : "AGENT / IMPORTED"}</strong></div>
                {selected.latest_metrics && <>
                  <div className="inspector-row"><span>CPU</span><strong>{selected.latest_metrics.cpu_utilization.toFixed(1)}%</strong></div>
                  <div className="inspector-row"><span>Memory</span><strong>{selected.latest_metrics.memory_utilization.toFixed(1)}%</strong></div>
                  <div className="inspector-row"><span>Response</span><strong>{selected.latest_metrics.response_time_ms.toFixed(0)} ms</strong></div>
                  <div className="inspector-row"><span>Availability</span><strong>{selected.latest_metrics.service_availability.toFixed(2)}%</strong></div>
                </>}
                <button className="button button-secondary full-width" onClick={() => navigate(`/services/${selected.id}`)}>Open service</button>
              </div>
            )}
          </aside>
        </div>
      )}
    </div>
  );
}
