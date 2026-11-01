import bpy, math, sys, time
OUT = sys.argv[-1]
SAMPLES = int(sys.argv[-2])
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene

def cr(pts, n=10):
    """Closed Catmull-Rom; a point listed twice becomes a sharp corner."""
    out=[]; N=len(pts)
    for i in range(N):
        p0,p1,p2,p3=pts[i-1],pts[i],pts[(i+1)%N],pts[(i+2)%N]
        for k in range(n):
            t=k/n; t2=t*t; t3=t2*t
            out.append(tuple(0.5*((2*p1[j])+(-p0[j]+p2[j])*t+(2*p0[j]-5*p1[j]+4*p2[j]-p3[j])*t2+(-p0[j]+3*p1[j]-3*p2[j]+p3[j])*t3) for j in range(2)))
    ded=[out[0]]
    for q in out[1:]:
        if abs(q[0]-ded[-1][0])+abs(q[1]-ded[-1][1])>1e-4: ded.append(q)
    if abs(ded[0][0]-ded[-1][0])+abs(ded[0][1]-ded[-1][1])<1e-4: ded.pop()
    return ded

def shape(name, pts, z, extrude, bevel, mat, parent):
    import bmesh
    P=cr(pts); me=bpy.data.meshes.new(name); bm=bmesh.new()
    vs=[bm.verts.new((-(x-10),y,0)) for x,y in P]
    f=bm.faces.new(vs); bm.normal_update()
    if f.normal.z<0: f.normal_flip()
    bm.to_mesh(me); bm.free()
    ob=bpy.data.objects.new(name,me); ob.location.z=z; ob.parent=parent
    sc.collection.objects.link(ob); me.materials.append(mat)
    so=ob.modifiers.new("Solid",'SOLIDIFY'); so.thickness=extrude*2; so.offset=0
    bv=ob.modifiers.new("Bevel",'BEVEL'); bv.width=bevel; bv.segments=4; bv.limit_method='ANGLE'
    tr=ob.modifiers.new("Tri",'TRIANGULATE')
    for poly in me.polygons: poly.use_smooth=False
    return ob

def cyl(name, x, y, z, r, d, mat, parent, verts=32):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=d, location=(-(x-10),y,z))
    ob=bpy.context.object; ob.name=name; ob.parent=parent; ob.data.materials.append(mat)
    bpy.ops.object.shade_smooth(); return ob

# ---------- materials ----------
def gamma_mat():
    m=bpy.data.materials.new("GammaSwirl"); m.use_nodes=True; nt=m.node_tree; N=nt.nodes; L=nt.links
    b=N["Principled BSDF"]
    tc=N.new("ShaderNodeTexCoord"); mp=N.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value=(0.14,0.14,0.14)
    n1=N.new("ShaderNodeTexNoise"); n1.inputs["Scale"].default_value=1.6; n1.inputs["Detail"].default_value=9; n1.inputs["Distortion"].default_value=1.4; n1.inputs["Roughness"].default_value=0.62
    r1=N.new("ShaderNodeValToRGB"); e=r1.color_ramp.elements
    e[0].position=0.30; e[0].color=(0.004,0.08,0.03,1)
    e[1].position=0.74; e[1].color=(0.55,1.0,0.95,1)
    for pos,col in [(0.42,(0.02,0.55,0.10,1)),(0.52,(0.03,0.75,0.65,1)),(0.61,(0.06,0.40,1.0,1))]:
        el=e.new(pos); el.color=col
    n2=N.new("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value=4.5; n2.inputs["Detail"].default_value=12; n2.inputs["Distortion"].default_value=4.0
    r2=N.new("ShaderNodeValToRGB"); f=r2.color_ramp.elements
    f[0].position=0.44; f[0].color=(0.04,0.10,0.07,1); f[1].position=0.54; f[1].color=(1,1,1,1)
    mix=N.new("ShaderNodeMix"); mix.data_type='RGBA'; mix.blend_type='MULTIPLY'; mix.inputs[0].default_value=0.75
    L.new(tc.outputs["Object"],mp.inputs["Vector"]); L.new(mp.outputs["Vector"],n1.inputs["Vector"]); L.new(mp.outputs["Vector"],n2.inputs["Vector"])
    L.new(n1.outputs["Fac"],r1.inputs["Fac"]); L.new(n2.outputs["Fac"],r2.inputs["Fac"])
    L.new(r1.outputs["Color"],mix.inputs[6]); L.new(r2.outputs["Color"],mix.inputs[7])
    L.new(mix.outputs[2],b.inputs["Base Color"])
    b.inputs["Metallic"].default_value=0.8; b.inputs["Roughness"].default_value=0.22
    b.inputs["Coat Weight"].default_value=0.7; b.inputs["Coat Roughness"].default_value=0.05
    return m
def metal(name,c,rough):
    m=bpy.data.materials.new(name); m.use_nodes=True; b=m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value=(c,c,c*1.04,1); b.inputs["Metallic"].default_value=1; b.inputs["Roughness"].default_value=rough
    return m
GAMMA=gamma_mat(); STEEL=metal("Steel",0.55,0.28); DARK=metal("DarkSteel",0.12,0.35)

root=bpy.data.objects.new("Knife",None); sc.collection.objects.link(root)

# ---------- geometry (side profile, x along length, tip at x≈20) ----------
blade=[(8.6,0.95),(11,1.05),(13.5,1.2),(15.8,1.45),(17.6,1.95),(19.1,2.75),(20.4,3.7),(20.4,3.7),
       (19.6,2.35),(18.3,1.05),(16.4,0.0),(14.0,-0.55),(11.5,-0.7),(10.0,-0.6),(9.6,-0.25),(9.2,-0.45),(8.6,-0.5)]
shape("Blade",blade,0.0,0.07,0.06,GAMMA,root)
# lighter ground edge along the cutting side
edge=[(9.7,-0.42),(11.5,-0.5),(14.0,-0.36),(16.3,0.15),(18.2,1.18),(19.5,2.45),(20.25,3.5),(20.25,3.5),
      (19.6,2.35),(18.3,1.05),(16.4,0.0),(14.0,-0.55),(11.5,-0.7),(10.0,-0.6)]
shape("Edge",edge,0.09,0.012,0.012,metal("Edge",0.75,0.18),root)

handle=[(9.4,1.0),(7.0,0.95),(4.5,0.75),(2.2,0.35),(0.4,-0.25),(-0.5,-0.95),(-0.45,-1.65),(0.4,-1.95),
        (1.3,-1.6),(2.2,-1.25),(3.1,-1.7),(4.1,-1.45),(5.0,-1.85),(6.0,-1.55),(7.2,-1.2),(8.4,-1.0),(9.4,-0.75)]
shape("Handle",handle,0.0,0.32,0.08,GAMMA,root)
bolster=[(10.3,1.08),(7.4,1.05),(6.6,0.6),(6.8,-0.6),(7.3,-1.25),(8.6,-1.05),(10.3,-0.7)]
shape("Bolster",bolster,0.0,0.4,0.06,STEEL,root)
butt=[(1.0,-0.05),(0.4,-0.25),(-0.5,-0.95),(-0.45,-1.65),(0.4,-1.95),(0.9,-1.75),(0.2,-1.3)]
shape("ButtCap",butt,0.0,0.4,0.05,STEEL,root)
cyl("Pivot",9.2,0.15,0.47,0.3,0.12,DARK,root); cyl("PivotRing",9.2,0.15,0.43,0.42,0.06,STEEL,root)
for (x,y) in [(7.6,0.55),(7.9,-0.75),(3.6,0.15)]: cyl("Screw",x,y,0.45,0.13,0.1,DARK,root)
cyl("Lanyard",0.1,-1.1,0.0,0.22,0.9,DARK,root)
root.rotation_euler=(math.radians(14),math.radians(-8),math.radians(-36)); root.location=(0,0.4,0)

# ---------- backdrop, lights, camera ----------
bpy.ops.mesh.primitive_plane_add(size=120,location=(0,0,-6)); bd=bpy.context.object
bm=bpy.data.materials.new("Backdrop"); bm.use_nodes=True; nt=bm.node_tree; nt.nodes.clear()
tc=nt.nodes.new("ShaderNodeTexCoord"); mp=nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value=(1/18,1/18,1)
gr=nt.nodes.new("ShaderNodeTexGradient"); gr.gradient_type='SPHERICAL'
rp=nt.nodes.new("ShaderNodeValToRGB"); rp.color_ramp.elements[0].color=(0.006,0.008,0.011,1); rp.color_ramp.elements[1].color=(0.03,0.04,0.05,1)
em=nt.nodes.new("ShaderNodeEmission"); out=nt.nodes.new("ShaderNodeOutputMaterial")
nt.links.new(tc.outputs["Object"],mp.inputs["Vector"]); nt.links.new(mp.outputs["Vector"],gr.inputs["Vector"])
nt.links.new(gr.outputs["Fac"],rp.inputs["Fac"]); nt.links.new(rp.outputs["Color"],em.inputs["Color"]); nt.links.new(em.outputs["Emission"],out.inputs["Surface"])
bd.data.materials.append(bm); bd.visible_glossy=False; bd.visible_diffuse=False

def area(loc,rot,size,energy,cam=False):
    bpy.ops.object.light_add(type='AREA',location=loc,rotation=rot); l=bpy.context.object
    l.data.size=size; l.data.energy=energy; l.visible_camera=cam; return l
area((0,0,22),(0,0,0),26,900)                                   # softbox the flat steel reflects
area((-10,10,12),(math.radians(-35),math.radians(-35),0),8,2200) # key from upper left
area((12,-9,6),(math.radians(55),math.radians(40),0),5,1200)     # rim
w=bpy.data.worlds.new("W"); sc.world=w; w.use_nodes=True; w.node_tree.nodes["Background"].inputs[0].default_value=(0.02,0.025,0.03,1)

bpy.ops.object.camera_add(location=(0,0,40),rotation=(0,0,0)); cam=bpy.context.object
cam.data.type='ORTHO'; cam.data.ortho_scale=20; sc.camera=cam

sc.render.engine='CYCLES'; sc.cycles.device='CPU'; sc.cycles.samples=SAMPLES; sc.cycles.use_denoising=True
sc.render.resolution_x=1600; sc.render.resolution_y=1600
sc.view_settings.view_transform='AgX'; sc.view_settings.look='AgX - Medium High Contrast'
sc.render.filepath=OUT
t=time.time(); bpy.ops.render.render(write_still=True); print("RENDER %.1fs"%(time.time()-t))
bpy.ops.wm.save_as_mainfile(filepath=OUT.replace('.png','.blend'))
