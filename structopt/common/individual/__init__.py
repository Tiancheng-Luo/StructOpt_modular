import logging
import random
import ase
from importlib import import_module
import numpy as np

import structopt
from . import relaxations, fitnesses, mutations, fingerprinters, mutations
from structopt.tools import root, single_core, parallel


class Individual(ase.Atoms):
    """An abstract base class for a structure."""

    @single_core
    def __init__(self, index=None, **kwargs):
        """Additional class parameters that extend ASE.Atoms:
            index
            _kwargs
            _modified

            fitnesses
            relaxations
            mutations

        Methods:
            fitness
            relax
            mutate
            copy
            get_nearest_atom_indices
            get_atom_indices_within_distance_of_atom
        """
        self._kwargs = kwargs  # Store the parameters necessary for initializing for making a copy of self
        self.index = index
        self._modified = True
        self._fitness = None

        cls_name = self.__class__.__name__.lower()
        # Load in the appropriate functionality
        fitnesses = import_module('structopt.{}.individual.fitnesses'.format(cls_name))
        mutations = import_module('structopt.{}.individual.mutations'.format(cls_name))
        relaxations = import_module('structopt.{}.individual.relaxations'.format(cls_name))

        self.fitnesses = fitnesses.Fitnesses()
        self.mutations = mutations.Mutations()
        self.relaxations = relaxations.Relaxations()

        # Initialize the ase.Atoms structure
        super().__init__()
        generators = import_module('structopt.{}.individual.generators'.format(cls_name))
        generators.generate(self, **kwargs)


    def __getstate__(self):
        # Copy the object's state from self.__dict__ which contains
        # all our instance attributes. Always use the dict.copy()
        # method to avoid modifying the original state.
        state = self.__dict__.copy()
        # Remove the unpicklable entries.
        del state['fitnesses']
        del state['relaxations']
        del state['mutations']
        del state['_calc']
        del state['_kwargs']
        return state


    @parallel
    def mutate(self):
        """Mutate an individual.

        Args:
            individual (Individual): the individual to mutate
        """
        self.mutations.select_mutation()
        self.mutations.mutate(self)
        self.mutations.post_processing()


    @parallel
    def relax(self):
        """Relax an individual.

        Args:
            individual (Individual): the individual to relax
        """
        self.relaxations.relax(self)
        self._modified = True
        self.relaxations.post_processing()


    @parallel
    def fitness(self):
        """Perform the fitness calculations on an individual.

        Args:
            individual (Individual): the individual to evaluate
        """
        fits = self.fitnesses.fitness(self)
        self.fitnesses.post_processing()
        return fits


    @single_core
    def get_atom_indices_within_distance_of_atom(self, atom_index, distance):
        dists = self.get_distances(atom_index, slice(None, None, None))
        return np.where(dists < distance)

    @single_core
    def get_nearest_atom_indices(self, atom_index, count):
        dists = self.get_distances(atom_index, slice(None, None, None))[0]
        return np.argsort(dists)[:count]

    @single_core
    def copy(self):
        new = self.__class__()
        new.index = self.index  # TODO
        new.extend(self)
        return new

