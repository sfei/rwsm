#!/usr/bin/env python

"""helpers.py: Helper files for common tasks."""

__copyright__ = """
    Copyright (C) 2018 San Francisco Estuary Institute (SFEI)

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Lesser General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Lesser General Public License for more details.

    You should have received a copy of the GNU Lesser General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

__copyright__ = "Copyright 2017, San Francisco Estuary Institute"

import os
import sys
import csv
import ConfigParser
import arcpy
import arcinfo
import datetime
import logging
import time

# Log levels are for debugging the application via Python command line,
# which is outside the scope of this initial beta release.
# LOG_LEVEL = logging.DEBUG  # Only show debug and up
# LOG_LEVEL = logging.NOTSET # Show all messages
# LOG_LEVEL = logging.CRITICAL # Only show critical messages


def strip_chars(watershed_name, strip_set):
    """Strips illegal characters from watershed name
    
    Arguments:
        watershed_name {string} -- name for the watershed of interest, should avoid numeric as first character
        strip_set {string} -- characters to remove from watershed name
    
    Returns:
        string -- watershed name with characters from strip_set removed
    """

    watershed_name_tmp = ''.join(watershed_name.split())
    for char in strip_set:
        watershed_name_tmp = watershed_name_tmp.replace(char, '')
    return watershed_name_tmp


def get_logger(logger_level):
    """Initialize a logger instance
    
    Arguments:
        logger_level {level} -- enumerated, numeric value corresponding to logging level
    
    Returns:
        instance -- instance of python logger
    """
    
    logging.basicConfig(level=logger_level)
    logger = logging.getLogger(__name__)
    return logger


def load_slope_bins(config, get_dict=False):
    """Populate slope bin list structure. Reteurn dictionary if specified.
    
    Arguments:
        config {instance} -- ConfigParser instance holding RWSM parameters
    
    Keyword Arguments:
        get_dict {bool} -- Choose to return a dictionary of slope values, default is a list (default: {False})
    
    Returns:
        dictionary or list -- slope bins contained within a dictionary or list
    """

    runoff_coeff_file_name = config.get("RWSM", "runoff_coeff_file_name")
    slope_file_name = config.get("RWSM", "slope_file_name")
    slope_bin_field = config.get("RWSM", "runoff_coeff_slope_bin_field")

    if get_dict:
        slope_bins = {}
    else:
        slope_bins = []

    slope_bins_strs = []
    slope_raster = arcpy.sa.Raster(slope_file_name)
    slope_raster_max = int(slope_raster.maximum)

    # Gather unique slope bin values
    with open(runoff_coeff_file_name, 'rb') as csvfile:
        reader = csv.reader(csvfile)
        headers = next(reader, None)  # skip the headers
        slope_idx = headers.index(slope_bin_field)
        for row in reader:
            slope = row[slope_idx]
            if slope not in slope_bins_strs:
                slope_bins_strs.append(slope)

    # Convert strings to numeric values
    if get_dict:
        for slope_bin in slope_bins_strs:
            if "+" in slope_bin:
                slope_bins[slope_bin] = [
                    int(slope_bin.strip("+").strip("%")), slope_raster_max]
            else:
                slope_bins[slope_bin] = map(lambda x: int(
                    x), slope_bin.strip("%").split("-"))
    else:
        for slope_bin in slope_bins_strs:
            if "+" in slope_bin:
                slope_bins.append(
                    [int(slope_bin.strip("+").strip("%")), slope_raster_max])
            else:
                slope_bins.append(
                    map(lambda x: int(x), slope_bin.strip("%").split("-")))

    return slope_bins


def load_land_use_table(config):
    """Load unique sets of land use codes, land use descriptions, and classifications
    
    Arguments:
        config {instance} -- ConfigParser instance containing RWSM parameters
    
    Returns:
        list -- list of triplets containing each observed code, description and classification combination
    """


    # Gather relevant parameter values
    file_name = config.get("RWSM", "land_use_LU_file_name")
    code_field = config.get("RWSM", "land_use_field")
    description_field = config.get("RWSM", "land_use_LU_desc_field")
    classification_field = config.get("RWSM", "land_use_LU_class_field")

    # Populate values structure with unique triples
    values = []
    with open(file_name, 'rb') as csvfile:
        reader = csv.reader(csvfile)
        headers = reader.next()
        code_idx = headers.index(code_field)
        description_idx = headers.index(description_field)
        classification_idx = headers.index(classification_field)

        for row in reader:
            code = row[code_idx]
            description = row[description_idx]
            classification = row[classification_idx]
            if (code, description, classification) not in values:
                values.append((code, description, classification))

    return values


# TODO: Check if we want to dynamically apply coefficient fields based on location category
def load_runoff_coeff_lu(file_name, coefficient_field):
    """Helper function for populating land use data structure
    
    Arguments:
        file_name {string} -- path to runoff coefficient file
        coefficient_field {string} -- field name for column containing runoff coefficients
    
    Returns:
        dictionary -- dictionary containing two dictionaries; dict of triplets for each set of runoff parameters
            (i.e. slope, soil, category) assigned to coefficients, dict for converting codes to coefficients.
    """


    # Initialize data structure, dictionary with three valued tuples
    runoff_lu = {
        "sets": {},
        "codes": {}
    }

    # Read and loop through CSV, populate structure
    with open(file_name, 'rb') as csvfile:
        reader = csv.reader(csvfile)
        headers = reader.next()
        coeff_index = headers.index(coefficient_field)
        for row in reader:
            slope = row[1]
            soil = row[2]
            category = row[3]
            code = row[7]
            coeff = row[coeff_index]
            runoff_set = (slope, soil, category)
            if runoff_set not in runoff_lu["sets"].keys():
                runoff_lu["sets"][runoff_set] = coeff
            runoff_lu["codes"][code] = coeff
    return runoff_lu

# Read parameter values from configuration file


def load_config(file_name):
    """Instantiate and return ConfigParser instance containing RWSM parameters
    
    Arguments:
        file_name {string} -- path to configuration file
    
    Returns:
        instance -- ConfigParser instance containing RWSM parameters
    """

    config = ConfigParser.ConfigParser()
    config.readfp(open(file_name))
    return config


def get_empty_config():
    """Instantiate blank ConfigParser instance
    
    Returns:
        instance -- blank ConfigParser instance
    """

    config = ConfigParser.ConfigParser()
    return config

# Write configuration file using user supplied values


def write_config(file_name, params):
    """Writes config instance to file for future use.
    
    Arguments:
        file_name {string} -- path for output file
        params {list} -- list of arcpy parameter instances, object obtained from GUI
    """

    config = ConfigParser.RawConfigParser()

    config.add_section("RWSM")

    for param in params:
        config.set("RWSM", param.name, param.valueAsText)


def load_csv(file_name):
    """Read in CSV file
    
    Arguments:
        file_name {string} -- path to CSV file
    
    Returns:
        list -- list from CSV reader
    """

    with open(file_name, "r") as csv_file:
        reader = csv.reader(csv_file, delimiter=",")
        return list(reader)


def init_workspace(workspace):
    """Initialize workspace for writing temporary and output files.
    
    Arguments:
        workspace {string} -- path to folder for writing temporary and output files
    
    Returns:
        tuple -- tuple of strings containing temporary, output, and workspace paths
    """

    # TODO: Read from configuration file.
    create_new_folder = True

    # Get date and time for folder names.
    date = str(datetime.datetime.today())[:10].replace('-', '')
    time = str(datetime.datetime.today())[11:19].replace(':', '')

    # If create_new_folder flagged, append workspace folder path.
    if create_new_folder:
        workspace += '_{}_{}'.format(date, time)
        if not os.path.exists(workspace):
            os.makedirs(workspace)

    # Initiate workspace using output folder name.
    arcpy.env.workspace = workspace
    arcpy.env.overwriteOutputs = True

    # Initialize file gdb management for temp and output folders
    temp_file_name = 'temp_{}_{}.gdb'.format(date, time)
    out_file_name = 'output_{}_{}.gdb'.format(date, time)

    arcpy.CreateFileGDB_management(workspace, temp_file_name)

    arcpy.CreateFileGDB_management(workspace, out_file_name)

    return (temp_file_name, out_file_name, workspace)


def fasterJoin(fc, fcField, joinFC, joinFCField, fields, fieldsNewNames=None, convertCodes=False):
    """Custom function for joining feature class data sets, originally written by Marshall
    
    Arguments:
        fc {feature class} -- feature class to be updated
        fcField {string} -- feature class field for identifying related records in joinFC
        joinFC {feature class} -- feature class to join
        joinFCField {string} -- feature class field for identifying related records in fc
        fields {list} -- list of fields to add to fc from joinFC
    
    Keyword Arguments:
        fieldsNewNames {list} -- list of new names for fields being added (default: {None})
        convertCodes {bool} -- flag for converting codes to float values, required for some 
            operations (default: {False})
    """

    # Create joinList, which is a list of [name, type] for input fields
    listfields = arcpy.ListFields(joinFC)
    joinList = [[k.name, k.type] for k in listfields if k.name in fields]

    if fieldsNewNames:
        # Replace original names with new names in joinList and append old ones to list
        for name, typ in joinList:
            i = fields.index(name)
            joinList[joinList.index([name, typ])][0] = fieldsNewNames[i]
    else:
        fieldsNewNames = fields

    # As Field object types and AddField types have different names (shrug),
    # map object types to AddField types
    for name, typ in joinList:
        i = joinList.index([name, typ])
        if typ == 'Integer':
            joinList[i] = [name, 'LONG']
        elif typ == 'SmallInteger':
            joinList[i] = [name, 'SHORT']
        elif typ == 'String':
            joinList[i] = [name, 'TEXT']
        elif typ == 'Single':
            joinList[i] = [name, 'FLOAT']
        elif typ == 'Double':
            joinList[i] = [name, 'DOUBLE']

    # Add fields with associated names
    for name, typ in joinList:
        arcpy.AddField_management(fc, name, typ)

    joinDict = {}
    for f in fields:
        joinDict[f] = {}

    sFields = (joinFCField, ) + fields
    with arcpy.da.SearchCursor(joinFC, sFields) as cursor:
        for row in cursor:
            for f in fields:
                if convertCodes:
                    joinDict[f][float(row[0])] = row[fields.index(f) + 1]
                else:
                    joinDict[f][row[0]] = row[fields.index(f) + 1]

    uFields = (fcField, ) + fieldsNewNames
    with arcpy.da.UpdateCursor(fc, uFields) as cursor:
        for row in cursor:
            for f in fields:
                row[fields.index(f) + 1] = joinDict[f].get(row[0], None)
            cursor.updateRow(row)


def elimSmallPolys(fc, outName, clusTol):
    """Runs Eliminate on all features in fc with area less than clusTol.
        This merges all small features to larger adjacent features.
    
    Arguments:
        fc {feature class} -- feature class to run operation over
        outName {feature class} -- reference to feature class
        clusTol {float} -- custer tolerance for specifying minimum shape area
    
    Returns:
        feature class -- reference to feature class that has had eliminate management run
    """

    lyr = arcpy.MakeFeatureLayer_management(fc)
    arcpy.SelectLayerByAttribute_management(
        lyr, "NEW_SELECTION", '"Shape_Area" < ' + str(clusTol))
    out = arcpy.Eliminate_management(lyr, outName, 'LENGTH')
    arcpy.Delete_management(lyr)
    return out


def rasterAvgs(INT, dem, rname, wname):
    """Uses arcpy Spatial Analysis package to calculate raster averages
    
    Arguments:
        INT {feature layer} -- intersected feature layer
        dem {raster layer} -- slope or precipitation raster layer
        rname {string} -- 'slope' or 'precipitation', prepended to watershed name
        wname {string} -- watershed name
    """

    arcpy.CheckOutExtension('Spatial')
    zstatdem = arcpy.sa.ZonalStatisticsAsTable(
        INT, 'uID', dem, rname + "_" + wname, "DATA", "MEAN")
    meanField = rname + "_mean"
    fasterJoin(INT, 'uID', zstatdem, 'uID', ("MEAN",), (meanField,))
    sel = arcpy.MakeFeatureLayer_management(
        INT, "omit_"+rname+"_"+wname, '"{0}" IS NULL'.format(meanField))
    if getCountInt(sel) > 0:
        selpt = arcpy.FeatureToPoint_management(
            sel, "omit_"+rname+"_centroid_"+wname)
        selex = arcpy.sa.ExtractValuesToPoints(
            selpt, dem, "omit_"+rname+"_val_"+wname)
        arcpy.AddJoin_management(sel, 'uID', selex, 'uID')
        meanFieldJ = wname + "." + meanField
        rastervaluJ = "omit_"+rname+"_val_"+wname + ".RASTERVALU"
        arcpy.CalculateField_management(
            sel, meanFieldJ, '['+rastervaluJ+']', 'VB')
    arcpy.Delete_management(sel)
    arcpy.CheckInExtension('Spatial')


def getCountInt(fc):
    """Returns number of rows within feature class
    
    Arguments:
        fc {feature class} -- feature class to obtain row count
    
    Returns:
        int -- number of rows within feature class
    """

    return int(arcpy.GetCount_management(fc).getOutput(0))


def calculateCode(slpValue, geolValue, luValue, geolName):
    """Calculates code for each unique land unit, used in runoff coeff lookup table
    
    Arguments:
        slpValue {string} -- slope bin value
        geolValue {string} -- geologic bin value (e.g. soils bin value)
        luValue {float} -- land use lookup value
        geolName {string} -- field name for geologic values (e.g. soil)
    
    Returns:
        float -- numeric code represneting combination of slope, geologic, and lookup values
    """


    geolValues = {'A': 10, 'B': 20, 'C': 30, 'D': 40,
                  'ROCK': 50, 'UNCLASS': 60, 'WATER': 70}

    if geolValue in geolValues:
        geolValueOut = geolValues[geolValue]
    else:
        geolValueOut = 0
    if not slpValue:
        slpValue = 0
    if not luValue:
        luValue = 0.0

    return slpValue + geolValueOut + luValue


def format_time(t):
    """Date formatting for arcpy message output
    
    Arguments:
        t {time} -- time to format
    
    Returns:
        string -- fomatted time for display within arcpy console output
    """

    return str(datetime.timedelta(seconds=round(time.clock() - t)))


def get_code_to_coeff_lookup(config):
    """Obtain code to coefficient dictionary
    
    Arguments:
        config {instance} -- ConfigParser instance containing RWSM parameters
    
    Returns:
        dictionary -- dictionary for converting codes to coefficients.
    """


    # Output data structure
    code_to_coeff_lookup = {}

    # Load values from config
    runoff_coeff_file_name = config.get("RWSM", "runoff_coeff_file_name")
    runoff_coeff_slope_bin_field = config.get(
        "RWSM", "runoff_coeff_slope_bin_field")
    runoff_coeff_field = config.get("RWSM", "runoff_coeff_field")
    runoff_coeff_soil_type_field = config.get(
        "RWSM", "runoff_coeff_soil_type_field")
    runoff_coeff_land_use_class_code_field = config.get(
        "RWSM", "runoff_coeff_land_use_class_code_field")

    # Specify soil values, only remaining hard-coded references
    soil_type_values = {'A': 10, 'B': 20, 'C': 30, 'D': 40,
                        'ROCK': 50, 'UNCLASS': 60, 'WATER': 70, 'null': 0}

    # Obtain dictionary mapping slope bins observed in runoff file with codes
    slope_bins = load_slope_bins(config=config, get_dict=True)
    slope_bins_w_codes = {}
    slope_bin_code = 100
    for slope_bin in slope_bins.keys():
        slope_bins_w_codes[slope_bin] = slope_bin_code
        slope_bin_code += 100

    with open(runoff_coeff_file_name, 'rb') as csvfile:
        reader = csv.reader(csvfile)
        headers = next(reader, None)

        # Get indicies
        slope_bin_idx = headers.index(runoff_coeff_slope_bin_field)
        coeff_idx = headers.index(runoff_coeff_field)
        soil_type_idx = headers.index(runoff_coeff_soil_type_field)
        land_use_class_code_idx = headers.index(
            runoff_coeff_land_use_class_code_field)

        for row in reader:
            slope_bin_val = row[slope_bin_idx]
            coeff_val = float(row[coeff_idx])
            soil_type = row[soil_type_idx]
            land_use_class_code = float(row[land_use_class_code_idx])

            # Get code for slope bin, convert string and lookup in structure
            slope_bin_code = slope_bins_w_codes[slope_bin_val]

            soil_type_code = soil_type_values[soil_type]
            code = slope_bin_code + soil_type_code + land_use_class_code
            code_to_coeff_lookup[code] = coeff_val

    return code_to_coeff_lookup
