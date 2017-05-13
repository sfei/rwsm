import os, sys, helpers, arcpy, datetime, logging, numpy

LOG_LEVEL = logging.DEBUG  # Only show debug and up
# LOG_LEVEL = logging.NOTSET # Show all messages
# LOG_LEVEL = logging.CRITICAL # Only show critical messages

class Watershed(object):

    def __init__(self,file_name,field):
        self.is_dissolved = False
        self.file_name = file_name
        self.field = field
    
    # Check if dissolved, return dissolved watershed if so
    def dissolve(self):
        if not self.is_dissolved:
            self.dissolved = arcpy.Dissolve_management(
                in_features = self.file_name, 
                out_feature_class = self.field+"_dissolved",
                dissolve_field = self.field, 
                multi_part = "SINGLE_PART"
            )
            self.is_dissolved = True
        
        return self.dissolved

class Land_Use(object):
    def __init__(self,file_name,field):
        self.file_name = file_name,
        self.field = field

    def create_lookup(self):
        return True


def clip_land_use():
    return true

def clip_soils():
    return true

def run_analysis():
    """Test land use clip analysis."""

    # Initialize logger for output.
    logger = helpers.get_logger( LOG_LEVEL )

    # Load values from config file
    CONFIG_FILE_NAME = "rwsm.ini"
    if os.path.isfile( CONFIG_FILE_NAME ):
        config = helpers.load_config( CONFIG_FILE_NAME )
    workspace = config.get("RWSM", "workspace")
    workspace = os.path.join(workspace,"rwsm")
    # watersheds_file_name = config.get("RWSM", "watersheds")
    watersheds_file_name = config.get("RWSM", "watersheds_calibration")
    watersheds_field = config.get("RWSM", "watersheds_field")
    land_use_file_name = config.get("RWSM", "land_use")

    # Create workspace
    ( temp_file_name, out_file_name, workspace ) = helpers.init_workspace( workspace )

    # Instantiate watershed, run dissolve
    logger.info( 'Dissolving watershed...' )
    watersheds = Watershed( watersheds_file_name, watersheds_field )
    dissolved_watersheds = watersheds.dissolve()
    logger.info( 'watershed dissolved!' )

    # Change to temporary workspace
    arcpy.env.workspace = temp_file_name

    # Set aside tracking data structures
    land_use_descriptions = []

    # Gather configuration file values --------------------------------------------
    # Land Use (Raster)
    land_use_field = config.get("RWSM","land_use_field")
    land_use_LU = config.get("RWSM","land_use_LU")
    land_use_LU_code_field = config.get("RWSM","land_use_LU_code_field")
    land_use_LU_bin_field = config.get("RWSM","land_use_LU_bin_field")
    land_use_LU_desc_field = config.get("RWSM","land_use_LU_desc_field")

    # Soils (Shapefile)
    soils_file_name = config.get("RWSM","soils_file_name")
    soils_field = config.get("RWSM","soils_field")

    # Slope (Raster)
    slope_file_name = config.get("RWSM","slope_file_name")
    slope_bin_field = config.get("RWSM","slope_bin_field")

    # precipitation (Raster)
    precipitation_file_name = config.get("RWSM", "precipitation_file_name")

    # Run-off Coefficient (CSV or Table)
    runoff_coeff_file_name = config.get("RWSM","runoff_coeff_file_name")
    runoff_coeff_field = config.get("RWSM","runoff_coeff_field")

    # Populate Slope Bins data structure ------------------------------------------
    # TODO: Allow helpers.load_slope_bins to accept raster too.
    slope_raster = arcpy.sa.Raster( slope_file_name )
    slope_bins = helpers.load_slope_bins( runoff_coeff_file_name, slope_file_name )

    # Get precipitation raster
    precipitation_raster = arcpy.sa.Raster( precipitation_file_name )


    # Iterate through watersheds, run precipitation clip analysis
    #------------------------------------------------------------------------------
    values = {}
    logger.info( 'Iterating watersheds...')
    with arcpy.da.SearchCursor( dissolved_watersheds, (watersheds_field, "SHAPE@") ) as cursor:
        for watershed in cursor:
            
            # Prepare watershed data ----------------------------------------------
            watershed_name = watershed[0]
            watershed_val = watershed[1]

            logger.info('')
            logger.info('Running analysis for watershed {}...'.format(watershed_name))

            # Remove illegal characters from watershed name
            # TODO: verify this is necessary
            watershed_name_tmp = ''.join( watershed_name.split() )
            for char in '!@#$%^&*()-+=,<>?/\~`[]{}.':
                watershed_name_tmp = watershed_name_tmp.replace(char, '')
            watershed_name = watershed_name_tmp
            
            # Land Use Operations -------------------------------------------------
            logger.info('Clipping land use...')
            arcpy.Clip_analysis( 
                in_features = land_use_file_name, 
                clip_features = watershed_val, 
                out_feature_class = "lu_" + watershed_name
            )
            logger.info("Land use clipped!")

            # Adds land use lookup bin and description
            helpers.fasterJoin(
                fc = "lu_" + watershed_name,
                fcField = land_use_field, # luField
                joinFC = land_use_LU, # lookupLU
                joinFCField = land_use_LU_code_field, # lookupLUcode_field
                fields = ( # fields
                    land_use_LU_bin_field, # lookupLUbinField
                    land_use_LU_desc_field # lookupLUdescField
                )
            )

            # Dissolve land use
            logger.info('Dissolving land use...')
            land_use_clip = arcpy.Dissolve_management(
                in_features = "lu_" + watershed_name,
                out_feature_class = "luD_" + watershed_name,
                dissolve_field = [
                    land_use_field, 
                    land_use_LU_desc_field, 
                    land_use_LU_bin_field
                ], 
                statistics_fields = "", 
                multi_part = "SINGLE_PART"
            )
            logger.info("Land use dissolved!")

            # Check size of land use area
            if int(arcpy.GetCount_management(land_use_clip).getOutput(0)) > 0:
                logger.info("Land use clip and dissolve has data, continuing analysis...")
            else:
                logger.info("Land use clip and dissolve yielded no data, skipping {}".format(watershed_name))
                break

            # Iterate through dissolved land use file, gather descriptions
            logger.info('Gathering descriptions...')
            with arcpy.da.SearchCursor( land_use_clip, (land_use_field, land_use_LU_desc_field) ) as cursor:
                for row in cursor:
                    land_use_descriptions.append( [ row[0], row[1] ] )
            logger.info('...descriptions gathered!')

            # Soils ---------------------------------------------------------------
            logger.info('Clipping soils...')
            arcpy.Clip_analysis( 
                in_features = soils_file_name, 
                clip_features = watershed_val, 
                out_feature_class = "soils_" + watershed_name
            )
            logger.info('...soils clipped!')
            logger.info('Dissolving soils...')
            soils_clip = arcpy.Dissolve_management(
                in_features = "soils_" + watershed_name,  # In feature class
                out_feature_class = "soilsD_" + watershed_name, # Out feature class
                dissolve_field = soils_field,
                statistics_fields = "",
                multi_part = "SINGLE_PART"
            )
            logger.info('...soils dissolved!')
            if int(arcpy.GetCount_management(soils_clip).getOutput(0)) > 0:
                logger.info("Soils clip and dissolve contains data, continuing analysis...")
            else:
                logger.info("Soils clip and dissolve yielded no rows, skipping {}...".format(watershed_name))
                break
            
            # Intersect Land Use and Soils ----------------------------------------
            logger.info('Intersecting land use and soils...')
            intersect_land_use_and_soils = arcpy.Intersect_analysis(
                in_features = [land_use_clip, soils_clip],
                out_feature_class = "int_" + watershed_name,
                join_attributes = "NO_FID"
            )
            logger.info('...land use and soils intersected!')
            logger.info('Convering multiparts to single parts...')
            intersect_land_use_and_soils_singles = arcpy.MultipartToSinglepart_management(
                in_features = intersect_land_use_and_soils,
                out_feature_class = "intX_" + watershed_name
            )
            logger.info('...conversion complete!')
            logger.info('Eliminating small polygons, saving to output file...')
            intersect = helpers.elimSmallPolys(
                fc = intersect_land_use_and_soils_singles, 
                outName = os.path.join( workspace, out_file_name, watershed_name ), 
                clusTol = 0.005
            )
            logger.info('...small polygons eliminated!')
            # TODO: Add eliminate small polygon step
            # intersect = intersect_land_use_and_soils_singles

            logger.info( "Intersect complete for {}!".format(watershed_name) )

            # Slope ---------------------------------------------------------------
            # TODO: Add slope computations, add slope bin
            arcpy.AddField_management(
                in_table = intersect, 
                field_name = 'uID', 
                field_type = 'LONG'
            )
            with arcpy.da.UpdateCursor(intersect, ('OID@', 'uID')) as cursor:
                for row in cursor:
                    row[1] = row[0]
                    cursor.updateRow(row)

            logger.info('Computing slope raster statistics...')
            helpers.rasterAvgs(intersect, slope_raster, 'slope', watershed_name)
            arcpy.AddField_management(intersect, slope_bin_field, "TEXT")
            logger.info('Raster statistics computed!')
            
            
            # Precipitation -------------------------------------------------------
            # TODO: Add precipitation average computation
            logger.info('Computing precipitation raster statistics...')
            helpers.rasterAvgs(intersect, precipitation_raster, 'precipitation', watershed_name)
            logger.info('Raster statistics computed!')

            # Add soils, land use, and slope fields -------------------------------
            logger.info( "Adding field values...".format(watershed_name) )
            arcpy.AddField_management(intersect, "watershed", "TEXT")
            arcpy.AddField_management(intersect, "soils", "TEXT")
            arcpy.AddField_management(intersect, "land_use", "LONG")
            with arcpy.da.UpdateCursor(intersect, ("watershed","soils",soils_field,"land_use",land_use_field,slope_bin_field,'slope_mean')) as cursor:
                for row in cursor:
                    # Shift columns
                    row[0] = watershed_name
                    row[1] = row[2]
                    row[3] = row[4]
                    
                    # Add slope bin to feature data
                    slope_bin = filter(lambda x: x[0] < row[6] < x[1],slope_bins)
                    if len(slope_bin) > 0:
                        slope_bin = str(slope_bin[0]).strip('[').strip(']').replace(', ','-')
                    else:
                        # TODO: Identify what area/shape yields no slope bin
                        slope_bin = "NaN"
                    row[5] = slope_bin

                    cursor.updateRow(row)

            # Add land use code fields ---------------------------------------------
            # TODO: Update this so it doesn't use codes, but combination of slope bin, soils, and land use category
            logger.info('Adding land use fields...')
            code_field = 'code_' + land_use_LU_bin_field
            base_field = 'runoff_vol_' + runoff_coeff_field
            arcpy.AddField_management(intersect, code_field, "DOUBLE")
            arcpy.AddField_management(intersect, base_field, "DOUBLE")
            logger.info('...land use fields added!')

            # Write in values for new fields --------------------------------------
            logger.info('Adding land use code to output...')
            # TODO: Phase out slope bin codes in general
            slope_bins_w_codes = list(slope_bins)
            map(lambda x: x.append( ( slope_bins_w_codes.index(x) + 1 ) * 100 ), slope_bins_w_codes )
            with arcpy.da.UpdateCursor(intersect, ('soils', land_use_LU_bin_field, slope_bin_field, code_field)) as cursor:
                for row in cursor:
                    slpBin1 = int(row[2].split('-')[0]) if row[2] != 'NaN' else 0 # TODO: Identify why NaNs exist
                    slpBinVal = [k[2] for k in slope_bins_w_codes if k[0] == slpBin1][0]
                    row[3] = helpers.calculateCode(slpBinVal, row[0], row[1], 'soils')
                    cursor.updateRow(row)
            logger.info('...land use codes added!')

            # Join runoff coeff lookup table and calculate runoff volume
            # logger.info("\nfc: {}\nfcField: {}\njoinFC: {}\njoinFCField: {}\nfields: {}".format(intersect,code_field,runoff_coeff_file_name,'code',(runoff_coeff_field,)))
            helpers.fasterJoin(
                fc = intersect,
                fcField = code_field, 
                joinFC = runoff_coeff_file_name, 
                joinFCField = 'code', 
                fields = (runoff_coeff_field,),
                convertCodes = True # TODO: Find alternative for flagging string to float/int conversion
            )

            # Convert precipitation from mm to m and multiple by runoff vol.
            logger.info('Converting precipitation...')
            with arcpy.da.UpdateCursor(intersect, ['SHAPE@AREA', runoff_coeff_field, base_field, 'precipitation_mean'],
                                           '"{0}" is not null'.format(runoff_coeff_field)) as cursor:
                    for row in cursor:
                        # convert ppt from mm to m and multiply by area and runoff coeff
                        row[2] = (row[3] / 1000.0) * row[0] * row[1]
                        cursor.updateRow(row)
            logger.info('...precipitation converted!')

            fc_table = arcpy.da.FeatureClassToNumPyArray( intersect, ["OID@","slope_mean", base_field, land_use_LU_bin_field, 'soils',
                slope_bin_field, 'SHAPE@AREA', 'land_use', code_field, 'precipitation_mean'])
            
            values[ watershed_name ] = {}
            values[ watershed_name ][ 'weighted_slope' ] = numpy.sum( fc_table["slope_mean"] * fc_table["SHAPE@AREA"] )
            values[ watershed_name ][ 'weighted_precipitation' ] = numpy.sum( fc_table["precipitation_mean"] * fc_table["SHAPE@AREA"] )

            values[ watershed_name ][ 'land_use_bins' ] = {}
            lu_bin_values = numpy.unique( fc_table[:][land_use_LU_bin_field] )
            for lu_bin_value in lu_bin_values:
                values[ watershed_name ][ 'land_use_bins' ][ lu_bin_value ] = numpy.sum( fc_table[ fc_table[ land_use_LU_bin_field ] == lu_bin_value ]["SHAPE@AREA"] )

            values[ watershed_name ][ 'slope_bins' ] = {}
            slope_bin_values = numpy.unique( fc_table[:][slope_bin_field] )
            for slope_bin_value in slope_bin_values:
                values[ watershed_name ][ 'slope_bins' ][ slope_bin_value ] = numpy.sum( fc_table[ fc_table[ slope_bin_field ] == slope_bin_value ]["SHAPE@AREA"] )

            # values[ watershed_name ][ 'slope_bins' ] = 
            # values[ watershed_name ][ 'soils' ]
            print values
            
            logger.info('FC Table successfully created!')
