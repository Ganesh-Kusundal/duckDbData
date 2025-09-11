"""
Risk Management Domain Repositories
"""

from .risk_profile_repository import RiskProfileRepository
from .risk_assessment_repository import RiskAssessmentRepository

__all__ = [
    'RiskProfileRepository',
    'RiskAssessmentRepository'
]

