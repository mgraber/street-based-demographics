import match_tlid_utils as tlid_utils
import pandas as pd
import numpy as np



def county_to_dicts(county_code='08031'):

    # Import data and convert to dictionaries
    addresses, edges = tlid_utils.import_data(county_code=county_code)

    print(addresses.head())
    xwalk = tlid_utils.import_xwalk(county_code=county_code)
    maf_xwalk = tlid_utils.merge_xwalk_addresses(addresses, xwalk)

    single_match = tlid_utils.get_single_TLID_addresses(maf_xwalk)
    multi_match = tlid_utils.get_multi_TLID_addresses(maf_xwalk)

    geom_list = tlid_utils.get_candidate_geoms(multi_match, edges)
    #point_coords = tlid_utils.get_lat_long(maf_xwalk)

    # Convert address data to a list of dictionaries
    add_list = addresses.to_dict('records')

    return single_match, multi_match, geom_list, add_list

def match_an_address(a, geom_list):
    if a['OPTIONS'] > 1:
        id = (a['MAF_NAME'],  a['BLKID'])
        linedict = geom_list[id]
        point = np.array((float(a['LATITUDE']), float(a['LONGITUDE'])))
        return a['MAFID'], tlid_utils.find_closest(linedict, point)
    else:

def match_generator(multi_match, geom_list, add_list):
    results_list = (match_an_address(address, geom_list) for address in add_list)
    return dict(results_list)

def match_county_tlid(county_code='08031'):
    single, multi, geom_list, add_list = county_to_dicts(county_code=county_code)
    multi_results = match_generator(multi, geom_list, add_list)

if __name__ == "__main__":
    match_county_tlid(county_code='08031')
