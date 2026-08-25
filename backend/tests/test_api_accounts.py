"""Accounts over HTTP: balances, uniqueness, archiving, ownership."""

import pytest

CONTO = {
    "name": "Conto corrente",
    "kind": "corrente",
    "opening_balance_cents": 100_000,
    "opening_date": "2026-01-01",
}


def create(client, **overrides):
    return client.post("/api/accounts", json={**CONTO, **overrides})


def test_accounts_need_a_session(client):
    assert client.get("/api/accounts").status_code == 401
    assert create(client).status_code == 401


def test_a_new_account_starts_at_its_opening_balance(signed_in):
    created = create(signed_in)
    assert created.status_code == 201
    assert created.json()["balance_cents"] == 100_000

    listed = signed_in.get("/api/accounts").json()
    assert [a["name"] for a in listed["accounts"]] == ["Conto corrente"]
    assert listed["net_worth_cents"] == 100_000


def test_net_worth_is_the_sum_of_the_counted_accounts(signed_in):
    create(signed_in, name="Corrente", opening_balance_cents=100_000)
    create(signed_in, name="Deposito", kind="deposito", opening_balance_cents=500_000)
    create(signed_in, name="Contante", kind="contante", opening_balance_cents=5_000)

    assert signed_in.get("/api/accounts").json()["net_worth_cents"] == 605_000


def test_an_excluded_account_leaves_the_total_and_keeps_its_balance(signed_in):
    create(signed_in, name="Mio", opening_balance_cents=100_000)
    shared = create(
        signed_in,
        name="Cointestato",
        opening_balance_cents=80_000,
        include_in_net_worth=False,
    ).json()

    listed = signed_in.get("/api/accounts").json()
    assert listed["net_worth_cents"] == 100_000

    by_id = {a["id"]: a for a in listed["accounts"]}
    # Out of the total, but it still has a balance of its own.
    assert by_id[shared["id"]]["balance_cents"] == 80_000


@pytest.mark.parametrize("second", ["conto corrente", "CONTO CORRENTE", " Conto Corrente "])
def test_the_same_name_in_another_case_is_refused(signed_in, second):
    """Two accounts you cannot tell apart in a picker is how movements end up
    filed against the wrong one."""
    create(signed_in)
    clash = create(signed_in, name=second)

    assert clash.status_code == 409
    assert "Conto corrente" in clash.json()["detail"]


def test_renaming_onto_an_existing_name_is_refused_but_onto_itself_is_not(signed_in):
    first = create(signed_in, name="Corrente").json()
    second = create(signed_in, name="Deposito", kind="deposito").json()

    clash = signed_in.patch(f"/api/accounts/{second['id']}", json={"name": "corrente"})
    assert clash.status_code == 409

    # Changing the capitalisation of its own name is not a conflict.
    same = signed_in.patch(f"/api/accounts/{first['id']}", json={"name": "CORRENTE"})
    assert same.status_code == 200
    assert same.json()["name"] == "CORRENTE"


def test_a_patch_only_touches_what_it_names(signed_in):
    account = create(signed_in).json()

    patched = signed_in.patch(
        f"/api/accounts/{account['id']}", json={"name": "Rinominato"}
    ).json()

    assert patched["name"] == "Rinominato"
    assert patched["kind"] == account["kind"]
    assert patched["opening_balance_cents"] == account["opening_balance_cents"]
    assert patched["include_in_net_worth"] is True


def test_archiving_keeps_the_account_and_sinks_it(signed_in):
    """⚠️ There is no DELETE, and archived is not hidden: a closed account still
    holds history, and making its money vanish from the list would read as a
    bug rather than as a decision."""
    create(signed_in, name="Vecchio", opening_balance_cents=1_000)
    create(signed_in, name="Nuovo", opening_balance_cents=2_000)

    listed = signed_in.get("/api/accounts").json()
    old = next(a for a in listed["accounts"] if a["name"] == "Vecchio")

    archived = signed_in.patch(f"/api/accounts/{old['id']}", json={"is_archived": True})
    assert archived.status_code == 200

    after = signed_in.get("/api/accounts").json()
    names = [a["name"] for a in after["accounts"]]
    assert names == ["Nuovo", "Vecchio"]  # archived sinks to the bottom
    assert after["net_worth_cents"] == 3_000


def test_an_unknown_account_is_a_404_not_a_403(signed_in):
    """The same answer for "does not exist" and "not yours": a 403 would confirm
    that the id is in use by someone."""
    assert signed_in.patch("/api/accounts/9999", json={"name": "x"}).status_code == 404


def test_a_misspelled_field_fails_loudly(signed_in):
    """extra="forbid": a typo must not be silently dropped on the floor."""
    response = signed_in.post("/api/accounts", json={**CONTO, "openingBalance": 1})
    assert response.status_code == 422


def test_an_unknown_kind_is_refused(signed_in):
    assert create(signed_in, kind="cripto").status_code == 422
