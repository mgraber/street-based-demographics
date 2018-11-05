import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from tqdm import tqdm

"""
Step 1) Open CSV of address points and load into gpd using lat/long
Step 2) Open edges shapefile into a gpd DataFrame
Step 3) Open crosswalk
Step 4) Merge crosswalk with address points
Step 5) Use apply with address point lat/lon and list of TLIDs as inputs to find closest TLID
Step 6) Add column of TLID to the address table
"""
def min_dist(point, edges):
    """

    """
    #print('\n\nFinding closest TLID for ', point['BLKID'], point['MAF_NAME'])
    if len(point['TLIDs']) == 0:
        #print('No possible TLIDs found in edge file')
        return 'None'
    if len(point['TLIDs']) == 1:
        #print('Only one TLID option:', point['TLIDs'][0])
        return point['TLIDs'][0]
    else:
        tlid_df = edges.loc[edges['TLID'].isin(point['TLIDs'])]
        tlid_df = tlid_df.reset_index()
        tlid_df.loc[:,'dist'] = tlid_df.apply(lambda row: point.geometry.distance(row.geometry), axis=1)
        closest_tlid = tlid_df.iloc[np.argmin(tlid_df['dist'])]
        #print('Closest TLID:', closest_tlid['TLID'])
        return closest_tlid['TLID']

if __name__ == "__main__":

    tqdm.pandas()

    ## Open address point CSV and convert to GeoDataFrame
    den_ad_pd = pd.read_csv("den_addresses.csv")
    geometry = [Point(xy) for xy in zip(den_ad_pd.LONGITUDE, den_ad_pd.LATITUDE)]
    den_ad_pd = den_ad_pd.drop(['LATITUDE', 'LONGITUDE'], axis=1)
    crs = {'init': 'epsg:4269'}
    addresses = gpd.GeoDataFrame(den_ad_pd, crs=crs, geometry=geometry)

    ## Open TIGER edges shapefile and crosswalk CSV
    edges = gpd.read_file("denver_tiger/tl_2017_08031_edges/tl_2017_08031_edges.shp")
    #print(edges.head())

    xwalk = pd.read_csv("den_xwalk.csv")
    xwalk = xwalk.assign(TLIDs=xwalk.TLIDs.str.strip('[]').str.split(','))

    ## Would merge on both BLKID and FULLNAME, or would search for the appropriate TLID list each time
    maf_xwalk = pd.merge(addresses, xwalk,  how='left', left_on=['MAF_NAME','BLKID'], right_on = ['MAF_NAME','BLKID'])


    ## Find closest TLID for each address using min_dist()
    maf_xwalk = maf_xwalk[pd.notnull(maf_xwalk['TLIDs'])]
    maf_xwalk.loc[:,'TLID_match'] = maf_xwalk.progress_apply(lambda row: min_dist(row, edges), axis=1)
    maf_xwalk[['BLKID','MAF_NAME','TLID_match']].to_csv('den_tlid_match.csv')
