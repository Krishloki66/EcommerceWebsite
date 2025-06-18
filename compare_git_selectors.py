import subprocess
import re

def run_cmd(cmd):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        return result.stdout.strip() if result.stdout else ""
    except Exception as e:
        print(f"⚠️ Command failed: {cmd}\n{e}")
        return ""

def get_git_diff():
    print("🔄 Fetching all remote branches...")
    run_cmd(["git", "fetch", "--all"])

    print("🔍 Checking diff between origin/master and origin/main...")
    diff = run_cmd(["git", "diff", "origin/master..origin/main"])
    return diff

def extract_selectors(diff_text):
    added = set()
    removed = set()

    for line in diff_text.splitlines():
        line = line.strip()
        if line.startswith('+') and not line.startswith('+++'):
            added.update(re.findall(r'class="([^"]+)"', line))  # HTML class
            added.update(re.findall(r'id="([^"]+)"', line))     # HTML ID
            added.update(re.findall(r'\.([a-zA-Z0-9_-]+)\s*\{', line))  # CSS class
            added.update(re.findall(r'#([a-zA-Z0-9_-]+)\s*\{', line))   # CSS ID
        elif line.startswith('-') and not line.startswith('---'):
            removed.update(re.findall(r'class="([^"]+)"', line))
            removed.update(re.findall(r'id="([^"]+)"', line))
            removed.update(re.findall(r'\.([a-zA-Z0-9_-]+)\s*\{', line))
            removed.update(re.findall(r'#([a-zA-Z0-9_-]+)\s*\{', line))

    # Split multi-class declarations
    added = set(cls for entry in added for cls in entry.split())
    removed = set(cls for entry in removed for cls in entry.split())
    return added, removed

def main():
    diff = get_git_diff()

    if not diff.strip():
        print("❌ No diff found or Git error.")
        return

    added, removed = extract_selectors(diff)

    if not added and not removed:
        print("✅ No selector changes found between main and master.")
    else:
        print("🧠 Detected selector changes:")
        if added:
            print("➕ Added selectors:")
            for sel in sorted(added):
                print(f"   .{sel}")
        if removed:
            print("➖ Removed selectors:")
            for sel in sorted(removed):
                print(f"   .{sel}")

if __name__ == "__main__":
    main()
