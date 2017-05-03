import helpers, os


LOCAL_PATH = os.path.dirname( os.path.realpath(__file__) )
CONFIG_FILE_NAME = os.path.join( LOCAL_PATH, "rwsm.ini" )

class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "RWSM"
        self.alias = ""

        # List of tool classes associated with this toolbox
        self.tools = [RWSM]


class RWSM(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "RWSM Hydrology Analysis"
        self.description = ""
        self.canRunInBackground = False

    # Configure UI fields
    def getParameterInfo(self):

        # TODO: Identify if workspace needs to be a required field
        workspace = arcpy.Parameter(
            displayName="Workspace",
            name="workspace",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input"
        )

        # Watershed shapefile location
        watersheds = arcpy.Parameter(
            displayName="Watersheds",
            name="watersheds",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input",
        )

        # Watershed identification field
        # TODO: Add check to ensure field exists in shapefile
        watersheds_field = arcpy.Parameter(
            displayName="Watershed Field",
            name="watersheds_field",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        watersheds_field.parameterDependencies = [watersheds.name]

        # Land Use shapefile
        land_use = arcpy.Parameter(
            displayName="Land Use Shapefile",
            name="land_use",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )

        # Land use field
        # TODO: Add check to ensure field exists in shapefile
        land_use_field = arcpy.Parameter(
            displayName="Land Use Field",
            name="land_use_field",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        land_use_field.parameterDependencies = [land_use.name]

        # Land use lookup table
        # TODO: Idenitfy if we need to support CSV import option
        #       for land use lookup.
        land_use_LU = arcpy.Parameter(
            displayName="Land Use Lookup",
            name='land_use_LU',
            datatype="DETable",
            parameterType="Required",
            direction="Input")

        # Land use lookup bin field
        land_use_LU_bin_field = arcpy.Parameter(
            displayName="Land Use Lookup Bin Field",
            name="land_use_LU_bin_field",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        land_use_LU_bin_field.parameterDependencies = [land_use_LU.name]

        # Runoff Coefficient Lookup Table
        # TODO: Idenitfy if we need to support CSV import option
        #       for runoff coefficient lookup table.
        runoff_coeff_LU = arcpy.Parameter(
            displayName="Runoff Coefficient Lookup Table",
            name='runoff_coeff_LU',
            datatype="DETable",
            parameterType="Required",
            direction="Input"
        )

        runoff_coeff_field = arcpy.Parameter(
            displayName="Runoff Coefficient Field",
            name="runoff_coeff_field",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        runoff_coeff_field.parameterDependencies = [runoff_coeff_LU.name]

        # Slope Raster
        slope_file_name = arcpy.Parameter(
            displayName="Slope Raster Input",
            name="slope_file_name",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input"
        )

        # Soils Shapefile
        soils_file_name = arcpy.Parameter(
            displayName="Soils Shapefile Input",
            name="soils_file_name",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input",
        )

        # Precipitation Raster
        precipitation_file_name = arcpy.Parameter(
            displayName="Precipitation Raster Input",
            name="precipitation_file_name",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input"
        )

        out_name = arcpy.Parameter(
            displayName="Output Name",
            name="out_name",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )

        # TODO: Need to add logic check for ini file support
        delete_temp = arcpy.Parameter(
            displayName="Delete Temp Data",
            name="delete_temp",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )
        delete_temp.value = False

        overwrite_config = arcpy.Parameter(
            displayName="Overwrite Stored Defaults",
            name="overwrite_config",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )
        overwrite_config.value = False

        params = [workspace,watersheds,watersheds_field,land_use,land_use_field,
            land_use_LU,land_use_LU_bin_field,runoff_coeff_LU,runoff_coeff_field,slope_file_name,
            soils_file_name,precipitation_file_name,out_name,
            delete_temp,overwrite_config]

        # If present, populate input values from configuration file.
        params_tmp = []
        if os.path.isfile( CONFIG_FILE_NAME ):
            config = helpers.load_config( CONFIG_FILE_NAME )
            for param in params:
                if param.datatype != "Boolean":
                    # TODO: Add check to ensure file paths exist
                    param.value = config.get("RWSM", param.name)

        config = helpers.load_config( CONFIG_FILE_NAME )
        runoff_coeff_LU.value = config.get("RWSM", "runoff_coeff_LU")

        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        # Validate parameters here

        # Write values to config file if it doesn't exist
        # TODO: Add checkbox to override existing configuration file.
        # if not os.path.isfile("rwsm.ini"):
        #     helpers.write_config( params )

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        # Validation responses here

        # Make sure watersheds file is a polygon
        watersheds = parameters[1]
        if watersheds.hasBeenValidated:
            describe = arcpy.Describe( watersheds.value )
            if describe.shapeType == 'Polygon':
                # watersheds.setWarningMessage("Watersheds shapefile does not have polygon information," \
                #     "please select a feature layer with polygons")
                watersheds.setErrorMessage("Watersheds shapefile does not have polygon information," \
                    "please select a feature layer with polygons")
            else:
                watersheds.clearMessage()

        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        # Read parameter values as text
        workspace = parameters[0].valueAsText
        watersheds = parameters[1].valueAsText
        watersheds_field = parameters[2].valueAsText
        land_use = parameters[3].valueAsText
        land_use_field = parameters[4].valueAsText
        land_use_LU = parameters[5].valueAsText
        land_use_LU_bin_field = parameters[6].valueAsText
        runoff_coeff_LU = parameters[7].valueAsText
        runoff_coeff_field = parameters[8].valueAsText
        out_name = parameters[9].valueAsText
        slope_file_name = parameters[10].valueAsText
        soils_file_name = parameters[11].valueAsText
        precipitation_file_name = parameters[12].valueAsText
        delete_temp = parameters[13].valueAsText
        overwrite_config = parameters[14].valueAsText

        # Initialize workspace
        # TODO: Insert workspace optimization here, temporary gdb
        # See dissolve test, make cleaner

        # TODO: Update progressor label

        # Dissolve watersheds, keep single parts
        # TODO: Determine if we really neeed to dissolve watersheds.
        ws = rwsm.Watershed(watersheds,watersheds_field)
        

        # Iterate through watersheds


        # TODO: Clip land use
        #clipped_land_use = rwsm.clip_land_use(watersheds, land_use, land_use_field)
        
        # Clip soils




        return