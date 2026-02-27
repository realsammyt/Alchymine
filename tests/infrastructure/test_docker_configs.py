"""Tests for Docker Compose and Dockerfile configuration files.

Validates that all infrastructure configuration files:
- Are valid YAML/Dockerfile syntax
- Define all required services with health checks
- Include resource limits and restart policies
- Reference Dockerfiles that exist
- CI workflow has required jobs
"""

from __future__ import annotations

from pathlib import Path

import yaml
import pytest


# ─── Paths ────────────────────────────────────────────────────────────────────

# The tests live at tests/infrastructure/, project root is two levels up.
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
INFRA_DIR = PROJECT_ROOT / "infrastructure"
GITHUB_DIR = PROJECT_ROOT / ".github"


# ─── Helpers ──────────────────────────────────────────────────────────────────


def load_yaml(path: Path) -> dict:
    """Load and parse a YAML file, raising a clear error on failure."""
    assert path.exists(), f"YAML file does not exist: {path}"
    with open(path) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict), f"YAML file did not parse as a mapping: {path}"
    return data


# ─── docker-compose.yml ──────────────────────────────────────────────────────


class TestDockerComposeYml:
    """Tests for the production docker-compose.yml."""

    @pytest.fixture(autouse=True)
    def _load(self) -> None:
        self.compose = load_yaml(INFRA_DIR / "docker-compose.yml")

    def test_is_valid_yaml(self) -> None:
        """docker-compose.yml parses as valid YAML."""
        assert self.compose is not None

    def test_has_services_key(self) -> None:
        """Top-level 'services' key exists."""
        assert "services" in self.compose

    def test_required_services_defined(self) -> None:
        """All five required services are present: api, web, db, redis, worker."""
        services = set(self.compose["services"].keys())
        required = {"api", "web", "db", "redis", "worker"}
        missing = required - services
        assert not missing, f"Missing required services: {missing}"

    @pytest.mark.parametrize("service", ["api", "web", "db", "redis", "worker"])
    def test_healthcheck_configured(self, service: str) -> None:
        """Every required service has a healthcheck block."""
        svc = self.compose["services"][service]
        assert "healthcheck" in svc, f"Service '{service}' is missing a healthcheck"
        hc = svc["healthcheck"]
        assert "test" in hc, f"Service '{service}' healthcheck is missing 'test'"

    @pytest.mark.parametrize("service", ["api", "web", "db", "redis", "worker"])
    def test_restart_policy(self, service: str) -> None:
        """Every service has a restart policy."""
        svc = self.compose["services"][service]
        assert "restart" in svc, f"Service '{service}' is missing restart policy"

    @pytest.mark.parametrize("service", ["api", "web", "db", "redis", "worker"])
    def test_resource_limits(self, service: str) -> None:
        """Every service has resource limits defined under deploy.resources.limits."""
        svc = self.compose["services"][service]
        assert "deploy" in svc, f"Service '{service}' is missing deploy block"
        deploy = svc["deploy"]
        assert "resources" in deploy, f"Service '{service}' is missing deploy.resources"
        resources = deploy["resources"]
        assert "limits" in resources, f"Service '{service}' is missing deploy.resources.limits"
        limits = resources["limits"]
        assert "memory" in limits, f"Service '{service}' is missing memory limit"

    def test_named_volumes(self) -> None:
        """Named volumes are defined for db and redis data persistence."""
        assert "volumes" in self.compose, "Top-level 'volumes' key missing"
        volumes = set(self.compose["volumes"].keys())
        assert "db_data" in volumes, "Missing named volume: db_data"
        assert "redis_data" in volumes, "Missing named volume: redis_data"

    def test_internal_network(self) -> None:
        """A named network is defined for inter-service communication."""
        assert "networks" in self.compose, "Top-level 'networks' key missing"
        networks = self.compose["networks"]
        assert len(networks) >= 1, "At least one network should be defined"

    def test_api_exposes_port_8000(self) -> None:
        """API service exposes port 8000."""
        api = self.compose["services"]["api"]
        ports = api.get("ports", [])
        port_strs = [str(p) for p in ports]
        assert any("8000" in p for p in port_strs), "API should expose port 8000"

    def test_web_exposes_port_3000(self) -> None:
        """Web service exposes port 3000."""
        web = self.compose["services"]["web"]
        ports = web.get("ports", [])
        port_strs = [str(p) for p in ports]
        assert any("3000" in p for p in port_strs), "Web should expose port 3000"

    def test_db_uses_postgres_15(self) -> None:
        """DB service uses PostgreSQL 15."""
        db = self.compose["services"]["db"]
        image = db.get("image", "")
        assert "postgres:15" in image, f"DB should use postgres:15, got: {image}"

    def test_redis_uses_redis_7(self) -> None:
        """Redis service uses Redis 7."""
        redis_svc = self.compose["services"]["redis"]
        image = redis_svc.get("image", "")
        assert "redis:7" in image, f"Redis should use redis:7, got: {image}"

    def test_worker_same_image_as_api(self) -> None:
        """Worker service uses the same Dockerfile as the API."""
        api_build = self.compose["services"]["api"].get("build", {})
        worker_build = self.compose["services"]["worker"].get("build", {})
        api_dockerfile = api_build.get("dockerfile", "")
        worker_dockerfile = worker_build.get("dockerfile", "")
        assert api_dockerfile == worker_dockerfile, (
            f"Worker should use the same Dockerfile as API. "
            f"API: {api_dockerfile}, Worker: {worker_dockerfile}"
        )


# ─── docker-compose.dev.yml ──────────────────────────────────────────────────


class TestDockerComposeDevYml:
    """Tests for the dev override docker-compose.dev.yml."""

    @pytest.fixture(autouse=True)
    def _load(self) -> None:
        self.compose = load_yaml(INFRA_DIR / "docker-compose.dev.yml")

    def test_is_valid_yaml(self) -> None:
        """docker-compose.dev.yml parses as valid YAML."""
        assert self.compose is not None

    def test_has_services_key(self) -> None:
        """Top-level 'services' key exists."""
        assert "services" in self.compose

    def test_api_has_volume_mounts(self) -> None:
        """API service has volume mounts for live reload."""
        api = self.compose["services"].get("api", {})
        assert "volumes" in api, "Dev API should have volume mounts"
        assert len(api["volumes"]) > 0, "Dev API should have at least one volume mount"

    def test_web_has_volume_mounts(self) -> None:
        """Web service has volume mounts for live reload."""
        web = self.compose["services"].get("web", {})
        assert "volumes" in web, "Dev web should have volume mounts"

    def test_debug_port_exposed(self) -> None:
        """API debug port (5678) is exposed for debugpy."""
        api = self.compose["services"].get("api", {})
        ports = [str(p) for p in api.get("ports", [])]
        assert any("5678" in p for p in ports), "Dev API should expose debug port 5678"


# ─── Dockerfiles ──────────────────────────────────────────────────────────────


class TestDockerfiles:
    """Validate that Dockerfiles exist and contain required directives."""

    def test_dockerfile_api_exists(self) -> None:
        """Dockerfile.api exists."""
        path = INFRA_DIR / "Dockerfile.api"
        assert path.exists(), f"Dockerfile.api not found at {path}"

    def test_dockerfile_web_exists(self) -> None:
        """Dockerfile.web exists."""
        path = INFRA_DIR / "Dockerfile.web"
        assert path.exists(), f"Dockerfile.web not found at {path}"

    def test_dockerfile_api_is_multistage(self) -> None:
        """Dockerfile.api uses multi-stage build (multiple FROM instructions)."""
        content = (INFRA_DIR / "Dockerfile.api").read_text()
        from_count = sum(1 for line in content.splitlines() if line.strip().startswith("FROM "))
        assert from_count >= 2, f"Expected multi-stage (>=2 FROM), got {from_count}"

    def test_dockerfile_web_is_multistage(self) -> None:
        """Dockerfile.web uses multi-stage build (multiple FROM instructions)."""
        content = (INFRA_DIR / "Dockerfile.web").read_text()
        from_count = sum(1 for line in content.splitlines() if line.strip().startswith("FROM "))
        assert from_count >= 2, f"Expected multi-stage (>=2 FROM), got {from_count}"

    def test_dockerfile_api_base_python311(self) -> None:
        """Dockerfile.api uses python:3.11-slim as base."""
        content = (INFRA_DIR / "Dockerfile.api").read_text()
        assert "python:3.11-slim" in content, "Dockerfile.api should use python:3.11-slim"

    def test_dockerfile_web_base_node20(self) -> None:
        """Dockerfile.web uses node:20-alpine as base."""
        content = (INFRA_DIR / "Dockerfile.web").read_text()
        assert "node:20-alpine" in content, "Dockerfile.web should use node:20-alpine"

    def test_dockerfile_api_non_root_user(self) -> None:
        """Dockerfile.api runs as non-root user."""
        content = (INFRA_DIR / "Dockerfile.api").read_text()
        assert "USER " in content, "Dockerfile.api should switch to non-root USER"
        # Verify the USER directive is not root
        user_lines = [
            line.strip() for line in content.splitlines()
            if line.strip().startswith("USER ")
        ]
        assert user_lines, "No USER directive found"
        for line in user_lines:
            user = line.split()[1]
            assert user != "root", "Dockerfile.api should not run as root"

    def test_dockerfile_web_non_root_user(self) -> None:
        """Dockerfile.web runs as non-root user."""
        content = (INFRA_DIR / "Dockerfile.web").read_text()
        assert "USER " in content, "Dockerfile.web should switch to non-root USER"
        user_lines = [
            line.strip() for line in content.splitlines()
            if line.strip().startswith("USER ")
        ]
        assert user_lines, "No USER directive found"
        for line in user_lines:
            user = line.split()[1]
            assert user != "root", "Dockerfile.web should not run as root"

    def test_dockerfile_api_healthcheck(self) -> None:
        """Dockerfile.api has a HEALTHCHECK instruction."""
        content = (INFRA_DIR / "Dockerfile.api").read_text()
        assert "HEALTHCHECK" in content, "Dockerfile.api should have HEALTHCHECK"
        assert "8000" in content, "Dockerfile.api HEALTHCHECK should reference port 8000"

    def test_dockerfile_web_healthcheck(self) -> None:
        """Dockerfile.web has a HEALTHCHECK instruction."""
        content = (INFRA_DIR / "Dockerfile.web").read_text()
        assert "HEALTHCHECK" in content, "Dockerfile.web should have HEALTHCHECK"
        assert "3000" in content, "Dockerfile.web HEALTHCHECK should reference port 3000"

    def test_dockerfile_api_exposes_8000(self) -> None:
        """Dockerfile.api EXPOSEs port 8000."""
        content = (INFRA_DIR / "Dockerfile.api").read_text()
        assert "EXPOSE 8000" in content, "Dockerfile.api should EXPOSE 8000"

    def test_dockerfile_web_exposes_3000(self) -> None:
        """Dockerfile.web EXPOSEs port 3000."""
        content = (INFRA_DIR / "Dockerfile.web").read_text()
        assert "EXPOSE 3000" in content, "Dockerfile.web should EXPOSE 3000"


# ─── CI Workflow ──────────────────────────────────────────────────────────────


class TestCIWorkflow:
    """Validate the GitHub Actions CI workflow configuration."""

    @pytest.fixture(autouse=True)
    def _load(self) -> None:
        self.ci = load_yaml(GITHUB_DIR / "workflows" / "ci.yml")

    def test_is_valid_yaml(self) -> None:
        """ci.yml parses as valid YAML."""
        assert self.ci is not None

    def test_has_name(self) -> None:
        """CI workflow has a name."""
        assert "name" in self.ci

    def test_triggers_on_push_to_main(self) -> None:
        """CI triggers on push to main."""
        on = self.ci.get("on", self.ci.get(True, {}))
        push = on.get("push", {})
        branches = push.get("branches", [])
        assert "main" in branches, f"CI should trigger on push to main, got: {branches}"

    def test_triggers_on_pull_requests(self) -> None:
        """CI triggers on pull requests."""
        on = self.ci.get("on", self.ci.get(True, {}))
        assert "pull_request" in on, "CI should trigger on pull_request"

    def test_has_jobs_key(self) -> None:
        """CI workflow defines jobs."""
        assert "jobs" in self.ci

    def test_required_jobs_present(self) -> None:
        """CI has all required job types: lint, type-check, test-python, test-frontend, ethics-check, security."""
        jobs = set(self.ci["jobs"].keys())
        required = {"lint", "type-check", "test-python", "test-frontend", "ethics-check", "security"}
        missing = required - jobs
        assert not missing, f"CI missing required jobs: {missing}"

    def test_lint_job_runs_ruff(self) -> None:
        """Lint job runs ruff check and ruff format --check."""
        lint = self.ci["jobs"]["lint"]
        steps_yaml = yaml.dump(lint.get("steps", []))
        assert "ruff check" in steps_yaml, "Lint job should run 'ruff check'"
        assert "ruff format" in steps_yaml, "Lint job should run 'ruff format --check'"

    def test_type_check_job_runs_mypy(self) -> None:
        """Type check job runs mypy."""
        tc = self.ci["jobs"]["type-check"]
        steps_yaml = yaml.dump(tc.get("steps", []))
        assert "mypy" in steps_yaml, "Type check job should run mypy"

    def test_test_python_job_runs_pytest(self) -> None:
        """Test Python job runs pytest with coverage."""
        tp = self.ci["jobs"]["test-python"]
        steps_yaml = yaml.dump(tp.get("steps", []))
        assert "pytest" in steps_yaml, "Test Python job should run pytest"
        assert "cov" in steps_yaml, "Test Python job should include coverage"

    def test_test_frontend_job_runs_npm_test(self) -> None:
        """Test frontend job runs npm test."""
        tf = self.ci["jobs"]["test-frontend"]
        steps_yaml = yaml.dump(tf.get("steps", []))
        assert "npm test" in steps_yaml or "npm run test" in steps_yaml, (
            "Test frontend job should run npm test"
        )

    def test_ethics_check_job_present(self) -> None:
        """Ethics check is configured as a CI gate."""
        ec = self.ci["jobs"]["ethics-check"]
        steps_yaml = yaml.dump(ec.get("steps", []))
        assert "ethics" in steps_yaml.lower(), "Ethics check should reference ethics validation"

    def test_security_job_present(self) -> None:
        """Security job runs pip-audit and npm audit."""
        sec = self.ci["jobs"]["security"]
        steps_yaml = yaml.dump(sec.get("steps", []))
        assert "pip-audit" in steps_yaml or "pip_audit" in steps_yaml, (
            "Security job should run pip-audit"
        )
        assert "npm audit" in steps_yaml, "Security job should run npm audit"

    def test_python_matrix_versions(self) -> None:
        """Test Python job uses a matrix with Python 3.11 and 3.12."""
        tp = self.ci["jobs"]["test-python"]
        strategy = tp.get("strategy", {})
        matrix = strategy.get("matrix", {})
        python_versions = matrix.get("python-version", [])
        assert "3.11" in python_versions, "Python matrix should include 3.11"
        assert "3.12" in python_versions, "Python matrix should include 3.12"

    def test_coverage_artifact_upload(self) -> None:
        """Test Python job uploads coverage as artifact."""
        tp = self.ci["jobs"]["test-python"]
        steps_yaml = yaml.dump(tp.get("steps", []))
        assert "upload-artifact" in steps_yaml, "Test Python should upload coverage artifact"
        assert "coverage" in steps_yaml.lower(), "Artifact should reference coverage"


# ─── Release Workflow ─────────────────────────────────────────────────────────


class TestReleaseWorkflow:
    """Validate the GitHub Actions release workflow."""

    @pytest.fixture(autouse=True)
    def _load(self) -> None:
        self.release = load_yaml(GITHUB_DIR / "workflows" / "release.yml")

    def test_is_valid_yaml(self) -> None:
        """release.yml parses as valid YAML."""
        assert self.release is not None

    def test_triggers_on_tags(self) -> None:
        """Release triggers on version tags (v*)."""
        on = self.release.get("on", self.release.get(True, {}))
        push = on.get("push", {})
        tags = push.get("tags", [])
        assert len(tags) > 0, "Release should trigger on tags"
        tag_str = " ".join(tags)
        assert "v" in tag_str, "Release tags should match v* pattern"

    def test_has_build_job(self) -> None:
        """Release has a build/push job for Docker images."""
        jobs = self.release["jobs"]
        build_jobs = [k for k in jobs if "build" in k.lower() or "push" in k.lower()]
        assert build_jobs, "Release should have a build/push job"

    def test_has_github_release_job(self) -> None:
        """Release has a job to create a GitHub Release."""
        jobs = self.release["jobs"]
        release_jobs = [k for k in jobs if "release" in k.lower()]
        assert release_jobs, "Release should have a GitHub Release creation job"

    def test_has_changelog_generation(self) -> None:
        """Release generates a changelog."""
        jobs = self.release["jobs"]
        jobs_yaml = yaml.dump(jobs)
        assert "changelog" in jobs_yaml.lower(), "Release should include changelog generation"
