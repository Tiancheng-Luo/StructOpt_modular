def write_xyz(fileobj, atoms, data=0, append=True):
    """Function to write xyz file with some data. Adapted from ase.io.xyz"""
    
    if isinstance(fileobj, str) and append:
        fileobj = open(fileobj, 'a')
    else:
        fileobj = open(fileobj, 'w')

    symbols = atoms.get_chemical_symbols()
    natoms = len(symbols)

    fileobj.write('{}\n'.format(natoms))
    fileobj.write('{}\n'.format(str(data)))
    for s, (x, y, z) in zip(symbols, atoms.get_positions()):
        fileobj.write('%-2s %22.15f %22.15f %22.15f\n' % (s, x, y, z))

    return