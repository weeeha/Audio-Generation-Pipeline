# Runs Krita's ComfyUI with its venv packages, without going through the venv's
# uv trampoline (which can't resolve the cpython-3.12 junction from an SSH session).
# Launch with the real interpreter:
#   %APPDATA%\uv\python\cpython-3.12.9-windows-x86_64-none\python.exe -s run_comfy.py <comfy args>
import os
import runpy
import site
import sys

KRITA_ROOT = r"G:\Krita AI\ComfyUI"
COMFY_DIR = os.path.join(KRITA_ROOT, "ComfyUI")

site.addsitedir(os.path.join(KRITA_ROOT, "venv", "Lib", "site-packages"))
sys.path.insert(0, COMFY_DIR)
os.chdir(COMFY_DIR)

main = os.path.join(COMFY_DIR, "main.py")
sys.argv = [main] + sys.argv[1:]
runpy.run_path(main, run_name="__main__")
