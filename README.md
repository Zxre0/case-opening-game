# case-opening-game

**Caseforge**, a CS2-style case opening simulator in a single HTML file, plus Blender scripts for 3D knife renders.

## Play

Open `index.html` in a browser. No build step and no server needed. To host it, turn on GitHub Pages for the `main` branch.

- 8 cases using CS2 case and skin names, with the standard rarity odds (Mil-Spec 79.92%, Restricted 15.98%, Classified 3.2%, Covert 0.64%, Rare Special 0.26%)
- Spinning reel, open 1, 3 or 5 cases at a time, quick-open toggle
- Float values and wear grades, 10% StatTrak chance (not on gloves)
- Inventory with sorting and selling, stats, a payday button, and sound
- Progress is saved in the browser's localStorage

The weapon artwork is drawn in code as a stand-in and prices are simulated. Fan project, not affiliated with Valve. No real money involved.

## Blender

`setup.sh` installs headless Blender 5.0 (the `bpy` module from PyPI) into `/opt/blender-env`.

```bash
./setup.sh
/opt/blender-env/bin/python blender/knife.py 128 "$PWD/renders/knife_render.png"   # samples, output path
/opt/blender-env/bin/python blender/test_render.py
```

`knife.py` models an original curved folding knife with a green and blue swirled metallic finish, renders it with Cycles on the CPU, and saves a `.blend` next to the image. The output is in `renders/`.

## Blender MCP server

`mcp/blender_mcp_server.py` is a stdio MCP server that runs Blender in-process, with no Blender window needed. Its tools are `run_python`, `render` (returns the image), `scene_info`, `reset_scene`, `save_blend`, `open_blend` and `import_model`.

`.mcp.json` registers it for Claude Code when this repo is opened, once `setup.sh` has been run.

## Knife models

`blender/knives.py` builds 19 original knife models, one for each knife type in the game: Karambit, M9 Bayonet, Bayonet, Flip, Gut, Butterfly, Talon, Ursus, Stiletto, Navaja, Skeleton, Nomad, Survival, Paracord, Falchion, Bowie, Huntsman, Shadow Daggers and Kukri. Each is modeled from the real-world knife type, not copied from game assets. They are rendered in plain steel with stock handle materials.

```bash
/opt/blender-env/bin/python blender/knives.py                    # all knives -> renders/knives/<name>.png + .blend
/opt/blender-env/bin/python blender/knives.py karambit kukri     # only some
/opt/blender-env/bin/python blender/contact_sheet.py             # renders/knives_sheet.png
```
