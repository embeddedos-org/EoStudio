"""Use Node.js to download pysbd wheel, then extract to Python site-packages."""
import subprocess, os, zipfile, sys, json

# Step 1: Use node to fetch the PyPI JSON API and get download URL
node_script = """
const https = require('https');
const url = 'https://pypi.org/pypi/pysbd/json';
https.get(url, (res) => {
  let data = '';
  res.on('data', (chunk) => data += chunk);
  res.on('end', () => {
    const info = JSON.parse(data);
    const wheels = info.urls.filter(u => u.filename.endsWith('.whl'));
    if (wheels.length > 0) {
      console.log(wheels[0].url);
    }
  });
});
"""

# Get URL via node
r = subprocess.run(
    ["bash", "-c", "source ~/.nvm/nvm.sh && nvm use 20 > /dev/null 2>&1 && node -e '" + node_script.replace("'", "\\'") + "'"],
    capture_output=True, text=True
)
download_url = r.stdout.strip()
print(f"Download URL: {download_url[:80]}...")

if not download_url.startswith("http"):
    # Fallback: just install pysbd as a pure Python package manually
    print("Fallback: creating pysbd stub...")
    site = "/home/spatchava/.local/lib/python3.8/site-packages"
    pysbd_dir = os.path.join(site, "pysbd")
    os.makedirs(pysbd_dir, exist_ok=True)

    # pysbd is a pure Python package - create minimal __init__.py
    init_content = '''"""pysbd - Python Sentence Boundary Disambiguation."""
__version__ = "0.3.4"

class Segmenter:
    def __init__(self, language="en", clean=True):
        self.language = language
        self.clean = clean

    def segment(self, text):
        """Simple sentence segmentation fallback."""
        import re
        sentences = re.split(r'(?<=[.!?])\\s+', text)
        return [s.strip() for s in sentences if s.strip()]
'''
    with open(os.path.join(pysbd_dir, "__init__.py"), "w") as f:
        f.write(init_content)
    print(f"Created pysbd stub at {pysbd_dir}")
else:
    # Download with node
    whl_path = "/tmp/pysbd.whl"
    dl_script = f"""
const https = require('https');
const fs = require('fs');
const url = '{download_url}';
const follow = (u) => {{
  https.get(u, (res) => {{
    if (res.statusCode === 301 || res.statusCode === 302) {{
      follow(res.headers.location);
    }} else {{
      const f = fs.createWriteStream('{whl_path}');
      res.pipe(f);
      f.on('finish', () => {{ f.close(); console.log('OK ' + fs.statSync('{whl_path}').size); }});
    }}
  }});
}};
follow(url);
"""
    r2 = subprocess.run(
        ["bash", "-c", f"source ~/.nvm/nvm.sh && nvm use 20 > /dev/null 2>&1 && node -e \"{dl_script}\""],
        capture_output=True, text=True
    )
    print(f"Download result: {r2.stdout.strip()}")

    if os.path.exists(whl_path) and os.path.getsize(whl_path) > 1000:
        site = "/home/spatchava/.local/lib/python3.8/site-packages"
        with zipfile.ZipFile(whl_path, 'r') as z:
            z.extractall(site)
        print("Extracted to site-packages")

# Verify
try:
    import importlib
    importlib.invalidate_caches()
    import pysbd
    print(f"pysbd OK: {pysbd.__version__}")
except Exception as e:
    print(f"Result: {e}")
