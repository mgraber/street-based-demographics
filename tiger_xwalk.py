import os
import pandas as pd
import numpy as np
import copy
import geopandas as gpd


"""
This script creates a crosswalk between MAFIDs and a list of all possible TLIDs
and official names for the streets surrounding an address's enumeration block.

Joins:
1) Table 1: MAF, with primary key MAFID
2) Table 2: Extract of MAF, with primary key MAFID. This will also contain the
    BLOCKID and street name associated with each MAFID.
3) Table 3: Blocks table (available as a TIGER product) has primary key BLOCKID.
4) Table 4: Faces table (available as a TIGER product) has a primary key TFID.
    Each TFID also has associated BLOCKID.
5) Table 5: Need to create a table with primary key TFID-TLID-SIDE. This requires
    creating a column of all TFIDs from the TFIDL and TFIDR fields of the edges
    file. When doing so, save the associated TLID, and create an indicator column
    for left or right.
6) Table 6: Edges table (available as a TIGER product) has primary key TLID. There
    are also TFIDL and TFIDR used in step 5. Also important is the FULLNAME column,
    and the indicator for roads (either the feature class column or the indicator).
7) Table 7: Need to create a table with primary key FULLNAME-BLOCKID. This requires
    taking the FULLNAME from all of the rows in table 5, then looking up which
    block the associated with each TFID using the faces table.
8) Table 8: Using Table 2 and Table 7, make another table where each row has
    a street name, a BLOCKID, and a name source -- either MAF or TIGER.

Function:
Given a MAFID, use associated BLOCKID and NAME, find closest TIGER name that matches
the block ID, then use BLOCKID with the faces table to get a list of associated TFIDs,
then use this list and the TIGER name with table 5 to get a list of associated TLIDs.

This list can then be used to make geometric searching much faster.
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
    faces['BLKID'] = faces['STATEFP10'] + faces['COUNTYFP10'] + faces['TRACTCE10'] + faces['BLOCKCE10']
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


def maf_names_blocks():
    """
    Creates a new table with linkage between block IDs and MAF official road names

    Need to understand the RDC input data better to write this.

    Parameters
    ----------
    ???

    Returns
    -------
    maf_name_blocks: pd DataFrame
            Contains a column with MAF names, and one with the neighboring block
            id.
    """
    pass


def names_table(names_blocks, maf_names_blocks):
    """
    Creates a table with a new street name identifier, and links this to both
    the MAF and TIGER street names, as well as neighboring blocks.

    Uses text similarity to find which street name of all names associated with
    each block ID is closest to the MAF name.

    Parameters
    ----------
    names_blocks: pd DataFrame
            Output of create_names_blocks()
            Contains rows for each name-block combination. Names are in the form
            of the TIGER files
    maf_names_blocks: pd DataFrame
            Output of maf_names_blocks()
            Contains rows for each name-block combination. Names are in the form
            of the MAF

    Returns
    -------
    names: pd DataFrame
            Contains one row for each street name-block id combo.
            Columns: STREETID(index), TIGER_NAME, MAF_NAME, BLKID
    """
    pass


def fake_names_table(names_blocks):
    """
    Creates a table with a new street name identifier, and links this to both
    the MAF and TIGER street names, as well as neighboring blocks.

    This is a fake version of the real function to work with the synthetic MAF
    data derived from the TIGER edges file.


    Parameters
    ----------
    names_blocks: pd DataFrame
            Synthetic names-blocks connection from the TIGER edges file

    Returns
    -------
    names: pd DataFrame
            Contains one row for each street name-block id combo.
            Columns: STREETID(index), TIGER_NAME, MAF_NAME, BLKID
    """

    names = names_blocks.rename(columns={'block_id':'BLKID', 'street_name':'TIGER_NAME'})
    names.loc[:,'MAF_NAME'] = names['TIGER_NAME']
    names.loc[:,'STREETID'] = names.index

    return names




def find_possible_tlid(maf_street_name, block_id, names, face, edge_face):
    """
    Uses relationship tables to return a list of TLIDs that could be associated
    with the address of interest, given the MAF street name and block ID.

    Parameters
    ----------
    street_name: str
            Full name of the street of interest, in MAF form
    block_id: str
            15 digit block identifier
    names: pd DataFrame
            Contains one row for each street name-block id combo.
            Columns: STREETID(index), TIGER_NAME, MAF_NAME, BLKID
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

    tiger_name_df = names.loc[names['MAF_NAME'] == maf_street_name]
    tiger_name = tiger_name_df.reset_index().loc[0,'TIGER_NAME']

    possible_faces_df = face.loc[face['BLKID'] == block_id]
    possible_faces = possible_faces_df['TFID'].tolist()

    possible_edge_faces = edge_face.loc[(edge_face['TFID'].isin(possible_faces))
                                & (edge_face['FULLNAME'] == tiger_name)]

    possible_tlid = possible_edge_faces['TLID'].tolist()
    return possible_tlid



if __name__ == "__main__":

    # Load TIGER data
    den_edges, den_faces = load_tiger("denver_tiger/tl_2017_08031_edges/tl_2017_08031_edges.shp",
                                            "denver_tiger/tl_2017_08031_faces/tl_2017_08031_faces.shp")
    bldr_edges, bldr_faces = load_tiger("boulder_tiger/tl_2018_08013_edges/tl_2018_08013_edges.shp",
                                            "boulder_tiger/tl_2018_08013_faces/tl_2018_08013_faces.shp")

    # Create edge-face relationship table
    den_edge_face = create_edge_face(den_edges, den_faces)
    bldr_edge_face = create_edge_face(bldr_edges, bldr_faces)

    #print(den_edge_face.head())
    #print(den_edge_face.tail())

    # Create names-blocks relationship table using TIGER names
    den_tiger_names = create_names_blocks(den_edge_face, den_faces)
    bldr_tiger_names = create_names_blocks(bldr_edge_face, bldr_faces)
    #print(bldr_tiger_names.head())
    #print()

    # Create names-blocks relationship table using MAF names (this is the cheat way for synthetic MAF)
    den_synth_maf = pd.read_csv('den_synth_maf.csv')
    den_synth_maf = den_synth_maf[['block_id','street_name']]

    bldr_synth_maf = pd.read_csv('bldr_synth_maf.csv')
    bldr_synth_maf = bldr_synth_maf[['block_id','street_name']]

    den_maf_names = den_synth_maf.drop_duplicates()
    bldr_maf_names = bldr_synth_maf.drop_duplicates()


    # Link MAF names and TIGER names by looking at text similarity (fake version for now)
    den_names = fake_names_table(den_maf_names)
    bldr_names = fake_names_table(bldr_maf_names)

    # Molly's house example
    print("TLID list for Molly's house:")
    print(find_possible_tlid('Grandview Ave', '080130123002008', bldr_names, bldr_faces, bldr_edge_face))

    # Civic center park example\
    print("TLID list for Civic Center Park:")
    print(find_possible_tlid('W 14th Ave','080310020001016', den_names, den_faces, den_edge_face))
