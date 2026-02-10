<p align="center">
  <img src="assets/banner.svg" alt="PySyringe - Dependency Injection for Python" width="100%"/>
</p>

<p align="center">
  <a href="https://github.com/hugochinchilla/pysyringe/actions/workflows/test.yml"><img src="https://github.com/hugochinchilla/pysyringe/actions/workflows/test.yml/badge.svg" alt="Tests"/></a>
  <a href="https://codecov.io/gh/hugochinchilla/pysyringe"><img src="https://codecov.io/gh/hugochinchilla/pysyringe/graph/badge.svg?token=SN3JSCBB4U" alt="Coverage"/></a>
  <a href="https://badge.fury.io/py/pysyringe"><img src="https://badge.fury.io/py/pysyringe.svg" alt="PyPI version"/></a>
  <a href="https://www.hugochinchilla.net/pysyringe/"><img src="https://img.shields.io/badge/docs-pysyringe-blue" alt="Docs"/></a>
</p>

<p align="center">
  <strong>Dependency injection for Python that keeps your domain clean.</strong>
</p>

Your business logic should not know a DI container exists. No decorators on your classes, no registration boilerplate. PySyringe resolves dependencies through type hints and injects them at the call site --- your HTTP handlers, CLI commands, or message consumers --- so the rest of your code stays framework-free.

## Features

- 🚀 **Zero-decorator DI**: keep your domain clean; inject only at call sites.
- 🏭 **Factory-based wiring**: resolve by return type annotations on your factory.
- 🧩 **Inference-based construction**: auto-wire constructor dependencies by type hints.
- 🧪 **Test-friendly mocks**: replace any dependency per test with `override(...)`.
- 🔒 **Thread-safe**: mocks are per-thread; singleton creation uses locking.
- 🧰 **Aliases & blacklists**: map interfaces to implementations and mark types as non-creatable.
- ⚡ **Resolution cache**: caches factory lookups and constructor introspection (not instances).

## Installation

```
pip install pysyringe
```

## Example

```python
from datetime import datetime, timezone
from flask import Flask
from pysyringe.container import Container


class CalendarInterface:
    def now(self) -> datetime:
        raise NotImplementedError


class Calendar(CalendarInterface):
    def now(self) -> datetime:
        return datetime.now(timezone.utc)


container = Container()
container.alias(CalendarInterface, Calendar)

app = Flask(__name__)

@app.get("/now")
@container.inject
def get_now(calendar: CalendarInterface):
    return {"now": calendar.now().isoformat()}
```

`CalendarInterface` and `Calendar` are plain Python classes. The container resolves the dependency at the call site via `@container.inject` --- nothing else in your code needs to know about it.

## Documentation

For factory methods, constructor inference, singleton helpers, testing with mocks, thread safety, and the full API reference, see the **[documentation](https://www.hugochinchilla.net/pysyringe/)**.
