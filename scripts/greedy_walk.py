import random
import csv
import numpy as np
import pandas as pd
import scipy as sp
from scipy.spatial.distance import mahalanobis

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
    edges_file = pd.read_csv(edge_path, converters={'TFIDL': lambda x: x.split('.')[0],
                                                'TFIDR': lambda x: x.split('.')[0],
                                                'TLID':lambda x: str(x),
                                                'TNIDF':lambda x: str(x),
                                                'TNIDT':lambda x: str(x)})
    edges = edges_file.loc[:,['FULLNAME','TLID','TFIDL','TFIDR','TNIDF','TNIDT', 'ROADFLG']]
    edges.dropna(subset=['FULLNAME','TLID','TFIDL','TFIDR','TNIDF','TNIDT', 'ROADFLG'], inplace=True)

    # Only keep roads
    edges = edges[edges['ROADFLG'] == 'Y'].reset_index()
    edges.drop(['ROADFLG'], axis=1)

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

    print("Check that every edge has both to/from nodes: ", edge_node_df.shape[0]/edges.shape[0])

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
    edge_node = edge_node_df.groupby('TNID')['TLID'].apply(list).apply(set).apply(list).to_dict()
    nodes_from_edges = edge_node_df.groupby('TLID')['TNID'].apply(list).to_dict()
    return edge_node, nodes_from_edges


def generate_synthetic_data(edges, cols=4, invcov=True):
    """
    Generates columns of synthetic data for the sake of method development

    Parameters
    ----------
    edges: pd DataFrame
            each row is a road edge (street segment)
    cols: int
            number of columns of synthetic data to generate
    invcov: bool
            if True, also returns an inverse covariance matrix
            of the data

    Returns
    -------
    edges_data: pd DataFrame
            each row is a road edge (street segment), with TLID as its index,
            remaining columns are random numbers representing demographic data.
    invcov_data: np array, optional
            inverse covariance of the array of data returned in edges_data,
            used to calculate Mahalanobis distance
    """
    column_names = list(map(int, list(range(cols))))
    edges_data = pd.DataFrame(np.random.rand(edges.shape[0], cols), columns=column_names)
    edges_data.loc[:,'TLID'] = edges['TLID']
    edges_data.loc[:,'FULLNAME'] = edges['FULLNAME']
    # Block ID is not contianed in edges file, but is contained in TLID aggregated data (?)
    ## TODO: Check that TLID aggregations keep BLKID, create BLKID for synthetic data
    #edges_data.loc[:,'BLKID'] = edges['BLKID']
    edges_data.set_index('TLID', inplace=True)

    if invcov:
        cov = edges_data.drop('FULLNAME', axis=1).cov()
        invcov_data = sp.linalg.inv(cov)
        return edges_data, invcov_data

    else:
        return edges_data

def mahal_distance(tlid_1, tlid_2, data, invcov_data):
    """
    Calculates multivariate distance metric between two data points
    Uses Mahalanobis distance

    Parameters
    ----------
    tlid_1: str
            ID of first data point
    tlid_2: str
            ID of second data point
    data: pd DataFrame
            contains data, where index is TLIDs
    invcov_data: np array
            covariance matrix for data

    Returns
    -------
    m_dist: float
            Mahalanobis distance between the two data points
    """
    point_1 = data.loc[tlid_1,:]
    try:
        point_2 = data.loc[tlid_2,:]
    except:
        print("No households on this possible TLID")
        return np.inf
    m_dist = mahalanobis(point_1, point_2, invcov_data)
    return m_dist

def euc_distance(tlid_1, tlid_2, data):
    """
    Calculates multivariate distance metric between two data points
    Uses Euclidean distance

    Parameters
    ----------
    tlid_1: str
            ID of first data point
    tlid_1: str
            ID of second data point
    data: pd DataFrame
            contains data, where index is TLIDs
    Returns
    -------
    e_dist: float
            Euclidean distance between the two data points
    """
    point_1 = data.loc[tlid_1,:]
    try:
        point_2 = data.loc[tlid_2,:]
    except:
        print("No households on this possible TLID")
        return np.inf
    e_dist = np.linalg.norm(point_1-point_2)
    return e_dist

def find_most_similar(tlid, node, edge_node, data, invcov_data=None, metric='m'):
    """
    Searches all other TLIDs sharing the same node, computing multivariate
    distance metrics to each. Returns the TLID of the most similar.

    Parameters
    ----------
    tlid: str
            ID of the current street segment
    node: str
            ID of the intersection where a decision is being made
    edge_node: dict
            keys are TNIDs, values are lists of associated TLIDs
    data: pd DataFrame
            each row is a road edge (street segment), with TLID as its index,
            remaining columns are random numbers representing demographic data.
            For example, the output of generate_synthetic_data()
    invcov_data: np array, optional
            inverse covariance of the array of data returned in edges_data,
            used to calculate Mahalanobis distance
    metric: 'e' or 'm'
            If 'e', computes Euclidean distance. If 'm', computes mahalanobis
            distance
    Returns
    -------
    next_tlid: str
            ID of the most similar street segment sharing the same node
    """
    #print("Currently at node: ", node)
    #print("Currently at edge: ", tlid)
    #print("Contiguous edges: ", edge_node[node])
    min_dist = np.inf
    next_tlid = None
    for contig_tlid in edge_node[node]:
        #print("Possible next TLID: ", contig_tlid)
        if metric=='e':
            dist = euc_distance(tlid_1=tlid, tlid_2=contig_tlid, data=data)
        elif metric=='m':
            dist = mahal_distance(tlid_1=tlid, tlid_2=contig_tlid,
                                data=data,
                                invcov_data=invcov_data)
        #print("Distance: ", dist)
        if dist < min_dist:
            dist = min_dist
            next_tlid = contig_tlid
    return next_tlid


def walk_network(edge_node, nodes_from_edges, data, invcov_data = None, metric='m'):
    """
    Randomly selects a starting node-TLID pair. At each node, makes a decision
    about the next move using find_most_similar(). For each node, saves indicators
    for the next move staying on the same-named street, and for staying on the same
    block. After each move, removes visited nodes from the set of node-TLID pairs.
    Continues until all node-TLID pairs are visited.

    Parameters
    ----------
    edge_node: dict
            keys are TNIDs, values are lists of associated TLIDs
    edges_data: pd DataFrame
            each row is a road edge (street segment), with TLID as its index,
            remaining columns are random numbers representing demographic data.
    invcov_data: np array, optional
            inverse covariance of the array of data returned in edges_data,
            used to calculate Mahalanobis distance
    metric: 'e' or 'm'
            If 'e', computes Euclidean distance. If 'm', computes mahalanobis
            distance
    Returns
    -------
    nodes: dict
            Keys are TNIDs, values are indicators for same-street moves and
            same-block moves
    """
    nodes = {}
    num_paths = 1

    # Randomly select a node-TLID pair as the start of the walk_network
    cur_node = random.choice(list(edge_node))
    cur_tlid = random.choice(list(edge_node[cur_node]))

    only_vars = data.drop('FULLNAME', axis=1)

    # Perform find_most_similar, remove each visited node-TLID from possibilities
    while(len(nodes_from_edges) > 0):

        # Remove visited edge
        #print("Removing visited TLID: ", cur_tlid)
        nodes_from_edges.pop(cur_tlid, None)

        # Remove TLID options for cur_node if they've already been visited

        edge_node[cur_node] = [tlid for tlid in edge_node[cur_node] if tlid in nodes_from_edges.keys()]

        if len(edge_node[cur_node]) == 0:
            # This case occurs if there are no possible moves from the current node
            edge_node.pop(cur_node, "Could not remove empty node key")
            #print("No possible contiguous roads -- chosing next step randomly...")

            # Re-pick a random start, continue picking until there are possible moves
            next_node = random.choice(list(edge_node))
            edge_node[next_node] = [tlid for tlid in edge_node[next_node] if tlid in nodes_from_edges.keys()]

            while len(edge_node[next_node]) == 0:
                edge_node.pop(next_node, "Could not remove empty node key")
                if len(edge_node) == 0:
                    print("Total nodes evaluated: ", len(nodes))
                    print("Number of discrete paths: ", str(num_paths))
                    return nodes
                #print("No possible contiguous roads -- chosing next step randomly...")
                next_node = random.choice(list(edge_node))
                # Remove TLID options for next_node if they've already been visited
                edge_node[next_node] = [tlid for tlid in edge_node[next_node] if tlid in nodes_from_edges.keys()]

            #print(edge_node[next_node])
            next_tlid = random.choice(list(edge_node[next_node]))
            #print(next_tlid)
            num_paths += 1

        else:
            # Find most similar TLID sharing the current node
            next_tlid = find_most_similar(tlid=cur_tlid, node=cur_node,
                                        edge_node=edge_node,
                                        data=only_vars,
                                        invcov_data=invcov_data,
                                        metric=metric)

            # Don't end up at the same node when moving to the next edge
            nodes_from_edges[next_tlid].remove(cur_node)
            if len(nodes_from_edges[next_tlid]) == 0:
                # This should never execute
                print("Error: Both to- and from-nodes for this edge have been visited")

            # Compare name and block of current TLID and next TLID to characterize move
            if data.loc[cur_tlid, 'FULLNAME'] == data.loc[next_tlid, 'FULLNAME']:
                nodes.update({cur_node:{'street': 1}})
                #print("Same street move")
            else:
                nodes.update({cur_node:{'street': 0}})
            ## TODO: Merge BLKID to road network for public data before including this
            '''
            if data.loc[cur_tlid, 'BLKID'] == data.loc[next_tlid, 'BLKID']:
                nodes[cur_node]['block'] = 1
            else:
                nodes[cur_node]['block'] = 0
            '''

        # Step to the next position
        #print("Next TLID: ", next_tlid)
        if next_tlid not in nodes_from_edges.keys():
            print("Next TLID already visited")
        #print("Next node: ", nodes_from_edges[next_tlid][0])

        # Move to the next TLID-node combo
        next_node = nodes_from_edges[next_tlid][0]
        #print("TLIDs left to visit: ", len(nodes_from_edges))

        cur_tlid = next_tlid
        cur_node = next_node

    print("Total nodes evaluated: ", len(nodes))
    print("Number of discrete paths: ", str(num_paths))
    return nodes

def walk_county(county_code = '08031'):
    county_roads = load_roads('../data/tiger_csv/' + county_code + '_edges.csv')
    county_edge_node_df = create_edge_node_df(county_roads)
    county_edge_node, tlid_dict = create_node_dict(county_edge_node_df)
    ## TODO: Replace this step with loading demographic data
    dem_data, dem_invcov = generate_synthetic_data(county_roads)
    dem_data.to_csv("../data/synthetic/" + county_code + "_synthetic.csv")

    nodes = walk_network(edge_node=county_edge_node,
                        nodes_from_edges=tlid_dict,
                        data=dem_data,
                        invcov_data=dem_invcov,
                        metric='e')

    outfile_name = "../results/walk_results/" + county_code + "_walk.csv"

    with open(outfile_name, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(["TNID", "Same-name"])
        for row in nodes.items():
            writer.writerow(row)


if __name__ == "__main__":
    walk_county(county_code = '08031')
    walk_county(county_code = '08031')
    walk_county(county_code = '08031')
    walk_county(county_code = '08031')
