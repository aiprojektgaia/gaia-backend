# Tasks

The project relies on tasks to execute the engine actions.
These tasks can not be executed individually, they belong to a group called *run-type*.
The system defines different run-types depending on the outcome the user wants to achieve.

## Run-types
There supported run-types are:

* SegmentArea
* Vectorize
* RunItAll
* CompareToBaseImage

### SegmentArea
Given a wms server and layer, the system will download several images which cover a
selected area and then run a segmentation process on them.
The output would be a set of segmented images (binary images with a gray scale values).

### Vectorize
This is the process of converting the segmented images into vector data (geo-packages).
To do that the system will first apply a confidence level to the segmented images and then
convert them into vector data. The images may or may not be combined into a larger one 
before the vectorization process (by default they would be merged).

### RunItAll
This is a combination of the previous two run-types. It will first segment the images and then
vectorize them.

### CompareToBaseImage (not implemented)
This run-type is used to compare the results of a segmentation process to a base image.
The base image would be a binary image with the same dimensions as the segmented images.


## Task
In order for the reuse of certain actions, the run-types are divided into tasks.

A task is usually linked directly to an action that an engine can perform.
The system is build so a task is only linked to one engine.
In the case of the segmentation step, which can have several engines selected, 
the system will create a segmentation task for each selected engine. 
None of the other tasks will do a split like that, they will only have one engine.


The system has implemented the following tasks:

* TileImagesSrc
* SegmentationProcess
* MergeTiles
* ApplyConfidence
* Vectorize
* MergeGeoPackages

### TileImagesSrc
This task takes a wms layer and creates several tiled images which represent 
the selected area.

### SegmentationProcess
The segmentation task will take the tiled images and run a segmentation process on them.
The output will be a binary image with a gray scale value which will represent 
buildings/roads or any other specific feature the engine was trained to detect.

### MergeTiles
Will move all the segmented images (results) per engine into a single folder 
for easier access. No engine is run in this process.

### ApplyConfidence
This process does two things, it applies a confidence threshold to the
segmented images and creates a bit-image from each of them.
Then it merges all the bit images into one bigger image.

### Vectorize
It vectorizes all the images created in the previous step (for now just one big one)
and generates a GeoPackage for each of them.

### MergeGeoPackages
This process will merge all the GeoPackages into one folder.
No engine is run in this process


## Task Step
In short, a task step is a single execution of a task.

In several of the tasks, the system will execute the same action on multiple images (files).
To make it easier to track the progress, the system creates a task step for each image.
A task step is expected to report when it is done, and it is up to the tasks to interpret 
the result or failure (if only one filed image is enough to fail the task or not)

Each task step has also a result which shows in more detail the result of the execution.

## Task execution (queue/poller)

The system has a feature called poller, which manages the execution of the tasks.
The poller runs every few seconds (5s by default) and checks if there are tasks running.

If there are no tasks or task-steps to be run, then it sleeps until there is something to do.

If nothing is running then it does a check for any task-step in the queue to be run.

And if there are no more steps to be run, it checks for queued tasks and forces the 
task to create task-steps so they can run.
