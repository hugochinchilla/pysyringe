# PySyringe

An opinionated dependency injection library for Python.

A container that does not rely on adding decorators to your domain classes. It only wraps views in the infrastructure layer to keep your domain and app layer decoupled from the framework and the container.

## Installation

```bash
pip install pysyringe
```

[pysyringe on PyPI](https://pypi.org/project/pysyringe/)

## Usage


```python
# container.py
from myapp.domain import CalendarInterface, EmailSenderInterface
from myapp.infra import LoggingEmailSender, SmtpEmailSender, Calendar
from django.core.http import HttpRequest, HttpResponse


class Factory:
    """
    The factory is used to instruct how to create complex objects or to
    customize dependencies based on the environment.

    Any class with methods annotated with return types can be used to
    resolve dependencies. There is not a concrete interface you need to implement,
    the container will introspect the return types of the methods to know how to
    resolve the dependencies.
    """
    def __init__(self, environment: str) -> None:
        self.environment = environment

    def get_mailer(self) -> EmailSenderInterface:
        """
        The name of the method is irrelevant, the container knows this method
        is used to resolve the EmailSenderInterface because of the return type
        annotation.
        """
        if self.environment == "production":
            return SmtpEmailSender("mta.example.org", 25)

        return LoggingEmailSender()


# Create your custom factory
factory = Factory(getenv('ENVIRONMENT'))
# Initialize the container with your factory
container = Container(factory)
# You can blacklist classes yo don't want the container to try to instantiate by inference
container.never_provide(HttpRequest)
container.never_provide(HttpResponse)
# You can also alias interfaces to concrete classes
container.alias(CalendarInterface, Calendar)


# views.py
from container import container

@container.inject
def my_view(request: HttpRequest, calendar: CalendarInterface) -> HttpResponse:
    now = calendar.now()
    return HttpResponse(f"Hello, World! The current time is {now}")
```

### Testing

The container can be patched for testing.

```python
# test_service.py
from container import container
from myapp.domain import UserRepository
from myapp.usecases import SignupUserService
from myapp.infra.testing import InMemoryUserRepository

import pytest

@pytest.fixture(autouse=True)
def clear_container_mocks_after_each_test():
    yield
    container.clear_mocks()


def test_create_user():
    user_repository = InMemoryUserRepository()
    container.use_mock(UserRepository, user_repository)
    signup_user_service = container.provide(SignupUserService)

    signup_user_service.signup("John Doe", "john.doe@example.org")

    assert user_repository.get_by_email("john.doe@example.org")
```

### Thread safety

The `Container` is thread-safe with respect to mocks. Mocks configured after the container has been created are stored in thread-local storage, so changes made to mocks in one thread do not affect other threads.

- **Shared across all threads**: `alias(...)`, `never_provide(...)`, and the factory configuration (methods on your factory used for resolution).
- **Thread-local**: `use_mock(...)` and `clear_mocks()` operate only on the calling thread's mock store.

Implications:
- Using `use_mock(SomeType, mock_instance)` in one thread will not change what another thread receives for `SomeType`.
- Calling `clear_mocks()` clears only the current thread's mocks.
- To share a behavior globally across threads, prefer `alias(...)` or implement a factory method instead of relying on mocks.
