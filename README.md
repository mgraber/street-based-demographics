# (Almost) Geoless Geocoding: Linking blocks to streets via the Census Replationship files.

The US Census Bureau publishes a national map of streets and addresses called the TIGER Files.  These files form the foundation of many widley used public data sets.  This national map of streets also yields a map of blocks.  That is, every polygon bounded by three or more streets can be thought of as a "Block."  There are millions of such blocks in the United States, and they are used to publish data such as the block-wise population counts used for Cogressional Redistricting and other critical public processes.  

Some data sets from federal agencies include only a block identifier and an address.  Block identifiers are added to data sets to support block-wise aggregation of data.  For example, one might imagine a data set describing recipents of aid from some program.  

`USER_ID  |   ADDRESS     | BLOCK_ID
123         123 Main St.    4567`

If this data included a block identifier, one could create block-wise summaries with a simple: 

`SELECT COUNT(*) FROM DATA GROUP BY BLOCK_ID`

However, producing street-wise summaries from the same data would be difficult.  That is what if one wanted to know how many people lived on the same segment of Main St.?

The code in the repository enables one to map Block-Address combinations to individual census street geometries.  It relies on the [Block Relationshp Files](https://www.census.gov/geo/maps-data/data/rel_blk_download.html) This repostory enables one to make street-wise maps of program participation, crime, any event/record mapped to a street and census block.

##But this is stupid, why not just geocode the addresses?
Geocoding is expensive (via available APIs) and inefficent for very large databases (think hundreds of millions of points).  The methods here enable on to create streetwise maps of large colelctions of point data.
