#!/usr/bin/env python

"""RWSM_Toolbox.pyt: RWSM Toolbox python template file, initializes toolbox."""

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

import os
import arcpy
import helpers
import rwsm

# Initialization file for populating toolbox GUI
LOCAL_PATH = os.path.dirname(os.path.realpath(__file__))
CONFIG_FILE_NAME = os.path.join(LOCAL_PATH, "rwsm.ini")


class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "RWSM Toolbox"
        self.alias = ""

        self.tools = [RWSM_Toolbox]


class RWSM_Toolbox(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "RWSM Hydrology Analysis"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Configure Toolbox UI fields"""

        workspace = arcpy.Parameter(
            displayName="Workspace",
            name="workspace",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")

        watersheds = arcpy.Parameter(
            displayName="Watersheds - feature class",
            name="watersheds",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")

        watersheds_field = arcpy.Parameter(
            displayName="Watershed name field (from Watersheds feature class)",
            name="watersheds_field",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        watersheds_field.parameterDependencies = [watersheds.name]

        land_use = arcpy.Parameter(
            displayName="Land use - feature class",
            name="land_use",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")

        land_use_field = arcpy.Parameter(
            displayName="Land use code field (from Land Use feature class)",
            name="land_use_field",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        land_use_field.parameterDependencies = [land_use.name]

        land_use_LU_file_name = arcpy.Parameter(
            displayName="Land use - CSV",
            name='land_use_LU_file_name',
            datatype="DETable",
            parameterType="Required",
            direction="Input")

        land_use_LU_code_field = arcpy.Parameter(
            displayName="Land use code field (from Land Use CSV)",
            name="land_use_LU_code_field",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        land_use_LU_code_field.parameterDependencies = [
            land_use_LU_file_name.name]

        land_use_LU_bin_field = arcpy.Parameter(
            displayName="Land use classification code field (from Land Use CSV)",
            name="land_use_LU_bin_field",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        land_use_LU_bin_field.parameterDependencies = [
            land_use_LU_file_name.name]

        land_use_LU_desc_field = arcpy.Parameter(
            displayName="Land use description field (from Land Use CSV)",
            name="land_use_LU_desc_field",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        land_use_LU_desc_field.parameterDependencies = [
            land_use_LU_file_name.name]

        land_use_LU_class_field = arcpy.Parameter(
            displayName="Land use classification field (from Land Use CSV)",
            name="land_use_LU_class_field",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        land_use_LU_class_field.parameterDependencies = [
            land_use_LU_file_name.name]

        runoff_coeff_file_name = arcpy.Parameter(
            displayName="Runoff coefficient - CSV",
            name='runoff_coeff_file_name',
            datatype="DETable",
            parameterType="Required",
            direction="Input")

        runoff_coeff_field = arcpy.Parameter(
            displayName="Runoff coefficient field (from Runoff Coefficient CSV)",
            name="runoff_coeff_field",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        runoff_coeff_field.parameterDependencies = [
            runoff_coeff_file_name.name]

        runoff_coeff_slope_bin_field = arcpy.Parameter(
            displayName="Slope bin field (from Runoff Coefficient CSV)",
            name="runoff_coeff_slope_bin_field",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        runoff_coeff_slope_bin_field.parameterDependencies = [
            runoff_coeff_file_name.name]

        runoff_coeff_soil_type_field = arcpy.Parameter(
            displayName="Soil type field (from Runoff Coefficient CSV)",
            name="runoff_coeff_soil_type_field",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        runoff_coeff_soil_type_field.parameterDependencies = [
            runoff_coeff_file_name.name]

        runoff_coeff_land_use_class_field = arcpy.Parameter(
            displayName="Land use classification field (from Runoff Coefficient CSV)",
            name="runoff_coeff_land_use_class_field",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        runoff_coeff_land_use_class_field.parameterDependencies = [
            runoff_coeff_file_name.name]

        runoff_coeff_land_use_class_code_field = arcpy.Parameter(
            displayName="Land use classification code field (from Runoff Coefficient CSV)",
            name="runoff_coeff_land_use_class_code_field",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        runoff_coeff_land_use_class_code_field.parameterDependencies = [
            runoff_coeff_file_name.name]

        slope_file_name = arcpy.Parameter(
            displayName="Slope - raster",
            name="slope_file_name",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input")

        # slope_bin_field = arcpy.Parameter(
        #     displayName="Slope bin field",
        #     name="slope_bin_field",
        #     datatype="GPString",
        #     parameterType="Required",
        #     direction="Input")
        # slope_bin_field.value = "slope_bin"

        soils_file_name = arcpy.Parameter(
            displayName="Soils - feature class",
            name="soils_file_name",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")

        soils_field = arcpy.Parameter(
            displayName="Soils group field (from Soils feature class)",
            name="soils_field",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        soils_field.parameterDependencies = [soils_file_name.name]

        # soils_bin_field = arcpy.Parameter(
        #     displayName="Soils bin field",
        #     name="soils_bin_field",
        #     datatype="GPString",
        #     parameterType="Required",
        #     direction="Input")
        # soils_bin_field.value = "soils_bin"

        precipitation_file_name = arcpy.Parameter(
            displayName="Precipitation - raster",
            name="precipitation_file_name",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input")

        out_name = arcpy.Parameter(
            displayName="Output file name (user defined)",
            name="out_name",
            datatype="GPString",
            parameterType="Required",
            direction="Input")

        # delete_temp = arcpy.Parameter(
        #     displayName="Delete Temp Data",
        #     name="delete_temp",
        #     datatype="GPBoolean",
        #     parameterType="Optional",
        #     direction="Input",
        #     enabled=0)
        # delete_temp.value = False

        # overwrite_config = arcpy.Parameter(
        #     displayName="Overwrite Stored Defaults",
        #     name="overwrite_config",
        #     datatype="GPBoolean",
        #     parameterType="Optional",
        #     direction="Input",
        #     enabled=0)
        # overwrite_config.value = False

        # params = [workspace, watersheds, watersheds_field, land_use, land_use_field,
        #           land_use_LU_file_name, land_use_LU_code_field, land_use_LU_bin_field, land_use_LU_desc_field, land_use_LU_class_field,
        #           runoff_coeff_file_name, runoff_coeff_field, runoff_coeff_slope_bin_field, runoff_coeff_soil_type_field, runoff_coeff_land_use_class_field,
        #           runoff_coeff_land_use_class_code_field, slope_file_name, slope_bin_field, soils_file_name, soils_field, soils_bin_field, precipitation_file_name, out_name]
        params = [workspace, watersheds, watersheds_field, land_use, land_use_field,
                  land_use_LU_file_name, land_use_LU_code_field, land_use_LU_bin_field, land_use_LU_desc_field, land_use_LU_class_field,
                  runoff_coeff_file_name, runoff_coeff_field, runoff_coeff_slope_bin_field, runoff_coeff_soil_type_field, runoff_coeff_land_use_class_field,
                  runoff_coeff_land_use_class_code_field, slope_file_name, soils_file_name, soils_field, precipitation_file_name, out_name]

        # If present, populate input values from configuration file. Assumes all fields present,
        # will throw an error if a parameter is missing in ini file.
        if os.path.isfile(CONFIG_FILE_NAME):
            config = helpers.load_config(CONFIG_FILE_NAME)
            for param in params:
                if param.datatype != "Boolean":
                    param.value = config.get("RWSM", param.name)

        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        # Validate parameters here
        # TODO: Add paramter validation in a future release.

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        # Validation responses here

        # TODO: Add messages for parmaeter validadtion, in a future release.

        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        # Populate config object with GUI values
        config = helpers.get_empty_config()
        config.add_section("RWSM")
        config.set("RWSM", "workspace", parameters[0].valueAsText)
        config.set("RWSM", "watersheds", parameters[1].valueAsText)
        config.set("RWSM", "watersheds_field", parameters[2].valueAsText)
        config.set("RWSM", "land_use", parameters[3].valueAsText)
        config.set("RWSM", "land_use_field", parameters[4].valueAsText)
        config.set("RWSM", "land_use_LU_file_name", parameters[5].valueAsText)
        config.set("RWSM", "land_use_LU_code_field", parameters[6].valueAsText)
        config.set("RWSM", "land_use_LU_bin_field", parameters[7].valueAsText)
        config.set("RWSM", "land_use_LU_desc_field", parameters[8].valueAsText)
        config.set("RWSM", "land_use_LU_class_field",
                   parameters[9].valueAsText)
        config.set("RWSM", "runoff_coeff_file_name",
                   parameters[10].valueAsText)
        config.set("RWSM", "runoff_coeff_field", parameters[11].valueAsText)
        config.set("RWSM", "runoff_coeff_slope_bin_field",
                   parameters[12].valueAsText)
        config.set("RWSM", "runoff_coeff_soil_type_field",
                   parameters[13].valueAsText)
        config.set("RWSM", "runoff_coeff_land_use_class_field",
                   parameters[14].valueAsText)
        config.set("RWSM", "runoff_coeff_land_use_class_code_field",
                   parameters[15].valueAsText)
        config.set("RWSM", "slope_file_name", parameters[16].valueAsText)
        # config.set("RWSM", "slope_bin_field", parameters[17].valueAsText)
        config.set("RWSM", "slope_bin_field", "slope_bin")
        config.set("RWSM", "soils_file_name", parameters[17].valueAsText)
        config.set("RWSM", "soils_field", parameters[18].valueAsText)
        # config.set("RWSM", "soils_bin_field", parameters[20].valueAsText)
        config.set("RWSM", "soils_bin_field", "soils_bin")
        config.set("RWSM", "precipitation_file_name",
                   parameters[19].valueAsText)
        config.set("RWSM", "out_name", parameters[20].valueAsText)
        # config.set("RWSM", "delete_temp", parameters[22].valueAsText)
        # config.set("RWSM", "overwrite_config", parameters[23].valueAsText)

        # Write config file to disk
        config_file = open(CONFIG_FILE_NAME, 'w')
        config.write(config_file)
        config_file.close()

        # Run analysis
        rwsm.run_analysis(config=config, is_gui=True)

        return
