"""Exact checks for theory/extensions/random-sign-count-design.md.

Run from the repository root:
    python3 theory/scripts/check_random_sign_encoding.py

Mapping multisets carry their exact multinomial weights. All encoded signs
are enumerated. The ideal checksum is a formal coefficient vector; these
checks do not estimate collision probabilities of finite checksum fields.
"""

from collections import Counter
from fractions import Fraction
from itertools import combinations, combinations_with_replacement, product
from math import comb, factorial
from pathlib import Path
import json


def core_of(edges, cells):
    active = set(range(len(edges)))
    while active:
        degrees = [sum(v in edges[i] for i in active) for v in range(cells)]
        pure = next((v for v, degree in enumerate(degrees) if degree == 1), None)
        if pure is None:
            break
        active.remove(next(i for i in active if pure in edges[i]))
    return active


def add_item(table, edge, key_index, coefficient, keys):
    for v in edge:
        table[v][0] += coefficient
        table[v][1] += coefficient * keys[key_index]
        table[v][2][key_index] += coefficient


def blank_table(cells, items):
    return [[0, 0, [0] * items] for _ in range(cells)]


def decode(edges, effective, original, cells):
    """Exercise aggregate-based recovery, with a collision-free formal checksum."""
    keys = [17 + 13 * i for i in range(len(edges))]
    key_index = {key: i for i, key in enumerate(keys)}
    random_signs = [a * b for a, b in zip(effective, original)]
    table = blank_table(cells, len(edges))
    for i, edge in enumerate(edges):
        add_item(table, edge, i, effective[i], keys)
    recovered = {}
    while True:
        candidate = None
        for v, (count, key_sum, checksum) in enumerate(table):
            if abs(count) != 1:
                continue
            i = key_index.get(count * key_sum)
            if i is None or v not in edges[i]:
                continue
            expected = [0] * len(edges)
            expected[i] = count
            if checksum == expected:
                candidate = (i, count)
                break
        if candidate is None:
            break
        i, coefficient = candidate
        assert i not in recovered
        recovered[i] = coefficient * random_signs[i]
        assert recovered[i] == original[i]
        add_item(table, edges[i], i, -coefficient, keys)
    remaining = set(range(len(edges))) - set(recovered)
    assert remaining == core_of(edges, cells)
    assert all(row == [0, 0, [0] * len(edges)] for row in table) == (not remaining)
    return len(recovered)


def check_common_cancellation():
    edges = [(0, 1, 2), (0, 2, 3), (1, 2, 3)]
    keys = [17, 30, 43]
    checked = 0
    for random_signs in product((-1, 1), repeat=3):
        # First item is common; item 1 is A-only and item 2 is B-only.
        left, right = blank_table(4, 3), blank_table(4, 3)
        for i in (0, 1):
            add_item(left, edges[i], i, random_signs[i], keys)
        for i in (0, 2):
            add_item(right, edges[i], i, random_signs[i], keys)
        difference = [[a[0] - b[0], a[1] - b[1],
                       [x - y for x, y in zip(a[2], b[2])]]
                      for a, b in zip(left, right)]
        direct = blank_table(4, 3)
        add_item(direct, edges[1], 1, random_signs[1], keys)
        add_item(direct, edges[2], 2, -random_signs[2], keys)
        assert difference == direct
        checked += 1
    return checked


def check_configuration(cells, k, d):
    types = list(combinations(range(cells), k))
    signs = list(product((-1, 1), repeat=d))
    pairs = list(combinations(range(d), 2))
    triangles = list(combinations(range(d), 3))
    denominator = k * (cells - k)
    graph_count = state_count = recovered_count = 0
    labeled_count = failed_count = 0
    variance_sum = failed_variance_sum = failed_third_sum = Fraction(0)
    failed_zero_signs = 0
    graph_classes = Counter()
    for indices in combinations_with_replacement(range(len(types)), d):
        multiplicity = factorial(d)
        for n in Counter(indices).values():
            multiplicity //= factorial(n)
        edges = [types[i] for i in indices]
        edge_sets = [set(edge) for edge in edges]
        overlaps = {(i, j): cells * len(edge_sets[i] & edge_sets[j]) - k*k
                    for i, j in pairs}
        deviations = []
        numerators = []
        original = tuple(1 if i % 2 == 0 else -1 for i in range(d))
        for effective in signs:
            counts = [sum(effective[i] for i in range(d) if v in edges[i])
                      for v in range(cells)]
            numerator = cells * sum(c*c for c in counts) - sum(counts)**2
            delta = numerator - d * denominator
            assert delta == 2 * sum(w * effective[i] * effective[j]
                                    for (i, j), w in overlaps.items())
            numerators.append(numerator)
            deviations.append(delta)
            recovered_count += decode(edges, effective, original, cells)
        assert sum(deviations) == 0
        variance = Fraction(sum(x*x for x in deviations), len(signs)*denominator**2)
        predicted_variance = Fraction(4 * sum(w*w for w in overlaps.values()),
                                      denominator**2)
        third = Fraction(sum(x**3 for x in deviations), len(signs)*denominator**3)
        predicted_third = Fraction(
            48 * sum(overlaps[i, j] * overlaps[i, h] * overlaps[j, h]
                     for i, j, h in triangles), denominator**3)
        assert variance == predicted_variance
        assert third == predicted_third
        assert variance <= 2*d*(d-1)
        assert all(0 <= x <= d*d*denominator for x in numerators)
        failed = bool(core_of(edges, cells))
        # Reweight every original direction pattern on the first graph to
        # verify distributional invariance and recovery for all compositions.
        if graph_count == 0:
            by_effective = dict(zip(signs, numerators))
            target_histogram = Counter(numerators)
            for direction in signs:
                effective_states = [tuple(a*b for a, b in zip(direction, eps))
                                    for eps in signs]
                assert Counter(by_effective[e] for e in effective_states) == target_histogram
                for effective in effective_states:
                    decode(edges, effective, direction, cells)
        graph_count += 1
        state_count += len(signs)
        labeled_count += multiplicity
        variance_sum += multiplicity * variance
        graph_classes[len(core_of(edges, cells))] += multiplicity
        if failed:
            failed_count += multiplicity
            failed_variance_sum += multiplicity * variance
            failed_third_sum += multiplicity * third
            failed_zero_signs += multiplicity * numerators.count(0)
    assert labeled_count == len(types)**d
    unconditional_variance = variance_sum / labeled_count
    assert unconditional_variance == Fraction(2*d*(d-1), cells-1)
    return {
        "M": cells, "k": k, "d": d,
        "mapping_multisets": graph_count,
        "effective_sign_states_checked": state_count,
        "recovered_items_checked": recovered_count,
        "labeled_mapping_count": labeled_count,
        "failure_probability": str(Fraction(failed_count, labeled_count)),
        "unconditional_mean": d, "failure_conditional_mean": d,
        "unconditional_variance": str(unconditional_variance),
        "failure_conditional_variance": str(failed_variance_sum / failed_count),
        "failure_conditional_third_central_moment": str(failed_third_sum / failed_count),
        "failure_conditional_zero_probability": str(Fraction(failed_zero_signs,
                                                              failed_count*len(signs))),
        "core_size_labeled_counts": dict(sorted(graph_classes.items())),
    }


def check_repetition_bound():
    # Each block averages 32 conditionally independent count channels.
    # Var(block|G) <= d^2/16; Cantelli at d/2 yields p <= 1/5.
    bound = sum(Fraction(comb(51, j)*4**(51-j), 5**51) for j in range(26, 52))
    assert bound < Fraction(1, 10**6)
    # d=2 and a duplicated edge: a block is 4*Binomial(32,1/2)/32.
    duplicated_pair_bad_block = Fraction(sum(comb(32, j) for j in range(8)), 2**32)
    assert duplicated_pair_bad_block <= Fraction(1, 5)
    return {
        "channels_per_block": 32, "blocks": 51, "count_channels": 1632,
        "upper_bound_multiplier": 2,
        "graph_uniform_undercoverage_bound_exact": str(bound),
        "graph_uniform_undercoverage_bound": float(bound),
        "duplicated_pair_single_channel_zero_probability": "1/2",
        "duplicated_pair_block_under_half_probability": str(duplicated_pair_bad_block),
    }


def main():
    cases = [(4, 3, 2), (4, 3, 3), (4, 3, 4), (5, 3, 3), (5, 3, 4), (6, 3, 4)]
    rows = [check_configuration(*case) for case in cases]
    assert rows[0]["failure_conditional_zero_probability"] == "1/2"
    result = {
        "arithmetic": "exact integer and rational",
        "all_checks_passed": True,
        "mapping_multisets": sum(r["mapping_multisets"] for r in rows),
        "effective_sign_states_checked": sum(r["effective_sign_states_checked"] for r in rows),
        "common_cancellation_checks": check_common_cancellation(),
        "cases": rows,
        "finite_repetition_guarantee": check_repetition_bound(),
        "scope": "Finite encoding, peeling, moment and probability identities; not a CLT verification or a finite-checksum collision analysis.",
    }
    output = Path(__file__).resolve().parents[1] / "diagnostics/random-sign-encoding-exact.json"
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "cases"}, indent=2))


if __name__ == "__main__":
    main()
