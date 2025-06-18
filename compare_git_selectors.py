import subprocess
import re

def get_git_diff():
    subprocess.run(["git", "fetch", "origin", "main"], check=True)
    subprocess.run(["git", "fetch", "origin", "master"], check=True)
    result = subprocess.run(["git", "diff", "origin/main..origin/master"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return result.stdout.decode("utf-8", errors="ignore")

def extract_selectors(diff_text):
    if not diff_text:
        return set(), set()

    added = set()
    removed = set()

    for line in diff_text.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            added.update(re.findall(r'class="([^"]+)"', line))
            added.update(re.findall(r'id="([^"]+)"', line))
        elif line.startswith("-") and not line.startswith("---"):
            removed.update(re.findall(r'class="([^"]+)"', line))
            removed.update(re.findall(r'id="([^"]+)"', line))

    added = set(cls for entry in added for cls in entry.split())
    removed = set(cls for entry in removed for cls in entry.split())
    return added, removed

# MAIN EXECUTION
diff = get_git_diff()
added, removed = extract_selectors(diff)

if added or removed:
    print("🧠 Detected selector changes:")
    if added:
        print("➕ Added:", ", ".join(f".{a}" for a in added))
    if removed:
        print("➖ Removed:", ", ".join(f".{r}" for r in removed))
else:
    print("✅ No selector changes found between main and master.")
