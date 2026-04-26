from pydantic import BaseModel, Field, field_validator, model_validator


def _validate_non_empty(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} cannot be empty")
    return cleaned


class PatchProposeRequest(BaseModel):
    project_path: str
    task: str
    files: list[str]
    max_files: int = Field(default=20, ge=1, le=50)

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
    def validate_file_count(self) -> "PatchProposeRequest":
        if len(self.files) > self.max_files:
            raise ValueError(f"files list length must be at most max_files ({self.max_files})")
        return self


class PatchProposeResponse(BaseModel):
    explanation: str
    diff: str
    context_files: list[str]
    safety_notes: list[str]
    warnings: list[str] = Field(default_factory=list)
