#!/usr/bin/env python3
"""
Script to consolidate all Python source code from the Nodal project into a single text file.
Combines all .py files into one condensed file for easy viewing/sharing.
"""

import os
from pathlib import Path
from datetime import datetime

def build_tree_structure(root_path, prefix="", exclude_dirs=None, extensions_to_include=None, exclude_files=None):
    """
    Build a formatted tree structure of the project.
    
    Args:
        root_path: Path to the root directory
        prefix: Prefix for tree formatting
        exclude_dirs: Set of directories to exclude
        extensions_to_include: Set of file extensions to include
        exclude_files: Set of files to exclude
        
    Returns:
        Formatted tree string
    """
    if exclude_dirs is None:
        exclude_dirs = set()
    if extensions_to_include is None:
        extensions_to_include = {".py", ".json", ".txt", ".md"}
    if exclude_files is None:
        exclude_files = set()
    
    tree_lines = []
    
    def walk_tree(path, prefix="", is_last=True):
        try:
            entries = sorted(os.listdir(path))
        except PermissionError:
            return
        
        # Filter entries
        filtered_entries = []
        for entry in entries:
            if entry.startswith("."):
                continue
            if entry in exclude_dirs:
                continue
            if entry in exclude_files:
                continue
            
            entry_path = os.path.join(path, entry)
            if os.path.isdir(entry_path):
                filtered_entries.append((entry, True))
            else:
                # Check file extension
                file_ext = os.path.splitext(entry)[1]
                if file_ext in extensions_to_include or entry in {"LICENSE", "Makefile"}:
                    filtered_entries.append((entry, False))
        
        for i, (entry, is_dir) in enumerate(filtered_entries):
            is_last_entry = i == len(filtered_entries) - 1
            current_prefix = "└── " if is_last_entry else "├── "
            tree_lines.append(f"{prefix}{current_prefix}{entry}")
            
            if is_dir:
                next_prefix = prefix + ("    " if is_last_entry else "│   ")
                entry_path = os.path.join(path, entry)
                walk_tree(entry_path, next_prefix, is_last_entry)
    
    tree_lines.append(os.path.basename(root_path) + "/")
    walk_tree(root_path, "")
    
    return "\n".join(tree_lines)


def consolidate_code(output_filename="consolidated_code.txt"):
    """
    Condense all Python files from the project into a single text file.
    
    Args:
        output_filename (str): Name of the output file to create
    """
    
    # Get the project root directory (parent of the script location)
    project_root = Path(__file__).parent
    
    # Directories to exclude
    exclude_dirs = {
        "__pycache__",
        ".git",
        ".pytest_cache",
        ".venv",
        "venv",
        "env",
        "__pycache__",
        ".idea",
        ".vscode",
        "node_modules",
    }
    
    # Files to exclude
    exclude_files = {
        "consolidate_code.py",  # Exclude this script itself
        output_filename,  # Exclude the output file
    }
    
    # File extensions to include
    extensions_to_include = {".py", ".json", ".txt", ".md"}
    
    # Collect all files
    files_to_process = []
    
    for root, dirs, files in os.walk(project_root):
        # Remove excluded directories from dirs in-place to prevent traversal
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        # Skip the output file itself if it exists
        files = [f for f in files if not f.startswith(".") and f not in exclude_files]
        
        for file in files:
            file_path = Path(root) / file
            # Check if file has an extension we want to include
            if file_path.suffix in extensions_to_include or file_path.name in {"LICENSE", "Makefile"}:
                files_to_process.append(file_path)
    
    # Sort files for consistent output
    files_to_process.sort()
    
    # Write consolidated file
    output_path = project_root / output_filename
    
    with open(output_path, "w", encoding="utf-8") as outfile:
        outfile.write("=" * 80 + "\n")
        outfile.write(f"NODAL PROJECT - CONSOLIDATED CODE\n")
        outfile.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        outfile.write("=" * 80 + "\n\n")
        
        # Write project structure
        outfile.write("PROJECT STRUCTURE\n")
        outfile.write("-" * 80 + "\n\n")
        tree_structure = build_tree_structure(project_root, exclude_dirs=exclude_dirs, extensions_to_include=extensions_to_include, exclude_files=exclude_files)
        outfile.write(tree_structure)
        outfile.write("\n\n")
        
        outfile.write("=" * 80 + "\n")
        outfile.write("SOURCE CODE\n")
        outfile.write("=" * 80 + "\n")
        
        file_count = 0
        total_lines = 0
        
        for file_path in files_to_process:
            # Skip the output file itself and the consolidate script
            if file_path.name == output_filename or file_path.name == "consolidate_code.py":
                continue
            
            try:
                # Calculate relative path for display
                rel_path = file_path.relative_to(project_root)
                
                # Read file content
                with open(file_path, "r", encoding="utf-8", errors="ignore") as infile:
                    content = infile.read()
                    lines = content.count('\n') + (1 if content and not content.endswith('\n') else 0)
                    total_lines += lines
                
                # Write header for this file
                outfile.write("\n" + "-" * 80 + "\n")
                outfile.write(f"FILE: {rel_path}\n")
                outfile.write(f"LINES: {lines}\n")
                outfile.write("-" * 80 + "\n\n")
                
                # Write file content
                outfile.write(content)
                
                # Add spacing between files
                if not content.endswith('\n'):
                    outfile.write('\n')
                
                file_count += 1
                
            except Exception as e:
                outfile.write(f"[ERROR reading file: {e}]\n\n")
        
        # Write summary at the end
        outfile.write("\n" + "=" * 80 + "\n")
        outfile.write("SUMMARY\n")
        outfile.write("=" * 80 + "\n")
        outfile.write(f"Total files consolidated: {file_count}\n")
        outfile.write(f"Total lines of code: {total_lines}\n")
        outfile.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    print(f"✓ Code consolidated successfully!")
    print(f"  Output file: {output_path}")
    print(f"  Files processed: {file_count}")
    print(f"  Total lines: {total_lines}")
    print(f"\n  File size: {output_path.stat().st_size / (1024 * 1024):.2f} MB")

if __name__ == "__main__":
    consolidate_code()
