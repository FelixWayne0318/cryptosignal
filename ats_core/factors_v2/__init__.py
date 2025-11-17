# coding: utf-8
"""
统一因子系统 v7.4.0 - 四步分层决策系统

v7.4.0核心架构：
- Step1方向确认因子: I独立性（市场对齐veto）
- Step2时机判断因子: F资金流向（Enhanced F v2）
- Step3风险管理: Entry/SL/TP价格计算
- Step4质量控制: 四道闸门过滤

factors_v2模块保留：
- B因子（基差+资金费，市场情绪）
- I因子（独立性，Step1核心veto机制）
"""

from .basis_funding import score_basis_funding
from .independence import calculate_independence

__all__ = [
    'score_basis_funding',
    'calculate_independence',
]
