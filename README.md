# PySyringe

An opinionated dependency injection library for Python.

A container that does not rely on adding decorators to your domain classes. It only wraps views in the infrastructure layer to keep your domain and app layer decoupled from the framework and the container.

## Usage


```python
# container.py
from myapp.domain import CalendarInterface
from myapp.infra import LoggingEmailSender, SmtpEmailSender, Calendar
from django.core.http import HttpRequest, HttpResponse


class Factory:
    def __init__(self, environment: str) -> None:
        self.environment = environment

    def get_mailer(self) -> EmailSender:
        if self.environment == "production":
            return SmtpEmailSender("mta.example.org", 25)

        return LoggingEmailSender()


factory = Factory(str(settings.ENVIRONMENT))

container = Container(factory)
container.never_provide(HttpRequest)
container.never_provide(HttpResponse)
container.alias(CalendarInterface, Calendar)


# views.py
from container import container

@container.inject
def my_view(request: HttpRequest, calendar: CalendarInterface) -> HttpResponse:
    now = calendar.now()
    return HttpResponse(f"Hello, World! The current time is {now}")
```
