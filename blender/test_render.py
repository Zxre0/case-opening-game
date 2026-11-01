import bpy, time
bpy.ops.wm.read_factory_settings(use_empty=True)
sc=bpy.context.scene
bpy.ops.mesh.primitive_monkey_add(location=(0,0,0)); m=bpy.context.object
bpy.ops.object.modifier_add(type='SUBSURF'); m.modifiers[0].levels=2; bpy.ops.object.shade_smooth()
mat=bpy.data.materials.new("orange"); mat.use_nodes=True
b=mat.node_tree.nodes["Principled BSDF"]; b.inputs["Base Color"].default_value=(1,.45,.1,1); b.inputs["Metallic"].default_value=.6; b.inputs["Roughness"].default_value=.3
m.data.materials.append(mat)
bpy.ops.object.camera_add(location=(0,-4,1), rotation=(1.35,0,0)); sc.camera=bpy.context.object
bpy.ops.object.light_add(type='AREA', location=(2,-2,3)); bpy.context.object.data.energy=500
w=bpy.data.worlds.new("w"); sc.world=w; w.use_nodes=True; w.node_tree.nodes["Background"].inputs[0].default_value=(.05,.06,.08,1)
sc.render.engine='CYCLES'; sc.cycles.device='CPU'; sc.cycles.samples=32
sc.render.resolution_x=640; sc.render.resolution_y=400
import os; sc.render.filepath=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','renders','test_render.png')
t=time.time(); bpy.ops.render.render(write_still=True); print("rendered in %.1fs"%(time.time()-t))
