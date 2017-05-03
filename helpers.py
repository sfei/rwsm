import os, sys, csv, ConfigParser, arcpy, datetime, logging

LOG_LEVEL = logging.DEBUG  # Only show debug and up
# LOG_LEVEL = logging.NOTSET # Show all messages
# LOG_LEVEL = logging.CRITICAL # Only show critical messages

def get_logger( logger_level ):
    logging.basicConfig( level = logger_level )
    logger = logging.getLogger(__name__)
    return logger

def load_ruoff_coeff_lu( file_name ):
    return 0

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
            logger.info( "Creating RWSM workspace directory {}...".format(workspace) )
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

    return (temp_file_name,out_file_name)



def fasterJoin(fc, fcField, joinFC, joinFCField, fields, fieldsNewNames=None):
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
                joinDict[f][row[0]] = row[fields.index(f) + 1]

    uFields = (fcField, ) + fieldsNewNames
    with arcpy.da.UpdateCursor(fc, uFields) as cursor:
        for row in cursor:
            for f in fields:
                row[fields.index(f) + 1] = joinDict[f].get(row[0], None)
            cursor.updateRow(row)