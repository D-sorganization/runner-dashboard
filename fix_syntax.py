import re

with open("backend/server.py", "r", encoding="utf-8") as f:
    code = f.read()

def fix_signature(match):
    full = match.group(0)
    inner = match.group(2)
    name = match.group(1)
    
    if "principal: Principal = Depends" not in inner:
        return full
        
    if "*, principal: Principal" in inner:
        return full
    
    # We can just split the parameters, and append * before principal.
    # To avoid parsing issues, we can just do string replacement:
    new_inner = inner.replace(", principal: Principal", ", *, principal: Principal")
    # If it was the first argument (unlikely since `request` is usually first)
    if new_inner.startswith("principal: Principal"):
        new_inner = "*, " + new_inner
        
    return f"async def {name}({new_inner}):"

code = re.sub(r'async def (\w+)\((.*?)\):', fix_signature, code, flags=re.DOTALL)

with open("backend/server.py", "w", encoding="utf-8") as f:
    f.write(code)
