import { Node, Edge } from '@xyflow/react';

export interface FileData {
  label: string;
  imports: string[];
  icon: string;
  content: string;
}

export interface FileMap {
  [filepath: string]: FileData;
}

export interface CustomNodeData extends Record<string, unknown> {
  label: string;
  icon: string;
  highlight?: boolean;
}

export type GraphNode = Node<CustomNodeData>;
export type GraphEdge = Edge;

export interface GraphDataPayload {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface UploadResponse {
  message: string;
  graph: GraphDataPayload;
  files: FileMap;
}

export interface NodeDetail extends FileData {
  id: string;
}

export interface ChatRequest {
  message: string;
  context?: Record<string, unknown>;
}

export interface ChatResponse {
  reply?: string;
  detail?: string;
}
