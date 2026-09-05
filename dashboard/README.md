# SwarmSAR live dashboard

A dependency-free web replay of a recorded mission: drones, the live comms
mesh, sensor footprints, the fused survivor map (pending vs. confirmed), and
rescue alerts — with a timeline scrubber and playback speed.

![theme-aware](https://img.shields.io/badge/theme-light%20%2F%20dark-blue)

## Run it

The page loads `run.json` from this folder, so serve the folder (browsers block
`fetch` over `file://`):

```bash
python examples/record_dashboard.py   # regenerate run.json (optional)
python -m http.server -d dashboard 8000
# open http://localhost:8000
```

## Regenerating the data

`examples/record_dashboard.py` runs a mission with `DashboardRecorder` and
writes `dashboard/run.json`. Tweak the swarm size, area, seed, or AI provider
there and re-run to record a new scenario.

## What you see

| Mark | Meaning |
| --- | --- |
| Cyan dot | Drone searching |
| Amber dot | Drone holding station to confirm a sighting |
| Amber ring | Pending estimate (seen, not yet corroborated) |
| Green dot | Confirmed survivor |
| Red pulse | Rescue alert dispatched |
| Hollow grey ring | Ground-truth survivor (hidden from the swarm) |
| Thin lines | Live mesh links between drones |
