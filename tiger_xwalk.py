import os
import pandas as pd
import numpy as np
import copy
import difflib
import line_profiler

# Hide warnings from output
import warnings
warnings.filterwarnings('ignore')

"""
This script creates a crosswalk between block-street combinations and
a list of all possible TLIDs.

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

def load_tiger_csv(edge_path, face_path):
    """
    Loads csv-converted TIGER data from paths, keeps relevant attributes,
    and sets index for face data.
    """
    # Import TIGER edge data
    edges = pd.read_csv(edge_path, converters={'TFIDL': lambda x: x.split('.')[0],
                                                 'TFIDR': lambda x: x.split('.')[0]})
    print("\nLoaded publically available edges table:")
    print(edges[['FULLNAME','TLID','TFIDL','TFIDR']].head())


    # Import TIGER face data
    faces = pd.read_csv(face_path, converters={'STATEFP10': lambda x: str(x),
                                                    'COUNTYFP10': lambda x: str(x),
                                                    'TRACTCE10': lambda x: str(x),
                                                    'BLOCKCE10': lambda x: str(x),
                                                    'TFID': lambda x: str(x)})
    faces.loc[:,'BLKID'] = faces['STATEFP10'] + faces['COUNTYFP10'] + faces['TRACTCE10'] + faces['BLOCKCE10']
    faces = faces[['TFID','BLKID']]
    faces.set_index('TFID')
    print("\nLoaded publically available faces table:")
    print(faces.head())

    return edges, faces

def create_edge_face(edges, faces, roads_only=True):
    """
    Creates a new table with a row for each edge-face
    object

    Parameters
    ----------
    edge: gpd DataFrame
            edge data from TIGER
    face: pd DataFrame
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
    face: pd DataFrame
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


def match_names(street_name, block_id, names_blocks, counter = 0):
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
        return closest_match[0]
    else:
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
    name_errors = names.loc[pd.isna(names['FULLNAME'])]
    print("No match rate:", name_errors.shape[0]/names.shape[0])
    name_errors.to_csv("names_blocks_xwalk/name_match_errors.csv")
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
    possible_faces_df = face.loc[face['BLKID'] == block_id]
    possible_faces = possible_faces_df['TFID'].tolist()
    possible_edge_faces = edge_face.loc[(edge_face['TFID'].isin(possible_faces))
                                & (edge_face['FULLNAME'] == tiger_name)]

    possible_tlid = possible_edge_faces['TLID'].tolist()
    return possible_tlid

def process_county(county_code = '08031'):
    # Load TIGER data
    county_edges, county_faces = load_tiger_csv("tiger_csv/" + county_code + "_edges.csv",
                                            "tiger_csv/" + county_code + "_faces.csv")
    # Load Denver address data (block IDs were imputed using a spatial join with face data)
    county_maf = pd.read_csv("addresses/" + county_code + "_addresses.csv", converters={'BLKID': lambda x: str(x)})
    print("\nLoaded address data:")
    print(county_maf[['LATITUDE','LONGITUDE','MAF_NAME','BLKID']].head())

    # Create edge-face relationship table
    county_edge_face = create_edge_face(county_edges, county_faces)
    print("\nEdge-face relationship table: ")
    print(county_edge_face[['TLID', 'TFID', 'FULLNAME']].head())

    # Create names-blocks relationship table using TIGER names
    county_tiger_names = create_names_blocks(county_edge_face, county_faces)
    print("\nTIGER Names-Blocks relationship table: ")
    print(county_tiger_names.head())

    # Match names to create MAFname-block-TIGERname tables (most time consuming step)
    print("\n Matching names... (this will take a little while) \n")
    if os.path.exists("names_blocks_xwalk/" + county_code + "_address_names.csv"):
        county_add_names = pd.read_csv("names_blocks_xwalk/" + county_code + "_address_names.csv", converters={'BLKID': lambda x: str(x)})
    else:
        if not os.path.exists("names_blocks_xwalk/"):
            os.mkdir("names_blocks_xwalk/")
        county_add_names = make_names_table(county_maf, county_tiger_names)
        county_add_names.to_csv("names_blocks_xwalk/" + county_code + "_address_names.csv")
    print("\nNames match relationship table: ")
    print(county_add_names[['MAF_NAME', 'BLKID', 'FULLNAME']].head())

    print("\n Finding possible TLIDs... \n")

    county_add_xwalk = name_tlid_table(county_add_names, county_faces, county_edge_face)
    print("\n Final results: \n")
    county_add_xwalk.loc[:,'OPTIONS'] = county_add_xwalk.apply(lambda row: len(row['TLIDs']), axis=1)
    needs_geo = county_add_xwalk.loc[county_add_xwalk['OPTIONS'] > 1]
    print(county_add_xwalk[['MAF_NAME', 'BLKID', 'FULLNAME', 'TLIDs','OPTIONS']].head())
    print("\nRate needing spatial selection: ", needs_geo.shape[0]/county_add_xwalk.shape[0])
    if not os.path.exists("possible_tlids/"):
        os.mkdir("possible_tlids/")
    county_add_xwalk.to_csv("possible_tlids/" + county_code + "_address_maf_xwalk.csv")


if __name__ == "__main__":
    process_county(county_code = '08031')
