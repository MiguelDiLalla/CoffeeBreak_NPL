import os
from datetime import datetime
import time
import sys
import fnmatch

def get_time_diff(timestamp):
    now = time.time()
    diff = now - timestamp
    
    # Convert to different time units
    minutes = int(diff / 60)
    hours = int(minutes / 60)
    days = int(hours / 24)
    
    if days > 0:
        return f"{days} days ago"
    elif hours > 0:
        return f"{hours} hours ago"
    elif minutes > 0:
        return f"{minutes} minutes ago"
    else:
        return "just now"

def get_gitignore_patterns(root_dir):
    patterns = set(['.git/**'])  # Always ignore .git folder
    gitignore_path = os.path.join(root_dir, '.gitignore')
    
    if os.path.exists(gitignore_path):
        with open(gitignore_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    patterns.add(line)
    return patterns

def should_ignore(path, root, patterns):
    if '.git' in path.split(os.sep):
        return True
        
    if patterns:
        rel_path = os.path.relpath(path, root)
        return any(fnmatch.fnmatch(rel_path, pattern) for pattern in patterns)
    return False

def create_folder_tree(use_gitignore=True):
    try:
        # Get the directory where the script is located
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if not current_dir:  # fallback if __file__ doesn't work
            current_dir = os.getcwd()
            
        print(f"Scanning directory: {current_dir}")
        output_file = os.path.join(current_dir, 'folder_tree.txt')
        
        # Get ignore patterns if needed
        ignore_patterns = get_gitignore_patterns(current_dir) if use_gitignore else {'.git/**'}
        print(f"Using {'gitignore patterns' if use_gitignore else 'only .git ignore'}")
        
        file_count = 0
        dir_count = 0
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"Folder tree generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Root: {current_dir}\n")
            f.write(f"Ignoring: {', '.join(ignore_patterns)}\n\n")
            
            for root, dirs, files in os.walk(current_dir):
                # Filter out ignored directories
                dirs[:] = [d for d in dirs if not should_ignore(os.path.join(root, d), current_dir, ignore_patterns)]
                
                # Calculate level for indentation
                level = root[len(current_dir):].count(os.sep)
                indent = '│   ' * level
                
                # Write directory name
                dir_name = os.path.basename(root)
                if level > 0:
                    try:
                        last_mod = os.path.getmtime(root)
                        f.write(f"{indent}├── 📁 {dir_name} ({get_time_diff(last_mod)})\n")
                        dir_count += 1
                    except Exception as e:
                        print(f"Error processing directory {dir_name}: {e}")
                
                # Filter and write files
                filtered_files = [f for f in sorted(files) 
                                if not should_ignore(os.path.join(root, f), current_dir, ignore_patterns)]
                
                # Only proceed if there are files to process
                if filtered_files:
                    subindent = '│   ' * (level + 1)
                    for i, file in enumerate(filtered_files):
                        try:
                            file_path = os.path.join(root, file)
                            last_mod = os.path.getmtime(file_path)
                            
                            # Check if this is the last file in the filtered list
                            if i == len(filtered_files) - 1:
                                # Last file uses └── symbol with correct indentation
                                f.write(f"{subindent}└── 📄 {file} ({get_time_diff(last_mod)})\n")
                            else:
                                # Other files use ├── symbol
                                f.write(f"{subindent}├── 📄 {file} ({get_time_diff(last_mod)})\n")
                            file_count += 1
                        except Exception as e:
                            print(f"Error processing file {file}: {e}")
        
        print(f"\nScan complete!")
        print(f"Found {dir_count} directories and {file_count} files")
        print(f"Results saved to: {output_file}")
        
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("Starting folder tree generation...")
    create_folder_tree(use_gitignore=True)  # Set to False to ignore only .git folder
