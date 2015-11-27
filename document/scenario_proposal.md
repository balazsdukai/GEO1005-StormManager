---
title: GEO1005 Project – Storm manager
author: Balázs Dukai (4516001), Yuxuan Kang (4504410)
date: November 19, 2015
---

**Scenario: Crisis Management in a Storm event** 

## User Requirements

+ the system should have quick response, be fast
+ simple interface with simple and straightforward operations
+ simple visualizations that can be understood at a glance
+ speed of response is prior to accuracy
+ direction of the storm and how long is it going to last
+ output as a layer and then use QGIS print composer to print or send digitally
+ user selects the data, and he should be aware of which data to select

## Decisions

+ Which are the blocked roads?
+ What is the affected area that has to be considered? 
+ Which areas need to be provided help first?
	+ dangerous industries
	+ schools
	+ hospitals
+ How many fire trucks are needed?
+ How to keep in contact with the citizens?
+ Areas with dangerous industries

## What will it do?

**General input and output:**

+ Input:
	+ Layers already loaded into QGIS. The input layers are both hazard and impact layers.
	+ mouse input as click on a point or trace a polygon
+ Output:
	+ QGIS layers, these can be printed on demand
	+ Modify the blocked roads (e.g. add or remove road blocks) based on click-input from the user.
	+ Add risk area based on polygon input from the user.
+ The analysis functions are preset. Basically the user is able to perform impact assessment with less "clicks" than normal, because the plugin takes care of the details. This way time is saved.

**Specific inputs and outputs:**

+ Blocked roads:
	+ Input: 
		+ reported accidents/road blocks (trees, collapsed buildings, damaged road surface etc.)
		+ road network
		+ topography
	+ Output:
		+ An updated road network with the integrated road blocks. The new dead ends should be accounted for in any route calculation.
		+ Send the updated road network to the crisis management fleet (firefighters, ambulance etc.).

+ Affected area and where to help first:
	+ Input:
		+ hazard layer(s) (reported property damage and reported civil damage)
		+ buildings layer, including the type of buildings
		+ topography 
	+ Output:
		+ A thematic layer showing the affected areas and the level of the damage.
		+ If special locations fall inside the affected area, they are highlighted on the map. Special locations include: dangerous industries, hospitals, schools, power plants, petrol stations.
		+ Level of highlighting in affected areas:
			1. (Highest) civil damage
			2. Special locations in highly damaged areas
			3. Special locations in damaged areas

+ How many fire trucks are needed:
	+ Input:
		+ fire hazard layer (reported fires)
		+ buildings (with type)
	+ Output:
		+ Numbers showing the required nr. of fire trucks above the affected areas.
		+ Highlight special locations if they are on fire.

## Questions

1. How to subdivide the output layers? Overview layer vs. thematic layers for transportation, buildings etc.

2. Should the plugin be able to subset the data / analyse only a selection of the data, or the data is already prepared and clipped to the correct extent?

3. How regularly are the data going to be updated? What are communication channels? Phone, web server, ...?

4. What about simulation models? Should we write them? What about dynamic input data, for the weather forecast for example? 
	+ A possibility for simulation whould be:
		Dynamic input data for weather forecast, but the simulations are based on a single time which is selected by the user. This way the simulations become simpler and faster. For example the user can select between now, in 1 hour, in 2 hours and in 3 hours time span. Then he gets an output based on the time he selected.

5. Who is providing information about damages and when? Should we predict where damage is likely to happen, or only take into account damages that have alrady happened and have been reported by someone?

6. Is crisis management about a crisis that has happened, or about a crisis that is likely/going to happen?
