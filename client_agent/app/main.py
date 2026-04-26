from __future__ import annotations

from fastapi import FastAPI, HTTPException, status

from app.ai_server_client import ping_ai_server, request_plan_from_context
from app.authorization_store import (
    AuthorizationError,
    list_project_authorizations,
    load_project_authorization,
    preview_project_authorization,
    require_project_authorization,
    save_project_authorization,
)
from app.config import get_settings
from app.diff_builder import generate_insert_after_anchor_diff, validate_plan
from app.proposal_apply import apply_client_proposal
from app.proposal_store import list_client_proposals, load_client_proposal, save_client_proposal
from app.schemas import (
    ClientProposalApplyRequest,
    ClientProposalApplyResponse,
    ClientProposalSummary,
    ClientStatusResponse,
    WorkspaceAuthorizationPreviewRequest,
    WorkspaceAuthorizationPreviewResponse,
    WorkspaceAuthorizationResponse,
    WorkspaceAuthorizationSummary,
    WorkspaceAuthorizeRequest,
    WorkspacePlanChangeRequest,
    WorkspacePlanChangeResponse,
    WorkspaceScanRequest,
    WorkspaceScanResponse,
)
from app.workspace_reader import WorkspaceReaderError, build_context_files, scan_workspace

settings = get_settings()
app = FastAPI(title=settings.client_agent_name)

DEFAULT_SAFETY_NOTES = [
    "This client agent does not write project files during plan generation.",
    "Review the generated diff before applying it locally.",
    "Only explicitly selected files are sent to the AI server.",
]


def _bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def _forbidden(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def _ai_error(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "name": settings.client_agent_name,
        "env": settings.client_agent_env,
    }


@app.get("/status", response_model=ClientStatusResponse)
async def client_status() -> ClientStatusResponse:
    try:
        response = await ping_ai_server()
        ai_server_ok = True
    except RuntimeError as exc:
        response = {"error": str(exc)}
        ai_server_ok = False
    return ClientStatusResponse(
        name=settings.client_agent_name,
        env=settings.client_agent_env,
        ai_server_base_url=settings.ai_server_base_url,
        ai_server_ok=ai_server_ok,
        ai_server_response=response,
    )


@app.post("/workspace/authorize/preview", response_model=WorkspaceAuthorizationPreviewResponse)
async def workspace_authorize_preview(
    payload: WorkspaceAuthorizationPreviewRequest,
) -> WorkspaceAuthorizationPreviewResponse:
    try:
        preview = preview_project_authorization(
            payload.project_path,
            task=payload.task,
            files=payload.files,
        )
    except AuthorizationError as exc:
        raise _forbidden(str(exc)) from exc
    except ValueError as exc:
        raise _bad_request(str(exc)) from exc
    return WorkspaceAuthorizationPreviewResponse(**preview)


@app.post("/workspace/authorize", response_model=WorkspaceAuthorizationResponse)
async def workspace_authorize(payload: WorkspaceAuthorizeRequest) -> WorkspaceAuthorizationResponse:
    if not payload.confirm:
        raise _bad_request("confirm=true is required to save project authorization.")
    try:
        authorization = save_project_authorization(
            payload.project_path,
            read_files=payload.read_files,
            create_files=payload.create_files,
            modify_files=payload.modify_files,
            apply_changes=payload.apply_changes,
            delete_files=payload.delete_files,
        )
    except ValueError as exc:
        raise _bad_request(str(exc)) from exc
    return WorkspaceAuthorizationResponse(
        authorization_id=authorization["authorization_id"],
        project_path=authorization["project_path"],
        created_at=authorization.get("created_at"),
        updated_at=authorization.get("updated_at"),
        permissions=authorization["permissions"],
        message="Project authorization saved.",
    )


@app.get("/workspace/authorizations", response_model=list[WorkspaceAuthorizationSummary])
async def workspace_authorizations() -> list[WorkspaceAuthorizationSummary]:
    return [WorkspaceAuthorizationSummary(**item) for item in list_project_authorizations()]


@app.get("/workspace/authorizations/{authorization_id}", response_model=WorkspaceAuthorizationSummary)
async def workspace_authorization_detail(authorization_id: str) -> WorkspaceAuthorizationSummary:
    try:
        return WorkspaceAuthorizationSummary(**load_project_authorization(authorization_id))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Authorization not found.") from exc
    except ValueError as exc:
        raise _bad_request(str(exc)) from exc


@app.post("/workspace/scan", response_model=WorkspaceScanResponse)
async def workspace_scan(payload: WorkspaceScanRequest) -> WorkspaceScanResponse:
    try:
        require_project_authorization(payload.project_path, read_files=True)
        files = scan_workspace(payload.project_path, max_files=payload.max_files)
    except AuthorizationError as exc:
        raise _forbidden(str(exc)) from exc
    except WorkspaceReaderError as exc:
        raise _bad_request(str(exc)) from exc
    return WorkspaceScanResponse(project_path=payload.project_path, files=files)


@app.post("/workspace/plan-change", response_model=WorkspacePlanChangeResponse)
async def workspace_plan_change(payload: WorkspacePlanChangeRequest) -> WorkspacePlanChangeResponse:
    try:
        require_project_authorization(payload.project_path, read_files=True)
        context_files = build_context_files(payload.project_path, payload.files)
    except AuthorizationError as exc:
        raise _forbidden(str(exc)) from exc
    except WorkspaceReaderError as exc:
        raise _bad_request(str(exc)) from exc

    try:
        ai_response = await request_plan_from_context(payload.task, context_files)
    except RuntimeError as exc:
        raise _ai_error(str(exc)) from exc

    explanation = str(ai_response.get("explanation") or "No explanation provided by the AI server.")
    target_file = ai_response.get("target_file")
    operation = str(ai_response.get("operation") or "")
    anchor = ai_response.get("anchor")
    code = str(ai_response.get("code") or "")
    warnings = list(ai_response.get("warnings") or [])
    safety_notes = list(ai_response.get("safety_notes") or DEFAULT_SAFETY_NOTES)

    if target_file:
        warnings.extend(validate_plan(payload.task, str(target_file), operation, code, payload.files))
        try:
            diff_result = generate_insert_after_anchor_diff(
                project_path=payload.project_path,
                target_file=str(target_file),
                anchor=str(anchor or ""),
                code=code,
                task=payload.task,
            )
        except WorkspaceReaderError as exc:
            raise _bad_request(str(exc)) from exc
    else:
        diff_result = {
            "generated_diff": "",
            "warnings": ["AI server did not select a target_file."],
            "normalized_anchor": None,
        }

    warnings.extend(diff_result["warnings"])
    if diff_result["generated_diff"] == "":
        warnings.append("Generated diff is empty.")
    if warnings and "This proposal has warnings and should not be applied until reviewed." not in safety_notes:
        safety_notes.append("This proposal has warnings and should not be applied until reviewed.")

    result = {
        "explanation": explanation,
        "target_file": target_file,
        "operation": operation,
        "anchor": anchor,
        "code": code,
        "generated_diff": diff_result["generated_diff"],
        "warnings": list(dict.fromkeys(warnings)),
        "safety_notes": list(dict.fromkeys(safety_notes)),
        "ai_server_response": ai_response,
    }

    proposal_id: str | None = None
    proposal_path: str | None = None
    if payload.save_proposal:
        saved = save_client_proposal(
            project_path=payload.project_path,
            task=payload.task,
            result=result,
            proposal_name=payload.proposal_name,
        )
        proposal_id = saved["proposal_id"]
        proposal_path = saved["proposal_path"]

    return WorkspacePlanChangeResponse(
        explanation=explanation,
        target_file=target_file,
        operation=operation,
        anchor=anchor,
        normalized_anchor=diff_result["normalized_anchor"],
        code=code,
        generated_diff=diff_result["generated_diff"],
        context_files=[item["path"] for item in context_files],
        proposal_id=proposal_id,
        proposal_path=proposal_path,
        warnings=list(dict.fromkeys(warnings)),
        safety_notes=list(dict.fromkeys(safety_notes)),
    )


@app.get("/workspace/proposals", response_model=list[ClientProposalSummary])
async def workspace_proposals() -> list[ClientProposalSummary]:
    return [ClientProposalSummary(**item) for item in list_client_proposals()]


@app.get("/workspace/proposals/{proposal_id}")
async def workspace_proposal_detail(proposal_id: str) -> dict:
    try:
        return load_client_proposal(proposal_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposal not found.") from exc
    except ValueError as exc:
        raise _bad_request(str(exc)) from exc


@app.post("/workspace/proposals/{proposal_id}/apply", response_model=ClientProposalApplyResponse)
async def workspace_apply_proposal(
    proposal_id: str,
    payload: ClientProposalApplyRequest,
) -> ClientProposalApplyResponse:
    try:
        proposal = load_client_proposal(proposal_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposal not found.") from exc
    except ValueError as exc:
        raise _bad_request(str(exc)) from exc

    try:
        require_project_authorization(
            str(proposal.get("project_path", "")),
            modify_files=True,
            apply_changes=True,
        )
    except AuthorizationError as exc:
        raise _forbidden(str(exc)) from exc

    result = apply_client_proposal(
        proposal_id=proposal_id,
        confirm_apply=payload.confirm_apply,
        allow_warnings=payload.allow_warnings,
        create_backup=payload.create_backup,
    )
    return ClientProposalApplyResponse(**result)
