"""Bypass broken pip — manually install pysbd from wheel."""
import subprocess, os, zipfile, sys

# Download pysbd wheel using curl
url = "https://files.pythonhosted.org/packages/01/97/1052b9a73917d2b561c0b59eab62a4fa7e27e7ef8dabe5cb6a05ad0a688b/pysbd-0.3.4-py3-none-any.whl"
whl_path = "/tmp/pysbd-0.3.4.whl"

# Use curl to download
r = subprocess.run(["curl", "-sL", "-o", whl_path, url], capture_output=True)
size = os.path.getsize(whl_path) if os.path.exists(whl_path) else 0
print(f"Downloaded: {size} bytes")

if size < 1000:
    print("Download failed or got HTML error page. Trying alternative...")
    # Try extracting from cached pip packages
    r2 = subprocess.run(["find", "/home/spatchava/.cache/pip", "-name", "pysbd*", "-type", "f"],
                        capture_output=True, text=True)
    print(f"Cached: {r2.stdout}")

# Install manually by extracting wheel to site-packages
site_packages = [p for p in sys.path if "site-packages" in p and ".local" in p]
if site_packages:
    target = site_packages[0]
    print(f"Target: {target}")
    if os.path.exists(whl_path) and os.path.getsize(whl_path) > 1000:
        with zipfile.ZipFile(whl_path, 'r') as z:
            z.extractall(target)
        print("Extracted pysbd to site-packages")
    else:
        print("Need to download properly")
else:
    print("No site-packages found")

# Test
try:
    import pysbd
    print(f"pysbd imported OK: {pysbd.__version__}")
except ImportError as e:
    print(f"Still missing: {e}")
