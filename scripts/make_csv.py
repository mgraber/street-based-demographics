from glob import glob
import os
import numpy as np
import pandas as pd
import geopandas as gpd

def make_csv(dir, columns=[]):
  shapefiles = glob(dir + "/*/")
  gpd_files = [gpd.read_file(shapefile + os.path.basename(os.path.normpath(shapefile)) + '.shp') for shapefile in shapefiles]
  merged_df = pd.concat(gpd_files)[columns]
  print(dir + 'all_counties.csv')
  print(list(merged_df))
  print(merged_df.shape)
  print('\n\n\n', merged_df.head())
  merged_df.to_csv(dir + 'all_counties.csv')

if __name__ == "__main__":
    make_csv('./edges/', ['STATEFP', 'COUNTYFP', 'TLID', 'TFIDL', 'TFIDR', 'MTFCC', 'FULLNAME', 'ROADFLG','TNIDF','TNIDT','geometry'])
    make_csv('./faces/', ['STATEFP10','COUNTYFP10','TRACTCE10','BLOCKCE10','TFID','geometry'])
