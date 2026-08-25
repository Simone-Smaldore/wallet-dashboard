from pydantic import BaseModel, Field


class LinkRequest(BaseModel):
    # Plain str rather than EmailStr: that would pull in email-validator, and it
    # would buy nothing. The real gate is the allow-list — an address that is not
    # on it goes nowhere, malformed or not.
    email: str = Field(min_length=3, max_length=255)


class LinkRequested(BaseModel):
    """Deliberately says nothing about whether the address exists.

    The same payload comes back for an allowed address, an unknown one and a
    rate-limited one, so the endpoint cannot be used to enumerate who has access.
    """

    message: str = "Se l'indirizzo è abilitato riceverai un link fra pochi istanti."


class VerifyRequest(BaseModel):
    token: str = Field(min_length=16, max_length=256)
