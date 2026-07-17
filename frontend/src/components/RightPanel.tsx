"use client";

import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { endpoints } from "@/lib/api";
import type { FileData } from "@/types";

type Message = {
  id: string;
  sender: "user" | "ai";
  text: string;
};

export function RightPanel({ 
  selectedNodeId, 
  selectedNodeData 
}: { 
  selectedNodeId?: string | null;
  selectedNodeData?: FileData | null;
}) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMsg: Message = { id: Date.now().toString(), sender: "user", text: input.trim() };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsLoading(true);

    const contextPayload: {
      selectedFile?: {
        id: string;
        path: string;
        imports: string[];
        content: string;
        role: string;
      };
    } = {};
    if (selectedNodeId && selectedNodeData) {
      contextPayload.selectedFile = {
        id: selectedNodeId,
        path: selectedNodeId,
        imports: selectedNodeData.imports,
        content: selectedNodeData.content,
        role: "File" // Fallback role, can be enhanced later
      };
    }

    try {
      const response = await fetch(endpoints.chat, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message: userMsg.text, context: contextPayload }),
      });
      const data = await response.json();
      
      let replyText = data.reply;
      if (!response.ok) {
        replyText = `Error: ${data.detail || "Server error"}`;
      } else if (!replyText) {
        replyText = "Error: No response from AI.";
      }
      
      const aiMsg: Message = { id: (Date.now() + 1).toString(), sender: "ai", text: replyText };
      setMessages((prev) => [...prev, aiMsg]);
    } catch (error) {
      console.error("Chat error:", error);
      const errorMsg: Message = { id: (Date.now() + 1).toString(), sender: "ai", text: "Error: Could not connect to chat server." };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="w-full md:w-2/5 lg:w-1/3 border-l border-surface-variant bg-surface-bright flex flex-col overflow-hidden h-full">
      <div className="flex-1 overflow-y-auto p-6 flex flex-col">
        {messages.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center text-center text-on-surface-variant p-8">
            <span className="material-symbols-outlined text-[48px] text-outline mb-4">forum</span>
            <h3 className="font-h2 text-h2 text-on-surface mb-2">DocSwarm AI</h3>
            <p className="font-body-md text-[14px]">
              Ask questions about the uploaded architecture. I can help explain dependencies, module logic, and system structure.
            </p>
          </div>
        ) : (
          <div className="space-y-6 pt-4 pb-4">
            {messages.map((msg) => (
              <div key={msg.id} className={`flex gap-3 ${msg.sender === 'user' ? 'flex-row-reverse' : ''}`}>
                {msg.sender === "ai" ? (
                  <div className="w-8 h-8 rounded-full bg-primary-container overflow-hidden flex-shrink-0 flex items-center justify-center text-primary border border-primary-fixed-dim">
                    <span className="material-symbols-outlined text-[16px]">smart_toy</span>
                  </div>
                ) : (
                  <div className="w-8 h-8 rounded-full bg-surface-container overflow-hidden flex-shrink-0 border border-outline-variant flex items-center justify-center text-on-surface-variant">
                    <span className="material-symbols-outlined text-[16px]">person</span>
                  </div>
                )}
                
                <div className={`max-w-[85%] ${msg.sender === 'user' ? 'text-right' : ''}`}>
                  <div className={`flex items-baseline gap-2 mb-1 ${msg.sender === 'user' ? 'justify-end' : ''}`}>
                    <span className="font-ui-label text-[13px] text-on-surface">
                      {msg.sender === "ai" ? "DocSwarm AI" : "You"}
                    </span>
                  </div>
                  <div className={`font-body-md p-3 rounded-lg border inline-block text-left ${
                    msg.sender === 'user' 
                      ? 'bg-[#F1F1EF] border-transparent text-slate-800 rounded-tr-none' 
                      : 'bg-surface-container-low border-surface-variant text-on-surface-variant rounded-tl-none'
                  }`}>
                    {msg.sender === "ai" ? (
                      <div className="prose-chat">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {msg.text}
                        </ReactMarkdown>
                      </div>
                    ) : (
                      <p className="text-[14px]">{msg.text}</p>
                    )}
                  </div>
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="flex gap-3">
                <div className="w-8 h-8 rounded-full bg-primary-container overflow-hidden flex-shrink-0 flex items-center justify-center text-primary border border-primary-fixed-dim">
                  <span className="material-symbols-outlined text-[16px]">smart_toy</span>
                </div>
                <div>
                  <div className="flex items-baseline gap-2 mb-1">
                    <span className="font-ui-label text-[13px] text-on-surface">DocSwarm AI</span>
                  </div>
                  <p className="font-body-md text-[14px] text-on-surface-variant bg-surface-container-low p-3 rounded-lg rounded-tl-none border border-surface-variant inline-block">
                    <span className="animate-pulse">Thinking...</span>
                  </p>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Persistent Chat Bar at bottom of right column */}
      <div className="p-4 border-t border-surface-variant bg-surface-bright shrink-0">
        <div className="max-w-3xl mx-auto w-full mb-2">
          <span className="text-[11px] font-ui-label text-on-surface-variant uppercase tracking-wider">
            Current Context: <strong className="text-primary truncate">{selectedNodeId || "Repository Overview"}</strong>
          </span>
        </div>
        <form className="max-w-3xl mx-auto w-full" onSubmit={handleSubmit}>
          <div className="relative flex items-center bg-[#f6f6f8] rounded-full border border-[#d1d5db] px-4 py-2 shadow-sm group focus-within:border-primary/50 transition-all">
            <input
              className="flex-1 bg-transparent border-none p-0 font-body-md text-[14px] text-slate-600 placeholder-slate-400 focus:ring-0 focus:outline-none"
              placeholder="Ask about this context..."
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={isLoading}
            />
            <button 
              type="submit"
              disabled={isLoading || !input.trim()}
              className="flex-shrink-0 w-8 h-8 rounded-full bg-[#0037b0] text-white flex items-center justify-center hover:bg-blue-800 transition-colors shadow-md ml-3 disabled:opacity-50 disabled:hover:bg-[#0037b0]"
            >
              <span className="material-symbols-outlined text-[18px]">
                arrow_upward
              </span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
