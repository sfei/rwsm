class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "RWSM"
        self.alias = ""

        # List of tool classes associated with this toolbox
        self.tools = [RWSM_Hydrology_Analysis]


class RWSM_Hydrology_Analysis(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Tool"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):

        workspace = arcpy.Parameter(
            displayName="Workspace",
            name="workspace",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")

        watersheds = arcpy.Parameter(
            displayName="Watersheds",
            name="watersheds",
            datatype="GPFeatureLayer",
            parameterType="Optional",
            direction="Input")

        wsField = arcpy.Parameter(
            displayName="Watershed Field",
            name="watershed_field",
            datatype="Field",
            parameterType="Optional",
            direction="Input")
        wsField.parameterDependencies = [watersheds.name]

        slpBins = arcpy.Parameter(
            displayName="Slope Bins",
            name="slope_bins",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        slpBins.value = '[0, 5], [5, 10]'

        lookupLU = arcpy.Parameter(
            displayName="Land Use Lookup",
            name='land_use_lookup',
            datatype="DETable",
            parameterType="Required",
            direction="Input")

        lookupLUbinField = arcpy.Parameter(
            displayName="Land Use Lookup Bin Field",
            name="land_use_lookup_bin_field",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        lookupLUbinField.parameterDependencies = [lookupLU.name]

        lookupCoeff = arcpy.Parameter(
            displayName="Coefficient Lookup",
            name='coeff_lookup',
            datatype="DETable",
            parameterType="Required",
            direction="Input")

        coeffField = arcpy.Parameter(
            displayName="Coefficient Field",
            name="coeff_field",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        coeffField.parameterDependencies = [lookupCoeff.name]

        outName = arcpy.Parameter(
            displayName="Output Name",
            name="outName",
            datatype="GPString",
            parameterType="Required",
            direction="Input")

        deleteTemp = arcpy.Parameter(
            displayName="Delete Temp Data",
            name='deleteTemp',
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input")
        deleteTemp.value = True

        params = [workspace, watersheds, wsField, slpBins, lookupLU,
                  lookupLUbinField, lookupCoeff, coeffField, outName, deleteTemp]

        return params



        """Define parameter definitions"""
        params = None
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        return