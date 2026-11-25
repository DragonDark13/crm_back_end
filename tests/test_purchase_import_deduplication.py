import unittest
from datetime import date
from decimal import Decimal

from import_data_func.add_new_Product import (
    _filter_duplicate_purchase_rows,
    _purchase_fingerprint,
)


def purchase():
    return {
        "name": "Товар А",
        "supplier_name": "Постачальник",
        "purchase_date": date(2026, 1, 10),
        "quantity": 2,
        "total_price": Decimal("100.00"),
        "price_per_item": Decimal("50.000"),
    }


class PurchaseImportDeduplicationTests(unittest.TestCase):
    def test_skips_previously_imported_occurrences_and_keeps_new_extra_occurrence(self):
        first = purchase()
        second = purchase()
        fingerprint = _purchase_fingerprint(first)

        rows_to_import, duplicates = _filter_duplicate_purchase_rows(
            [(2, first), (3, second)],
            {fingerprint: 1},
        )

        self.assertEqual(duplicates, 1)
        self.assertEqual(len(rows_to_import), 1)
        self.assertEqual(rows_to_import[0][0], 3)
        self.assertEqual(rows_to_import[0][3], 2)

    def test_keeps_identical_rows_when_none_were_imported_before(self):
        first = purchase()
        second = purchase()

        rows_to_import, duplicates = _filter_duplicate_purchase_rows(
            [(2, first), (3, second)],
            {},
        )

        self.assertEqual(duplicates, 0)
        self.assertEqual(len(rows_to_import), 2)
        self.assertEqual(
            [row[3] for row in rows_to_import],
            [1, 2],
        )


    def test_uses_next_available_persisted_index_when_history_has_a_gap(self):
        first = purchase()
        second = purchase()
        fingerprint = _purchase_fingerprint(first)

        rows_to_import, duplicates = _filter_duplicate_purchase_rows(
            [(2, first), (3, second)],
            {fingerprint: {"count": 1, "max_index": 2}},
        )

        self.assertEqual(duplicates, 1)
        self.assertEqual(len(rows_to_import), 1)
        self.assertEqual(rows_to_import[0][3], 3)

    def test_fingerprint_normalizes_name_and_database_decimal_precision(self):
        first = purchase()
        second = purchase()
        second["name"] = "  ТОВАР А "
        second["total_price"] = Decimal("100.004")
        second["price_per_item"] = Decimal("50.0004")

        self.assertEqual(
            _purchase_fingerprint(first),
            _purchase_fingerprint(second),
        )

    def test_fingerprint_changes_when_purchase_identity_changes(self):
        first = purchase()
        second = purchase()
        second["purchase_date"] = date(2026, 1, 11)

        self.assertNotEqual(
            _purchase_fingerprint(first),
            _purchase_fingerprint(second),
        )


if __name__ == "__main__":
    unittest.main()
