# Patrol Encounter Rate Map Workflow

## Introduction

This workflow helps you to see where your patrols encounter events most often, by combining patrol effort and patrol events from **EarthRanger** into a grid-based encounter rate heatmap.

**What this workflow does:**
- Downloads **patrols** and **patrol events** from EarthRanger for the time range you specify
- Reconstructs patrol trajectories and calculates patrol effort (kilometers traveled) in each grid cell
- Counts the events in each grid cell — or, if you prefer, totals a numeric event field such as `Number of Animals`
- Calculates the encounter rate for each cell (events per kilometer of patrol effort)
- Creates an interactive dashboard map where each cell is colored by its encounter rate, with cells that received too little patrol effort masked in grey
- Optionally splits the map into separate views by category, time period, or spatial region

**Who should use this:**
- Conservation managers evaluating where patrol effort produces the most sightings or incidents
- Researchers analyzing the spatial distribution of wildlife sightings, illegal activity, or other events relative to patrol coverage
- Anyone needing to visualize **patrols** and **patrol events** stored in EarthRanger as a single encounter rate map

---

## Prerequisites

Before using this workflow, you need:

1. **Ecoscope Desktop** installed on your computer
   - If you haven't installed it yet, please follow the installation instructions for Ecoscope Desktop

2. **EarthRanger Data Source** configured in Ecoscope Desktop
   - You must have already set up a connection to your EarthRanger server
   - Your data source should be configured with proper authentication credentials
   - You'll need to know the name of your configured data source (e.g., `"mep_dev"`)

3. **Patrols and Patrol Events** recorded in EarthRanger
   - You need at least one **patrol type** with completed patrols within your selected time range
   - Patrol types can be found at `https://<your-site>.pamdas.org/admin/activity/patroltype/`
   - Event types can be found at `https://<your-site>.pamdas.org/admin/activity/eventtype/`
   - You'll need to know the exact "value" (not display name) of any patrol type or event type you want to filter by — for example `"ecoscope_patrol"` or `"wildlife_sighting_rep"`

---

## Installation

1. Select "Workflow Templates" tab
2. Click "+ Add Template"
3. Copy and paste this URL https://github.com/wildlife-dynamics/patrol-encounter-rate-map and wait for the workflow template to be downloaded and initialized
4. The template will now appear in your available template list

---

## Configuration Guide

### Basic Configuration

#### 1. Workflow Details
Add information that will help to differentiate this workflow from another.

- **Workflow Name** (required): A descriptive name for this analysis
  - Example: `Encounter Rate Workflow`
- **Workflow Description** (optional): Additional details about the purpose of this run
  - Example: `Analyze patrol encounter rates with events.`

#### 2. Data Source
Select the EarthRanger connection to pull data from.

- **Data Source** (required): Select one of your configured data sources
  - Example: `mep_dev`

#### 3. Time Range
Choose the period of time to analyze.

- **Since** (required): The start time
  - Example: `2015-01-10T00:00:00`
- **Until** (required): The end time
  - Example: `2015-02-28T23:59:59`
- **Timezone** (required): The timezone used to interpret and display times
  - Example: `Africa/Nairobi (UTC+03:00)`

#### 4. Patrol and Event Types
Choose which patrols and events to include in the analysis.

- **Patrol Types** (optional): The patrol type(s) to analyze. Enter the "Patrol Types" value for each patrol type — one per field
  - Example: `ecoscope_patrol`
  - Leave empty to include all patrol types
- **Event Types** (optional): The event type(s) to include. Enter the "Event Types" value for each event type — one per field
  - Example: `wildlife_sighting_rep`
  - Leave empty to include all event types
- **Patrol Status** (optional): Analyze only patrols with a certain status
  - Default: `done`
  - Leave empty to include patrols of all statuses
  - Note: Use the exact "value" from EarthRanger, not the display name — check the admin pages listed in Prerequisites if unsure
- **Event State** (optional): Which event states to include (`new`, `active`, `resolved`, `review`)
  - Note: Leave empty to include events of all states

#### 5. Filter Data
Optional spatial and quality filters applied to both patrol observations and events.

- **Bounding Box** (optional): Only include patrol observations and events whose coordinates fall inside this box
  - Default: the whole world (`min_x: -180, max_x: 180, min_y: -90, max_y: 90`)
- **Filter Exact Point Coordinates** (optional): Exclude observations and events recorded at these exact coordinates (e.g., known bad GPS fixes)
  - Default: `(180, 90)`, `(0, 0)`, `(1, 1)`
- **Trajectory Filter** (optional): Drop trajectory segments outside these length / time / speed bounds (e.g., to remove implausible jumps)
  - Defaults: length `0.001–100000 m`, time `1–172800 s`, speed `0.01–500 km/h`
  - Note: Tightening these bounds (e.g., `max_speed_kmhr: 120`) removes GPS artifacts that would otherwise inflate patrol effort

#### 6. Group Data
Configure how data is grouped and split into per-group dashboard views. Leave empty to produce a single map covering all data.

You can add any combination of groupers:

- **Category**: Split by a data attribute
  - Options: `Event Type`, `Patrol Type`, `Patrol Subject`
- **Temporal**: Split by a time period
  - Options include `Year (example: 2024)`, `Month (example: September)`, `Year and Month (example: 2023-01)`, `Day of the week (example: Sunday)`, and more
- **Spatial**: Split by the regions of a spatial feature group configured in your EarthRanger site
  - **Spatial Regions**: Select the spatial feature group to split by
  - Note: Each region in the group becomes its own map view; the grid is calculated separately per region

#### 7. Encounter Rate Map
These settings control the grid-based heatmap showing encounter rate (events per unit of patrol effort in each cell).

- **Measure Events By** (required): What the encounter rate counts in each grid cell
  - `Number of Events` (default): Each event counts as 1
  - `Sum of an Event Field`: Total a numeric event details field instead — for example, summing `Number of Animals` across sighting events measures *animals seen per km* rather than *sightings per km*
- **Event Field to Sum** (appears when "Sum of an Event Field" is selected): The event details field whose values are totaled, using the field title shown in EarthRanger
  - Example: `Number of Animals`
  - Note: The field must exist on the included event types and contain numeric values; events without the field contribute nothing to the total

### Advanced Configuration

These optional settings appear in the "Advanced Configurations" accordion of the Encounter Rate Map section:

- **Minimum Patrol Effort Threshold (km)**: Grid cells with less patrol effort than this render grey instead of being colored by rate
  - Default: `0.2` (200 m)
  - Note: This avoids misleadingly extreme rates in cells that were barely patrolled
- **Grid Cell Size**: `Auto-scale` (default) sizes cells automatically from the extent of your data; `Customize` lets you set an exact size in meters
  - Example: `5000` for 5 km cells; `1000` for a fine 1 km grid
  - Note: Smaller cells give finer detail but take longer to compute and can look sparse
- **Coordinate Reference System**: The CRS in which the grid is built and distances are measured
  - Default: `EPSG:3857`
- **Map Base Layers**: Tile layers used as the map background; the first layer in the list renders on top
  - Default: ArcGIS World Topo Map with semi-transparent World Imagery

---

## Running the Workflow

Once you've configured all the settings:

1. **Review your configuration**
   - Double-check your time range, data source, and patrol/event type values

2. **Save and run**
   - Click the "Submit" and the workflow will show up in "My Workflows" table button in Ecoscope Desktop
   - Click on "Run" and the workflow will begin processing

3. **Monitor progress and wait for completion**
   - You'll see status updates as the workflow runs
   - Processing time depends on:
     - The size of your date range
     - The number of patrols and events in the system
     - The grid cell size (finer grids take longer)
     - The number of groups (each group renders its own map)
   - The workflow completes with status "Success" or "Failed"

---

## Understanding Your Results

After the workflow completes successfully, the dashboard shows a single full-width visualization.

### Encounter Rate Map

- **Format**: Interactive map with a grid overlay
- **Features**:
  - Each grid cell is colored by its encounter rate — the number of events (or the summed event field) per kilometer of patrol effort in that cell
  - Rates are classified into 10 equal-interval bins colored green (low) through yellow to red (high)
  - Cells patrolled less than the Minimum Patrol Effort Threshold render **grey** (legend: `< 200 m patrol effort` at the default threshold)
  - Cells with no patrol effort at all are omitted entirely
  - **Interactive hover**: Each cell's tooltip shows its exact rate (e.g., `Events per km`), the event total for the cell (`Events`, or your summed field's name), and `Patrol Effort (km)`
  - Legend (bottom-right) titled with the rate being displayed; north arrow top-left
  - When "Sum of an Event Field" is selected, all labels update automatically — e.g., legend `Number of Animals per km`

### Grouped Outputs

If you configured groupers, the dashboard gains a group selector, and each group (e.g., each month, each patrol type, or each spatial region) gets its own encounter rate map calculated from just that group's patrols and events. Groups that had patrol effort but no events still render, showing an all-zero (green) grid over the patrolled area.

---

## Common Use Cases & Examples

Here are some typical scenarios and how to configure the workflow for each:

### Example 1: Baseline encounter rate map
**Goal**: A single map of event encounters per km of patrol effort over a two-month period

**Configuration**:
- **Time Range**:
  - Since: `2015-01-10T00:00:00`
  - Until: `2015-02-28T23:59:59`
  - Timezone: `Africa/Nairobi (UTC+03:00)`
- **Patrol Types**: `ecoscope_patrol`
- **Patrol Status**: `done`
- **Group Data**: empty
- **Grid Cell Size**: `Customize`, `5000` (5 km cells)

**Result**:
- One full-width map; each 5 km cell colored by events per km patrolled, with barely-patrolled cells grey

---

### Example 2: Monthly comparison
**Goal**: See how encounter rates change month to month

**Configuration**:
- Same as Example 1, plus:
- **Group Data**: Temporal grouper set to `Month (example: September)`

**Result**:
- One map per month (e.g., January, February); months with patrols but no events render an all-zero grid rather than disappearing

---

### Example 3: Animals seen per kilometer
**Goal**: Weight the rate by herd size, not just sighting count

**Configuration**:
- Same as Example 1, plus:
- **Measure Events By**: `Sum of an Event Field`
- **Event Field to Sum**: `Number of Animals` (the field title shown in EarthRanger for your sighting events)

**Result**:
- Cell colors now represent total animals per km of patrol effort; tooltips and the legend re-label automatically (e.g., `Number of Animals per km`)

---

### Example 4: Encounter rates by management sector
**Goal**: Compare encounter rates across the regions of a spatial feature group

**Configuration**:
- Same as Example 1, plus:
- **Group Data**: Spatial grouper with **Spatial Regions** set to your feature group (e.g., `Management Sectors`)

**Result**:
- One map per region; each region's grid is computed from only the patrols and events inside it

---

## Troubleshooting

### Common Issues and Solutions

#### Workflow fails to start
**Problem**: The workflow fails immediately with an authentication or connection error

**Solutions**:
- Verify your EarthRanger data source is configured correctly in Ecoscope Desktop
- Check that your credentials are valid and have permission to read patrols and events
- Confirm the data source name selected in the form matches a configured connection

#### Empty map or "no data" result
**Problem**: The workflow succeeds but the map is empty

**Solutions**:
- Confirm completed patrols of the selected **patrol type** exist within your time range — check `https://<your-site>.pamdas.org/admin/activity/patroltype/` for the exact type value
- Check your **Patrol Status** filter — with the default `done`, open or cancelled patrols are excluded; clear it to include all statuses
- Make sure your **Bounding Box** (if set) actually covers your patrol area
- Widen the time range to confirm data exists at all

#### Wrong or missing patrol/event types
**Problem**: Filtering by a patrol or event type returns nothing, even though the data exists

**Solutions**:
- Use the type's **value**, not its display name — e.g., `wildlife_sighting_rep`, not "Wildlife Sighting"
- Values are case-sensitive and must match exactly
- Look up values in the EarthRanger admin pages listed in Prerequisites

#### "Column not found" error in sum mode
**Problem**: With "Sum of an Event Field" selected, the workflow fails saying the field/column was not found

**Solutions**:
- Enter the field's **title exactly as shown in EarthRanger** event details (e.g., `Number of Animals`), including capitalization
- Confirm the included event types actually carry that field — restrict **Event Types** to the types that do
- If the field is numeric-looking but stored as a choice list, its values may not be summable; pick a numeric field

#### Workflow runs very slowly
**Problem**: The workflow takes a long time to complete

**Solutions**:
- The first run after installation includes a one-time "warm-up" while the workflow environment is prepared; later runs are faster
- Reduce the time range, or use a coarser **Grid Cell Size** (larger cells compute faster than a fine 1 km grid)
- Reduce the number of groupers — each group renders its own map
- Large patrol datasets simply take longer to download; narrow the patrol types if possible

#### Everything renders grey
**Problem**: Most or all grid cells are grey

**Solutions**:
- Grey means the cell received less patrol effort than the **Minimum Patrol Effort Threshold (km)** (default `0.2` km); lower the threshold if your patrols are sparse relative to the cell size
- Use a larger grid cell size so each cell accumulates more patrol effort
- Check the **Trajectory Filter** bounds — overly strict speed/length limits can discard most patrol segments, leaving little recorded effort
