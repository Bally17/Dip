"""Návrh formátu správ zo simulátora (verzia na dohodu s kolegom)."""
from typing import Annotated, Literal

from pydantic import BaseModel, Field, TypeAdapter


class Vec3(BaseModel):
    x: float
    y: float
    z: float


class Quat(BaseModel):
    x: float
    y: float
    z: float
    w: float


class Pose(BaseModel):
    pos: Vec3
    rot: Quat


class _Base(BaseModel):
    participant: str = Field(min_length=1, max_length=64)
    session: str = Field(min_length=1, max_length=64)
    t: int = Field(ge=0, description="Unix čas v milisekundách")
    phase: int = Field(ge=0)


class Sample(_Base):
    type: Literal["sample"]
    heart_rate: float | None = Field(default=None, ge=20, le=250)
    head: Pose
    left: Pose | None = None
    right: Pose | None = None


class Event(_Base):
    type: Literal["event"]
    kind: Literal["reaction_time", "task1_time", "task2_time"]
    value_ms: float = Field(ge=0)


class Questionnaire(_Base):
    type: Literal["questionnaire"]
    score: float = Field(ge=0)


Message = Annotated[Sample | Event | Questionnaire, Field(discriminator="type")]
message_adapter = TypeAdapter(Message)
