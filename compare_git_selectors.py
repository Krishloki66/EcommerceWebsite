import subprocess
import re

def get_git_diff():
    # Get the diff between main and master
    result = subprocess.run(
        ["git", "diff", "origin/master..origin/main"],
        capture_output=True,
        text=True
    )
    return result.stdout

def extract_selectors(diff_text):
    added = set()
    removed = set()
    
    for line in diff_text.splitlines():
        line = line.strip()
        
        # Skip unchanged lines
        if not line or line.startswith("+++ ") or line.startswith("--- "):
            continue
        
        # Detect added lines
        if line.startswith('+') and not line.startswith('+++'):
            added.update(re.findall(r'class="([^"]+)"', line))
            added.update(re.findall(r'id="([^"]+)"', line))

        # Detect removed lines
        if line.startswith('-') and not line.startswith('---'):
            removed.update(re.findall(r'class="([^"]+)"', line))
            removed.update(re.findall(r'id="([^"]+)"', line))

    return added, removed

def main():
    diff = get_git_diff()
    
    if not diff:
        print("❌ No diff found or git error.")
        return

    added, removed = extract_selectors(diff)

    if not added and not removed:
        print("✅ No selector changes found between main and master.")
    else:
        print("🧠 Detected selector changes:")
        if added:
            print("➕ Added:", added)
        if removed:
            print("➖ Removed:", removed)

if __name__ == "__main__":
    main()
