"""System coordinators — one per Alchymine pillar.

Each coordinator wraps the corresponding engine module, invokes the
right calculations, runs quality gate validation, and returns a
uniform CoordinatorResult. Coordinators handle ImportError and
runtime exceptions gracefully so the orchestrator can continue with
the remaining systems when one is unavailable (degraded mode).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


# ─── Coordinator status ──────────────────────────────────────────────


class CoordinatorStatus(str, Enum):
    """Status of a coordinator's processing result."""

    SUCCESS = "success"
    ERROR = "error"
    DEGRADED = "degraded"


# ─── Coordinator result ──────────────────────────────────────────────


@dataclass
class CoordinatorResult:
    """Uniform result from any system coordinator.

    Attributes
    ----------
    system:
        Name of the system that produced this result.
    status:
        Processing status (success / error / degraded).
    data:
        The output data dictionary from the engine.
    errors:
        Error messages collected during processing.
    quality_passed:
        Whether the quality gate passed for this output.
    """

    system: str
    status: str  # CoordinatorStatus value
    data: dict = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    quality_passed: bool = True


# ─── Base coordinator ────────────────────────────────────────────────


class BaseCoordinator:
    """Abstract base for system coordinators.

    Subclasses must implement ``_execute`` to perform the actual
    engine calls. The public ``process`` method wraps ``_execute``
    in error handling and quality gate validation.
    """

    system_name: str = "base"

    async def process(
        self,
        user_id: str,
        request_data: dict,
    ) -> CoordinatorResult:
        """Process a request through this system's coordinator.

        Parameters
        ----------
        user_id:
            The user's profile identifier.
        request_data:
            Request-specific data to pass to the engine.

        Returns
        -------
        CoordinatorResult
            The result with status, data, errors, and quality flag.
        """
        try:
            result = await self._execute(user_id, request_data)

            # Run quality gate validation
            quality_result = self._run_quality_gate(result.data)
            result.quality_passed = quality_result

            if not quality_result:
                if result.status == CoordinatorStatus.SUCCESS.value:
                    result.status = CoordinatorStatus.DEGRADED.value
                result.errors.append(
                    f"Quality gate validation failed for {self.system_name}"
                )

            return result

        except Exception as exc:
            logger.exception(
                "Coordinator %s failed for user %s: %s",
                self.system_name,
                user_id,
                exc,
            )
            return CoordinatorResult(
                system=self.system_name,
                status=CoordinatorStatus.ERROR.value,
                data={},
                errors=[f"{self.system_name} coordinator error: {exc!s}"],
                quality_passed=False,
            )

    async def _execute(
        self,
        user_id: str,
        request_data: dict,
    ) -> CoordinatorResult:
        """Execute the system-specific logic.

        Subclasses must override this method.

        Parameters
        ----------
        user_id:
            The user's profile identifier.
        request_data:
            Request-specific data.

        Returns
        -------
        CoordinatorResult
            The processing result before quality gate validation.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement _execute"
        )

    def _run_quality_gate(self, output: dict) -> bool:
        """Run the quality gate for this system's output.

        Default implementation uses the quality gate dispatcher.
        Systems without a dedicated gate (e.g. intelligence) return True.

        Parameters
        ----------
        output:
            The output data dictionary to validate.

        Returns
        -------
        bool
            True if the quality gate passed, False otherwise.
        """
        try:
            from alchymine.agents.quality.validators import run_quality_gate

            gate_result = run_quality_gate(output, system=self.system_name)
            return gate_result.passed
        except ValueError:
            # No quality gate registered for this system — pass by default
            return True
        except Exception as exc:
            logger.warning(
                "Quality gate error for %s: %s", self.system_name, exc
            )
            return True


# ─── Intelligence coordinator ────────────────────────────────────────


class IntelligenceCoordinator(BaseCoordinator):
    """Coordinator for the Personalized Intelligence system.

    Handles numerology, astrology, archetype, and personality
    calculations.
    """

    system_name = "intelligence"

    async def _execute(
        self,
        user_id: str,
        request_data: dict,
    ) -> CoordinatorResult:
        errors: list[str] = []
        data: dict = {}

        # Numerology
        try:
            from alchymine.engine.numerology import (
                calculate_pythagorean_profile,
            )

            full_name = request_data.get("full_name", "")
            birth_date = request_data.get("birth_date")

            if full_name and birth_date:
                profile = calculate_pythagorean_profile(full_name, birth_date)
                data["numerology"] = {
                    "life_path": profile.life_path,
                    "expression": profile.expression,
                    "soul_urge": profile.soul_urge,
                    "personality": profile.personality,
                    "personal_year": profile.personal_year,
                    "personal_month": profile.personal_month,
                }
            else:
                errors.append(
                    "Intelligence: missing full_name or birth_date for numerology"
                )
        except ImportError:
            errors.append("Intelligence: numerology engine not available")
        except Exception as exc:
            errors.append(f"Intelligence: numerology error — {exc!s}")

        # Astrology
        try:
            from alchymine.engine.astrology import (
                approximate_sun_sign,
                approximate_sun_degree,
            )

            birth_date = request_data.get("birth_date")
            if birth_date:
                sun_sign = approximate_sun_sign(birth_date)
                sun_degree = approximate_sun_degree(birth_date)
                data["astrology"] = {
                    "sun_sign": sun_sign,
                    "sun_degree": sun_degree,
                }
            else:
                errors.append("Intelligence: missing birth_date for astrology")
        except ImportError:
            errors.append("Intelligence: astrology engine not available")
        except Exception as exc:
            errors.append(f"Intelligence: astrology error — {exc!s}")

        status = CoordinatorStatus.SUCCESS.value
        if errors and not data:
            status = CoordinatorStatus.ERROR.value
        elif errors:
            status = CoordinatorStatus.DEGRADED.value

        return CoordinatorResult(
            system=self.system_name,
            status=status,
            data=data,
            errors=errors,
        )


# ─── Healing coordinator ─────────────────────────────────────────────


class HealingCoordinator(BaseCoordinator):
    """Coordinator for the Ethical Healing system.

    Handles modality matching, breathwork patterns, and crisis
    detection.
    """

    system_name = "healing"

    async def _execute(
        self,
        user_id: str,
        request_data: dict,
    ) -> CoordinatorResult:
        errors: list[str] = []
        data: dict = {
            "disclaimers": [
                "This is not medical advice. Please consult a qualified "
                "healthcare professional for medical concerns."
            ],
        }

        # Crisis detection
        try:
            from alchymine.engine.healing import detect_crisis

            user_text = request_data.get("text", "")
            if user_text:
                crisis = detect_crisis(user_text)
                data["crisis_flag"] = crisis.is_crisis
                if crisis.is_crisis:
                    data["crisis_response"] = {
                        "severity": crisis.severity.value if crisis.severity else None,
                        "resources": [
                            {"name": r.name, "contact": r.contact}
                            for r in (crisis.resources or [])
                        ],
                    }
        except ImportError:
            errors.append("Healing: crisis detection not available")
        except Exception as exc:
            errors.append(f"Healing: crisis detection error — {exc!s}")

        # Modality matching
        try:
            from alchymine.engine.healing import match_modalities

            archetype = request_data.get("archetype")
            attachment = request_data.get("attachment_style")
            intention = request_data.get("intention")

            if archetype and attachment and intention:
                modalities = match_modalities(archetype, attachment, intention)
                data["recommended_modalities"] = [
                    {
                        "modality": m.modality,
                        "skill_trigger": m.skill_trigger,
                        "preference_score": m.preference_score,
                        "difficulty_level": m.difficulty_level.value
                        if hasattr(m.difficulty_level, "value")
                        else str(m.difficulty_level),
                    }
                    for m in modalities
                ]
        except ImportError:
            errors.append("Healing: modality engine not available")
        except Exception as exc:
            errors.append(f"Healing: modality matching error — {exc!s}")

        status = CoordinatorStatus.SUCCESS.value
        if errors and len(data) <= 1:  # Only disclaimers
            status = CoordinatorStatus.DEGRADED.value
        elif errors:
            status = CoordinatorStatus.DEGRADED.value

        return CoordinatorResult(
            system=self.system_name,
            status=status,
            data=data,
            errors=errors,
        )


# ─── Wealth coordinator ──────────────────────────────────────────────


class WealthCoordinator(BaseCoordinator):
    """Coordinator for the Generational Wealth system.

    Handles wealth archetype mapping, lever prioritisation, debt
    strategies, and activation plans. All calculations are
    deterministic.
    """

    system_name = "wealth"

    async def _execute(
        self,
        user_id: str,
        request_data: dict,
    ) -> CoordinatorResult:
        errors: list[str] = []
        data: dict = {
            "disclaimers": [
                "This is not financial advice. Please consult a qualified "
                "financial advisor for personalised recommendations."
            ],
        }

        # Wealth archetype
        try:
            from alchymine.engine.wealth import map_wealth_archetype

            life_path = request_data.get("life_path")
            risk_tolerance = request_data.get("risk_tolerance", "moderate")

            if life_path is not None:
                archetype = map_wealth_archetype(life_path, risk_tolerance)
                data["wealth_archetype"] = {
                    "name": archetype.name,
                    "description": archetype.description,
                }
        except ImportError:
            errors.append("Wealth: archetype engine not available")
        except Exception as exc:
            errors.append(f"Wealth: archetype error — {exc!s}")

        # Lever prioritisation
        try:
            from alchymine.engine.wealth import prioritize_levers

            life_path = request_data.get("life_path")
            risk_tolerance = request_data.get("risk_tolerance", "moderate")
            intention = request_data.get("intention")

            if life_path is not None and intention:
                levers = prioritize_levers(life_path, risk_tolerance, intention)
                data["lever_priorities"] = [
                    lev.value if hasattr(lev, "value") else str(lev)
                    for lev in levers
                ]
        except ImportError:
            errors.append("Wealth: lever engine not available")
        except Exception as exc:
            errors.append(f"Wealth: lever prioritisation error — {exc!s}")

        data["calculations"] = {}

        status = CoordinatorStatus.SUCCESS.value
        if errors and len(data) <= 2:  # Only disclaimers + empty calculations
            status = CoordinatorStatus.DEGRADED.value
        elif errors:
            status = CoordinatorStatus.DEGRADED.value

        return CoordinatorResult(
            system=self.system_name,
            status=status,
            data=data,
            errors=errors,
        )


# ─── Creative coordinator ────────────────────────────────────────────


class CreativeCoordinator(BaseCoordinator):
    """Coordinator for the Creative Development system.

    Handles Guilford assessment, Creative DNA, style analysis,
    and project suggestions.
    """

    system_name = "creative"

    async def _execute(
        self,
        user_id: str,
        request_data: dict,
    ) -> CoordinatorResult:
        errors: list[str] = []
        data: dict = {}

        # Creative orientation from life path
        try:
            from alchymine.engine.creative import derive_creative_orientation

            life_path = request_data.get("life_path")
            if life_path is not None:
                orientation = derive_creative_orientation(life_path)
                data["creative_orientation"] = orientation
        except ImportError:
            errors.append("Creative: orientation engine not available")
        except Exception as exc:
            errors.append(f"Creative: orientation error — {exc!s}")

        # Style analysis
        try:
            from alchymine.engine.creative import identify_strengths

            guilford_scores = request_data.get("guilford_scores")
            if guilford_scores:
                strengths = identify_strengths(guilford_scores)
                data["strengths"] = strengths
        except ImportError:
            errors.append("Creative: style engine not available")
        except Exception as exc:
            errors.append(f"Creative: style analysis error — {exc!s}")

        status = CoordinatorStatus.SUCCESS.value
        if errors and not data:
            status = CoordinatorStatus.ERROR.value
        elif errors:
            status = CoordinatorStatus.DEGRADED.value

        return CoordinatorResult(
            system=self.system_name,
            status=status,
            data=data,
            errors=errors,
        )


# ─── Perspective coordinator ─────────────────────────────────────────


class PerspectiveCoordinator(BaseCoordinator):
    """Coordinator for the Perspective Enhancement system.

    Handles decision frameworks, bias detection, Kegan stage
    assessment, and scenario modelling.
    """

    system_name = "perspective"

    async def _execute(
        self,
        user_id: str,
        request_data: dict,
    ) -> CoordinatorResult:
        errors: list[str] = []
        data: dict = {}

        # Bias detection
        try:
            from alchymine.engine.perspective import detect_biases

            reasoning_text = request_data.get("text", "")
            if reasoning_text:
                biases = detect_biases(reasoning_text)
                data["detected_biases"] = biases
        except ImportError:
            errors.append("Perspective: bias engine not available")
        except Exception as exc:
            errors.append(f"Perspective: bias detection error — {exc!s}")

        # Kegan assessment
        try:
            from alchymine.engine.perspective import assess_kegan_stage

            responses = request_data.get("kegan_responses")
            if responses:
                stage = assess_kegan_stage(responses)
                data["kegan_stage"] = stage
        except ImportError:
            errors.append("Perspective: kegan engine not available")
        except Exception as exc:
            errors.append(f"Perspective: kegan assessment error — {exc!s}")

        # Decision framework
        try:
            from alchymine.engine.perspective import pros_cons_analysis

            decision = request_data.get("decision")
            pros = request_data.get("pros", [])
            cons = request_data.get("cons", [])
            if decision:
                analysis = pros_cons_analysis(decision, pros, cons)
                data["decision_analysis"] = analysis
        except ImportError:
            errors.append("Perspective: framework engine not available")
        except Exception as exc:
            errors.append(f"Perspective: framework error — {exc!s}")

        status = CoordinatorStatus.SUCCESS.value
        if errors and not data:
            status = CoordinatorStatus.ERROR.value
        elif errors:
            status = CoordinatorStatus.DEGRADED.value

        return CoordinatorResult(
            system=self.system_name,
            status=status,
            data=data,
            errors=errors,
        )
