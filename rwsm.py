import os, sys, helpers, arcpy

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