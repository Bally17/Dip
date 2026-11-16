"""Správa účtov. Admin vidí člena len pod pseudonymom, prihlasovacie meno sa mu nevracia."""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from . import security, storage
from .auth import admin_only

router = APIRouter(dependencies=[Depends(admin_only)])


class NewUser(BaseModel):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9._@-]+$")
    password: str = Field(min_length=8, max_length=128)
    role: Literal["admin", "researcher", "member"]


def public(username: str, role: str) -> dict:
    """Účet tak, ako ho smie vidieť admin: člen pod pseudonymom, ostatní pod menom."""
    shown = security.participant_code(username) if role == "member" else username
    return {"id": shown, "name": shown, "role": role}


@router.post("/users", status_code=201)
async def create_user(body: NewUser):
    if not await storage.create_user(body.username, security.hash_password(body.password), body.role):
        raise HTTPException(409, "Účet s týmto menom už existuje")
    return public(body.username, body.role)


@router.get("/users")
async def list_users():
    return [public(u["username"], u["role"]) for u in await storage.list_users()]


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, admin: dict = Depends(admin_only)):
    match = next((u for u in await storage.list_users() if public(u["username"], u["role"])["id"] == user_id), None)
    if not match:
        raise HTTPException(404, "Účet neexistuje")
    if match["username"] == admin["username"]:
        raise HTTPException(400, "Vlastný účet sa zrušiť nedá")
    await storage.delete_user(match["username"])
    return {"deleted": user_id}
