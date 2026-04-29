"use client";

import { useState, useEffect } from "react";
import {
  ReactFlow,
  Background,
  useNodesState,
  useEdgesState,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

function CustomNode({ data }: { data: any }) {
  return (
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
  );
}

const nodeTypes = {
  customNode: CustomNode,
};

export function GraphCanvas({ data }: { data: any }) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNode, setSelectedNode] = useState<any>(null);

  useEffect(() => {
    if (data && data.graph) {
      setNodes(data.graph.nodes || []);
      setEdges(data.graph.edges || []);
    }
  }, [data, setNodes, setEdges]);

  const handleNodeClick = (_: any, node: any) => {
    const fileData = data.files[node.id];
    if (fileData) {
      setSelectedNode({ id: node.id, ...fileData });
    }
  };

  return (
    <div className="flex-1 flex flex-col bg-surface relative overflow-hidden">
      <div className="p-lg flex justify-between items-center z-10 relative pointer-events-none">
        <div className="pointer-events-auto">
          <h1 className="font-h1 text-h1 text-on-surface">System Architecture Map</h1>
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
                onClick={() => setSelectedNode(null)}
              >
                <span className="material-symbols-outlined text-[18px]">close</span>
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
                  <p className="font-body-md text-body-md text-on-surface-variant">No content available.</p>
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
                        <span key={i} className="bg-surface-container px-2 py-1 rounded text-xs font-code text-on-surface-variant truncate max-w-full">
                          {imp}
                        </span>
                      ))
                    ) : (
                      <span className="text-xs text-on-surface-variant">None detected</span>
                    )}
                  </div>
                </div>
              </div>
            </div>
            <div className="p-4 border-t border-surface-variant bg-surface shrink-0">
              <button className="w-full py-2 bg-primary text-on-primary font-ui-label text-ui-label rounded-md hover:bg-on-primary-fixed-variant transition-colors">
                View Source
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
