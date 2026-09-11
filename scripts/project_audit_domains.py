#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "config" / "g0_audit_domains.json"
SCHEMA = "KAT9I_G0_AUDIT/1"
REGISTRY_SCHEMA = "KAT9I_G0_AUDIT_DOMAINS/1"


def load_registry(path: Path = REGISTRY_PATH) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != REGISTRY_SCHEMA:
        raise ValueError(f"Ожидалась schema registry {REGISTRY_SCHEMA}")
    order = data.get("domain_order")
    if not isinstance(order, list) or not order or len(order) != len(set(order)):
        raise ValueError("domain_order должен быть непустым списком уникальных доменов")
    domains = set(order)
    exact = data.get("exact")
    prefixes = data.get("prefixes")
    fallback = data.get("fallback")
    if not isinstance(exact, dict) or not isinstance(prefixes, list) or not isinstance(fallback, dict):
        raise ValueError("registry должен содержать exact, prefixes и fallback")
    if fallback.get("policy") != "UNREGISTERED_ONLY" or fallback.get("domain") not in domains:
        raise ValueError("fallback policy должен быть UNREGISTERED_ONLY с известным domain")
    for code, domain in exact.items():
        if not isinstance(code, str) or not code or domain not in domains:
            raise ValueError("Некорректное exact правило registry")
    seen_prefixes: set[str] = set()
    for rule in prefixes:
        if not isinstance(rule, dict):
            raise ValueError("Каждое prefix правило должно быть объектом")
        prefix = rule.get("prefix")
        domain = rule.get("domain")
        if not isinstance(prefix, str) or not prefix or prefix in seen_prefixes or domain not in domains:
            raise ValueError("Некорректное или дублирующее prefix правило registry")
        seen_prefixes.add(prefix)
    return data


REGISTRY = load_registry()
DOMAIN_ORDER = tuple(REGISTRY["domain_order"])


def classify_finding(code: str) -> tuple[str, str]:
    value = str(code or "")
    exact = REGISTRY["exact"]
    if value in exact:
        return str(exact[value]), f"exact:{value}"

    matches = [rule for rule in REGISTRY["prefixes"] if value.startswith(str(rule["prefix"]))]
    domains = {str(rule["domain"]) for rule in matches}
    if len(domains) > 1:
        raise ValueError(f"Finding {value!r} неоднозначно классифицируется по нескольким доменам")
    if matches:
        longest = max(matches, key=lambda rule: len(str(rule["prefix"])))
        return str(longest["domain"]), f"prefix:{longest['prefix']}"

    return str(REGISTRY["fallback"]["domain"]), "fallback:UNREGISTERED_ONLY"


def finding_domain(code: str, *, require_registered: bool = False) -> str:
    domain, source = classify_finding(code)
    if require_registered and source.startswith("fallback:"):
        raise ValueError(f"Finding code {code!r} отсутствует в registry доменов")
    return domain


def enrich(summary: dict[str, Any]) -> dict[str, Any]:
    if summary.get("schema") != SCHEMA:
        raise ValueError(f"Ожидалась schema {SCHEMA}")
    findings = summary.get("findings")
    if not isinstance(findings, list):
        raise ValueError("findings должен быть списком")
    if summary.get("finding_count") != len(findings):
        raise ValueError("finding_count не совпадает с длиной findings")
    grouped: dict[str, list[dict[str, Any]]] = {domain: [] for domain in DOMAIN_ORDER}
    counts: Counter[str] = Counter()
    for finding in findings:
        if not isinstance(finding, dict) or not finding.get("code") or "message" not in finding:
            raise ValueError("Каждый finding должен содержать code и message")
        domain = finding_domain(str(finding["code"]))
        counts[domain] += 1
        grouped[domain].append({"code": finding["code"], "message": finding["message"]})
    result = dict(summary)
    result["domain_registry_schema"] = REGISTRY_SCHEMA
    result["domain_counts"] = {domain: counts.get(domain, 0) for domain in DOMAIN_ORDER}
    result["findings_by_domain"] = grouped
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Добавить домены к Evidence G0-аудита из machine-readable registry")
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    enriched = enrich(data)
    target = args.output or args.input
    target.write_text(json.dumps(enriched, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(enriched.get("domain_counts"), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
