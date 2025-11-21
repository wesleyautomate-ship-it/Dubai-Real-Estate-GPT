from pathlib import Path
import os
for root, dirs, files in os.walk('.'):
    for name in files:
        if name.endswith('.py'):
            path = Path(root) / name
            text = path.read_text(encoding='utf-8', errors='ignore')
            if 'fetch_transactions' in text:
                print(path)
