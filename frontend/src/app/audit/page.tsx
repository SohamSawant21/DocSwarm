"use client";

import { useEffect, useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import { TopAppBar } from "@/components/TopAppBar";
import { SideNav } from "@/components/SideNav";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { useStore } from "@/store/useStore";
import { MarkdownViewer } from "@/components/MarkdownViewer";
import toast from "react-hot-toast";
import { AuditFinding } from "@/types";
import { ChevronDown, ChevronRight, AlertTriangle, ShieldAlert, CheckCircle, FileWarning } from "lucide-react";

const getSeverityColor = (severity: string) => {
  switch (severity) {
    case 'Critical': return 'text-error bg-error/10 border-error/20';
    case 'High': return 'text-orange-500 bg-orange-500/10 border-orange-500/20';
    case 'Medium': return 'text-yellow-500 bg-yellow-500/10 border-yellow-500/20';
    default: return 'text-primary bg-primary/10 border-primary/20';
  }
};

const getCategoryIcon = (issueType: string) => {
  const type = issueType.toLowerCase();
  if (type.includes('security') || type.includes('credential')) return <ShieldAlert size={18} />;
  if (type.includes('architecture')) return <FileWarning size={18} />;
  return <AlertTriangle size={18} />;
};

function FindingCard({ finding, filePath }: { finding: AuditFinding, filePath: string }) {
  const [expanded, setExpanded] = useState(false);
  
  return (
    <div className="bg-surface border border-outline-variant rounded-lg overflow-hidden mb-4">
      <div 
        className="p-4 flex items-start gap-4 cursor-pointer hover:bg-surface-variant transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="mt-1 flex-shrink-0 text-on-surface-variant">
          {expanded ? <ChevronDown size={20} /> : <ChevronRight size={20} />}
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-1">
            <span className={`px-2.5 py-0.5 rounded text-xs font-medium border ${getSeverityColor(finding.severity)}`}>
              {finding.severity}
            </span>
            <div className="flex items-center gap-1.5 text-sm font-medium text-on-surface-variant">
              {getCategoryIcon(finding.issue_type)}
              {finding.issue_type}
            </div>
          </div>
          <h3 className="text-lg font-semibold text-on-surface mb-1">
            {filePath} <span className="text-sm font-normal text-on-surface-variant ml-2">({finding.location})</span>
          </h3>
          <p className="text-sm text-on-surface-variant line-clamp-2">{finding.description}</p>
        </div>
      </div>
      
      {expanded && (
        <div className="p-4 pt-0 border-t border-outline-variant bg-surface-container/30">
          <div className="mt-4">
            <h4 className="text-sm font-bold text-on-surface mb-2 uppercase tracking-wider">Why it matters</h4>
            <p className="text-sm text-on-surface-variant mb-4">{finding.description}</p>
            
            <h4 className="text-sm font-bold text-on-surface mb-2 uppercase tracking-wider">Evidence</h4>
            <div className="mb-4">
              <MarkdownViewer content={`\`\`\`javascript\n${finding.evidence}\n\`\`\``} />
            </div>
            
            <h4 className="text-sm font-bold text-on-surface mb-2 uppercase tracking-wider">Recommended Remediation</h4>
            <div className="text-sm">
              <MarkdownViewer content={finding.remediation} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function AuditDashboard() {
  const router = useRouter();
  const { graphData, reset } = useStore();

  useEffect(() => {
    if (!graphData) {
      toast.error("Session expired or missing. Please upload a repository.");
      router.replace("/");
    }
  }, [graphData, router]);

  const handleReset = () => {
    reset();
    router.replace("/");
  };

  const findings = useMemo(() => {
    const all: { finding: AuditFinding, filePath: string }[] = [];
    if (graphData?.audit_results) {
      Object.values(graphData.audit_results).forEach(fileRes => {
        if (!fileRes.is_safe && fileRes.findings) {
          fileRes.findings.forEach(f => {
            all.push({ finding: f, filePath: fileRes.file_path });
          });
        }
      });
    }
    
    // Sort by severity
    const severityOrder = { 'Critical': 0, 'High': 1, 'Medium': 2, 'Low': 3 };
    all.sort((a, b) => {
      const aVal = severityOrder[a.finding.severity as keyof typeof severityOrder] ?? 4;
      const bVal = severityOrder[b.finding.severity as keyof typeof severityOrder] ?? 4;
      return aVal - bVal;
    });
    
    return all;
  }, [graphData]);

  const counts = useMemo(() => {
    const c = { Critical: 0, High: 0, Medium: 0, Low: 0 };
    findings.forEach(f => {
      if (f.finding.severity in c) {
        c[f.finding.severity as keyof typeof c]++;
      }
    });
    return c;
  }, [findings]);

  if (!graphData) return null;

  return (
    <>
      <TopAppBar onReset={handleReset} />
      <div className="flex-1 flex overflow-hidden relative pt-14">
        <SideNav />
        <main className="flex-1 ml-16 overflow-y-auto bg-surface-container p-8">
          <ErrorBoundary sectionName="Audit Dashboard" onReset={handleReset}>
            <div className="max-w-5xl mx-auto pb-20">
              <div className="mb-8">
                <h1 className="text-3xl font-display font-bold text-on-surface mb-2">Repository Audit</h1>
                <p className="text-on-surface-variant">Automated security and architecture review powered by Gemini.</p>
              </div>
              
              <div className="grid grid-cols-4 gap-4 mb-10">
                <div className="bg-surface p-6 rounded-xl border border-outline-variant shadow-sm flex flex-col items-center justify-center">
                  <span className="text-4xl font-bold text-error mb-2">{counts.Critical}</span>
                  <span className="text-sm font-medium text-on-surface-variant uppercase tracking-wide">Critical</span>
                </div>
                <div className="bg-surface p-6 rounded-xl border border-outline-variant shadow-sm flex flex-col items-center justify-center">
                  <span className="text-4xl font-bold text-orange-500 mb-2">{counts.High}</span>
                  <span className="text-sm font-medium text-on-surface-variant uppercase tracking-wide">High</span>
                </div>
                <div className="bg-surface p-6 rounded-xl border border-outline-variant shadow-sm flex flex-col items-center justify-center">
                  <span className="text-4xl font-bold text-yellow-500 mb-2">{counts.Medium}</span>
                  <span className="text-sm font-medium text-on-surface-variant uppercase tracking-wide">Medium</span>
                </div>
                <div className="bg-surface p-6 rounded-xl border border-outline-variant shadow-sm flex flex-col items-center justify-center">
                  <span className="text-4xl font-bold text-primary mb-2">{counts.Low}</span>
                  <span className="text-sm font-medium text-on-surface-variant uppercase tracking-wide">Low</span>
                </div>
              </div>
              
              <div className="space-y-2">
                <h2 className="text-xl font-bold text-on-surface mb-6">Identified Issues</h2>
                {findings.length === 0 ? (
                  <div className="bg-surface p-12 rounded-xl border border-outline-variant text-center flex flex-col items-center justify-center">
                    <CheckCircle className="text-primary mb-4" size={48} />
                    <h3 className="text-xl font-medium text-on-surface mb-2">No Issues Found</h3>
                    <p className="text-on-surface-variant">The audit did not detect any security flaws, code smells, or architectural anti-patterns in the flagged files.</p>
                  </div>
                ) : (
                  findings.map((item, idx) => (
                    <FindingCard key={`${item.filePath}-${idx}`} finding={item.finding} filePath={item.filePath} />
                  ))
                )}
              </div>
            </div>
          </ErrorBoundary>
        </main>
      </div>
    </>
  );
}
