import importlib
import numpy as np
from collections import Counter

import structopt
from ..individual import Individual
from .crossovers import Crossovers
from .predators import Predators
from .selections import Selections
from .fitnesses import Fitnesses
from .relaxations import Relaxations
from .mutations import Mutations
from .pso_moves import Pso_Moves
from structopt.tools import root, single_core, parallel, allgather

POPULATION_MODULES = ['crossovers', 'selections', 'predators', 'fitnesses', 'relaxations', 'mutations', 'pso_moves']

class Population(list):
    """A list-like class that contains the Individuals and the operations to be run on them."""

    @single_core
    def __init__(self, parameters, individuals=None):

        self.parameters = parameters
        self.structure_type = self.parameters.structure_type.lower()
        self.load_modules()
        self.generation = 0

        if individuals is None:
            # Import the structure type class: e.g from structopt.crystal import Crystal
            # Unfortunately 'from' doesn't seem to work implicitly
            # so a getattr on the module is needed
            module = importlib.import_module('structopt.{}'.format(self.structure_type))
            Structure = getattr(module, self.structure_type.title())

            # Generate/load initial structures
            starting_index = 0
            for generator in self.parameters.generators:
                n = self.parameters.generators[generator].number_of_individuals
                for j in range(n):
                    kwargs = self.parameters.generators[generator].kwargs

                    # For the read_xyz, the input is a list of filenames. These need to be
                    # passed as arguments one by one instead of all at once
                    if generator == 'read_xyz':
                        kwargs = {'filename': kwargs[j]}

                    generator_parameters = {generator: kwargs}

                    structure = Structure(index=starting_index + j,
                                          relaxation_parameters=self.parameters.relaxations,
                                          fitness_parameters=self.parameters.fitnesses,
                                          mutation_parameters=self.parameters.mutations,
                                          pso_moves_parameters=self.parameters.pso_moves,
                                          generator_parameters=generator_parameters)
                    self.append(structure)
                starting_index += n
        else:
            self.extend(individuals)

        self.initial_number_of_individuals = len(self)


    def __getstate__(self):
        # Copy the object's state from self.__dict__ which contains
        # all our instance attributes. Always use the dict.copy()
        # method to avoid modifying the original state.
        state = self.__dict__.copy()
        # Remove the unpicklable entries.
        for name in ['crossovers', 'predators', 'selections', 'fitnesses', 'relaxations', 'mutations', 'pso_moves']:
             if name in state:
                del state[name]
        return state


    def __setstate__(self, other):
        self.__dict__.update(other)
        self.load_modules()


    def load_modules(self):
        importlib.import_module('structopt.{}'.format(self.structure_type))
        for module in self.parameters:
            if module in POPULATION_MODULES and self.parameters[module] is not None:
                Module = globals()[module.title()](getattr(self.parameters, module))
                setattr(self, module, Module)


    @parallel
    def allgather(self, individuals_per_core):
        """Performs an MPI.allgather on self (the population) and updates the
        correct individuals that have been modified based on the inputs from
        individuals_per_core.

        See stuctopt.tools.parallel.allgather for a similar function.
        """
        correct_population = allgather(self, individuals_per_core)
        self.replace(correct_population)


    @single_core
    def append(self, individual):
        """Does a standard list append and assigns an index to the individual if it doesn't already have one."""
        assert isinstance(individual, Individual)
        # Rudimentary implementation of MEX (minimum excluded value) to assign unique
        # index values to the new individuals
        indexes = sorted([_individual.index for _individual in self])
        excluded = [i for i in range(len(indexes)+1) if i not in indexes]
        assert individual.index not in indexes
        if individual.index is None:
            individual.index = excluded[0]
        super().append(individual)


    @single_core
    def replace(self, a_list):
        """Deletes the current list of individuals and replaces them with the ones in a_list."""
        counter = Counter(individual.index for individual in self)
        assert max(counter.values()) == 1
        counter = Counter(individual.index for individual in a_list)
        assert max(counter.values()) == 1

        self.clear()
        self.extend(a_list)


    @single_core
    def extend(self, other):
        """Does a standard list extend and assigns an index to each individual if it doesn't already have one."""
        # Rudimentary implementation of MEX (minimum excluded value) to assign unique
        # index values to the new individuals
        indexes = sorted([individual.index for individual in self])
        excluded = [i for i in range(len(indexes)+len(other)) if i not in indexes]
        for i, individual in enumerate(other):
            assert individual.index is None or individual.index not in indexes
            individual.index = individual.index or excluded[i]
        super().extend(other)

        counter = Counter(individual.index for individual in self)
        assert max(counter.values()) == 1


    @root
    def crossover(self, pairs):
        """Perform crossovers on the population."""
        children = self.crossovers.crossover(pairs)
        return children


    @root
    def mutate(self):
        """Perform mutations on the population."""
        self.mutations.mutate(self)
        return self


    @root
    def run_pso_moves(self, best_swarm, best_particles):
        """Perform PSO moves on the population."""
        self.pso_moves.move(self, best_swarm, best_particles)
        return self


    @parallel
    def fitness(self):
        """Perform the fitness evaluations on the entire population."""

        fits = self.fitnesses.fitness(self)

        # Store the individuals total fitness for each individual
        for i, individual in enumerate(self):
            individual._fitness = fits[i]

        # Set each individual to unmodified so that the fitnesses wont't be recalculated
        for individual in self:
            individual._fitted = True

        return fits


    @parallel
    def relax(self):
        """Relax the entire population."""
        self.relaxations.relax(self)


    @root
    def kill(self, fits):
        """Remove individuals from the population whose fingerprints are very similar.
        The goal of this selection-like scheme is to encourage diversity in the population.

        Args:
            fits (list<float>): the fitnesses of each individual in the population
        """
        self.predators.select_predator()
        self.predators.kill(self, fits, nkeep=self.initial_number_of_individuals)
        return self


    @root
    def select(self, fits):
        """Select the individuals in the population to perform crossovers on.

        Args:
            fits (list<float>): the fitnesses of each individual in the population
        """
        self.selections.select_selection()
        pairs = self.selections.select(self, fits)
        return pairs

