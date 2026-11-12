# Output structure

## Project
Every result will be inside the projects folders. 
The folder name would be project-{project_id}

## Project run
Same as the project, each run will have a folder with the name run-{run_id}

But depending on the type of the run, the structure will be different.
All run-types have a list of task-types that will be executed. 
Each task-type will have a folder named after itself and inside it will be an 
output folder as well.

Here I will describe the structure for the type ``RunItAll``.

Its tasks are:
- TileImagesSrc
- SegmentationProcess
- MergeTiles
- ApplyConfidence
- Vectorize
- MergeGeoPackages

### TileImagesSrc
Here we will find the tiled images that were generated from a source image 
(in this case a WMS server).

### SegmentationProcess
The system will create one folder for each of the images that were tiled.
And the output folder will contain the segmented images.
Note. The results will be in the output folder until the next step moves them.

### MergeTiles
Will move all the segmented images (results) into a single folder.

### ApplyConfidence
This process does two things, it applies a confidence threshold to each of the 
segmented images and creates a bit output from it. 
This partial result is stored in the output/working_area folder.
After all the images are processed, the system merge them into one bigger image.
This image will be found in the output folder.

### Vectorize
It vectorizes all the images created in the previous step (in the output folder only)
and generates a GeoPackage for each of them.

### MergeGeoPackages
This process will merge all the GeoPackages into one folder.
Note. In case the previous step generated more than one GeoPackage, 
you will find multiple files here as well.

## The important folders
The different processes create different output and in some cases partial results that may or may not be useful.
But here is a list of the most important folders:

- TileImagesSrc/{id}/output - Contains the tiled images
- MergeTiles/{id}/output - Contains the segmented images
- ApplyConfidence/{id}/output/working_area - Contains the bit images before they are merged
- ApplyConfidence/{id}/output - Contains the merged bit image
- MergeGeoPackages/{id}/output - Contains the resulting GeoPackages
