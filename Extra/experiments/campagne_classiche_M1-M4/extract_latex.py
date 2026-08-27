"""Produce snippet LaTeX deterministici dagli artefatti sperimentali JSON.

Per impostazione predefinita sono accettati solo artefatti con ``schema_version=2.0``.
I file storici possono essere letti esclusivamente passando
``--allow-legacy-schema``; in quel caso non viene mai ricostruita una baseline da
costanti incorporate nello script. I confronti v2 sono Wilcoxon appaiati e usano
i sentinel già presenti nei vettori ``all_iters``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from scipy.stats import mannwhitneyu, wilcoxon


SCHEMA_VERSION = "2.0"
PARAMETER_ANALYSIS_REVISION = "parameter-analysis-shared-hist-v4"
BASELINE_ANALYSIS_REVISION = "baseline-shared-hist-ties-holm-v3"
ZNE_ANALYSIS_REVISION = "zne-digital-shared-levels-holm-v3"
ANALYSIS_REVISIONS = {
    "parameter": PARAMETER_ANALYSIS_REVISION,
    "baseline": BASELINE_ANALYSIS_REVISION,
    "zne": ZNE_ANALYSIS_REVISION,
}
MANIFEST_KEYS = (
    "circuit_revision",
    "noise_model_revision",
    "postprocess_revision",
    "circuit_sha256",
    "basis_gates",
    "optimization_level",
    "seed_transpiler",
)
SWEEP_NAMES = (
    "sweep_k",
    "sweep_eps2q",
    "sweep_shots",
    "sweep_joint",
    "sweep_t1t2",
    "sweep_eps1q",
    "sweep_pro",
    "sweep_opt_level",
)


class ExtractionError(ValueError):
    """Errore di contratto in uno degli artefatti di input."""


@dataclass(frozen=True)
class Source:
    kind: str
    path: Path
    payload: dict[str, Any]
    legacy: bool
    sha256: str


def _load_source(path: Path, kind: str, allow_legacy: bool) -> Source:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ExtractionError(f"impossibile leggere {kind} JSON {path}: {exc}") from exc

    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ExtractionError(f"{kind} JSON non valido ({path}): {exc}") from exc
    if not isinstance(payload, dict):
        raise ExtractionError(f"{kind} JSON deve avere un oggetto alla radice: {path}")

    version = payload.get("schema_version")
    if version == SCHEMA_VERSION:
        legacy = False
    elif version is None or str(version).startswith("1."):
        legacy = True
    else:
        raise ExtractionError(
            f"schema_version non supportata in {path}: {version!r}; "
            f"questo extractor implementa {SCHEMA_VERSION}"
        )
    if legacy and not allow_legacy:
        shown = "assente" if version is None else repr(version)
        raise ExtractionError(
            f"schema storico/non supportato in {path} (schema_version={shown}); "
            "usare --allow-legacy-schema solo per un'estrazione esplicitamente storica"
        )
    if not legacy:
        manifest = payload.get("manifest")
        if not isinstance(manifest, dict):
            raise ExtractionError(f"{path}: lo schema v2 richiede un manifest")
        missing_manifest = [key for key in MANIFEST_KEYS if key not in manifest]
        if missing_manifest:
            raise ExtractionError(
                f"{path}: manifest v2 incompleto, mancano {', '.join(missing_manifest)}"
            )
        expected_revision = ANALYSIS_REVISIONS.get(kind)
        if expected_revision and payload.get("analysis_revision") != expected_revision:
            raise ExtractionError(
                f"{path}: risultato {kind} v2 privo di analysis_revision="
                f"{expected_revision!r}; possibile contratto obsoleto"
            )

    return Source(
        kind=kind,
        path=path,
        payload=payload,
        legacy=legacy,
        sha256=hashlib.sha256(raw).hexdigest(),
    )


def _mapping(value: Any, context: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise ExtractionError(f"{context} deve essere un oggetto JSON")
    return value


def _finite_float(
    value: Any,
    context: str,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ExtractionError(f"{context} deve essere numerico")
    converted = float(value)
    if not math.isfinite(converted):
        raise ExtractionError(f"{context} deve essere finito")
    if minimum is not None and converted < minimum:
        raise ExtractionError(f"{context} deve essere >= {minimum}")
    if maximum is not None and converted > maximum:
        raise ExtractionError(f"{context} deve essere <= {maximum}")
    return converted


def _parameter_parts(source: Source) -> tuple[Mapping[str, Any], Mapping[str, Any] | None]:
    payload = source.payload
    if source.legacy:
        sweeps_value = payload.get("sweeps")
        if sweeps_value is None:
            sweeps_value = {name: payload[name] for name in SWEEP_NAMES if name in payload}
        sweeps = _mapping(sweeps_value, f"sweep storici in {source.path}")
        baseline_value = payload.get("baseline_m1")
        baseline = (
            _mapping(baseline_value, f"baseline_m1 in {source.path}")
            if baseline_value is not None
            else None
        )
    else:
        if "sweeps" not in payload or "baseline_m1" not in payload:
            raise ExtractionError(
                f"{source.path}: lo schema v2 richiede le chiavi sweeps e baseline_m1"
            )
        sweeps = _mapping(payload["sweeps"], f"sweeps in {source.path}")
        baseline = _mapping(payload["baseline_m1"], f"baseline_m1 in {source.path}")

    if not sweeps:
        raise ExtractionError(f"nessuno sweep presente in {source.path}")
    unknown = sorted(set(sweeps) - set(SWEEP_NAMES))
    if unknown:
        raise ExtractionError(
            f"sweep non riconosciuti in {source.path}: {', '.join(unknown)}"
        )
    return sweeps, baseline


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _merge_parameter_sources(
    sources: Sequence[Source],
) -> tuple[
    dict[str, Any],
    Mapping[str, Any] | None,
    Mapping[str, Any] | None,
    dict[str, bool],
]:
    merged: dict[str, Any] = {}
    baseline: Mapping[str, Any] | None = None
    manifest: Mapping[str, Any] | None = None
    legacy_sweeps: dict[str, bool] = {}

    if len({source.legacy for source in sources}) > 1:
        raise ExtractionError(
            "non e' consentito mescolare parameter JSON v2 e storici nella stessa estrazione"
        )

    for source in sources:
        sweeps, current_baseline = _parameter_parts(source)
        current_manifest_value = source.payload.get("manifest")
        current_manifest = (
            _mapping(current_manifest_value, f"manifest in {source.path}")
            if current_manifest_value is not None
            else None
        )

        if current_manifest is not None:
            if manifest is None:
                manifest = current_manifest
            elif _canonical(manifest) != _canonical(current_manifest):
                raise ExtractionError(
                    f"manifest incompatibili fra i parameter JSON (ultimo: {source.path})"
                )

        if current_baseline is not None:
            if baseline is None:
                baseline = current_baseline
            elif _canonical(baseline) != _canonical(current_baseline):
                raise ExtractionError(
                    f"baseline_m1 incompatibili fra i parameter JSON (ultimo: {source.path})"
                )

        for name, values in sweeps.items():
            if name in merged and _canonical(merged[name]) != _canonical(values):
                raise ExtractionError(
                    f"sweep {name} duplicato con contenuto diverso ({source.path})"
                )
            merged[name] = values
            legacy_sweeps[name] = source.legacy

    return merged, baseline, manifest, legacy_sweeps


def _campaign_items(source: Source) -> list[Mapping[str, Any]]:
    value = source.payload.get("use_case")
    if not isinstance(value, list) or not value:
        raise ExtractionError(f"{source.path}: chiave use_case mancante o vuota")
    items: list[Mapping[str, Any]] = []
    for index, item in enumerate(value):
        items.append(_mapping(item, f"use_case[{index}] in {source.path}"))
    return items


def _strategies(source: Source) -> Mapping[str, Any]:
    value = source.payload.get("strategies")
    if value is None and source.legacy:
        value = {
            key: source.payload[key]
            for key in ("M1", "ZNE-2", "ZNE-3", "TOP4")
            if key in source.payload
        }
    strategies = _mapping(value, f"strategies in {source.path}")
    missing = [key for key in ("M1", "ZNE-2", "ZNE-3", "TOP4") if key not in strategies]
    if missing:
        raise ExtractionError(
            f"{source.path}: strategie mancanti: {', '.join(missing)}"
        )
    return strategies


def _manifest(source: Source) -> Mapping[str, Any] | None:
    value = source.payload.get("manifest")
    return _mapping(value, f"manifest in {source.path}") if value is not None else None


def _check_manifest_compatibility(
    expected: Mapping[str, Any] | None, source: Source
) -> None:
    current = _manifest(source)
    if source.legacy:
        return
    if expected is None or current is None:
        raise ExtractionError(f"{source.path}: manifest v2 mancante o non confrontabile")
    differences = [key for key in MANIFEST_KEYS if expected.get(key) != current.get(key)]
    if differences:
        raise ExtractionError(
            f"{source.path}: manifest non compatibile per {', '.join(differences)}"
        )


def _baseline_from_campaign(source: Source) -> Mapping[str, Any] | None:
    uc1 = next(
        (item for item in _campaign_items(source) if item.get("use_case") == "UC1"),
        None,
    )
    if uc1 is None:
        return None
    m1 = _mapping(uc1.get("M1"), f"M1 di UC1 in {source.path}")
    iterations = _mapping(
        uc1.get("_iterazioni"), f"_iterazioni di UC1 in {source.path}"
    ).get("M1")
    if not isinstance(iterations, list) or not iterations:
        return None
    return {
        "M_bar": m1.get("M_bar"),
        "std": m1.get("sigma"),
        "success_rate": m1.get("P_succ"),
        "all_iters": iterations,
        "failure_sentinel": uc1.get("failure_sentinel"),
    }


def _iterations(summary: Mapping[str, Any], context: str) -> list[float]:
    values = summary.get("all_iters")
    if not isinstance(values, list) or not values:
        raise ExtractionError(f"{context}: all_iters mancante o vuoto")
    if any(
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(float(value))
        for value in values
    ):
        raise ExtractionError(f"{context}: all_iters deve contenere solo numeri finiti")
    converted = [float(value) for value in values]
    n_runs = summary.get("n_runs")
    if n_runs is not None and n_runs != len(converted):
        raise ExtractionError(f"{context}: n_runs non coincide con all_iters")
    successes = summary.get("all_success")
    sentinel = summary.get("failure_sentinel")
    if successes is not None:
        if (
            not isinstance(successes, list)
            or len(successes) != len(converted)
            or any(type(value) is not bool for value in successes)
        ):
            raise ExtractionError(f"{context}: all_success non coerente con all_iters")
        if sentinel is not None:
            if not isinstance(sentinel, (int, float)) or isinstance(sentinel, bool):
                raise ExtractionError(f"{context}: failure_sentinel non numerico")
            for value, success in zip(converted, successes):
                if (success and value >= float(sentinel)) or (
                    not success and value != float(sentinel)
                ):
                    raise ExtractionError(
                        f"{context}: codifica success/failure_sentinel incoerente"
                    )
    # Nel contratto v2 i fallimenti sono gia' MAX_ITER+1. Non censurare,
    # sostituire o ricostruire questi valori prima del test statistico.
    return converted


def _paired_wilcoxon(
    reference: Mapping[str, Any] | None,
    candidate: Mapping[str, Any],
    context: str,
    *,
    alternative: str = "greater",
) -> tuple[float, float] | None:
    if reference is None:
        return None
    ref_values = _iterations(reference, "baseline_m1")
    candidate_values = _iterations(candidate, context)
    if len(ref_values) != len(candidate_values):
        raise ExtractionError(
            f"{context}: Wilcoxon appaiato richiede campioni della stessa lunghezza "
            f"({len(ref_values)} != {len(candidate_values)})"
        )
    ref_sentinel = reference.get("failure_sentinel")
    candidate_sentinel = candidate.get("failure_sentinel")
    if (
        ref_sentinel is not None
        and candidate_sentinel is not None
        and ref_sentinel != candidate_sentinel
    ):
        raise ExtractionError(
            f"{context}: failure_sentinel incompatibili "
            f"({ref_sentinel!r} != {candidate_sentinel!r})"
        )
    ref_pair_ids = reference.get("pair_ids")
    candidate_pair_ids = candidate.get("pair_ids")
    if (ref_pair_ids is not None or candidate_pair_ids is not None) and (
        not isinstance(ref_pair_ids, list)
        or ref_pair_ids != candidate_pair_ids
        or len(ref_pair_ids) != len(ref_values)
    ):
        raise ExtractionError(f"{context}: pair_ids non allineati per il test appaiato")
    if ref_values == candidate_values:
        return 0.0, 1.0
    result = wilcoxon(
        ref_values,
        candidate_values,
        alternative=alternative,
        zero_method="pratt",
        method="auto",
    )
    return float(result.statistic), float(result.pvalue)


def _paired_greater(
    reference: Mapping[str, Any] | None,
    candidate: Mapping[str, Any],
    context: str,
) -> float | None:
    result = _paired_wilcoxon(reference, candidate, context)
    return None if result is None else result[1]


def _comparison_greater(
    reference: Mapping[str, Any] | None,
    candidate: Mapping[str, Any],
    context: str,
    *,
    legacy: bool,
) -> float | None:
    if not legacy:
        return _paired_greater(reference, candidate, context)
    if reference is None:
        return None
    # Compatibilita' esplicita con gli artefatti storici: quei risultati erano
    # stati analizzati come campioni indipendenti. Il ramo v2 non passa mai qui.
    _, p_value = mannwhitneyu(
        _iterations(reference, "baseline_m1 storica"),
        _iterations(candidate, context),
        alternative="greater",
    )
    return float(p_value)


def _rho(
    candidate: Mapping[str, Any], reference: Mapping[str, Any] | None
) -> float | None:
    if reference is None:
        return None
    ref_value = reference.get("M_bar")
    candidate_value = candidate.get("M_bar")
    if (
        not isinstance(ref_value, (int, float))
        or isinstance(ref_value, bool)
        or not math.isfinite(float(ref_value))
        or not isinstance(candidate_value, (int, float))
        or isinstance(candidate_value, bool)
        or not math.isfinite(float(candidate_value))
    ):
        return None
    if candidate_value <= 0:
        return None
    return float(ref_value) / float(candidate_value)


def _paired_components(
    result: Mapping[str, Any], context: str
) -> tuple[Mapping[str, Any], Mapping[str, Any], float, float | None]:
    """Validate and recompute a schema-v2 paired M1/TOP-K condition."""
    m1 = _mapping(result.get("m1"), f"m1 per {context}")
    topk = _mapping(result.get("topk"), f"topk per {context}")
    pairing = _mapping(result.get("pairing"), f"pairing per {context}")
    if pairing.get("paired") is not True:
        raise ExtractionError(f"{context}: pairing.paired deve essere true")
    if pairing.get("same_histograms_within_replica") is not True:
        raise ExtractionError(
            f"{context}: il contratto richiede gli stessi istogrammi per M1 e TOP-K"
        )

    test_result = _paired_wilcoxon(m1, topk, f"topk per {context}")
    if test_result is None:  # pragma: no cover - m1 e' sempre presente qui
        raise ExtractionError(f"{context}: confronto M1/TOP-K mancante")
    statistic, p_value = test_result
    n_pairs = len(_iterations(m1, f"m1 per {context}"))
    if pairing.get("n_pairs") != n_pairs:
        raise ExtractionError(
            f"{context}: pairing.n_pairs={pairing.get('n_pairs')!r}, atteso {n_pairs}"
        )
    m1_pair_ids = m1.get("pair_ids")
    topk_pair_ids = topk.get("pair_ids")
    pairing_ids = pairing.get("pair_ids")
    if (
        not isinstance(m1_pair_ids, list)
        or len(m1_pair_ids) != n_pairs
        or m1_pair_ids != topk_pair_ids
        or m1_pair_ids != pairing_ids
        or len({_canonical(value) for value in m1_pair_ids}) != n_pairs
    ):
        raise ExtractionError(
            f"{context}: pair_ids M1/TOP-K devono essere unici, completi e nello stesso ordine"
        )
    sentinel = m1.get("failure_sentinel")
    if sentinel is None or pairing.get("failure_sentinel") != sentinel:
        raise ExtractionError(
            f"{context}: failure_sentinel mancante o incoerente nel pairing"
        )

    stored_test = _mapping(
        result.get("wilcoxon_M1_gt_TOPK"),
        f"wilcoxon_M1_gt_TOPK per {context}",
    )
    if stored_test.get("alternative") != "greater" or stored_test.get("zero_method") != "pratt":
        raise ExtractionError(f"{context}: contratto Wilcoxon non coerente")
    for key, expected in (("W", statistic), ("p", p_value)):
        value = stored_test.get(key)
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(float(value))
            or not math.isclose(
            float(value), expected, rel_tol=1e-12, abs_tol=1e-12
            )
        ):
            raise ExtractionError(
                f"{context}: {key} Wilcoxon salvato non coincide con il dato appaiato"
            )

    expected_rho = _rho(topk, m1)
    stored_rho = result.get("rho")
    if expected_rho is None:
        if stored_rho is not None:
            raise ExtractionError(f"{context}: rho deve essere null")
    elif (
        not isinstance(stored_rho, (int, float))
        or isinstance(stored_rho, bool)
        or not math.isfinite(float(stored_rho))
        or not math.isclose(
            float(stored_rho), expected_rho, rel_tol=0.0, abs_tol=5e-4
        )
    ):
        raise ExtractionError(f"{context}: rho salvato non coincide con M1/TOP-K")
    return m1, topk, p_value, expected_rho


def _validated_holm_p(
    test: Mapping[str, Any], raw_p: float, context: str
) -> float:
    value = test.get("p_holm")
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(float(value))
        or not raw_p <= float(value) <= 1.0
    ):
        raise ExtractionError(
            f"{context}: p_holm deve essere finito e appartenere a [p, 1]"
        )
    return float(value)


def _validate_holm_family(
    tests: Mapping[str, Mapping[str, Any]], context: str
) -> None:
    ordered: list[tuple[str, float]] = []
    for name, test in tests.items():
        raw_p = test.get("p")
        if (
            not isinstance(raw_p, (int, float))
            or isinstance(raw_p, bool)
            or not math.isfinite(float(raw_p))
            or not 0.0 <= float(raw_p) <= 1.0
        ):
            raise ExtractionError(f"{context}.{name}: p raw non valido")
        ordered.append((name, float(raw_p)))
    ordered.sort(key=lambda item: item[1])
    running = 0.0
    total = len(ordered)
    expected: dict[str, float] = {}
    for index, (name, raw_p) in enumerate(ordered):
        running = max(running, min(1.0, (total - index) * raw_p))
        expected[name] = running
    for name, adjusted in expected.items():
        stored = tests[name].get("p_holm")
        if (
            not isinstance(stored, (int, float))
            or isinstance(stored, bool)
            or not math.isfinite(float(stored))
            or not math.isclose(float(stored), adjusted, rel_tol=1e-12, abs_tol=1e-12)
        ):
            raise ExtractionError(
                f"{context}.{name}: p_holm non coincide con la correzione Holm della famiglia"
            )


def _number(value: Any, digits: int = 2, missing: str = "N/A") -> str:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(float(value))
    ):
        return missing
    return f"{float(value):.{digits}f}"


def _percent(value: Any) -> str:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(float(value))
    ):
        return "N/A"
    return f"{float(value) * 100:.1f}\\%"


def _rho_text(value: float | None) -> str:
    return f"{value:.3f}" if value is not None else "---"


def _p_text(value: float | None, significance: bool = False) -> str:
    if value is None:
        return "---"
    base = r"${<}0.001$" if value < 0.001 else f"${value:.3f}$"
    if significance:
        base += r" (sign.)" if value < 0.05 else " (n.s.)"
    return base


def _scientific(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ExtractionError(f"valore scientifico non numerico: {value!r}") from exc
    if not math.isfinite(number):
        raise ExtractionError(f"valore scientifico non finito: {value!r}")
    if number == 0:
        return "$0$"
    mantissa_text, exponent_text = f"{number:.0e}".split("e")
    mantissa = int(mantissa_text)
    exponent = int(exponent_text)
    if mantissa == 1:
        return f"$10^{{{exponent}}}$"
    return f"${mantissa}\\times10^{{{exponent}}}$"


def _numeric_items(values: Mapping[str, Any]) -> list[tuple[str, Any]]:
    def key(item: tuple[str, Any]) -> tuple[int, float | str]:
        try:
            return (0, float(item[0]))
        except (TypeError, ValueError):
            return (1, str(item[0]))

    return sorted(((str(k), v) for k, v in values.items()), key=key)


def _section(name: str, columns: str, rows: Sequence[str]) -> list[str]:
    return [
        "% ============================================================",
        f"% tabella {name} ({columns})",
        "% ============================================================",
        *rows,
        "",
    ]


def _render_simple_sweep(
    name: str,
    values: Mapping[str, Any],
    baseline: Mapping[str, Any] | None,
    key_formatter,
    columns: str,
    *,
    legacy: bool,
) -> list[str]:
    rows: list[str] = []
    for raw_key, raw_summary in _numeric_items(values):
        summary = _mapping(raw_summary, f"{name}[{raw_key}]")
        p_value = _comparison_greater(
            baseline, summary, f"{name}[{raw_key}]", legacy=legacy
        )
        rho_value = _rho(summary, baseline)
        row = [
            key_formatter(raw_key),
            _percent(summary.get("success_rate")),
            _number(summary.get("M_bar")),
            _number(summary.get("std")),
            _rho_text(rho_value),
        ]
        if name == "sweep_k":
            row.append(_p_text(p_value))
        rows.append("        " + " & ".join(row) + r" \\")
    return _section(name, columns, rows)


def _render_paired_sweep(
    name: str,
    values: Mapping[str, Any],
    key_formatter,
    columns: str,
) -> list[str]:
    """Render v2 con TOP-1 e TOP-K misurati sulla stessa condizione."""
    rows: list[str] = []
    for raw_key, raw_result in _numeric_items(values):
        result = _mapping(raw_result, f"{name}[{raw_key}]")
        m1, topk, p_value, rho_value = _paired_components(
            result, f"{name}[{raw_key}]"
        )
        row = [
            key_formatter(raw_key),
            _number(m1.get("M_bar")),
            _number(topk.get("M_bar")),
            _percent(topk.get("success_rate")),
            _rho_text(rho_value),
            _p_text(p_value),
        ]
        rows.append("        " + " & ".join(row) + r" \\")
    return _section(name, columns, rows)


def _render_sweep_eps2q(values: Mapping[str, Any], *, legacy: bool) -> list[str]:
    rows: list[str] = []
    for raw_key, raw_result in _numeric_items(values):
        result = _mapping(raw_result, f"sweep_eps2q[{raw_key}]")
        if legacy:
            m1 = _mapping(result.get("m1"), f"m1 per eps_2q={raw_key}")
            topk = _mapping(result.get("topk"), f"topk per eps_2q={raw_key}")
            p_value = _comparison_greater(
                m1, topk, f"topk per eps_2q={raw_key}", legacy=True
            )
            rho_value = _rho(topk, m1)
        else:
            m1, topk, p_value, rho_value = _paired_components(
                result, f"sweep_eps2q[{raw_key}]"
            )
        proxy_key = "p_surv" if legacy else "p_no_nonidentity_2q_proxy"
        if proxy_key not in result:
            raise ExtractionError(
                f"sweep_eps2q[{raw_key}]: chiave {proxy_key} mancante "
                f"nel contratto {'storico' if legacy else 'v2'}"
            )
        proxy_value = _finite_float(
            result[proxy_key], f"sweep_eps2q[{raw_key}].{proxy_key}",
            minimum=0.0, maximum=1.0,
        )
        row = [
            _scientific(raw_key),
            f"${proxy_value:.2e}$",
            _number(m1.get("M_bar")),
            _number(topk.get("M_bar")),
            _rho_text(rho_value),
            _p_text(p_value),
            _percent(topk.get("success_rate")),
        ]
        rows.append("        " + " & ".join(row) + r" \\")
    return _section(
        "sweep_eps2q",
        "eps_2q & P_no_nonidentity_2q_proxy & M1 & TOP4 & rho & p & success_rate",
        rows,
    )


def _render_sweep_joint(values: Mapping[str, Any]) -> list[str]:
    k_items = _numeric_items(values)
    if not k_items:
        raise ExtractionError("sweep_joint vuoto")
    first = _mapping(k_items[0][1], f"sweep_joint[{k_items[0][0]}]")
    eps_keys = [key for key, _ in _numeric_items(first)]
    header = " & ".join(f"$\\varepsilon_{{2q}}={_scientific(key)[1:-1]}$" for key in eps_keys)
    rows = [f"        $K$ & {header}" + " \\\\", r"        \midrule"]
    for k_key, raw_eps in k_items:
        eps_values = _mapping(raw_eps, f"sweep_joint[{k_key}]")
        if set(eps_values) != set(eps_keys):
            raise ExtractionError(
                f"sweep_joint[{k_key}] non condivide la stessa griglia eps_2q"
            )
        cells: list[str] = []
        for eps_key in eps_keys:
            raw_summary = eps_values.get(eps_key)
            if not isinstance(raw_summary, dict):
                cells.append("N/A")
                continue
            m_bar = raw_summary.get("M_bar")
            if not isinstance(m_bar, (int, float)):
                cells.append("N/A")
                continue
            text = f"{float(m_bar):.2f}"
            cells.append(f"\\textbf{{{text}}}" if m_bar <= 1.5 else text)
        rows.append(f"        {k_key} & " + " & ".join(cells) + r" \\")
    return _section("sweep_joint", "K x eps_2q; celle=M_bar", rows)


def _render_sweep_t1t2(
    values: Mapping[str, Any],
    baseline: Mapping[str, Any] | None,
    *,
    legacy: bool,
) -> list[str]:
    rows: list[str] = []
    for raw_key, raw_summary in _numeric_items(values):
        summary = _mapping(raw_summary, f"sweep_t1t2[{raw_key}]")
        t1_ns = float(raw_key)
        if legacy:
            t2_ns = summary.get("t2_ns", t1_ns * 0.8)
            row = [
                f"{t1_ns / 1000:g}",
                f"{float(t2_ns) / 1000:g}",
                _percent(summary.get("success_rate")),
                _number(summary.get("M_bar")),
                _number(summary.get("std")),
                _rho_text(_rho(summary, baseline)),
            ]
        else:
            if "t2_ns" not in summary:
                raise ExtractionError(
                    f"sweep_t1t2[{raw_key}]: t2_ns esplicito mancante nello schema v2"
                )
            t2_ns = summary["t2_ns"]
            m1, topk, p_value, rho_value = _paired_components(
                summary, f"sweep_t1t2[{raw_key}]"
            )
            row = [
                f"{t1_ns / 1000:g}",
                f"{float(t2_ns) / 1000:g}",
                _number(m1.get("M_bar")),
                _number(topk.get("M_bar")),
                _percent(topk.get("success_rate")),
                _rho_text(rho_value),
                _p_text(p_value),
            ]
        rows.append("        " + " & ".join(row) + r" \\")
    columns = (
        "T1_us & T2_us & success_rate & M_bar & std & rho"
        if legacy
        else "T1_us & T2_us & M1 & TOP4 & success_rate_TOP4 & rho & p"
    )
    return _section("sweep_t1t2", columns, rows)


def _render_sweep_opt_level(values: Mapping[str, Any], *, legacy: bool) -> list[str]:
    rows: list[str] = []
    for raw_key, raw_result in _numeric_items(values):
        result = _mapping(raw_result, f"sweep_opt_level[{raw_key}]")
        if legacy:
            m1 = _mapping(result.get("m1"), f"m1 per optimization_level={raw_key}")
            topk = _mapping(result.get("topk"), f"topk per optimization_level={raw_key}")
            p_value = None
            rho_value = _rho(topk, m1)
        else:
            m1, topk, p_value, rho_value = _paired_components(
                result, f"sweep_opt_level[{raw_key}]"
            )
        row = [
            raw_key,
            str(result.get("cx_count", "N/A")),
            str(result.get("depth", "N/A")),
            _number(m1.get("M_bar")),
            _percent(m1.get("success_rate")),
            _number(topk.get("M_bar")),
            _percent(topk.get("success_rate")),
            _rho_text(rho_value),
        ]
        if not legacy:
            row.append(_p_text(p_value))
        rows.append("        " + " & ".join(row) + r" \\")
    return _section(
        "sweep_opt_level",
        (
            "livello & CX & profondita & M1 & SR1 & TOP4 & SR4 & rho"
            if legacy
            else "livello & CX & profondita & M1 & SR1 & TOP4 & SR4 & rho & p"
        ),
        rows,
    )


def render_parameter_sweeps(
    sweeps: Mapping[str, Any],
    baseline: Mapping[str, Any] | None,
    legacy_sweeps: Mapping[str, bool] | None = None,
) -> list[str]:
    legacy_sweeps = legacy_sweeps or {}
    lines: list[str] = []
    for name in SWEEP_NAMES:
        if name not in sweeps:
            continue
        values = _mapping(sweeps[name], name)
        if name == "sweep_k":
            if legacy_sweeps.get(name, False):
                lines.extend(_render_simple_sweep(
                    name, values, baseline, str,
                    "K & success_rate & M_bar & std & rho & p",
                    legacy=True,
                ))
            else:
                lines.extend(_render_paired_sweep(
                    name, values, str,
                    "K & M1 & TOPK & success_rate_TOPK & rho & p",
                ))
        elif name == "sweep_eps2q":
            lines.extend(
                _render_sweep_eps2q(values, legacy=bool(legacy_sweeps.get(name, False)))
            )
        elif name == "sweep_shots":
            if legacy_sweeps.get(name, False):
                lines.extend(_render_simple_sweep(
                    name, values, baseline, str,
                    "shots & success_rate & M_bar & std & rho",
                    legacy=True,
                ))
            else:
                lines.extend(_render_paired_sweep(
                    name, values, str,
                    "shots & M1 & TOP4 & success_rate_TOP4 & rho & p",
                ))
        elif name == "sweep_joint":
            lines.extend(_render_sweep_joint(values))
        elif name == "sweep_t1t2":
            lines.extend(_render_sweep_t1t2(
                values, baseline,
                legacy=bool(legacy_sweeps.get(name, False)),
            ))
        elif name == "sweep_eps1q":
            if legacy_sweeps.get(name, False):
                lines.extend(_render_simple_sweep(
                    name, values, baseline, _scientific,
                    "eps_1q & success_rate & M_bar & std & rho",
                    legacy=True,
                ))
            else:
                lines.extend(_render_paired_sweep(
                    name, values, _scientific,
                    "eps_1q & M1 & TOP4 & success_rate_TOP4 & rho & p",
                ))
        elif name == "sweep_pro":
            formatter = lambda value: f"{float(value) * 100:g}\\%"
            if legacy_sweeps.get(name, False):
                lines.extend(_render_simple_sweep(
                    name, values, baseline, formatter,
                    "p_ro & success_rate & M_bar & std & rho",
                    legacy=True,
                ))
            else:
                lines.extend(_render_paired_sweep(
                    name, values, formatter,
                    "p_ro & M1 & TOP4 & success_rate_TOP4 & rho & p",
                ))
        elif name == "sweep_opt_level":
            lines.extend(_render_sweep_opt_level(
                values, legacy=bool(legacy_sweeps.get(name, False))
            ))
    return lines


def render_baseline(source: Source) -> list[str]:
    rows: list[str] = []
    ablations: list[str] = []
    labels = {
        "M1": "M1 (TOP-1)",
        "M_TOP4": r"$M_{\text{TOP4}}$ (no clf)",
        "M2": "M2 (CLF+TOP-4)",
    }
    for item in sorted(_campaign_items(source), key=lambda value: str(value.get("use_case", ""))):
        use_case = str(item.get("use_case", "?"))
        raw_iterations: dict[str, Mapping[str, Any]] = {}
        if not source.legacy:
            sentinel = item.get("failure_sentinel")
            if not isinstance(sentinel, (int, float)) or isinstance(sentinel, bool):
                raise ExtractionError(f"{use_case}: failure_sentinel v2 mancante")
            iteration_map = _mapping(
                item.get("_iterazioni"), f"_iterazioni di {use_case}"
            )
            for method in ("M1", "M_TOP4", "M2"):
                if method in item:
                    raw_iterations[method] = {
                        "all_iters": iteration_map.get(method),
                        "failure_sentinel": sentinel,
                    }
                    _iterations(raw_iterations[method], f"{use_case}.{method}")
            multiplicity = _mapping(
                item.get("multiplicity"), f"multiplicity di {use_case}"
            )
            expected_family = ["wilcoxon_M1_gt_TOP4"]
            if "M2" in item:
                expected_family.extend(
                    ["wilcoxon_M2_vs_TOP4", "wilcoxon_M1_gt_M2"]
                )
            if (
                multiplicity.get("method") != "Holm"
                or multiplicity.get("family") != expected_family
                or multiplicity.get("alpha") != 0.05
            ):
                raise ExtractionError(
                    f"{use_case}: famiglia di molteplicita Holm non coerente"
                )
            _validate_holm_family(
                {
                    name: _mapping(item.get(name), f"{use_case}.{name}")
                    for name in expected_family
                },
                f"{use_case}.multiplicity",
            )
        for method in ("M1", "M_TOP4", "M2"):
            if method not in item:
                continue
            summary = _mapping(item[method], f"{use_case}.{method}")
            if method == "M1":
                rho_value = None
                p_value = None
            elif method == "M_TOP4":
                rho_value = item.get("rho_TOP4")
                comparison_key = (
                    "mwu_M1_gt_TOP4"
                    if source.legacy
                    else "wilcoxon_M1_gt_TOP4"
                )
                test = _mapping(
                    item.get(comparison_key), f"{use_case}.{comparison_key}"
                )
                statistic_key = "U" if source.legacy else "W"
                if statistic_key not in test or "p" not in test:
                    raise ExtractionError(
                        f"{use_case}.{comparison_key} richiede {statistic_key} e p"
                    )
                if source.legacy:
                    p_value = test.get("p")
                else:
                    if test.get("alternative") != "greater":
                        raise ExtractionError(
                            f"{use_case}.wilcoxon_M1_gt_TOP4 richiede alternative='greater'"
                        )
                    recomputed = _paired_wilcoxon(
                        raw_iterations["M1"], raw_iterations["M_TOP4"],
                        f"{use_case}.M_TOP4",
                    )
                    if recomputed is None:  # pragma: no cover
                        raise ExtractionError(f"{use_case}: confronto TOP4 mancante")
                    expected_w, p_value = recomputed
                    if not all(
                        isinstance(test.get(key), (int, float))
                        and math.isclose(float(test[key]), expected, rel_tol=1e-12, abs_tol=1e-12)
                        for key, expected in (("W", expected_w), ("p", p_value))
                    ):
                        raise ExtractionError(
                            f"{use_case}.wilcoxon_M1_gt_TOP4 non coincide con _iterazioni"
                        )
                    p_value = _validated_holm_p(
                        test, p_value, f"{use_case}.wilcoxon_M1_gt_TOP4"
                    )
                    expected_rho = _rho(summary, _mapping(item["M1"], f"{use_case}.M1"))
                    if expected_rho is None and rho_value is not None:
                        raise ExtractionError(f"{use_case}.rho_TOP4 deve essere null")
                    if expected_rho is None:
                        rho_value = None
                    elif (
                        not isinstance(rho_value, (int, float))
                        or isinstance(rho_value, bool)
                        or not math.isfinite(float(rho_value))
                        or not math.isclose(
                            float(rho_value), expected_rho, rel_tol=1e-12, abs_tol=1e-12
                        )
                    ):
                        raise ExtractionError(f"{use_case}.rho_TOP4 non coincide con i summary")
                    else:
                        rho_value = expected_rho
            else:
                rho_value = item.get("rho_M2")
                comparison_key = (
                    "mwu_M1_gt_M2" if source.legacy else "wilcoxon_M1_gt_M2"
                )
                test = _mapping(
                    item.get(comparison_key), f"{use_case}.{comparison_key}"
                )
                statistic_key = "U" if source.legacy else "W"
                if statistic_key not in test or "p" not in test:
                    raise ExtractionError(
                        f"{use_case}.{comparison_key} richiede {statistic_key} e p"
                    )
                if source.legacy:
                    p_value = test.get("p")
                else:
                    if test.get("alternative") != "greater":
                        raise ExtractionError(
                            f"{use_case}.wilcoxon_M1_gt_M2 richiede alternative='greater'"
                        )
                    recomputed = _paired_wilcoxon(
                        raw_iterations["M1"], raw_iterations["M2"],
                        f"{use_case}.M2",
                    )
                    if recomputed is None:  # pragma: no cover
                        raise ExtractionError(f"{use_case}: confronto M2 mancante")
                    expected_w, p_value = recomputed
                    if not all(
                        isinstance(test.get(key), (int, float))
                        and math.isclose(float(test[key]), expected, rel_tol=1e-12, abs_tol=1e-12)
                        for key, expected in (("W", expected_w), ("p", p_value))
                    ):
                        raise ExtractionError(
                            f"{use_case}.wilcoxon_M1_gt_M2 non coincide con _iterazioni"
                        )
                    p_value = _validated_holm_p(
                        test, p_value, f"{use_case}.wilcoxon_M1_gt_M2"
                    )
                    expected_rho = _rho(summary, _mapping(item["M1"], f"{use_case}.M1"))
                    if expected_rho is None and rho_value is not None:
                        raise ExtractionError(f"{use_case}.rho_M2 deve essere null")
                    if expected_rho is None:
                        rho_value = None
                    elif (
                        not isinstance(rho_value, (int, float))
                        or isinstance(rho_value, bool)
                        or not math.isfinite(float(rho_value))
                        or not math.isclose(
                            float(rho_value), expected_rho, rel_tol=1e-12, abs_tol=1e-12
                        )
                    ):
                        raise ExtractionError(f"{use_case}.rho_M2 non coincide con i summary")
                    else:
                        rho_value = expected_rho
            row = [
                use_case,
                labels[method],
                _percent(summary.get("P_succ")),
                _number(summary.get("M_bar")),
                _rho_text(float(rho_value) if isinstance(rho_value, (int, float)) else None),
                _p_text(float(p_value) if isinstance(p_value, (int, float)) else None, True),
            ]
            rows.append("        " + " & ".join(row) + r" \\")

        ablation_key = (
            "mwu_TOP4_gt_M2" if source.legacy else "wilcoxon_M2_vs_TOP4"
        )
        ablation = item.get(ablation_key)
        if "M2" in item and not isinstance(ablation, dict):
            raise ExtractionError(f"{use_case}.{ablation_key} mancante")
        statistic_key = "U" if source.legacy else "W"
        if isinstance(ablation, dict) and (
            statistic_key not in ablation or "p" not in ablation
        ):
            raise ExtractionError(
                f"{use_case}.{ablation_key} richiede {statistic_key} e p"
            )
        if isinstance(ablation, dict):
            if (
                not isinstance(ablation.get("p"), (int, float))
                or isinstance(ablation.get("p"), bool)
                or not math.isfinite(float(ablation["p"]))
            ):
                raise ExtractionError(f"{use_case}.{ablation_key}.p non valido")
            if not source.legacy:
                if ablation.get("alternative") != "two-sided":
                    raise ExtractionError(
                        f"{use_case}.{ablation_key} richiede alternative='two-sided'"
                    )
                recomputed = _paired_wilcoxon(
                    raw_iterations["M2"], raw_iterations["M_TOP4"],
                    f"{use_case}.M2_vs_M_TOP4",
                    alternative="two-sided",
                )
                if recomputed is None:  # pragma: no cover
                    raise ExtractionError(f"{use_case}: ablazione mancante")
                expected_w, expected_p = recomputed
                if not all(
                    isinstance(ablation.get(key), (int, float))
                    and math.isclose(float(ablation[key]), expected, rel_tol=1e-12, abs_tol=1e-12)
                    for key, expected in (("W", expected_w), ("p", expected_p))
                ):
                    raise ExtractionError(
                        f"{use_case}.{ablation_key} non coincide con _iterazioni"
                    )
                displayed_ablation_p = _validated_holm_p(
                    ablation, expected_p, f"{use_case}.{ablation_key}"
                )
            else:
                displayed_ablation_p = float(ablation["p"])
            ablations.append(
                (
                    f"% ablazione {use_case}, M2 vs M_TOP4 (Wilcoxon bilaterale): "
                    f"p={displayed_ablation_p:.6g}"
                )
            )
    return _section(
        "riepilogo_rho",
        "UC & variante & success_rate & M_bar & rho_vs_M1 & p_vs_M1",
        [*rows, *ablations],
    )


def render_zne(source: Source) -> list[str]:
    strategies = _strategies(source)
    config = _mapping(source.payload.get("config", {}), f"config in {source.path}")
    base_shots = config.get("SHOTS")
    shot_multipliers = {"M1": 1, "ZNE-2": 2, "ZNE-3": 3, "TOP4": 1}
    labels = {
        "M1": "M1 (baseline)",
        "ZNE-2": "ZNE-2 (lineare)",
        "ZNE-3": "ZNE-3 (Richardson)",
        "TOP4": r"$M_{\text{TOP4}}$",
    }
    m1 = _mapping(strategies["M1"], "strategies.M1")
    modern_comparisons: dict[str, Mapping[str, Any]] = {}
    if not source.legacy:
        multiplicity = _mapping(
            source.payload.get("multiplicity"), f"multiplicity in {source.path}"
        )
        if multiplicity.get("method") != "Holm" or multiplicity.get("alpha") != 0.05:
            raise ExtractionError(
                f"{source.path}: multiplicity deve dichiarare Holm con alpha=0.05"
            )
        stored_comparisons = _mapping(
            source.payload.get("comparisons_vs_M1"),
            f"comparisons_vs_M1 in {source.path}",
        )
        expected_names = ("ZNE-2", "ZNE-3", "TOP4")
        if set(stored_comparisons) != set(expected_names):
            raise ExtractionError(
                f"{source.path}: comparisons_vs_M1 deve contenere ZNE-2, ZNE-3 e TOP4"
            )
        for key in expected_names:
            summary = _mapping(strategies[key], f"strategies.{key}")
            stored = _mapping(stored_comparisons[key], f"comparisons_vs_M1.{key}")
            if stored.get("alternative") != "greater":
                raise ExtractionError(
                    f"comparisons_vs_M1.{key}: alternative deve essere greater"
                )
            recomputed = _paired_wilcoxon(m1, summary, f"strategies.{key}")
            if recomputed is None:  # pragma: no cover
                raise ExtractionError(f"strategies.{key}: baseline M1 mancante")
            statistic, raw_p = recomputed
            if not all(
                isinstance(stored.get(field), (int, float))
                and not isinstance(stored.get(field), bool)
                and math.isfinite(float(stored[field]))
                and math.isclose(float(stored[field]), expected, rel_tol=1e-12, abs_tol=1e-12)
                for field, expected in (("W", statistic), ("p", raw_p))
            ):
                raise ExtractionError(
                    f"comparisons_vs_M1.{key}: W/p non coincidono con all_iters"
                )
            _validated_holm_p(stored, raw_p, f"comparisons_vs_M1.{key}")
            modern_comparisons[key] = stored
        _validate_holm_family(modern_comparisons, "comparisons_vs_M1")

    rows: list[str] = []
    for key in ("M1", "ZNE-2", "ZNE-3", "TOP4"):
        summary = _mapping(strategies[key], f"strategies.{key}")
        if key == "M1":
            p_value = None
        elif source.legacy:
            p_value = _comparison_greater(
                m1, summary, f"strategies.{key}", legacy=True
            )
        else:
            p_value = float(modern_comparisons[key]["p_holm"])
        rho_value = None if key == "M1" else _rho(summary, m1)
        shots_per_iteration = (
            str(int(base_shots) * shot_multipliers[key])
            if isinstance(base_shots, (int, float))
            else "N/A"
        )
        row = [
            labels[key],
            _percent(summary.get("success_rate")),
            _number(summary.get("M_bar")),
            shots_per_iteration,
            _number(summary.get("shots_mean"), digits=0),
            _rho_text(rho_value),
            _p_text(p_value, True),
        ]
        rows.append("        " + " & ".join(row) + r" \\")
    return _section(
        "confronto_zne",
        "strategia & success_rate & M_bar & shot_iter & shot_totali & rho & p",
        rows,
    )


def _provenance(sources: Sequence[Source]) -> list[str]:
    lines = [
        "% Generato deterministicamente da extract_latex.py.",
        "% I fallimenti in all_iters sono sentinel gia' codificati nei JSON e non vengono alterati.",
    ]
    if any(not source.legacy for source in sources):
        lines.append(
            "% Confronti schema v2: Wilcoxon appaiato unilaterale, "
            "alternative='greater', zero_method='pratt'."
        )
    for source in sources:
        version = source.payload.get("schema_version", "storico")
        timestamp = source.payload.get("timestamp", "non disponibile")
        lines.append(
            f"% source[{source.kind}]: {source.path.as_posix()} | "
            f"sha256={source.sha256} | schema={version} | "
            f"analysis_revision={source.payload.get('analysis_revision', 'storico')} | "
            f"timestamp={timestamp}"
        )
        manifest = source.payload.get("manifest")
        if isinstance(manifest, dict):
            lines.append(
                "% manifest: "
                f"circuit_revision={manifest.get('circuit_revision', 'N/A')} | "
                f"circuit_sha256={manifest.get('circuit_sha256', 'N/A')} | "
                f"noise_model_revision={manifest.get('noise_model_revision', 'N/A')} | "
                f"seed_transpiler={manifest.get('seed_transpiler', 'N/A')}"
            )
        if source.legacy:
            lines.append("% ATTENZIONE: sorgente storica accettata esplicitamente.")
        elif source.kind == "parameter":
            config = source.payload.get("config")
            if isinstance(config, dict) and isinstance(config.get("inferential_scope"), str):
                lines.append(f"% inferential_scope: {config['inferential_scope']}")
    lines.append("")
    return lines


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Estrae snippet LaTeX dagli artefatti sperimentali JSON v2."
    )
    parser.add_argument(
        "--parameter-json",
        action="append",
        nargs="+",
        required=True,
        type=Path,
        metavar="PATH",
        help="uno o piu' risultati parameter-analysis v2; il flag e' ripetibile",
    )
    parser.add_argument("--baseline-json", type=Path, help="risultato baseline v2 opzionale")
    parser.add_argument("--zne-json", type=Path, help="risultato ZNE v2 opzionale")
    parser.add_argument(
        "--allow-legacy-schema",
        "--allow-historical-schema",
        action="store_true",
        dest="allow_legacy_schema",
        help="accetta consapevolmente artefatti privi del contratto v2",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    parameter_paths = [path for group in args.parameter_json for path in group]

    try:
        parameter_sources = [
            _load_source(path, "parameter", args.allow_legacy_schema)
            for path in parameter_paths
        ]
        baseline_source = (
            _load_source(args.baseline_json, "baseline", args.allow_legacy_schema)
            if args.baseline_json
            else None
        )
        zne_source = (
            _load_source(args.zne_json, "zne", args.allow_legacy_schema)
            if args.zne_json
            else None
        )

        (
            sweeps,
            baseline_m1,
            parameter_manifest,
            legacy_sweeps,
        ) = _merge_parameter_sources(parameter_sources)
        if baseline_source is not None:
            _check_manifest_compatibility(parameter_manifest, baseline_source)
            if baseline_m1 is None:
                baseline_m1 = _baseline_from_campaign(baseline_source)
        if zne_source is not None:
            _check_manifest_compatibility(parameter_manifest, zne_source)

        all_sources = [*parameter_sources]
        if baseline_source is not None:
            all_sources.append(baseline_source)
        if zne_source is not None:
            all_sources.append(zne_source)
        if len({source.legacy for source in all_sources}) > 1:
            raise ExtractionError(
                "non e' consentito mescolare sorgenti v2 e storiche nella stessa estrazione"
            )

        lines = _provenance(all_sources)
        lines.extend(render_parameter_sweeps(sweeps, baseline_m1, legacy_sweeps))
        if baseline_source is not None:
            lines.extend(render_baseline(baseline_source))
        if zne_source is not None:
            lines.extend(render_zne(zne_source))
    except ExtractionError as exc:
        parser.error(str(exc))

    print("\n".join(lines).rstrip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
