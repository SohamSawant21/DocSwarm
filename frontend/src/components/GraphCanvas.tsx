"use client";

import { useState, useEffect } from "react";
import dagre from "dagre";
import {
  ReactFlow,
  Background,
  Handle,
  Position,
  useNodesState,
  useEdgesState,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import Editor from "@monaco-editor/react";
import type { UploadResponse, CustomNodeData, GraphNode, GraphEdge, NodeDetail } from "@/types";
import type { ReactFlowInstance } from "@xyflow/react";

function CustomNode({ data }: { data: CustomNodeData }) {
  return (
    <>
      <Handle type="target" position={Position.Left} />

      <div className="flex flex-col items-center gap-2 cursor-pointer group">
        <div
          className={`w-12 h-12 rounded-full flex items-center justify-center border shadow-sm transition-transform hover:scale-105 ${
            data.highlight
              ? "bg-primary-fixed border-primary shadow-[0_4px_24px_rgba(29,78,216,0.15)] ring-4 ring-primary-fixed-dim ring-opacity-20"
              : "bg-surface-container border-outline-variant group-hover:border-primary"
          }`}
        >
          <span
            className={`material-symbols-outlined text-[24px] ${
              data.highlight ? "text-on-primary-fixed" : "text-on-surface"
            }`}
          >
            {data.icon}
          </span>
        </div>
        <span
          className={`font-ui-label text-ui-label ${
            data.highlight
              ? "text-on-surface font-semibold bg-surface-bright px-2 py-1 rounded"
              : "text-on-surface-variant group-hover:text-on-surface"
          }`}
        >
          {data.label}
        </span>
      </div>
      <Handle type="source" position={Position.Right} />
    </>
  );
}

const nodeTypes = {
  customNode: CustomNode,
};

// --- DAGRE LAYOUT ENGINE SETUP ---
const getLayoutedElements = (nodes: GraphNode[], edges: GraphEdge[], direction = "LR") => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  dagreGraph.setGraph({ rankdir: direction });

  nodes.forEach((node) => {
    // Setting dimensions based on your custom node to ensure proper spacing
    dagreGraph.setNode(node.id, { width: 150, height: 80 });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const newNodes: GraphNode[] = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    return {
      ...node,
      targetPosition: Position.Left,
      sourcePosition: Position.Right,
      position: {
        x: nodeWithPosition.x - 75, // Center offset (width / 2)
        y: nodeWithPosition.y - 40, // Center offset (height / 2)
      },
    };
  });

  return { nodes: newNodes, edges };
};
// ---------------------------------

const getLanguage = (filename: string) => {
  const ext = filename.split('.').pop()?.toLowerCase();
  switch (ext) {
    case 'js':
    case 'jsx': return 'javascript';
    case 'ts':
    case 'tsx': return 'typescript';
    case 'py': return 'python';
    case 'json': return 'json';
    case 'md': return 'markdown';
    case 'html': return 'html';
    case 'css': return 'css';
    default: return 'plaintext';
  }
};

export function GraphCanvas({ 
  data,
  selectedNodeId,
  onSelectNode
}: { 
  data: UploadResponse;
  selectedNodeId: string | null;
  onSelectNode: (id: string | null) => void;
}) {
  const [nodes, setNodes, onNodesChange] = useNodesState<GraphNode>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<GraphEdge>([]);
  const [isSourceModalOpen, setIsSourceModalOpen] = useState(false);
  const [reactFlowInstance, setReactFlowInstance] = useState<ReactFlowInstance<GraphNode, GraphEdge> | null>(null);

  const selectedNode = selectedNodeId && data.files[selectedNodeId]
    ? { id: selectedNodeId, ...data.files[selectedNodeId] }
    : null;

  useEffect(() => {
    if (data && data.graph) {
      const rawNodes = data.graph.nodes || [];
      const rawEdges = data.graph.edges || [];

      // Calculate layout before setting state
      const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
        rawNodes,
        rawEdges,
        "LR" // Left-to-Right flow. Change to "TB" for Top-to-Bottom.
      );

      setNodes(layoutedNodes);
      setEdges(layoutedEdges);
    }
  }, [data, setNodes, setEdges]);

  // Synchronize selection highlight
  useEffect(() => {
    setNodes((nds) =>
      nds.map((n) => ({
        ...n,
        data: {
          ...n.data,
          highlight: n.id === selectedNodeId,
        },
      }))
    );
  }, [selectedNodeId, setNodes]);

  // Center node on selection
  useEffect(() => {
    if (reactFlowInstance && selectedNodeId && nodes.length > 0) {
      const node = nodes.find((n) => n.id === selectedNodeId);
      if (node && node.position) {
        // Offset centering slightly to account for the right-side metadata panel
        reactFlowInstance.setCenter(node.position.x + 75, node.position.y + 40, {
          zoom: 1.2,
          duration: 800,
        });
      }
    }
  }, [selectedNodeId, reactFlowInstance, nodes]);

  const handleNodeClick = (_: React.MouseEvent, node: GraphNode) => {
    onSelectNode(node.id === selectedNodeId ? null : node.id);
  };

  return (
    <div className="flex-1 flex flex-col bg-surface relative overflow-hidden">
      <div className="p-lg flex justify-between items-center z-10 relative pointer-events-none">
        <div className="pointer-events-auto">
          <h1 className="font-h1 text-h1 text-on-surface">
            System Architecture Map
          </h1>
          <p className="font-body-md text-body-md text-on-surface-variant mt-1">
            Exploring dependencies for current context.
          </p>
        </div>
      </div>

      <div className="flex-1 relative w-full h-full">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={nodeTypes}
          fitView
          onInit={setReactFlowInstance}
          proOptions={{ hideAttribution: true }}
          onNodeClick={handleNodeClick}
        >
          <Background color="#e2e1ed" gap={16} />
        </ReactFlow>

        {/* Integrated Sidebar Panel for Metadata (overlaying graph) */}
        {selectedNode && (
          <div className="absolute right-6 top-6 bottom-6 w-80 bg-surface-bright border border-surface-variant rounded-xl shadow-[0_8px_32px_rgba(0,0,0,0.03)] flex flex-col overflow-hidden z-30 pointer-events-auto max-h-[calc(100%-48px)]">
            <div className="p-4 border-b border-surface-variant flex justify-between items-center bg-surface shrink-0">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-primary text-[20px]">
                  {selectedNode.icon || "description"}
                </span>
                <h3 className="font-ui-label text-ui-label text-on-surface truncate">
                  {selectedNode.label}
                </h3>
              </div>
                <button
                  className="text-on-surface-variant hover:text-on-surface"
                  onClick={() => onSelectNode(null)}
                >
                  <span className="material-symbols-outlined text-[18px]">
                    close
                  </span>
                </button>
            </div>
            <div className="p-4 flex-1 overflow-y-auto">
              <div className="mb-6">
                {selectedNode.content ? (
                  <pre className="text-xs overflow-x-auto text-outline font-code bg-surface p-2 rounded border border-surface-variant">
                    {selectedNode.content.substring(0, 500)}
                    {selectedNode.content.length > 500 && "..."}
                  </pre>
                ) : (
                  <p className="font-body-md text-body-md text-on-surface-variant">
                    No content available.
                  </p>
                )}
              </div>
              <div className="space-y-4">
                <div>
                  <span className="font-ui-label text-ui-label text-outline uppercase tracking-wider text-[10px] block mb-1">
                    Dependencies
                  </span>
                  <div className="flex flex-wrap gap-2">
                    {selectedNode.imports?.length > 0 ? (
                      selectedNode.imports.map((imp: string, i: number) => (
                        <span
                          key={i}
                          className="bg-surface-container px-2 py-1 rounded text-xs font-code text-on-surface-variant truncate max-w-full"
                        >
                          {imp}
                        </span>
                      ))
                    ) : (
                      <span className="text-xs text-on-surface-variant">
                        None detected
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>
            <div className="p-4 border-t border-surface-variant bg-surface shrink-0">
              <button 
                className="w-full py-2 bg-primary text-on-primary font-ui-label text-ui-label rounded-md hover:bg-on-primary-fixed-variant transition-colors"
                onClick={() => setIsSourceModalOpen(true)}
              >
                View Source
              </button>
            </div>
          </div>
        )}

        {/* Source Code Modal Overlay */}
        {isSourceModalOpen && selectedNode && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-8">
            <div className="bg-surface-bright border border-surface-variant rounded-xl shadow-2xl flex flex-col w-full max-w-5xl h-full max-h-[85vh] overflow-hidden">
              <div className="p-4 border-b border-surface-variant flex justify-between items-center bg-surface shrink-0">
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-primary text-[20px]">
                    code
                  </span>
                  <h3 className="font-ui-label text-ui-label text-on-surface truncate">
                    {selectedNode.id}
                  </h3>
                </div>
                <button
                  className="text-on-surface-variant hover:text-on-surface"
                  onClick={() => setIsSourceModalOpen(false)}
                >
                  <span className="material-symbols-outlined text-[24px]">
                    close
                  </span>
                </button>
              </div>
              <div className="flex-1 bg-[#1e1e1e] overflow-hidden">
                <Editor
                  height="100%"
                  language={getLanguage(selectedNode.id)}
                  theme="vs-dark"
                  value={selectedNode.content || ""}
                  options={{
                    readOnly: true,
                    minimap: { enabled: true },
                    scrollBeyondLastLine: false,
                    wordWrap: "on",
                    fontSize: 14,
                  }}
                />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}