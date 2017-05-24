import os, sys, csv, helpers, arcpy, datetime, logging, numpy, gc

LOG_LEVEL = logging.DEBUG  # Only show debug and up
# LOG_LEVEL = logging.NOTSET # Show all messages
# LOG_LEVEL = logging.CRITICAL # Only show critical messages

class Watersheds(object):

    def __init__( self, config):
        self.is_dissolved = False
        self.config = config
        self.file_name = config.get("RWSM", "watersheds_calibration")
        self.field = config.get("RWSM", "watersheds_field")
        self.watershed_names = []
    
    # Check if dissolved, return dissolved watershed if so
    def dissolve( self ):
        if not self.is_dissolved:
            self.dissolved = arcpy.Dissolve_management(
                in_features = self.file_name, 
                out_feature_class = self.field+"_dissolved", #TODO: Change to 'disWS'
                dissolve_field = self.field, 
                multi_part = "SINGLE_PART"
            )
            self.is_dissolved = True
        
        return self.dissolved

    def get_names( self ):
        """Obtain set of watershed names from dissolved watershed feature class."""
        if len( self.watershed_names ) == 0:
            watersheds_field = self.config.get("RWSM","watersheds_field")
            fc_table = arcpy.da.FeatureClassToNumPyArray(
                in_table = self.file_name, 
                field_names = [ watersheds_field ]
            )
            watershed_names = sorted( numpy.unique( fc_table[:][watersheds_field] ).tolist() )
            self.watershed_names = map( lambda x: helpers.strip_chars( x, '!@#$%^&*()-+=,<>?/\~`[]{}.' ), watershed_names )

        return self.watershed_names

class Stats_Writer(object):
    """Object for writing watershed statistics tables"""

    def __init__( self, config, watershed_names, slope_bins ):
        self.config = config
        self.slope_bins = self.slope_bins_to_strs( sorted(slope_bins) )
        self.ws_stats = []
        self.lu_stats = []
        self.watershed_names = watershed_names
        self.load_soil_and_land_use_values( config )
        self.init_lu_stats( watershed_names )
        self.ws_headers = self.get_ws_stats_headers()
        self.lu_headers = self.get_lu_stats_headers()
        # print self.lu_stats
        
    def init_lu_stats( self, watershed_names ):
        """Initializes land use statistics data structure"""
        
        # Write headers to stats list
        header = []
        header.append( 'Land Use Code' )
        header.append( 'Land Use Description' )
        header.append( 'Land Use Classification' )
        for watershed_name in self.watershed_names:
            header.append( watershed_name )    
        self.lu_stats.append( header )

        # Populate stats table with unique code, description, and class sets as well as empty values.
        self.land_use_values = helpers.load_land_use_table( self.config )
        for ( code, description, classification ) in self.land_use_values:
            lu_row = []
            lu_row.append( int(code) )
            lu_row.append( description )
            lu_row.append( classification )
            lu_row = lu_row + [""] * len( self.watershed_names )
            self.lu_stats.append( lu_row )
    
    def slope_bins_to_strs( self, slope_bins ):
        tmp = []
        for slope_bin in slope_bins:
            tmp.append( str( slope_bin[0] ) + "-" + str( slope_bin[1] ) )
        return tmp

    def load_soil_and_land_use_values( self, config ):
        """Read in runoff coefficient table, generate list of values and headers for watershed stats."""
        soil_types = []
        land_use_classes = []

        with open( self.config.get("RWSM","runoff_coeff_file_name"), 'rb' ) as csvfile:
            reader = csv.reader( csvfile )
            rc_headers = reader.next()

            # Gather indecies
            # TODO: Load string values from config file
            soil_idx = rc_headers.index('Soil')
            land_use_idx = rc_headers.index('LU')

            # Iterate through csv file, collect soil and land use values
            for row in reader:
                soil_type = row[ soil_idx ]
                land_use_class = row[ land_use_idx ]

                if soil_type not in soil_types:
                    soil_types.append( soil_type )
                
                if land_use_class not in land_use_classes:
                    land_use_classes.append( land_use_class )
        
        self.soil_types = sorted(soil_types)
        self.land_use_classes = sorted(land_use_classes)

    def get_ws_stats_headers( self ):
        """Header row for watershed statistics file"""
        ws_headers = []
        ws_headers.append( "Watershed" )
        ws_headers.append( "Tot. Area (km2)" )
        ws_headers.append( "Tot. Runoff Vol. (m3)" )
        ws_headers.append( "Tot. Runoff Vol. (10^6 m3)" )
        ws_headers.append( "Average Weighted Precipitation (mm)" )
        ws_headers.append( "Average Weighted Slope (%)" )

        for slope_bin in self.slope_bins:
            ws_headers.append( "Slope Bin " + slope_bin + " % Tot." )

        for soil_type in self.soil_types:
            ws_headers.append( "Soil Type " + soil_type + " % Tot." )
        
        for land_use in self.land_use_classes:
            ws_headers.append( "LU " + land_use + " Tot. Area (km2)" )

        for land_use in self.land_use_classes:
            ws_headers.append( "LU " + land_use + " Runoff Vol. (m3)" )

        for land_use in self.land_use_classes:
            ws_headers.append( "LU " + land_use + " % WS Area" )

        for land_use in self.land_use_classes:
            ws_headers.append( "LU " + land_use + " % WS Runoff Vol. (m3)" )

        return ws_headers

    def get_lu_stats_headers( self ):
        """Headers for land use statistics file."""
        lu_headers = []
        lu_headers.append( "Land Use Code" )
        lu_headers.append( "Land Use Description" )
        lu_headers.append( "Land Use Classification" )
        for watershed_name in self.watershed_names:
            lu_headers.append( watershed_name )
        return lu_headers
        
    def add_fc_table(self, watershed ):
        """Add feature class data to values data structure"""

        # Watershed Stats Table ---------------------------------------------------
        intersect = watershed
        # print str(watershed)
        watershed_name = os.path.split(str(watershed))[1]

        # List to be written as a row in watershed statistics data
        ws_row = []

        # Watershed Name
        ws_row.append( watershed_name )

        # Tot. Area (km2)
        fc_table = arcpy.da.FeatureClassToNumPyArray( 
            in_table = intersect, 
            field_names = 'SHAPE@AREA'
        )
        total_area = numpy.sum( fc_table[ "SHAPE@AREA" ] )
        ws_row.append( total_area )

        # Tot. Runoff Vol. (m3)
        runoff_vol_field = 'runoff_vol_' + self.config.get("RWSM","runoff_coeff_field")
        fc_table = arcpy.da.FeatureClassToNumPyArray( 
            in_table = intersect, 
            field_names = runoff_vol_field
        )
        tot_runoff_vol = numpy.sum( fc_table[ runoff_vol_field ] )
        ws_row.append( tot_runoff_vol )

        # Tot. Runoff Vol. (10^6 m3)
        ws_row.append( tot_runoff_vol / 10**6 )
        

        # Average Weighted Precipitation (mm)
        fc_table = arcpy.da.FeatureClassToNumPyArray( 
            in_table = intersect, 
            field_names = [ "precipitation_mean", "SHAPE@AREA" ]
        )
        ws_row.append( numpy.sum( fc_table[ "precipitation_mean" ] * fc_table[ "SHAPE@AREA" ] ) / total_area )

        # Average Weighted Slope (%)
        # TODO: Verify this computation
        fc_table = arcpy.da.FeatureClassToNumPyArray( 
            in_table = intersect, 
            field_names = [ "slope_mean", "SHAPE@AREA" ]
        )
        ws_row.append( numpy.sum( fc_table[ "slope_mean" ] * fc_table[ "SHAPE@AREA" ] ) / total_area )

        # Slope Bin Percent (%) Totals
        slope_bin_field = self.config.get("RWSM","slope_bin_field")
        fc_table = arcpy.da.FeatureClassToNumPyArray( 
            in_table = intersect, 
            field_names = [ slope_bin_field, "SHAPE@AREA" ]
        )
        for slope_bin in self.slope_bins:
            ws_row.append( numpy.sum( fc_table[ fc_table[ slope_bin_field ] == slope_bin ][ "SHAPE@AREA" ] ) / total_area )

        # Soil Type Percent (%) Totals
        soils_type_field = self.config.get("RWSM","soils_bin_field")
        fc_table = arcpy.da.FeatureClassToNumPyArray( 
            in_table = intersect, 
            field_names = [ soils_type_field, "SHAPE@AREA" ]
        )
        for soil_type in self.soil_types:
            ws_row.append( numpy.sum( fc_table[ fc_table[ soils_type_field ] == soil_type ][ "SHAPE@AREA" ] ) / total_area )

        # Land Use - Total areas (km2)
        land_use_LU_class_field = self.config.get("RWSM","land_use_LU_class_field")
        fc_table = arcpy.da.FeatureClassToNumPyArray( 
            in_table = intersect, 
            field_names = [ land_use_LU_class_field, "SHAPE@AREA" ]
        )
        for land_use_class in self.land_use_classes:
            ws_row.append( numpy.sum( fc_table[ fc_table[ land_use_LU_class_field ] == land_use_class ][ "SHAPE@AREA" ] ) )

        # Land Use - Runoff Vol. (m3)
        fc_table = arcpy.da.FeatureClassToNumPyArray( 
            in_table = intersect, 
            field_names = [ land_use_LU_class_field, runoff_vol_field ]
        )
        for land_use_class in self.land_use_classes:
            ws_row.append( numpy.sum( fc_table[ fc_table[ land_use_LU_class_field ] == land_use_class ][ runoff_vol_field ] ) )

        # Land Use - Percent (%) WS Area
        fc_table = arcpy.da.FeatureClassToNumPyArray( 
            in_table = intersect, 
            field_names = [ land_use_LU_class_field, "SHAPE@AREA" ]
        )
        for land_use_class in self.land_use_classes:
            ws_row.append( numpy.sum( fc_table[ fc_table[ land_use_LU_class_field ] == land_use_class ][ "SHAPE@AREA" ] ) / total_area )

        # Land Use - Percent (%) WS Runoff Vol. (m3)
        fc_table = arcpy.da.FeatureClassToNumPyArray( 
            in_table = intersect, 
            field_names = [ land_use_LU_class_field, runoff_vol_field ]
        )
        for land_use_class in self.land_use_classes:
            ws_row.append( numpy.sum( fc_table[ fc_table[ land_use_LU_class_field ] == land_use_class ][ runoff_vol_field ] ) / tot_runoff_vol )

        self.ws_stats.append( ws_row )

        # Land Use Stats Table ----------------------------------------------------
        # Update land use stats list
        land_use_LU_code_field = self.config.get("RWSM","land_use_LU_code_field")
        fc_table = arcpy.da.FeatureClassToNumPyArray( 
            in_table = intersect, 
            field_names = [ land_use_LU_code_field, "SHAPE@AREA" ]
        )
        watershed_idx = self.lu_stats[0].index( watershed_name )
        for row in self.lu_stats[1:]:
            code = row[0]
            # print numpy.sum( fc_table[ fc_table[ land_use_LU_code_field ] == code ][ "SHAPE@AREA" ] )
            percent_area = numpy.sum( fc_table[ fc_table[ land_use_LU_code_field ] == code ][ "SHAPE@AREA" ] ) / total_area
            if percent_area > 0: row[ watershed_idx ] = percent_area

        del fc_table

    def write_ws_stats_table( self, output_file_name ):
        with open( output_file_name, "wb" ) as csvfile:
            writer = csv.writer( csvfile )
            writer.writerow( self.ws_headers )
            for row in self.ws_stats:
                writer.writerow( row )
    
    def write_lu_stats_table( self, output_file_name ):
        with open( output_file_name, "wb" ) as csvfile:
            writer = csv.writer( csvfile )
            for row in self.lu_stats:
                writer.writerow( row )

    def write_stats_tables( intersected_watersheds ):
        """Given a list of tuples containing watershed names and refereces, outputs stats tables"""
        intersected_watersheds.append( ( watershed_name, intersect ) )
        for ( watershed_name, intersect ) in intersected_watersheds:
            writer.add_fc_table(watershed_name, intersect)

def get_analysis_statistics( ):
    """Assumes analysis has already been run, generate statistics for intersected shapefiles"""

    # Initialize logger for output.
    logger = helpers.get_logger( LOG_LEVEL )

    # Load values from config file
    CONFIG_FILE_NAME = "rwsm.ini"
    if os.path.isfile( CONFIG_FILE_NAME ):
        config = helpers.load_config( CONFIG_FILE_NAME )
    workspace = config.get("RWSM", "workspace")
    # workspace = os.path.join(workspace,"rwsm")
    output_folder = config.get("RWSM", "output_folder")
    
    arcpy.env.workspace = os.path.join(workspace,output_folder)

    watersheds_file_name = config.get("RWSM", "watersheds_calibration")
    watersheds_field = config.get("RWSM", "watersheds_field")
    watersheds = Watersheds( config )
    watershed_names = watersheds.get_names()

    runoff_coeff_file_name = config.get("RWSM","runoff_coeff_file_name")
    slope_file_name = config.get("RWSM","slope_file_name")
    slope_bins = helpers.load_slope_bins( runoff_coeff_file_name, slope_file_name )
    
    writer = Stats_Writer( config, watershed_names, slope_bins )
    for watershed in sorted( arcpy.ListFeatureClasses('','All') ):
        writer.add_fc_table(watershed)

    # Switch back to results folder
    arcpy.env.workspace = os.path.join(workspace)

    # Write stats to csv files  
    writer.write_ws_stats_table( os.path.join( workspace, "results_wsStats.csv" ) )
    writer.write_lu_stats_table( os.path.join( workspace, "results_luStats.csv" ) )

def run_analysis( params = None ):
    """Test land use clip analysis."""

    # Initialize logger for output.
    logger = helpers.get_logger( LOG_LEVEL )

    # Load config if no params datastructure present
    if params:
        workspace = params['workspace']
        watersheds = params['watersheds']
        watersheds_field = params['watersheds_field']
        land_use = params['land_use']
        land_use_field = params['land_use_field']
        land_use_LU_file_name = params['land_use_LU_file_name']
        land_use_LU_code_field = params['land_use_LU_code_field']
        land_use_LU_bin_field = params['land_use_LU_bin_field']
        land_use_LU_desc_field = params['land_use_LU_desc_field']
        land_use_LU_class_field = params['land_use_LU_class_field']
        runoff_coeff_file_name = params['runoff_coeff_file_name']
        runoff_coeff_field = params['runoff_coeff_field']
        runoff_coeff_slope_bin_field = params['runoff_coeff_slope_bin_field']
        runoff_coeff_soil_type_field = params['runoff_coeff_soil_type_field']
        runoff_coeff_land_use_class_field = params['runoff_coeff_land_use_class_field']
        slope_file_name = params['slope_file_name']
        slope_bin_field = params['slope_bin_field']
        soils_file_name = params['soils_file_name']
        soils_field = params['soils_field']
        soils_bin_field = params['soils_bin_field']
        precipitation_file_name = params['precipitation_file_name']
        out_name = params['out_name']
        delete_temp = params['delete_temp']
        overwrite_config = params['overwrite_config']
    else:
        # Load values from config file
        CONFIG_FILE_NAME = "rwsm.ini"
        if os.path.isfile( CONFIG_FILE_NAME ):
            config = helpers.load_config( CONFIG_FILE_NAME )
        workspace = config.get("RWSM", "workspace")
        # workspace = os.path.join(workspace,"rwsm")
        watersheds_file_name = config.get("RWSM", "watersheds")
        # watersheds_file_name = config.get("RWSM", "watersheds_calibration")
        watersheds_field = config.get("RWSM", "watersheds_field")
        land_use = config.get("RWSM", "land_use")
        land_use_field = config.get("RWSM", "land_use_field")
        land_use_LU_file_name = config.get("RWSM", "land_use_LU_file_name")
        land_use_LU_code_field = config.get("RWSM", "land_use_LU_code_field")
        land_use_LU_bin_field = config.get("RWSM", "land_use_LU_bin_field")
        land_use_LU_desc_field = config.get("RWSM", "land_use_LU_desc_field")
        land_use_LU_class_field = config.get("RWSM", "land_use_LU_class_field")
        runoff_coeff_file_name = config.get("RWSM", "runoff_coeff_file_name")
        runoff_coeff_field = config.get("RWSM", "runoff_coeff_field")
        runoff_coeff_slope_bin_field = config.get("RWSM", "runoff_coeff_slope_bin_field")
        runoff_coeff_soil_type_field = config.get("RWSM", "runoff_coeff_soil_type_field")
        runoff_coeff_land_use_class_field = config.get("RWSM", "runoff_coeff_land_use_class_field")
        slope_file_name = config.get("RWSM", "slope_file_name")
        slope_bin_field = config.get("RWSM", "slope_bin_field")
        soils_file_name = config.get("RWSM", "soils_file_name")
        soils_field = config.get("RWSM", "soils_field")
        soils_bin_field = config.get("RWSM", "soils_bin_field")
        precipitation_file_name = config.get("RWSM", "precipitation_file_name")
        out_name = config.get("RWSM", "out_name")
        delete_temp = config.get("RWSM", "delete_temp")
        overwrite_config = config.get("RWSM", "overwrite_config")

    # Create workspace
    ( temp_file_name, out_file_name, workspace ) = helpers.init_workspace( workspace )

    # Instantiate watershed, run dissolve
    logger.info( 'Dissolving watershed...' )
    watersheds = Watersheds( config )
    dissolved_watersheds = watersheds.dissolve()
    logger.info( 'watershed dissolved!' )

    # Change to temporary workspace
    arcpy.env.workspace = temp_file_name

    # Set aside tracking data structures
    land_use_descriptions = []

    # Gather configuration file values --------------------------------------------
    # Land Use (Shapefile)
    land_use_file_name = config.get("RWSM", "land_use")
    land_use_field = config.get("RWSM","land_use_field")
    # land_use_LU = config.get("RWSM","land_use_LU")
    land_use_LU_code_field = config.get("RWSM","land_use_LU_code_field")
    land_use_LU_bin_field = config.get("RWSM","land_use_LU_bin_field")
    land_use_LU_desc_field = config.get("RWSM","land_use_LU_desc_field")
    land_use_LU_class_field = config.get("RWSM","land_use_LU_class_field")
    land_use_LU_file_name = config.get("RWSM","land_use_LU")

    # Soils (Shapefile)
    soils_file_name = config.get("RWSM","soils_file_name")
    soils_field = config.get("RWSM","soils_field")
    soils_bin_field = config.get("RWSM","soils_bin_field")

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
    slope_bins_w_codes = helpers.load_slope_bins( runoff_coeff_file_name, slope_file_name )
    map(lambda x: x.append( ( slope_bins_w_codes.index(x) + 1 ) * 100 ), slope_bins_w_codes )
    logger.info( "Slope Bins: {}".format( slope_bins ) )
    logger.info( "Slope Bins w/ Codes: {}".format( slope_bins_w_codes ) )

    # Get precipitation raster
    precipitation_raster = arcpy.sa.Raster( precipitation_file_name )

    # Set aside structure for holding intersected watershed references ------------
    intersected_watersheds = []

    # Setup statistics output object ----------------------------------------------
    # writer = Stats_Writer( config, dissolved_watersheds, slope_bins )
    writer = Stats_Writer( config, watersheds.get_names(), slope_bins )


    # Iterate through watersheds, run precipitation clip analysis
    #------------------------------------------------------------------------------
    values = {}
    logger.info( 'Iterating watersheds...')
    fc_table = "" # Attempt to minimize memory usage
    cnt = 1
    with arcpy.da.SearchCursor( dissolved_watersheds, (watersheds_field, "SHAPE@") ) as cursor:
        for watershed in cursor:
            if 0 < cnt < 16:
                # Prepare watershed data ----------------------------------------------
                watershed_name = watershed[0]
                watershed_val = watershed[1]

                logger.info('')
                logger.info('Running analysis for watershed {}...'.format(watershed_name))
                logger.info('cnt {}...'.format(cnt))

                # Remove illegal characters from watershed name
                watershed_name = helpers.strip_chars( watershed_name, '!@#$%^&*()-+=,<>?/\~`[]{}.' )
                
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
                    joinFC = land_use_LU_file_name, # lookupLU TODO: Testing csv file, was land_use_LU before.
                    joinFCField = land_use_LU_code_field, # lookupLUcode_field
                    fields = ( # fields
                        land_use_LU_bin_field, # lookupLUbinField
                        land_use_LU_desc_field, # lookupLUdescField
                        land_use_LU_class_field
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
                        land_use_LU_bin_field,
                        land_use_LU_class_field
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
                logger.info('Converting multiparts to single parts...')
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
                with arcpy.da.UpdateCursor(intersect, (soils_bin_field, land_use_LU_bin_field, slope_bin_field, code_field)) as cursor:
                    for row in cursor:
                        slpBin1 = int(row[2].split('-')[0]) if row[2] != 'NaN' else 0 # TODO: Identify why NaNs exist
                        slpBinVal = [k[2] for k in slope_bins_w_codes if k[0] == slpBin1][0]
                        row[3] = helpers.calculateCode(slpBinVal, row[0], row[1], soils_bin_field)
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
                with arcpy.da.UpdateCursor(
                    in_table = intersect, 
                    field_names = ['SHAPE@AREA', runoff_coeff_field, base_field, 'precipitation_mean'],
                    where_clause = '"{0}" is not null'.format(runoff_coeff_field)
                ) as cursor:
                    for row in cursor:
                        # convert ppt from mm to m and multiply by area and runoff coeff
                        row[2] = (row[3] / 1000.0) * row[0] * row[1]
                        cursor.updateRow(row)
                logger.info('...precipitation converted!')

                # Add to intersected watersheds list
                # intersected_watersheds.append( ( watershed_name, intersect ) )
                
                # Gather area statistics ----------------------------------------------
                writer.add_fc_table( os.path.join( workspace, out_file_name, watershed_name ) )
                
                # logger.info( "FC Table successfully created for watershed {}!\n\n".format( watershed_name ) )

                # gc.collect()

                cnt += 1
            else:
                logger.info("")
                logger.info("Skipping {}...".format(watershed[0]))
                logger.info("")
                cnt += 1

    # Write stats to csv files
    writer.write_ws_stats_table( os.path.join( workspace, "results_wsStats.csv" ) )
    writer.write_lu_stats_table( os.path.join( workspace, "results_luStats.csv" ) )
