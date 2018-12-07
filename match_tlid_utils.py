import numpy as np
import pandas as pd
from shapely.geometry import Point
from shapely.geometry import LineString
from shapely.wkt import loads
import math

def import_data(county_code = '08031'):
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
    county_address_df = pd.read_csv("addresses/" + county_code + "_addresses.csv", converters={'BLKID': lambda x: str(x),
                                                                                                'Unnamed: 0': lambda x: str(x)})

    # Use former index to create a synthetic MAFID -- this is any unique identifier for each household
    county_address_df = county_address_df.rename(index=str, columns={"Unnamed: 0": "MAFID"})

    edges_df = pd.read_csv("tiger_csv/" + county_code + "_edges.csv", converters={'TLID': lambda x: str(x)})
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
    xwalk = pd.read_csv("possible_tlids/" + county_code + "_address_maf_xwalk.csv", converters={'BLKID': lambda x: str(x)})
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
    addresses['MAF_NAME'], addresses['BLKID'] = addresses['MAF_NAME'].astype(str), addresses['BLKID'].astype(str)
    xwalk['MAF_NAME'], xwalk['BLKID'] = xwalk['MAF_NAME'].astype(str), xwalk['BLKID'].astype(str)
    maf_xwalk = pd.merge(addresses, xwalk,  how='left', left_on=['MAF_NAME','BLKID'], right_on = ['MAF_NAME','BLKID'])
    maf_xwalk = maf_xwalk.set_index(['MAF_NAME', 'BLKID'])
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
    Identifies where there are multiple options

    Parameters
    ----------
    xwalk: pd DataFrame of merged address and xwalk data

    Returns
    -------
    address_point_TLIDs: dict
            dictionary of addresses points as key with possible TLIDs as values
    """
    address_point_TLID_candidates = xwalk.loc[:,'TLIDs'].to_dict()
    address_point_TLIDs = {}
    for id, candidates in address_point_TLID_candidates.items():
        if isinstance(candidates, list):
            if len(candidates) > 1:
                address_point_TLIDs[id] = candidates
    return address_point_TLIDs


def find_edge_geo(id, edges):
    try:
        geo = edges.loc[id, 'geometry']
        return geo
    except:
        return 'None'

def get_candidate_geoms(multi_TLID_addresses, edges):
    """
    Extracts geometry of the TLIDs, saving as a dictionary
    Parameters
    ----------
    multi_TLID_addresses: dict
            dictionary of addresses points as key with possible TLIDs as values
    Returns
    -------
    geom_list: dict
            dictionary, where key is a street-block combo and value is a list
            of TLID geometries
    """
    geom_list = {}
    for idx, row in multi_TLID_addresses.items():
        geom_list[idx] = {id : find_edge_geo(id, edges) for id in row}
    return geom_list


def find_closest(linedict, point):
    """
    Finds closest TLID to the given point, looping through
    the vertices of the line
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
        if aline_wkt != 'None':
            aline = loads(aline_wkt)
            #print(idx, aline)
            for vert in list(aline.coords):
                if straight_line_distance(vert, point) < min_dist:
                    min_dist = straight_line_distance(vert, point)
                    closest_line = idx
        return closest_line

def straight_line_distance(coord1, coord2):
    """
    Calculates stright-line distance between two points
    ----------
    coord1: two-value np array
                of latitude, longitude
    coord2: two-value np array
                of latitude, longitude

    Returns
    -------
    closest_line: dict item
            TLID and geometry of closest line
    """
    return np.sqrt(np.sum((coord1 - coord2) ** 2))
