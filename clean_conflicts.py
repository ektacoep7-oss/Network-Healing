#!/usr/bin/env python3
"""Remove all git merge conflict markers from files, keeping HEAD version."""
import re
import os
import sys

def clean_file(filepath):
    """Clean merge conflict markers from a file."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        if '<<<<<<< HEAD' not in content:
            return False
        
        # Keep HEAD version (first part between <<<< and =====)
        pattern = r'<<<<<<< HEAD\n(.*?)\n=======\n.*?\n>>>>>>> ekta-simulation\n'
        cleaned = re.sub(pattern, r'\1\n', content, flags=re.DOTALL)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(cleaned)
        
        return True
    except Exception as e:
        print(f"ERROR in {filepath}: {e}")
        return False

# Find and clean all files
found_count = 0
for root, dirs, files in os.walk('.'):
    dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', '.git']]
    
    for file in files:
        if not file.endswith(('.py', '.csv')):
            continue
        
        filepath = os.path.join(root, file)
        if clean_file(filepath):
            print(f"✅ Cleaned: {filepath}")
            found_count += 1

print(f"\n✅ Cleaned {found_count} files")
