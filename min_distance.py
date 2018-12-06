import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from shapely import ops
from shapely import wkt
import line_profiler

# Hide warnings from output
import warnings
warnings.filterwarnings('ignore')

"""

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

    tlid_df = edges.loc[edges['TLID'].isin(point['TLIDs'])].copy(deep=True).reset_index()
    tlid_df.loc[:,'dist'] = tlid_df.apply(lambda row: point.geometry.distance(row.geometry), axis=1)
    closest_tlid = tlid_df.iloc[np.argmin(tlid_df['dist'])]
    return closest_tlid['TLID']


def find_midpoints(edges):
    """
    Calculates midpoints of edge segments, converting lines to points

    Parameters
    ----------
    edges: gpd DataFrame
            edge data from TIGER

    Returns
    -------
    midpoints: gpd DataFrame
    """
    midpoints = edges.copy()
    midpoints.loc[:,'geometry'] = edges.centroid
    return midpoints


def import_data(county_code = '08031', spatial = True):
    """
    Imports address and TIGER data

    Parameters
    ----------
    county_code: str
            fips code for county
    spatial: bool
            flag to load data and create spatial object with geopandas
            if false, data remain in pandas df with 'geometry' column
            containing wkt

    Returns
    -------
    county_address_df: pd or gpd DataFrame
            of address points
    edges_df: pd or gpd DataFrame
            of edges lines
    """
    # Open address point csv
    county_address_df = pd.read_csv("addresses/" + county_code + "_addresses_sample.csv")
    edges_df = pd.read_csv("tiger_csv/" + county_code + "_edges.csv")

    if spatial:
        crs = {'init': 'epsg:4269'}

        # Convert addresses
        geometry = [Point(xy) for xy in zip(county_address_df.LONGITUDE, county_address_df.LATITUDE)]
        county_address_df = county_address_df.drop(['LATITUDE', 'LONGITUDE'], axis=1)
        county_address_df = gpd.GeoDataFrame(county_address_df, crs=crs, geometry=geometry)

        # Convert edges to spatial object
        edges_df['geometry'] = edges_df['geometry'].apply(wkt.loads)
        edges_df = gpd.GeoDataFrame(edges_df, crs=crs, geometry='geometry')

    return county_address_df, edges_df


def import_xwalk(county_code = '08031'):
    """
    Imports and parses crosswalk created using tiger_xwalk.py

    Parameters
    ----------
    county_code: str
            fips code for county

    Returns
    -------
    xwalk: pd DataFrame
            crosswalk
    """
    xwalk = pd.read_csv("possible_tlids/" + county_code + "_address_maf_xwalk.csv", converters={'BLKID': lambda x: int(x)})
    # Convert TLIDs column to lists
    xwalk = xwalk.assign(TLIDs=xwalk.TLIDs.str.strip('[]').str.split(','))
    return xwalk


def merge_xwalk_addresses(addresses, xwalk):
    """
    Merges crosswalk with addresses to find possible TLIDs for each

    Parameters
    ----------
    addresses: pd or gpd DataFrame
            of address points
    xwalk: pd DataFrame
            crosswalk
    Returns
    -------
    maf_xwalk: pd or gpd DataFrame
            addresses with possible TLIDs and OPTIONS from xwalk
    """
    maf_xwalk = pd.merge(addresses, xwalk,  how='left', left_on=['MAF_NAME','BLKID'], right_on = ['MAF_NAME','BLKID'])
    return maf_xwalk


def simplify_road(edges, county_code='08031', tol=10):
    """
    Simplifies road geometry using shapely
    Saves as shapefile for easy result viewing in QGIS

    Parameters
    ----------
    edges: gpd DataFrame
            of edges lines
    county_code: str
            fips code for county
    tol: int
            maximum allowable meters away from original roads

    Returns
    -------
    edges: gpd DataFrame
            of simplified edges lines
    """
    edges.loc[:,'geometry'] = edges.simplify(tolerance=tol, preserve_topology=False)
    edges.to_file(driver = 'ESRI Shapefile', filename = "tiger_csv/" + county_code + "_edges_simp_" + str(tol))
    return edges


def run_distance_calc(county_code = '08031', spatial = True, simplify = False, tol = 10, mids=False):
    """
    Finds the TLID closest to the point, given that the TLID is one of the options
    found using the tiger_xwalk.py crosswalk

    Parameters
    ----------
    county_code: str
            fips code for county
    spatial: bool
            flag to load and process data using spatial libraries
    simplify: bool
            flag to use shapely's line simplification on the roads prior to calculating
            distances from points
    tol: float
            tolerance for the simplify option -- the number of units away from the true line
            that is acceptable
    mids: bool
            flag to instead calculate distances from the midpoints of each line segment

    Output
    ------

    A csv titled [[county]]_tlid_match.csv, which links each household in the original (or sampled)
    input data with the closest possible TLID, after having narrowed the search area using
    the tiger_xwalk.py crosswalk
    """

    addresses, edges = import_data(spatial = spatial)
    maf_xwalk = merge_xwalk_addresses(addresses, import_xwalk())

    # Identify rows needing a TLID match
    maf_needs_tlid = maf_xwalk.loc[maf_xwalk['OPTIONS'] > 1]
    maf_has_tlid = maf_xwalk.loc[maf_xwalk['OPTIONS'] == 1]

    maf_has_tlid.loc[:,'TLID_match'] = maf_has_tlid.apply(lambda row: row['TLIDs'][0], axis=1)

    if spatial==True:
        if  mids==True:
            edges = find_midpoints(edges)
        elif simplify==True:
            edges = simplify_road(edges, tol = tol)
        #maf_needs_tlid = maf_needs_tlid[pd.notnull(maf_needs_tlid['TLIDs'])]
        maf_needs_tlid.loc[:,'TLID_match'] = maf_needs_tlid.apply(lambda row: min_dist(row, edges), axis=1)

    maf_xwalk = pd.concat([maf_has_tlid, maf_needs_tlid])

    if not os.path.exists("address_tlid_xwalk/"):
        os.mkdir("address_tlid_xwalk/")
    maf_xwalk.to_csv("address_tlid_xwalk/" + county_code + "_tlid_match.csv")

if __name__ == "__main__":
    run_distance_calc(county_code = '08031')
