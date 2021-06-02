"""
    This program will scan through the ascii version of the trace
    and identify the bytecodes that are accessed to generated the
    bytecode graph (TurboFan IR) that optimisation will be applied.

    Example,
        $python3 bytecode_identifier.py -f <ascii.out> -o <output_file.out>

    Author: Terrence J. Lim
"""

import os, sys
import re
import json
import argparse

# Code to import modules from other directories.
# Soruce: https://codeolives.com/2020/01/10/python-reference-module-in-parent-directory/
currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)

import PhaseIdentifier as pi
import x86Tracer.backTracer.instruction_restructor as ir
import FunctionLists as FL

# Assembly instructions for moving opcode.
MOVXX = [
    "movsx",
    "movzx",
]

def bytecode_identifier(lines: list, bytecode_dict: dict, phase_scope: dict):
    """This function identifies only the bytecodes that are used to
    generate the bytecode graph during the GraphBuilderPhase for V8
    version 8.2.

    args:
        lines (list): lines of raw ascii traces.
        bytecode_dict (dict): dictionary of opcode-to-bytecode.
        phase_scope (dict): phase name-to-scope dictionary.

    returns:
        (dict) dictionary holding bytecode info.
        (int) last line number that next operation should begin scanning the trace file.
    """
    # Bytecode array access at GraphBuilderPhase
    assert (
            "GraphBuilderPhase" in phase_scope
            and len(phase_scope["GraphBuilderPhase"]) > 1
    ), f"ERROR: Failed to find GraphBuilderPhase in phase_scope. phase_scope: {phase_scope}"
    GraphBuilderPhase_Scope = phase_scope["GraphBuilderPhase"]

    # Found and collected bytecode info. stored in this dictionary.
    bytecode_info = {}
    #base_counter = {}

    is_return = False
    line_number = GraphBuilderPhase_Scope[0]
    for i in range(GraphBuilderPhase_Scope[0], GraphBuilderPhase_Scope[1]):
        line = lines[i]
        re_inst = ir.instruction_splitter(line)

        # If function name is "OnHeadpBytecodeArray::get",
        # assembly operation is "mov", and destination register
        # is accumulator (al - RAX),
        if (
                re_inst[2] == FL.VERSION_GET
                or re_inst[2] == FL.VERSION_BYTECODESIZE
                or FL.VERSION_READFIELD in re_inst[2]
        ):
            # then check if MR operation exists and return, if it does.
            address, value = get_mr_info(re_inst[5:])
            
            # If address and value exists and value is an opcode,
            if address and (value in bytecode_dict):
                if is_return and bytecode_dict[value] != "Return":
                    break

                if bytecode_dict[value] == "Return":
                    is_return = True
                
                # then add to bytecode_info dict.
                bytecode_info[address] = [value, bytecode_dict[value]]
                #if address[0] not in base_counter:
                #    base_counter[address[0]] = 1
                #else:
                #    base_counter[address[0]] += 1

        line_number += 1
    #bytecode_info = bytecode_info_verifier(bytecode_info, base_counter)

    return bytecode_info, line_number

def bytecode_info_verifier(bytecode_info: dict, base_counter: dict):
    """This function scans through the collected bytecode
    information and fixes if anything that does not belong
    to part of the optimisation target bytecodes.
    
    args:
        bytecode_info (dict): dictionary holding bytecode info.
        base_counter (dict): dictionary of address base counter.

    returns:
        (dict) fixed bytecode_info dictionary.
    """
    print (f"DEBUG: base_counter - {base_counter}")
    odd_one_out = min(base_counter.values())
    target_base = None
    for base, count in base_counter.items():
        if count == odd_one_out:
            target_base = base

    print (f"DEBUG: target_base - {target_base}")

    bytecode_info_copy = bytecode_info.copy()

    for address in bytecode_info:
        if address[0] == target_base:
            bytecode_info_copy.pop(address)

    return bytecode_info_copy

def get_mr_info(mem_reg_accesses: list):
    """This function will locate memory read operation,
    if exists, in the current instruction. Then, it will
    return the memory address and value back to the caller.

    args:
        mem_reg_accesses (list): list of memory and register access
        operations.

    returns:
        (str) memory address.
        (str) stored value.
    """

    address = None
    value = None

    for op in mem_reg_accesses:
        if op[0] == "mr":
            address = op[1]
            value = op[2]
            break

    return address, value

# ============================================================================

def argument_parser():
    """This function is for a safe command line
    input. It should receive the trace file name.

    returns:
        (str) file name.
    """

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-f",
        "--file",
        type=str,
        help="An input trace file."
    )
    parser.add_argument(
        "-b",
        "--bytecode",
        type=str,
        help="Opcode to bytecode JSON file."
    )
    parser.add_argument(
        "-v",
        "--version",
        type=str,
        help="Version of v8."
    )
    args = parser.parse_args()

    return args.file, args.bytecode, args.version

def read_file(filename: str) -> list:
    """This function simply opens the file, if exists,
    then returns the read in lines in list. If the file,
    does not exist, then print out appropriate error
    message and terminates the program.

    args:
        filenmae (str): File name.

    returns:
        (list) list of read in lines.
    """

    try:
        with open(filename) as f:
            return f.readlines()
    except IOError as x:
        if x.errno == errno.ENOENT:
            assert False, "Error(" + str(errno.ENOENT) + "). " + filename + ' - does not exist'
        elif x.errno == errno.EACCES:
            assert False, "Error(" + str(errno.EACCESS) + "). " + filename + ' - cannot be read'
        else:
            assert False, "Error(" + str(x.errno) + "). " + filename + ' - some other error'

# ============================================================================

if __name__ == "__main__":
    input_file, bytecode_file, version = argument_parser()

    assert (
            version in V8_VERSIONS
    ), f"ERROR: V8 version {version} is currently not handled. Handled versions: {V8_VERSIONS}."

    with open (bytecode_file) as json_file:
        bytecode_dict = json.load(json_file)
        lines = read_file(input_file)
        # Identify the scope of each optimisation phases from the GraphBuilderPhase.
        phase_scope, has_exception, line_number = pi.phase_identifier(lines)
        if (
                version == FL.V8_VERSIONS[0]
                or version == FL.V8_VERSIONS[1]
        ):
            # Get the bytecode info.
            bytecode_info, line_number = bytecode_identifier(lines, bytecode_dict, phase_scope)
        elif version == FL.V8_VERSIONS[3]:
            # Get the bytecode info.
            bytecode_info = bytecode_identifier_8_2_0(lines, bytecode_dict, phase_scope)
        elif version == FL.V8_VERSIONS[4]:
            # Get the bytecode info.
            bytecode_info, line_number = bytecode_identifier_8_2_297(lines, bytecode_dict, phase_scope)

        print (bytecode_info)

