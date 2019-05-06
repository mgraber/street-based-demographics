import random
import numpy as np
import pandas as pd


"""
This script contains functions for testing whether demographic characteristics
are distributed randomly within blocks. It does so by randomly shuffling households
in each block, and comparing street-aggregated shuffled data with real aggregations.
Using these simulations, the function find_p_vals calculates pseudo p-values
based on an empirical (simulated) null distribution of spatial randomness
within each block.
"""

def permute_houses(dem_data, iterations = 10):
    """
    Randomly permute houses within each block. This allows for
    an empirical distribution to test the hypothesis that data are
    clustered by street.

    Parameters
    ----------
    dem_data: pd DataFrame
            demographic (or synthetic) data with columns for TLIDs and
            BLKIDs. Each row represents a MAFID-indexed household.
    seed: int
            random seed for permutation

    Returns
    -------
    dem_data: pd DataFrame
            demographic (or synthetic) data with columns for TLIDs and
            BLKIDs. Each row represents a MAFID-indexed household. New column
            with shuffled TLIDs, called 'TLID_permuted_{iteration}'
    """
    for i in range(iterations):
        random.seed(25*i)
        dem_data['TLID_permuted_'+str(i)] = dem_data.groupby('BLKID')['TLID'].transform(np.random.permutation)
    return dem_data

def find_global_p_val(data, iterations=10):
    """
    Randomly shuffles TLID assignments within each block,
    reassigning them to each MAFID. Aggregates both the true data
    and the shuffled data, and uses random shuffle to calculate
    empirical p-values for the null hypothesis of random distribution
    within blocks.

    Parameters
    ----------
    data: pd DataFrame
            demographic (or synthetic) data with columns for TLIDs and
            BLKIDs. Each row represents a MAFID-indexed household.
    iterations: int
            number of times to shuffle households and reaggregate

    Returns
    -------
    aggs_avg: pd DataFrame
            each row is a TLID-BLKID pair, first columns are the differences in
            aggregation for each variable, remaining columns are empirical p-values
            averaged over all iterations
    """

    # Aggregate "data"
    # TODO: Change this aggregation to account for real data (TLID-BLKID differences)
    aggs = data[['TLID','A', 'B', 'C', 'D', 'E']].groupby(['TLID']).mean()
    blk_aggs = data[['TLID','BLKID','A', 'B', 'C', 'D', 'E']].groupby(['BLKID']).mean()
    tlid_blk_aggs = data[['TLID','BLKID','A', 'B', 'C', 'D', 'E']].groupby(['TLID','BLKID']).mean().reset_index()
    print("TLID-BLKID aggs: \n", tlid_blk_aggs.head())

    data_sims = permute_houses(dem_data=data, iterations=iterations)
    var_list = ['A', 'B', 'C', 'D', 'E']

    means_list = []
    for i in range(iterations):
        synth_aggs = data_sims[['TLID_permuted_'+str(i),'BLKID','A', 'B', 'C', 'D', 'E']].groupby(['TLID_permuted_'+str(i), 'BLKID']).mean()
        means_list.append({var:synth_aggs[var].abs().mean() for var in var_list})
    means = pd.DataFrame(means_list)
    print(means.abs().head(20))
    print(tlid_blk_aggs.mean().abs())

    p_vals = {var:((means[tlid_blk_aggs[var].abs().mean() < means[var]].shape[0])/iterations) for var in var_list}
    print(p_vals)
    return p_vals

def average_pvals(pval_df, iterations=10):
    """
    Averages p-values accross several iterations

    Parameters
    ----------
    pval_df: pd DataFrame
            each row is a TLID-BLKID pair, first columns are the differences in
            aggregation for each variable, remaining columns are empirical p-values
            with a suffix of the iteration number
    iterations: int
            number of times to shuffle households and reaggregate

    Returns
    -------
    pval_df: pd DataFrame
            each row is a TLID-BLKID pair, first columns are the differences in
            aggregation for each variable, remaining columns are empirical p-values
            averaged over all iterations
    """
    for col in ['A', 'B', 'C', 'D', 'E']:
        p_val_cols = [(col+'_p_'+str(i)) for i in range(iterations)]
        these_p_vals = pval_df[p_val_cols]
        avg_col_name = col+'_avg_p'
        pval_df[avg_col_name] = these_p_vals.astype(float).mean(axis=1)
        pval_df.drop(p_val_cols, axis=1, inplace=True)

    return pval_df


def find_p_vals(data, iterations=10):
    """
    Randomly shuffles TLID assignments within each block,
    reassigning them to each MAFID. Aggregates both the true data
    and the shuffled data, and uses random shuffle to calculate
    empirical p-values for the null hypothesis of random distribution
    within blocks.

    Parameters
    ----------
    data: pd DataFrame
            demographic (or synthetic) data with columns for TLIDs and
            BLKIDs. Each row represents a MAFID-indexed household.
    iterations: int
            number of times to shuffle households and reaggregate

    Returns
    -------
    aggs_avg: pd DataFrame
            each row is a TLID-BLKID pair, first columns are the differences in
            aggregation for each variable, remaining columns are empirical p-values
            averaged over all iterations
    """

    # Aggregate "data"
    # TODO: Change this aggregation to account for real data (TLID-BLKID differences)
    aggs = data[['TLID','BLKID','A', 'B', 'C', 'D', 'E']].groupby(['TLID']).mean()
    blk_aggs = data[['TLID','BLKID','A', 'B', 'C', 'D', 'E']].groupby(['BLKID']).mean()
    tlid_blk_aggs = data[['TLID','BLKID','A', 'B', 'C', 'D', 'E']].groupby(['TLID','BLKID']).mean()
    print("TLID-BLKID aggs: \n", tlid_blk_aggs.head())

    for i in range(iterations):
        shuffled_data = permute_houses(data, seed=i)
        synth_aggs = shuffled_data[['TLID_permuted_'+str(i),'A', 'B', 'C', 'D', 'E']].groupby(['TLID_permuted_'+str(i), 'BLKID']).mean()
        for col in ['A', 'B', 'C', 'D', 'E']:
            #print(synth_aggs[synth_aggs.abs()[col] > aggs.abs()[col]].shape[0])
            aggs.loc[:, col+'_p_'+str(i)] = aggs.apply(lambda row: rate_more_extreme(row[col], synth_aggs[col]), axis=1)
            #aggs.loc[:, col+'_p_'+str(i)] = synth_aggs[synth_aggs.abs()[col] > aggs.abs()[col]].shape[0] / synth_aggs.shape[0]

    aggs_avg = average_pvals(pval_df=tlid_blk_aggs, iterations=iterations)
    return aggs_avg


def rate_more_extreme(val, synth_series):
    """
    Finds proportion of synthetic values that are more extreme than the given
    value

    Parameters
    ----------
    val: float
            value corresponding with a single block-tlid combinations aggregation
            difference
    synth_series: pd Series
            column of a pd DataFrame containing block-tlid
            combinations aggregation difference for a single iteration of shuffled
            data, must be of the same variable as val

    Returns
    -------
    p_val: float
            empirical p-value based on a null-hypothesis formed by the randomly
            shuffled households
    """

    p_val = synth_series[abs(val) < synth_series.abs()].shape[0] / synth_series.shape[0]
    return p_val


if __name__ == "__main__":
    # Load public addresses & crosswalk
    addresses = pd.read_csv('../data/addresses/08031_addresses.csv')
    xwalk = pd.read_csv('../results/address_tlid_xwalk/08031_tlid_match.csv')
    merged_xwalk = pd.merge(addresses, xwalk, on='MAFID')
    merged_xwalk.rename(columns={'TLID_match':'TLID'}, inplace=True)

    # Create random data and merge it to address-xwalk table
    ## TODO: Fix so column names aren't hard coded
    column_names = ['A', 'B', 'C', 'D', 'E']
    rand_data = pd.DataFrame(np.random.randn(merged_xwalk.shape[0], 5), columns=column_names)
    rand_data.loc[:,'MAFID'] = merged_xwalk['MAFID']
    synth_dem_data = pd.merge(merged_xwalk, rand_data, on='MAFID')

    print("\n\nSynthetic demographic data:")
    print(synth_dem_data.head(20))

    pvals = find_global_p_val(synth_dem_data, iterations=30)
