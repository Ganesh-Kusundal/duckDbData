"""
Risk Management Domain Query Handlers

Query handlers for risk management operations that retrieve risk data
and assessment results efficiently.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from application.queries.base_query import QueryHandler, QueryResult
from application.queries.risk_management_queries import (
    GetRiskAssessmentByIdQuery, GetRiskAssessmentsByPortfolioQuery,
    GetRiskProfilesQuery, GetRiskProfileByIdQuery
)
from domain.risk_management.repositories.risk_profile_repository import RiskProfileRepository
from domain.risk_management.repositories.risk_assessment_repository import RiskAssessmentRepository
from domain.shared.exceptions import DomainException

logger = logging.getLogger(__name__)


class GetRiskAssessmentByIdQueryHandler(QueryHandler):
    """
    Handler for GetRiskAssessmentByIdQuery.

    Retrieves a specific risk assessment by its ID.
    """

    def __init__(self, risk_assessment_repository: Optional[RiskAssessmentRepository] = None):
        self.risk_assessment_repository = risk_assessment_repository

    @property
    def handled_query_type(self) -> str:
        return "GetRiskAssessmentById"

    async def handle(self, query: GetRiskAssessmentByIdQuery) -> QueryResult:
        """Handle get risk assessment by ID query."""
        try:
            logger.info(f"Retrieving risk assessment {query.assessment_id}")

            if not self.risk_assessment_repository:
                raise DomainException("Risk assessment repository not available")

            assessment = await self.risk_assessment_repository.find_by_id(query.assessment_id)
            if not assessment:
                return QueryResult(
                    success=True,
                    query_id=query.query_id,
                    data=None
                )

            return QueryResult(
                success=True,
                query_id=query.query_id,
                data={
                    "assessment": {
                        "id": assessment.id,
                        "portfolio_id": assessment.portfolio_id,
                        "assessment_type": assessment.assessment_type,
                        "overall_risk_score": assessment.overall_risk_score,
                        "risk_factors": assessment.risk_factors,
                        "recommendations": assessment.recommendations,
                        "parameters": assessment.parameters,
                        "metadata": assessment.metadata,
                        "status": assessment.status,
                        "created_at": assessment.created_at,
                        "completed_at": assessment.completed_at
                    }
                }
            )

        except Exception as e:
            logger.error(f"Get risk assessment by ID failed: {e}")
            return QueryResult(
                success=False,
                query_id=query.query_id,
                error_message=str(e)
            )


class GetRiskAssessmentsByPortfolioQueryHandler(QueryHandler):
    """
    Handler for GetRiskAssessmentsByPortfolioQuery.

    Retrieves risk assessments for a specific portfolio with filtering.
    """

    def __init__(self, risk_assessment_repository: Optional[RiskAssessmentRepository] = None):
        self.risk_assessment_repository = risk_assessment_repository

    @property
    def handled_query_type(self) -> str:
        return "GetRiskAssessmentsByPortfolio"

    async def handle(self, query: GetRiskAssessmentsByPortfolioQuery) -> QueryResult:
        """Handle get risk assessments by portfolio query."""
        try:
            logger.info(f"Retrieving risk assessments for portfolio {query.portfolio_id}")

            if not self.risk_assessment_repository:
                raise DomainException("Risk assessment repository not available")

            # Build filters
            filters = {"portfolio_id": query.portfolio_id}
            if query.assessment_type:
                filters["assessment_type"] = query.assessment_type
            if query.status:
                filters["status"] = query.status

            # Add date range filter
            if query.start_date or query.end_date:
                if query.start_date:
                    filters["start_date"] = query.start_date
                if query.end_date:
                    filters["end_date"] = query.end_date

            result = await self.risk_assessment_repository.find_by_criteria(
                filters, limit=query.limit, offset=query.offset
            )

            assessments = result.data if result.success and result.data else []

            # Calculate summary statistics
            total_assessments = len(assessments)
            avg_risk_score = sum(a.overall_risk_score for a in assessments) / max(1, total_assessments)
            high_risk_count = sum(1 for a in assessments if a.overall_risk_score > 0.7)
            completed_count = sum(1 for a in assessments if a.status == "COMPLETED")

            return QueryResult(
                success=True,
                query_id=query.query_id,
                data={
                    "assessments": [
                        {
                            "id": assessment.id,
                            "assessment_type": assessment.assessment_type,
                            "overall_risk_score": assessment.overall_risk_score,
                            "status": assessment.status,
                            "completed_at": assessment.completed_at
                        }
                        for assessment in assessments
                    ],
                    "summary": {
                        "total_assessments": total_assessments,
                        "average_risk_score": avg_risk_score,
                        "high_risk_count": high_risk_count,
                        "completion_rate": (completed_count / max(1, total_assessments)) * 100
                    },
                    "portfolio_id": query.portfolio_id,
                    "filters_applied": filters
                }
            )

        except Exception as e:
            logger.error(f"Get risk assessments by portfolio failed: {e}")
            return QueryResult(
                success=False,
                query_id=query.query_id,
                error_message=str(e)
            )


class GetRiskProfilesQueryHandler(QueryHandler):
    """
    Handler for GetRiskProfilesQuery.

    Retrieves risk profiles with filtering and pagination.
    """

    def __init__(self, risk_profile_repository: Optional[RiskProfileRepository] = None):
        self.risk_profile_repository = risk_profile_repository

    @property
    def handled_query_type(self) -> str:
        return "GetRiskProfiles"

    async def handle(self, query: GetRiskProfilesQuery) -> QueryResult:
        """Handle get risk profiles query."""
        try:
            logger.info("Retrieving risk profiles")

            if not self.risk_profile_repository:
                raise DomainException("Risk profile repository not available")

            # Build filters
            filters = {}
            if query.is_active is not None:
                filters["is_active"] = query.is_active
            if query.risk_tolerance:
                filters["risk_tolerance"] = query.risk_tolerance

            result = await self.risk_profile_repository.find_by_criteria(
                filters, limit=query.limit, offset=query.offset
            )

            profiles = result.data if result.success and result.data else []

            return QueryResult(
                success=True,
                query_id=query.query_id,
                data={
                    "profiles": [
                        {
                            "id": profile.id,
                            "name": profile.name,
                            "description": profile.description,
                            "risk_tolerance": profile.risk_tolerance,
                            "max_position_size": profile.max_position_size,
                            "max_portfolio_risk": profile.max_portfolio_risk,
                            "is_active": profile.is_active,
                            "created_at": profile.created_at
                        }
                        for profile in profiles
                    ],
                    "total_count": len(profiles),
                    "active_count": sum(1 for p in profiles if p.is_active),
                    "filters_applied": filters
                }
            )

        except Exception as e:
            logger.error(f"Get risk profiles failed: {e}")
            return QueryResult(
                success=False,
                query_id=query.query_id,
                error_message=str(e)
            )


class GetRiskProfileByIdQueryHandler(QueryHandler):
    """
    Handler for GetRiskProfileByIdQuery.

    Retrieves a specific risk profile by its ID.
    """

    def __init__(self, risk_profile_repository: Optional[RiskProfileRepository] = None):
        self.risk_profile_repository = risk_profile_repository

    @property
    def handled_query_type(self) -> str:
        return "GetRiskProfileById"

    async def handle(self, query: GetRiskProfileByIdQuery) -> QueryResult:
        """Handle get risk profile by ID query."""
        try:
            logger.info(f"Retrieving risk profile {query.profile_id}")

            if not self.risk_profile_repository:
                raise DomainException("Risk profile repository not available")

            profile = await self.risk_profile_repository.find_by_id(query.profile_id)
            if not profile:
                return QueryResult(
                    success=True,
                    query_id=query.query_id,
                    data=None
                )

            return QueryResult(
                success=True,
                query_id=query.query_id,
                data={
                    "profile": {
                        "id": profile.id,
                        "name": profile.name,
                        "description": profile.description,
                        "risk_tolerance": profile.risk_tolerance,
                        "max_position_size": profile.max_position_size,
                        "max_portfolio_risk": profile.max_portfolio_risk,
                        "max_daily_loss": profile.max_daily_loss,
                        "max_drawdown": profile.max_drawdown,
                        "required_margin": profile.required_margin,
                        "restricted_sectors": profile.restricted_sectors,
                        "allowed_asset_classes": profile.allowed_asset_classes,
                        "is_active": profile.is_active,
                        "created_at": profile.created_at,
                        "updated_at": profile.updated_at
                    }
                }
            )

        except Exception as e:
            logger.error(f"Get risk profile by ID failed: {e}")
            return QueryResult(
                success=False,
                query_id=query.query_id,
                error_message=str(e)
            )
