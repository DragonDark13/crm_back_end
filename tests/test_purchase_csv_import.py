import unittest
from datetime import datetime
from decimal import Decimal

from import_data_func.add_new_Product import _parse_purchase_row


class PurchaseCsvRowParsingTests(unittest.TestCase):
    def test_parses_ukrainian_columns_decimal_comma_and_multiple_categories(self):
        purchase = _parse_purchase_row({
            "Найменування": "Кільце Всевладдя",
            "Постачальник": "",
            "Кількість": "5",
            "Вартість за кількість": "123,51",
            "Вартість за 1 шт": "24,702",
            "Дата закупівлі": "15.06.2023",
            "Категорія": "Володар перснів (Толкін); Аксесуари",
            "Одиниця виміру": "шт",
            "Опис товару": "Тестовий опис",
        }, 2)

        self.assertEqual(purchase["total_price"], Decimal("123.51"))
        self.assertEqual(purchase["price_per_item"], Decimal("24.702"))
        self.assertEqual(purchase["purchase_date"].isoformat(), "2023-06-15")
        self.assertEqual(purchase["categories"], ["Володар перснів (Толкін)", "Аксесуари"])
        self.assertIsNone(purchase["supplier_name"])
        self.assertEqual(purchase["unit_of_measure"], "шт")

    def test_calculates_missing_total_from_quantity_and_unit_price(self):
        purchase = _parse_purchase_row({
            "Найменування": "Кулон Часоворот",
            "Постачальник": "",
            "Кількість": "3",
            "Вартість за кількість": "",
            "Вартість за 1 шт": "119",
            "Дата закупівлі": "15.01.2025",
            "Категорія": "Гаррі Поттер",
            "Одиниця виміру": "",
            "Опис товару": "",
        }, 3)

        self.assertEqual(purchase["total_price"], Decimal("357"))
        self.assertEqual(purchase["price_per_item"], Decimal("119"))

    def test_legacy_format_uses_passed_purchase_date(self):
        purchase = _parse_purchase_row({
            "Наименование": "Legacy product",
            "Поставщик": "Supplier",
            "Количество": "2",
            "Стоимость за количество": "50",
            "Стоимость за 1 шт": "25",
        }, 2, datetime(2023, 9, 15))

        self.assertEqual(purchase["purchase_date"].isoformat(), "2023-09-15")

    def test_uses_zero_when_both_prices_are_unknown(self):
        purchase = _parse_purchase_row({
            "Найменування": "Без відомої ціни",
            "Кількість": "1",
            "Вартість за кількість": "",
            "Вартість за 1 шт": "",
            "Дата закупівлі": "15.01.2025",
        }, 2)

        self.assertEqual(purchase["total_price"], Decimal("0"))
        self.assertEqual(purchase["price_per_item"], Decimal("0"))


if __name__ == "__main__":
    unittest.main()
