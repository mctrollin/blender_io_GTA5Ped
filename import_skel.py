import bpy
import os.path
import traceback
from mathutils import *
from . import readerutils

def import_skel_from_file(filepath):
    skelname = os.path.splitext(os.path.basename(filepath))[0]
    print("Import GTAV Skeleton {} : begin".format(skelname))
    with open(filepath, 'r', encoding='utf-8') as reader:
        string_to_skel(reader, skelname)

    return {'FINISHED'}


def string_to_skel(reader, skelName):
    #the skel file must have a "Version" header
    line = readerutils.read_until_line_containing(reader,"Version")
    
    if line == '':
        return
    
    print("Version OK")
    
    #store the number of bones declared in the file
    #so that we may know if we succeeded in importing all of them
    line = readerutils.read_until_line_containing(reader,"NumBones")
    
    if line == '':
        return
    
    boneCount = line.split(" ")[1]
    
    print("Bone count declared in file: {}".format(boneCount))
    
    #jump to the first bone
    line = readerutils.read_until_line_containing(reader,"Bone ")
    
    if line == '':
        return
    
    print("Got a bone! Should create armature then")
    armature, armatureObj = create_armature(skelName)
    
    armature.display_type = "STICK"
    
    #select new armatureObj, then add bones
    bpy.context.view_layer.objects.active = armatureObj
    
    boneDataList = []
    
    try:
        recursive_parse_bone(reader, line, armature, armatureObj, boneDataList)        
    except Exception as e:
        print("Bone parsing failed! {}.{}".format(e, traceback.format_exc()))
        
        delete_armature(armature)
        
    for boneData in boneDataList:
        apply_bone_data(boneData)
        
    bpy.ops.pose.armature_apply()
    bpy.ops.object.mode_set(mode="OBJECT")
    

def recursive_parse_bone(reader, curReaderLine, armature, armatureObj, boneDataList, parentPoseBone = None):
    """jumps to the next Bone line (if necessary) and creates a new bone and its children"""
    
    if "Bone " not in curReaderLine:
        curReaderLine = readerutils.read_until_line_containing(reader, "Bone ")
        
        if curReaderLine == '':
            return
        
    #get bone name from cur line and adds it to the armature
    boneName = curReaderLine.split(" ")[1]
    
    boneData = create_new_bone(armature, boneName, parentPoseBone)
    
    newPoseBone = armatureObj.pose.bones[boneData.name]
    
    boneData.poseBone = newPoseBone
    
    boneDataList.append(boneData)
    
    while "Children" not in curReaderLine and "}" not in curReaderLine:
        curReaderLine, boneData = parse_bone_dataline(reader, boneData)
        
    #apply gathered data now
    #apply_bone_data(newPoseBone, boneData)
        
    if "Children" in curReaderLine:
        childCount = int(curReaderLine.split(" ")[1])
        
        for _ in range(childCount):
            recursive_parse_bone(reader, curReaderLine, armature, armatureObj, boneDataList, newPoseBone)
        


def create_new_bone(armature, boneName, parentPoseBone = None):
    """goes into edit mode, creates a new bone with the target parent, then exits edit mode"""
    bpy.ops.object.mode_set(mode="EDIT")
    
    newEditBone = armature.edit_bones.new(boneName)
    
    boneData = GTABone()
    
    print("creating new bone: {}, parent: {}".format(newEditBone.name, parentPoseBone))
    
    if parentPoseBone is not None:
        parentBone = armature.edit_bones[parentPoseBone.name]
        newEditBone.parent = parentBone
        #newEditBone.use_connect = True
        newEditBone.head = parentPoseBone.head
        #print("set head to parent's pose head: {}".format(parentPoseBone.head))
        newEditBone.tail = parentPoseBone.tail
    else:
        #print("no parent, setting tail: {}".format(newEditBone.head))
        newEditBone.tail = newEditBone.head
        newEditBone.tail.y -= 0.02
        
    newBoneName = newEditBone.name
    
    bpy.ops.object.mode_set(mode="POSE")
    
    boneData.name = newBoneName
    
    return boneData
    
    

def parse_bone_dataline(reader, boneData):
    """goes to the next line and attempts to retrieve data from it"""
    line = reader.readline()
    
    if "RotationQuaternion" in line:
        lineData = line.split(" ")
        
        boneData.rotationQuat = Quaternion(map(float,lineData[1:]))
#        print(boneData.rotationQuat.magnitude)
        
    
    elif "LocalOffset" in line:
        lineData = line.split(" ")
        
        boneData.location = Vector(map(float,lineData[1:]))
        
    return line, boneData



def apply_bone_data(boneData):
    print("applying gathered bone data for bone {}".format(boneData.name))
    
    poseBone = boneData.poseBone
    
    if boneData.location is not None:
        poseBone.location.x = -boneData.location.x
        poseBone.location.y = -boneData.location.y
        poseBone.location.z = -boneData.location.z
        
        #print("LOC BEFORE QUAT MULT : {}".format(poseBone.location))
                
        #print("applied location {}".format(poseBone.location))
        
    if boneData.rotationQuat is not None:
        #rotMat = boneData.rotationQuat.to_matrix()
#        boneData.rotationQuat = rotMat.inverted().transposed().to_quaternion()
        #boneData.rotationQuat = boneData.rotationQuat.conjugated()
        poseBone.rotation_quaternion.w = -boneData.rotationQuat.z
        poseBone.rotation_quaternion.x = boneData.rotationQuat.y
        poseBone.rotation_quaternion.y = -boneData.rotationQuat.x
        poseBone.rotation_quaternion.z = -boneData.rotationQuat.w
        
        #poseBone.location = poseBone.rotation_quaternion @ poseBone.location
        
        #print("applied rotation {}".format(poseBone.rotation_quaternion))
    
        

def create_armature(armatureName):
    """Creates an armature object and adds it to the current collection"""
    armature = bpy.data.armatures.new(armatureName)
    armatureObj = bpy.data.objects.new(armatureName, armature)
    
    bpy.context.scene.collection.objects.link(armatureObj)
    
    return armature, armatureObj

def delete_armature(armature):
    """Deletes the target armature (armature obj will also be deleted)"""
    bpy.data.armatures.remove(armature)

class GTABone:
    pass


from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator

class ImportGta5Skel(Operator, ImportHelper):
    """Operator for importing a .skel separatedly"""
    bl_idname = "io_gta5ped.import_skel"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Import GTA5 Ped Skeleton (.skel)"

    # ImportHelper mixin class uses this
    filename_ext = ".skel"

    filter_glob: StringProperty(
        default="*.skel",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    def execute(self, context):
        return import_skel_from_file(self.filepath)


# Only needed if you want to add into a dynamic menu
def menu_func_import(self, context):
    self.layout.operator(ImportGta5Skel.bl_idname, text="Import GTA5 Ped Skeleton (.skel)")


def register():
    bpy.utils.register_class(ImportGta5Skel)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    bpy.utils.unregister_class(ImportGta5Skel)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
