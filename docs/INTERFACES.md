# Interfaces — the engine extension point

An **interface** is one unit of engine work: tiling, a segmentation model, a
vectoriser. GAIA cannot do anything without them. This document describes the
contract, so you can add your own.

Supersedes the earlier `ENGINE.md` and `PLUGINS.md`.

## Why interfaces are separate processes

Engine code is not imported by the backend. It lives outside the application, in
its own virtual environment, and is executed as a subprocess.

**Benefits:** the backend carries none of the engine dependencies — `torch`,
GDAL and `fiona` have conflicting requirements and could not share one
environment; and an engine crash cannot take the API down.

**Costs:** a communication layer is needed (the callback below), and the backend
cannot always tell a hung engine process from a slow one.

## Anatomy of an interface

A directory under `MODEL_BASE_PATH` containing three files:

| File | Required | Purpose |
|---|---|---|
| `model.json` | yes | Declares the interface(s). Its presence is what marks the directory. |
| `requirements.txt` | yes | Installed into a per-interface `venv/` |
| `main.py` | yes | Must exist — see the note below |

> **`main.py` must exist even if it is not the script you run.** Registration of
> a *new* interface checks for `main.py` specifically and skips the directory if
> it is absent. The file actually executed is `module_file_name`, which may be
> something else — `segmentation` declares `engine_runner.py` while still
> shipping a `main.py`. Existing interfaces are not re-checked, so this bites
> only when adding one.

One `model.json` may declare several interfaces — `segmentation/model.json`
declares both the roads and buildings models over the same code.

```json
[
  {
    "name": "Segmentation - Buildings (ResUNet)",
    "group": "Classification",
    "description": "Building segmentation using ResUNet architecture",
    "args": {
      "classname": "buildings",
      "image_path": "",
      "output_path": "",
      "callback_url": ""
    },
    "function_name": "runInference",
    "module_file_name": "engine_runner.py"
  }
]
```

## Groups

`group` must be exactly one of the following. Any other value or spelling makes
the interface unusable.

| Group | Purpose |
|---|---|
| `Classification` | Segments an input. Offered to the user as a selectable object type. |
| `Vectorization` | Converts a segmentation raster into vectors. |
| `Internal` | Glue steps supplied by the GAIA team — `wms_tiler`, `image_bitter`. |

Only `Classification` members appear in `GET /models/segmentation`, and so in
the client's object-type selector.

Adding an `Internal` interface usually means the `run_type` flow needs a new
task and task step implemented to invoke it — it will not be called
automatically.

## Arguments

`args` supplies defaults. Empty strings are placeholders filled in per step, and
the whole map is rendered onto the command line as `--key value`.

Four names are meaningful to the backend:

| Argument | Meaning |
|---|---|
| `image_path` | Input path. Sometimes a single file, sometimes a folder. |
| `output_path` | Folder for result files. |
| `callback_url` | Endpoint to call on completion. |
| `classname` | Object class — `buildings`, `roads`, `vegetation`, `hard_surfaces`. Required for `Classification` and `Vectorization`. |

### `classname` links classification to vectorisation

This is the only coupling between the two groups. Each classification interface
runs individually and carries its `classname` forward; when the run reaches
vectorisation, the backend selects the `Vectorization` interface whose
`classname` matches. Add a new object class and you need both halves, agreeing
on the string.

## Lifecycle

### Discovery

At startup `InterfaceService.scan_and_install_interfaces()` walks
`MODEL_BASE_PATH` two directory levels deep — enough to find both
`segmentation/` and `core/image_bitter/`. A directory containing `model.json` is
treated as an interface and is not descended into.

### Installation

For each interface found, the backend creates `<interface>/venv` if missing and
runs `pip install -r requirements.txt`.

**This happens on every backend start, not only the first.** The consequences
are worth understanding:

- A change to `requirements.txt` takes effect on the next restart with no
  rebuild.
- A transient network failure, or a pin that cannot build, **disables a working
  interface**: the failure handler sets `installed = False` *and*
  `is_active = False`, which removes it from `GET /models/segmentation` and
  empties the client's selector, with no error surfaced to the user.
- The flag is restored automatically by the next successful install.

An interface present in the database but no longer on disk is also marked
inactive.

Native dependencies are the usual cause of failure here. The GDAL Python
bindings must match the `libgdal` in the Docker base image; the pin and the
`FROM` line move together or not at all. See [OPERATIONS.md](OPERATIONS.md).

### Execution

`app/tasks/task_runner.py` validates that the interface is installed and active
and that `module_file_name` exists, then builds:

```
<venv>/bin/python <module_file_name> --arg value --arg value ...
```

It runs via `asyncio.create_subprocess_exec` with the interface directory as the
working directory, and records the PID so the process can be monitored at OS
level. `stdout`/`stderr` are piped but not currently stored. **No timeout is
applied at this level.**

The step is marked `RUNNING` and the backend moves on — it does not wait.

### Completion callback

The interface must report its own completion by POSTing to the `callback_url`
it was given (`/run_result/{step_external_id}`):

```json
{
  "task_step_id": 42,
  "success": true,
  "error": null,
  "additional_info": null
}
```

`success` decides whether the step becomes `FINISHED` or `ERROR`. `error` and
`additional_info` are free-form and unvalidated.

> Earlier documentation named this field `additional_data`. The schema
> (`TaskStepResultInsert`) uses **`additional_info`**.

`handle_run_result.py` marks the step complete and releases the next step.
**An interface that never calls back leaves its step `RUNNING` forever**, and
because only one step runs at a time server-wide, that stalls everything.

## Adding an interface — checklist

1. Create a directory under the engine root (one or two levels deep).
2. Add `requirements.txt`, `main.py`, and `model.json`.
3. Pick the right `group`; set `classname` if it is a classification or
   vectorisation model.
4. Accept `--image_path`, `--output_path`, `--callback_url` on the command line.
5. POST the result to `callback_url` on success *and* on failure.
6. Restart the backend and confirm no `Error setting up interface` line appears.
7. For a classification model, confirm it appears in
   `GET /models/segmentation`.

If you add a new object class, add the matching `Vectorization` interface with
the same `classname` — otherwise the run fails at the vectorisation stage.
