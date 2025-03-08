from http import HTTPStatus


def test_root_returns_ok_and_welcome_message(client):
    response = client.get("/")

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        "message": "Welcome to SmartRoute API! To access the docs, go to /docs or /redoc"
    }
