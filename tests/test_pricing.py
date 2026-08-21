"""定价模块测试（无网络、无依赖）。"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.pricing.calculator import PricePlan, recommend_price
from src.pricing.cost import total_cost
from src.pricing.profit import margin, profit


class TestCost(unittest.TestCase):
    def test_total_cost(self):
        self.assertEqual(total_cost(20, 15), 35.0)
        self.assertEqual(total_cost(20, 15, 5), 40.0)


class TestProfit(unittest.TestCase):
    def test_profit_and_margin(self):
        self.assertEqual(profit(63.64, 35), 28.64)
        self.assertAlmostEqual(margin(28.64, 63.64), 0.45, places=2)
        self.assertEqual(margin(10, 0), 0.0)


class TestCalculator(unittest.TestCase):
    def test_example(self):
        # 采购 20 + 物流 15，佣金 15% + 目标利润 30% -> 35 / 0.55 ≈ 63.64
        plan = recommend_price(20, shipping=15, commission_rate=0.15, target_margin=0.30)
        self.assertIsInstance(plan, PricePlan)
        self.assertAlmostEqual(plan.sale_price, 63.64, places=2)
        self.assertEqual(plan.total_cost, 35.0)
        self.assertAlmostEqual(plan.profit, 28.64, places=2)
        self.assertAlmostEqual(plan.actual_margin, 0.45, places=2)
        self.assertEqual(plan.currency, "RMB")

    def test_commission_default(self):
        # 不传佣金，使用默认 0.15；仅成本 20，目标 0.30 -> 20 / 0.55 ≈ 36.36
        plan = recommend_price(20)
        self.assertAlmostEqual(plan.sale_price, 36.36, places=2)

    def test_denominator_guard(self):
        with self.assertRaises(ValueError):
            recommend_price(20, commission_rate=0.6, target_margin=0.5)

    def test_no_profit_below_cost(self):
        plan = recommend_price(100, commission_rate=0.0, target_margin=0.0)
        self.assertAlmostEqual(plan.sale_price, 100.0, places=2)


if __name__ == "__main__":
    unittest.main()
