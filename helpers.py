import os, sys, ConfigParser

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
