from pathlib import Path
lines = Path('backend/core/analytics_engine.py').read_text(encoding='utf-8', errors='ignore').splitlines()
with open('tmp_analytics_requests.txt','w', encoding='utf-8') as out:
    for i,line in enumerate(lines,1):
        if 'requests' in line:
            out.write(f'{i}: {line.strip()}\n')
