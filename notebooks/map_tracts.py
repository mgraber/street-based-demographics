import pandas as pd
import geopandas as gpd
import cenpy as cen
import matplotlib.pyplot as plt
import seaborn as sns
import folium
import warnings
warnings.filterwarnings('ignore')

"""
This script contains functions to support plotting tract-level data in notebooks.
See notebooks/blog.ipynb and notebooks/final_report.ipynb for implementation.
"""

# Define filters: tract is the spatial unit, and we will request data for 8 counties
SPATIAL_FILTERS = {'Los Angeles':{'state':'06', 'county':'037'},
                   'Denver':{'state':'08', 'county':'031'},
                   'Cook':{'state':'17', 'county':'031'},
                   'Bronx':{'state':'36', 'county':'005'},
                   'Kings':{'state':'36', 'county':'047'},
                   'New York':{'state':'36', 'county':'061'},
                   'Queens':{'state':'36', 'county':'081'},
                   'Harris':{'state':'48', 'county':'201'}}

MAP_FILTERS = {'Los Angeles':'STATE=06 and COUNTY=037',
               'Denver':'STATE=08 and COUNTY=031',
               'Cook':'STATE=17 and COUNTY=031',
               'Bronx':'STATE=36 and COUNTY=005',
               'Kings':'STATE=36 and COUNTY=047',
               'New York':'STATE=36 and COUNTY=061',
               'Queens':'STATE=36 and COUNTY=081',
               'Harris':'STATE=48 and COUNTY=201'}

COUNTY_CENTERS = {'Los Angeles':[34, -118],
               'Denver':[39, -104],
               'Cook':[41, -87],
               'Bronx':[40, -37],
               'Kings':[40, -37],
               'New York':[40, -37],
               'Queens':[40, -37],
               'Harris':[29, -95],}


# Define demographic variables of interest
COLS = ['H003001','H003003']
COLS_RENT = ['H004003','H004001']

def download_merge_data(county_name='Denver', cols=[], spatial_filters=[], map_filters=[]):
    """
    Accesses 2000 decennial data and 2014 TIGER data to download tract-level
    variables specified, as well as the necessary geometry to map them.

    Merges demographic data with spatial data and returns a geodataframe.

    Parameters
    ----------
    county_name: str
        Name of county
    cols: list
        List of strings containing codes for decennial variables
    spatial_filters: dict
        Dictionary of dictionaries containing spatial filters for decennial data
    map_filters: dict
        Dictionary of strings containing spatial filters for TIGER data

    Returns
    -------
    dem_merged: gpd DataFrame
        Contains tract-level demographic data for the requested variables merged with tract
        geometry
    """

    # Establish connection with the 2000 Decennial Census API
    conn = cen.base.Connection('2000sf1')

    # Submit a query
    dem_data = conn.query(cols, geo_unit='tract',
                          geo_filter=spatial_filters[county_name])

    # Add a conection to get TIGER file spatial information
    conn.set_mapservice('tigerWMS_ACS2014')

    # Submit query, requesting map data in the form of gpd DataFrame
    geodata = conn.mapservice.query(layer=8,
                                    where=map_filters[county_name],
                                    pkg='geopandas')

    # Set GEOID as index and remove prefix
    dem_data.loc[:,'GEOID'] = dem_data.state + dem_data.county + dem_data.tract
    dem_data.index = dem_data.GEOID

    # Merge demographic and geo data on GEOID, convert to gpd DataFrame
    dem_merged = pd.merge(dem_data, geodata, left_index=True, right_on='GEOID')
    dem_merged = gpd.GeoDataFrame(dem_merged)

    return dem_merged

def create_choropleth(dem_merged, col, title='', bins=5):
    """
    Creates static choropleth of demographic data, using the output of
    download_merged_data

    Parameters
    ----------
    dem_merged: gpd DataFrame
        Contains tract-level demographic data for the requested variables merged with tract
        geometry
    cols: str
        Codes for decennial variable to map
    title: str
        Plot heading
    bins: int
        Number of bins in color-map

    """
    fig, ax = plt.subplots(1, figsize=(10, 10))

    dem_merged = dem_merged.dropna()
    dem_merged.plot(column=col,
                        k=bins,
                        ax=ax,
                        legend=True,
                        cmap='Blues',
                        vmin=0, vmax=.5)

    # Get rid of the axis -- the projected coordinates aren't that meaningful
    ax.axis('off')

    # Add a title
    ax.set_title(title,  fontsize=20)

    # Cite data source
    ax.annotate('Source: 2000 Decennial Census Summary File 1',
                xy=(0.1, .05),
                xycoords='figure fraction',
                horizontalalignment='left',
                verticalalignment='top',
                fontsize=12,
                color='#555555')
    plt.show()

def plot_rented(county_name='Denver'):
    """
    Plots maps of tract-level rates of home rentership for the given county

    Parameters
    ----------
    county_name: str
        Name of county to map. Options are: Los Angeles, Denver, Cook, New York,
        Kings, Queens, Bronx, and Harris

    """
    merged_data = download_merge_data(county_name=county_name,
                                   cols=COLS_RENT,
                                   spatial_filters=SPATIAL_FILTERS,
                                   map_filters=MAP_FILTERS)
    merged_data.loc[:,'Rented_Rate'] = merged_data.H004003 / merged_data.H004001
    create_choropleth(merged_data, 'Rented_Rate', "Rented Household Rate by Tract\n"+county_name+" County")

def get_vacant_rates(county_name='Denver'):
    """
    Dowloads and merges tract-level vacancy rates for the given county

    Parameters
    ----------
    county_name: str
        Name of county to map. Options are: Los Angeles, Denver, Cook, New York,
        Kings, Queens, Bronx, and Harris

    """
    merged_data = download_merge_data(county_name=county_name,
                                   cols=COLS,
                                   spatial_filters=SPATIAL_FILTERS,
                                   map_filters=MAP_FILTERS)
    merged_data.loc[:,'Vacant_Rate'] = merged_data.H003003 / merged_data.H003001
    print(merged_data['Vacant_Rate'].describe())
    return merged_data

def plot_vacant(merged_data, county_name='Denver'):
    """
    Plots maps of tract-level vacancy rates for the given county

    Parameters
    ----------
    county_name: str
        Name of county to map. Options are: Los Angeles, Denver, Cook, New York,
        Kings, Queens, Bronx, and Harris

    """
    create_choropleth(merged_data, 'Vacant_Rate', "Vacancy Rate by Tract\n"+county_name+" County")

def hist_vacant(merged_data, county_name='Denver'):
    """
    Plots histograms of tract-level vacancy rates for the given county

    Parameters
    ----------
    county_name: str
        Name of county to map. Options are: Los Angeles, Denver, Cook, New York,
        Kings, Queens, Bronx, and Harris

    """
    merged_data.dropna(subset=['Vacant_Rate'], inplace=True)
    #plt.xlim(0, 1)
    sns.distplot(merged_data['Vacant_Rate'], axlabel="Vacancy Rate by Tract\n"+county_name+" County")
