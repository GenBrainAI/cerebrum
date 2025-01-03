class CurriedProxy(BaseModel):
    """A proxy that holds a set of tools and their metadata."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tool_names: List[str] = Field(default_factory=list)
    catalog: ToolsCatalog = Field(default_factory=lambda: tools_catalog)
    name_counter: Dict[str, int] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True 