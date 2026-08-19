import re
import ast
from typing import Dict, Any, List

# Pre-compile regex patterns for performance
SECRET_PATTERNS = [
    # Basic matching for API keys, tokens, passwords
    re.compile(r'(?i)(api[_-]?key|secret|token|password|passwd|pwd)\s*[:=]\s*[\'""][A-Za-z0-9\-_]{8,}[\'""]'),
    re.compile(r'(?i)bearer\s+[A-Za-z0-9\-\._~+/]+=*')
]

HIGH_RISK_KEYWORDS = [
    # TODOs referencing security
    re.compile(r'(?i)\b(TODO|FIXME|HACK|XXX)\b.*?(security|vuln|bypass|auth|leak)'),
    # Bypassing patterns
    re.compile(r'(?i)(disable[_-]?auth|bypass[_-]?auth|no[_-]?verify)')
]

DANGEROUS_PY_FUNCS = {'eval', 'exec', 'system', 'popen', 'subprocess.call', 'subprocess.Popen'}

def scan_python_ast(content: str) -> List[str]:
    """Scan Python code using AST to find dangerous function calls."""
    flags = []
    try:
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name = None
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    # Simplistic approach to get 'subprocess.call'
                    if isinstance(node.func.value, ast.Name):
                        func_name = f"{node.func.value.id}.{node.func.attr}"
                    else:
                        func_name = node.func.attr
                
                if func_name in DANGEROUS_PY_FUNCS:
                    flags.append(f"Dangerous function call: {func_name}")
    except Exception:
        # Ignore parse errors for static analysis triage
        pass
    return flags

def scan_js_ts(content: str) -> List[str]:
    """Basic Regex scan for JS/TS to find dangerous function calls."""
    flags = []
    # simple eval check
    if re.search(r'\beval\s*\(', content):
        flags.append("Dangerous function call: eval")
    # simple child_process exec check
    if re.search(r'\bexec\s*\(', content) and 'child_process' in content:
        flags.append("Dangerous function call: exec")
    return flags

def scan_file_content(filepath: str, content: str) -> Dict[str, Any]:
    """
    Main entry point for Phase 1 Audit Triage.
    Runs static analysis to flag suspicious files for later Gemini analysis.
    """
    flags = {
        "has_secrets": False,
        "has_dangerous_functions": False,
        "has_high_risk_keywords": False,
        "is_suspicious": False,
        "details": []
    }
    
    # 1. Regex Scanners for Secrets
    for pattern in SECRET_PATTERNS:
        if pattern.search(content):
            flags["has_secrets"] = True
            flags["details"].append("Potential secret or credential found")
            flags["is_suspicious"] = True
            break
            
    # 2. Regex Scanners for High-Risk Keywords
    for pattern in HIGH_RISK_KEYWORDS:
        if pattern.search(content):
            flags["has_high_risk_keywords"] = True
            flags["details"].append("High-risk keyword found (e.g., TODO security, auth bypass)")
            flags["is_suspicious"] = True
            break
            
    # 3. AST or Regex Scanners for Dangerous Functions
    if filepath.endswith('.py'):
        ast_flags = scan_python_ast(content)
        if ast_flags:
            flags["has_dangerous_functions"] = True
            flags["details"].extend(ast_flags)
            flags["is_suspicious"] = True
            
    elif filepath.endswith(('.js', '.ts', '.jsx', '.tsx')):
        js_flags = scan_js_ts(content)
        if js_flags:
            flags["has_dangerous_functions"] = True
            flags["details"].extend(js_flags)
            flags["is_suspicious"] = True
            
    # Remove duplicates from details
    flags["details"] = list(set(flags["details"]))
    
    return flags
