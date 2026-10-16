import { useState, useMemo, useCallback } from 'react';
import { useOutletContext } from 'react-router-dom';
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  Handle,
  Position,
  MarkerType
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import {
  getMemberName, getOwnerColor, STATUS_COLORS, STATUS_LABELS
} from '../hooks/useSnapshot';
import TaskDrawer from '../components/TaskDrawer';
import { AlertCircle, AlertTriangle, Milestone, ShieldAlert, GitFork, RefreshCw } from 'lucide-react';
import './Graph.css';

// Custom Node Component
function TaskNode({ data }) {
  const { task, ownerName, ownerColor, isBlockedOrLate, isMilestone } = data;

  const riskBorderColor = task.risk === 'critical' ? 'var(--red)'
    : task.risk === 'at_risk' ? 'var(--amber)'
    : ownerColor;

  return (
    <div
      className={`task-graph-node ${isBlockedOrLate ? 'node-blocked' : ''} ${isMilestone ? 'node-milestone' : ''}`}
      style={{
        borderColor: riskBorderColor,
        boxShadow: isBlockedOrLate
          ? '0 0 16px rgba(248, 81, 73, 0.45)'
          : task.risk === 'critical'
          ? '0 0 12px rgba(248, 81, 73, 0.3)'
          : 'none'
      }}
    >
      <Handle type="target" position={Position.Top} className="flow-handle" />

      <div className="node-top">
        <span className="font-mono node-key">{task.key}</span>
        {isMilestone && (
          <span className="node-milestone-badge">
            <Milestone size={11} />
          </span>
        )}
        <span
          className="node-status-dot"
          style={{ background: STATUS_COLORS[task.status] || '#8B949E' }}
          title={STATUS_LABELS[task.status] || task.status}
        />
      </div>

      <div className="node-title">{task.title}</div>

      <div className="node-bottom">
        <div className="node-owner">
          <span className="owner-dot" style={{ background: ownerColor }} />
          <span>{ownerName}</span>
        </div>
        <span className="node-effort font-mono">{task.effort || 1}h</span>
      </div>

      <Handle type="source" position={Position.Bottom} className="flow-handle" />
    </div>
  );
}

const nodeTypes = {
  taskNode: TaskNode,
};

export default function Graph() {
  const { snapshot, code } = useOutletContext();
  const [selectedTaskKey, setSelectedTaskKey] = useState(null);

  const tasks = useMemo(() => snapshot?.tasks || [], [snapshot]);
  const deps = useMemo(() => snapshot?.deps || [], [snapshot]);
  const members = useMemo(() => snapshot?.members || [], [snapshot]);

  // Compute ripple impact: find blocked tasks and their downstream paths
  const rippleImpact = useMemo(() => {
    const blockedTasks = tasks.filter(t => t.status === 'blocked' || t.risk === 'critical');
    if (blockedTasks.length === 0) return null;

    // Build adjacency list for downstream search: from -> to
    const adj = {};
    deps.forEach(d => {
      if (!adj[d.from]) adj[d.from] = [];
      adj[d.from].push(d.to);
    });

    // Find affected downstream keys
    const affectedKeys = new Set();
    const affectedMilestones = [];

    blockedTasks.forEach(bt => {
      const q = [bt.key];
      while (q.length > 0) {
        const curr = q.shift();
        const neighbors = adj[curr] || [];
        for (const n of neighbors) {
          if (!affectedKeys.has(n)) {
            affectedKeys.add(n);
            q.push(n);
            const targetTask = tasks.find(t => t.key === n);
            if (targetTask?.is_milestone) {
              affectedMilestones.push(targetTask);
            }
          }
        }
      }
    });

    const primaryBlocked = blockedTasks[0];
    const blockedOwner = getMemberName(snapshot, primaryBlocked.owner_member_id);
    const targetMilestone = affectedMilestones[0] || tasks.find(t => t.is_milestone);

    return {
      blockedTask: primaryBlocked,
      blockedOwner,
      targetMilestone,
      affectedKeys,
    };
  }, [tasks, deps, snapshot]);

  // Calculate layout coordinates (DAG layered positioning)
  const { nodes, edges } = useMemo(() => {
    if (tasks.length === 0) return { nodes: [], edges: [] };

    // Compute in-degrees to sort layers
    const inDegree = {};
    const taskMap = {};
    tasks.forEach(t => {
      inDegree[t.key] = 0;
      taskMap[t.key] = t;
    });

    deps.forEach(d => {
      if (inDegree[d.to] !== undefined) {
        inDegree[d.to] += 1;
      }
    });

    // Assign rank / depth
    const depth = {};
    const queue = [];
    tasks.forEach(t => {
      if (inDegree[t.key] === 0) {
        queue.push(t.key);
        depth[t.key] = 0;
      }
    });

    // Build children map
    const children = {};
    deps.forEach(d => {
      if (!children[d.from]) children[d.from] = [];
      children[d.from].push(d.to);
    });

    while (queue.length > 0) {
      const u = queue.shift();
      const uDepth = depth[u] || 0;
      const neighbors = children[u] || [];
      for (const v of neighbors) {
        depth[v] = Math.max(depth[v] || 0, uDepth + 1);
        inDegree[v] -= 1;
        if (inDegree[v] === 0) {
          queue.push(v);
        }
      }
    }

    // Default depth for remaining or cyclic nodes
    tasks.forEach(t => {
      if (depth[t.key] === undefined) depth[t.key] = 0;
    });

    // Group tasks by depth level
    const levels = {};
    tasks.forEach(t => {
      const d = depth[t.key];
      if (!levels[d]) levels[d] = [];
      levels[d].push(t);
    });

    const NODE_WIDTH = 220;
    const NODE_HEIGHT = 100;
    const HORIZONTAL_GAP = 60;
    const VERTICAL_GAP = 120;

    const flowNodes = [];
    Object.keys(levels).forEach(levelStr => {
      const lvl = Number(levelStr);
      const rowTasks = levels[lvl];
      const totalRowWidth = rowTasks.length * (NODE_WIDTH + HORIZONTAL_GAP) - HORIZONTAL_GAP;
      const startX = -totalRowWidth / 2;

      rowTasks.forEach((task, idx) => {
        const x = startX + idx * (NODE_WIDTH + HORIZONTAL_GAP);
        const y = lvl * (NODE_HEIGHT + VERTICAL_GAP) + 60;

        const isBlocked = task.status === 'blocked';
        const isLate = task.risk === 'critical';

        flowNodes.push({
          id: task.key,
          type: 'taskNode',
          position: { x, y },
          data: {
            task,
            ownerName: getMemberName(snapshot, task.owner_member_id),
            ownerColor: getOwnerColor(task.owner_member_id),
            isBlockedOrLate: isBlocked || isLate,
            isMilestone: task.is_milestone,
          },
        });
      });
    });

    // Build flow edges with red glow if downstream of a blocked task
    const flowEdges = deps.map((d, index) => {
      const isDownstreamBlocked = rippleImpact?.affectedKeys.has(d.to) ||
        (rippleImpact?.blockedTask?.key === d.from);

      const isHandoff = d.kind === 'handoff';

      return {
        id: `e-${d.from}-${d.to}-${index}`,
        source: d.from,
        target: d.to,
        animated: isDownstreamBlocked,
        style: {
          stroke: isDownstreamBlocked ? 'var(--red)' : '#8B949E',
          strokeWidth: isDownstreamBlocked ? 2.5 : 1.5,
          strokeDasharray: isHandoff ? '6,6' : undefined,
          filter: isDownstreamBlocked ? 'drop-shadow(0 0 6px rgba(248, 81, 73, 0.8))' : 'none',
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: isDownstreamBlocked ? 'var(--red)' : '#8B949E',
          width: 14,
          height: 14,
        },
      };
    });

    return { nodes: flowNodes, edges: flowEdges };
  }, [tasks, deps, snapshot, rippleImpact]);

  const onNodeClick = useCallback((event, node) => {
    setSelectedTaskKey(node.id);
  }, []);

  return (
    <div className="graph-page">
      {/* Ripple Alert Banner */}
      {rippleImpact && (
        <div className="ripple-alert-banner">
          <div className="ripple-alert-left">
            <ShieldAlert size={20} className="text-red animate-pulse" />
            <div>
              <div className="ripple-alert-headline">
                <strong>{rippleImpact.blockedOwner}</strong> is blocked on{' '}
                <span className="font-mono text-red">{rippleImpact.blockedTask.key}</span>
                {rippleImpact.targetMilestone && (
                  <>
                    {' '}→ <span className="text-amber">"{rippleImpact.targetMilestone.title}"</span> milestone is at risk!
                  </>
                )}
              </div>
              <div className="ripple-alert-sub">
                Downstream dependency paths are glowing red. Check Task Drawer for blocker routing status.
              </div>
            </div>
          </div>

          <button
            className="btn btn-secondary btn-sm"
            onClick={() => setSelectedTaskKey(rippleImpact.blockedTask.key)}
          >
            Inspect Blocker
          </button>
        </div>
      )}

      {/* Header & Legend */}
      <div className="graph-header">
        <div>
          <h1 className="graph-title">Dependency &amp; Ripple Graph</h1>
          <p className="graph-subtitle">
            Live topological DAG. Red glowing edges trace bottleneck propagation to project milestones.
          </p>
        </div>

        {/* Legend */}
        <div className="graph-legend">
          <div className="legend-item">
            <span className="legend-line solid" />
            <span>Hard Dependency</span>
          </div>
          <div className="legend-item">
            <span className="legend-line dashed" />
            <span>Handoff Edge</span>
          </div>
          <div className="legend-item">
            <span className="legend-line glow-red" />
            <span>Slip / Ripple Alert</span>
          </div>
          <div className="legend-item">
            <span className="legend-dot milestone" />
            <span>Milestone</span>
          </div>
        </div>
      </div>

      {/* React Flow Container */}
      <div className="graph-canvas-container">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          onNodeClick={onNodeClick}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          minZoom={0.2}
          maxZoom={1.5}
        >
          <Background color="#30363D" gap={20} size={1} />
          <Controls className="flow-controls-custom" />
          <MiniMap
            className="flow-minimap-custom"
            nodeColor={n => n.data?.ownerColor || '#58A6FF'}
            maskColor="rgba(13, 15, 20, 0.7)"
          />
        </ReactFlow>
      </div>

      {/* Task Drawer */}
      {selectedTaskKey && (
        <TaskDrawer
          taskKey={selectedTaskKey}
          snapshot={snapshot}
          code={code}
          onClose={() => setSelectedTaskKey(null)}
          onOpenTask={key => setSelectedTaskKey(key)}
        />
      )}
    </div>
  );
}
