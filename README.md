# Regional Watershed Spreadsheet Model

The Regional Watershed Spreadsheet Model (RWSM) was developed to estimate average annual regional and sub-regional scale loads for the San Francisco Bay Area. It is part of a class of deterministic empirical models based on the volume-concentration method. The assumption within these types of models is that an estimate of mean annual volume for each land use type within a watershed can be combined with an estimate of mean annual concentration for that same land use type to derive a load which can be aggregated for a watershed or many watersheds in a region of interest. 

## Getting Started

Instructions below are a basic overview of the steps required to get started with the RWSM. For more in-depth instructions please refer to section 2.4, Running the Hydrology Model Tool, within the RWSM Tool-Kit User Manual.

### Prerequisites

This code-base has been tested with ArcMap verison 10.5.1 and requires a valid Spatial Analyst package license.

### Installing and Running

1. Download the source code to your computer and unpackage into a local directory.
2. Open ArcMap and navigate to the Catalog interface.
    * You may have to use the Catalog's "Connect to Folder" feature to access the toolbox.
3. Browse to the toolbox file path, double click RWSM_Toolbox.pyt.
4. After ArcMap loads the toolbox, click "RWSM Hydrology Analysis".
5. Double clicking "RWSM Hydrology Analysis" will launch the toolbox GUI.
6. Use the RWSM GUI to select appropriate input data.
7. For more information please refer to the "RWSM Tool-Kit User Manual" available at http://www.sfei.org/projects/regional-watershed-spreadsheet-model

### Model Outputs

After running the RWSM tool, you can view runoff load statistics, output shapefiles, and intermediate shapefiles within the output directory selected within the GUI. For more information about model output refer to the "RWSM Tool-Kit User Manual".

## Authors

* Lorenzo T. FLores
* Marshall Kunze

## License

This project is licensed under the GNU Lesser General Public License - see the LICENSE file for details

## Acknowledgments

* Alicia Gilbreath for reviewing RWSM protocol and leading discussions regarding protocol.

