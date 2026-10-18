"""Read private V3.6 reports; export an allowlisted summary into a NEW directory.

No capability promotion, runtime access, process inspection or historical rewrite.
Report hashes identify observed bytes; they do not manufacture missing provenance.
"""

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]


def read_record(root, relative, references):
    path = root / relative
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        references[relative] = {"available": False}
        return None
    references[relative] = {
        "available": True,
        "sha256": hashlib.sha256(data).hexdigest(),
    }
    return json.loads(data)


def manifest_identity(record):
    if not record:
        return None
    digest = hashlib.sha256(
        json.dumps(record["files"], sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    if digest != record.get("source_sha256"):
        raise ValueError("Source inventory digest mismatch")
    return digest


def passing_checks(record):
    if not record:
        return None
    checks = record.get("checks", {})
    return {
        "reported_passed": record.get("passed"),
        "checks_recorded": len(checks),
        "checks_true": sum(value is True for value in checks.values()),
        "all_recorded_checks_true": bool(checks)
        and all(value is True for value in checks.values()),
    }


def reconcile(root):
    references = {}

    def read(path):
        return read_record(root, path, references)

    source = read(".local/v36-source-03/source.json")
    tested = read(".local/v36-source-01/source.json")
    package = read(".local/v36-package-check-final-03/report.json")
    pair = read(".local/v36-upgrade-pair-final-03/report.json")
    bundle = read(".local/v36-package-03/Victus/release-manifest.json")
    device = read(".local/v36-device-final-01/report.json")
    soak = read(".local/v36-soak-standard-04/report.json")
    progress = read(".local/v36-soak-standard-04/progress.json")
    soak_observed = soak if soak is not None else progress
    source_hash = manifest_identity(source)
    tested_hash = manifest_identity(tested)
    backend_identical = bool(source and tested) and {
        k: v for k, v in source["files"].items() if k.startswith("backend/")
    } == {k: v for k, v in tested["files"].items() if k.startswith("backend/")}
    def scope_identical(prefix, exclude=()):
        return bool(source and tested) and {
            k: v for k, v in source["files"].items()
            if k.startswith(prefix) and not k.startswith(exclude)
        } == {
            k: v for k, v in tested["files"].items()
            if k.startswith(prefix) and not k.startswith(exclude)
        }
    junit_path = ".local/v36-regression-01.xml"
    junit = None
    if (root / junit_path).is_file():
        raw = (root / junit_path).read_bytes()
        references[junit_path] = {
            "available": True,
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
        suites = list(ElementTree.fromstring(raw).iter("testsuite"))
        junit = {
            k: sum(int(x.get(k, 0)) for x in suites)
            for k in ("tests", "errors", "failures", "skipped")
        }
    else:
        references[junit_path] = {"available": False}
    bundle_ref = references[".local/v36-package-03/Victus/release-manifest.json"]
    artifact_binding = bool(pair and bundle and source_hash) and (
        bundle_ref.get("sha256") == pair.get("candidate_manifest_sha256")
        and bundle.get("source_sha256") == source_hash
    )
    return {
        "milestone": "V3.6-reconciled-by-V4.0",
        "observed_utc": datetime.now(UTC).isoformat(),
        "release_qualified": False,
        "historical_source_sha256": source_hash,
        "backend_tested_source_sha256": tested_hash,
        "backend_inventory_identical_to_final": backend_identical,
        "backend_application_identical_to_final": scope_identical("backend/victus/"),
        "ordinary_backend_tests_identical_to_final": scope_identical("backend/tests/", ("backend/tests/live/",)),
        "live_runners_identical_to_final": scope_identical("backend/tests/live/"),
        "historical_junit": junit,
        "package_self_test": passing_checks(package),
        "package_report_embeds_artifact_identity": bool(
            package and package.get("source_sha256")
        ),
        "package_provenance_limit": "Self-test report lacks an embedded bundle hash; sibling artifact binding is corroboration only.",
        "artifact_pair": passing_checks(pair),
        "candidate_manifest_matches_pair_and_source": artifact_binding,
        "formal_cross_version_release_qualified": False,
        "fresh_standard_account_tested": False,
        "device_component_checks": passing_checks(device),
        "quiet_samples_measured": device.get("quiet_commands_measured")
        if device
        else None,
        "noisy_samples_measured": device.get("noisy_commands_measured")
        if device
        else None,
        "soak": {
            "final_report_available": soak is not None,
            "qualified": bool(soak and soak.get("qualified") is True),
            "progress_is_not_final_evidence": soak is None,
            **{
                key: soak_observed.get(key) if soak_observed else None
                for key in (
                    "elapsed_seconds",
                    "tasks_verified",
                    "pressure_rejections",
                    "backup_restores",
                    "implementation_start_sha256",
                    "implementation_end_sha256",
                )
            },
        },
        "references": references,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-directory", type=Path, required=True)
    args = parser.parse_args()
    output = args.output_directory.resolve()
    output.mkdir(parents=True, exist_ok=False)
    report = reconcile(ROOT)
    (output / "report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "historical_source_sha256": report["historical_source_sha256"],
                "soak_final_report_available": report["soak"]["final_report_available"],
                "release_qualified": False,
            }
        )
    )


if __name__ == "__main__":
    main()
