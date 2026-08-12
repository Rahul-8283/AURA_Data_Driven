from pydantic import BaseModel, Field
from typing import Literal

class Element(BaseModel):
    symbol: str = Field(description="The atomic symbol of the element, e.g., Li, Ni, Co")
    name: str = Field(description="The full name of the element")
    group: int = Field(description="The periodic group number")

class Material(BaseModel):
    name: str = Field(description="The battery compound name, e.g., NMC811, LFP")
    class_name: Literal["cathode", "anode", "electrolyte"] = Field(alias="class")

class Property(BaseModel):
    name: str = Field(description="The electrochemical behavior or property, e.g., High Capacity")

class DegradationMode(BaseModel):
    name: str = Field(description="The failure mechanism, e.g., Cation Mixing")

class Triplet(BaseModel):
    subject_label: Literal["Element", "Material", "Property", "DegradationMode"]
    subject: str
    predicate: Literal["CONTAINS", "CAN_BE_DOPED_WITH", "EXHIBITS", "SUFFERS_FROM", "MITIGATES"]
    object_label: Literal["Element", "Material", "Property", "DegradationMode"]
    object: str
