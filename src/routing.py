import numpy as np
import requests
import time
import folium
import matplotlib.colors as colors
import matplotlib.cm as cm
from sklearn.neighbors import BallTree


# --------------------------------------------------
# BallTree: compute the k nearest center candidates 
# to each point using the Haversine metric
# --------------------------------------------------

def get_candidate_centers(
    df_points,
    df_centers,
    lat_col_points,
    lon_col_points,
    lat_col_centers,
    lon_col_centers,
    k
):

    if k is None:
        return np.tile(np.arange(len(df_centers)), (len(df_points), 1))

    centers_rad = np.radians(
        np.c_[df_centers[lat_col_centers], df_centers[lon_col_centers]]
    )

    tree = BallTree(centers_rad, metric="haversine")

    points_rad = np.radians(
        np.c_[df_points[lat_col_points], df_points[lon_col_points]]
    )

    _, candidate_idx = tree.query(points_rad, k=k)

    return candidate_idx


# --------------------------------------------------
# OSRM table request: coonects with the OSMR API 
# and returns the durations matrix
# --------------------------------------------------

def osrm_table_request(coords, n_sources, osrm_url, profile, timeout):

    coord_string = ";".join([f"{lon},{lat}" for lon, lat in coords])

    url = f"{osrm_url}/table/v1/{profile}/{coord_string}"

    params = {
        "sources": ";".join(map(str, range(n_sources))),
        "destinations": ";".join(map(str, range(n_sources, len(coords))))
    }

    r = requests.get(url, params=params, timeout=timeout)
    data = r.json()

    return data["durations"]


# --------------------------------------------------
# Createns the maps using Folium
# --------------------------------------------------

def create_maps(
    df_points,
    df_centers,
    lat_col_points,
    lon_col_points,
    lat_col_centers,
    lon_col_centers,
    name_col_points,
    name_col_centers,
    map_zoom,
    center_icon
):

    geographical_center = [
        df_points[lat_col_points].mean(),
        df_points[lon_col_points].mean(),
    ]

    # ----------------------------------
    # MAP 1: travel time from each
    # point to the nearest center
    # ----------------------------------

    map1 = folium.Map(location=geographical_center, zoom_start=map_zoom)

    vmin = df_points["travel_time_min"].quantile(0.015)
    vmax = df_points["travel_time_min"].quantile(0.985)

    norm = colors.Normalize(vmin=vmin, vmax=vmax)

    cmap = cm.get_cmap("viridis")

    for _, row in df_centers.iterrows():

        folium.Marker(
            location=[row[lat_col_centers], row[lon_col_centers]],
            icon=folium.Icon(color="red", icon=center_icon, prefix="fa"),
            tooltip=f"{row[name_col_centers]}"
        ).add_to(map1)

    for _, row in df_points.iterrows():

        color = colors.to_hex(cmap(norm(row["travel_time_min"])))

        folium.CircleMarker(
            location=[row[lat_col_points], row[lon_col_points]],
            radius=4,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.9,
            tooltip=(
                f"{row[name_col_points]}<br>"
                f"Nearest center: {row['nearest_center']}<br>"
                f"{row['travel_time_min']:.0f} min"
            ),
        ).add_to(map1)

    # -----------------------------------------------
    # MAPA 2: regions sharing common nearest center
    # -----------------------------------------------

    map2 = folium.Map(location=geographical_center, zoom_start=map_zoom)

    centers = df_points["nearest_center"].unique()

    cmap_regions = cm.get_cmap("tab20", len(centers))

    center_colors = {
        ct: colors.to_hex(cmap_regions(i))
        for i, ct in enumerate(centers)
    }

    # centers

    for _, row in df_centers.iterrows():

        ct = row[name_col_centers]

        if ct in center_colors:
            color = center_colors[ct]
        else:
            color = "black"

        folium.Marker(
            location=[row[lat_col_centers], row[lon_col_centers]],
            icon=folium.DivIcon(
                html=f"""
                <div style="
                    font-size:20px;
                    color:{color};
                ">
                    <i class="fa fa-{center_icon}"></i>
                </div>
                """
            ),
            tooltip=f"{ct}"
        ).add_to(map2)

    # municipalities

    for _, row in df_points.iterrows():

        color = center_colors[row["nearest_center"]]

        folium.CircleMarker(
            location=[row[lat_col_points], row[lon_col_points]],
            radius=3,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.9,
            tooltip=(
                f"{row[name_col_points]}<br>"
                f"Nearest center: {row['nearest_center']}<br>"
                f"{row['travel_time_min']:.0f} min"
            ),
        ).add_to(map2)

    return map1, map2


# --------------------------------------------------
# MAIN FUNCION: nearest_center_osrm
# --------------------------------------------------

def nearest_center_osrm(
    df_points,
    df_centers,
    lon_col_points="lon",
    lat_col_points="lat",
    lon_col_centers="lon",
    lat_col_centers="lat",
    name_col_points="name",
    name_col_centers="name",
    batch_size=100,
    k=5,
    osrm_url="http://router.project-osrm.org",
    profile="driving",
    sleep=0.05,
    timeout=20,
    verbose=True,
    make_map=False,
    map_zoom=7,
    center_icon="star"
):
    
    """
    Assign each point to the nearest center based on **travel time** computed using the OSRM routing engine.
    Optionally generates interactive maps showing accessibility patterns.

    Parameters
    ----------
    df_points : pandas.DataFrame
        DataFrame containing the origin locations (points).

    df_centers : pandas.DataFrame
        DataFrame containing the candidate destination locations (centers).

    lon_col_points : str, default="lon"
        Longitude column in `df_points`.

    lat_col_points : str, default="lat"
        Latitude column in `df_points`.

    lon_col_centers : str, default="lon"
        Longitude column in `df_centers`.

    lat_col_centers : str, default="lat"
        Latitude column in `df_centers`.

    name_col_points : str, default="name"
        Column used to label points.

    name_col_centers : str, default="name"
        Column used to label centers.

    batch_size : int, default=100
        Number of points processed per OSRM request.

    k : int or None, default=5
        Number of geographically closest candidate centers evaluated with BallTree.
        If None, all centers are evaluated.

    osrm_url : str, default="http://router.project-osrm.org"
        URL of the OSRM routing service.

    profile : str, default="driving"
        Routing profile used by OSRM (e.g. "driving", "walking", "cycling").

    sleep : float, default=0.0
        Optional delay between OSRM requests.

    timeout : int, default=20
        Maximum time (seconds) to wait for OSRM responses.

    verbose : bool, default=True
        Print progress information during batch processing.

    make_map : bool, default=False
        If True, generate two Folium maps.

    map_zoom : int, default=7
        Initial zoom level of the generated maps.

    center_icon : str, default="star"
        FontAwesome icon used to represent centers ("star", "hospital", "flag", "building").

    Returns
    -------
    pandas.DataFrame
        Original dataframe with two additional columns:
        `nearest_center` and `travel_time_min`.

    or

    pandas.DataFrame, folium.Map, folium.Map
        DataFrame plus two interactive maps if `make_map=True`.
    """




    # Lon / Lat column names validation for df_points / df_centers

    if lon_col_points not in df_points.columns or lat_col_points not in df_points.columns:
        raise ValueError("df_points must contain longitude and latitude columns")

    if lon_col_centers not in df_centers.columns or lat_col_centers not in df_centers.columns:
        raise ValueError("df_centers must contain longitude and latitude columns")

    df_points = df_points.copy()
    df_centers = df_centers.copy()

    # Create name for each point / center 
    # (just in case the specified name or the default name does not match with any column in the DataFrame)

    if name_col_points not in df_points.columns:
        df_points[name_col_points] = [f"point_{i}" for i in range(len(df_points))]

    if name_col_centers not in df_centers.columns:
        df_centers[name_col_centers] = [f"center_{i}" for i in range(len(df_centers))]

    # BallTree for getting the k nearest candidates

    candidate_idx = get_candidate_centers(
        df_points,
        df_centers,
        lat_col_points,
        lon_col_points,
        lat_col_centers,
        lon_col_centers,
        k
    )

    nearest_center = []
    travel_time = []

    n_points = len(df_points)

    # batching for reducing the number of requests (it makes the function faster)

    for start in range(0, n_points, batch_size):

        end = min(start + batch_size, n_points)

        if verbose:
            print(f"\nBatch {start+1}–{end} (out of {n_points})")

        batch_points = df_points.iloc[start:end]
        batch_candidates = candidate_idx[start:end]

        batch_points_coords = list(
            zip(batch_points[lon_col_points], batch_points[lat_col_points])
        )

        unique_centers = np.unique(batch_candidates)

        centers_subset = df_centers.iloc[unique_centers]

        centers_coords = list(
            zip(centers_subset[lon_col_centers], centers_subset[lat_col_centers])
        )

        centers_names = centers_subset[name_col_centers].values

        coords = batch_points_coords + centers_coords

        try:

            durations = osrm_table_request(
                coords,
                len(batch_points_coords),
                osrm_url,
                profile,
                timeout
            )

        except Exception as e:

            if verbose:
                print("OSRM error:", e)

            durations = [[1e9] * len(centers_coords) for _ in batch_points_coords]

        for i, row in enumerate(durations):

            row = [d if d is not None else 1e9 for d in row]

            min_idx = int(np.argmin(row))

            nearest = centers_names[min_idx]
            time_min = row[min_idx] / 60

            nearest_center.append(nearest)
            travel_time.append(time_min)

        if sleep > 0:
            time.sleep(sleep)

    df_points["nearest_center"] = nearest_center
    df_points["travel_time_min"] = travel_time

    if make_map:

        map1, map2 = create_maps(
            df_points,
            df_centers,
            lat_col_points,
            lon_col_points,
            lat_col_centers,
            lon_col_centers,
            name_col_points,
            name_col_centers,
            map_zoom,
            center_icon
        )

        return df_points, map1, map2

    return df_points