import json
import random
import numpy as np
from ase import Atom, Atoms
from ase.visualize import view
from ase.data import atomic_numbers, reference_states

from structopt.tools import random_three_vector
from structopt.common.crossmodule import get_particle_radius

def sphere(atomlist, cell, fill_factor=0.74, radius=None):
    """Generates a random sphere of particles given an
    atomlist and radius.

    Parameters
    ----------
    atomlist : list
        A list of [sym, n] pairs where sym is the chemical symbol
        and n is the number of of sym's to include in the individual
    cell : list
        The x, y, and z dimensions of the cell which holds the particle.
    fill_factor : float
        How densely packed the sphere should be. Ranges from 0 to 1.
    radius : float
        The radius of the sphere. If None, estimated from the
        atomic radii
    """

    if radius is None:
        radius = get_particle_radius(atomlist, fill_factor)

    # Create a list of random order of the atoms
    chemical_symbols = []
    for atom in atomlist:
        chemical_symbols += [atom[0]] * atom[1]

    random.shuffle(chemical_symbols)

    unit_vec = np.array([random_three_vector() for i in range(len(chemical_symbols))])
    D = radius * np.random.sample(size=len(chemical_symbols)) ** (1.0/3.0)
    positions = np.array([D]).T * unit_vec

    indiv = Atoms(symbols=chemical_symbols, positions=positions)

    if cell is not None:
        indiv.set_cell(cell)
        cell_center = np.sum(indiv.get_cell(), axis=1) / 2.0
        indiv.translate(indiv.get_center_of_mass() + cell_center)
        indiv.set_pbc(True)

    return indiv
