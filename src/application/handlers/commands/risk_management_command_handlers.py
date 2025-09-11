"""
Risk Management Domain Command Handlers

Command handlers for risk management operations that orchestrate
risk assessment, monitoring, and limit enforcement.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from application.commands.base_command import CommandHandler, CommandResult
from application.commands.risk_management_commands import (
    AssessPortfolioRiskCommand, UpdateRiskLimitsCommand, CreateRiskProfileCommand,
    ExecuteRiskCheckCommand, UpdateRiskAssessmentCommand
)
from domain.risk_management.entities.risk_profile import RiskProfile
from domain.risk_management.entities.risk_assessment import RiskAssessment
from domain.risk_management.repositories.risk_profile_repository import RiskProfileRepository
from domain.risk_management.repositories.risk_assessment_repository import RiskAssessmentRepository
from domain.risk_management.services.risk_assessment_service import RiskAssessmentService
from domain.shared.exceptions import DomainException

logger = logging.getLogger(__name__)


class AssessPortfolioRiskCommandHandler(CommandHandler):
    """
    Handler for AssessPortfolioRiskCommand.

    Orchestrates portfolio risk assessment and analysis.
    """

    def __init__(self, risk_assessment_repository: Optional[RiskAssessmentRepository] = None,
                 risk_assessment_service: Optional[RiskAssessmentService] = None):
        self.risk_assessment_repository = risk_assessment_repository
        self.risk_assessment_service = risk_assessment_service

    @property
    def handled_command_type(self) -> str:
        return "AssessPortfolioRisk"

    async def handle(self, command: AssessPortfolioRiskCommand) -> CommandResult:
        """Handle portfolio risk assessment command."""
        try:
            logger.info(f"Assessing portfolio risk for {command.portfolio_id}")

            # Create risk assessment entity
            assessment = RiskAssessment(
                portfolio_id=command.portfolio_id,
                assessment_type=command.assessment_type,
                parameters=command.parameters,
                risk_profile_id=command.risk_profile_id
            )

            # Perform risk assessment
            assessment_result = {}
            if self.risk_assessment_service:
                result = await self.risk_assessment_service.assess_portfolio_risk(
                    command.portfolio_id, command.assessment_type, command.parameters
                )
                assessment.overall_risk_score = result.get('overall_risk_score', 0.0)
                assessment.risk_factors = result.get('risk_factors', {})
                assessment.recommendations = result.get('recommendations', [])
                assessment.metadata = result.get('metadata', {})
                assessment.status = "COMPLETED"
                assessment.completed_at = datetime.utcnow()
                assessment_result = result
            else:
                # Mock risk assessment
                assessment.overall_risk_score = 0.35
                assessment.risk_factors = {
                    "concentration": 0.2,
                    "volatility": 0.4,
                    "liquidity": 0.1,
                    "correlation": 0.3
                }
                assessment.recommendations = [
                    "Consider reducing exposure to high-volatility assets",
                    "Diversify across different sectors",
                    "Monitor liquidity requirements"
                ]
                assessment.metadata = {"method": "mock", "confidence": 0.85}
                assessment.status = "COMPLETED"
                assessment.completed_at = datetime.utcnow()

                assessment_result = {
                    "overall_risk_score": assessment.overall_risk_score,
                    "risk_factors": assessment.risk_factors,
                    "recommendations": assessment.recommendations,
                    "metadata": assessment.metadata
                }

            # Save assessment to repository
            if self.risk_assessment_repository:
                await self.risk_assessment_repository.save(assessment)

            return CommandResult(
                success=True,
                command_id=command.command_id,
                data={
                    "assessment_id": assessment.id,
                    "portfolio_id": assessment.portfolio_id,
                    "assessment_type": assessment.assessment_type,
                    "overall_risk_score": assessment.overall_risk_score,
                    "risk_factors": assessment.risk_factors,
                    "recommendations": assessment.recommendations,
                    "status": assessment.status
                }
            )

        except Exception as e:
            logger.error(f"Portfolio risk assessment failed: {e}")
            return CommandResult(
                success=False,
                command_id=command.command_id,
                error_message=str(e)
            )


class UpdateRiskLimitsCommandHandler(CommandHandler):
    """
    Handler for UpdateRiskLimitsCommand.

    Orchestrates the update of risk limits and thresholds.
    """

    def __init__(self, risk_profile_repository: Optional[RiskProfileRepository] = None):
        self.risk_profile_repository = risk_profile_repository

    @property
    def handled_command_type(self) -> str:
        return "UpdateRiskLimits"

    async def handle(self, command: UpdateRiskLimitsCommand) -> CommandResult:
        """Handle risk limits update command."""
        try:
            logger.info(f"Updating risk limits for profile {command.risk_profile_id}")

            if not self.risk_profile_repository:
                raise DomainException("Risk profile repository not available")

            # Find existing risk profile
            risk_profile = await self.risk_profile_repository.find_by_id(command.risk_profile_id)
            if not risk_profile:
                raise DomainException(f"Risk profile not found: {command.risk_profile_id}")

            # Apply limit updates
            updates_applied = []
            for limit_type, new_value in command.limit_updates.items():
                if hasattr(risk_profile, limit_type):
                    setattr(risk_profile, limit_type, new_value)
                    updates_applied.append(limit_type)
                else:
                    logger.warning(f"Unknown risk limit type: {limit_type}")

            # Update timestamp
            risk_profile.updated_at = datetime.utcnow()

            # Save updated profile
            await self.risk_profile_repository.update(risk_profile)

            return CommandResult(
                success=True,
                command_id=command.command_id,
                data={
                    "risk_profile_id": command.risk_profile_id,
                    "limits_updated": updates_applied,
                    "new_limits": {k: getattr(risk_profile, k) for k in updates_applied},
                    "updated_at": risk_profile.updated_at
                }
            )

        except Exception as e:
            logger.error(f"Risk limits update failed: {e}")
            return CommandResult(
                success=False,
                command_id=command.command_id,
                error_message=str(e)
            )


class CreateRiskProfileCommandHandler(CommandHandler):
    """
    Handler for CreateRiskProfileCommand.

    Orchestrates the creation of risk profiles and limit configurations.
    """

    def __init__(self, risk_profile_repository: Optional[RiskProfileRepository] = None):
        self.risk_profile_repository = risk_profile_repository

    @property
    def handled_command_type(self) -> str:
        return "CreateRiskProfile"

    async def handle(self, command: CreateRiskProfileCommand) -> CommandResult:
        """Handle risk profile creation command."""
        try:
            logger.info(f"Creating risk profile: {command.name}")

            # Create risk profile entity
            risk_profile = RiskProfile(
                name=command.name,
                description=command.description,
                risk_tolerance=command.risk_tolerance,
                max_position_size=command.max_position_size,
                max_portfolio_risk=command.max_portfolio_risk,
                max_daily_loss=command.max_daily_loss,
                max_drawdown=command.max_drawdown,
                required_margin=command.required_margin,
                restricted_sectors=command.restricted_sectors or [],
                allowed_asset_classes=command.allowed_asset_classes or [],
                is_active=command.is_active
            )

            # Save risk profile to repository
            if self.risk_profile_repository:
                await self.risk_profile_repository.save(risk_profile)

            return CommandResult(
                success=True,
                command_id=command.command_id,
                data={
                    "risk_profile_id": risk_profile.id,
                    "name": risk_profile.name,
                    "risk_tolerance": risk_profile.risk_tolerance,
                    "is_active": risk_profile.is_active,
                    "created_at": risk_profile.created_at
                }
            )

        except Exception as e:
            logger.error(f"Risk profile creation failed: {e}")
            return CommandResult(
                success=False,
                command_id=command.command_id,
                error_message=str(e)
            )


class ExecuteRiskCheckCommandHandler(CommandHandler):
    """
    Handler for ExecuteRiskCheckCommand.

    Orchestrates real-time risk checking and limit validation.
    """

    def __init__(self, risk_assessment_service: Optional[RiskAssessmentService] = None):
        self.risk_assessment_service = risk_assessment_service

    @property
    def handled_command_type(self) -> str:
        return "ExecuteRiskCheck"

    async def handle(self, command: ExecuteRiskCheckCommand) -> CommandResult:
        """Handle risk check execution command."""
        try:
            logger.info(f"Executing risk check for {command.portfolio_id}")

            # Perform risk check
            check_result = {}
            if self.risk_assessment_service:
                result = await self.risk_assessment_service.check_risk_limits(
                    command.portfolio_id, command.check_type, command.parameters
                )
                check_result = result
            else:
                # Mock risk check
                check_result = {
                    "portfolio_id": command.portfolio_id,
                    "check_type": command.check_type,
                    "limits_checked": ["position_size", "daily_loss", "drawdown"],
                    "violations_found": 0,
                    "warnings_issued": 1,
                    "status": "PASS",
                    "warnings": [
                        {
                            "type": "high_concentration",
                            "message": "Portfolio concentration in tech sector is above recommended limit",
                            "severity": "MEDIUM"
                        }
                    ]
                }

            return CommandResult(
                success=True,
                command_id=command.command_id,
                data={
                    "portfolio_id": command.portfolio_id,
                    "check_type": command.check_type,
                    "check_result": check_result,
                    "executed_at": datetime.utcnow()
                }
            )

        except Exception as e:
            logger.error(f"Risk check execution failed: {e}")
            return CommandResult(
                success=False,
                command_id=command.command_id,
                error_message=str(e)
            )


class UpdateRiskAssessmentCommandHandler(CommandHandler):
    """
    Handler for UpdateRiskAssessmentCommand.

    Orchestrates the update of existing risk assessments.
    """

    def __init__(self, risk_assessment_repository: Optional[RiskAssessmentRepository] = None):
        self.risk_assessment_repository = risk_assessment_repository

    @property
    def handled_command_type(self) -> str:
        return "UpdateRiskAssessment"

    async def handle(self, command: UpdateRiskAssessmentCommand) -> CommandResult:
        """Handle risk assessment update command."""
        try:
            logger.info(f"Updating risk assessment {command.assessment_id}")

            if not self.risk_assessment_repository:
                raise DomainException("Risk assessment repository not available")

            # Find existing assessment
            assessment = await self.risk_assessment_repository.find_by_id(command.assessment_id)
            if not assessment:
                raise DomainException(f"Risk assessment not found: {command.assessment_id}")

            # Apply updates
            for key, value in command.updates.items():
                if hasattr(assessment, key):
                    setattr(assessment, key, value)

            # Update timestamp
            assessment.updated_at = datetime.utcnow()

            # Save updated assessment
            await self.risk_assessment_repository.update(assessment)

            return CommandResult(
                success=True,
                command_id=command.command_id,
                data={
                    "assessment_id": command.assessment_id,
                    "updates_applied": list(command.updates.keys()),
                    "updated_at": assessment.updated_at
                }
            )

        except Exception as e:
            logger.error(f"Risk assessment update failed: {e}")
            return CommandResult(
                success=False,
                command_id=command.command_id,
                error_message=str(e)
            )
