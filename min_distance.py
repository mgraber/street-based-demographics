import numpy as np
import pandas as pd
import geopandas as gpd
import line_profiler
import profile
from shapely.geometry import Point
import time

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
    if len(point['TLIDs']) == 0:
        return 'None'
    if len(point['TLIDs']) == 1:
        return point['TLIDs'][0]
    else:
        tlid_df = edges.loc[edges['TLID'].isin(point['TLIDs'])]..reset_index().copy(deep=True)
        #tlid_df = tlid_df.reset_index()
        tlid_df.loc[:,'dist'] = tlid_df.apply(lambda row: point.geometry.distance(row.geometry), axis=1)
        closest_tlid = tlid_df.iloc[np.argmin(tlid_df['dist'])]
        #print('Closest TLID:', closest_tlid['TLID'])
        return closest_tlid['TLID']

def simplify_roads(edge_gpd, tol=.5):
    simple_edges = edge_gpd.simplify(tolerance=tol, preserve_topology=False)
    return simple_edges


def create_webmap(add_gpd, edge_gpd):
    # Interactive plots with Folium
    addresses_json = add_gpd.to_crs(epsg='4326').to_json()
    edges_json = edge_gpd.to_crs(epsg='4326').to_json()
    den_map = folium.Map([39.75, -104.977],
                  zoom_start=14,
                  tiles='cartodbpositron')

    points = folium.features.GeoJson(addresses_json)
    lines = folium.features.GeoJson(edges_json)
    den_map.add_child(points)
    den_map.add_child(lines)
    den_map

def driver(simplify = True, tol = 0):
    import_data_t0 = time.time()

    # Open address point CSV and convert to GeoDataFrame
    den_ad_pd = pd.read_csv("den_addresses.csv")
    geometry = [Point(xy) for xy in zip(den_ad_pd.LONGITUDE, den_ad_pd.LATITUDE)]
    den_ad_pd = den_ad_pd.drop(['LATITUDE', 'LONGITUDE'], axis=1)
    crs = {'init': 'epsg:4269'}
    addresses = gpd.GeoDataFrame(den_ad_pd, crs=crs, geometry=geometry)

    # Open TIGER edges shapefile and crosswalk CSV
    edges = gpd.read_file("denver_tiger/tl_2017_08031_edges/tl_2017_08031_edges.shp")
    xwalk = pd.read_csv("den_xwalk.csv")

    # Convert TLIDs column to lists
    xwalk = xwalk.assign(TLIDs=xwalk.TLIDs.str.strip('[]').str.split(','))
    import_data_t1 = time.time()

    # Merge addresses and crosswalk on both street name and block ID
    maf_xwalk = pd.merge(addresses, xwalk,  how='left', left_on=['MAF_NAME','BLKID'], right_on = ['MAF_NAME','BLKID'])

    simplify_t0 = time.time()
    if simplify == True:
        # Simplify roads before calculating distances
        edges = simplify_roads(edges, tol=tol)
    simplify_t1 = time.time()

    print("Tolerance level: ", tol)

    webmap_t0 = time.time()
    # Create webmap showing the simplified roads along with the points
    create_webmap(addresses, edges_simple)
    webmap_t1 = time.time()

    # Find closest TLID for each address using min_dist()
    geometric_t0 = time.time()
    maf_xwalk = maf_xwalk[pd.notnull(maf_xwalk['TLIDs'])]
    maf_xwalk.loc[:,'TLID_match'] = maf_xwalk.progress_apply(lambda row: min_dist(row, edges), axis=1)
    maf_xwalk[['BLKID','MAF_NAME','TLID_match']].to_csv('den_tlid_match.csv')
    geometric_t1 = time.time()

    print("Import time: ", import_data_t1-import_data_t0)
    print("Simplify time: ", simplify_t1-simplify_t0)
    print("Geometric opporations time: ", geometric_t1-geometric_t0)
    print("Total time: ", import_data_t1-import_data_t0+simplify_t1-simplify_t0+geometric_t1-geometric_t0)

if __name__ == "__main__":



    # Initialize profiler
    profiler = profile.Profile()

    # Calibrate the profiler -- this measures CPU overhead
    cpu_overhead = profiler.calibrate(10000)

    # Remove overhead bias, run driver
    profiler = profile.Profile(bias=cpu_overhead)
    results = profiler.run("driver()")

    # Put the results into a file and view
    profiler.dump_stats("min_dist.prof")
    results.print_stats()
