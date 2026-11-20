"""
Generator 工具组 - 数据生成器。

基于论文 Algorithm 2: BUILDGENERATORSUITE 实现。
"""

from __future__ import annotations

import hashlib
import os
import re
from difflib import SequenceMatcher
from typing import Any

from pydantic import ValidationError

from ..utils.compiler import resolve_effective_compiler, run_binary, run_binary_with_args
from ..utils.platform import get_exe_extension
from ..workflow import load_manifest
from .base import Tool, ToolResult, input_schema_from_model
from .mixins import BuildToolMixin, resolve_source
from .schemas import GeneratorBuildInput, GeneratorRunInput


class GeneratorBuildTool(Tool, BuildToolMixin):
    """构建数据生成器。"""

    @property
    def name(self) -> str:
        return "generator_build"

    @property
    def description(self) -> str:
        return """构建数据生成器。

        保存并编译 gen.cpp。

        规范要求（testlib.h）：
        - 源码文件需包含 #include "testlib.h"
        - 入口函数首行必须调用 registerGen(argc, argv, 1);
        - 命令行传参结构：gen <seed> <type> <n_min> <n_max> <t_min> <t_max> [extra_args...]
        - 类型参数语义：1=tiny, 2=random, 3=extreme, 4=tle

        前置条件：
        1. 已运行 problem_create 创建题目目录

        建议下一步：
        - 运行 validator_build 构建校验器
        - 运行 stress_test_run 进行对拍测试
        """

    @property
    def input_schema(self) -> dict:
        return input_schema_from_model(GeneratorBuildInput)

    async def execute(
        self,
        problem_dir: str,
        code: str | None = None,
        source_path: str | None = None,
        compiler: str | None = None,
        enable_semantic_check: bool = True,
        strict_semantic_check: bool = False,
    ) -> ToolResult:
        """执行 Generator 构建。"""
        try:
            manifest = load_manifest(problem_dir)
        except (ValidationError, OSError, ValueError) as exc:
            return ToolResult.fail(f"invalid or unreadable manifest.json: {exc}")
        effective_compiler = resolve_effective_compiler(compiler, manifest)

        resolved, err = resolve_source(
            problem_dir,
            code,
            source_path,
            default_source_path=os.path.join("files", "gen.cpp"),
        )
        if err is not None:
            return err
        assert resolved is not None

        os.makedirs(problem_dir, exist_ok=True)
        files_dir = os.path.join(problem_dir, "files")
        os.makedirs(files_dir, exist_ok=True)

        canonical_path = os.path.join(files_dir, "gen.cpp")
        try:
            with open(canonical_path, "w", encoding="utf-8") as f:
                f.write(resolved.code)
        except Exception as e:
            return ToolResult.fail(f"Failed to save code: {str(e)}")

        exe_ext = get_exe_extension()
        binary_path = os.path.join(files_dir, f"gen{exe_ext}")

        compile_source = resolved.original_source_path or canonical_path
        include_dirs = [resolved.include_dir] if resolved.include_dir else None
        compile_result = await self.build(
            compile_source, binary_path, compiler=effective_compiler, include_dirs=include_dirs
        )

        if not compile_result.success:
            return ToolResult.fail(
                f"Compilation failed: {compile_result.error}",
                source_path=compile_source,
                canonical_path=canonical_path,
                compile_log=compile_result.stderr,
            )

        binary_size = os.path.getsize(binary_path) if os.path.exists(binary_path) else 0

        if enable_semantic_check:
            sample_probe = await self._probe_type34_sample_distribution(binary_path)
            semantic_check = self._check_type34_semantics(resolved.code, sample_probe=sample_probe)
        else:
            semantic_check = {"enabled": False}

        if (
            enable_semantic_check
            and strict_semantic_check
            and not semantic_check.get("passed", True)
        ):
            return ToolResult.fail(
                "Generator semantic check failed: type=3/type=4 lack substantial difference",
                semantic_check=semantic_check,
            )

        return ToolResult.ok(
            source_path=compile_source,
            canonical_path=canonical_path,
            binary_path=binary_path,
            binary_size=binary_size,
            compile_log=compile_result.stderr,
            semantic_check=semantic_check,
            message="Generator built successfully",
        )

    def _check_type34_semantics(
        self,
        code: str,
        *,
        sample_probe: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        branches3 = self._extract_type_branches(code, 3)
        branches4 = self._extract_type_branches(code, 4)
        type3_blocks = [b["body"] for b in branches3]
        type4_blocks = [b["body"] for b in branches4]
        type3_lines = [[b["start_line"], b["end_line"]] for b in branches3]
        type4_lines = [[b["start_line"], b["end_line"]] for b in branches4]

        has_type3 = bool(type3_blocks)
        has_type4 = bool(type4_blocks)
        if not has_type3 or not has_type4:
            res: dict[str, Any] = {
                "enabled": True,
                "passed": True,
                "advisory": True,
                "severity": "info",
                "reason": "semantic check could not reliably detect both type=3/type=4 branches",
                "hint": "请人工确认 type=3/type=4 分支存在且有实质差异",
                "type3_lines": type3_lines,
                "type4_lines": type4_lines,
                "trigger_reasons": [],
            }
            if sample_probe is not None:
                res["sample_probe"] = sample_probe
            return res

        norm3 = re.sub(r"\s+", "", " ".join(type3_blocks))
        norm4 = re.sub(r"\s+", "", " ".join(type4_blocks))
        identical_body = bool(norm3 and norm3 == norm4)
        body_similarity = (
            round(SequenceMatcher(None, norm3, norm4).ratio(), 3)
            if (norm3 and norm4)
            else 0.0
        )

        type3_signals = self._extract_branch_signals(" ".join(type3_blocks))
        type4_signals = self._extract_branch_signals(" ".join(type4_blocks))
        shared_signals = type3_signals.intersection(type4_signals)
        signal_overlap = (
            len(shared_signals) / max(len(type3_signals.union(type4_signals)), 1)
            if (type3_signals or type4_signals)
            else 1.0
        )

        probe_executed = bool(sample_probe and sample_probe.get("executed"))
        runtime_distinct = bool(probe_executed and sample_probe and sample_probe.get("runtime_distinct"))
        runtime_identical = bool(probe_executed and sample_probe and sample_probe.get("runtime_identical"))

        trigger_reasons: list[str] = []
        if identical_body:
            trigger_reasons.append(
                f"identical branch body between type=3 (lines {type3_lines}) and type=4 (lines {type4_lines})"
            )
        elif body_similarity >= 0.88:
            trigger_reasons.append(
                f"high lexical similarity (body_similarity={body_similarity:.3f}) between "
                f"type=3 (lines {type3_lines}) and type=4 (lines {type4_lines})"
            )
        if signal_overlap >= 0.75:
            trigger_reasons.append(f"high identifier signal_overlap={signal_overlap:.3f}")
        if runtime_identical and sample_probe is not None:
            trigger_reasons.append(
                "runtime sample probe produced identical outputs for type=3 and type=4 "
                f"(same_seed_match_ratio={sample_probe.get('same_seed_match_ratio')})"
            )

        low_signal_overlap = signal_overlap < 0.35
        static_similar = identical_body or (body_similarity >= 0.88 and signal_overlap >= 0.75)

        passed = True
        severity = "ok"
        advisory = False
        reason = ""

        if identical_body and not runtime_distinct:
            passed = False
            severity = "error"
            reason = (
                f"type=3 (lines {type3_lines}) and type=4 (lines {type4_lines}) have identical branch bodies"
            )
        elif static_similar:
            if low_signal_overlap or runtime_distinct:
                # 信号重叠明显偏低或实测样本分布已明显不同：降级为 warning 而非硬拦截
                passed = True
                severity = "warning"
                advisory = True
                reason = (
                    "static branch text looks similar, downgraded to warning because "
                    + (
                        f"signal_overlap={signal_overlap:.3f} < 0.35"
                        if low_signal_overlap
                        else "runtime type=3/type=4 sample distributions are distinct"
                    )
                )
            else:
                passed = False
                severity = "error"
                reason = (
                    f"type=3 (lines {type3_lines}) and type=4 (lines {type4_lines}) "
                    f"branch logic is too similar (body_similarity={body_similarity:.3f}, "
                    f"signal_overlap={signal_overlap:.3f})"
                )
        elif runtime_identical and signal_overlap >= 0.5:
            passed = False
            severity = "error"
            reason = (
                "runtime probe showed type=3 and type=4 generated identical samples across seeds "
                f"(signal_overlap={signal_overlap:.3f}, lines type3={type3_lines}, type4={type4_lines})"
            )
        elif runtime_identical:
            passed = True
            severity = "warning"
            advisory = True
            reason = (
                "runtime probe produced identical small-scale samples despite distinct branch code "
                f"(signal_overlap={signal_overlap:.3f}); verify type=4 divergence on target scales"
            )

        overlap_advisory = signal_overlap > 0.9 and passed
        if overlap_advisory and severity == "ok":
            severity = "warning"
            advisory = True

        out: dict[str, Any] = {
            "enabled": True,
            "passed": passed,
            "advisory": advisory,
            "severity": severity,
            "reason": reason,
            "hint": "为 type=4 增加针对性卡法，而不仅是 n_max/t_max 取最大值",
            "body_similarity": body_similarity,
            "signal_overlap": round(signal_overlap, 3),
            "signal_overlap_advisory": overlap_advisory,
            "type3_lines": type3_lines,
            "type4_lines": type4_lines,
            "trigger_reasons": trigger_reasons,
            "type3_signals": sorted(type3_signals)[:20],
            "type4_signals": sorted(type4_signals)[:20],
        }
        if sample_probe is not None:
            out["sample_probe"] = sample_probe
        return out

    async def _probe_type34_sample_distribution(self, binary_path: str) -> dict[str, Any]:
        """运行已编译的生成器对 type=3 与 type=4 采样对比实际输出分布特征。"""
        if not os.path.isfile(binary_path):
            return {"executed": False, "reason": "generator binary missing"}

        seeds = (1, 2, 3, 4)
        scale_candidates = (("5", "15"), ("1", "5"))
        selected_scale: tuple[str, str] | None = None
        type3_outputs: dict[int, str] = {}
        type4_outputs: dict[int, str] = {}

        for n_min, n_max in scale_candidates:
            t3: dict[int, str] = {}
            t4: dict[int, str] = {}
            for seed in seeds:
                r3 = await run_binary_with_args(
                    binary_path,
                    [str(seed), "3", n_min, n_max, "1", "1"],
                    timeout=2,
                )
                if r3.success and (r3.stdout or "").strip():
                    t3[seed] = r3.stdout
                r4 = await run_binary_with_args(
                    binary_path,
                    [str(seed), "4", n_min, n_max, "1", "1"],
                    timeout=2,
                )
                if r4.success and (r4.stdout or "").strip():
                    t4[seed] = r4.stdout
            if t3 and t4:
                type3_outputs = t3
                type4_outputs = t4
                selected_scale = (n_min, n_max)
                break

        if not type3_outputs or not type4_outputs or selected_scale is None:
            return {
                "executed": False,
                "reason": "generator did not produce valid probe outputs for both type=3 and type=4",
            }

        common_seeds = sorted(set(type3_outputs) & set(type4_outputs))
        same_seed_matches = sum(
            1 for s in common_seeds if type3_outputs[s].strip() == type4_outputs[s].strip()
        )
        same_seed_match_ratio = (
            round(same_seed_matches / len(common_seeds), 3) if common_seeds else 0.0
        )

        hashes3 = {
            hashlib.md5(out.strip().encode("utf-8", errors="replace")).hexdigest()
            for out in type3_outputs.values()
        }
        hashes4 = {
            hashlib.md5(out.strip().encode("utf-8", errors="replace")).hexdigest()
            for out in type4_outputs.values()
        }
        output_overlap_ratio = round(
            len(hashes3 & hashes4) / max(1, min(len(hashes3), len(hashes4))), 3
        )

        feat3 = self._summarize_sample_features(list(type3_outputs.values()))
        feat4 = self._summarize_sample_features(list(type4_outputs.values()))

        runtime_identical = (
            (bool(common_seeds) and same_seed_match_ratio >= 0.75)
            or output_overlap_ratio >= 0.75
        )
        runtime_distinct = (
            bool(common_seeds)
            and same_seed_match_ratio == 0.0
            and output_overlap_ratio < 0.25
        )

        return {
            "executed": True,
            "scale": {"n_min": int(selected_scale[0]), "n_max": int(selected_scale[1])},
            "comparable_seeds": len(common_seeds),
            "same_seed_match_ratio": same_seed_match_ratio,
            "output_overlap_ratio": output_overlap_ratio,
            "type3_features": feat3,
            "type4_features": feat4,
            "runtime_distinct": runtime_distinct,
            "runtime_identical": runtime_identical,
        }

    @staticmethod
    def _summarize_sample_features(outputs: list[str]) -> dict[str, Any]:
        byte_lens = [len(o.encode("utf-8", errors="replace")) for o in outputs]
        line_counts = [len([ln for ln in o.splitlines() if ln.strip()]) for o in outputs]
        token_counts: list[int] = []
        distinct_ratios: list[float] = []
        for out in outputs:
            tokens = out.split()
            token_counts.append(len(tokens))
            if tokens:
                distinct_ratios.append(len(set(tokens)) / len(tokens))
        return {
            "sample_count": len(outputs),
            "avg_bytes": round(sum(byte_lens) / max(1, len(byte_lens)), 1),
            "avg_lines": round(sum(line_counts) / max(1, len(line_counts)), 1),
            "avg_tokens": round(sum(token_counts) / max(1, len(token_counts)), 1),
            "avg_distinct_token_ratio": round(
                sum(distinct_ratios) / max(1, len(distinct_ratios)), 3
            ),
        }

    @staticmethod
    def _skip_ws_and_comments(code: str, pos: int) -> int:
        n = len(code)
        while pos < n:
            ch = code[pos]
            if ch.isspace():
                pos += 1
            elif ch == "/" and pos + 1 < n and code[pos + 1] == "/":
                nl = code.find("\n", pos + 2)
                pos = n if nl == -1 else nl + 1
            elif ch == "/" and pos + 1 < n and code[pos + 1] == "*":
                end = code.find("*/", pos + 2)
                pos = n if end == -1 else end + 2
            else:
                break
        return pos

    @staticmethod
    def _find_matching_delimiter(code: str, open_pos: int, open_ch: str, close_ch: str) -> int:
        """Scan forward from ``open_pos`` (at ``open_ch``) to the index after its matching ``close_ch``."""
        n = len(code)
        depth = 0
        i = open_pos
        in_str = False
        in_char = False
        in_line = False
        in_block = False
        while i < n:
            ch = code[i]
            nxt = code[i + 1] if i + 1 < n else ""
            if in_line:
                if ch == "\n":
                    in_line = False
                i += 1
                continue
            if in_block:
                if ch == "*" and nxt == "/":
                    in_block = False
                    i += 2
                else:
                    i += 1
                continue
            if in_str:
                if ch == "\\" and i + 1 < n:
                    i += 2
                else:
                    if ch == '"':
                        in_str = False
                    i += 1
                continue
            if in_char:
                if ch == "\\" and i + 1 < n:
                    i += 2
                else:
                    if ch == "'":
                        in_char = False
                    i += 1
                continue
            if ch == "/" and nxt == "/":
                in_line = True
                i += 2
                continue
            if ch == "/" and nxt == "*":
                in_block = True
                i += 2
                continue
            if ch == '"':
                in_str = True
                i += 1
                continue
            if ch == "'":
                in_char = True
                i += 1
                continue
            if ch == open_ch:
                depth += 1
            elif ch == close_ch:
                depth -= 1
                if depth == 0:
                    return i + 1
            i += 1
        return n

    def _extract_type_branches(self, code: str, type_value: int) -> list[dict[str, Any]]:
        """提取指定 type 分支的完整代码块与起止行号（避免固定字符截断导致误判）。"""
        patterns = [
            ("if", rf"type\s*==\s*{type_value}\b"),
            ("if", rf"\b{type_value}\s*==\s*type\b"),
            ("case", rf"\bcase\s+{type_value}\s*:"),
        ]
        branches: list[dict[str, Any]] = []
        seen_spans: set[tuple[int, int]] = set()
        n = len(code)

        for kind, pattern in patterns:
            for match in re.finditer(pattern, code):
                start_line = code.count("\n", 0, match.start()) + 1
                if kind == "case":
                    body_start = match.end()
                    # Scan until break;, next top-level case/default, or closing brace of switch
                    depth = 0
                    i = body_start
                    in_str = in_char = in_line = in_block = False
                    body_end = n
                    while i < n:
                        ch = code[i]
                        nxt = code[i + 1] if i + 1 < n else ""
                        if in_line:
                            if ch == "\n":
                                in_line = False
                            i += 1
                            continue
                        if in_block:
                            if ch == "*" and nxt == "/":
                                in_block = False
                                i += 2
                            else:
                                i += 1
                            continue
                        if in_str:
                            if ch == "\\" and i + 1 < n:
                                i += 2
                            else:
                                if ch == '"':
                                    in_str = False
                                i += 1
                            continue
                        if in_char:
                            if ch == "\\" and i + 1 < n:
                                i += 2
                            else:
                                if ch == "'":
                                    in_char = False
                                i += 1
                            continue
                        if ch == "/" and nxt == "/":
                            in_line = True
                            i += 2
                            continue
                        if ch == "/" and nxt == "*":
                            in_block = True
                            i += 2
                            continue
                        if ch == '"':
                            in_str = True
                            i += 1
                            continue
                        if ch == "'":
                            in_char = True
                            i += 1
                            continue
                        if ch == "{":
                            depth += 1
                        elif ch == "}":
                            if depth == 0:
                                body_end = i
                                break
                            depth -= 1
                        elif depth == 0:
                            tail = code[i:]
                            if re.match(r"\b(?:case\s+\d+\s*:|default\s*:)", tail):
                                body_end = i
                                break
                            break_m = re.match(r"\bbreak\s*;", tail)
                            if break_m:
                                body_end = i + break_m.end()
                                break
                        i += 1
                else:
                    # Find closing ')' of enclosing if(...) condition
                    paren_open = code.rfind("(", max(0, match.start() - 120), match.start())
                    if paren_open != -1:
                        after_cond = self._find_matching_delimiter(code, paren_open, "(", ")")
                    else:
                        after_cond = match.end()
                    body_start = self._skip_ws_and_comments(code, after_cond)
                    if body_start < n and code[body_start] == "{":
                        block_end = self._find_matching_delimiter(code, body_start, "{", "}")
                        body_start += 1
                        body_end = max(body_start, block_end - 1)
                    else:
                        semi = code.find(";", body_start)
                        body_end = (semi + 1) if semi != -1 else min(n, body_start + 240)

                span = (body_start, body_end)
                if span in seen_spans:
                    continue
                seen_spans.add(span)
                end_line = code.count("\n", 0, max(body_start, body_end - 1)) + 1
                branches.append(
                    {
                        "body": code[body_start:body_end].strip(),
                        "start_line": start_line,
                        "end_line": max(start_line, end_line),
                    }
                )
        return branches

    def _extract_type_branch_snippets(self, code: str, type_value: int) -> list[str]:
        return [b["body"] for b in self._extract_type_branches(code, type_value)]

    def _extract_branch_signals(self, snippet: str) -> set[str]:
        """提取分支内结构信号，用于判断 type=3/type=4 是否只有参数放大差异。"""
        tokens = set(re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", snippet))
        stop_words = {
            "if", "else", "case", "switch", "for", "while", "return", "int", "long", "double",
            "seed", "type", "n_min", "n_max", "t_min", "t_max", "std", "cout", "endl", "break",
        }
        return {t for t in tokens if t not in stop_words and len(t) > 2}


class GeneratorRunTool(Tool):
    """运行多策略数据生成器。"""

    @property
    def name(self) -> str:
        return "generator_run"

    @property
    def description(self) -> str:
        return """运行多策略数据生成器。

        基于论文 Algorithm 2 实现三种策略:
        - tiny: 小数据穷举 (G1)
        - random: 随机数据 (G2)
        - extreme: 极端数据 (溢出、精度、hash碰撞)
        - tle: TLE 诱导数据 (G3)

        自动通过 Validator 过滤无效输入。
        支持去重、平衡、采样。

        前置条件：
        1. 已运行 generator_build 构建生成器

        建议下一步：
        - 运行 stress_test_run 验证解法正确性
        - 运行 problem_generate_tests 生成最终测试数据
        """

    @property
    def input_schema(self) -> dict:
        return input_schema_from_model(GeneratorRunInput)

    async def execute(
        self,
        problem_dir: str,
        strategies: list[str],
        test_count: int = 20,
        validator_path: str | None = None,
        seed_start: int = 1,
        n_min: int = 1,
        n_max: int = 100000,
        t_min: int = 1,
        t_max: int = 1,
        extra_args: list[str] | None = None,
    ) -> ToolResult:
        """执行数据生成。"""
        exe_ext = get_exe_extension()
        extra_args = extra_args or []

        # 检查 generator - 优先查找 files/ 子目录
        gen_exe = os.path.join(problem_dir, "files", f"gen{exe_ext}")
        if not os.path.exists(gen_exe):
            gen_exe = os.path.join(problem_dir, f"gen{exe_ext}")

        if not os.path.exists(gen_exe):
            return ToolResult.fail("Generator not found. Run generator_build first.")

        # 检查 validator
        val_exe = validator_path
        if val_exe and not os.path.exists(val_exe):
            val_exe = None

        generated_inputs = []
        signatures = set()  # 用于去重
        generator_failures: list[dict[str, object]] = []

        # 策略映射到 type 参数
        strategy_type_map = {
            "tiny": "1",
            "random": "2",
            "extreme": "3",
            "tle": "4",
        }

        seed = seed_start
        attempts = 0
        max_attempts = test_count * 10  # 最多尝试 10 倍

        while len(generated_inputs) < test_count and attempts < max_attempts:
            attempts += 1

            # 选择策略
            strategy = strategies[(attempts - 1) % len(strategies)]
            type_param = strategy_type_map.get(strategy, "2")

            # 运行 generator
            # gen.exe <seed> <type> <n_min> <n_max> <t_min> <t_max> [extra_args...]
            cmd_args = [str(seed), type_param, str(n_min), str(n_max), str(t_min), str(t_max)] + extra_args

            gen_result = await run_binary_with_args(
                gen_exe,
                cmd_args,
                timeout=10,
            )

            if not gen_result.success:
                generator_failures.append(
                    {
                        "seed": seed,
                        "strategy": strategy,
                        "return_code": gen_result.return_code,
                        "stderr": (gen_result.stderr or "")[:200],
                    }
                )
                seed += 1
                continue

            input_data = gen_result.stdout
            if not input_data or not input_data.strip():
                generator_failures.append(
                    {
                        "seed": seed,
                        "strategy": strategy,
                        "return_code": gen_result.return_code,
                        "stderr": (gen_result.stderr or "")[:200],
                        "reason": "empty_stdout",
                    }
                )
                seed += 1
                continue

            # 计算 signature 用于去重
            sig = hashlib.md5(input_data.encode()).hexdigest()
            if sig in signatures:
                continue
            signatures.add(sig)

            # 使用 validator 过滤
            if val_exe:
                val_result = await run_binary(val_exe, input_data, timeout=5)
                if val_result.return_code != 0:
                    continue

            generated_inputs.append(
                {
                    "input": input_data,
                    "strategy": strategy,
                    "seed": seed,
                }
            )
            seed += 1

        return ToolResult.ok(
            generated_count=len(generated_inputs),
            test_count=test_count,
            inputs=generated_inputs[:test_count],
            strategies_used=strategies,
            generator_failures=generator_failures[-20:],
            message=f"Generated {len(generated_inputs)} test inputs",
        )
