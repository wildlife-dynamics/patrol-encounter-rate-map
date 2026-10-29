"""Build synthetic mock-io fixtures for the patrol leg grouper test cases.

Adapted from patrol-encounter-rate-stats' dev/fixtures/build_leg_fixtures.py (itself from
patrol-effort-table's). The data MODEL is
the mep-dev sample pulled on 2026-10-22 (.scratch/sample, never committed): the column set,
dtypes and nesting of the patrols / observations / legs frames an EarthRanger site with the
`patrol_schemas` flag returns. Every ROW here is made up: uuid5 ids, invented ranger / team /
vehicle names, a jittered straight-line track. Only the patrol-type slug (`ecoscope_leg_test`,
org config) and the two event-type slugs (from the packaged 2015 fixture's model) are real.

EVENTS: the seeded mep-dev legs carry none, so each leg's nested `patrol_segments[].events`
gets planted events in the exact shape the packaged `get-patrols` fixture nests them
(`unpack_events_from_patrols_df` is not an io task; it unpacks whichever patrols fixture is in
play). This workflow then passes the unpacked events through the io task
`get_event_type_display_names_from_events`, whose mock returns the packaged 2015 events, so
the leg cases also override it with `events-display-names.parquet`: the planted events
unpacked by the library's own task plus `event_type_display`, in the packaged return's column
order.

PATROL TYPE DISPLAY NAMES: `add_patrol_type_display_names` (io) runs on the leg frame; its
fixture `legs-type-display-names.parquet` rewrites `patrol_type` to the display name and keeps
the slug in `patrol_type__value` (flag-off: "Ecoscope Patrol" for the packaged `ecoscope_patrol`).

Planted shape (what the test cases assert):
- 2 patrols, 3 legs: 08-12 and 13-16 on 2026-01-05 (patrol 1001), 09-11 on 2026-01-06
  (patrol 1002) -> Active Duration 4+3+2 = 9 h, Elapsed 8 h + 2 h = 10 h, Leg Count 3; every
  leg has the same 2 members and 1 asset -> Member-days 2*3 = 6, one Team, a Member fan-out
  of two.
- one fix every 10 minutes per leg (25 + 19 + 13 = 57) walking east along lat -1.4, so the
  trajectory timespan equals the leg duration (9 h in total) and a north-south boundary
  splits the track length ~3:1 between the two polygons of the `LegTestRegions` spatial
  feature group (West / East).
- 9 events on the legs' tracks (4 + 2 + 3), at track fractions that put 6 in West and 3 in
  East; two event types.
- flag-off fixtures: the leg frames the library builds from the PACKAGED 2015 patrols fixture
  (no team / member / asset keys -> name columns "None", Member-days NaN), so the flag-off
  cases keep today's numbers and exercise the "None" path.
- empty variants of every frame (schema, zero rows).

Legs are derived from the nested `patrol_segments` with the library's own
`patrol_segments_from_patrols_df`, so the leg schema is the library's, not this script's.

Run from the inner workflow env (after the editable compile):
    cd ecoscope-workflows-patrol-encounter-rate-map-workflow
    pixi run --frozen python ../dev/fixtures/build_leg_fixtures.py
"""

import json
import uuid
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point, box

from ecoscope.io.earthranger_utils import patrol_segments_from_patrols_df
from ecoscope.platform.tasks.filter import TimeRange, TimezoneInfo
from ecoscope.platform.tasks.io import unpack_events_from_patrols_df
from wt_task.testing import create_func_magicmock

OUT = Path(__file__).resolve().parent
LEGS_DIR, OFF_DIR, EMPTY_DIR = OUT / "legs", OUT / "flag-off", OUT / "empty"
RNG = np.random.default_rng(20261023)


def fake_id(name: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"patrol-encounter-rate-map-fixture/{name}"))


SLUG, DISPLAY = "ecoscope_leg_test", "Ecoscope Leg Test"
TYPE_ID = fake_id("patrol-type/ecoscope_leg_test")
TEAM = ("Leg Test Team", fake_id("team/leg-test"))
MEMBERS = [("Ranger Amani", fake_id("subject/amani")), ("Ranger Baraka", fake_id("subject/baraka"))]
ASSET = ("Patrol Vehicle 1", fake_id("subject/vehicle-1"))
LEADER = MEMBERS[0]
SOURCE_ID = fake_id("source/amani-radio")
TENANT_ID = fake_id("tenant")
CREATED = "2026-01-02T08:00:00.000000Z"
SITE = "https://example.invalid"

# (serial, [(start, end), ...]) — one patrol per day, legs in UTC
PATROLS = [
    (1001, [("2026-01-05T08:00:00Z", "2026-01-05T12:00:00Z"), ("2026-01-05T13:00:00Z", "2026-01-05T16:00:00Z")]),
    (1002, [("2026-01-06T09:00:00Z", "2026-01-06T11:00:00Z")]),
]
# Events per leg as (track fraction, event_type); fractions < 0.75 fall West of the
# spatial boundary, so West gets 6 events and East 3.
EVENTS = [
    [(0.10, "wildlife_sighting_rep"), (0.30, "poacher_camp_rep"), (0.50, "wildlife_sighting_rep"), (0.90, "poacher_camp_rep")],
    [(0.20, "wildlife_sighting_rep"), (0.80, "wildlife_sighting_rep")],
    [(0.15, "poacher_camp_rep"), (0.50, "wildlife_sighting_rep"), (0.85, "wildlife_sighting_rep")],
]
LAT0, LON_START, LON_STEP, LEG_LON_OFFSET = -1.40, 36.90, 0.0045, 0.04
FIX_MINUTES = 10


def leader_dict() -> dict:
    return {
        "content_type": "observations.subject",
        "id": LEADER[1],
        "name": LEADER[0],
        "subject_type": "person",
        "subject_subtype": "ranger",
        "common_name": None,
        "additional": None,
        "created_at": CREATED,
        "updated_at": CREATED,
        "is_active": True,
        "user": None,
        "tracks_available": False,
        "image_url": "/static/ranger-black.svg",
    }


def leg_geometry(leg_no: int, start: str, end: str):
    """Fix times and eastward positions of one leg's track (shared by observations and events)."""
    times = pd.date_range(start, end, freq=f"{FIX_MINUTES}min", tz="UTC")
    n = len(times)
    lons = LON_START + leg_no * LEG_LON_OFFSET + LON_STEP * np.arange(n)
    return times, lons


def event_dict(leg_no: int, k: int, serial: int, start: str, end: str, fraction: float, event_type: str) -> dict:
    times, lons = leg_geometry(leg_no, start, end)
    pos = int(round(fraction * (len(lons) - 1)))
    when = times[pos] + pd.Timedelta(minutes=3)
    lon, lat = float(lons[pos]), float(LAT0 + RNG.normal(0, 0.0004))
    icon = f"{SITE}/static/{event_type.removesuffix('_rep')}-gray.svg"
    return {
        "id": fake_id(f"event/{serial}/{leg_no}/{k}"),
        "serial_number": 90000 + 10 * leg_no + k,
        "event_type": event_type,
        "priority": 0,
        "state": "new",
        "title": event_type,
        "is_collection": False,
        "contains": [],
        "patrol_type": SLUG,
        "created_at": when.strftime("%Y-%m-%d %H:%M:%S.%f"),
        "updated_at": when.strftime("%Y-%m-%d %H:%M:%S.%f"),
        "geojson": {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": {
                "datetime": when.isoformat(),
                "icon": {"className": "dot", "iconAncor": [12, 12], "iconSize": [25, 25], "iconUrl": icon, "popupAncor": [0, -13]},
                "image": icon,
                "message": "",
            },
        },
    }


def build_patrols() -> pd.DataFrame:
    rows = []
    leg_no = 0
    for serial, legs in PATROLS:
        patrol_id = fake_id(f"patrol/{serial}")
        segments = []
        for k, (start, end) in enumerate(legs):
            segments.append(
                {
                    "id": fake_id(f"segment/{serial}/{k}"),
                    "patrol_type": SLUG,
                    "leader": leader_dict(),
                    "scheduled_start": None,
                    "scheduled_end": None,
                    "time_range": {"start_time": start, "end_time": end},
                    "start_location": None,
                    "end_location": None,
                    "events": [
                        event_dict(leg_no, j, serial, start, end, frac, etype) for j, (frac, etype) in enumerate(EVENTS[leg_no])
                    ],
                    "team": TEAM[1],
                    "members": [m[1] for m in MEMBERS],
                    "assets": [ASSET[1]],
                    "segment_details": {"weather": "dry"},
                    "type_details": None,
                    "is_pause": False,
                    "image_url": f"{SITE}/static/sprite-src/generic_rep.svg",
                    "icon_id": "generic_rep",
                    "updates": [],
                }
            )
            leg_no += 1
        rows.append(
            {
                "id": patrol_id,
                "priority": 0,
                "state": "done",
                "objective": None,
                "serial_number": serial,
                "title": f"Leg test patrol {serial}",
                "files": [],
                "notes": [],
                "patrol_segments": segments,
                "updates": [],
            }
        )
    return pd.DataFrame(rows)


def build_observations(patrols: pd.DataFrame) -> gpd.GeoDataFrame:
    frames = []
    leg_no = 0
    for _, patrol in patrols.iterrows():
        p_start = min(s["time_range"]["start_time"] for s in patrol["patrol_segments"])
        p_end = max(s["time_range"]["end_time"] for s in patrol["patrol_segments"])
        for seg in patrol["patrol_segments"]:
            times, lons = leg_geometry(leg_no, seg["time_range"]["start_time"], seg["time_range"]["end_time"])
            n = len(times)
            lats = LAT0 + RNG.normal(0, 0.0004, size=n)
            frames.append(
                gpd.GeoDataFrame(
                    {
                        "extra__id": [fake_id(f"obs/{seg['id']}/{i}") for i in range(n)],
                        "extra__location": [{"latitude": float(y), "longitude": float(x)} for x, y in zip(lons, lats)],
                        "extra__created_at": pd.Timestamp(CREATED, tz="UTC"),
                        "extra__recorded_at": times,
                        "extra__source": SOURCE_ID,
                        "extra__exclusion_flags": 0,
                        "extra__subject_id": LEADER[1],
                        "groupby_col": patrol["id"],
                        "fixtime": times,
                        "junk_status": False,
                        "patrol_id": patrol["id"],
                        "patrol_title": patrol["title"],
                        "patrol_serial_number": int(patrol["serial_number"]),
                        "patrol_start_time": pd.Timestamp(p_start, tz="UTC"),
                        "patrol_end_time": pd.Timestamp(p_end, tz="UTC"),
                        "patrol_type": TYPE_ID,
                        "patrol_status": "done",
                        "patrol_subject": LEADER[0],
                        "patrol_segment_id": seg["id"],
                        "patrol_team": seg["team"],
                        "patrol_members": [list(seg["members"])] * n,
                        "patrol_assets": [list(seg["assets"])] * n,
                        "patrol_segment_details": json.dumps(seg["segment_details"]),
                        "patrol_type_details": json.dumps({}),
                        "patrol_type__value": SLUG,
                        "patrol_type__display": DISPLAY,
                        "patrol_type__icon": "",
                    },
                    geometry=[Point(x, y) for x, y in zip(lons, lats)],
                    crs=4326,
                )
            )
            leg_no += 1
    return gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), crs=4326)


EVENT_TYPE_DISPLAY = {"wildlife_sighting_rep": "Wildlife Sighting", "poacher_camp_rep": "Poachers Camp"}
TIME_RANGE = TimeRange(
    since=pd.Timestamp("2026-01-05T00:00:00Z"),
    until=pd.Timestamp("2026-01-07T00:00:00Z"),
    timezone=TimezoneInfo(label="UTC (UTC+00:00)", tzCode="UTC", name="(UTC+00:00) UTC", utc="+00:00"),
)


def name_chain(legs: pd.DataFrame, team_names: dict, subject_names: dict, type_display: dict) -> dict[str, pd.DataFrame]:
    """The three io name tasks' returns, each = its input + the columns it adds (mock chains)."""
    team = legs.copy()
    if "patrol_team" in team.columns:
        team["patrol_team_name"] = team["patrol_team"].map(lambda t: "None" if pd.isna(t) else team_names.get(t, t))
    else:
        team["patrol_team_name"] = "None"
    roster = team.copy()
    for src, dst in {"patrol_members": "patrol_member_names", "patrol_assets": "patrol_asset_names"}.items():
        roster[dst] = roster[src].map(lambda ids: [subject_names.get(i, i) for i in list(ids)]) if src in roster.columns else "None"
    display = roster.copy()
    display["patrol_type__value"] = display["patrol_type"]
    display["patrol_type"] = display["patrol_type"].map(lambda v: type_display.get(v, v))
    return {"legs-team-names": team, "legs-roster-names": roster, "legs-type-display-names": display}


def build_events_display_names(patrols: pd.DataFrame) -> gpd.GeoDataFrame:
    """get_event_type_display_names_from_events' return for the planted events: the library's own
    unpack (same call the workflow makes) plus event_type_display, columns in the packaged order."""
    events = unpack_events_from_patrols_df(
        patrols_df=patrols,
        event_types=[],
        time_range=TIME_RANGE,
        include_null_geometry=False,
        truncate_to_time_range=True,
        raise_on_empty=False,
    )
    events["event_type_display"] = events["event_type"].map(EVENT_TYPE_DISPLAY)
    packaged = create_func_magicmock(anchor="ecoscope.platform.tasks.io", func_name="get_event_type_display_names_from_events")()
    missing = [c for c in packaged.columns if c not in events.columns]
    assert not missing, f"unpacked events lack packaged columns {missing}"
    return gpd.GeoDataFrame(events[list(packaged.columns)], geometry="geometry", crs=4326)


def build_spatial_features(obs: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    # boundary such that ~75% of the eastward track length lies West of it
    lon = obs.geometry.x
    spans = obs.groupby("patrol_segment_id").agg(lo=("geometry", lambda g: g.x.min()), hi=("geometry", lambda g: g.x.max()))
    total = (spans.hi - spans.lo).sum()
    boundary = (0.75 * total + spans.lo.sum()) / len(spans)  # every leg crosses it (checked below)
    assert ((spans.lo < boundary) & (spans.hi > boundary)).all(), "boundary must cut every leg"
    south, north = float(obs.geometry.y.min()) - 0.05, float(obs.geometry.y.max()) + 0.05
    west, east = float(lon.min()) - 0.05, float(lon.max()) + 0.05
    polys = {"West": box(west, south, boundary, north), "East": box(boundary, south, east, north)}
    group_id = fake_id("spatial-feature-group/leg-test-regions")
    return gpd.GeoDataFrame(
        {
            "created_at": CREATED,
            "updated_at": CREATED,
            "feature_type": fake_id("feature-type/region"),
            "name": list(polys),
            "short_name": "",
            "external_id": None,
            "external_source": "",
            "description": "",
            "feature_geometry_webmercator": None,
            "spatialfile": None,
            "arcgis_item": None,
            "das_tenant": TENANT_ID,
            "pk": [fake_id(f"spatial-feature/{n}") for n in polys],
            "metadata": [{"display_name": "LegTestRegions", "id": group_id}] * len(polys),
        },
        geometry=list(polys.values()),
        crs=4326,
    )


def write(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def main() -> None:
    patrols = build_patrols()
    obs = build_observations(patrols)
    legs = patrol_segments_from_patrols_df(patrols)
    names = name_chain(
        legs, team_names={TEAM[1]: TEAM[0]}, subject_names={i: n for n, i in MEMBERS + [ASSET]}, type_display={SLUG: DISPLAY}
    )
    events_display = build_events_display_names(patrols)
    spatial = build_spatial_features(obs)
    boundary = spatial.geometry.iloc[0].bounds[2]
    events = [e for segs in patrols.patrol_segments for s in segs for e in s["events"]]
    west_events = sum(e["geojson"]["geometry"]["coordinates"][0] < boundary for e in events)

    write(patrols, LEGS_DIR / "patrols.parquet")
    write(obs, LEGS_DIR / "observations.parquet")
    write(legs, LEGS_DIR / "legs.parquet")
    for stem, frame in names.items():
        write(frame, LEGS_DIR / f"{stem}.parquet")
    write(spatial, LEGS_DIR / "spatial-features.parquet")
    write(events_display, LEGS_DIR / "events-display-names.parquet")

    # flag-off: the library's leg frame over the PACKAGED 2015 patrols fixture
    packaged = create_func_magicmock(anchor="ecoscope.platform.tasks.io", func_name="get_patrols_from_combined_params")()
    off_legs = patrol_segments_from_patrols_df(
        packaged, since=pd.Timestamp("2015-01-10T00:00:00Z"), until=pd.Timestamp("2015-02-28T23:59:59Z")
    )
    write(off_legs, OFF_DIR / "legs.parquet")
    for stem, frame in name_chain(off_legs, {}, {}, {"ecoscope_patrol": "Ecoscope Patrol"}).items():
        write(frame, OFF_DIR / f"{stem}.parquet")

    for stem, frame in {"patrols": patrols, "observations": obs, "legs": legs, "events-display-names": events_display, **names}.items():
        write(frame.iloc[0:0], EMPTY_DIR / f"{stem}.parquet")

    print(
        f"patrols {len(patrols)}, observations {len(obs)}, legs {len(legs)}, events {len(events)} "
        f"({west_events} West / {len(events) - west_events} East of lon {boundary:.4f}; "
        f"{len(events_display)} unpacked with display names); "
        f"active {legs.leg_active_seconds.sum() / 3600:g} h, elapsed {legs.patrol_elapsed_seconds.sum() / 3600:g} h, "
        f"member-days {legs.leg_member_days.sum():g}; flag-off legs {len(off_legs)}"
    )


if __name__ == "__main__":
    main()
