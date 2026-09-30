import unittest
import numpy as np
from entropy import calculate_shannon_entropy, text_to_timeseries, calculate_hydrodynamic_entropy

class TestEntropy(unittest.TestCase):
    
    def test_shannon_constant(self):
        # H("aaaaa") should be 0
        self.assertAlmostEqual(calculate_shannon_entropy("aaaaa"), 0.0)
        
    def test_shannon_random_equal(self):
        # H("abcd") should be 2.0 (4 symbols, prob 0.25 each -> -sum(0.25 * -2) = 2)
        self.assertAlmostEqual(calculate_shannon_entropy("abcd"), 2.0)
        
    def test_hydro_constant(self):
        # Constant signal -> Single DC peak -> p=[1, 0, 0...] -> H=0
        text = "aaaaa"
        # frequencies -> [5, 5, 5, 5, 5]
        # ascii -> [97, 97, 97, 97, 97]
        # Both represent constant signals
        ts = text_to_timeseries(text, method='frequency')
        h = calculate_hydrodynamic_entropy(ts)
        self.assertAlmostEqual(h, 0.0)
        
        ts_ascii = text_to_timeseries(text, method='ascii')
        h_ascii = calculate_hydrodynamic_entropy(ts_ascii)
        self.assertAlmostEqual(h_ascii, 0.0)

    def test_hydro_periodic(self):
        # "abab" -> [1, 2, 1, 2]? No, wait. 
        # text: "abab"
        # frequency: 'a':2, 'b':2 -> [2, 2, 2, 2] (CONSTANT!) -> Entropy 0
        # ascii: [97, 98, 97, 98] -> Periodic. Should have low entropy but > 0
        
        text = "abab"
        ts_freq = text_to_timeseries(text, method='frequency')
        # [2, 2, 2, 2] is constant
        self.assertAlmostEqual(calculate_hydrodynamic_entropy(ts_freq), 0.0)
        
        ts_ascii = text_to_timeseries(text, method='ascii')
        # [97, 98, 97, 98]
        # FFT has DC and Nyquist component.
        # Signal: 97.5 +/- 0.5 * (-1)^n
        # Spectrum will have 2 spikes. p=[0.5, 0?, 0.5, 0?] roughly (depends on N).
        # Actually for N=4, [97, 98, 97, 98]
        # FFT: [390, -1-1j?, 0, -1+1j?] -> let's not calc manually, just assert > 0
        h_ascii = calculate_hydrodynamic_entropy(ts_ascii)
        self.assertTrue(h_ascii > 0.0)
        # Should be low (ordered)
        
    def test_methods_impl(self):
        text = "banana"
        # 'b':1, 'a':3, 'n':2
        # b, a, n, a, n, a
        # 1, 3, 2, 3, 2, 3
        expected_freq = np.array([1, 3, 2, 3, 2, 3])
        np.testing.assert_array_equal(text_to_timeseries(text, method='frequency'), expected_freq)
        
        expected_ascii = np.array([ord(c) for c in text])
        np.testing.assert_array_equal(text_to_timeseries(text, method='ascii'), expected_ascii)

if __name__ == '__main__':
    unittest.main()
