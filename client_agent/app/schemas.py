from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class WorkspaceFile(BaseModel):
    path: str
    size_bytes: int
    extension: str


class WorkspaceScanRequest(BaseModel):
    project_path: str
    max_files: int = Field(default=300, ge=1, le=1000)

    @field_validator("project_path")
    @classmethod
    def validate_project_path(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("project_path must not be empty.")
        return value


class WorkspaceScanResponse(BaseModel):
    project_path: str
    files: list[WorkspaceFile]


class WorkspacePlanChangeRequest(BaseModel):
    project_path: str
    task: str
    files: list[str]
    save_proposal: bool = False
    proposal_name: str | None = None

    @field_validator("project_path", "task")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Value must not be empty.")
        return value

    @field_validator("files")
    @classmethod
    def validate_files(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("files must not be empty.")
        if not any(path.strip() for path in value):
            raise ValueError("files must contain at least one non-empty path.")
        return value


class WorkspacePlanChangeResponse(BaseModel):
    explanation: str
    target_file: str | None
    operation: str
    anchor: str | None
    normalized_anchor: str | None
    code: str
    generated_diff: str
    context_files: list[str]
    proposal_id: str | None = None
    proposal_path: str | None = None
    warnings: list[str]
    safety_notes: list[str]


class WorkspaceAuthorizationPermissions(BaseModel):
    read_files: bool = False
    create_files: bool = False
    modify_files: bool = False
    apply_changes: bool = False
    delete_files: bool = False


class WorkspaceAuthorizationQuestion(BaseModel):
    permission: str
    question: str
    recommended: bool = False
    reason: str


class WorkspaceAuthorizationPreviewRequest(BaseModel):
    project_path: str
    task: str = ""
    files: list[str] = []

    @field_validator("project_path")
    @classmethod
    def validate_preview_project_path(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("project_path must not be empty.")
        return value


class WorkspaceAuthorizationPreviewResponse(BaseModel):
    authorization_id: str
    project_path: str
    has_existing_authorization: bool
    current_permissions: WorkspaceAuthorizationPermissions | None = None
    questions: list[WorkspaceAuthorizationQuestion]


class WorkspaceAuthorizeRequest(BaseModel):
    project_path: str
    confirm: bool = False
    read_files: bool = False
    create_files: bool = False
    modify_files: bool = False
    apply_changes: bool = False
    delete_files: bool = False

    @field_validator("project_path")
    @classmethod
    def validate_authorize_project_path(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("project_path must not be empty.")
        return value


class WorkspaceAuthorizationResponse(BaseModel):
    authorization_id: str
    project_path: str
    created_at: str | None = None
    updated_at: str | None = None
    permissions: WorkspaceAuthorizationPermissions
    message: str


class WorkspaceAuthorizationSummary(BaseModel):
    authorization_id: str
    project_path: str
    created_at: str | None = None
    updated_at: str | None = None
    permissions: WorkspaceAuthorizationPermissions


class ClientProposalSummary(BaseModel):
    proposal_id: str
    created_at: str | None = None
    task: str | None = None
    target_file: str | None = None
    warnings_count: int = 0


class ClientProposalApplyRequest(BaseModel):
    confirm_apply: bool = False
    allow_warnings: bool = False
    create_backup: bool = True


class ClientProposalApplyResponse(BaseModel):
    proposal_id: str
    applied: bool
    target_file: str | None
    backup_path: str | None
    message: str
    warnings: list[str]


class ClientStatusResponse(BaseModel):
    name: str
    env: str
    ai_server_base_url: str
    ai_server_ok: bool
    ai_server_response: dict | None = None
