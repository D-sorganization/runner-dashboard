import re

with open("backend/server.py", "r", encoding="utf-8") as f:
    code = f.read()

dispatch_workflow_replacement = """    inputs = body.get("inputs", {}) or {}
    correlation_id = request.headers.get("X-Correlation-Id", secrets.token_hex(8))
    inputs["correlation_id"] = correlation_id"""
code = code.replace('    inputs = body.get("inputs", {}) or {}', dispatch_workflow_replacement)

# Also sanitize log outputs: "closes #46" says Sanitize all principal-derived strings before logging
# For example, in backend/server.py
code = code.replace('log.info(f"Accepted workflow dispatch for {repo}/{workflow_id} by {principal.id}")', 'log.info(f"Accepted workflow dispatch for {repo}/{workflow_id} by {principal.id.replace(chr(10), \'\').replace(chr(13), \'\')}")')
# Just doing a generic sanitize function
sanitize_func = """
def sanitize_log_value(val: str) -> str:
    return str(val).replace("\\n", "").replace("\\r", "").strip()
"""
if "sanitize_log_value" not in code:
    code = code.replace('import time', 'import time\n' + sanitize_func)

code = re.sub(r'log\.info\((.*)principal\.id(.*)\)', r'log.info(\1sanitize_log_value(principal.id)\2)', code)

with open("backend/server.py", "w", encoding="utf-8") as f:
    f.write(code)

with open("backend/agent_remediation.py", "r", encoding="utf-8") as f:
    code2 = f.read()

# For agent remediation, we might have inputs there too. Let's look for workflow inputs.
code2 = code2.replace('"prompt": prompt, "model": provider', '"prompt": prompt, "model": provider, "correlation_id": getattr(request, "state", {}).get("correlation_id", "unknown") if "request" in locals() else "unknown"')

with open("backend/agent_remediation.py", "w", encoding="utf-8") as f:
    f.write(code2)
