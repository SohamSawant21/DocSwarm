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
  getNodesBounds,
  getViewportForBounds,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { toPng, toSvg } from "html-to-image";
import toast from "react-hot-toast";
import Editor from "@monaco-editor/react";
import type { UploadResponse, CustomNodeData, GraphNode, GraphEdge } from "@/types";
import type { ReactFlowInstance } from "@xyflow/react";
import { getIconForFile } from "@/utils/fileIcons";

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
          {(() => {
            const Icon = getIconForFile(data.label || "").icon;
            return (
              <Icon
                size={18}
                strokeWidth={1.5}
                className={data.highlight ? "text-on-primary-fixed" : "text-on-surface"}
              />
            );
          })()}
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
    dagreGraph.setNode(node.id, { width: 112.5, height: 60 });
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
        x: nodeWithPosition.x - 56.25, // Center offset (width / 2)
        y: nodeWithPosition.y - 30, // Center offset (height / 2)
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
  onSelectNode,
  activeFileContent,
  isFileLoading
}: { 
  data: UploadResponse;
  selectedNodeId: string | null;
  onSelectNode: (id: string | null) => void;
  activeFileContent?: string | null;
  isFileLoading?: boolean;
}) {
  const [nodes, setNodes, onNodesChange] = useNodesState<GraphNode>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<GraphEdge>([]);
  const [isSourceModalOpen, setIsSourceModalOpen] = useState(false);
  const [reactFlowInstance, setReactFlowInstance] = useState<ReactFlowInstance<GraphNode, GraphEdge> | null>(null);
  const [isExporting, setIsExporting] = useState<boolean>(false);

  const handleExport = async (format: "png" | "svg") => {
    if (nodes.length === 0 || !reactFlowInstance) {
      toast.error("Graph is empty, nothing to export.");
      return;
    }
    setIsExporting(true);
    try {
      const nodesBounds = getNodesBounds(nodes);
      const imageWidth = 1920;
      const imageHeight = 1080;
      
      const targetViewport = getViewportForBounds(
        nodesBounds,
        imageWidth,
        imageHeight,
        0.5,
        2.5,
        0.1
      );

      // The core export target is the viewport, which natively contains nodes and edges
      const viewportEl = document.querySelector(".react-flow__viewport") as HTMLElement;
      if (!viewportEl) {
        throw new Error("Viewport element not found");
      }

      // FIX 1: Ensure all SVGs have proper XML namespaces. 
      // html-to-image uses strict XML serialization internally. Missing xmlns causes SVGs to disappear.
      const allSvgs = document.querySelectorAll(".react-flow svg");
      allSvgs.forEach((svg) => {
        if (!svg.getAttribute("xmlns")) {
          svg.setAttribute("xmlns", "http://www.w3.org/2000/svg");
        }
      });

      // FIX 2: React Flow places arrowheads (<defs>) in a separate SVG outside the viewport.
      // If a <path> references a missing <marker> URL, strict XML parsers drop the ENTIRE edge.
      // We temporarily inject these defs into the viewport before capturing.
      const directSvgs = Array.from(document.querySelectorAll(".react-flow > svg"));
      const injectedDefs: HTMLElement[] = [];
      directSvgs.forEach((svg) => {
        const clone = svg.cloneNode(true) as HTMLElement;
        clone.style.position = "absolute";
        clone.style.width = "0";
        clone.style.height = "0";
        viewportEl.appendChild(clone);
        injectedDefs.push(clone);
      });

      // FIX 3: React Flow dynamically sets explicit pixel widths (e.g., width: 800px) on the edges SVG based on the screen.
      // When html-to-image expands the capture canvas to 1920x1080, edges outside 800x600 get clipped/hidden.
      // We force the edges SVG to expand natively.
      const edgesSvgs = Array.from(document.querySelectorAll(".react-flow__edges"));
      const originalEdgeStyles: { el: HTMLElement; w: string; h: string; ov: string }[] = [];
      edgesSvgs.forEach((svg) => {
        const el = svg as HTMLElement;
        originalEdgeStyles.push({ el, w: el.style.width, h: el.style.height, ov: el.style.overflow });
        el.style.width = "100%";
        el.style.height = "100%";
        el.style.overflow = "visible";
      });

      const exportFunc = format === "png" ? toPng : toSvg;
      
      const dataUrl = await exportFunc(viewportEl, {
        backgroundColor: "#faf8ff",
        width: imageWidth,
        height: imageHeight,
        style: {
          width: `${imageWidth}px`,
          height: `${imageHeight}px`,
          // Overwrite the user's current zoom/pan with the perfectly framed bounds
          transform: `translate(${targetViewport.x}px, ${targetViewport.y}px) scale(${targetViewport.zoom})`,
        },
      });

      // CLEANUP: Restore the DOM to its original state seamlessly
      injectedDefs.forEach((def) => def.remove());
      originalEdgeStyles.forEach(({ el, w, h, ov }) => {
        el.style.width = w;
        el.style.height = h;
        el.style.overflow = ov;
      });

      const a = document.createElement("a");
      a.setAttribute("download", `architecture-graph.${format}`);
      a.setAttribute("href", dataUrl);
      a.click();
      toast.success(`Exported as ${format.toUpperCase()}!`);
    } catch (error) {
      console.error("Export error:", error);
      toast.error(`Failed to export ${format.toUpperCase()}`);
    } finally {
      setIsExporting(false);
    }
  };

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
        reactFlowInstance.setCenter(node.position.x + 56.25, node.position.y + 30, {
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
        <div className="pointer-events-auto flex items-center gap-3">
          <button
            onClick={() => handleExport("png")}
            disabled={isExporting || nodes.length === 0}
            className={`flex items-center gap-2 bg-surface-bright border border-outline-variant text-on-surface text-ui-label font-ui-label px-4 py-2 rounded-md transition-colors shadow-sm ${isExporting || nodes.length === 0 ? "opacity-50 cursor-not-allowed" : "hover:bg-surface-variant active:scale-95"}`}
          >
            <span className="material-symbols-outlined text-[1rem]">image</span>
            PNG
          </button>
          <button
            onClick={() => handleExport("svg")}
            disabled={isExporting || nodes.length === 0}
            className={`flex items-center gap-2 bg-surface-bright border border-outline-variant text-on-surface text-ui-label font-ui-label px-4 py-2 rounded-md transition-colors shadow-sm ${isExporting || nodes.length === 0 ? "opacity-50 cursor-not-allowed" : "hover:bg-surface-variant active:scale-95"}`}
          >
            <span className="material-symbols-outlined text-[1rem]">polyline</span>
            SVG
          </button>
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
                {(() => {
                  const Icon = getIconForFile(selectedNode.label || "").icon;
                  return (
                    <Icon
                      size={15}
                      strokeWidth={1.75}
                      className="text-primary"
                    />
                  );
                })()}
                <h3 className="font-ui-label text-ui-label text-on-surface truncate">
                  {selectedNode.label}
                </h3>
              </div>
                <button
                  className="text-on-surface-variant hover:text-on-surface"
                  onClick={() => onSelectNode(null)}
                >
                  <span className="material-symbols-outlined text-[1.1250rem]">
                    close
                  </span>
                </button>
            </div>
            <div className="p-4 flex-1 overflow-y-auto">
              <div className="mb-6">
                {isFileLoading ? (
                  <div className="flex flex-col items-center justify-center p-4 bg-surface rounded border border-surface-variant">
                    <span className="material-symbols-outlined animate-spin text-primary mb-2">progress_activity</span>
                    <span className="text-xs text-on-surface-variant">Loading content...</span>
                  </div>
                ) : activeFileContent ? (
                  <pre className="text-xs overflow-x-auto text-outline font-code bg-surface p-2 rounded border border-surface-variant">
                    {activeFileContent.substring(0, 500)}
                    {activeFileContent.length > 500 && "..."}
                  </pre>
                ) : (
                  <p className="font-body-md text-body-md text-on-surface-variant">
                    No content available.
                  </p>
                )}
              </div>
              <div className="space-y-4">
                <div>
                  <span className="font-ui-label text-ui-label text-outline uppercase tracking-wider text-[0.6250rem] block mb-1">
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
                  <span className="material-symbols-outlined text-primary text-[1.2500rem]">
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
                  <span className="material-symbols-outlined text-[1.5000rem]">
                    close
                  </span>
                </button>
              </div>
              <div className="flex-1 bg-[#1e1e1e] overflow-hidden">
                <Editor
                  height="100%"
                  language={getLanguage(selectedNode.id)}
                  theme="vs-dark"
                  value={isFileLoading ? "// Loading..." : (activeFileContent || "")}
                  options={{
                    readOnly: true,
                    minimap: { enabled: true },
                    scrollBeyondLastLine: false,
                    wordWrap: "on",
                    fontSize: 11,
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
