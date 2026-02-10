"""Integration test: pysyringe + Django views.

Verifies that @container.inject with Provide[T] markers works correctly
alongside Django's request handling — Django controls `request`, pysyringe
injects only the marked parameters.
"""

import json

import django
from django.conf import settings

settings.configure(
    DEBUG=True,
    SECRET_KEY="test-secret-key",
    ROOT_URLCONF=__name__,
)
django.setup()

from django.http import HttpRequest, HttpResponse, JsonResponse  # noqa: E402
from django.test import RequestFactory  # noqa: E402

from pysyringe.container import Container, Provide  # noqa: E402


class GreetingService:
    def greet(self, name: str) -> str:
        return f"Hello, {name}!"


class UserRepository:
    def find(self, user_id: int) -> dict:
        return {"id": user_id, "name": "Alice"}


def greeting_view(
    request: HttpRequest,
    service: Provide[GreetingService],
) -> HttpResponse:
    name = request.GET.get("name", "World")
    return HttpResponse(service.greet(name))


def user_detail_view(
    request: HttpRequest,
    repo: Provide[UserRepository],
) -> JsonResponse:
    user = repo.find(user_id=1)
    return JsonResponse(user)


def multi_injection_view(
    request: HttpRequest,
    greeting: Provide[GreetingService],
    repo: Provide[UserRepository],
) -> HttpResponse:
    user = repo.find(user_id=1)
    message = greeting.greet(user["name"])
    return HttpResponse(message)


class DjangoIntegrationTest:
    def test_view_receives_request_and_injected_service(self) -> None:
        container = Container()
        view = container.inject(greeting_view)

        request = RequestFactory().get("/greet", {"name": "Django"})
        response = view(request)

        assert response.status_code == 200
        assert response.content == b"Hello, Django!"

    def test_request_object_is_real_django_request(self) -> None:
        captured = {}

        def inspect_view(
            request: HttpRequest,
            service: Provide[GreetingService],
        ) -> HttpResponse:
            captured["request"] = request
            return HttpResponse("ok")

        container = Container()
        view = container.inject(inspect_view)

        factory = RequestFactory()
        original_request = factory.get("/test")
        view(original_request)

        assert captured["request"] is original_request
        assert isinstance(captured["request"], HttpRequest)

    def test_json_response_with_injected_repository(self) -> None:
        container = Container()
        view = container.inject(user_detail_view)

        request = RequestFactory().get("/user/1")
        response = view(request)

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data == {"id": 1, "name": "Alice"}

    def test_multiple_injected_services(self) -> None:
        container = Container()
        view = container.inject(multi_injection_view)

        request = RequestFactory().get("/greet-user")
        response = view(request)

        assert response.status_code == 200
        assert response.content == b"Hello, Alice!"

    def test_override_replaces_injected_service(self) -> None:
        container = Container()

        class FakeRepo(UserRepository):
            def find(self, user_id: int) -> dict:
                return {"id": user_id, "name": "Bob"}

        with container.override(UserRepository, FakeRepo()):
            view = container.inject(user_detail_view)
            request = RequestFactory().get("/user/1")
            response = view(request)

        data = json.loads(response.content)
        assert data["name"] == "Bob"

    def test_mock_replaces_injected_service(self) -> None:
        container = Container()

        class StubGreeting(GreetingService):
            def greet(self, name: str) -> str:
                return f"Howdy, {name}!"

        container.use_mock(GreetingService, StubGreeting())

        view = container.inject(greeting_view)
        request = RequestFactory().get("/greet", {"name": "Partner"})
        response = view(request)

        assert response.content == b"Howdy, Partner!"
        container.clear_mocks()

    def test_view_with_factory(self) -> None:
        class Config:
            def __init__(self) -> None:
                self.prefix = "Greetings"

        class ConfiguredGreeting:
            def __init__(self, config: Config) -> None:
                self.config = config

            def greet(self, name: str) -> str:
                return f"{self.config.prefix}, {name}!"

        class Factory:
            def get_config(self) -> Config:
                return Config()

        def view(
            request: HttpRequest,
            service: Provide[ConfiguredGreeting],
        ) -> HttpResponse:
            return HttpResponse(service.greet("World"))

        container = Container(Factory())
        injected = container.inject(view)

        request = RequestFactory().get("/greet")
        response = injected(request)

        assert response.content == b"Greetings, World!"
