import numpy as np
import pandas as pd
import math

def load_roads(edge_path):
    """
    Loads csv-converted TIGER data from paths, subsets to only include roads,
    and keeps relevant attributes.

    Parameters
    ----------
    edge_path: str
                path to csv-converted TIGER edge table

    Returns
    -------
    edges: pd DataFrame
            each row is a road edge (street segment),
            only relevant columns are retained
    """
    # Import TIGER edge data
    edges = pd.read_csv(edge_path, converters={'TFIDL': lambda x: x.split('.')[0],
                                                'TFIDR': lambda x: x.split('.')[0]})
    edges = edges[['FULLNAME','TLID','TFIDL','TFIDR','TNIDF','TNIDT', 'ROADFLG']]

    # Only keep roads
    edges = edges[edges['ROADFLG'] == 'Y']
    edges.drop(['ROADFLG'], axis=1)

    print("\nLoaded publically available road data:")
    print(edges.head())

    return edges


def create_edge_node_df(edges):
    """
    Creates a table where each row is
    a TLID-TNID pair (a street segment and defining intersection node).

    Parameters
    ----------
    edges: pd DataFrame
            each row is a road edge (street segment),
            only relevant columns are retained

    Returns
    -------
    edge_node_df: pd DataFrame
            each row is an edge-node pair (street segment
            and one defining intersection), with official "from"
            and "to" directions saved in the bool column 'DIR'
    """

    # Create edge-node table
    from_nodes = edges[['TLID','TNIDF','FULLNAME','ROADFLG']]
    from_nodes.loc[:,'DIR'] = 0
    from_nodes = from_nodes.rename(columns={'TNIDF': 'TNID'})

    to_nodes = edges[['TLID','TNIDT','FULLNAME','ROADFLG']]
    to_nodes.loc[:,'DIR'] = 1
    to_nodes = to_nodes.rename(columns={'TNIDT': 'TNID'})

    edge_node_df = from_nodes.append(to_nodes)

    return  edge_node_df


def create_node_dict(edge_node_df):
    """
    Creates a dictionary where keys are TNIDs, values are lists of TLIDs

    Parameters
    ----------
    edge_node_df: pd DataFrame
            each row is an edge-node pair (street segment
            and one defining intersection), with official "from"
            and "to" directions saved in the bool column 'DIR'

    Returns
    -------
    edge_node: dict
            keys are TNIDs, values are lists of associated TLIDs
    """
    edge_node = edge_node_df.groupby('TNID')['TLID'].apply(list).to_dict()
    return edge_node

def generate_synthetic_data(edges, cols=4):
    """
    Generates columns of synthetic data for the sake of method development

    Parameters
    ----------
    edges: pd DataFrame
            each row is a road edge (street segment)
    cols: int
            number of columns of synthetic data to generate
    Returns
    -------
    edges_data: pd DataFrame
            each row is a road edge (street segment), with TLID as its index,
            remaining columns are random numbers representing demographic data.
    """
    column_names = list(map(int, list(range(cols))))
    edges_data = pd.DataFrame(np.random.randn(edges.shape[0], cols), columns=column_names)
    edges_data['TLID'] = edges['TLID']
    edges_data = edges_data.set_index('TLID')
    return edges_data


if __name__ == "__main__":
    roads = load_roads('../data/tiger_csv/08031_edges.csv')
    edge_node = create_node_dict(create_edge_node_df(roads))
    #print(edge_node)
    data = generate_synthetic_data(roads)
    print(data.head())
