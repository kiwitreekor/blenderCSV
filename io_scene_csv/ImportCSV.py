#    Copyright 2018, 2019 Dmirty Pritykin, 2019 S520
#
#    This file is part of blenderCSV.
#
#    blenderCSV is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    blenderCSV is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with blenderCSV.  If not, see <http://www.gnu.org/licenses/>.

import bpy
import pathlib
import mathutils
from . import CSV
from . import logger
from . import Transform


class ImportCsv:
    INV255 = 1.0 / 255.0

    def __init__(self):
        self.file_path = ""

    def get_same_material(self, csv_mesh: CSV.CsvMesh, mat_name: str) -> bpy.types.Material:
        mat = bpy.data.materials.get(mat_name)

        if mat is None:
            return None

        if mat.diffuse_color[0] != csv_mesh.diffuse_color[0] * self.INV255 or mat.diffuse_color[1] != csv_mesh.diffuse_color[1] * self.INV255 or mat.diffuse_color[2] != csv_mesh.diffuse_color[2] * self.INV255:
            return None

        if csv_mesh.diffuse_color[3] != 255:
            if mat.alpha != csv_mesh.diffuse_color[3] * self.INV255:
                return None

        return mat

    def create_material(self, csv_mesh: CSV.CsvMesh, blender_mesh: bpy.types.Mesh) -> None:
        # Decide the name of the material. If a texture file exists, use that file name.
        if csv_mesh.texture_file != "":
            mat_name = pathlib.Path(csv_mesh.texture_file).stem
        else:
            mat_name = blender_mesh.name

        # Check if the same material already exists.
        mat = self.get_same_material(csv_mesh, mat_name)

        # Since the same material does not exist, create a new one.
        if mat is None:
            logger.debug("Create new material: " + mat_name)
            mat = bpy.data.materials.new(mat_name)
            mat.diffuse_color = (csv_mesh.diffuse_color[0] * self.INV255, csv_mesh.diffuse_color[1] * self.INV255, csv_mesh.diffuse_color[2] * self.INV255)
            mat.alpha = csv_mesh.diffuse_color[3] * self.INV255
            mat.transparency_method = "Z_TRANSPARENCY"
            mat.use_transparency = csv_mesh.diffuse_color[3] != 255

            # Set the texture on the material.
            if csv_mesh.texture_file != "":
                texture_path = pathlib.Path(self.file_path).joinpath("..", csv_mesh.texture_file).resolve()
                texture = bpy.data.textures.get(texture_path.stem)

                if texture is None:
                    texture = bpy.data.textures.new(texture_path.stem, "IMAGE")
                    texture.image = bpy.data.images.load(str(texture_path))

                slot = mat.texture_slots.add()
                slot.texture = texture
                slot.texture_coords = "UV"
                slot.uv_layer = "default"
                slot.use_map_color_diffuse = True
                slot.use_map_alpha = True
                slot.alpha_factor = mat.alpha
                mat.alpha = 0.0
                mat.use_transparency = True

        # Set the material on the mesh.
        blender_mesh.materials.append(mat)

    def set_texcoords(self, csv_mesh: CSV.CsvMesh, blender_mesh: bpy.types.Mesh) -> None:
        blender_mesh.uv_textures.new("default")

        for face in blender_mesh.polygons:
            for vert_idx, loop_idx in zip(face.vertices, face.loop_indices):
                try:
                    texcoords = [j for j in csv_mesh.texcoords_list if j[0] == vert_idx][0]
                except Exception:
                    logger.error("VertexIndex: " + str(vert_idx) + " is not defined with the SetTextureCoordinates command.")
                    continue

                blender_mesh.uv_layers["default"].data[loop_idx].uv = [texcoords[1], 1.0 - texcoords[2]]

    def import_model(self, file_path: str, use_transform_coords: bool) -> None:
        self.file_path = file_path

        meshes_list = CSV.CsvObject().load_csv(file_path)

        logger.info("Loaded meshes: " + str(len(meshes_list)))

        for i in range(len(meshes_list)):
            logger.info("Loaded mesh" + str(i) + ": (Vertex: " + str(len(meshes_list[i].vertex_list)) + ", Face: " + str(len(meshes_list[i].faces_list)) + ")")

            for j in range(len(meshes_list[i].vertex_list)):
                logger.debug("Vertex" + str(j) + ": " + str(meshes_list[i].vertex_list[j]))

            for j in range(len(meshes_list[i].faces_list)):
                logger.debug("Face" + str(j) + ": " + str(meshes_list[i].faces_list[j]))
                pass

        obj_base_name = pathlib.Path(file_path).stem

        for i in range(len(meshes_list)):
            blender_mesh = bpy.data.meshes.new(str(obj_base_name) + " - " + str(i))
            blender_mesh.from_pydata(meshes_list[i].vertex_list, [], meshes_list[i].faces_list)
            blender_mesh.update(True)

            self.create_material(meshes_list[i], blender_mesh)

            self.set_texcoords(meshes_list[i], blender_mesh)

            if use_transform_coords:
                Transform.swap_coordinate_system(mathutils.Matrix.identity(), blender_mesh)

            obj = bpy.data.objects.new(blender_mesh.name, blender_mesh)
            bpy.context.scene.objects.link(obj)
            obj.select = True
