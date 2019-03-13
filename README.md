# Street Based Demographics


## (Almost) Geoless Geocoding: Linking blocks to streets via the Census Relationship files.

The US Census Bureau maintains a map of streets, natural features, and addresses called the Topologically Integrated Geographic Encoding and Referencing (TIGER) files. These files are crucial for the design and publication of public use demographic data. The map of streets allows the Census to divide the entire nation into blocks -- any polygon bounded by three or more streets. These millions of blocks are used as a small spatial aggregation unit, and allow the Census Bureau to publish vast amounts of data. These include the block-level population counts necessary for congressional redistricting, small-area measures of poverty used to allocate federal aid, and the neighborhood-level demographic statistics frequently used in social science research. According to a [USCB executive report](https://www.census.gov/library/working-papers/2017/decennial/census-data-federal-funds.html), "132 programs used Census Bureau data to distribute more than $675 billion in funds during fiscal year 2015," all using blocks as their smallest unit of aggregation.

Some data sets from federal agencies include only a block identifier and an address.  Block identifiers are added to data sets to support block-wise aggregation of data.  For example, one might imagine a data set describing recipients of aid from some program.  

`USER_ID  |   ADDRESS     | BLOCK_ID
123         123 Main St.    4567`

If this data included a block identifier, one could create block-wise summaries with a simple:

`SELECT COUNT(*) FROM DATA GROUP BY BLOCK_ID`

However, producing street-wise summaries from the same data would be difficult.  That is what if one wanted to know how many people lived on the same segment of Main St.?

The code in the repository enables one to map Block-Address combinations to individual census street geometries.  It relies on the [Block Relationship Files](https://www2.census.gov/geo/pdfs/maps-data/data/tiger/tgrshp2014/TGRSHP2014_TechDoc_Ch4.pdf) These scripts enable one to make street-wise maps of program participation, crime, any event/record mapped to a named street and census block.

## But this is stupid, why not just geocode the addresses?
Geocoding is expensive (via available APIs) and inefficient for very large databases (think hundreds of millions of points).  The methods here enable on to create streetwise maps of large collections of point data.

## Workflow overview

### Inputs:
* TIGER edge files and block relationship files for an area of interest. Edges are any linear features included in the Census Bureau's official map. These might be roads, walkways, or ditches. An edge file and block file for Denver county are included in the data directory. TIGER files are downloadable [here](https://www.census.gov/geo/maps-data/data/tiger.html). Note that the included TIGER files have been converted from shapefiles to CSV's with a WKT geometry column (by exporting a geopandas object to CSV) for better portability. This has the added benefit of allowing us to avoid creating spatial objects whenever possible.

* Point level data of interest, where each record has a named street and census block identifier (for example, household-level demographic survey data, such as what is available through the Census Bureau's Federal Statistical Research Data Centers). Due to privacy issues, obtaining example point-level data is often challenging. For the sake of demonstration, this repository includes a 10% sample of address points for Denver county, available through [Denver Open Data](https://www.denvergov.org/opendata/dataset/city-and-county-of-denver-addresses). While these data do not have any associated demographic fields, they have all of the necessary ingredients for linking point data to street segments.

### Necessary libraries:
The code in this repository is largely built around basic table joins, which rely on [`pandas`](http://pandas.pydata.org).
Spatial operations, such as converting latitude and longitude strings to WKT spatial objects, relies on [`shapely`](https://pypi.org/project/Shapely/).
The script `match_tlid_geo.py` relies on [`geopandas`](http://geopandas.org), a hybrid of shapely and pandas. Note that this script is not strictly necessary for the completion of the workflow, as `match_tlid.py` presents a more-efficient alternative.

### Workflow summary
1. Run `tiger_xwalk.py`
2. Run `match_tlid.py` (or `match_tlid_geo.py`)
3. Run `permute_tlids.py`
Final output: point-level data with links to TLIDs (official Census street segment identifiers) in CSV form, and a CSV of empirical p-values describing whether average street-level data aggregations differ from block-level data aggregations

### Step one: Finding possible street segments
Given that calculating every possible pair-wise distance between points and street segments is not a feasible approach, the most obvious way of improving efficiency is to first limit the number of possible street segments for each point.
Think about a typical, rectangular city block with a house on it. Simply based on the block ID associated with that house (let's call it block 1), we know that there are only four possible streets on which the house could be addressed. For convenience, let's call these streets North, South, East, and West. Luckily, we also have the full address of the street: 1234 North St. In our simplistic scenario, we can link the house to a segment of North Street that borders block 1. If there is only one segment matching these criteria, then we're done! No spatial calculations necessary.

Unfortunately, most city blocks are a bit more complex. Street segments are separated by more than street intersections. They are also broken up by intersections with rivers, pipelines, and other linear features. Instead, let's say that there are two possible street segments that border block 1 and are on North Street. From here, we can use spatial operations to find the closest of the two. Less time-consuming than searching every possible segment in the city, we've significantly improved the problem by limiting our search area to two possible lines.

The first step in this method creates a crosswalk between a block ID-street name combination and a list of possible street segments (called TLIDs, for Tiger Linear IDs). The functions to do so are contained in `tiger_xwalk.py`.

### Step two: finding the closest TLID in the list of all possibilities

In Denver county, simply running `tiger_xwalk.py` matches almost 80% of all address points to street segments. The remaining scripts are need to match the other 20%.

The first method available is to use common spatial packages and built-in tools. This primarily involves opening our data into `geopandas` geoDataFrames. In the previous section, our data contained a column called 'geometry' containing the WKT for points, lines, or polygons. Loading data into pandas keeps the columns as is. On the other hand, `geopandas` loads a table while creating `shapely` geometric objects behind the scenes. This gives us access to all of the `shapely` geometric manipulation functions, including a useful one called `distance()`. This approach is implemented in `match_tlid_geo.py`.

A more efficient approach is implemented in `match_tlid.py`, which relies on `match_tlid_utils.py`. The modified workflow is essentially the following: data are loaded, merged with the crosswalk created by `tiger_xwalk.py` (giving lists of possible TLIDs), then converted to dictionaries. Minimum distances are calculated using a basic euclidean distance, which walks along all coordinates of all possible line segments and returns the TLID associated with minimum distance vertex. A dictionary of results is exported as a CSV.

### Analysis of results: Hypothesis testing

The utility of the scripts in this repository assumes we have some reason to group point-based data by street segments, rather than by blocks or other polygons. The final script, `permute_tlids.py` allows us to test whether street-based groupings actually differ from more conventional (and convenient) areal units.

`permute_tlids.py` performs a hypothesis test. The null hypothesis is that point-level data are distributed randomly (spatially-speaking) within each block. The script generates an empirical distribution for this hypothesis by randomly shuffling TLID assignments of points within each block for several iterations. Using this disribution, the script finds empirical p-values. Each p-value represents the following:

The probability of observing a an average difference between street-aggregations and associated block-aggregations more extreme than the "real" difference, given a null hypothesis that data within each block is spatially random (i.e. there is no pattern in the location of point data, holding blocks constant).

`permute_tlids.py` includes a step that generates random point-level "data" -- values associated with each of the Denver address points. "Real" implementations would use point-level data that contains more variables than simple location -- such as point-level demographic data available in restricted Census data centers.
