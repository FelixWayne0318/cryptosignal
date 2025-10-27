# coding: utf-8
"""
时间序列交叉验证器

功能：
1. 5折时间序列交叉验证（TimeSeriesSplit）
2. 评估模型在不同时间段的稳定性
3. 检测时间依赖性过拟合
4. 生成交叉验证报告

理论基础：
时间序列交叉验证特点：
- 不能随机打乱（必须保持时间顺序）
- 使用滚动窗口（Rolling Window）或扩展窗口（Expanding Window）
- 训练集始终在测试集之前

5折示例（Expanding Window）:
Fold 1: Train[0:20]    Test[20:40]
Fold 2: Train[0:40]    Test[40:60]
Fold 3: Train[0:60]    Test[60:80]
Fold 4: Train[0:80]    Test[80:100]
Fold 5: Train[0:100]   Test[100:120]

评估指标：
- Mean Accuracy: 平均准确率
- Std Accuracy: 准确率标准差（越小越稳定）
- Mean IC: 平均IC
- IC Consistency: IC一致性（所有fold的IC同号比例）
"""

from __future__ import annotations
from typing import Dict, List, Tuple, Any, Callable, Optional
import numpy as np
from collections import defaultdict


class TimeSeriesCrossValidator:
    """时间序列交叉验证器"""

    def __init__(
        self,
        n_splits: int = 5,
        test_size: Optional[int] = None,
        expanding_window: bool = True
    ):
        """
        初始化交叉验证器

        Args:
            n_splits: 折数（默认5）
            test_size: 测试集大小（None表示自动计算）
            expanding_window: 是否使用扩展窗口（True）还是滚动窗口（False）
        """
        self.n_splits = n_splits
        self.test_size = test_size
        self.expanding_window = expanding_window

        # 存储交叉验证结果
        self.cv_results = {}

    def split(
        self,
        X: List[Any],
        y: Optional[List[Any]] = None
    ) -> List[Tuple[List[int], List[int]]]:
        """
        生成训练/测试集索引

        Args:
            X: 特征数据
            y: 标签数据（可选）

        Returns:
            [(train_indices, test_indices), ...]
        """
        n_samples = len(X)

        if n_samples < self.n_splits + 1:
            raise ValueError(f"Not enough samples ({n_samples}) for {self.n_splits} splits")

        # 计算测试集大小
        if self.test_size is None:
            # 自动计算：确保每个fold都有合理的测试集大小
            test_size = max(1, n_samples // (self.n_splits + 1))
        else:
            test_size = self.test_size

        # 生成splits
        splits = []

        for i in range(self.n_splits):
            if self.expanding_window:
                # 扩展窗口：训练集逐渐扩大
                test_start = (i + 1) * test_size
                test_end = test_start + test_size

                if test_end > n_samples:
                    break

                train_indices = list(range(0, test_start))
                test_indices = list(range(test_start, test_end))

            else:
                # 滚动窗口：训练集和测试集大小固定
                test_start = (i + 1) * test_size
                test_end = test_start + test_size

                if test_end > n_samples:
                    break

                train_start = max(0, test_start - test_size * self.n_splits)
                train_indices = list(range(train_start, test_start))
                test_indices = list(range(test_start, test_end))

            if train_indices and test_indices:
                splits.append((train_indices, test_indices))

        return splits

    def cross_validate(
        self,
        X: List[Any],
        y: List[Any],
        model_fn: Callable,
        score_fn: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        执行交叉验证

        Args:
            X: 特征数据列表
            y: 标签数据列表
            model_fn: 模型训练函数 model_fn(X_train, y_train) -> model
            score_fn: 评分函数 score_fn(model, X_test, y_test) -> score
                     默认使用分类准确率

        Returns:
            交叉验证结果字典
        """
        if score_fn is None:
            # 默认评分函数：分类准确率
            def default_score_fn(model, X_test, y_test):
                predictions = [model.predict(x) for x in X_test]
                correct = sum(1 for pred, true in zip(predictions, y_test) if pred == true)
                return correct / len(y_test)

            score_fn = default_score_fn

        # 生成splits
        splits = self.split(X, y)

        if len(splits) < 2:
            return {
                "error": "Insufficient data for cross-validation",
                "n_samples": len(X),
                "n_splits_possible": len(splits)
            }

        # 执行交叉验证
        fold_scores = []
        fold_details = []

        for fold_idx, (train_indices, test_indices) in enumerate(splits):
            # 提取训练/测试数据
            X_train = [X[i] for i in train_indices]
            y_train = [y[i] for i in train_indices]
            X_test = [X[i] for i in test_indices]
            y_test = [y[i] for i in test_indices]

            # 训练模型
            model = model_fn(X_train, y_train)

            # 评分
            score = score_fn(model, X_test, y_test)
            fold_scores.append(score)

            fold_details.append({
                "fold": fold_idx + 1,
                "train_size": len(train_indices),
                "test_size": len(test_indices),
                "score": score
            })

        # 计算统计量
        mean_score = np.mean(fold_scores)
        std_score = np.std(fold_scores)
        min_score = np.min(fold_scores)
        max_score = np.max(fold_scores)

        # 稳定性评估
        if std_score < 0.05:
            stability = "excellent"
        elif std_score < 0.10:
            stability = "good"
        elif std_score < 0.15:
            stability = "fair"
        else:
            stability = "poor"

        # 存储结果
        self.cv_results = {
            "n_splits": len(splits),
            "fold_scores": fold_scores,
            "fold_details": fold_details,
            "mean_score": mean_score,
            "std_score": std_score,
            "min_score": min_score,
            "max_score": max_score,
            "stability": stability
        }

        return self.cv_results

    def cross_validate_ic(
        self,
        factor_scores: List[Dict[str, float]],
        future_returns: List[float]
    ) -> Dict[str, Dict[str, Any]]:
        """
        对所有因子执行IC交叉验证

        Args:
            factor_scores: 因子评分列表 [{factor_name: score}, ...]
            future_returns: 未来收益列表

        Returns:
            {factor_name: cv_results, ...}
        """
        if not factor_scores or not future_returns:
            return {}

        # 获取所有因子名称
        factor_names = list(factor_scores[0].keys())

        results = {}

        for factor_name in factor_names:
            # 提取该因子的所有评分
            X = [[obs[factor_name]] for obs in factor_scores]
            y = future_returns

            # 定义简单的"模型"和评分函数（IC计算）
            def simple_model_fn(X_train, y_train):
                # 返回训练数据（用于IC计算）
                return (X_train, y_train)

            def ic_score_fn(model, X_test, y_test):
                # 计算IC（Spearman秩相关）
                X_test_flat = [x[0] for x in X_test]

                # 秩相关
                factor_ranks = self._rank(X_test_flat)
                return_ranks = self._rank(y_test)

                ic = np.corrcoef(factor_ranks, return_ranks)[0, 1]

                # 处理NaN
                if np.isnan(ic):
                    ic = 0.0

                return ic

            # 执行交叉验证
            cv_result = self.cross_validate(X, y, simple_model_fn, ic_score_fn)

            # 计算IC一致性（所有fold的IC同号比例）
            if "fold_scores" in cv_result:
                fold_ics = cv_result["fold_scores"]
                positive_ics = sum(1 for ic in fold_ics if ic > 0)
                negative_ics = sum(1 for ic in fold_ics if ic < 0)

                ic_consistency = max(positive_ics, negative_ics) / len(fold_ics)

                cv_result["ic_consistency"] = ic_consistency
                cv_result["consistent_direction"] = "positive" if positive_ics > negative_ics else "negative"

            results[factor_name] = cv_result

        return results

    def _rank(self, values: List[float]) -> List[float]:
        """计算秩"""
        sorted_indices = np.argsort(values)
        ranks = np.empty(len(values))
        ranks[sorted_indices] = np.arange(len(values))
        return ranks.tolist()

    def generate_report(self) -> str:
        """
        生成交叉验证报告

        Returns:
            Markdown格式的报告
        """
        if not self.cv_results:
            return "# Cross-Validation Report\n\n⚠️ No cross-validation results available\n"

        report = []
        report.append("# Time Series Cross-Validation Report")
        report.append("")
        report.append(f"**Method**: {'Expanding Window' if self.expanding_window else 'Rolling Window'}")
        report.append(f"**Number of Splits**: {self.cv_results['n_splits']}")
        report.append("")

        # 总体结果
        report.append("## Overall Results")
        report.append("")
        report.append(f"- **Mean Score**: {self.cv_results['mean_score']:.4f}")
        report.append(f"- **Std Score**: {self.cv_results['std_score']:.4f}")
        report.append(f"- **Min Score**: {self.cv_results['min_score']:.4f}")
        report.append(f"- **Max Score**: {self.cv_results['max_score']:.4f}")
        report.append(f"- **Stability**: {self.cv_results['stability'].upper()}")
        report.append("")

        # Fold详情
        report.append("## Fold Details")
        report.append("")
        report.append("| Fold | Train Size | Test Size | Score |")
        report.append("|------|------------|-----------|-------|")

        for fold_detail in self.cv_results["fold_details"]:
            report.append(
                f"| {fold_detail['fold']} | {fold_detail['train_size']} | "
                f"{fold_detail['test_size']} | {fold_detail['score']:.4f} |"
            )

        report.append("")

        # 稳定性评估
        stability = self.cv_results["stability"]

        if stability == "excellent":
            report.append("## ✅ Excellent Stability")
            report.append("")
            report.append("The model shows consistent performance across all folds (Std < 0.05).")
            report.append("Low risk of overfitting.")
        elif stability == "good":
            report.append("## ✅ Good Stability")
            report.append("")
            report.append("The model shows good consistency (Std < 0.10).")
        elif stability == "fair":
            report.append("## ⚠️ Fair Stability")
            report.append("")
            report.append("The model shows moderate variability (Std < 0.15).")
            report.append("Consider:")
            report.append("- Increasing training data")
            report.append("- Simplifying the model")
            report.append("- Using regularization")
        else:
            report.append("## ❌ Poor Stability")
            report.append("")
            report.append("The model shows high variability across folds (Std >= 0.15).")
            report.append("")
            report.append("⚠️ **High risk of overfitting!**")
            report.append("")
            report.append("Recommended actions:")
            report.append("1. Reduce model complexity")
            report.append("2. Increase training data")
            report.append("3. Apply stronger regularization")
            report.append("4. Re-examine feature engineering")

        report.append("")

        return "\n".join(report)

    def generate_factor_ic_report(
        self,
        factor_ic_results: Dict[str, Dict[str, Any]]
    ) -> str:
        """
        生成因子IC交叉验证报告

        Args:
            factor_ic_results: cross_validate_ic()的返回结果

        Returns:
            Markdown格式的报告
        """
        report = []
        report.append("# Factor IC Cross-Validation Report")
        report.append("")
        report.append(f"**Method**: {'Expanding Window' if self.expanding_window else 'Rolling Window'}")
        report.append(f"**Number of Splits**: {self.n_splits}")
        report.append("")

        # 汇总表格
        report.append("## Factor IC Summary")
        report.append("")
        report.append("| Factor | Mean IC | Std IC | IC Consistency | Stable |")
        report.append("|--------|---------|--------|----------------|--------|")

        for factor_name, cv_result in sorted(
            factor_ic_results.items(),
            key=lambda x: abs(x[1].get("mean_score", 0)),
            reverse=True
        ):
            if "error" in cv_result:
                continue

            mean_ic = cv_result["mean_score"]
            std_ic = cv_result["std_score"]
            ic_consistency = cv_result.get("ic_consistency", 0)

            stable = "✅" if ic_consistency >= 0.8 else ("⚠️" if ic_consistency >= 0.6 else "❌")

            report.append(
                f"| **{factor_name}** | {mean_ic:.4f} | {std_ic:.4f} | "
                f"{ic_consistency:.2f} | {stable} |"
            )

        report.append("")

        # 稳定因子
        stable_factors = [
            name for name, result in factor_ic_results.items()
            if result.get("ic_consistency", 0) >= 0.8
        ]

        if stable_factors:
            report.append("## ✅ Stable Factors (IC Consistency >= 0.8)")
            report.append("")
            for factor_name in stable_factors:
                result = factor_ic_results[factor_name]
                direction = result.get("consistent_direction", "unknown")
                report.append(f"- **{factor_name}**: Consistently {direction} (IC Consistency: {result['ic_consistency']:.2f})")
            report.append("")

        # 不稳定因子
        unstable_factors = [
            name for name, result in factor_ic_results.items()
            if result.get("ic_consistency", 1) < 0.6
        ]

        if unstable_factors:
            report.append("## ⚠️ Unstable Factors (IC Consistency < 0.6)")
            report.append("")
            report.append("These factors show inconsistent predictive power across time periods:")
            report.append("")
            for factor_name in unstable_factors:
                result = factor_ic_results[factor_name]
                report.append(f"- **{factor_name}**: IC Consistency = {result.get('ic_consistency', 0):.2f}")
            report.append("")
            report.append("💡 Consider:")
            report.append("- Removing these factors")
            report.append("- Investigating time-dependent behavior")
            report.append("- Using rolling windows or adaptive weighting")

        report.append("")

        return "\n".join(report)


# ========== 测试代码 ==========

if __name__ == "__main__":
    print("=" * 70)
    print("时间序列交叉验证器测试")
    print("=" * 70)

    # 创建验证器
    cv = TimeSeriesCrossValidator(n_splits=5, expanding_window=True)

    # 模拟数据
    np.random.seed(42)

    print("\n[模拟数据] 生成150个观测...")

    factor_scores = []
    future_returns = []

    for i in range(150):
        # 模拟未来收益
        future_return = np.random.randn() * 0.02  # ±2%
        future_returns.append(future_return)

        # 模拟因子（T有稳定预测能力，M不稳定）
        T = future_return * 10 + np.random.randn() * 20  # 稳定
        M = future_return * (5 if i < 100 else -5) + np.random.randn() * 25  # 不稳定

        factor_scores.append({"T": T, "M": M})

    # 因子IC交叉验证
    print("\n[因子IC交叉验证]")
    ic_results = cv.cross_validate_ic(factor_scores, future_returns)

    for factor_name, result in ic_results.items():
        if "error" not in result:
            print(f"\n  {factor_name}:")
            print(f"    Mean IC:       {result['mean_score']:.4f}")
            print(f"    Std IC:        {result['std_score']:.4f}")
            print(f"    IC一致性:       {result['ic_consistency']:.2f}")
            print(f"    稳定性:        {result['stability']}")

    # 生成报告
    print("\n[生成报告]")
    factor_report = cv.generate_factor_ic_report(ic_results)

    # 保存报告
    report_path = "/tmp/cross_validation_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(factor_report)

    print(f"  报告已保存到: {report_path}")

    # 显示报告
    print("\n[报告预览]")
    print("-" * 70)
    print(factor_report)

    print("\n" + "=" * 70)
    print("✅ 时间序列交叉验证器测试完成")
    print("=" * 70)
