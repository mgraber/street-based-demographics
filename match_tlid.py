import match_tlid_utils as tlid_utils
import pandas as pd
import numpy as np
import csv


def county_to_dicts(county_code='08031'):

    # Import data and convert to dictionaries
    addresses, edges = tlid_utils.import_data(county_code=county_code)
    xwalk = tlid_utils.import_xwalk(county_code=county_code)
    maf_xwalk = tlid_utils.merge_xwalk_addresses(addresses, xwalk)

    single_match = tlid_utils.get_single_TLID_addresses(maf_xwalk)
    multi_match = tlid_utils.get_multi_TLID_addresses(maf_xwalk)

    geom_list = tlid_utils.get_candidate_geoms(multi_match, edges)


    return single_match, multi_match, geom_list

def match_an_address(id, attributes, geom_list):
    linedict = geom_list[id]['TLIDs']
    point = np.array((float(attributes['LATITUDE']), float(attributes['LONGITUDE'])))
    k, v = id, tlid_utils.find_closest(linedict, point)
    #print(linedict, point)
    #print(k, v)
    return k, v

def match_generator(multi_match, geom_list):
    results_list = (match_an_address(id, attributes, geom_list) for id, attributes in multi_match.items())
    #print(next(results_list))
    return dict(results_list)

def match_county_tlid(county_code='08031'):
    single, multi, geom_list = county_to_dicts(county_code=county_code)
    #print(geom_list)
    multi_results = match_generator(multi, geom_list)
    results = {**single, **multi_results}

    with open("address_tlid_xwalk/" + county_code + "_tlid_match.csv", 'wb') as f:
        w = csv.writer(f)
        w.writerows(results.items())


if __name__ == "__main__":
    match_county_tlid(county_code='08031')
