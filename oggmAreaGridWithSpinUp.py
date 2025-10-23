import matplotlib.pyplot as plt
import oggm.cfg as cfg
import salem
import xarray as xr
import numpy as np
import glob
import os
from oggm.sandbox import distribute_2d
from oggm import tasks, utils, workflow, graphics, DEFAULT_BASE_URL
from oggm.workflow import execute_entity_task
from oggm.utils import get_demo_file


# Start by following the "Run with a long spinup and GCM data" tutorial for glaical growth modeling.
# Initialize OGGM and set up the default run parameters
cfg.initialize()

# Local working directory (where OGGM will write its output)
cfg.PATHS['working_dir'] = utils.gettempdir('OGGM_spinup_run_area_grid')

# Use multiprocessing?
cfg.PARAMS['use_multiprocessing'] = False

# This is necessary for spinup runs!
cfg.PARAMS['store_model_geometry'] = True


rgi_ids = ['RGI60-11.00897'] #Using Hintereisferner as suggested in the tutorial

#Slight change from tutotial as from_prepro_level=4 seemed required for area/thickness grid tutorial
gdirs = workflow.init_glacier_directories(rgi_ids, prepro_base_url=DEFAULT_BASE_URL, from_prepro_level=4, prepro_border=80)

# Additional climate file (CESM)
cfg.PATHS['cesm_temp_file'] = get_demo_file('cesm.TREFHT.160001-200512'
                                            '.selection.nc')
cfg.PATHS['cesm_precc_file'] = get_demo_file('cesm.PRECC.160001-200512'
                                             '.selection.nc')
cfg.PATHS['cesm_precl_file'] = get_demo_file('cesm.PRECL.160001-200512'
                                             '.selection.nc')
execute_entity_task(tasks.process_cesm_data, gdirs);

# Run the last 200 years with the default starting point (current glacier)
# and CESM data as input
execute_entity_task(tasks.run_from_climate_data, gdirs,
                    climate_filename='gcm_data',
                    ys=1801, ye=2000,
                    store_fl_diagnostics=True,
                    output_filesuffix='_no_spinup');
# Run the spinup simulation: a rather "cold" climate with a cold temperature bias
execute_entity_task(tasks.run_constant_climate, gdirs, y0 = 1965,
                    nyears=100, bias=0, 
                    store_fl_diagnostics=True,
                    output_filesuffix='_spinup');
# Run a past climate run based on this spinup
execute_entity_task(tasks.run_from_climate_data, gdirs,
                    climate_filename='gcm_data',
                    ys=1801, ye=2000,
                    store_fl_diagnostics=True,
                    init_model_filesuffix='_spinup',
                    output_filesuffix='_with_spinup');
# Run a past climate run based on this spinup
execute_entity_task(tasks.run_from_climate_data, gdirs,
                    climate_filename='gcm_data',
                    ys=1801, ye=2000, init_model_yr=50,
                    init_model_filesuffix='_spinup',
                    store_fl_diagnostics=True,
                    output_filesuffix='_with_spinup_50yr');


# Compile output
utils.compile_glacier_statistics(gdirs)
ds1 = utils.compile_run_output(gdirs, input_filesuffix='_no_spinup')
ds2 = utils.compile_run_output(gdirs, input_filesuffix='_with_spinup')
ds3 = utils.compile_run_output(gdirs, input_filesuffix='_with_spinup_50yr')

#Starting part of the "Display Glacier Area and Thickness Changes on a Grid" tutorial
#Skiping to the preprocessing part as the glaicer of intreset and the workflow task has already been done.

# This is to add a new topography to the file (smoothed differently)
workflow.execute_entity_task(distribute_2d.add_smoothed_glacier_topo, gdirs)
# This is to get the bed map at the start of the simulation
workflow.execute_entity_task(tasks.distribute_thickness_per_altitude, gdirs)
# This is to prepare the glacier directory for the interpolation (needs to be done only once)
workflow.execute_entity_task(distribute_2d.assign_points_to_band, gdirs);


gdir = gdirs[0] #Get the gridded data for Hintereisferner
with xr.open_dataset(gdir.get_filepath('gridded_data')) as ds:
    ds = ds.load()

ds = workflow.execute_entity_task(
    distribute_2d.distribute_thickness_from_simulation,
    gdirs, 
    input_filesuffix="_with_spinup", # Use the simulation with the 100 year spin up that we just did
    output_filesuffix='',  # filesuffix added to the output filename gridded_simulation.nc, if empty input_filesuffix is used
)

# Simple ploting function
def plot_distributed_thickness(ds, title):
    f, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(14, 4))
    ds.simulated_thickness.sel(time=1855).plot(ax=ax1, vmax=400);
    ds.simulated_thickness.sel(time=1900).plot(ax=ax2, vmax=400);
    ds.simulated_thickness.sel(time=2000).plot(ax=ax3, vmax=400);
    plt.tight_layout();
    plt.savefig("HintereisfernerSpunUp.pdf")
    plt.close()

plot_distributed_thickness(ds[0], 'Hintereisferner')
