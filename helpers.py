import os, sys, csv, ConfigParser, arcpy, arcinfo, datetime, logging

LOG_LEVEL = logging.DEBUG  # Only show debug and up
# LOG_LEVEL = logging.NOTSET # Show all messages
# LOG_LEVEL = logging.CRITICAL # Only show critical messages

def strip_chars( watershed_name, strip_set ):
    """Strips illegal characters from watershed name"""
    watershed_name_tmp = ''.join( watershed_name.split() )
    for char in strip_set:
        watershed_name_tmp = watershed_name_tmp.replace(char, '')
    return watershed_name_tmp


def get_logger( logger_level ):
    logging.basicConfig( level = logger_level )
    logger = logging.getLogger(__name__)
    return logger

# TODO: Allow function to accept slope raster OR file name
def load_slope_bins( runoff_coeff_file_name, slope_file_name ):
    """Populate slope bin lookup structure."""
    slope_bins_strs = []
    slope_bins = []
    slope_raster = arcpy.sa.Raster( slope_file_name )
    slope_raster_max = int(slope_raster.maximum)

    # Gather unique slope bin values
    with open( runoff_coeff_file_name, 'rb' ) as csvfile:
        reader = csv.reader( csvfile )
        next(reader, None)  # skip the headers
        for row in reader:
            slope = row[1]
            if slope not in slope_bins_strs:
                slope_bins_strs.append( slope )

    # Convert strings to numeric values
    for slope_bin in slope_bins_strs:
        if "+" in slope_bin:
            slope_bins.append( [int(slope_bin.strip("+").strip("%")), slope_raster_max] )
        else:
            slope_bins.append( map(lambda x: int(x), slope_bin.strip("%").split("-")) )
        
    return slope_bins

def load_land_use_table(config):
    """Load unique sets of land use codes, land use descriptions, and classifications"""

    # Gather relevant parameter values
    file_name = config.get("RWSM","land_use_LU_file_name")
    code_field = config.get("RWSM","land_use_field")
    description_field = config.get("RWSM","land_use_LU_desc_field")
    classification_field = config.get("RWSM","land_use_LU_class_field")

    # Populate values structure with unique triples
    values = []
    with open( file_name, 'rb') as csvfile:
        reader = csv.reader( csvfile )
        headers = reader.next()
        code_idx = headers.index( code_field )
        description_idx = headers.index( description_field )
        classification_idx = headers.index( classification_field )

        for row in reader:
            code = row[ code_idx ]
            description = row[ description_idx ]
            classification = row[ classification_idx ]
            if ( code, description, classification ) not in values:
                values.append( ( code, description, classification ) )
    
    return values


# TODO: Check if we want to dynamically apply coefficient fields based on location category
def load_runoff_coeff_lu( file_name, coefficient_field ):
    """Helper function for populating land use data structure"""

    # Initialize data structure, dictionary with three valued tuples
    runoff_lu = {
        "sets" : {},
        "codes" : {}
    }

    # Read and loop through CSV, populate structure
    with open( file_name, 'rb' ) as csvfile:
        reader = csv.reader( csvfile )
        headers = reader.next()
        coeff_index = headers.index( coefficient_field )
        for row in reader:
            slope = row[1]
            soil = row[2]
            category = row[3]
            code = row[7]
            coeff = row[ coeff_index ]
            runoff_set = ( slope, soil, category )
            if runoff_set not in runoff_lu["sets"].keys():
                runoff_lu["sets"][runoff_set] = coeff
            runoff_lu["codes"][code] = coeff
    return runoff_lu

# Read parameter values from configuration file
def load_config( file_name ):
    config = ConfigParser.ConfigParser()
    config.readfp( open( file_name ) )
    return config

# Write configuration file using user supplied values
def write_config( file_name, params ):
    config = ConfigParser.RawConfigParser()

    config.add_section( "RWSM" )

    for param in params:
        config.set( "RWSM", param.name, param.valueAsText)

def load_csv( file_name ):
    with open( file_name, "r") as csv_file:
        reader = csv.reader( csv_file, delimiter = "," )
        return list( reader )

def unique_field_values( file_name, field_name):
    return true

def init_workspace( workspace ):
    """Initialize workspace for writing temporary and output files."""

    # Initialize logger for output.
    logger = get_logger( LOG_LEVEL )

    # TODO: Read from configuration file.
    create_new_folder = True

    # Get date and time for folder names.
    date = str(datetime.datetime.today())[:10].replace('-', '')
    time = str(datetime.datetime.today())[11:19].replace(':', '')

    # If create_new_folder flagged, append workspace folder path.
    if create_new_folder:
        workspace += '_{}_{}'.format( date, time)
        if not os.path.exists(workspace):
            logger.info( "Creating RWSM temp and output directory in workspace '{}'...".format(workspace) )
            os.makedirs( workspace )

    # Initiate workspace using output folder name.
    arcpy.env.workspace = workspace
    arcpy.env.overwriteOutputs = True
    
    # Initialize file gdb management for temp and output folders
    temp_file_name = 'temp_{}_{}.gdb'.format(date, time)
    out_file_name = 'output_{}_{}.gdb'.format(date,time)

    logger.info( 'Creating {}...'.format( temp_file_name ) )
    arcpy.CreateFileGDB_management( workspace, temp_file_name )
    logger.info( '{} created!'.format( temp_file_name ) )
    
    logger.info( 'Creating {}'.format( out_file_name ) )
    arcpy.CreateFileGDB_management( workspace, out_file_name )
    logger.info( '{} created!'.format( out_file_name ) )

    return (temp_file_name,out_file_name,workspace)



def fasterJoin(fc, fcField, joinFC, joinFCField, fields, fieldsNewNames=None, convertCodes=False):
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

def get_unique_field_vals(file_name,field):
    """Get unique values for field in shapefile"""
    values = [row[0] for row in arcpy.da.SearchCursor(file_name, (field))]
    unique_values = list(set(values))

    return unique_values

def compare_unique_field_vals(file_name1,field1,file_name2,field2):
    """Display intersection and difference for two sets"""
    set_1 = get_unique_field_vals(file_name1,field1)
    set_2 = get_unique_field_vals(file_name2,field2)

    print "{} intersected with {}".format(file_name1,file_name2)
    set_intersection = set(set_1).intersection(set_2)
    for val in set_intersection:
        print val
    print "------------------------"
    print "Total: {}\n\n".format(len(set_intersection))

    print "{} - {}".format(file_name1,file_name2)
    set_difference = set(set_1).difference(set_2)
    for val in set_difference:
        print val
    print "------------------------"
    print "Total: {}\n\n".format(len(set_difference))

def add_descriptions_to_land_use_shp(lu_file_name,lu_field,shp_file_name):
    """Function for adding land use description field to shape file."""
    
    # Read in lookup table, create dictionary
    land_use_LU = {}
    with open(lu_file_name,'rb') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if row[3] not in land_use_LU.keys():
                land_use_LU[ row[3] ] = row[4]

    # create UpdateCursor instance, append lookup desscription as l_use_desc field based on l_use_code value found.
    arcpy.AddField_management(shp_file_name, "l_use_desc", "TEXT")
    with arcpy.da.UpdateCursor(shp_file_name, ["l_use_code","l_use_desc"]) as cursor:
        for row in cursor:
            row[1] = land_use_LU[str(row[0])]
            # print row
            
            # Add try / catch to identify which rows are not updated.

            # cursor.updateRow(row)

def elimSmallPolys(fc, outName, clusTol):
    """Runs Eliminate on all features in fc with area less than clusTol.
    This merges all small features to larger adjacent features."""
    lyr = arcpy.MakeFeatureLayer_management(fc)
    arcpy.SelectLayerByAttribute_management(lyr, "NEW_SELECTION", '"Shape_Area" < ' + str(clusTol))
    out = arcpy.Eliminate_management(lyr, outName, 'LENGTH')
    arcpy.Delete_management(lyr)
    return out

def rasterAvgs(INT, dem, rname, wname):
    arcpy.CheckOutExtension('Spatial')
    #zstatdem = ZonalStatisticsAsTable(INT, 'uID', dem, rname + "_" + wname, "TRUE", "MEAN")
    zstatdem = arcpy.sa.ZonalStatisticsAsTable(INT, 'uID', dem, rname + "_" + wname, "DATA", "MEAN")
    meanField = rname + "_mean"
    fasterJoin(INT, 'uID', zstatdem, 'uID', ("MEAN",), (meanField,))
    sel = arcpy.MakeFeatureLayer_management(INT, "omit_"+rname+"_"+wname, '"{0}" IS NULL'.format(meanField))
    if getCountInt(sel) > 0:
        selpt = arcpy.FeatureToPoint_management(sel, "omit_"+rname+"_centroid_"+wname)
        selex = arcpy.sa.ExtractValuesToPoints(selpt, dem, "omit_"+rname+"_val_"+wname)
        arcpy.AddJoin_management(sel, 'uID', selex, 'uID')
        meanFieldJ = wname + "." + meanField
        rastervaluJ = "omit_"+rname+"_val_"+wname + ".RASTERVALU"
        arcpy.CalculateField_management(sel, meanFieldJ, '['+rastervaluJ+']', 'VB')
    arcpy.Delete_management(sel)
    arcpy.CheckInExtension('Spatial')

def getCountInt(fc):
    return int(arcpy.GetCount_management(fc).getOutput(0))

# TODO: This will be phased out once land use lookups are indexed by tuples
def calculateCode(slpValue, geolValue, luValue, geolName):
    """Calculates code for each unique land unit, used in runoff coeff lookup table"""
    if geolName == 'geol':
        geolValues = {'Franciscan': 10, 'Great Valley': 20, 'Quaternary': 30, 'Salinian': 40, 'Tertiary': 50, 'Water': 60}
    elif geolName == 'soils':
        geolValues = {'A': 10, 'B': 20, 'C': 30, 'D': 40, 'ROCK': 50, 'UNCLASS': 60, 'WATER': 70}
    if geolValue in geolValues:
        geolValueOut = geolValues[geolValue]
    else:
        geolValueOut = 0
    if not slpValue:
        slpValue = 0
    if not luValue:
        luValue = 0.0
    #else:
        #luValue = float(str(luValue)[0] + '.' + str(luValue)[1:])  # convert luValue to decimal with highest digit as ones place
    return slpValue + geolValueOut + luValue