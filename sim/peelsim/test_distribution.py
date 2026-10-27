import unittest
import numpy as np
from scipy.stats import norm
from distribution import discrete_ks, continuous_ks, gd_lattice

class Distances(unittest.TestCase):
    def test_displaced_atom(self):
        self.assertEqual(discrete_ks(np.array([0]),[1.],np.array([1]),[1.]),1.)
    def test_coincident_atoms(self):
        x=np.array([-3,0,3]); p=np.array([.2,.5,.3])
        self.assertEqual(discrete_ks(x,p,x,p),0.)
    def test_left_limit(self):
        self.assertAlmostEqual(discrete_ks(np.array([0,2]),[.7,.3],np.array([1,2]),[.2,.8]),.7)
    def test_continuous_atom(self):
        self.assertEqual(continuous_ks(np.array([0]),[1.],norm.cdf),.5)
    def test_two_point_law(self):
        for d in (2,3):
            x,p=gd_lattice(3,64,d)
            np.testing.assert_array_equal(x[p>0],[-3,3])
            np.testing.assert_array_equal(p[p>0],[.5,.5])
    def test_gd_moments(self):
        x,p=gd_lattice(3,16384,128); x=x*2/3
        self.assertAlmostEqual(p.sum(),1.,places=12)
        self.assertAlmostEqual(np.dot(x,p),0.,places=12)
        self.assertAlmostEqual(np.dot(x*x,p),4+2*126*125/16384,places=10)
if __name__=='__main__': unittest.main()
