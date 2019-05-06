import numpy as np
import pandas as pd
from shapely.geometry import Point
from shapely.geometry import LineString
from shapely.wkt import loads
import math

"""
This script contains functions required to run match_tlid.py
"""

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
    print("Number of addresses in input file:", county_address_df.shape[0])

    # Extract a sample for code testing and shorter run-times
    if sample:
        county_address_df = county_address_df.sample(frac=.1)
    edges_df = pd.read_csv("../data/tiger_csv/" + county_code + "_edges.csv", converters={'TLID': lambda x: str(x)})
    edges_df = edges_df.set_index(['TLID'])

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
    # Convert street names and block IDs to strings
    addresses['MAF_NAME'], addresses['BLKID'] = addresses['MAF_NAME'].astype(str), addresses['BLKID'].astype(str)
    xwalk['MAF_NAME'], xwalk['BLKID'] = xwalk['MAF_NAME'].astype(str), xwalk['BLKID'].astype(str)

    # Merge addresses with crosswalk, created with tiger_xwalk.py
    maf_xwalk = pd.merge(addresses, xwalk,  how='left', left_on=['MAF_NAME','BLKID'], right_on = ['MAF_NAME','BLKID'])
    maf_xwalk = maf_xwalk.set_index(['MAFID'])
    print("Number of addresses sucessfully merged with crosswalk:", maf_xwalk.shape[0])
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
    # Convert possible TLIDs to dictionary
    address_point_TLID_candidates = xwalk.loc[:,'TLIDs'].to_dict()
    print("Number of candidates in dictionary form: ", len(address_point_TLID_candidates))
    address_point_TLID = {}
    address_no_cand = []

    # Sort addresses by number of candidates
    for id, candidates in address_point_TLID_candidates.items():
        if isinstance(candidates, list):
            if len(candidates) == 1:
                address_point_TLID[id] = candidates[0]
            elif len(candidates) == 0:
                print("Found address with empty list of TLID candidates")
                address_no_cand.append(id)
        else:
            print("Found address with no list of TLID candidates")
            address_no_cand.append(id)
    print("Number of one-option addresses:", len(address_point_TLID))
    print("Number of no-option addresses:", len(address_no_cand))
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
    # Covert pd address/MAFX data to dictionary format
    address_points = xwalk.loc[:,['TLIDs', 'LATITUDE', 'LONGITUDE']].to_dict('index')
    print("Number of candidates in dictionary form, multi: ", len(address_points))
    multi_TLID_addresses = {}
    address_no_cand = []

    # Sort addresses by number of candidates
    for id, data in address_points.items():
        if isinstance(data['TLIDs'], list):
            if len(data['TLIDs']) > 1:
                multi_TLID_addresses[id] = data
        else:
            print("Found address with no list of TLID candidates")
            address_no_cand.append(id)
    print("Number of multi-option addresses:", len(multi_TLID_addresses))
    return multi_TLID_addresses

def find_edge_geo(id, edges):
    """
    Gets vertices for a given edge

    Parameters
    ----------
    id: str
        TLID -- unique edge identifier
    edges: pd DataFrame
        Edges TIGER file
    Returns
    -------
    geo: str
        WKT of edge's geometry
    """

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
    # Initialize minimum distance as inf
    closest_line = None
    min_dist = np.inf

    # Loop through all vertices of all possible TLIDs
    for idx, aline_wkt in linedict.items():
        if isinstance(aline_wkt, str):
            aline = loads(aline_wkt)
            for vert in list(aline.coords):
                dist = straight_line_distance(vert, point)
                if dist < min_dist:
                    min_dist = dist
                    closest_line = idx
    if closest_line == None:
        print("No TLID match found, last distance calculated: ", vert, point, dist)
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
