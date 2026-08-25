"""Categories over HTTP: two lists, one per sign, that never mix."""

SPESA = {"name": "Spesa", "kind": "expense", "color": "chart-1", "icon": "ShoppingCart"}


def create(client, **overrides):
    return client.post("/api/categories", json={**SPESA, **overrides})


def test_categories_need_a_session(client):
    assert client.get("/api/categories").status_code == 401


def test_create_and_list(signed_in):
    assert create(signed_in).status_code == 201
    create(signed_in, name="Stipendio", kind="income", icon="Banknote")

    listed = signed_in.get("/api/categories").json()
    assert {c["name"] for c in listed} == {"Spesa", "Stipendio"}


def test_the_same_name_on_the_two_lists_is_allowed(signed_in):
    """⚠️ Not a duplicate: "Regalo" as an expense is a present you bought, as an
    income it is money someone gave you. Uniqueness is per sign."""
    assert create(signed_in, name="Regalo", kind="expense", icon="Gift").status_code == 201
    assert create(signed_in, name="Regalo", kind="income", icon="Gift").status_code == 201


def test_the_same_name_in_another_case_on_the_same_list_is_refused(signed_in):
    """"Bar" and "bar" would be two slices of the same pie."""
    create(signed_in, name="Bar", icon="Coffee")
    clash = create(signed_in, name="bar", icon="Coffee")

    assert clash.status_code == 409
    assert "Bar" in clash.json()["detail"]


def test_a_colour_outside_the_palette_is_refused(signed_in):
    """The value is a token name, not a hex: a colour no chart can draw must not
    reach the database."""
    assert create(signed_in, color="#ff0000").status_code == 422
    assert create(signed_in, color="chart-99").status_code == 422


def test_an_icon_outside_the_curated_list_is_refused(signed_in):
    """The frontend imports these by name; one outside the list renders as
    nothing at all."""
    assert create(signed_in, icon="Rocket").status_code == 422


def test_the_sign_cannot_be_changed(signed_in):
    """⚠️ A spending category must not become an income one: movements already
    point at it, and flipping the sign would move past amounts from one side of
    every chart to the other. The field is simply not on the update schema."""
    category = create(signed_in).json()

    response = signed_in.patch(f"/api/categories/{category['id']}", json={"kind": "income"})
    assert response.status_code == 422


def test_renaming_propagates_by_pointing_not_by_copying(signed_in):
    category = create(signed_in).json()

    renamed = signed_in.patch(
        f"/api/categories/{category['id']}", json={"name": "Spesa alimentare"}
    )
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Spesa alimentare"
    # Same row: movements pointing at this id follow the new name for free.
    assert renamed.json()["id"] == category["id"]


def test_archiving_keeps_it_readable(signed_in):
    """Past movements point at it and the year-on-year comparison reads it."""
    category = create(signed_in).json()

    signed_in.patch(f"/api/categories/{category['id']}", json={"is_archived": True})

    listed = signed_in.get("/api/categories").json()
    archived = next(c for c in listed if c["id"] == category["id"])
    assert archived["is_archived"] is True


def test_an_unknown_category_is_a_404(signed_in):
    assert signed_in.patch("/api/categories/9999", json={"name": "x"}).status_code == 404
