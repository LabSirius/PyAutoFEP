#! /usr/bin/env python3
#
#  generic_loader.py
#
#  Copyright 2019 Luan Carvalho Martins <luancarvalho@ufmg.br>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#
#
import os

import rdkit
from os.path import splitext
import all_classes
import os_util
import mol_util


def extract_docking_poses(ligands_dict, no_checks=False, verbosity=0):
    """
    :param dict ligands_dict: dict containing docking poses
    :param bool no_checks: ignore checks and tries to go on
    :param int verbosity: be verbosity
    :rtype: dict
    """

    os_util.local_print('Entering extract_docking_poses(poses_data={}, verbosity={})'
                        ''.format(ligands_dict, verbosity),
                        msg_verbosity=os_util.verbosity_level.debug, current_verbosity=verbosity)

    os_util.local_print('{:=^50}\n{:<15} {:<20} {:<20}'.format(' Poses read ', 'Name', 'File', 'Details'),
                        msg_verbosity=os_util.verbosity_level.default, current_verbosity=verbosity)

    docking_mol_local = {}
    for each_name, each_mol in ligands_dict.items():

        if isinstance(each_mol, str):
            ligand_format = splitext(each_mol)[1].lower()
            docking_mol_rd = mol_util.generic_mol_read(each_mol, ligand_format=ligand_format, verbosity=verbosity)
            each_mol = all_classes.Namespace({'filename': each_mol, 'comment': ''})
        elif isinstance(each_mol, all_classes.Namespace):
            docking_mol_rd = mol_util.generic_mol_read(each_mol.data, ligand_format=each_mol.format,
                                                       verbosity=verbosity)
        elif isinstance(each_mol, dict):
            if isinstance(each_mol['molecule'], rdkit.Chem.Mol):
                docking_mol_rd = each_mol['molecule']
            else:
                ligand_format = each_mol.setdefault('format', os.path.splitext(each_mol['molecule'])[1])
                docking_mol_rd = mol_util.generic_mol_read(each_mol['molecule'], ligand_format=ligand_format,
                                                           verbosity=verbosity)
        elif isinstance(each_mol, rdkit.Chem.Mol):
            docking_mol_rd = each_mol
            each_mol = all_classes.Namespace({'comment': 'Read as rdkit.Chem.Mol'})
        else:
            os_util.local_print("Could not understand type {} (repr: {}) for your ligand {}"
                                "".format(type(each_mol), repr(each_mol), each_name),
                                current_verbosity=verbosity, msg_verbosity=os_util.verbosity_level.error)
            raise TypeError('Ligand must be str or all_classes.Namespace')

        if docking_mol_rd is not None:
            os_util.local_print("Read molecule {} from {}".format(each_name, each_mol),
                                current_verbosity=verbosity, msg_verbosity=os_util.verbosity_level.info)
            docking_mol_rd = mol_util.process_dummy_atoms(docking_mol_rd, verbosity=verbosity)

            docking_mol_local[each_name] = docking_mol_rd
            os_util.local_print('{:<15} {:<18} {:<18}'
                                ''.format(each_name, each_mol.get('filename', str(each_mol)),
                                          each_mol.get('comment', '')),
                                msg_verbosity=os_util.verbosity_level.default, current_verbosity=verbosity)
            os_util.local_print('Read molecule {} (SMILES: {}) from file {}'
                                ''.format(each_name, rdkit.Chem.MolToSmiles(docking_mol_rd), each_mol),
                                msg_verbosity=os_util.verbosity_level.debug, current_verbosity=verbosity)

        elif no_checks:
            os_util.local_print('Could not read data in {} using rdkit. Falling back to openbabel. It is strongly '
                                'advised you to check your file and convert it to a valid mol2.'
                                ''.format(str(each_mol)),
                                msg_verbosity=os_util.verbosity_level.warning, current_verbosity=verbosity)
            try:
                from openbabel import pybel
            except ImportError:
                import pybel

            if verbosity < os_util.verbosity_level.extra_debug:
                pybel.ob.obErrorLog.SetOutputLevel(pybel.ob.obError)
            else:
                os_util.local_print('OpenBabel warning messages are on, expect a lot of output.',
                                    msg_verbosity=os_util.verbosity_level.extra_debug, current_verbosity=verbosity)

            try:
                if type(each_mol) == str:
                    ligand_format = splitext(each_mol)[1].lstrip('.').lower()
                    docking_mol_ob = pybel.readfile(ligand_format, each_mol).__next__()
                elif type(each_mol) == all_classes.Namespace:
                    docking_mol_ob = pybel.readstring(each_mol.format, each_mol.data)
                else:
                    os_util.local_print("Could not understand type {} (repr: {}) for your ligand {}"
                                        "".format(type(each_mol), repr(each_mol), each_name))
                    raise TypeError('Ligand must be str or all_classes.Namespace')
            except (OSError, StopIteration) as error_data:
                os_util.local_print('Could not read your ligand {} from {} using rdkit nor openbabel. Please '
                                    'check/convert your ligand file. Openbabel error was: {}'
                                    ''.format(each_name, str(each_mol), error_data),
                                    msg_verbosity=os_util.verbosity_level.error, current_verbosity=verbosity)
                if not no_checks:
                    raise SystemExit(1)
            else:
                # Convert and convert back to apply mol_util.process_dummy_atoms
                docking_mol_rd = mol_util.process_dummy_atoms(mol_util.obmol_to_rwmol(docking_mol_ob))
                docking_mol_local[each_name] = docking_mol_rd

                os_util.local_print('{:<15} {:<18}'
                                    ''.format(each_name,
                                              each_mol['comment'] if isinstance(each_mol, dict)
                                              else each_mol),
                                    msg_verbosity=os_util.verbosity_level.default, current_verbosity=verbosity)
                os_util.local_print('Extracted molecule {} (SMILES: {}) using openbabel fallback from {}.'
                                    ''.format(each_name, rdkit.Chem.MolToSmiles(docking_mol_rd),
                                              str(each_mol)),
                                    msg_verbosity=os_util.verbosity_level.debug, current_verbosity=verbosity)
        else:
            os_util.local_print('Could not read data in {} using rdkit. Please, check your file and convert it to a '
                                'valid mol2. (You can also use "no_checks" to enable reading using pybel)'
                                ''.format(str(each_mol)),
                                msg_verbosity=os_util.verbosity_level.error, current_verbosity=verbosity)
            raise SystemExit(-1)

    return docking_mol_local


def read_reference_structure(reference_structure, verbosity=0):
    """ Reads a structure file

    :param str reference_structure: receptor file
    :param int verbosity: be verbosity
    :rtype: pybel.OBMol
    """

    try:
        from openbabel import pybel
    except ImportError:
        import pybel

    if verbosity < os_util.verbosity_level.extra_debug:
        pybel.ob.obErrorLog.SetOutputLevel(pybel.ob.obError)
    else:
        os_util.local_print('OpenBabel warning messages are on, expect a lot of output.',
                            msg_verbosity=os_util.verbosity_level.extra_debug, current_verbosity=verbosity)

    os_util.local_print('Entering extract read_reference_structure(reference_structure={}, verbosity={})'
                        ''.format(reference_structure, verbosity),
                        msg_verbosity=os_util.verbosity_level.debug, current_verbosity=verbosity)

    if isinstance(reference_structure, pybel.Molecule):
        # Flag that we cannot know the file path, if it's not already present. OpenBabel MoleculeData mimics a dict,
        # but lacks a setdefault method, so we're doing this the dumb way
        if 'file_path' not in reference_structure.data:
            reference_structure.data['file_path'] = False
        return reference_structure

    receptor_format = splitext(reference_structure)[1].lstrip('.')
    if receptor_format == 'pdbqt':
        receptor_format = 'pdb'

    os_util.local_print('Reading receptor data from {} as a {} file'.format(reference_structure, receptor_format),
                        msg_verbosity=os_util.verbosity_level.info, current_verbosity=verbosity)

    try:
        receptor_mol_local = pybel.readfile(receptor_format, reference_structure).__next__()
    except (ValueError, StopIteration, IOError) as error_data:
        os_util.local_print('Could not read file {}. Format {} was guessed from extension). Error message was "{}"'
                            ''.format(reference_structure, receptor_format, error_data),
                            msg_verbosity=os_util.verbosity_level.error, current_verbosity=verbosity)
        raise SystemExit(1)
    else:
        receptor_mol_local.data['file_path'] = reference_structure
        return receptor_mol_local


