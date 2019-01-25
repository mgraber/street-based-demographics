import pandas as pd
import numpy as np
import csv
import os

import match_tlid_utils as tlid_utils

def county_to_dicts(county_code='08031', sample=True):
    """
    Imports address points, crosswalk from tiger_xwalk.py, and TIGER edges data
    Merges addresses with crosswalk, indexing on synthetic MAFID. Identifies addresses
    with only one TLID option and assigns match. Seperates ones with multiple TLID options
    for distance-based matching. Both single-option and multi-option addresses are stored
    in dictionaries. Stores wkt geometry of TLID possibilities in a dictionary
    with synthetic MAFID as the key.

    Parameters
    ----------
    county_code: str
            fips code for county
    sample: bool
            if true, only process 10% of addresses

    Returns
    -------
    single_match: dict
            results dictionary -- contains results for one-option addresses, synthetic
            MAFID as keys and TLID as values
    multi_match: dict
            dictionary of addresses points, where key is synthetic MAFID, and values
            are another dictionary containing TLID lists, latitude, and longitude
    geom_list:dict
            dictionary, where key is a MAFID and value is a dictionary with
            TLIDs as keys and WKT geometries as values
    """
    # Import data and convert to dictionaries
    addresses, edges = tlid_utils.import_data(county_code=county_code, sample=sample)
    xwalk = tlid_utils.import_xwalk(county_code=county_code)
    maf_xwalk = tlid_utils.merge_xwalk_addresses(addresses, xwalk)

    single_match = tlid_utils.get_single_TLID_addresses(maf_xwalk)
    multi_match = tlid_utils.get_multi_TLID_addresses(maf_xwalk)
    geom_list = tlid_utils.get_candidate_geoms(multi_match, edges)


    return single_match, multi_match, geom_list

def match_an_address(id, attributes, geom_list):
    """
    Applies match_tlid_utils.find_closest to a single address. Extracts both
    line geometries from geom_list, and point coordinates from input dictionary.

    Returns synthetic MAFID and TLID of the match.

    Parameters
    ----------
    id: str
            synthetic MAFID or other unique point identifier
    attributes: dict
                contains list of possible TLIDs, latitude, and longitude
    geom_list:dict
            dictionary, where key is a MAFID and value is a dictionary with
            TLIDs as keys and WKT geometries as values
    Returns
    -------
    k, v: str, str
            synthetic MAFID and TLID match
    """
    # Get dictionary of geom of all possible TLIDs
    linedict = geom_list[id]
    point = np.array((float(attributes['LATITUDE']), float(attributes['LONGITUDE'])))
    k, v = id, tlid_utils.find_closest(linedict, point)
    return k, v

def match_generator(multi_match, geom_list):
    """
    Applies match_an_address to entire dictionary of addresses with multiple options
    using a generator list comprehension. Converts results to a dictionary.

    Parameters
    ----------
    multi_match: dict
            dictionary of addresses points, where key is synthetic MAFID, and values
            are another dictionary containing TLID lists, latitude, and longitude
    geom_list:dict
            dictionary, where key is a MAFID and value is a dictionary with
            TLIDs as keys and WKT geometries as values

    Returns
    -------
    results_list: dict
            results dictionary -- contains results for one-option addresses, synthetic
            MAFID as keys and TLID as values
    """
    results_list = (match_an_address(id, attributes, geom_list) for id, attributes in multi_match.items())
    return dict(results_list)

def match_county_tlid(county_code='08031', sample=False):
    """
    Opens data, crosswalk, and edges file and performs TLID match for address points.
    Saves results as a csv named "address_tlid_xwalk/[[county_code]]_tlid_match.csv"
    where the first column is synthetic MAFID and the second column is TLID match.

    Parameters
    ----------
    county_code: str
            fips code for county
    sample: bool
            if true, only process 10% of addresses

    """
    single, multi, geom_list = county_to_dicts(county_code=county_code, sample=sample)
    multi_results = match_generator(multi, geom_list)
    results = {**single, **multi_results}

    if not os.path.exists("../results/address_tlid_xwalk/"):
        os.mkdir("../results/address_tlid_xwalk/")

    if sample:
        outfile_name = "../results/address_tlid_xwalk/" + county_code + "samp_tlid_match.csv"
    else:
        outfile_name = "../results/address_tlid_xwalk/" + county_code + "_tlid_match.csv"

    with open(outfile_name, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(["MAFID", "TLID_match"])
        for row in results.items():
            writer.writerow(row)

if __name__ == "__main__":
    match_county_tlid(county_code='08031')
