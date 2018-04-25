#!/usr/bin/env python

"""rwsm.py: Primary RWSM (Beta) analysis code."""

__copyright__ = "Copyright 2017, San Francisco Estuary Institute"

import os
import sys
import csv
import helpers
import arcpy
import datetime
import time
import logging
import numpy
import gc

# Log levels are for debugging the application via Python command line,
# which is outside the scope of this initial beta release.
# LOG_LEVEL = logging.DEBUG  # Only show debug and up
# LOG_LEVEL = logging.NOTSET # Show all messages
# LOG_LEVEL = logging.CRITICAL # Only show critical messages


class Watersheds(object):
    """Used to manage set of initial watersheds
    
    Arguments:
        object {object} -- Remenant of python 2.7, declares new-style class
    
    Returns:
        Watersheds -- Instance of watersheds class
    """


    def __init__(self, config):
        """Class initialization
        
        Arguments:
            config {instance} -- ConfigParser instance containing parameter values.
        """

        self.is_dissolved = False
        self.config = config
        # self.file_name = config.get("RWSM", "watersheds_calibration")
        self.file_name = config.get("RWSM", "watersheds")
        self.field = config.get("RWSM", "watersheds_field")
        self.watershed_names = []

    def dissolve(self):
        """Dissolve if necessary, otherwise return pre-dissolved watersheds
        
        Returns:
            Feature Layer -- Dissolved feature layer
        """

        if not self.is_dissolved:
            self.dissolved = arcpy.Dissolve_management(
                in_features=self.file_name,
                out_feature_class="disWS",
                dissolve_field=self.field,
                multi_part="SINGLE_PART"
            )
            self.is_dissolved = True

        return self.dissolved

    def get_names(self):
        """Obtain set of watershed names from dissolved watershed feature class.
        
        Returns:
            list -- sorted list of watershed names
        """

        if len(self.watershed_names) == 0:
            watersheds_field = self.config.get("RWSM", "watersheds_field")
            fc_table = arcpy.da.FeatureClassToNumPyArray(
                in_table=self.file_name,
                field_names=[watersheds_field]
            )
            watershed_names = sorted(numpy.unique(
                fc_table[:][watersheds_field]).tolist())
            self.watershed_names = map(lambda x: helpers.strip_chars(
                x, '!@#$%^&*()-+=,<>?/\~`[]{}.'), watershed_names)

        return self.watershed_names


class Stats_Writer(object):
    """Object for writing watershed statistics tables
    
    Arguments:
        object {object} -- Remenant of python 2.7, declares new-style class
    
    Returns:
        Stats_Writer -- Stats_Writer instance
    """


    def __init__(self, config, watershed_names, slope_bins):
        """Class initialization function
        
        Arguments:
            config {instance} -- ConfigParser instance
            watershed_names {list} -- list of watershed names
            slope_bins {list} -- list containing slope bins
        """

        self.config = config
        self.slope_bins = self.slope_bins_to_strs(sorted(slope_bins))
        self.ws_stats = []
        self.lu_stats = []
        self.watershed_names = watershed_names
        self.load_soil_and_land_use_values(config)
        self.init_lu_stats(watershed_names)
        self.ws_headers = self.get_ws_stats_headers()
        self.lu_headers = self.get_lu_stats_headers()

    def init_lu_stats(self, watershed_names):
        """Initializes land use statistics data structure
        
        Arguments:
            watershed_names {list} -- sorted list of watershed names
        """


        # Write headers to stats list
        header = []
        header.append('Land Use Code')
        header.append('Land Use Description')
        header.append('Land Use Classification')
        for watershed_name in self.watershed_names:
            header.append(watershed_name)
        self.lu_stats.append(header)

        # Populate stats table with unique code, description, and class sets as well as empty values.
        self.land_use_values = helpers.load_land_use_table(self.config)
        for (code, description, classification) in self.land_use_values:
            lu_row = []
            lu_row.append(int(code))
            lu_row.append(description)
            lu_row.append(classification)
            lu_row = lu_row + [""] * len(self.watershed_names)
            self.lu_stats.append(lu_row)

    def slope_bins_to_strs(self, slope_bins):
        """Converts slope bin ranges into printable strings
        
        Arguments:
            slope_bins {list} -- slope bins
        
        Returns:
            list -- list of strings representing slope bins
        """

        tmp = []
        for slope_bin in slope_bins:
            tmp.append(str(slope_bin[0]) + "-" + str(slope_bin[1]))
        return tmp

    def load_soil_and_land_use_values(self, config):
        """Read in runoff coefficient table, generate list of values and headers for watershed stats.
        
        Arguments:
            config {instance} -- ConfigParser instance holding parameters
        """

        soil_types = []
        land_use_classes = []

        with open(self.config.get("RWSM", "runoff_coeff_file_name"), 'rb') as csvfile:
            reader = csv.reader(csvfile)
            rc_headers = reader.next()

            # Gather indecies
            soil_idx = rc_headers.index(self.config.get(
                "RWSM", "runoff_coeff_soil_type_field"))
            land_use_idx = rc_headers.index(self.config.get(
                "RWSM", "runoff_coeff_land_use_class_field"))

            # Iterate through csv file, collect soil and land use values
            for row in reader:
                soil_type = row[soil_idx]
                land_use_class = row[land_use_idx]

                if soil_type not in soil_types:
                    soil_types.append(soil_type)

                if land_use_class not in land_use_classes:
                    land_use_classes.append(land_use_class)

        self.soil_types = sorted(soil_types)
        self.land_use_classes = sorted(land_use_classes)

    def get_ws_stats_headers(self):
        """Header row for watershed statistics file
        
        Returns:
            list -- list of headers for writing to statistics CSV file
        """

        ws_headers = []
        ws_headers.append("Watershed")
        ws_headers.append("Tot. Area (km2)")
        ws_headers.append("Tot. Runoff Vol. (m3)")
        ws_headers.append("Tot. Runoff Vol. (10^6 m3)")
        ws_headers.append("Average Weighted Precipitation (mm)")
        ws_headers.append("Average Weighted Slope (%)")

        for slope_bin in self.slope_bins:
            ws_headers.append("Slope Bin " + slope_bin + " % Tot.")

        for soil_type in self.soil_types:
            ws_headers.append("Soil Type " + soil_type + " % Tot.")

        for land_use in self.land_use_classes:
            ws_headers.append("LU " + land_use + " Tot. Area (km2)")

        for land_use in self.land_use_classes:
            ws_headers.append("LU " + land_use + " Runoff Vol. (m3)")

        for land_use in self.land_use_classes:
            ws_headers.append("LU " + land_use + " % WS Area")

        for land_use in self.land_use_classes:
            ws_headers.append("LU " + land_use + " % WS Runoff Vol. (m3)")

        return ws_headers

    def get_lu_stats_headers(self):
        """Headers for land use statistics file.
        
        Returns:
            list -- list of headersf or writing to land use statistics CSV file
        """

        lu_headers = []
        lu_headers.append("Land Use Code")
        lu_headers.append("Land Use Description")
        lu_headers.append("Land Use Classification")
        for watershed_name in self.watershed_names:
            lu_headers.append(watershed_name)
        return lu_headers

    def add_fc_table(self, watershed):
        """Add feature class data to values data structure
        
        Arguments:
            watershed {String} -- feature class for watershed
        """


        # Watershed Stats Table ---------------------------------------------------
        intersect = watershed
        watershed_name = os.path.split(str(watershed))[1]

        # List to be written as a rows in watershed statistics table output
        ws_row = []

        # Watershed Name
        ws_row.append(watershed_name)

        # Tot. Area (km2)
        fc_table = arcpy.da.FeatureClassToNumPyArray(
            in_table=intersect,
            field_names='SHAPE@AREA'
        )
        total_area = numpy.sum(fc_table["SHAPE@AREA"])
        ws_row.append(total_area / 10**6)

        # Tot. Runoff Vol. (m3)
        runoff_vol_field = 'runoff_vol_' + \
            self.config.get("RWSM", "runoff_coeff_field")
        fc_table = arcpy.da.FeatureClassToNumPyArray(
            in_table=intersect,
            field_names=runoff_vol_field
        )
        tot_runoff_vol = numpy.sum(fc_table[runoff_vol_field])
        ws_row.append(tot_runoff_vol)

        # Tot. Runoff Vol. (10^6 m3)
        ws_row.append(tot_runoff_vol / 10**6)

        # Average Weighted Precipitation (mm)
        fc_table = arcpy.da.FeatureClassToNumPyArray(
            in_table=intersect,
            field_names=["precipitation_mean", "SHAPE@AREA"]
        )
        ws_row.append(numpy.sum(
            fc_table["precipitation_mean"] * fc_table["SHAPE@AREA"]) / total_area)

        # Average Weighted Slope (%)
        fc_table = arcpy.da.FeatureClassToNumPyArray(
            in_table=intersect,
            field_names=["slope_mean", "SHAPE@AREA"]
        )
        ws_row.append(
            numpy.sum(fc_table["slope_mean"] * fc_table["SHAPE@AREA"]) / total_area)

        # Slope Bin Percent (%) Totals
        slope_bin_field = self.config.get("RWSM", "slope_bin_field")
        fc_table = arcpy.da.FeatureClassToNumPyArray(
            in_table=intersect,
            field_names=[slope_bin_field, "SHAPE@AREA"]
        )
        for slope_bin in self.slope_bins:
            ws_row.append(numpy.sum(
                fc_table[fc_table[slope_bin_field] == slope_bin]["SHAPE@AREA"]) / total_area)

        # Soil Type Percent (%) Totals
        soils_type_field = self.config.get("RWSM", "soils_bin_field")
        fc_table = arcpy.da.FeatureClassToNumPyArray(
            in_table=intersect,
            field_names=[soils_type_field, "SHAPE@AREA"]
        )
        for soil_type in self.soil_types:
            ws_row.append(numpy.sum(
                fc_table[fc_table[soils_type_field] == soil_type]["SHAPE@AREA"]) / total_area)

        # Land Use - Total areas (km2)
        land_use_LU_class_field = self.config.get(
            "RWSM", "land_use_LU_class_field")
        fc_table = arcpy.da.FeatureClassToNumPyArray(
            in_table=intersect,
            field_names=[land_use_LU_class_field, "SHAPE@AREA"]
        )
        for land_use_class in self.land_use_classes:
            ws_row.append(numpy.sum(
                fc_table[fc_table[land_use_LU_class_field] == land_use_class]["SHAPE@AREA"]) / 10**6)

        # Land Use - Runoff Vol. (m3)
        fc_table = arcpy.da.FeatureClassToNumPyArray(
            in_table=intersect,
            field_names=[land_use_LU_class_field, runoff_vol_field]
        )
        for land_use_class in self.land_use_classes:
            ws_row.append(numpy.sum(
                fc_table[fc_table[land_use_LU_class_field] == land_use_class][runoff_vol_field]))

        # Land Use - Percent (%) WS Area
        fc_table = arcpy.da.FeatureClassToNumPyArray(
            in_table=intersect,
            field_names=[land_use_LU_class_field, "SHAPE@AREA"]
        )
        for land_use_class in self.land_use_classes:
            ws_row.append(numpy.sum(
                fc_table[fc_table[land_use_LU_class_field] == land_use_class]["SHAPE@AREA"]) / total_area)

        # Land Use - Percent (%) WS Runoff Vol. (m3)
        fc_table = arcpy.da.FeatureClassToNumPyArray(
            in_table=intersect,
            field_names=[land_use_LU_class_field, runoff_vol_field]
        )
        for land_use_class in self.land_use_classes:
            ws_row.append(numpy.sum(
                fc_table[fc_table[land_use_LU_class_field] == land_use_class][runoff_vol_field]) / tot_runoff_vol)

        self.ws_stats.append(ws_row)

        # Land Use Stats Table ----------------------------------------------------
        land_use_LU_code_field = self.config.get(
            "RWSM", "land_use_LU_code_field")
        fc_table = arcpy.da.FeatureClassToNumPyArray(
            in_table=intersect,
            field_names=[land_use_LU_code_field, "SHAPE@AREA"]
        )
        watershed_idx = self.lu_stats[0].index(watershed_name)
        for row in self.lu_stats[1:]:
            code = row[0]
            percent_area = numpy.sum(
                fc_table[fc_table[land_use_LU_code_field] == code]["SHAPE@AREA"]) / total_area
            if percent_area > 0:
                row[watershed_idx] = percent_area

        del fc_table

    def write_ws_stats_table(self, output_file_name):
        """Write area, runoff, soil, slope, and land use statistics for each watershed
        
        Arguments:
            output_file_name {String} -- File name for writing watershed statistics information as CSV
        """

        with open(output_file_name, "wb") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(self.ws_headers)
            for row in self.ws_stats:
                writer.writerow(row)

    def write_lu_stats_table(self, output_file_name):
        """Writes land use area percentages for each land use class / watershed combination
        
        Arguments:
            output_file_name {String} -- File name for writing land use statistics information as CSV
        """

        with open(output_file_name, "wb") as csvfile:
            writer = csv.writer(csvfile)
            for row in self.lu_stats:
                writer.writerow(row)

    def write_stats_tables(intersected_watersheds):
        """Given a list of tuples containing watershed names and refereces, outputs stats tables
        
        Arguments:
            intersected_watersheds {list} -- list of intersected watersheds 
        """

        intersected_watersheds.append((watershed_name, intersect))
        for (watershed_name, intersect) in intersected_watersheds:
            writer.add_fc_table(watershed_name, intersect)


def run_analysis(config=None, is_gui=False):
    """Primary RWSM analysis loop
    
    Keyword Arguments:
        config {instance} -- ConfigParser instance holding parameter values (default: {None})
        is_gui {bool} -- indicates if running from ArcMap toolbox GUI (default: {False})
    """


    # Logger used for command line debugging, not supported in beta.
    # logger = helpers.get_logger(LOG_LEVEL)
    # logger.info('Starting analysis...')

    # Initialize structures for user output.
    start_time = time.clock()
    if is_gui:
        arcpy.SetProgressor("default", "Initiating workspace...")

    # Load values from config file
    if not config:
        CONFIG_FILE_NAME = "rwsm.ini"
        if os.path.isfile(CONFIG_FILE_NAME):
            config = helpers.load_config(CONFIG_FILE_NAME)
    workspace = config.get("RWSM", "workspace")
    workspace = os.path.join(workspace, "rwsm")
    watersheds_file_name = config.get("RWSM", "watersheds")
    watersheds_field = config.get("RWSM", "watersheds_field")

    # Create workspace
    (temp_file_name, out_file_name, workspace) = helpers.init_workspace(workspace)

    # Instantiate watershed, run dissolve
    if is_gui:
        arcpy.SetProgressor("default", "Dissolving watersheds...")

    watersheds = Watersheds(config)
    dissolved_watersheds = watersheds.dissolve()

    # Change to temporary workspace
    arcpy.env.workspace = temp_file_name

    # Set aside tracking data structures
    land_use_descriptions = []

    # Gather configuration file values --------------------------------------------

    # Land Use (Shapefile)
    land_use_file_name = config.get("RWSM", "land_use")
    land_use_field = config.get("RWSM", "land_use_field")
    land_use_LU_code_field = config.get("RWSM", "land_use_LU_code_field")
    land_use_LU_bin_field = config.get("RWSM", "land_use_LU_bin_field")
    land_use_LU_desc_field = config.get("RWSM", "land_use_LU_desc_field")
    land_use_LU_class_field = config.get("RWSM", "land_use_LU_class_field")
    land_use_LU_file_name = config.get("RWSM", "land_use_LU_file_name")

    # Soils (Shapefile)
    soils_file_name = config.get("RWSM", "soils_file_name")
    soils_field = config.get("RWSM", "soils_field")
    soils_bin_field = config.get("RWSM", "soils_bin_field")

    # Slope (Raster)
    slope_file_name = config.get("RWSM", "slope_file_name")
    slope_bin_field = config.get("RWSM", "slope_bin_field")

    # precipitation (Raster)
    precipitation_file_name = config.get("RWSM", "precipitation_file_name")

    # Run-off Coefficient (CSV or Table)
    runoff_coeff_file_name = config.get("RWSM", "runoff_coeff_file_name")
    runoff_coeff_field = config.get("RWSM", "runoff_coeff_field")

    # Populate Slope Bins data structure ------------------------------------------
    if is_gui:
        arcpy.SetProgressor("default", "Computing slope bins...")

    slope_raster = arcpy.sa.Raster(slope_file_name)
    slope_bins = helpers.load_slope_bins(config)
    slope_bins_w_codes = helpers.load_slope_bins(config)
    map(lambda x: x.append((slope_bins_w_codes.index(x) + 1) * 100), slope_bins_w_codes)

    # Get precipitation raster ----------------------------------------------------
    if is_gui:
        arcpy.SetProgressor("default", "Importing precipitation raster...")
    precipitation_raster = arcpy.sa.Raster(precipitation_file_name)

    # Set aside structure for holding intersected watershed references ------------
    intersected_watersheds = []

    # Setup statistics output object ----------------------------------------------
    if is_gui:
        arcpy.SetProgressor("default", "Initiating statistics writer...")
    writer = Stats_Writer(config, watersheds.get_names(), slope_bins)

    # Initialize data structures for updating progressor label
    if is_gui:
        n_watersheds = len(watersheds.get_names())
        cnt = 1

    # List of tuples for holding error information
    watershed_errors = []

    # Load code to coefficient lookup table
    codes_to_coeff_lookup = helpers.get_code_to_coeff_lookup(config)

    # Iterate through watersheds, run precipitation clip analysis -----------------
    with arcpy.da.SearchCursor(dissolved_watersheds, (watersheds_field, "SHAPE@")) as cursor:
        for watershed in cursor:
            try:
                # Prepare watershed data ----------------------------------------------
                watershed_name = watershed[0]
                watershed_val = watershed[1]

                if is_gui:
                    msg = "Analysing {}, watershed {} of {}...".format(
                        watershed_name, cnt, n_watersheds)
                    arcpy.SetProgressor("step", msg, 0, n_watersheds, cnt)

                # Remove illegal characters from watershed name
                watershed_name = helpers.strip_chars(
                    watershed_name, '!@#$%^&*()-+=,<>?/\~`[]{}.')

                # Land Use Operations -------------------------------------------------
                arcpy.Clip_analysis(
                    in_features=land_use_file_name,
                    clip_features=watershed_val,
                    out_feature_class="lu_" + watershed_name
                )
                if is_gui:
                    msg = "{}: land use clip analysis complete: {}".format(
                        watershed_name, helpers.format_time(start_time))
                    arcpy.AddMessage(msg)

                # Adds land use lookup bin and description
                helpers.fasterJoin(
                    fc="lu_" + watershed_name,
                    fcField=land_use_field,
                    joinFC=land_use_LU_file_name,
                    joinFCField=land_use_LU_code_field,
                    fields=(
                        land_use_LU_bin_field,
                        land_use_LU_desc_field,
                        land_use_LU_class_field
                    )
                )

                # Dissolve land use
                land_use_clip = arcpy.Dissolve_management(
                    in_features="lu_" + watershed_name,
                    out_feature_class="luD_" + watershed_name,
                    dissolve_field=[
                        land_use_field,
                        land_use_LU_desc_field,
                        land_use_LU_bin_field,
                        land_use_LU_class_field
                    ],
                    statistics_fields="",
                    multi_part="SINGLE_PART"
                )
                if is_gui:
                    msg = "{}: land use dissolve complete: {}".format(
                        watershed_name, helpers.format_time(start_time))
                    arcpy.AddMessage(msg)

                # Check size of land use area, stop analysis if no data found.
                if int(arcpy.GetCount_management(land_use_clip).getOutput(0)) > 0:
                    if is_gui:
                        msg = "{}: Land use clip and dissolve has data, continuing analysis...".format(
                            watershed_name)
                        arcpy.AddMessage(msg)
                else:
                    if is_gui:
                        msg = "{}: Land use clip and dissolve yielded no data, skipping watershed...".format(
                            watershed_name)
                        arcpy.AddMessage(msg)
                    break

                # Clip soils
                arcpy.Clip_analysis(
                    in_features=soils_file_name,
                    clip_features=watershed_val,
                    out_feature_class="soils_" + watershed_name
                )
                if is_gui:
                    msg = "{}: soil clip analysis complete: {}".format(
                        watershed_name, helpers.format_time(start_time))
                    arcpy.AddMessage(msg)

                soils_clip = arcpy.Dissolve_management(
                    in_features="soils_" + watershed_name,
                    out_feature_class="soilsD_" + watershed_name,
                    dissolve_field=soils_field,
                    statistics_fields="",
                    multi_part="SINGLE_PART"
                )
                if is_gui:
                    msg = "{}: soils dissolve analysis complete: {}".format(
                        watershed_name, helpers.format_time(start_time))
                    arcpy.AddMessage(msg)

                if int(arcpy.GetCount_management(soils_clip).getOutput(0)) > 0:
                    if is_gui:
                        msg = "{}: Soils clip and dissolve contains data, continuing analysis...".format(
                            watershed_name)
                        arcpy.AddMessage(msg)
                else:
                    if is_gui:
                        msg = "{}: Soils clip and dissolve yielded no rows, skipping watershed...".format(
                            watershed_name)
                        arcpy.AddMessage(msg)
                    break

                # Intersect Land Use and Soils ----------------------------------------
                intersect_land_use_and_soils = arcpy.Intersect_analysis(
                    in_features=[land_use_clip, soils_clip],
                    out_feature_class="int_" + watershed_name,
                    join_attributes="NO_FID"
                )
                if is_gui:
                    msg = "{}: land use and soils intersect complete: {}".format(
                        watershed_name, helpers.format_time(start_time))
                    arcpy.AddMessage(msg)

                intersect_land_use_and_soils_singles = arcpy.MultipartToSinglepart_management(
                    in_features=intersect_land_use_and_soils,
                    out_feature_class="intX_" + watershed_name
                )
                if is_gui:
                    msg = "{}: Multipart to single part complete: {}".format(
                        watershed_name, helpers.format_time(start_time))
                    arcpy.AddMessage(msg)

                intersect = helpers.elimSmallPolys(
                    fc=intersect_land_use_and_soils_singles,
                    outName=os.path.join(
                        workspace, out_file_name, watershed_name),
                    clusTol=0.005
                )
                if is_gui:
                    msg = "{}: elimSmallPolys: {}".format(
                        watershed_name, helpers.format_time(start_time))
                    arcpy.AddMessage(msg)

                # Add unique ID field -------------------------------------------------
                arcpy.AddField_management(
                    in_table=intersect,
                    field_name='uID',
                    field_type='LONG'
                )
                with arcpy.da.UpdateCursor(intersect, ('OID@', 'uID')) as cursor:
                    for row in cursor:
                        row[1] = row[0]
                        cursor.updateRow(row)
                if is_gui:
                    msg = "{}: uID field added: {}".format(
                        watershed_name, helpers.format_time(start_time))
                    arcpy.AddMessage(msg)

                # Add Slope bin field -------------------------------------------------
                helpers.rasterAvgs(intersect, slope_raster,
                                   'slope', watershed_name)
                arcpy.AddField_management(intersect, slope_bin_field, "TEXT")
                if is_gui:
                    msg = "{}: slope bin field added: {}".format(
                        watershed_name, helpers.format_time(start_time))
                    arcpy.AddMessage(msg)

                # Precipitation -------------------------------------------------------
                helpers.rasterAvgs(intersect, precipitation_raster,
                                   'precipitation', watershed_name)
                if is_gui:
                    msg = "{}: Precipitation added: {}".format(
                        watershed_name, helpers.format_time(start_time))
                    arcpy.AddMessage(msg)

                # Add soils, land use, and slope fields -------------------------------
                arcpy.AddField_management(intersect, "watershed", "TEXT")
                arcpy.AddField_management(intersect, soils_bin_field, "TEXT")
                arcpy.AddField_management(intersect, "land_use", "LONG")
                with arcpy.da.UpdateCursor(intersect, ("watershed", soils_bin_field, soils_field, "land_use", land_use_field, slope_bin_field, 'slope_mean')) as cursor:
                    for row in cursor:
                        # Shift columns
                        row[0] = watershed_name
                        row[1] = row[2]
                        row[3] = row[4]

                        # Add slope bin to feature data
                        slope_bin = filter(
                            lambda x: x[0] <= row[6] < x[1], slope_bins)
                        if len(slope_bin) > 0:
                            slope_bin = str(slope_bin[0]).strip(
                                '[').strip(']').replace(', ', '-')
                        else:
                            slope_bin = "NaN"
                        row[5] = slope_bin

                        cursor.updateRow(row)
                if is_gui:
                    msg = "{}: soils, land use, and slope fields added: {}".format(
                        watershed_name, helpers.format_time(start_time))
                    arcpy.AddMessage(msg)

                # Add land use code fields ---------------------------------------------
                code_field = 'code_' + land_use_LU_bin_field
                base_field = 'runoff_vol_' + runoff_coeff_field
                arcpy.AddField_management(intersect, code_field, "DOUBLE")
                arcpy.AddField_management(intersect, base_field, "DOUBLE")
                if is_gui:
                    msg = "{}: land use code and runoff volume fields added: {}".format(
                        watershed_name, helpers.format_time(start_time))
                    arcpy.AddMessage(msg)

                # Write in values for new fields --------------------------------------
                with arcpy.da.UpdateCursor(intersect, (soils_bin_field, land_use_LU_bin_field, slope_bin_field, code_field)) as cursor:
                    for row in cursor:
                        # arcpy.AddMessage("{},{},{},{}".format(row[0],row[1],row[2],row[3]))
                        # TODO: Identify why NaNs exist
                        slpBin1 = int(row[2].split('-')[0]
                                      ) if row[2] != 'NaN' else 0
                        slpBinVal = [k[2]
                                     for k in slope_bins_w_codes if k[0] == slpBin1][0]
                        row[3] = helpers.calculateCode(
                            slpBinVal, row[0], float(row[1]), soils_bin_field)
                        cursor.updateRow(row)
                if is_gui:
                    msg = "{}: land use codes added: {}".format(
                        watershed_name, helpers.format_time(start_time))
                    arcpy.AddMessage(msg)

                # Join runoff coeff lookup table and calculate runoff volume
                arcpy.AddField_management(
                    intersect, runoff_coeff_field, "Double")
                with arcpy.da.UpdateCursor(intersect, (runoff_coeff_field, code_field)) as cursor:
                    for row in cursor:
                        row[0] = codes_to_coeff_lookup[row[1]]
                        cursor.updateRow(row)
                if is_gui:
                    msg = "{}: output fields added: {}".format(
                        watershed_name, helpers.format_time(start_time))
                    arcpy.AddMessage(msg)

                # Convert precipitation from mm to m and multiple by runoff vol.
                with arcpy.da.UpdateCursor(
                    in_table=intersect,
                    field_names=['SHAPE@AREA', runoff_coeff_field,
                                 base_field, 'precipitation_mean'],
                    where_clause='"{0}" is not null'.format(runoff_coeff_field)
                ) as cursor:
                    for row in cursor:
                        # convert ppt from mm to m and multiply by area and runoff coeff
                        row[2] = (row[3] / 1000.0) * row[0] * row[1]
                        cursor.updateRow(row)
                if is_gui:
                    msg = "{}: precipitation converted: {}".format(
                        watershed_name, helpers.format_time(start_time))
                    arcpy.AddMessage(msg)

                # Update statistics writer --------------------------------------------
                writer.add_fc_table(os.path.join(
                    workspace, out_file_name, watershed_name))
                if is_gui:
                    msg = "{}: statistics computed: {}\n".format(
                        watershed_name, helpers.format_time(start_time))
                    arcpy.AddMessage(msg)

                # Increment count -----------------------------------------------------
                cnt += 1

            except Exception as error:
                if is_gui:
                    msg = "{}: Error computing analysis: {}".format(
                        watershed_name, error)
                    arcpy.AddMessage(msg)
                watershed_errors.append((watershed_name, error))
                continue

    # Write stats to csv files and watersheds with errors
    writer.write_ws_stats_table(os.path.join(workspace, "results_wsStats.csv"))
    writer.write_lu_stats_table(os.path.join(workspace, "results_luStats.csv"))
    if is_gui:
        msg = "Analysis complete: {}".format(helpers.format_time(start_time))
        arcpy.AddMessage(msg)
        if len(watershed_errors) > 0:
            msg = "Errors encountered while computing analysis for the following watersheds:"
            arcpy.AddMessage(msg)
            for (watershed_name, error) in watershed_errors:
                arcpy.AddMessage(watershed_name)
        else:
            msg = "There were no errors during the analysis"
            arcpy.AddMessage(msg)
