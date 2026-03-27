from typing import TypedDict, List
from pydantic import BaseModel, Field

class BuildState(TypedDict, total=False):
    """
    Represents the internal state of the Elden Ring build generation workflow.
    """
    query: str
    is_valid: bool
    rejection_reason: str
    starting_class: str
    
    use_incantations: bool
    use_sorceries: bool
    use_shields: bool
    use_ammos: bool
    
    weapons: List[str]
    armor: List[str]
    talismans: List[str]
    spirits: List[str]
    incantations: List[str]
    sorceries: List[str]
    shields: List[str]
    ammos: List[str]
    
    final_build: str

class QueryValidation(BaseModel):
    """
    Model for holding the validation result of the user's query.
    """
    is_valid: bool = Field(description="True if the query is a feasible Elden Ring build request. False if it asks for impossible items, other games, or unrelated topics.")
    rejection_reason: str = Field(description="If is_valid is False, provide a short, in-universe explanation of why. If True, leave empty.")

class OptionalsDecision(BaseModel):
    """
    Model for deciding which optional categories are needed based on the build.
    """
    use_incantations: bool = Field(description="Whether the requested build type would benefit from incantations.")
    use_sorceries: bool = Field(description="Whether the requested build type would benefit from sorceries.")
    use_shields: bool = Field(description="Whether the requested build type typically uses shields.")
    use_ammos: bool = Field(description="Whether the requested build type uses a bow/crossbow and requires ammo.")

class CoreGearDecision(BaseModel):
    """
    Model for the core gear choices.
    """
    weapons: List[str] = Field(description="List of 1-3 best weapons for the build.")
    armor: List[str] = Field(description="List of the 4 armor pieces (head, chest, arms, legs) for the build.")
    talismans: List[str] = Field(description="List of the 4 best talismans for the build.")
    spirits: List[str] = Field(description="List of 1 best spirit ash for the build.")
    
class OptionalGearDecision(BaseModel):
    """
    Model for the optional gear choices.
    """
    incantations: List[str] = Field(default=[], description="List of incantations for the build. (Empty if none)")
    sorceries: List[str] = Field(default=[], description="List of sorceries for the build. (Empty if none)")
    shields: List[str] = Field(default=[], description="List of shields for the build. (Empty if none)")
    ammos: List[str] = Field(default=[], description="List of ammos for the build. (Empty if none)")

class CategoryExtraction(BaseModel):
    """
    Generic model for extracting gear list for a specific category.
    """
    items: List[str] = Field(default_factory=list, description="List of extracted items for this category.")
