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

        watersheds = arcpy.Parameter(
            displayName="Watersheds",
            name="watersheds",
            datatype="GPFeatureLayer",
            parameterType="Optional",
            direction="Input",
        )

        watersheds_field = arcpy.Parameter(
            displayName="Watershed Field",
            name="watersheds_field",
            datatype="Field",
            parameterType="Optional",
            direction="Input"
        )
        watersheds_field.parameterDependencies = [watersheds.name]

        # TODO: Idenitfy if we need to support CSV import option
        #       for land use lookup.
        land_use_LU = arcpy.Parameter(
            displayName="Land Use Lookup",
            name='land_use_LU',
            datatype="DETable",
            parameterType="Required",
            direction="Input")

        land_use_LU_bin_field = arcpy.Parameter(
            displayName="Land Use Lookup Bin Field",
            name="land_use_LU_bin_field",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        land_use_LU_bin_field.parameterDependencies = [land_use_LU.name]

        # TODO: Idenitfy if we need to support CSV import option
        #       for runoff coefficient lookup table.
        runoff_coeff_LU = arcpy.Parameter(
            displayName="Runoff Coefficient Lookup Table",
            name='runoff_coeff_LU',
            datatype="DETable",
            parameterType="Required",
            direction="Input")

        # Soils Raster
        # TODO: Load default from config or previous run (pickle)
        soils_file_name = arcpy.Parameter(
            displayName="Soils Raster Input",
            name="soils_file_name",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input"
        )

        # Precipitation Raster
        # TODO: Load default from config or previous run (pickle)
        precipitation_file_name = arcpy.Parameter(
            displayName="Precipitation Raster Input",
            name="precipitation_file_name",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input"
        )

        runoff_coeff_field = arcpy.Parameter(
            displayName="Coefficient Field",
            name="runoff_coeff_field",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        runoff_coeff_field.parameterDependencies = [runoff_coeff_LU.name]

        out_name = arcpy.Parameter(
            displayName="Output Name",
            name="out_name",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )

        # TODO: Verify this is needed
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

        params = [workspace, watersheds, watersheds_field, land_use_LU, land_use_LU_bin_field,
                  runoff_coeff_LU, runoff_coeff_field, out_name, soils_file_name, precipitation_file_name,
                  delete_temp, overwrite_config]

        # If present, populate input values from configuration file.
        params_tmp = []
        if os.path.isfile( CONFIG_FILE_NAME ):
            config = helpers.load_config( CONFIG_FILE_NAME )
            for param in params:
                if param.datatype != "Boolean":
                    param.value = config.get("RWSM", param.name)
                # params_tmp.append( param )
        
            # params = params_tmp

        # runoff_coeff_LU.value = "C:\Users\LorenzoF\Documents\RWSM\Input_Data\RunoffCoeff.csv"
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
        return