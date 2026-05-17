from pydantic import BaseModel, Field, field_validator


class QueryPlan(BaseModel):
    intent: str = Field(..., description="Short description of the user's goal")
    tables: list[str] = Field(default_factory=list)
    columns: list[str] = Field(default_factory=list)
    filters: list[str] = Field(default_factory=list)
    joins: list[str] = Field(default_factory=list)
    aggregation: list[str] = Field(default_factory=list)
    group_by: list[str] = Field(default_factory=list)
    order_by: list[str] = Field(default_factory=list)
    limit: int | None = None
    notes: list[str] = Field(default_factory=list)

    @field_validator(
        "tables",
        "columns",
        "filters",
        "joins",
        "aggregation",
        "group_by",
        "order_by",
        "notes",
        mode="before",
    )
    @classmethod
    def empty_string_to_list(cls, v):
        if v == "":
            return []
        return v
