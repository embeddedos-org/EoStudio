"""OTEngine.transform on two concurrent deletes whose ranges overlap.

Transforming a against b must give a' and b' such that applying a then b'
and applying b then a' leave the same text (the two sites converge), and
that text has every character either delete covered removed exactly once.
"""

from __future__ import annotations

import unittest

from eostudio.core.collaboration.realtime_collab import Operation, OpType, OTEngine


def _delete(position: int, length: int) -> Operation:
    return Operation(op_type=OpType.DELETE, position=position, length=length)


def _both_orders(text: str, op_a: Operation, op_b: Operation) -> tuple[str, str]:
    a2, b2 = OTEngine.transform(op_a, op_b)
    a_then_b = OTEngine.apply_to_text(OTEngine.apply_to_text(text, op_a), b2)
    b_then_a = OTEngine.apply_to_text(OTEngine.apply_to_text(text, op_b), a2)
    return a_then_b, b_then_a


class TestOverlappingDeletes(unittest.TestCase):
    def test_partial_overlap_a_first(self) -> None:
        # a deletes "bc", b deletes "cde": together "bcde" goes.
        self.assertEqual(_both_orders("abcdef", _delete(1, 2), _delete(2, 3)), ("af", "af"))

    def test_partial_overlap_b_first(self) -> None:
        self.assertEqual(_both_orders("abcdef", _delete(2, 3), _delete(1, 2)), ("af", "af"))

    def test_one_range_inside_the_other(self) -> None:
        # a deletes "bcde", b deletes "cd".
        self.assertEqual(_both_orders("abcdef", _delete(1, 4), _delete(2, 2)), ("af", "af"))
        self.assertEqual(_both_orders("abcdef", _delete(2, 2), _delete(1, 4)), ("af", "af"))

    def test_same_start_different_lengths(self) -> None:
        self.assertEqual(_both_orders("abcdef", _delete(1, 2), _delete(1, 4)), ("af", "af"))

    def test_identical_ranges(self) -> None:
        self.assertEqual(_both_orders("abcdef", _delete(1, 3), _delete(1, 3)), ("aef", "aef"))

    def test_negative_positions_use_the_applied_delete_ranges(self) -> None:
        text = "abcdef"
        for a_pos in (-3, -1, 0, 1, 3):
            for b_pos in (-3, -1, 0, 2, 5):
                if a_pos >= 0 and b_pos >= 0:
                    continue
                for a_len in (0, 1, 3):
                    for b_len in (0, 1, 3):
                        with self.subTest(a=(a_pos, a_len), b=(b_pos, b_len)):
                            a, b = _delete(a_pos, a_len), _delete(b_pos, b_len)
                            a_start, b_start = max(0, a_pos), max(0, b_pos)
                            removed = set(range(a_start, a_start + a_len)) | set(range(b_start, b_start + b_len))
                            expected = "".join(char for i, char in enumerate(text) if i not in removed)
                            self.assertEqual(_both_orders(text, a, b), (expected, expected))
                            self.assertEqual((a.position, b.position), (a_pos, b_pos))

    def test_transformed_ranges(self) -> None:
        a2, b2 = OTEngine.transform(_delete(1, 2), _delete(2, 3))
        self.assertEqual((a2.position, a2.length), (1, 1))  # "b", after "cde" is gone
        self.assertEqual((b2.position, b2.length), (1, 2))  # "de", after "bc" is gone


class TestDisjointDeletesUnchanged(unittest.TestCase):
    def test_adjacent_and_apart(self) -> None:
        self.assertEqual(_both_orders("abcdef", _delete(0, 2), _delete(2, 2)), ("ef", "ef"))
        self.assertEqual(_both_orders("abcdef", _delete(4, 2), _delete(0, 1)), ("bcd", "bcd"))


if __name__ == "__main__":
    unittest.main()
