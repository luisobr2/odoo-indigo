env = env  # noqa
import inspect
sig = inspect.signature(env["ir.asset"]._get_asset_paths)
print("Signature:", sig)
# Try with positional
try:
    files = env["ir.asset"]._get_asset_paths("web.assets_frontend", {})
    print("OK got", len(files), "files")
    indigo = [str(f) for f in files if "indigo_theme" in str(f)]
    print("indigo files:", indigo)
except Exception as e:
    print("err1:", e)
