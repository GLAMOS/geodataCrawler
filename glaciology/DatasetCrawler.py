# -*- coding: cp1252 -*-

from os import walk
from os.path import splitext, join
import arcpy
from arcpy import env
import os
from os.path import basename

# Global Variables
rootDirectory  = r"\\itetnas01.ee.ethz.ch\glazioarch\GlacioBaseData\GeoData\Glacier"
shapeDirectory = r"\\itetnas01.ee.ethz.ch\glazioarch\GlacioBaseData\GeoData\Glacier"
shapeFileName  = "vaw_L2_Datasets_lv03_temp03.shp"
geometryType   = "POLYGON"

# Global Constants
FIELD_NAME_FILEPATH     = "FilePath"
FIELD_NAME_GLACIER      = "Glacier"
FIELD_NAME_MEASUREDATE  = "MeasDate"
FIELD_NAME_TYPE         = "DataType"
FIELD_NAME_YEAR         = "Year"
FIELD_HORICOORD_SYSTEM  = "HoriCoord"
FIELD_VERTICOORD_SYSTEM = "VertiCoord"

UNKOWN_STRING_VALUE     = "unknown"

DELIMITOR_SPACE         = " "

#PRODUCTS_TO_ANALYZE     = {"DOP" : "Orthophoto", "TIN" : "Unregelmässiges Höhenmodell", "DSM" : "Regelmässiges Oberflächenmodell", "EDGE" : "Vollständige Gletscherumrisse", "TONGUE" : "Zungenbereich", "CONTOURLINE" : "Höhenkurven", "MAP" : "Georeferenzierte Karten", "PROFILE" : "Individuelle Punkte als Profillinien in Längs- oder Querrichtung zum Gletscher", "HILLSHADE" : "Relief basierend auf korrespondierendem DSM oder TIN"}
PRODUCTS_TO_ANALYZE     = {"DOP" : "Orthophoto", "TIN" : "Unregelmässiges Höhenmodell", "DSM" : "Regelmässiges Oberflächenmodell", "MAP" : "Georeferenzierte Karten"}

class MetaData(object):

    def __init__(self):
        self._xMin = 0
        self._xMax = 0
        self._yMin = 0
        self._yMax = 0

        self._name                 = UNKOWN_STRING_VALUE
        self._fullPath             = UNKOWN_STRING_VALUE
        self._spatialReferenceName = UNKOWN_STRING_VALUE

    @property
    def XMin(self):
        return self._xMin

    @property
    def XMax(self):
        return self._xMax

    @property
    def YMin(self):
        return self._yMin

    @property
    def YMax(self):
        return self._yMax

    @property
    def name(self):
        return self._name

    @property
    def fullPath(self):
        return self._fullPath

    @property
    def spatialReferenceName(self):
        return self._spatialReferenceName

class MetaDataRaster(MetaData):

    def parse(self, raster):

        self._fullPath = raster
        self._name = basename(raster)

        desc = arcpy.Describe(raster)

        self._xMin = desc.extent.XMin
        self._xMax = desc.extent.XMax

        self._yMin = desc.extent.YMin
        self._yMax = desc.extent.YMax

        self._spatialReferenceName = desc.spatialReference.name

class MetaDataXYZ(MetaData):

    def _analyseExtent(self):

        try:
            with open(self._fullPath) as f:
                for line in f:
                    
                    lineParts = line.split()

                    if len(lineParts) >= 3:
                        x = float(lineParts[0])
                        y = float(lineParts[1])
                        z = float(lineParts[2])

                        if x < self._xMin:
                            self._xMin = x
                        if x > self._xMax:
                            self._xMax = x

                        if y < self._yMin:
                            self._yMin = y
                        if y > self._yMax:
                            self._yMax = y

                    else:
                        self._xMin = 0
                        self._xMax = 10
                        self._yMin = 0
                        self._yMax = 10
                        
        except Exception as e:

            print "Exception during parsing of XYZ file: {0}".format(e.message) 

            self._xMin = 0
            self._xMax = 10
            self._yMin = 0
            self._yMax = 10


    def parse(self, xyzFile, delimiter):

        self._fullPath = xyzFile
        self._name = basename(xyzFile)

        self.__delimiter = delimiter

        self._xMin = 1000000000
        self._xMax = 0
        self._yMin = 1000000000
        self._yMax = 0

        self._analyseExtent()

def selectFiles(root, files):

    selectedFiles = []

    for file in files:
        # Concatenation to get full path 
        fullPath = join(root, file)
        ext = splitext(file)[1]

        if ext.upper() == ".TIF" or ext.upper() == ".ASC" or ext.upper().startswith(".XYZ"):
            selectedFiles.append(fullPath)

    return selectedFiles

def buildRecursiveDirectoryTree(path):

    selectedFiles = []

    for root, dirs, files in walk(path):
        selectedFiles += selectFiles(root, files)

    return selectedFiles


def analyseDataset(selectedFile):

    ext = splitext(selectedFile)[1]

    if ext.upper() == ".TIF" or ext.upper() == ".ASC":

        desc = MetaDataRaster()
        desc.parse(selectedFile)

        print("Dataset Type: {0}".format("Raster"))

    elif ext.upper().startswith(".XYZ"):

        desc = MetaDataXYZ()
        
        desc.parse(selectedFile, DELIMITOR_SPACE)

        print("Dataset Type: {0}".format("XYZ"))

    
    print("Extent:\n  XMin: {0}, XMax: {1}, YMin: {2}, YMax: {3}".format(desc.XMin, desc.XMax, desc.YMin, desc.YMax))
    print("Spatial reference name: {0}:".format(desc.spatialReferenceName))

    return desc

def prepareFeatureClass(workspace, featureClassName, featureType):

    env.workspace = workspace
    if arcpy.Exists(featureClassName):
        arcpy.Delete_management(featureClassName)

    spatialReferenceLV03 = arcpy.SpatialReference("CH1903 LV03")
    arcpy.CreateFeatureclass_management(workspace, featureClassName, featureType, "", "", "", spatialReferenceLV03)

    # Adding the needed fields
    arcpy.AddField_management(featureClassName, FIELD_NAME_GLACIER,      "TEXT",  "", "", 100, "", "NULLABLE", "")
    
    arcpy.AddField_management(featureClassName, FIELD_NAME_TYPE,         "TEXT",  "", "", 10,  "", "NULLABLE", "")
    arcpy.AddField_management(featureClassName, FIELD_NAME_MEASUREDATE,  "DATE",  "", "", "",  "", "NULLABLE", "")
    arcpy.AddField_management(featureClassName, FIELD_NAME_YEAR,         "SHORT", "", "", "",  "", "NULLABLE", "")
    arcpy.AddField_management(featureClassName, FIELD_HORICOORD_SYSTEM,  "TEXT",  "", "", 5,   "", "NULLABLE", "")
    arcpy.AddField_management(featureClassName, FIELD_VERTICOORD_SYSTEM, "TEXT",  "", "", 5,   "", "NULLABLE", "")

    arcpy.AddField_management(featureClassName, FIELD_NAME_FILEPATH,     "TEXT",  "", "", 500, "", "NULLABLE", "")

    # Removing the default Id field
    arcpy.DeleteField_management(featureClassName, ["Id"])


def fileNameAnalyser(fileName):

    print fileName

    fileNameParts = fileName.split(".")[0].split("_")

    glacierName = ""
    dateCoded   = ""
    product     = ""
    horizCoord  = ""
    vertCoord   = ""

    if len(fileNameParts) == 4:
        glacierName = fileNameParts[0]
        dateCoded   = fileNameParts[1]
        product     = fileNameParts[2].upper()
        horizCoord  = fileNameParts[3].upper()
    elif len(fileNameParts) == 5:
        glacierName = fileNameParts[0]
        dateCoded   = fileNameParts[1]
        product     = fileNameParts[2].upper()
        horizCoord  = fileNameParts[3].upper()
        vertCoord   = fileNameParts[4].upper()


    try:
        date = datetime.datetime.strptime(dateCoded, "%Y%m%d").date()
    except Exception as e:
        print "Exception during conversion of date: {0}".format(e.message)

        year = int(dateCoded[0:4])
        
        print "Only the year will be used with September 1st as default day: {0}".format(year)
        
        date = datetime.date(year, 9, 1)

    return [glacierName, date, product, horizCoord, vertCoord]


def writeFootprint(workspace, featureClass, fileDescription):

    cur = None

    try:
        env.workspace = workspace

        metadata = fileNameAnalyser(fileDescription.name)

        if metadata[2] in PRODUCTS_TO_ANALYZE:

            cur = arcpy.da.InsertCursor(featureClass, ["SHAPE@", FIELD_NAME_GLACIER, FIELD_NAME_MEASUREDATE, FIELD_NAME_YEAR, FIELD_NAME_TYPE, FIELD_HORICOORD_SYSTEM, FIELD_VERTICOORD_SYSTEM, FIELD_NAME_FILEPATH])

            array = arcpy.Array()

            array.add(arcpy.Point(fileDescription.XMin, fileDescription.YMin))
            array.add(arcpy.Point(fileDescription.XMin, fileDescription.YMax))
            array.add(arcpy.Point(fileDescription.XMax, fileDescription.YMax))
            array.add(arcpy.Point(fileDescription.XMax, fileDescription.YMin))

            # Add the first point of the array in to close off the polygon
            array.add(array.getObject(0))

            # Determination of the spatial reference based on the first coordinate and transformation into LV03 in case of LV95 coordinates.
            spatialReferenceLV03 = arcpy.SpatialReference("CH1903 LV03")
            footprint = None
            if fileDescription.XMin > 2000000 and fileDescription.YMin > 1000000:
                sr = arcpy.SpatialReference("CH1903+ LV95")
                tempFootprint = arcpy.Polygon(array, sr)
                footprint = tempFootprint.projectAs(spatialReferenceLV03)
            else:
                footprint = arcpy.Polygon(array, spatialReferenceLV03)

            cur.insertRow([footprint, metadata[0], metadata[1], metadata[1].year, metadata[2], metadata[3], metadata[4], fileDescription.fullPath])
        
    except Exception as e:
        print "Exception : {0}".format(e.message)
    finally:
        if cur != None:
            del cur
    

# Getting the featureclass ready
prepareFeatureClass(shapeDirectory, shapeFileName, geometryType)

# Start to run the walk through the directories
selectedFiles = buildRecursiveDirectoryTree(rootDirectory)

print PRODUCTS_TO_ANALYZE

for selectedFile in selectedFiles:
    print selectedFile
    fileDescription = analyseDataset(selectedFile)

    writeFootprint(shapeDirectory, shapeFileName, fileDescription)
    print "-----------------------------------------------------------------------------------------------\n\n"
    
