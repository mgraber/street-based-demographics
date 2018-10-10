import os
import pandas as pd
import numpy as np
import copy
import geopandas as gpd
from random import randint


edges = gpd.read_file(
    "denver_tiger/tl_2017_08031_edges/tl_2017_08031_edges.shp")
faces = gpd.read_file(
    "denver_tiger/tl_2017_08031_faces/tl_2017_08031_faces.shp")
faces['BLKID'] = faces['STATEFP10'] + faces['COUNTYFP10'] + faces['TRACTCE10'] + faces['BLOCKCE10']

streets = edges.loc[(edges['ROADFLG'] == 'Y') & (edges['FULLNAME'] != '')]
streets.reset_index()
print(streets.head())

d = []
for i in range(streets.shape[0]):
    street_name = streets['FULLNAME'].iloc[i]
    left_face = streets['TFIDL'].iloc[i]
    right_face = streets['TFIDR'].iloc[i]
    left_block = faces.loc[faces['TFID'] == left_face]
    if left_block.shape[0] > 0:
        left_block_id = left_block['BLKID'].iloc[0]
    right_block = faces.loc[faces['TFID'] == right_face]
    if right_block.shape[0] > 0:
        right_block_id = right_block['BLKID'].iloc[0]

    for j in range(randint(0, 10)):
        d.append({'street_name': street_name, 'block_id': left_block_id})
    for k in range(randint(0, 10)):
        d.append({'street_name': street_name, 'block_id': right_block_id})

synth_maf = pd.DataFrame(d)

synth_maf.to_csv('den_synth_maf.csv')
