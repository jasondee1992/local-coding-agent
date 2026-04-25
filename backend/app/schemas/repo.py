from pydantic import BaseModel, Field, field_validator


def _validate_non_empty(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} cannot be empty")
    return cleaned


class RepoFile(BaseModel):
    path: str
    size_bytes: int
    extension: str


class RepoScanRequest(BaseModel):
    project_path: str
    max_files: int = Field(default=300, ge=1, le=1000)

    @field_validator("project_path")
    @classmethod
    def validate_project_path(cls, value: str) -> str:
        return _validate_non_empty(value, "project_path")


class RepoScanResponse(BaseModel):
    project_path: str
    files: list[RepoFile]


class RepoSummaryRequest(BaseModel):
    project_path: str
    max_files: int = Field(default=300, ge=1, le=1000)

    @field_validator("project_path")
    @classmethod
    def validate_project_path(cls, value: str) -> str:
        return _validate_non_empty(value, "project_path")


class RepoSummaryResponse(BaseModel):
    summary: str


class RepoAskRequest(BaseModel):
    project_path: str
    question: str
    files: list[str] = Field(default_factory=list)
    max_files: int = Field(default=80, ge=1, le=200)

    @field_validator("project_path")
    @classmethod
    def validate_project_path(cls, value: str) -> str:
        return _validate_non_empty(value, "project_path")

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        return _validate_non_empty(value, "question")


class RepoAskResponse(BaseModel):
    response: str
    context_files: list[str]
