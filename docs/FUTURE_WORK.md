# Future work

What GAIA does not yet do, why, and what it would take. Written for whoever
picks this up after the project — a successor team, a contributor, or a funder
assessing scope.

The project delivered a working end-to-end pipeline and a QGIS plugin that
project participants described as usable. It did **not** deliver the full user
experience that was designed, validated with the participating municipalities,
and documented in the final report (*Slutrapport GAIA*, Arbetspaket 5 – Bilaga
4: Skisser Användargränssnitt). Closing that gap is the largest single body of
remaining work, and the comparison step is the largest part of it.

Effort sizes are **indicative only** — S = days, M = weeks, L = months for one
developer. They are estimates made from reading the code, not from planning
sessions.

## Where things stand

Working today, end to end:

- Install the plugin from ZIP; configure backend URL, GeoServer URL and API key
- Create a project; create a run with an area, a confidence level, an overlap
  and a set of object types
- Backend tiles imagery from a WMS, segments each tile, merges, vectorises,
  merges GeoPackages and applies the confidence threshold
- Poll run status; download results; layers load into QGIS

The shape of that flow is **fill in a form, press Kör, wait, download a ZIP**.
The designed flow is a **four-step wizard where the user makes decisions between
stages**. That difference drives most of this document.

## 1. Complete the run wizard

The designed flow (report, Bild 5–9):

```
Steg 1                Steg 2                   Steg 3                  Steg 4
Sätt parametrar  -->  Filtrera segmentering -->  Jämför med baskarta -->  Vektorisering
                                            \                          /
                                             \--- (skip comparison) --/
```

Each step shows results on the map, takes user input, and estimates remaining
runtime. Today only Steg 1 exists, and the pipeline runs to completion without
stopping.

### 1.0 Enabling work: interactive, resumable runs — **L**

**This is the keystone. Almost everything below depends on it.**

`Dispatcher.get_next_tasks()` (`app/service/dispatcher.py`) walks a run's tasks
in `task_type.order` and executes until none remain. There is no concept of a
run that pauses, surfaces intermediate output, waits for a decision, and
continues.

The primitives are already half-present and unused: `RunTypesEnum` defines
`SegmentArea`, `CompareToBaseImage` and `Vectorize` alongside `RunItAll`, but
`gaia_client/use_cases/create_project_run.py` hardcodes `RunItAll` and no UI
offers a choice. The decomposition was anticipated during design and never
wired up.

Needed:

- A run state that means *waiting for user input* — distinct from `RUNNING`,
  `FINISHED` and `ERROR`, so the poller does not treat it as stalled
- Endpoints to read intermediate results and to resume a run with decisions
  attached (per-class thresholds, which change classes to vectorise)
- Persisting user decisions against the run so a resumed run is reproducible and
  auditable
- Client-side wizard navigation and a stepper component
  (`gaia_client/ui/utils/router.py` currently switches whole views)

Design decision to make early: **does the run pause server-side, or does the
client orchestrate a sequence of separate runs?** Pausing keeps one run object
and one audit trail; orchestration is simpler to build but fragments a logical
job across several run records and complicates the "Starta ny körning" flow.

### 1.1 Steg 2 — post-segmentation confidence filtering — **M**

*Designed (Bild 7):* per object class, a collapsible panel with a confidence
**slider** (60–100) and a *Ta med till nästa steg* Ja/Nej choice. The map
updates to show what survives the threshold. A runtime estimate is shown. The
user then chooses **Jämför med baskarta** or **Vektorisera** (skip comparison).

*Today:* one global confidence number entered before the run starts, applied
once at the end by the `ApplyConfidence` task. No interactive re-thresholding.

This is where the model's continuous output earns its keep — segmentation emits
a 0–255 likelihood raster, so re-thresholding does **not** require re-running
inference. The data model already supports what the UX needs.

Needed:

- Per-class confidence instead of a single `confidence_level` in run attributes
  (`app/usecase/create_project_run.py:180` validates one scalar today)
- An endpoint returning the segmentation result for display before vectorisation
- Client: slider widget, per-class panels, map preview of the thresholded mask
- The branch choice, which is the first real use of the run-type decomposition

### 1.2 Steg 3 — Differentiering (comparison with basemap) — **L**

**The largest missing piece.** Nothing exists client-side: no basemap concept,
no diff view, no strings in `gaia_client/ui/i18n/se.py`.

*Designed (Bild 8):* per object class, the detected changes are grouped into
four classes, each independently selectable for vectorisation:

| Change class | Meaning |
|---|---|
| Nytt objekt | Present in imagery, absent from the basemap |
| Tillbyggnad på objekt | Existing object has grown |
| Borttaget objekt | In the basemap, no longer in imagery |
| Borttagen del av objekt | Existing object has shrunk |

Each has a *Vektorisera* Ja/Nej control and an `(i)` explanation. The map
renders each change class with its own symbol and colour, with a legend. A
runtime estimate precedes a confirm dialog, then a progress dialog.

#### The comparison interface cannot register today

Before any UI work, a blocking defect: `gaia-engine/comparison/model.json`
declares `"group": "Comparison"`, but only three groups are seeded —
`Classification`, `Vectorization` and `Internal` (see
`app/alembic/versions/2841b1f32f5f_*` and `e0a9b5baf59e_*`).
`InterfaceService.add_new_interface()` looks the group up and returns early when
it is missing:

```python
segmentation_group = self.interface_repository.get_group_by_name(interface.definition.group)
if segmentation_group is None:
    logger.error(f"Interface {interface.name} does not have a valid group, ...")
    return
```

So the comparison engine module builds its virtual environment on every start
and then silently fails to register. It is unreachable at every layer: no group,
no interface row, no run type sent, no UI.

**Fix first (S):** add a `Comparison` group in a migration, or align the
`model.json` to an existing group. Confirm the interface then appears in
`GET /status/interfaces`. This unblocks everything else in this section.

#### The missing data contract

The engine's comparison modules (`building_tile_comparer.py`,
`road_tile_comparer.py`, `comparer_v1.py`) work on rasters and produce raster
output. The UX needs a **per-feature classified change set** — geometry plus a
change class plus a confidence — that the client can render, filter and
selectively pass to vectorisation.

That translation layer does not exist and is the substantial engineering task
here, larger than the UI itself.

#### Known accuracy limits — the UX should reflect them

The report is explicit that two of the four change classes are weak
(Arbetspaket 3):

- Detecting **new** and **removed** buildings *"fungerar relativt bra"*
- Detecting **modified** buildings (tillbyggnad) *"fungerar mindre bra"*
- Road comparison is approximate: basemaps store roads as **lines** while
  segmentation produces **surfaces**, so the comparison can only judge whether a
  detected road lies near a mapped line. Asphalt paths and car parks cannot be
  distinguished from roads.

A UI that presents all four change classes as equally trustworthy would
misrepresent the system. Consider surfacing a confidence in the *change
classification* itself, separate from segmentation confidence, and treating
roads differently from buildings.

Needed:

- `Comparison` interface group (above)
- Basemap ingestion and association (section 2)
- Per-feature change classification output from the engine
- Endpoint exposing the change set; endpoint accepting per-class selections
- Client: diff view, per-class controls, map symbology and legend, `(i)`
  explanations

### 1.3 Steg 4 — Vectorisation and summary — **M**

*Designed (Bild 9):* a preview of generated vectors on the map, and a summary
panel — Namn, Datum, Min. konfidensnivå, Område, object types with their
per-class confidence, and classes included. A *Starta ny körning* button repeats
the setup.

*Today:* the run finishes, the user downloads a ZIP, and layers appear in QGIS.
There is no in-plugin preview and no summary.

The summary is largely presentation over data the backend already holds; the
preview needs vector geometry available before download.

### 1.4 Runtime estimation and confirmation — **M**

Every designed step shows *Körtid* and confirms before long operations
(*"Körtiden är beräknad till 3 h 45 min"*), then shows progress with a cancel.

Today there is no estimate anywhere. Work scales with the **area** of the
bounding box, and the tile count is not known until tiling completes — which is
why `ProjectRunStatus` has a `calculating` flag.

A usable first estimate can be derived from tile count × measured per-tile time
per class, refined as the run proceeds. Note that only one step runs at a time
across the whole server (section 6), so a queued run's estimate must include
waiting for whatever is ahead of it.

## 2. Basemap support and object-type mapping — **L**

Three designed capabilities, none implemented:

**Basemap on the project (Bild 1–2).** Projects should carry paths to an
orthophoto and a basemap. Today a project is name + description, and the data
source is a free-text field on the run form. Prerequisite for all of Steg 3.

**Object-type mapping (Bild 3).** A drag-and-drop mapping from the municipality's
own basemap classes onto GAIA's standard types (Byggnader, Vägar, …). This is
what makes the tool reusable across municipalities with different data models —
the report identifies exactly this heterogeneity as the central obstacle
(Arbetspaket 2: *"det krävs homogena träningsdata"*).

**Layer semantics.** Roads as lines vs surfaces (section 1.2) is a mapping
problem as much as a comparison problem.

## 3. Expose engine parameters — **M**

*Designed (Bild 4):* per object class, controls for minimum area, shortest edge,
simplification and tolerance.

Those parameters exist and are already tuned per class — `min_area`,
`smallest_hole`, `shortest_edge`, `gap_closure`, `sigma`, smoothing,
simplification — but live in engine configuration
(`gaia-engine/vectorisation/`, see `config_testcase.json` for the shape) and
cannot be changed without editing files on the server.

Needed: a parameter schema the backend can advertise per class, storage of
per-run overrides, pass-through to the vectorisation interface, and a client
form. Worth designing the schema so new object classes get a UI for free rather
than requiring client changes.

## 4. Model and data improvements

From the report's own conclusions. These are research and data directions rather
than software tasks.

| Item | Source | Note |
|---|---|---|
| Laser data and 3D via point clouds and oblique imagery | Framtida arbete | Expected to improve both segmentation and vectorisation, especially roads and complex buildings |
| Higher resolution, down to 3 cm/pixel | Framtida arbete | Enables more and finer object types |
| True orthophoto, ≥ 8 cm/pixel | Rekommendationer | Ordinary orthophotos displace façades, degrading segmentation |
| Simultaneous capture of imagery and laser | Rekommendationer | Comparison requires temporal alignment |
| Roads mapped as surfaces, not lines | Arbetspaket 3 | Would make road comparison exact rather than approximate |
| Harmonised municipal data models | Rekommendationer | The single biggest constraint on training data quality |
| Agent-based and multimodal AI frameworks | Arbetspaket 3 | The report notes the field moved substantially during the project and recommends evaluating newer approaches **before** investing further in the current models |
| Pre-train from existing basemap + orthophoto pairs | Arbetspaket 2 | The report judges that manual annotation absorbed effort that pre-training might have avoided |

One measured caveat worth carrying forward: the shipped checkpoints declare a
training resolution of 0.05 m/px while the tiler requests 0.08 m/px and
upsamples. Upsampling adds no detail. Imagery nearer the model resolution should
perform better, and this interaction deserves measurement rather than assumption.

## 5. Engineering debt

Concrete defects and rough edges found while documenting the system. None block
use today; all cost time later.

### Correctness

| Item | Where | Size |
|---|---|---|
| Comparison holes are order-dependent: a building drawn earlier that falls inside a later polygon's interior ring is erased. Needs per-polygon mask compositing instead of sequential painting | `gaia-engine/comparison/geo_object.py` + `image_object.py` | S |
| `create_assign_project_paths` sets `output_path` by calling `create_project_run_input_path()`, so a run's output path is its input path and `create_project_run_output_path()` is dead | `app/usecase/create_project_run.py` | S |
| `self.basemap_image` is assigned and never read | `gaia-engine/comparison/comparer.py:58` | S |
| `numpy` is imported directly but not pinned; it arrives transitively | `gaia-engine/segmentation/requirements.txt` | S |

### Robustness

| Item | Where | Size |
|---|---|---|
| Interface requirements are reinstalled on **every** start; a transient failure sets `installed=False` *and* `is_active=False`, silently removing the interface from `GET /models/segmentation` and emptying the client's object-type selector with no user-visible error | `app/service/interface_service.py` | M |
| No subprocess timeout. An engine process that never calls back leaves its step `RUNNING` forever and stalls the server | `app/tasks/task_runner.py` | M |
| Only one step runs at a time globally — not per run. A long run blocks every other run | `app/service/dispatcher.py` | L |
| `depends_on: db` waits only for container creation, and the `db` healthcheck is `exit 0` — a no-op. Migrations run from a `post_start` hook that can fire before networking is ready | `docker/linux.docker-compose.yml` | S |
| A task handler returning zero steps kills the whole run with a message naming the wrong stage | `app/service/dispatcher.py` | S |

### Client

| Item | Where | Size |
|---|---|---|
| Three modules import the private `qgis._core` / `qgis._gui` rather than the public API — unsupported and likely to break on a future QGIS | `map/layer_handler.py`, `ui/handlers/select_bounding_box.py`, `use_cases/get_and_show_run_results.py` | S |
| HTTP blocks the UI thread via `QEventLoop`; a slow backend freezes QGIS | `api/requests/http_client.py` | M |
| No automated tests. `gaia_client/test/` is a PyQt scratch area | — | M |
| Two different `layer_handler.py` modules under `map/` and `ui/handlers/` | — | S |
| Unused `PIL.Image` import | `ui/handlers/layer_handler.py` | S |

### API

| Item | Size |
|---|---|
| No pagination on `GET /projects` or `GET /runs` | S |
| No rate limiting; a client can queue unlimited runs | S |
| A single shared API key, no user accounts, no per-user audit trail. Rotating it means updating every client | M |
| No transport encryption by default; the API key crosses the wire in clear unless a TLS proxy is placed in front | M |

## 6. Governance and stewardship

Not engineering work, but the report identifies it as decisive for whether any
of the above happens.

- **Maintenance after project end is unresolved.** The report recommends a
  national actor or industry body take responsibility for maintaining GAIA and
  supporting municipalities in adopting it, and suggests a new Formas
  application or similar as the natural next step.
- **Open source is the distribution strategy.** Publishing the tool, models and
  source is intended to let municipalities and others replicate and extend it.
  That only produces value if someone triages issues and reviews contributions.
- **Framtidens baskarta.** The report raises, without answering, whether the
  basemap we map against today is the one worth optimising for. A successor
  project could contribute to that discussion rather than assuming the current
  target.

## Suggested sequencing

If the goal is completing the designed UX, dependency order matters more than
size:

1. **Register the `Comparison` group** (S) — unblocks the entire comparison
   feature and is a migration plus a check
2. **Interactive, resumable runs** (L) — the keystone; Steg 2, 3 and 4 all
   depend on it
3. **Basemap support** (L) — prerequisite for Steg 3, independent of item 2 and
   parallelisable
4. **Per-feature change classification in the engine** (L) — the real work
   behind Steg 3
5. **Steg 2 filtering** (M) — smallest of the wizard steps and good validation
   of the resumable-run design
6. **Steg 3 differentiering UI** (L)
7. **Steg 4 summary and preview** (M)
8. **Runtime estimation** (M) — pairs naturally with the concurrency work in
   section 5

Items in section 5 can be picked up independently and make good first
contributions.
