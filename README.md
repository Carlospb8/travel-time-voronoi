# Voronoi Regions in the Real World: Travel-Time Accessibility

This project explores how classical **Voronoi regions** change when distance is replaced by **travel time on a road network**.

Traditional Voronoi diagrams partition space by assigning each location to the nearest center using **Euclidean distance**. However, real-world accessibility depends on **transport networks**, not straight-line distance.

This repository demonstrates how to redefine Voronoi regions using **routing-based travel times**, applied to real geographic datasets from Spain.

---

## Methodology

The workflow combines spatial indexing and routing:

1. **BallTree (Haversine distance)**  
   Identify the *k* geographically closest candidate centers.

2. **OSRM Routing API**  
   Compute actual **travel times along the road network**.

3. **Minimum travel time assignment**  
   Each point is assigned to the center with the shortest travel time.  
   This is performed by the function `nearest_center_osrm()`, which computes routing-based travel times and selects the center with the minimum travel time for each point.

4. **Visualization**  
   Interactive maps are generated using **Folium**.

---

## Case Studies

### 1. Nearest Provincial Capital in Spain

Each **municipality** is treated as a point, and **provincial capitals** are treated as centers.

The goal is to determine which capital is **closest in travel time**, not distance.

This produces **travel-time Voronoi regions of provincial capitals**.

---

### 2. Accessibility to Hospitals in Castilla-La Mancha

Each **municipality** is treated as a point, and **hospitals** are treated as centers.

Travel times are used to evaluate **healthcare accessibility**, including:

- population living beyond certain travel-time thresholds
- spatial accessibility inequalities

---

## Repository Structure
