from pydantic import BaseModel, Field, field_validator, model_validator


def _validate_non_empty(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} cannot be empty")
    return cleaned


class PlanChangeRequest(BaseModel):
    project_path: str
    task: str
    files: list[str]
    max_files: int = Field(default=10, ge=1, le=20)
    save_proposal: bool = False
    proposal_name: str | None = None

    @field_validator("project_path")
    @classmethod
    def validate_project_path(cls, value: str) -> str:
        return _validate_non_empty(value, "project_path")

    @field_validator("task")
    @classmethod
    def validate_task(cls, value: str) -> str:
        return _validate_non_empty(value, "task")

    @field_validator("files")
    @classmethod
    def validate_files(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item.strip()]
        if not cleaned:
            raise ValueError("files must not be empty")
        return list(dict.fromkeys(cleaned))

    @model_validator(mode="after")
    def validate_file_count(self) -> "PlanChangeRequest":
        if len(self.files) > self.max_files:
            raise ValueError(f"files list length must be at most max_files ({self.max_files})")
        return self


class PlanChangeResponse(BaseModel):
    explanation: str
    target_file: str | None
    operation: str
    anchor: str | None
    code: str
    generated_diff: str
    context_files: list[str]
    proposal_id: str | None = None
    proposal_path: str | None = None
    warnings: list[str] = Field(default_factory=list)
    safety_notes: list[str] = Field(default_factory=list)
