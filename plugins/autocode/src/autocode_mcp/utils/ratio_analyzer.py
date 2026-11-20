import math
import re
from typing import Any


def normalize_complexity_expression(expr: str | None) -> str:
    if not expr or not isinstance(expr, str):
        return "O(n)"
    cleaned = expr.strip().lower()
    cleaned = cleaned.replace("\\log", "log").replace("\\cdot", "*").replace("\\times", "*")
    cleaned = re.sub(r"\s+", "", cleaned)
    match = re.search(r"o\((.+)\)", cleaned)
    if match:
        inner = match.group(1)
    else:
        inner = cleaned
    inner = inner.replace("*", "")
    inner = inner.replace("log(n)", "logn").replace("sqrt(n)", "sqrtn")
    inner = inner.replace("**", "^")

    # 映射为标准包含空格形式
    mapping = {
        "1": "O(1)",
        "logn": "O(log n)",
        "log2n": "O(log n)",
        "n": "O(n)",
        "nlogn": "O(n log n)",
        "nsqrtn": "O(n sqrt n)",
        "n^2": "O(n^2)",
        "n^3": "O(n^3)",
        "2^n": "O(2^n)",
        "n2^n": "O(n 2^n)",
        "n^22^n": "O(n^2 2^n)",
        "3^n": "O(3^n)",
        "n!": "O(n!)",
    }
    return mapping.get(inner, f"O({inner})")


class EmpiricalRatioAnalyzer:
    COMPLEXITY_ALPHA_RANGES: dict[str, tuple[float, float]] = {
        "O(1)": (-0.2, 0.35),
        "O(log n)": (-0.05, 0.65),
        "O(logn)": (-0.05, 0.65),
        "O(n)": (-0.25, 1.35),
        "O(n log n)": (-0.25, 1.45),
        "O(nlogn)": (-0.25, 1.45),
        "O(n sqrt n)": (1.15, 1.75),
        "O(nsqrtn)": (1.15, 1.75),
        "O(n^2)": (1.65, 2.35),
        "O(n^3)": (2.50, 3.45),
        "O(2^n)": (3.50, 100.0),
        "O(n 2^n)": (3.50, 100.0),
        "O(n^2 2^n)": (3.50, 100.0),
        "O(3^n)": (4.50, 150.0),
        "O(n!)": (3.50, 100.0),
    }

    EXPONENTIAL_BASE_RANGES: dict[str, tuple[float, float]] = {
        "O(2^n)": (1.45, 2.75),
        "O(n 2^n)": (1.45, 3.00),
        "O(n^2 2^n)": (1.45, 3.25),
        "O(3^n)": (2.10, 4.10),
    }

    @classmethod
    def evaluate_complexity_function(cls, normalized_expr: str, n: float) -> float:
        if n <= 1:
            n = 1.0001
        if normalized_expr in ("O(1)",):
            return 1.0
        if normalized_expr in ("O(log n)", "O(logn)"):
            return math.log2(max(2.0, n))
        if normalized_expr in ("O(n)",):
            return n
        if normalized_expr in ("O(n log n)", "O(nlogn)"):
            return n * math.log2(max(2.0, n))
        if normalized_expr in ("O(n sqrt n)", "O(nsqrtn)"):
            return n * math.sqrt(n)
        if normalized_expr in ("O(n^2)",):
            return n * n
        if normalized_expr in ("O(n^3)",):
            return n * n * n
        if normalized_expr in ("O(2^n)",):
            return math.pow(2.0, min(n, 1020.0))
        if normalized_expr in ("O(n 2^n)",):
            return n * math.pow(2.0, min(n, 1000.0))
        if normalized_expr in ("O(n^2 2^n)",):
            return (n * n) * math.pow(2.0, min(n, 980.0))
        if normalized_expr in ("O(3^n)",):
            return math.pow(3.0, min(n, 640.0))
        if normalized_expr in ("O(n!)",):
            int_n = max(1, min(int(n), 170))
            return float(math.factorial(int_n))
        return n

    @classmethod
    def calculate_expected_ratio(cls, claimed_complexity: str, n_from: int, n_to: int) -> float:
        norm_expr = normalize_complexity_expression(claimed_complexity)
        if norm_expr == "O(n!)":
            if n_from <= 0:
                n_from = 1
            if n_to <= 0:
                n_to = 1
            if n_to == n_from:
                return 1.0
            if n_to > n_from:
                ratio = 1.0
                for k in range(n_from + 1, n_to + 1):
                    ratio *= k
                    if ratio > 1e12:
                        return 1e12
                return ratio
            else:
                ratio = 1.0
                for k in range(n_to + 1, n_from + 1):
                    ratio *= k
                    if ratio > 1e12:
                        return 0.0
                return 1.0 / ratio if ratio > 0 else 0.0

        if norm_expr == "O(2^n)":
            diff = float(n_to - n_from)
            clamped_diff = min(max(diff, -100.0), 100.0)
            return math.pow(2.0, clamped_diff)

        if norm_expr == "O(n 2^n)":
            diff = float(n_to - n_from)
            clamped_diff = min(max(diff, -100.0), 100.0)
            n_ratio = (float(n_to) / float(n_from)) if n_from > 0 else 1.0
            return n_ratio * math.pow(2.0, clamped_diff)

        if norm_expr == "O(n^2 2^n)":
            diff = float(n_to - n_from)
            clamped_diff = min(max(diff, -100.0), 100.0)
            n_ratio = ((float(n_to) / float(n_from)) ** 2) if n_from > 0 else 1.0
            return n_ratio * math.pow(2.0, clamped_diff)

        if norm_expr == "O(3^n)":
            diff = float(n_to - n_from)
            clamped_diff = min(max(diff, -60.0), 60.0)
            return math.pow(3.0, clamped_diff)

        val_from = cls.evaluate_complexity_function(norm_expr, float(n_from))
        val_to = cls.evaluate_complexity_function(norm_expr, float(n_to))
        if val_from <= 0:
            return 1.0
        return val_to / val_from

    @classmethod
    def fit_log_linear(cls, samples: list[dict[str, Any]]) -> tuple[float, float]:
        valid_points: list[tuple[float, float]] = []
        for s in samples:
            try:
                n_val = float(s.get("n", 0) or 0)
                t_val = float(s.get("cpu_time_ms", 0.0) or 0.0)
            except (ValueError, TypeError):
                continue
            if n_val > 1 and t_val > 0.01 and math.isfinite(n_val) and math.isfinite(t_val):
                valid_points.append((math.log(n_val), math.log(t_val)))

        if len(valid_points) < 2:
            return 1.0, 0.0

        n_count = len(valid_points)
        sum_x = sum(p[0] for p in valid_points)
        sum_y = sum(p[1] for p in valid_points)
        sum_xx = sum(p[0] * p[0] for p in valid_points)
        sum_xy = sum(p[0] * p[1] for p in valid_points)

        denom = n_count * sum_xx - sum_x * sum_x
        if abs(denom) < 1e-9:
            return 1.0, 0.0

        alpha = (n_count * sum_xy - sum_x * sum_y) / denom
        beta = (sum_y - alpha * sum_x) / n_count

        mean_y = sum_y / n_count
        ss_tot = sum((p[1] - mean_y) ** 2 for p in valid_points)
        ss_res = sum((p[1] - (alpha * p[0] + beta)) ** 2 for p in valid_points)

        if ss_tot < 1e-9:
            r_squared = 1.0
        else:
            r_squared = max(0.0, 1.0 - (ss_res / ss_tot))

        return alpha, r_squared

    @classmethod
    def _linear_regression(cls, points: list[tuple[float, float]]) -> tuple[float, float, float]:
        """Ordinary least-squares fit y = slope * x + intercept; returns (slope, intercept, r_squared)."""
        if len(points) < 2:
            return 0.0, 0.0, 0.0
        n_count = len(points)
        sum_x = sum(p[0] for p in points)
        sum_y = sum(p[1] for p in points)
        sum_xx = sum(p[0] * p[0] for p in points)
        sum_xy = sum(p[0] * p[1] for p in points)
        denom = n_count * sum_xx - sum_x * sum_x
        if abs(denom) < 1e-9:
            return 0.0, sum_y / n_count, 0.0
        slope = (n_count * sum_xy - sum_x * sum_y) / denom
        intercept = (sum_y - slope * sum_x) / n_count
        mean_y = sum_y / n_count
        ss_tot = sum((p[1] - mean_y) ** 2 for p in points)
        ss_res = sum((p[1] - (slope * p[0] + intercept)) ** 2 for p in points)
        r_squared = 1.0 if ss_tot < 1e-9 else max(0.0, 1.0 - (ss_res / ss_tot))
        return slope, intercept, r_squared

    @classmethod
    def fit_exponential(cls, samples: list[dict[str, Any]]) -> tuple[float, float, float]:
        """Fit semi-log exponential model log2(t) = beta * n + c; returns (base=2**beta, beta, r_squared)."""
        pts: list[tuple[float, float]] = []
        for s in samples:
            try:
                n_val = float(s.get("n", 0) or 0)
                t_val = float(s.get("cpu_time_ms", 0.0) or 0.0)
            except (ValueError, TypeError):
                continue
            if n_val >= 1 and t_val > 0.01 and math.isfinite(n_val) and math.isfinite(t_val):
                pts.append((n_val, math.log2(t_val)))
        if len(pts) < 2:
            return 1.0, 0.0, 0.0
        beta, _, r2 = cls._linear_regression(pts)
        clamped_beta = min(max(beta, -20.0), 20.0)
        return math.pow(2.0, clamped_beta), beta, r2

    @classmethod
    def fit_query_log_linear(cls, samples: list[dict[str, Any]]) -> tuple[float, float, float]:
        """Fit interactive query curve queries = a * log2(n) + b; returns (a, b, r_squared)."""
        pts: list[tuple[float, float]] = []
        for s in samples:
            try:
                n_val = float(s.get("n", 0) or 0)
                q_val = float(s.get("queries", 0) or 0)
            except (ValueError, TypeError):
                continue
            if n_val > 1 and q_val > 0 and math.isfinite(n_val) and math.isfinite(q_val):
                pts.append((math.log2(n_val), q_val))
        return cls._linear_regression(pts)

    @classmethod
    def fit_query_power_law(cls, samples: list[dict[str, Any]]) -> tuple[float, float]:
        """Fit log-log query scaling ln(queries) = alpha * ln(n) + c; returns (alpha, r_squared)."""
        pts: list[tuple[float, float]] = []
        for s in samples:
            try:
                n_val = float(s.get("n", 0) or 0)
                q_val = float(s.get("queries", 0) or 0)
            except (ValueError, TypeError):
                continue
            if n_val > 1 and q_val > 0 and math.isfinite(n_val) and math.isfinite(q_val):
                pts.append((math.log(n_val), math.log(q_val)))
        if len(pts) < 2:
            return 0.0, 0.0
        alpha, _, r2 = cls._linear_regression(pts)
        return alpha, r2

    @classmethod
    def verify_query_complexity(
        cls,
        claimed_complexity: str,
        samples: list[dict[str, Any]],
        *,
        max_queries: int | None = None,
        time_limit_ms: float = 2000.0,
    ) -> dict[str, Any]:
        """Verify interactive query-count scaling (e.g. queries vs log2(n)) instead of noisy pipe CPU time."""
        norm_claimed = normalize_complexity_expression(claimed_complexity)
        if samples and samples[-1].get("status") == "timeout":
            last_sample = samples[-1]
            return {
                "passed": False,
                "verdict": "timeout_at_extreme",
                "fit_metric": "queries",
                "failure_reason": f"Execution timed out at extreme test point (N={last_sample.get('n')})",
                "claimed_complexity": norm_claimed,
                "fitted_complexity": "timeout",
                "fitted_alpha": None,
                "r_squared": None,
                "samples": samples,
                "growth_ratios": [],
                "remediation_advice": f"Interactive execution timed out on N={last_sample.get('n')}.",
            }

        valid_samples = [
            s
            for s in samples
            if s.get("status") == "ok"
            and isinstance(s.get("queries"), int | float)
            and not isinstance(s.get("queries"), bool)
            and float(s["queries"]) > 0
        ]
        if len(valid_samples) < 2:
            return {
                "passed": False,
                "verdict": "insufficient_samples",
                "fit_metric": "queries",
                "failure_reason": "Insufficient valid interactive query samples collected (minimum 2 required)",
                "claimed_complexity": norm_claimed,
                "fitted_complexity": "unknown",
                "fitted_alpha": None,
                "r_squared": None,
                "samples": samples,
                "growth_ratios": [],
                "remediation_advice": "Ensure interactor reports `queries=<k>` or exchanges interaction messages across scale points.",
            }

        max_obs_queries = max(int(s["queries"]) for s in valid_samples)
        if max_queries is not None and max_obs_queries > max_queries:
            return {
                "passed": False,
                "verdict": "query_budget_exceeded",
                "fit_metric": "queries",
                "failure_reason": f"Observed max queries ({max_obs_queries}) exceeded protocol.max_queries ({max_queries})",
                "claimed_complexity": norm_claimed,
                "fitted_complexity": "over_budget",
                "fitted_alpha": None,
                "r_squared": None,
                "max_observed_queries": max_obs_queries,
                "max_queries_limit": max_queries,
                "samples": samples,
                "growth_ratios": [],
                "remediation_advice": "Reduce query count or update protocol.max_queries to match the intended algorithm.",
            }

        slope_log2, intercept_log2, log2_r2 = cls.fit_query_log_linear(valid_samples)
        q_alpha, q_alpha_r2 = cls.fit_query_power_law(valid_samples)

        growth_ratios: list[dict[str, Any]] = []
        for i in range(len(valid_samples) - 1):
            s_from = valid_samples[i]
            s_to = valid_samples[i + 1]
            n_from = int(s_from["n"])
            n_to = int(s_to["n"])
            q_from = float(s_from["queries"])
            q_to = float(s_to["queries"])
            growth_ratios.append(
                {
                    "from_n": n_from,
                    "to_n": n_to,
                    "from_queries": int(q_from),
                    "to_queries": int(q_to),
                    "observed_ratio": round(q_to / max(q_from, 1.0), 2),
                    "expected_ratio": round(cls.calculate_expected_ratio(norm_claimed, n_from, n_to), 2),
                    "delta_log2_n": round(
                        math.log2(max(2.0, float(n_to))) - math.log2(max(2.0, float(n_from))), 2
                    ),
                }
            )

        cpu_times = [
            float(s["cpu_time_ms"])
            for s in valid_samples
            if s.get("cpu_time_ms") is not None and math.isfinite(float(s["cpu_time_ms"]))
        ]
        max_cpu = max(cpu_times) if cpu_times else 0.0
        headroom_ratio = max_cpu / time_limit_ms if time_limit_ms > 0 else 0.0

        query_curve = {
            "model": "queries = a * log2(n) + b",
            "queries_per_log2_n": round(slope_log2, 3),
            "intercept": round(intercept_log2, 3),
            "log2_r_squared": round(log2_r2, 3),
            "power_law_alpha": round(q_alpha, 3),
            "power_law_r_squared": round(q_alpha_r2, 3),
            "max_observed_queries": max_obs_queries,
        }

        if norm_claimed in ("O(log n)", "O(logn)"):
            # Falsify polynomial query growth (e.g. O(n) disguised as O(log n))
            if q_alpha > 0.65 and (q_alpha_r2 >= 0.80 or max_obs_queries > 4 * math.log2(max(4, int(valid_samples[-1]["n"]))) + 20):
                fitted_cat = cls.infer_complexity_category(q_alpha)
                return {
                    "passed": False,
                    "verdict": "query_ratio_mismatch",
                    "fit_metric": "queries",
                    "fit_model": "query_log2",
                    "failure_reason": (
                        f"Interactive query count scales as {fitted_cat} (alpha={q_alpha:.2f}, "
                        f"slope={slope_log2:.2f}/log2(n)), inconsistent with claimed {norm_claimed}"
                    ),
                    "claimed_complexity": norm_claimed,
                    "fitted_complexity": fitted_cat,
                    "fitted_alpha": round(q_alpha, 3),
                    "r_squared": round(q_alpha_r2, 3),
                    "query_curve": query_curve,
                    "samples": samples,
                    "growth_ratios": growth_ratios,
                    "remediation_advice": "Interactive solution issues too many queries as n grows; verify binary/logarithmic narrowing logic.",
                }
            fitted_label = "O(log n)" if slope_log2 > 0.05 else "O(1)"
            return {
                "passed": True,
                "verdict": "verified_query_curve",
                "fit_metric": "queries",
                "fit_model": "query_log2",
                "claimed_complexity": norm_claimed,
                "fitted_complexity": fitted_label,
                "fitted_alpha": round(q_alpha, 3),
                "r_squared": round(log2_r2, 3),
                "query_curve": query_curve,
                "samples": samples,
                "growth_ratios": growth_ratios,
                "max_scale_headroom_ratio": round(headroom_ratio, 3),
            }

        expected_range = cls.COMPLEXITY_ALPHA_RANGES.get(norm_claimed, (0.65, 1.35))
        fitted_cat = cls.infer_complexity_category(q_alpha)
        if expected_range[0] <= q_alpha <= expected_range[1]:
            return {
                "passed": True,
                "verdict": "verified_query_curve",
                "fit_metric": "queries",
                "fit_model": "query_power_law",
                "claimed_complexity": norm_claimed,
                "fitted_complexity": fitted_cat,
                "fitted_alpha": round(q_alpha, 3),
                "r_squared": round(q_alpha_r2, 3),
                "query_curve": query_curve,
                "samples": samples,
                "growth_ratios": growth_ratios,
                "max_scale_headroom_ratio": round(headroom_ratio, 3),
            }

        return {
            "passed": False,
            "verdict": "query_ratio_mismatch",
            "fit_metric": "queries",
            "fit_model": "query_power_law",
            "failure_reason": (
                f"Measured query scaling alpha={q_alpha:.2f} (fitted as {fitted_cat}) "
                f"outside claimed {norm_claimed} range [{expected_range[0]}, {expected_range[1]}]"
            ),
            "claimed_complexity": norm_claimed,
            "fitted_complexity": fitted_cat,
            "fitted_alpha": round(q_alpha, 3),
            "r_squared": round(q_alpha_r2, 3),
            "query_curve": query_curve,
            "samples": samples,
            "growth_ratios": growth_ratios,
            "remediation_advice": f"Interactive query count exhibits {fitted_cat} growth rather than claimed {norm_claimed}.",
        }

    @classmethod
    def infer_complexity_category(cls, alpha: float) -> str:
        if alpha < 0.35:
            return "O(1)"
        if alpha < 0.65:
            return "O(log n)"
        if alpha < 1.35:
            return "O(n)"
        if alpha < 1.65:
            return "O(n log n)"
        if alpha < 1.85:
            return "O(n sqrt n)"
        if alpha < 2.50:
            return "O(n^2)"
        if alpha < 3.50:
            return "O(n^3)"
        return "O(2^n)"

    @classmethod
    def verify_complexity(
        cls,
        claimed_complexity: str,
        samples: list[dict[str, Any]],
        time_limit_ms: float = 2000.0,
    ) -> dict[str, Any]:
        norm_claimed = normalize_complexity_expression(claimed_complexity)
        valid_samples = [
            s for s in samples
            if s.get("status") == "ok"
            and s.get("cpu_time_ms") is not None
            and math.isfinite(float(s.get("cpu_time_ms", 0.0) or 0.0))
        ]

        if not valid_samples:
            return {
                "passed": False,
                "verdict": "no_valid_samples",
                "failure_reason": "No valid execution samples collected",
                "claimed_complexity": norm_claimed,
                "fitted_complexity": "unknown",
                "fitted_alpha": None,
                "r_squared": None,
                "samples": samples,
                "growth_ratios": [],
                "remediation_advice": "Check if generator and solution execute properly without immediate crash.",
            }

        last_sample = samples[-1]
        if last_sample.get("status") == "timeout":
            return {
                "passed": False,
                "verdict": "timeout_at_extreme",
                "failure_reason": f"Execution timed out at extreme test point (N={last_sample.get('n')})",
                "claimed_complexity": norm_claimed,
                "fitted_complexity": "timeout",
                "fitted_alpha": None,
                "r_squared": None,
                "samples": samples,
                "growth_ratios": [],
                "remediation_advice": f"Algorithm execution timed out on N={last_sample.get('n')}. Optimize time complexity or reduce constant factors.",
            }

        if len(valid_samples) < 2:
            return {
                "passed": False,
                "verdict": "insufficient_samples",
                "failure_reason": "Insufficient valid execution samples collected (minimum 2 required)",
                "claimed_complexity": norm_claimed,
                "fitted_complexity": "unknown",
                "fitted_alpha": None,
                "r_squared": None,
                "samples": samples,
                "growth_ratios": [],
                "remediation_advice": "Ensure generator produces inputs and solution executes without early crash.",
            }

        alpha, r_squared = cls.fit_log_linear(valid_samples)
        fitted_cat = cls.infer_complexity_category(alpha)

        expected_range = cls.COMPLEXITY_ALPHA_RANGES.get(norm_claimed, (0.65, 1.35))
        is_alpha_match = expected_range[0] <= alpha <= expected_range[1]
        fit_model = "log_linear"
        exponential_fit: dict[str, Any] | None = None

        if norm_claimed in cls.EXPONENTIAL_BASE_RANGES:
            exp_base, exp_beta, exp_r2 = cls.fit_exponential(valid_samples)
            base_lo, base_hi = cls.EXPONENTIAL_BASE_RANGES[norm_claimed]
            exponential_fit = {
                "base": round(exp_base, 3),
                "beta_log2": round(exp_beta, 3),
                "r_squared": round(exp_r2, 3),
                "expected_base_range": [base_lo, base_hi],
            }
            if base_lo <= exp_base <= base_hi and exp_r2 >= 0.70:
                fit_model = "exponential"
                is_alpha_match = True
                fitted_cat = norm_claimed
                r_squared = exp_r2

        # 若后段高信噪比测点（后 3 点）呈现显著高阶增长，采用后段拟合结果以防前段底噪平线掩盖真实复杂度
        if fit_model == "log_linear" and len(valid_samples) >= 4:
            tail_samples = valid_samples[-3:]
            tail_alpha, tail_r2 = cls.fit_log_linear(tail_samples)
            if tail_alpha > expected_range[1]:
                is_alpha_match = False
                alpha = tail_alpha
                fitted_cat = cls.infer_complexity_category(tail_alpha)
                r_squared = tail_r2

        growth_ratios: list[dict[str, Any]] = []
        for i in range(len(valid_samples) - 1):
            s_from = valid_samples[i]
            s_to = valid_samples[i + 1]
            n_from = int(s_from["n"])
            n_to = int(s_to["n"])
            t_from = float(s_from["cpu_time_ms"])
            t_to = float(s_to["cpu_time_ms"])

            observed_ratio = (t_to / t_from) if t_from > 0.01 else 1.0
            expected_ratio = cls.calculate_expected_ratio(norm_claimed, n_from, n_to)

            growth_ratios.append(
                {
                    "from_n": n_from,
                    "to_n": n_to,
                    "scale_factor": round(float(n_to) / float(n_from), 2) if n_from > 0 else 1.0,
                    "observed_ratio": round(observed_ratio, 2),
                    "expected_ratio": round(expected_ratio, 2),
                }
            )

        max_sample = valid_samples[-1]
        max_time = float(max_sample["cpu_time_ms"])
        all_times = [float(s["cpu_time_ms"]) for s in valid_samples]
        peak_time = max(all_times)
        min_time = min(all_times)
        max_n = int(max_sample.get("n", 0))
        headroom_ratio = max_time / time_limit_ms if time_limit_ms > 0 else 1.0
        peak_headroom = peak_time / time_limit_ms if time_limit_ms > 0 else 1.0

        extra_meta: dict[str, Any] = {"fit_metric": "cpu_time_ms", "fit_model": fit_model}
        if exponential_fit is not None:
            extra_meta["exponential_fit"] = exponential_fit

        if not is_alpha_match:
            # 当全部样本耗时均处于 OS 计时底噪区间（<=15ms 且峰值 <5% TL），
            # 仅在不存在干净的高信噪比超阶增长信号（R^2>=0.90 且首尾缩放 >=4x 且最大点 >=2ms）时
            # 才按底噪豁免，既避免 O(1)/O(log n) 亚毫秒抖动误报，又不放过干净的 O(n^2)/O(n^3) 曲线。
            has_clean_high_order_signal = (
                alpha > expected_range[1]
                and r_squared >= 0.90
                and (max_time / max(min_time, 0.1)) >= 4.0
                and max_time >= 2.0
            )
            if peak_time <= 15.0 and peak_headroom < 0.05 and not has_clean_high_order_signal:
                return {
                    "passed": True,
                    "verdict": "verified_within_noise_floor",
                    "claimed_complexity": norm_claimed,
                    "fitted_complexity": norm_claimed,
                    "fitted_alpha": round(alpha, 2),
                    "r_squared": round(r_squared, 3),
                    "samples": samples,
                    "growth_ratios": growth_ratios,
                    "max_scale_headroom_ratio": round(headroom_ratio, 3),
                    "noise_floor_note": (
                        f"All scale samples completed within OS timer noise floor "
                        f"(peak={peak_time:.2f}ms <= 15ms, headroom={peak_headroom:.3f})."
                    ),
                    **extra_meta,
                }

            # 仅在规模足够大（跨越硬件缓存）且耗时余量充足时允许缓存跳跃容差
            if alpha > expected_range[1] and len(valid_samples) >= 3 and headroom_ratio < 0.40 and max_n >= 50000:
                sub_samples = valid_samples[:-1]
                sub_alpha, sub_r2 = cls.fit_log_linear(sub_samples)
                if expected_range[0] <= sub_alpha <= expected_range[1]:
                    return {
                        "passed": True,
                        "verdict": "verified_with_cache_jump",
                        "claimed_complexity": norm_claimed,
                        "fitted_complexity": norm_claimed,
                        "fitted_alpha": round(alpha, 2),
                        "r_squared": round(r_squared, 3),
                        "samples": samples,
                        "growth_ratios": growth_ratios,
                        "max_scale_headroom_ratio": round(headroom_ratio, 3),
                        "cache_jump_note": "Slight ratio jump observed at maximum scale likely due to L1/L2 cache capacity transition, well within time limit.",
                        **extra_meta,
                    }

            return {
                "passed": False,
                "verdict": "ratio_mismatch",
                "failure_reason": f"Measured complexity exponent alpha={alpha:.2f} (fitted as {fitted_cat}) outside claimed {norm_claimed} range [{expected_range[0]}, {expected_range[1]}]",
                "claimed_complexity": norm_claimed,
                "fitted_complexity": fitted_cat,
                "fitted_alpha": round(alpha, 2),
                "r_squared": round(r_squared, 3),
                "samples": samples,
                "growth_ratios": growth_ratios,
                "remediation_advice": (
                    f"The algorithm exhibits {fitted_cat} growth rather than claimed {norm_claimed}. "
                    "Inspect nested loops, optimize algorithm logic, update claimed_complexity, "
                    "or configure manifest.empirical_complexity (dominant_var/generator_args_template/scale_points) "
                    "for multi-parameter or exponential problems."
                ),
                **extra_meta,
            }

        return {
            "passed": True,
            "verdict": "verified",
            "claimed_complexity": norm_claimed,
            "fitted_complexity": fitted_cat,
            "fitted_alpha": round(alpha, 2),
            "r_squared": round(r_squared, 3),
            "samples": samples,
            "growth_ratios": growth_ratios,
            "max_scale_headroom_ratio": round(headroom_ratio, 3),
            **extra_meta,
        }
