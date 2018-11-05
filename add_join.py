import pandas as pd
import numpy as np
import geopandas as gpd

# Import Denver faces, check extent and CRS
faces = gpd.read_file(
    "denver_tiger/tl_2017_08031_faces/tl_2017_08031_faces.shp")
print('FACES DATA:')
print('Extent: ', faces.total_bounds)
print('CRS: ', faces.crs)

# Import Denver addresses, check extent and CRS
addresses = gpd.read_file(
    "den_addresses/addresses.shp")
print('\nADDRESS DATA:')
print('Extent: ', addresses.total_bounds)
print('CRS: ', addresses.crs)
print(addresses.shape)

# Reproject address data
add_reproj = addresses.to_crs({'init': 'epsg:4269'})

# Points within blocks
joined_data = gpd.sjoin(add_reproj,
                         faces,
                         how="inner",
                         op='intersects')
df = joined_data[['PREDIRECTI','STREET_NAM','POSTTYPE']]
df = df.apply(lambda row: None if row.isnull().all() else ' '.join(row.dropna()), axis=1)
joined_data.loc[:,'MAF_NAME'] = df
joined_data.loc[:,'BLKID'] = (joined_data['STATEFP10'] + joined_data['COUNTYFP10'] + joined_data['TRACTCE10'] + joined_data['BLOCKCE10']).astype(str)
joined_data = joined_data[['LATITUDE', 'LONGITUDE', 'MAF_NAME', 'BLKID']]
print(joined_data.shape)
print(joined_data.head())
joined_data.to_csv('den_addresses.csv')
