import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from shapely import ops
import time
import line_profiler

# Hide warnings from output
import warnings
warnings.filterwarnings('ignore')

"""
Step 1) Open CSV of address points and load into gpd using lat/long
Step 2) Open edges shapefile into a gpd DataFrame
Step 3) Open crosswalk
Step 4) Merge crosswalk with address points
Step 5) Use apply with address point lat/lon and list of TLIDs as inputs to find closest TLID
Step 6) Add column of TLID to the address table
"""

@profile
def min_dist(point, edges):
    """
    Finds the TLID closest to the point, given that the TLID is one of the options
    found using the tiger_xwalk.py crosswalk

    Parameters
    ----------
    edges: gpd DataFrame
            edge data from TIGER
    point: one row of a gpd DataFrame
            a point representing a household, where one column is 'TLIDs'

    Returns
    -------
    closest_tlid['TLID']: str
            TLID of the closest street segment. If none are found, returns 'None'
    """
    if len(point['TLIDs']) == 0:
        #print('No possible TLIDs')
        return 'None'
    if len(point['TLIDs']) == 1 or len(edges.loc[edges['TLID'].isin(point['TLIDs'])]) == 1:
        #print('Only one option')
        return point['TLIDs'][0]
    else:
        tlid_df = edges.loc[edges['TLID'].isin(point['TLIDs'])].copy(deep=True).reset_index()
        #print(tlid_df['TLID'].head())
        tlid_df.loc[:,'dist'] = tlid_df.apply(lambda row: point.geometry.distance(row.geometry), axis=1)
        closest_tlid = tlid_df.iloc[np.argmin(tlid_df['dist'])]
        #print('Closest TLID:', closest_tlid['TLID'])
        return closest_tlid['TLID']


def run_distance_calc(simplify = True, tol = 0, mids=False, sample=False, sample_rate=0.1):
    """
    Finds the TLID closest to the point, given that the TLID is one of the options
    found using the tiger_xwalk.py crosswalk

    Parameters
    ----------
    simplify: bool
            flag to use shapely's line simplification on the roads prior to calculating
            distances from points
    tol: float
            tolerance for the simplify option -- the number of units away from the true line
            that is acceptable
    mids: bool
            flag to instead calculate distances from the midpoints of each line segment
    sample: bool
            flag to run calculation on a random sample of all household points.
    sample_rate: float
            the size of sample desired if sample == True. Default is 10%

    Output
    ------

    A csv titled den_tlid_match.csv, which links each household in the original (or sampled)
    input data with the closest possible TLID, after having narrowed the search area using
    the tiger_xwalk.py crosswalk
    """

    import_data_t0 = time.time()

    # Open address point CSV and convert to GeoDataFrame, sampling if desired
    den_ad_pd = pd.read_csv("den_addresses_sample.csv")
    if sample:
        den_ad_pd = den_ad_pd.sample(frac=sample_rate, replace=False)
        den_ad_pd.to_csv('den_addresses_sample.csv')
    geometry = [Point(xy) for xy in zip(den_ad_pd.LONGITUDE, den_ad_pd.LATITUDE)]
    den_ad_pd = den_ad_pd.drop(['LATITUDE', 'LONGITUDE'], axis=1)
    crs = {'init': 'epsg:4269'}
    addresses = gpd.GeoDataFrame(den_ad_pd, crs=crs, geometry=geometry)


    # Open TIGER edges shapefile and crosswalk CSV. Calculate midpoints of edges if desired.
    edges = gpd.read_file("denver_tiger/tl_2017_08031_edges/tl_2017_08031_edges.shp")
    if mids:
        midpoints = edges.copy()
        midpoints.loc[:,'geometry'] = edges.centroid
    xwalk = pd.read_csv("den_xwalk.csv")

    # Convert TLIDs column to lists
    xwalk = xwalk.assign(TLIDs=xwalk.TLIDs.str.strip('[]').str.split(','))
    import_data_t1 = time.time()

    # Merge addresses and crosswalk on both street name and block ID
    maf_xwalk = pd.merge(addresses, xwalk,  how='left', left_on=['MAF_NAME','BLKID'], right_on = ['MAF_NAME','BLKID'])

    simplify_t0 = time.time()
    if simplify == True:
        print("Tolerance level: ", tol)
        # Simplify roads before calculating distances
        edges.loc[:,'geometry'] = edges.simplify(tolerance=tol, preserve_topology=False)
        edges.to_file(driver = 'ESRI Shapefile', filename = 'simplify_' + str(tol))
    simplify_t1 = time.time()

    # Find closest TLID for each address using min_dist()
    geometric_t0 = time.time()
    maf_xwalk = maf_xwalk[pd.notnull(maf_xwalk['TLIDs'])]
    if mids:
        maf_xwalk.loc[:,'TLID_match'] = maf_xwalk.apply(lambda row: min_dist(row, midpoints), axis=1)
    else:
        maf_xwalk.loc[:,'TLID_match'] = maf_xwalk.apply(lambda row: min_dist(row, edges), axis=1)
    maf_xwalk[['BLKID','MAF_NAME','TLID_match']].to_csv('den_tlid_match.csv')
    geometric_t1 = time.time()

    print("Import time: ", import_data_t1-import_data_t0)
    print("Simplify time: ", simplify_t1-simplify_t0)
    print("Geometric opporations time: ", geometric_t1-geometric_t0)
    print("Average geometric opporations time: ", (geometric_t1-geometric_t0)/maf_xwalk.shape[0])
    print("Total time: ", import_data_t1-import_data_t0+simplify_t1-simplify_t0+geometric_t1-geometric_t0)



if __name__ == "__main__":
    run_distance_calc(simplify = False, mids=True, sample=False)
