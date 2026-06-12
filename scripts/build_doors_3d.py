"""
Build 3 realistic decorative door models in Blender (via BlenderMCP on
localhost:9876) and export them as GLB into the Next.js panel's public
folder so the /customizer page can load them.

v2 — realism pass modeled after the client's reference renders:
  - curved arc patterns (clipped ellipse rings) instead of straight bars only
  - outer door jamb, stainless pull handles + deadbolts, hinges
  - beveled edges on every frame piece (catches highlights)

Models (meters, real door sizes):
  door-eclipse.glb — Double Door, two intersecting tall ovals per leaf
  door-orbit.glb   — Double Door, center circle + corner arcs
  door-roma.glb    — Single Door, classic rings on a center bar

Material slots (the viewer recolors by material name):
  PatternMetal — decorative metal + frame + jamb (recolored live)
  Glass        — frosted glass, fixed
  Hardware     — stainless handles/hinges, fixed

Usage:
  python scripts/build_doors_3d.py
"""
from pathlib import Path

from blender_client import BlenderClient

OUT_DIR = Path(r'C:/Trabajo/indigo-next/public/3d')

# Shared helpers, prepended to every per-design script so each execute_code
# call is self-contained (BlenderMCP does not guarantee a shared namespace
# between calls).
COMMON = r'''
import bpy, math

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.lights,
                 bpy.data.cameras, bpy.data.curves):
        for item in list(coll):
            coll.remove(item)

def make_mat(name, rgb, metallic=0.9, roughness=0.35, alpha=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    # Look up by type, not name — node names are localized in non-English UIs.
    bsdf = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs['Base Color'].default_value = (*rgb, 1.0)
    bsdf.inputs['Metallic'].default_value = metallic
    bsdf.inputs['Roughness'].default_value = roughness
    if alpha < 1.0:
        bsdf.inputs['Alpha'].default_value = alpha
        try:
            m.blend_method = 'BLEND'
        except Exception:
            pass
        try:
            m.surface_render_method = 'BLENDED'
        except Exception:
            pass
    return m

def box(name, sx, sy, sz, x, y, z, material, rot_y=0.0, bevel=0.003):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, z))
    o = bpy.context.active_object
    o.name = name
    o.scale = (sx, sy, sz)
    if rot_y:
        o.rotation_euler = (0, math.radians(rot_y), 0)
    bpy.ops.object.transform_apply(scale=True, rotation=True)
    if bevel:
        m = o.modifiers.new('bv', 'BEVEL')
        m.width = bevel
        m.segments = 2
        m.limit_method = 'ANGLE'
        bpy.ops.object.modifier_apply(modifier=m.name)
    o.data.materials.append(material)
    return o

def cyl(name, r, depth, x, y, z, material, rot_x=0.0):
    bpy.ops.mesh.primitive_cylinder_add(
        radius=r, depth=depth, vertices=24,
        location=(x, y, z), rotation=(math.radians(rot_x), 0, 0))
    o = bpy.context.active_object
    o.name = name
    o.data.materials.append(material)
    return o

def ering(name, cx, cz, rx, rz, tube, y, material, clip=None):
    """Elliptical ring (tube) in the XZ plane, optionally boolean-clipped
    to a rectangular region (ccx, ccz, w, h) — that's how we get sweeping
    arcs that terminate exactly at the glass edges like the reference
    photos. Scale is applied to the curve BEFORE the bevel so the tube
    stays perfectly round on elliptical shapes."""
    bpy.ops.curve.primitive_bezier_circle_add(radius=1.0, location=(0, 0, 0))
    o = bpy.context.active_object
    o.scale = (rx, rz, 1.0)
    bpy.ops.object.transform_apply(scale=True)
    o.data.bevel_depth = tube
    o.data.bevel_resolution = 8
    o.data.resolution_u = 48
    bpy.ops.object.convert(target='MESH')
    o = bpy.context.active_object
    o.rotation_euler = (math.radians(90), 0, 0)
    o.location = (cx, y, cz)
    bpy.ops.object.transform_apply(rotation=True, location=True)
    o.name = name
    o.data.materials.append(material)
    if clip:
        ccx, ccz, w, h = clip
        bpy.ops.mesh.primitive_cube_add(size=1, location=(ccx, y, ccz))
        cb = bpy.context.active_object
        cb.scale = (w, tube * 8, h)
        bpy.ops.object.transform_apply(scale=True)
        mod = o.modifiers.new('clip', 'BOOLEAN')
        mod.operation = 'INTERSECT'
        mod.object = cb
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.modifier_apply(modifier='clip')
        bpy.data.objects.remove(cb, do_unlink=True)
    return o

# One door leaf: metal frame (stiles + rails) around a frosted glass panel.
# Returns (glass_width, glass_height, glass_center_z).
def leaf(cx, metal, glass, W=0.915, H=2.03, T=0.045,
         stile=0.11, top=0.11, bottom=0.28):
    box('stile_l', stile, T, H, cx - W/2 + stile/2, 0, H/2, metal)
    box('stile_r', stile, T, H, cx + W/2 - stile/2, 0, H/2, metal)
    gw = W - 2 * stile
    box('rail_top', gw, T, top, cx, 0, H - top/2, metal)
    box('rail_bot', gw, T, bottom, cx, 0, bottom/2, metal)
    gh = H - top - bottom
    gz = bottom + gh / 2
    box('glass', gw, 0.006, gh, cx, 0, gz, glass, bevel=0)
    return gw, gh, gz

def jamb(total_w, H, metal):
    """Outer door frame around the opening — matches the door finish
    (like the reference photos)."""
    t, d = 0.07, 0.085
    box('jamb_l', t, d, H + t, -(total_w/2 + t/2), 0.012, (H + t)/2, metal)
    box('jamb_r', t, d, H + t,  (total_w/2 + t/2), 0.012, (H + t)/2, metal)
    box('jamb_t', total_w + 2*t, d, t, 0, 0.012, H + t/2, metal)

def handle(x, hw, z0=0.95):
    """Stainless vertical pull bar + deadbolt above, on the front face."""
    box('mount', 0.030, 0.022, 0.05, x, -0.034, z0, hw, bevel=0.002)
    box('mount', 0.030, 0.022, 0.05, x, -0.034, z0 + 0.34, hw, bevel=0.002)
    cyl('pull', 0.011, 0.46, x, -0.062, z0 + 0.17, hw)
    cyl('bolt', 0.024, 0.014, x, -0.030, z0 + 0.55, hw, rot_x=90)

def hinges(x, hw):
    for z in (0.30, 1.015, 1.73):
        box('hinge', 0.018, 0.016, 0.10, x, 0, z, hw, bevel=0.002)

# Default pattern color: Bronze (display tone), Hardware: stainless.
BRONZE = (0.060, 0.040, 0.032)
GLASS_RGB = (0.85, 0.90, 0.92)

clear_scene()
METAL = make_mat('PatternMetal', BRONZE, metallic=0.6, roughness=0.4)
GLASS = make_mat('Glass', GLASS_RGB, metallic=0.0, roughness=0.65, alpha=0.35)
HW = make_mat('Hardware', (0.55, 0.55, 0.55), metallic=1.0, roughness=0.3)
PAT_Y = -0.024   # pattern bars sit slightly proud of the door face
PAT_D = 0.022    # pattern bar depth
TUBE = 0.018     # arc tube radius (substantial bars like the references)
'''

EXPORT = r'''
import os
os.makedirs(r'{out_dir}', exist_ok=True)
path = r'{out_path}'
bpy.ops.export_scene.gltf(filepath=path, export_format='GLB')
print('EXPORTED', path, os.path.getsize(path), 'bytes')
'''

ECLIPSE = r'''
# --- Eclipse: double door, two intersecting tall ovals per leaf (ref #2) ---
GAP = 0.004
W, H = 0.915, 2.03
TW = 2*W + GAP
jamb(TW, H, METAL)
for side in (-1, 1):
    cx = side * (W/2 + GAP/2)
    gw, gh, gz = leaf(cx, METAL, GLASS)
    clip = (cx, gz, gw, gh)
    for off in (-0.085, 0.085):
        ering('oval', cx + off, gz, 0.27, 0.62, TUBE, PAT_Y, METAL, clip)
    box('bar_t', gw, PAT_D, 0.038, cx, PAT_Y, gz + 0.66, METAL)
    box('bar_b', gw, PAT_D, 0.038, cx, PAT_Y, gz - 0.66, METAL)
    handle(side * 0.075, HW)
    hinges(side * (TW/2 + 0.004), HW)
'''

ORBIT = r'''
# --- Orbit: double door, center circle + corner arcs (ref #1) ---
GAP = 0.004
W, H = 0.915, 2.03
TW = 2*W + GAP
jamb(TW, H, METAL)
leaf_info = []
for side in (-1, 1):
    cx = side * (W/2 + GAP/2)
    gw, gh, gz = leaf(cx, METAL, GLASS)
    leaf_info.append((cx, gw, gh, gz))
    # sweeping arcs from the four outer corners of the glass
    for vz in (-1, 1):
        ering('corner_arc',
              cx + side * gw/2, gz + vz * gh/2,
              0.62, 0.62, TUBE, PAT_Y, METAL,
              clip=(cx, gz, gw, gh))
    handle(side * 0.075, HW)
    hinges(side * (TW/2 + 0.004), HW)
# big center circle crossing both leaves (sits proud of the meeting stiles)
cx0, gw0, gh0, gz0 = leaf_info[0]
span = TW - 0.22  # full glass span minus outer stiles
ering('center_circle', 0, gz0, 0.42, 0.42, TUBE, PAT_Y, METAL,
      clip=(0, gz0, span, gh0))
'''

ROMA = r'''
# --- Roma: single door, center bar with three rings ---
W, H = 0.915, 2.03
jamb(W, H, METAL)
gw, gh, gz = leaf(0, METAL, GLASS)
box('bar_c', 0.034, PAT_D, gh, 0, PAT_Y, gz, METAL)
box('bar_l', 0.026, PAT_D, gh, -gw * 0.30, PAT_Y, gz, METAL)
box('bar_r', 0.026, PAT_D, gh,  gw * 0.30, PAT_Y, gz, METAL)
for dz, r in ((-0.55, 0.13), (0.0, 0.19), (0.55, 0.13)):
    ering('ring', 0, gz + dz, r, r, 0.014, PAT_Y, METAL)
handle(0.30, HW)
hinges(-(W/2 + 0.004), HW)
'''

DESIGNS = {
    'door-eclipse.glb': ECLIPSE,
    'door-orbit.glb': ORBIT,
    'door-roma.glb': ROMA,
}


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    client = BlenderClient(timeout=300.0)
    for fname, body in DESIGNS.items():
        out_path = OUT_DIR / fname
        code = COMMON + body + EXPORT.format(
            out_dir=str(OUT_DIR), out_path=str(out_path))
        print(f'Building {fname}…')
        result = client.execute(code)
        out = result.get('result', '') if isinstance(result, dict) else str(result)
        print('  ' + out.strip().splitlines()[-1] if out.strip() else f'  {result}')
        if out_path.exists():
            print(f'  OK — {out_path} ({out_path.stat().st_size:,} bytes)')
        else:
            raise RuntimeError(f'{fname} was not written!')


if __name__ == '__main__':
    main()
