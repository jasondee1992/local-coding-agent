from pydantic import BaseModel, Field


class ValidationCheckResult(BaseModel):
    name: str
    url: str
    ok: bool
    status_code: int | None = None
    response_preview: str | None = None
    error: str | None = None


class ValidationResponse(BaseModel):
    ok: bool
    checks: list[ValidationCheckResult] = Field(default_factory=list)


class ProposalValidationRequest(BaseModel):
    include_version: bool = True
    include_settings: bool = True
    include_models: bool = False
