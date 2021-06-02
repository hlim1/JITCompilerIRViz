"""
This program open and scan input trace file in ascii format.
It identifies the scope of each optimisation phases from the trace.

Example:
    $python3 phase_identifier.py -f ascii.out

Author: Terrence J. Lim
"""
import os
import re
import sys
import argparse
import statistics

# Code to import modules from other directories.
# Soruce: https://codeolives.com/2020/01/10/python-reference-module-in-parent-directory/
currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)

import FunctionLists as FL

EXCEPTION = "EXCEPTION"

def instruction_splitter(inst_line: str):
    """This function splits and clean up the instrcution line.
    The ascii file generated using updated trace2ascii under
    uacs-lynx conveniently delimited the line with semi-colons (;).

    args:
        inst_line (str): A single line of instruction read in from
        the ascii trace file.

    returns:
        (list): a list holding splitted instruction.
    """
    assert (
            len(inst_line) > 0
    ), f"Line cannot be an empty string."

    try:
        splitted = inst_line.split(';')[1:-1]
    except Exception as e:
        print (f"ERROR: {e} - Original: {inst_line} - Splitted: {inst_line.split(';')}")
        assert False, "Terminating the Program"

    idx = 0
    splitted_inst = []
    for elem in splitted:
        if idx == 1 or idx == 2 or idx == 4:
            if idx > 4:
                # Since we only need 3 info. from the instruction line, we break
                # out from the line scanning once they are all collected.
                break
            else:
                splitted_inst.append(elem.strip())
        idx += 1

    try:
        program = splitted_inst[0]
        function = splitted_inst[1]
        operation = splitted_inst[2]
    except Exception as e:
        print (f"ERROR: {e} - raw line: {inst_line} - splitted inst: {splitted_inst}")

    return program, function, operation

def phase_identifier(lines: list):
    """This function identifies the scope (line numbers) of each
    optimisation phase.

    args:
        lines (list): lines of raw ascii traces.

    returns:
        (dict) phase name-to-scope dictionary.
    """
    p_re = re.compile(FL.OPT_PHASE_REGEX)

    # Data Structure:
    #   {Phase name = [first, last],}
    opt_phase_scope = {}
    phase_scope = {}
    first_and_last = [0,0]

    line_number = 1
    has_exception = False
    is_match = False
    for raw_line in lines:
        # If "EXCEPTION" occured, then following instructions are
        # for debugging process and program termination, so we can
        # safely ignore rest and break out from the loop.
        if EXCEPTION in raw_line:
            has_exception = True
            break

        program, function, operation = instruction_splitter(raw_line)
        re_phase = p_re.search(function)
        if program == "d8":
            if re_phase:
                re_phase = p_re.search(function)
                phase = re_phase.group("phase")
                fill_phase_scopes(opt_phase_scope, line_number, operation, phase, first_and_last)
            elif re.match(FL.PHASE_REGEX, function):
                phase = function.split("::")[3]
                fill_phase_scopes(phase_scope, line_number, operation, phase, first_and_last)

        line_number += 1

    # Combine two dictionaries.
    for phase, scope in phase_scope.items():
        if phase not in opt_phase_scope:
            opt_phase_scope[phase] = scope
        else:
            opt_phase_scope[phase] += scope

        # TODO: Fix the odd number of phase scopes properly.
        # There was one case when handling V8 version 6.5.0 that one GraphBuilderPhase
        # return instruction is missing resulting to making scope list odd.
        if len(opt_phase_scope[phase]) % 2 != 0:
            opt_phase_scope[phase].pop(1)

    return opt_phase_scope, has_exception, line_number, first_and_last

def fill_phase_scopes(phase_scope: dict, line_number: int, operation: str, phase: str, first_and_last: list):
    if phase not in phase_scope:
        phase_scope[phase] = [line_number]
        if first_and_last[0] == 0:
            first_and_last[0] = line_number
    elif operation == "push rbp" or operation == "ret":
        phase_scope[phase].append(line_number)
        first_and_last[1] = line_number
    elif operation == "push r15" and len(phase_scope[phase]) % 2 == 0:
        phase_scope[phase].append(line_number)
        first_and_last[1] = line_number

def calculate_size(phase_scope: dict):
    """This function calculates the size of JIT compiler execution in terms of
    the trace line numbers of phases. This will find the total number of phase
    lines, max, median, and min.

    args:
        phase_scope (dict): phase-to-scope list dictionary.

    returns:
        (tuple) total, max, median, and min
    """

    list_of_line_numbers = []

    for phase, scopes in phase_scope.items():
        for i in range(0, len(scopes), 2):
            number_of_lines = (scopes[i+1] - scopes[i]) 
            list_of_line_numbers.append(number_of_lines)

    return (
            sum(list_of_line_numbers),
            max(list_of_line_numbers),
            int(statistics.median(list_of_line_numbers)),
            min(list_of_line_numbers)
    )

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
    args = parser.parse_args()

    return args.file

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


if __name__ == "__main__":        
    filename = argument_parser()
    lines = read_file(filename)
    phase_scope, has_exception, line_number, first_and_last = phase_identifier(lines)
    for phase, scope in phase_scope.items():
        print(f"Phase: {phase} - Scope: {scope}")
    print (f"First line number: {first_and_last[0]}. Last line number: {first_and_last[1]}")
    _sum, _max, _med, _min = calculate_size(phase_scope)
    print (f"Sum: {_sum}, Max: {_max}, Median: {_med}, Min: {_min}") 

