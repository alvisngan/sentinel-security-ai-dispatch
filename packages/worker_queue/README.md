# worker-queue

A lightweight background worker queue for decoupling fast producers from slow consumers.

Built for cases where one part of your app detects work quickly (polling an API, receiving a webhook) but processing that work is slow (calling an LLM, posting to an external service). Without a queue, each slow operation blocks the next detection. With `WorkerQueue`, detection and processing run independently.

## How it works

```
Producer (your fast code)        Worker thread(s)
────────────────────────         ────────────────────────
q.enqueue(item)        →         handler(item)   ← your slow code
q.enqueue(item)        →         handler(item)
q.enqueue(item)        →         (queued, processed when free)
```

`enqueue()` returns immediately. One or more background threads drain the queue and call your handler independently.

## Installation

This package is part of the monorepo. Add it as a workspace dependency:

```toml
# In your package's pyproject.toml
[project]
dependencies = [
    "worker-queue",
]

# In the root pyproject.toml
[tool.uv.sources]
worker-queue = { workspace = true }
```

Then sync:

```bash
uv sync
```

## Usage

```python
from worker_queue import WorkerQueue

def process(item):
    # your slow work here — runs in a background thread
    print(f"Processing: {item}")

q = WorkerQueue(handler=process, num_workers=2, name="my-worker")
q.start()

q.enqueue("item-1")
q.enqueue("item-2", label="optional log label")

q.stop()  # waits for all in-flight items to finish
```

### Wrapping with context

When your handler needs extra arguments (a client, config, etc.), capture them with `functools.partial` rather than using a closure. This keeps the `WorkerQueue` signature clean:

```python
from functools import partial
from worker_queue import WorkerQueue

def post_to_service(item, *, client, dry_run):
    client.post(item)

handler = partial(post_to_service, client=my_client, dry_run=False)
q = WorkerQueue(handler=handler, name="humanity")
```

### Subclassing for reuse

If the same context is reused across your app, wrap `WorkerQueue` in a thin subclass:

```python
class HumanityQueue:
    def __init__(self, client, *, num_workers=1):
        handler = partial(post_shift, client=client)
        self._queue = WorkerQueue(handler=handler, name="humanity", num_workers=num_workers)

    def start(self): self._queue.start()
    def stop(self):  self._queue.stop()

    def enqueue(self, shift):
        self._queue.enqueue(shift, label=shift.get("title", ""))
```

## API reference

### `WorkerQueue(handler, *, num_workers=1, maxsize=0, name="worker")`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `handler` | `Callable[[Any], None]` | required | Called for each item. Must be thread-safe. |
| `num_workers` | `int` | `1` | Number of parallel worker threads. |
| `maxsize` | `int` | `0` | Max items buffered. `0` = unlimited. When full, `enqueue()` blocks — intentional back-pressure. |
| `name` | `str` | `"worker"` | Label shown in log output, e.g. `[parse] Worker started`. |

### Methods

| Method | Description |
|---|---|
| `start()` | Spawn worker threads. Call once before enqueuing. |
| `stop()` | Signal workers to stop and block until the queue is drained. |
| `enqueue(item, *, label="")` | Add an item to the queue. `label` is an optional string shown in log output. |
| `depth()` | Returns the approximate number of items currently waiting. |

### Thread-safe printing

If your handler prints output from multiple threads, use the bundled helpers to avoid interleaved lines:

```python
from worker_queue import safe_print, print_lock

# Single-line output
safe_print("Processing item:", item)

# Multi-line block — hold the lock for the whole block
with print_lock():
    print("Subject :", item["subject"])
    print("From    :", item["from"])
```

## Back-pressure

By default the queue is unbounded. If your producer can outrun your workers significantly, cap the queue with `maxsize` to limit memory use:

```python
# Buffer at most 50 items. enqueue() blocks if the queue is full.
q = WorkerQueue(handler=process, num_workers=2, maxsize=50)
```

This means the producer slows down naturally rather than accumulating unbounded items in memory during a spike.

## Shutdown

`stop()` pushes a stop sentinel for each worker and then joins all threads. Workers finish their current item before exiting, so no in-flight work is lost:

```python
try:
    q.start()
    run_forever()
finally:
    q.stop()  # always drains cleanly, even on Ctrl-C or exception
```
