import os, sys, helpers, arcpy

def test_config_read():
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
        direction="Input"
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

    params = [workspace, watersheds, watersheds_field, land_use_LU,
                land_use_LU_bin_field, runoff_coeff_LU, runoff_coeff_field, out_name, delete_temp,
                soils_file_name, precipitation_file_name]

    CONFIG_FILE_NAME = "rwsm.ini"
    if os.path.isfile( CONFIG_FILE_NAME ):
            config = helpers.load_config( CONFIG_FILE_NAME )
            for param in params:
                if param.datatype != "Boolean":
                    print "Param Name: {}, Param Type: {}, Config Value: {}".format(param.name, param.datatype, config.get("RWSM", param.name))
                    param.value = config.get("RWSM", param.name)
                    

def check_shape_type():
    # Setup config object
    CONFIG_FILE_NAME = "rwsm.ini"
    config = helpers.load_config( CONFIG_FILE_NAME )

    watersheds = arcpy.Parameter(
        displayName="Watersheds",
        name="watersheds",
        datatype="GPFeatureLayer",
        parameterType="Optional",
        direction="Input"
    )
    watersheds.value = config.get("RWSM", watersheds.name)
    describe = arcpy.Describe( watersheds.value )

    print watersheds.datatype
    print describe.shapeType

