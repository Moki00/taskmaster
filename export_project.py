import os

# Root directory (run from the taskmaster root)
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(ROOT_DIR, "project_snapshot.txt")

# Folders and extensions to ignore
IGNORE_DIRS = {
    ".git", 
    "node_modules", 
    "__pycache__", 
    ".venv", 
    "venv", 
    "dist", 
    "build", 
    ".pytest_cache"
}
IGNORE_EXTENSIONS = {
    ".png", 
    ".jpg", 
    ".jpeg", 
    ".ico", 
    ".svg", 
    ".pyc", 
    ".lock"
}

def generate_tree(dir_path, prefix=""):
    """Generates an ASCII folder tree."""
    tree_str = ""
    try:
        entries = sorted(os.listdir(dir_path))
    except PermissionError:
        return ""
    
    entries = [e for e in entries if e not in IGNORE_DIRS and e != "project_snapshot.txt" and e != "export_project.py"]
    total = len(entries)
    
    for idx, entry in enumerate(entries):
        path = os.path.join(dir_path, entry)
        is_last = idx == (total - 1)
        connector = "└── " if is_last else "├── "
        
        tree_str += f"{prefix}{connector}{entry}\n"
        
        if os.path.isdir(path):
            extension = "    " if is_last else "│   "
            tree_str += generate_tree(path, prefix + extension)
            
    return tree_str

def extract_files(dir_path):
    """Gathers the text content of every source file."""
    content_str = ""
    for root, dirs, files in os.walk(dir_path):
        # Skip ignored directories
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        
        for file in sorted(files):
            if file in ["project_snapshot.txt", "export_project.py", "package-lock.json"]:
                continue
            
            _, ext = os.path.splitext(file)
            if ext in IGNORE_EXTENSIONS:
                continue
                
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, ROOT_DIR)
            
            content_str += f"\n{'='*70}\n"
            content_str += f"FILE: {rel_path}\n"
            content_str += f"{'='*70}\n"
            
            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    content_str += f.read() + "\n"
            except Exception as e:
                content_str += f"[Error reading file: {e}]\n"
                
    return content_str

def main():
    tree = f"TASKMASTER PROJECT DIRECTORY TREE\n{'='*70}\ntaskmaster/\n"
    tree += generate_tree(ROOT_DIR)
    
    file_contents = extract_files(ROOT_DIR)
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        out.write(tree)
        out.write("\n\nFILE CONTENTS\n")
        out.write(file_contents)
        
    print(f"[+] Snapshot created: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()