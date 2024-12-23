# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####
# <pep8 compliant>

bl_info = {
    "name": "New Batch export FBX files",
    "author": "brockmann",
    "version": (0, 1, 0),
    "blender": (2, 80, 0),
    "location": "File > Import-Export",
    "description": "Batch Export Objects in Selection to FBX",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Import-Export"}


import bpy
import os
import mathutils
import math

from bpy_extras.io_utils import ExportHelper

from bpy.props import (BoolProperty,
                       FloatProperty,
                       StringProperty,
                       EnumProperty,
                       CollectionProperty
                       )
                       
def reset_parent_inverse(ob):
    if (ob.parent):
        mat_world = ob.matrix_world.copy()
        ob.matrix_parent_inverse.identity()
        ob.matrix_basis = ob.parent.matrix_world.inverted() @ mat_world


def apply_rotation(ob):
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.ops.object.transform_apply(location = False, rotation = True, scale = False)

def fix_object(ob):
    # Only fix objects in current view layer
    if ob.name in bpy.context.view_layer.objects:

        # Reset parent's inverse so we can work with local transform directly
        reset_parent_inverse(ob)

        # Create a copy of the local matrix and set a pure X-90 matrix
        mat_original = ob.matrix_local.copy()
        ob.matrix_local = mathutils.Matrix.Rotation(math.radians(-90.0), 4, 'X')

        # Apply the rotation to the object
        apply_rotation(ob)

        # Reapply the previous local transform with an X+90 rotation
        ob.matrix_local = mat_original @ mathutils.Matrix.Rotation(math.radians(90.0), 4, 'X')

    # Recursively fix child objects in current view layer.
    # Children may be in the current view layer even if their parent isn't.
    for child in ob.children:
        fix_object(child)

class Batch_FBX_Export(bpy.types.Operator, ExportHelper):
    """Batch export objects to fbx files"""
    bl_idname = "export_scene.batch_fbx"
    bl_label = "Batch export FBX"
    bl_options = {'PRESET', 'UNDO'}

    # ExportHelper mixin class uses this
    filename_ext = ".fbx"

    filter_glob = StringProperty(
            default="*.fbx",
            options={'HIDDEN'},
            )

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator setting before calling.

    # context group
    use_selection_setting: BoolProperty(
            name="Selection Only",
            description="Export selected objects only",
            default=True,
            ) # type: ignore

    use_mesh_modifiers_setting: BoolProperty(
            name="Apply Modifiers",
            description="Apply modifiers (preview resolution)",
            default=True,
            ) # type: ignore

    axis_forward_setting: EnumProperty(
            name="Forward",
            items=(('X', "X Forward", ""),
                   ('Y', "Y Forward", ""),
                   ('Z', "Z Forward", ""),
                   ('-X', "-X Forward", ""),
                   ('-Y', "-Y Forward", ""),
                   ('-Z', "-Z Forward", ""),
                   ),
            default='-Z',
            ) # type: ignore

    axis_up_setting: EnumProperty(
            name="Up",
            items=(('X', "X Up", ""),
                   ('Y', "Y Up", ""),
                   ('Z', "Z Up", ""),
                   ('-X', "-X Up", ""),
                   ('-Y', "-Y Up", ""),
                   ('-Z', "-Z Up", ""),
                   ),
            default='Y',
            ) # type: ignore

    global_scale_setting: FloatProperty(
            name="Scale",
            min=0.01, max=1000.0,
            default=1.0,
            ) # type: ignore


    def execute(self, context):      

        # get the folder
        folder_path = os.path.dirname(self.filepath)

        # get objects selected in the viewport
        viewport_selection = context.selected_objects

        # get export objects
        obj_export_list = viewport_selection
        if self.use_selection_setting == False:
            obj_export_list = [i for i in context.scene.objects]

        # deselect all objects
        bpy.ops.object.select_all(action='DESELECT')

        for item in obj_export_list:
            item.select_set(True)
            if item.type == 'MESH':
                
                name = item.name
                
                # Duplicate the selected object 
                bpy.context.view_layer.objects.active = item 
                bpy.ops.object.duplicate() 
                duplicate_object = bpy.context.view_layer.objects.active
                
                # Print the name of the duplicated object for confirmation 
                print(f"Duplicated object: {duplicate_object.name}") 
                # Ensure the duplicated object is selected 
                duplicate_object.select_set(True)
                
                # Apply modifiers
                if hasattr(duplicate_object, "modifiers"):
                    for modifier in duplicate_object.modifiers: 
                        print(f"Object: {bpy.context.object.name}")
                        print(f"Applying modifier: {modifier.type}")
                        bpy.ops.object.modifier_apply(modifier=modifier.name)
                    
                # Apply correct rotation
                fix_object(duplicate_object)
                
                file_path = os.path.join(folder_path, "{}.fbx".format(name))

                # FBX settings
                bpy.ops.export_scene.fbx(
                        filepath=file_path, 
                        use_selection=self.use_selection_setting, 
                        use_active_collection=False, 
                        global_scale=self.global_scale_setting, 
                        apply_unit_scale=True, 
                        apply_scale_options='FBX_SCALE_NONE', 
                        bake_space_transform=False, 
                        object_types={'EMPTY', 'CAMERA', 'LIGHT', 'ARMATURE', 'MESH', 'OTHER'}, 
                        use_mesh_modifiers=self.use_mesh_modifiers_setting, 
                        use_mesh_modifiers_render=True, 
                        mesh_smooth_type='OFF', 
                        use_subsurf=False, 
                        use_mesh_edges=False, 
                        use_tspace=False, 
                        use_custom_props=False, 
                        add_leaf_bones=True, primary_bone_axis='Y', 
                        secondary_bone_axis='X', 
                        use_armature_deform_only=False, 
                        armature_nodetype='NULL', 
                        bake_anim=True, 
                        bake_anim_use_all_bones=True, 
                        bake_anim_use_nla_strips=True, 
                        bake_anim_use_all_actions=True, 
                        bake_anim_force_startend_keying=True, 
                        bake_anim_step=1, 
                        bake_anim_simplify_factor=1, 
                        path_mode='AUTO', 
                        embed_textures=False, 
                        batch_mode='OFF', 
                        use_batch_own_dir=True, 
                        use_metadata=True, 
                        axis_forward=self.axis_forward_setting, 
                        axis_up=self.axis_up_setting
                        )
                        
   
                # Delete the selected object 
                bpy.ops.object.delete()
         
                #item.select_set(False)
                
                # Apply the original rotation to the object
                # apply_rotation(item)
            

        # restore viewport selection
        for ob in viewport_selection:
            ob.select_set(True)

        # TODO: Reset rotation after done

        return {'FINISHED'}


# Only needed if you want to add into a dynamic menu
def menu_func_import(self, context):
    self.layout.operator(Batch_FBX_Export.bl_idname, text="FBX Batch Export (.fbx)")


def register():
    bpy.utils.register_class(Batch_FBX_Export)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_import)


def unregister():
    bpy.utils.unregister_class(Batch_FBX_Export)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_import)


if __name__ == "__main__":
    register()

    # test call
    #bpy.ops.export_scene.batch_fbx('INVOKE_DEFAULT')
