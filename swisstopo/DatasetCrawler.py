from os import walk
from os.path import splitext, join
import arcpy
from arcpy import env
import os

# Global Variables
rootDirectory = r"\\itetnas01.ee.ethz.ch\glazioarch\GlacioBaseData\GeoData\Swisstopo_L2"
shapeDirectory = r"\\itetnas01.ee.ethz.ch\glazioarch\GlacioBaseData\GeoData\Swisstopo_L2"
shapeFileName = "Swisstopo_L2_Datasets_lv03_NEW.shp"
geometryType = "POLYGON"

# Global Constants
FIELD_NAME_FILEPATH = "FilePath"
FIELD_NAME_TYPE = "DataType"
FIELD_NAME_YEAR = "Year"
FIELD_COORDINATE_SYSTEM = "CoordSys"

def selectFiles(root, files):

    selectedFiles = []

    for file in files:
        # Concatenation to get full path 
        fullPath = join(root, file)
        ext = splitext(file)[1]

        if ext.upper() == ".TIF" or ext.upper() == ".ASC":
            selectedFiles.append(fullPath)

    return selectedFiles

def buildRecursiveDirectoryTree(path):

    selectedFiles = []

    for root, dirs, files in walk(path):
        selectedFiles += selectFiles(root, files)

    return selectedFiles


def analyseDataset(selectedFile):
    
    desc = arcpy.Describe(selectedFile)
    print("Dataset Type: {0}".format(desc.datasetType))
    print("Extent:\n  XMin: {0}, XMax: {1}, YMin: {2}, YMax: {3}".format(desc.extent.XMin, desc.extent.XMax, desc.extent.YMin, desc.extent.YMax))

    print("Spatial reference name: {0}:".format(desc.spatialReference.name))

    return desc

def prepareFeatureClass(workspace, featureClassName, featureType):

    env.workspace = workspace
    if arcpy.Exists(featureClassName):
        arcpy.Delete_management(featureClassName)

    spatialReferenceLV03 = arcpy.SpatialReference("CH1903 LV03")
    arcpy.CreateFeatureclass_management(workspace, featureClassName, featureType, "", "", "", spatialReferenceLV03)

    # Adding the needed fields
    arcpy.AddField_management(featureClassName, FIELD_NAME_FILEPATH, "TEXT", "", "", 500, "", "NULLABLE", "")
    arcpy.AddField_management(featureClassName, FIELD_NAME_TYPE, "TEXT", "", "", 3, "", "NULLABLE", "")
    arcpy.AddField_management(featureClassName, FIELD_COORDINATE_SYSTEM, "TEXT", "", "", 9, "", "NULLABLE", "")
    arcpy.AddField_management(featureClassName, FIELD_NAME_YEAR, "SHORT", "", "", "", "", "NULLABLE", "")

    # Removing the default Id field
    arcpy.DeleteField_management(featureClassName, ["Id"])


def recursivePathAnalyser(path, parameter):
    pathParts = os.path.split(path)

    if parameter == "DATATYPE":
    
        if pathParts[1] == 'DOP' or pathParts[1] == 'DSM':
            return pathParts[1]
        else:
            return recursivePathAnalyser(pathParts[0], "DATATYPE")
        
    elif parameter == "YEAR":

        if pathParts[1].isdigit():
            return pathParts[1]
        else:
            return recursivePathAnalyser(pathParts[0], "YEAR")

    elif parameter == "COORDINATESYSTEM":

        if pathParts[1].upper().startswith("LV03") or pathParts[1].upper().startswith("LV95"):
            return pathParts[1]
        else:
            return recursivePathAnalyser(pathParts[0], "COORDINATESYSTEM")
  

def writeFootprint(workspace, featureClass, fileDescription):

    try:
        env.workspace = workspace

        cur = arcpy.da.InsertCursor(featureClass, ["SHAPE@", FIELD_NAME_FILEPATH, FIELD_NAME_TYPE, FIELD_COORDINATE_SYSTEM, FIELD_NAME_YEAR])

        array = arcpy.Array()

        array.add(arcpy.Point(fileDescription.extent.XMin, fileDescription.extent.YMin))
        array.add(arcpy.Point(fileDescription.extent.XMin, fileDescription.extent.YMax))
        array.add(arcpy.Point(fileDescription.extent.XMax, fileDescription.extent.YMax))
        array.add(arcpy.Point(fileDescription.extent.XMax, fileDescription.extent.YMin))

        # Add the first point of the array in to close off the polygon
        array.add(array.getObject(0))

        # Determination of the spatial reference based on the first coordinate and transformation into LV03 in case of LV95 coordinates.
        spatialReferenceLV03 = arcpy.SpatialReference("CH1903 LV03")
        footprint = None
        if fileDescription.extent.XMin > 2000000 and fileDescription.extent.YMin > 1000000:
            sr = arcpy.SpatialReference("CH1903+ LV95")
            tempFootprint = arcpy.Polygon(array, sr)
            footprint = tempFootprint.projectAs(spatialReferenceLV03)
        else:
            footprint = arcpy.Polygon(array, spatialReferenceLV03)

        datatype = recursivePathAnalyser(fileDescription.path, "DATATYPE")
        coordinateSystem = recursivePathAnalyser(fileDescription.path, "COORDINATESYSTEM")
        year = recursivePathAnalyser(fileDescription.path, "YEAR")

        cur.insertRow([footprint, fileDescription.path + "\\" + fileDescription.file, datatype, coordinateSystem, int(year)])
        
    except Exception as e:
        print e.message
    finally:
        if cur:
            del cur
    

# Getting the featureclass ready
prepareFeatureClass(shapeDirectory, shapeFileName, geometryType)

# Start to run the walk through the directories
selectedFiles = buildRecursiveDirectoryTree(rootDirectory)

for selectedFile in selectedFiles:
    print selectedFile
    fileDescription = analyseDataset(selectedFile)

    writeFootprint(shapeDirectory, shapeFileName, fileDescription)
    print "-----------------------------------------------------------------------------------------------\n\n"
    
