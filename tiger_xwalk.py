import os
import pandas as pd
import numpy as np
import copy
import geopandas as gpd
import difflib


"""
This script creates a crosswalk between MAFIDs and a list of all possible TLIDs
and official names for the streets surrounding an address's enumeration block.

"""

def load_tiger(edge_path, face_path):
    """
    Loads already downloaded TIGER data from paths, keeps relevant attributes,
    and sets index for face data.
    """
    # Import TIGER edge data
    edges = gpd.read_file(edge_path)

    # Import TIGER face data
    faces = gpd.read_file(face_path)
    faces.loc[:,'BLKID'] = faces['STATEFP10'] + faces['COUNTYFP10'] + faces['TRACTCE10'] + faces['BLOCKCE10']
    faces = faces[['TFID','BLKID']]
    faces.set_index('TFID')

    return edges, faces


def create_edge_face(edges, faces, roads_only=True):
    """
    Creates a new table with a row for each edge-face
    object

    Parameters
    ----------
    edge: gpd DataFrame
            edge data from TIGER
    face: gpd DataFrame
            face data from TIGER, with concatinated block id
    roads_only: bool
            only includes roads if true, and drops the road flag column in the
            returned DataFrame
    Returns
    -------
    edge_face: pd DataFrame
            Contains a column for TLID, one with the TIGER name,
            one for neighboring TFID, and one which describes which
            side the face is on (0 = left, 1 = right)
            Includes a road flag column if roads_only=False

    """

    # Create edge-face table by splitting face ID and side indicator into two columns
    right_edges = edges[['TLID','TFIDR','FULLNAME','ROADFLG']]
    right_edges.loc[:,'SIDE'] = 1
    right_edges = right_edges.rename(columns={'TFIDR': 'TFID'})

    left_edges = edges[['TLID','TFIDL','FULLNAME','ROADFLG']]
    left_edges.loc[:,'SIDE'] = 0
    left_edges = left_edges.rename(columns={'TFIDL': 'TFID'})

    edge_face = right_edges.append(left_edges)

    if roads_only == True:
        edge_face = edge_face[edge_face['ROADFLG'] == 'Y']
        edge_face.drop(['ROADFLG'], axis=1)

    return edge_face


def create_names_blocks(edge_face, faces):
    """
    Creates a new table with linkage between block IDs and TIGER road names

    Parameters
    ----------
    edge_face: pd DataFrame
            Output of create_edge_face()
            Contains rows for each edge-face combination. If this still contains
            non-roads, then the output will contain several nan values for names,
            and a few for blocks. Some of the names will also refer to things like
            railroads.
    face: gpd DataFrame
            Face data from TIGER, with concatinated block id

    Returns
    -------
    name_blocks: pd DataFrame
            Contains a column with TIGER names, and one with the neighboring block
            id.

    """
    # Link face IDs with block IDs using the edge-face
    edge_face_blocks = edge_face.merge(faces, on='TFID', how='left')
    name_blocks = edge_face_blocks[['FULLNAME', 'BLKID']].drop_duplicates()
    return name_blocks


def match_names(street_name, block_id, names_blocks):
    """
    Given a MAF street name and block id, finds the closest TIGER street name match
    among the street names associated with the same block.

    Parameters
    ----------
    street_name: str
            Full name of the street of interest, in MAF form
    block_id: str
            15 digit block identifier
    name_blocks: pd DataFrame
            Contains a column with TIGER names, and one with the neighboring block
            id

    Returns
    -------
    closest_match: str
            The TIGER street name most closely matching the MAF street name,
            among those associated with the same block
    """
    names_subset = names_blocks.loc[names_blocks['BLKID'] == block_id]
    possible_names = names_subset['FULLNAME'].dropna().tolist()
    closest_match = difflib.get_close_matches(street_name, possible_names, cutoff=0.5, n=1)
    if len(closest_match)>0:
        #print(closest_match[0])
        return closest_match[0]
    else:
        print('**** No Match Found ****')
        print(street_name, block_id)
        print(possible_names)
        return None


def make_names_table(maf, names_blocks):
    """
    Using all name-block combinations in the MAF and TIGER, makes a table matching
    MAF street name with TIGER street name. This does so by calling match_names()

    Parameters
    ----------
    maf: pd DataFrame
            Extract of MAF (or synthetic) which has street names ('MAF_NAME')
            and block id ('BLKID') fields
    name_blocks: pd DataFrame
            Contains a column with TIGER names, and one with the neighboring block
            id.

    Returns
    -------
    names: pd DataFrame
            Contains a column with TIGER names, one with the neighboring block
            id, and one with MAF name
    """

    names = maf[['MAF_NAME', 'BLKID']]
    names = names.drop_duplicates(keep='first')
    names = names.reset_index(drop=True)
    names.loc[:,'FULLNAME'] =  names.apply(lambda row: match_names(row['MAF_NAME'], row['BLKID'], names_blocks), axis=1)
    return names

def name_tlid_table(names, faces, edge_face):
    """
    Applies find_possible_tlid() to a names table contining both MAF and TIGER street names,
    by joining with face-edge information

    Parameters
    ----------
    names: pd DataFrame
            Contains a column with TIGER names, one with the neighboring block
            id, and one with MAF name
    face: gpd DataFrame
            Face data from TIGER, with concatinated block id
    edge_face: pd DataFrame
            Contains a column for TLID, one with the TIGER name,
            one for neighboring TFID, and one which describes which
            side the face is on (0 = left, 1 = right)
    Returns
    -------
    tlid_results: pd DataFrame
            Contains a column with TIGER names, one with the neighboring block
            id, one with MAF name, and one with a list of possible TLIDs
    """
    names.loc[:,'TLIDs'] = names.apply(lambda row: find_possible_tlid(row['FULLNAME'],
                                                                        row['BLKID'],
                                                                        faces,
                                                                        edge_face), axis=1)
    return names


def find_possible_tlid(tiger_name, block_id, face, edge_face):
    """
    Uses relationship tables to return a list of TLIDs that could be associated
    with the address of interest, given the MAF street name and block ID.

    Parameters
    ----------
    tiger_name: str
            Full name of the street of interest, in TIGER form
    block_id: str
            15 digit block identifier
    face: gpd DataFrame
            Face data from TIGER, with concatinated block id
    edge_face: pd DataFrame
            Contains a column for TLID, one with the TIGER name,
            one for neighboring TFID, and one which describes which
            side the face is on (0 = left, 1 = right)

    Returns
    -------
    possible_tlid: a list of possible TLIDs for given household
    """
    #print('Finding TLIDs for ', tiger_name, ', block ', block_id)
    possible_faces_df = face.loc[face['BLKID'] == block_id]
    possible_faces = possible_faces_df['TFID'].tolist()

    possible_edge_faces = edge_face.loc[(edge_face['TFID'].isin(possible_faces))
                                & (edge_face['FULLNAME'] == tiger_name)]

    possible_tlid = possible_edge_faces['TLID'].tolist()
    #print(possible_tlid)
    return possible_tlid

if __name__ == "__main__":

    # Load TIGER data
    den_edges, den_faces = load_tiger("denver_tiger/tl_2017_08031_edges/tl_2017_08031_edges.shp",
                                            "denver_tiger/tl_2017_08031_faces/tl_2017_08031_faces.shp")
    bldr_edges, bldr_faces = load_tiger("boulder_tiger/tl_2018_08013_edges/tl_2018_08013_edges.shp",
                                            "boulder_tiger/tl_2018_08013_faces/tl_2018_08013_faces.shp")

    # Create edge-face relationship table
    den_edge_face = create_edge_face(den_edges, den_faces)
    print('\n\n\n', 'Edge-Face table: \n', den_edge_face.head(), '\n\n\n')
    #bldr_edge_face = create_edge_face(bldr_edges, bldr_faces)

    # Create names-blocks relationship table using TIGER names
    den_tiger_names = create_names_blocks(den_edge_face, den_faces)
    print('\n\n\n', 'TIGER Names-Blocks table: \n', den_tiger_names.head(), '\n\n\n')
    #bldr_tiger_names = create_names_blocks(bldr_edge_face, bldr_faces)

    # Load Denver address data (block IDs were imputed using a spatial join with face data)
    den_maf = pd.read_csv('den_addresses.csv', converters={'BLKID': lambda x: str(x)})
    #den_maf.loc[:,'BLKID'] = '0' + den_maf['BLKID']
    print('\n\n\n', 'Imported Address table: \n', den_maf.head(), '\n\n\n')

    # Match names to create MAFname-block-TIGERname tables (most time consuming step)
    print('\n\n\n Creating names tables \n\n\n')

    den_add_names = make_names_table(den_maf, den_tiger_names)
    print(den_add_names.head())
    den_add_names.to_csv('den_add_names.csv')

    """
    Synthetic (circular) MAF data implementation

    # Load synthetic MAF data
    den_synth_maf = pd.read_csv('den_synth_maf.csv',  converters={'block_id': lambda x: str(x)})
    den_synth_maf = den_synth_maf[['block_id','street_name']]
    den_synth_maf = den_synth_maf.rename(columns={'street_name':'MAF_NAME','block_id':'BLKID'})

    bldr_synth_maf = pd.read_csv('bldr_synth_maf.csv',  converters={'block_id': lambda x: str(x)})
    bldr_synth_maf = bldr_synth_maf[['block_id','street_name']]
    bldr_synth_maf = bldr_synth_maf.rename(columns={'street_name':'MAF_NAME','block_id':'BLKID'})

    # Match names to create MAFname-block-TIGERname tables (most time consuming step, uncomment to recreate)
    # print('\n\n\n Creating names tables \n\n\n')

    # den_names = make_names_table(den_synth_maf, den_tiger_names)
    # print(den_names.head())
    # den_names.to_csv('den_names.csv')
    den_names = pd.read_csv('den_names.csv', converters={'BLKID': lambda x: str(x)})

    # bldr_names = make_names_table(bldr_synth_maf, bldr_tiger_names)
    # print(bldr_names.head())
    # bldr_names.to_csv('bldr_names.csv')
    bldr_names = pd.read_csv('bldr_names.csv', converters={'BLKID': lambda x: str(x)})
    """

    ############## Everything above this point can be done once if outputs are saved as CSVs #############

    print('\n\n\n\n\n Finding TLIDs \n\n\n')

    den_add_xwalk = name_tlid_table(den_add_names, den_faces, den_edge_face)
    print(den_add_xwalk.head())
    den_add_xwalk.to_csv('den_add_xwalk.csv')

    """
    bldr_xwalk = name_tlid_table(bldr_names, bldr_faces, bldr_edge_face)
    print(bldr_xwalk.head())
    bldr_xwalk.to_csv('bldr_xwalk.csv')
    """
