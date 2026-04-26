from pydantic import BaseModel, Field


class ProposalApplyRequest(BaseModel):
    confirm_apply: bool = False
    allow_warnings: bool = False
    create_backup: bool = True


class ProposalApplyResponse(BaseModel):
    proposal_id: str
    applied: bool
    target_file: str | None
    backup_path: str | None
    message: str
    warnings: list[str] = Field(default_factory=list)
