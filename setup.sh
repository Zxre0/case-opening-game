#!/usr/bin/env bash
# Installs headless Blender (the bpy module from PyPI) plus the MCP SDK into /opt/blender-env.
# Use it as the cloud environment's setup script, or run it once on a Linux machine.
set -euo pipefail
uv venv --python 3.11 /opt/blender-env
VIRTUAL_ENV=/opt/blender-env uv pip install bpy "mcp>=1.2,<2"
/opt/blender-env/bin/python -c "import bpy; print('Blender', bpy.app.version_string)"
