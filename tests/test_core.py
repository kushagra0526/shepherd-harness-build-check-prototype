import random
import unittest
from harnesscheck.core import make_spec, build_log, check, has_click, force_curve, KINDS


def case(defects, seed=3, n=30):
    rng = random.Random(seed)
    spec = make_spec(rng, n)
    log, planted = build_log(spec, rng, defects)
    return spec, log, planted


class T(unittest.TestCase):
    def test_clean_harness_has_no_flags(self):
        for s in range(10):
            spec, log, _ = case([], seed=s)
            self.assertEqual(check(spec, log), {})

    def test_each_defect_found(self):
        for kind in KINDS:
            spec, log, planted = case([kind])
            self.assertTrue(planted, kind)
            self.assertTrue(set(check(spec, log)) >= set(planted), kind)

    def test_swap_is_one_code_on_both_rows(self):
        spec, log, planted = case(["SWAPPED_PAIR"])
        out = check(spec, log)
        self.assertEqual({out[k] for k in planted}, {"SWAPPED_PAIR"})

    def test_click_detector(self):
        rng = random.Random(1)
        self.assertTrue(has_click(force_curve(rng, True, 0.2, False)))
        self.assertFalse(has_click(force_curve(rng, False, 0.2, False)))

    def test_early_snag_is_not_a_click(self):
        rng = random.Random(2)
        self.assertFalse(has_click(force_curve(rng, False, 0.2, True)))


if __name__ == "__main__":
    unittest.main()
