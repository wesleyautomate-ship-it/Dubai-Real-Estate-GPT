from pathlib import Path
lines=Path('backend/core/tools.py').read_text(encoding='utf-8', errors='ignore').splitlines()
for i in range(320, 380):
    print(f"{i+1:04d}: {lines[i]}")
