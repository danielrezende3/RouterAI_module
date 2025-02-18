from smartroute.routers.invoke import extract_model_name


def test_conflicting_request(client):
    """
    When both fallback and tier_model are provided,
    the request should be rejected with HTTP 422.
    """
    request_data = {"text": "Test input", "fallback": ["dummy"], "tier_model": "fast"}
    response = client.post("/v1/invoke", json=request_data)
    assert response.status_code == 422
    assert (
        response.json()["detail"]
        == "Please choose either fallback or tier_model, not both."
    )


def test_extract_model_name():
    """
    Verify that extract_model_name returns the correct model name based
    on available attributes.
    """

    # Case: model attribute exists and contains a slash.
    class ObjA:
        model = "abc/def"

    name = extract_model_name(ObjA())
    assert name == "def"

    # Case: model_name attribute exists.
    class ObjB:
        model_name = "xyz"

    name = extract_model_name(ObjB())
    assert name == "xyz"

    # Case: neither attribute exists.
    class ObjC:
        pass

    name = extract_model_name(ObjC())
    assert name == "unknown_model"

    # Case: model attribute exists without a slash.
    class ObjD:
        model = "simplemodel"

    name = extract_model_name(ObjD())
    assert name == "simplemodel"
