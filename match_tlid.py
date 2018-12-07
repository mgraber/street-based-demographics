import match_tlid_utils as tlid_utils
import pandas as pd
import numpy as np
import csv


def county_to_dicts(county_code='08031'):

    # Import data and convert to dictionaries
    addresses, edges = tlid_utils.import_data(county_code=county_code)
    print("Total input addresses:", addresses.shape[0])
    xwalk = tlid_utils.import_xwalk(county_code=county_code)
    maf_xwalk = tlid_utils.merge_xwalk_addresses(addresses, xwalk)

    single_match = tlid_utils.get_single_TLID_addresses(maf_xwalk)
    print("Total input single:", len(single_match))
    multi_match = tlid_utils.get_multi_TLID_addresses(maf_xwalk)
    print("Total input multi:", len(multi_match))
    geom_list = tlid_utils.get_candidate_geoms(multi_match, edges)


    return single_match, multi_match, geom_list

def match_an_address(id, attributes, geom_list):
    linedict = geom_list[id]
    point = np.array((float(attributes['LATITUDE']), float(attributes['LONGITUDE'])))
    k, v = id, tlid_utils.find_closest(linedict, point)
    return k, v

def match_generator(multi_match, geom_list):
    results_list = (match_an_address(id, attributes, geom_list) for id, attributes in multi_match.items())
    return dict(results_list)

def match_county_tlid(county_code='08031'):
    single, multi, geom_list = county_to_dicts(county_code=county_code)
    multi_results = match_generator(multi, geom_list)
    print("Total output multi:", len(multi_results))
    results = {**single, **multi_results}
    print("Total output addresses:", len(results))

    with open("address_tlid_xwalk/" + county_code + "_tlid_match.csv", 'w') as f:
        writer = csv.writer(f)
        for row in results.items():
            writer.writerow(row)

if __name__ == "__main__":
    match_county_tlid(county_code='08031')
