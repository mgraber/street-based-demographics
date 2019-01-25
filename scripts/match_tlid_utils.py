import numpy as np
import pandas as pd
from shapely.geometry import Point
from shapely.geometry import LineString
from shapely.wkt import loads
import math

def import_data(county_code = '08031', sample=True):
    """
    Imports address and TIGER data

    Parameters
    ----------
    county_code: str
            fips code for county
    sample: bool
            if true, only process 10% of addresses

    Returns
    -------
    county_address_df: pd DataFrame
            of address points
    edges_df: pd DataFrame
            of edges lines
    """
    # Open address point csv
    county_address_df = pd.read_csv("../data/addresses/" + county_code + "_addresses.csv", converters={'BLKID': lambda x: str(x)})
    if sample:
        county_address_df = county_address_df.sample(frac=.1)
    edges_df = pd.read_csv("../data/tiger_csv/" + county_code + "_edges.csv", converters={'TLID': lambda x: str(x)})
    edges_df = edges_df.set_index(['TLID'])
    print(edges_df.head(30))

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
    xwalk = pd.read_csv("../results/possible_tlids/" + county_code + "_address_maf_xwalk.csv", converters={'BLKID': lambda x: str(x)})
    # Convert TLIDs column to lists
    xwalk = xwalk.assign(TLIDs=xwalk.TLIDs.str.strip('[]').str.replace(" ", "").str.split(','))
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
            addresses with possible TLIDs from xwalk, index is (synthetic) MAFID or other point identifier
    """
    addresses['MAF_NAME'], addresses['BLKID'] = addresses['MAF_NAME'].astype(str), addresses['BLKID'].astype(str)
    xwalk['MAF_NAME'], xwalk['BLKID'] = xwalk['MAF_NAME'].astype(str), xwalk['BLKID'].astype(str)
    maf_xwalk = pd.merge(addresses, xwalk,  how='left', left_on=['MAF_NAME','BLKID'], right_on = ['MAF_NAME','BLKID'])
    maf_xwalk = maf_xwalk.set_index(['MAFID'])
    return maf_xwalk

def is_multi_TLID_candidates(edges_row_TLIDs):
    """
    Determines whether a point has multiple possible TLID candidates

    Parameters
    ----------
    edges_row_TLIDs: a row of the merged address-xwalk table
    Returns
    -------
    True or False
    """
    if len(edges_row_TLIDs) == 0:
        return False
    if len(edges_row_TLIDs) == 1:
        return False
    else:
        return True

def get_single_TLID_addresses(xwalk):
    """
    Converts address point and TLID possibilities to a dictionary
    Identifies where there is only one option, then assigns it as the TLID
    match.

    Parameters
    ----------
    xwalk: pd DataFrame of merged address and xwalk data

    Returns
    -------
    address_point_TLID: dict
            results dictionary -- contains results for one-option addresses
    """
    address_point_TLID_candidates = xwalk.loc[:,'TLIDs'].to_dict()
    address_point_TLID = {}
    for id, candidates in address_point_TLID_candidates.items():
        if isinstance(candidates, list):
            if len(candidates) == 1 and candidates[0]:
                address_point_TLID[id] = candidates[0]
    return address_point_TLID

def get_multi_TLID_addresses(xwalk):
    """
    Converts address point and TLID possibilities to a dictionary
    Identifies where there are multiple options.

    Parameters
    ----------
    xwalk: pd DataFrame of merged address and xwalk data

    Returns
    -------
    address_point_TLIDs: dict
            dictionary of addresses points, where key is synthetic MAFID, and values
            are another dictionary containing TLID lists, latitude, and longitude
    """
    address_points = xwalk.loc[:,['TLIDs', 'LATITUDE', 'LONGITUDE']].to_dict('index')
    multi_TLID_addresses = {}
    for id, data in address_points.items():
        if isinstance(data['TLIDs'], list):
            if len(data['TLIDs']) > 1:
                multi_TLID_addresses[id] = data
    return multi_TLID_addresses

def find_edge_geo(id, edges):
    try:
        geo = edges.loc[id, 'geometry']
        return geo
    except:
        print("Could not find edge geometry from TLID")
        return None

def get_candidate_geoms(multi_TLID_addresses, edges):
    """
    Extracts geometry of all possible TLIDs for an address, saving as a dictionary
    Parameters
    ----------
    multi_TLID_addresses: dict
            dictionary of addresses points as key with possible TLIDs as values
    Returns
    -------
    geom_list: dict
            dictionary, where key is a MAFID and value is a dictionary with
            TLIDs as keys and WKT geometries as values
    """
    geom_list = {}
    for id, data in multi_TLID_addresses.items():
        geom_list[id] = {tlid : find_edge_geo(tlid, edges) for tlid in data['TLIDs']}
    return geom_list


def find_closest(linedict, point):
    """
    Finds closest TLID to the given point, looping through
    the vertices of the line. Finds a local minimum distance
    along the line geometry.
    ----------
    linedict: dict
            TLIDs are keys, line geometry are values
    point: two-value np array
                of latitude, longitude
    Returns
    -------
    closest_line: str
            TLID of closest line
    """
    closest_line = None
    min_dist = np.inf
    for idx, aline_wkt in linedict.items():
        if isinstance(aline_wkt, str):
            aline = loads(aline_wkt)
            for vert in list(aline.coords):
                if straight_line_distance(vert, point) < min_dist:
                    min_dist = straight_line_distance(vert, point)
                    closest_line = idx
        if closest_line == None:
            print("No TLID match found")
        return closest_line

def straight_line_distance(coord1, coord2):
    """
    Calculates stright-line distance between two points
    ----------
    coord1: two-value np array
                of latitude, longitude
    coord2: two-value np array
                of latitude, longitude
    """
    return np.sqrt(np.sum((coord1 - coord2) ** 2))
