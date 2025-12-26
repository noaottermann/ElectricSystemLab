import os
import sys
from pathlib import Path

def display_tree(directory, prefix="", is_last=True, max_depth=None, current_depth=0):
    """Display directory tree structure"""
    if max_depth is not None and current_depth > max_depth:
        return
    
    path = Path(directory)
    if not path.exists():
        print(f"Directory '{directory}' not found")
        return
    
    # Print current directory
    connector = "└── " if is_last else "├── "
    print(f"{prefix}{connector}{path.name}/")
    
    # Get all items in directory
    try:
        items = sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
        files = [item for item in items if item.is_file() and not item.name.startswith('.')]
        dirs = [item for item in items if item.is_dir() and not item.name.startswith('.')]
        
        all_items = dirs + files
        
        # Print items
        for i, item in enumerate(all_items):
            is_last_item = i == len(all_items) - 1
            new_prefix = prefix + ("    " if is_last else "│   ")
            
            if item.is_dir():
                display_tree(item, new_prefix, is_last_item, max_depth, current_depth + 1)
            else:
                connector = "└── " if is_last_item else "├── "
                print(f"{new_prefix}{connector}{item.name}")
                
    except PermissionError:
        print(f"{prefix}    [Permission Denied]")

def main():
    project_root = Path.cwd()
    print("ElectricSystemLab Project Structure:")
    print("=" * 40)
    display_tree(project_root, max_depth=3)

if __name__ == "__main__":
    main()