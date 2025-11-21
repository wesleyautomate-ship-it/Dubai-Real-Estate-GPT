from pathlib import Path
lines=Path('backend/core/analytics_engine.py').read_text(encoding='utf-8', errors='ignore').splitlines()
with open('tmp_analytics_head.txt','w',encoding='utf-8') as f:
    f.write('\n'.join(f'{i+1:04d}: {line}' for i,line in enumerate(lines[:200], start=1)))
