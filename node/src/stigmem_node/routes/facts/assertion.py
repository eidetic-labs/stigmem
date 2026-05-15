"""POST /v1/facts route wrapper and plugin hook dispatch."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status

from ...auth import Identity, resolve_identity
from ...models.facts import AssertRequest, FactRecord
from ...plugins import Deny, Failure, Success, TenantContext, get_registry
from ...tracing import start_span
from .._facts_assert import assert_fact_impl as _assert_fact_impl
from .common import router


@router.post("", response_model=FactRecord, status_code=status.HTTP_201_CREATED)
def assert_fact(
    req: AssertRequest,
    identity: Annotated[Identity, Depends(resolve_identity)],
) -> FactRecord:
    """Assert a fact into the fabric.

    Covered by Spec-03-HTTP-API and Spec-01-Fact-Model. Normalizes
    entity/source URIs on ingest.
    """
    request_id = str(uuid.uuid4())
    tenant = TenantContext(tenant_id=identity.tenant_id)
    registry = get_registry()
    with start_span(
        "stigmem.assert_fact",
        **{"stigmem.tenant": identity.tenant_id, "stigmem.principal": identity.entity_uri},
    ) as _span:
        decision = registry.fire_voting(
            "pre_assert_authorize",
            req=req,
            identity=identity,
            tenant=tenant,
            request_id=request_id,
        )
        if isinstance(decision, Deny):
            registry.fire_fire_and_forget(
                "post_assert_audit",
                fact=None,
                req=req,
                identity=identity,
                tenant=tenant,
                request_id=request_id,
                outcome=Failure(reason=decision.reason),
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=decision.reason)

        decision = registry.fire_voting(
            "pre_assert_validate",
            req=req,
            identity=identity,
            tenant=tenant,
            request_id=request_id,
        )
        if isinstance(decision, Deny):
            registry.fire_fire_and_forget(
                "post_assert_audit",
                fact=None,
                req=req,
                identity=identity,
                tenant=tenant,
                request_id=request_id,
                outcome=Failure(reason=decision.reason),
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=decision.reason
            )

        req = registry.fire_filter_chain(
            "pre_assert_transform",
            req,
            identity=identity,
            tenant=tenant,
            request_id=request_id,
        )
        try:
            fact = _assert_fact_impl(req, identity, _span, request_id=request_id, tenant=tenant)
            registry.fire_fire_and_forget(
                "post_assert_propagate",
                fact=fact,
                identity=identity,
                tenant=tenant,
                request_id=request_id,
            )
            registry.fire_fire_and_forget(
                "post_assert_audit",
                fact=fact,
                req=req,
                identity=identity,
                tenant=tenant,
                request_id=request_id,
                outcome=Success(),
            )
            return fact
        except Exception as exc:
            registry.fire_fire_and_forget(
                "post_assert_audit",
                fact=None,
                req=req,
                identity=identity,
                tenant=tenant,
                request_id=request_id,
                outcome=Failure(reason=str(exc), exception_type=type(exc).__name__),
            )
            raise
