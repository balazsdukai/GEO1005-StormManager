# Workflow for developing the Storm Manager QGIS plugin

## Documentation

1. Write down workflow and TODOs for the coming weeks

2. Create a use case (use case diagram) for

	+ a fire scenario
	+ blocked road scenario
		+ tree (includes civil damage)
		+ building
	+ small flood/very high ground water due to heavy rain
	+ civil damage due to collapsed building

3. Update the documentation with the current state

	+ report, as of text
	+ diagrams
		+ update process overview based on meeting (27.11.)
		+ mark where is Stage 1
	+ data model 
		+ For the whole process, not only for a specific case. Use the *roadblock_model* as starting point.

## Data input

### Events

1. Install and familiarize with Time Manager plugin

2. Write a list of events in a CSV. Probably include:
	+ type of event
	+ location
	+ time of record (not when the event occured)

### Maps

1. Decide on what base maps do we need. Probably:
	+ a true color satellite image for overview
	+ a map with road network

2. Locate the aproptriate layer sourced and acquire the layers

## UI

1. Decide on the initial required UI elements

2. Create UI mock-up in Qt / paper

## Plugin operation

1. Create an empty plugin for the project

2. Research on how to combine the output from the TimeManager with the plugin

3. How to control layer visibility from the plugin? 
	+ Drop-down menu or tick box?


