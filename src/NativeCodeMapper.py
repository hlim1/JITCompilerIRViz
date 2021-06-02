"""
    This program first identifies all code generation steps
    for each final optimised node. Then, it maps the generated
    native codes to the bytecode and returns the dictionary.

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

import FunctionLists as FL
import X86ASM as X86

import x86Tracer.backTracer.instruction_restructor as IREST

# List of x86 registers.
RSI = ["esi", "rsi"]
PUSH_REGS = ["r12", "r13", "r14", "r15"]
PUSH_OPERANDS = ["54", "55", "56", "57"]

# List of assembly opcodes and mnemonics.
MOV = "mov"
MOV_ = [
        "8b", "49"
]
BYTEPTR = "byteptr"

# List of assembly operations.
OPTFUNCTION_SETTING_OP = "49 8b 75 00"
INSTRUCTION_EMIT_OPCODE_OP = "44 89 fe"
ADDINSTRUCTION_OP = "49 89 f7"
GET_CURRENT_VISITING_NODE_OP = "4c 89 ee"
GET_OPCODE_OP = "09 f7"
GET_ENCODED_OPCODE_01_OP = "09 c7"
GET_ENCODED_OPCODE_02_OP = "45 09 dd"
EMIT_FUNC_OPCODE_OP = "41 89 f7"

OPCODE_WRITE_INSTS = [
        "mov byte ptr [rcx]",
        "mov byte ptr [rax]",
]

def instruction_address_identifier(re_inst: list):
    """This function identifies the generated internal usage
    instruction address and returns.

    args:
        re_inst (list): restructured instruction line

    returns:
        (str) Found instruction address in a string type.
        (bool) Flag to indicate whether the address was found or not.
    """

    instruction_addrs = []

    asm_inst = re_inst[4]["asm_inst"]
    rw_insts = re_inst[5:]

    if len(asm_inst[1]) > 1 and asm_inst[1][1] == "rsi":
        for op in rw_insts:
            if op[0] == "r" and op[1] == "rsi":
                return op[2], True

    return None, False

def get_instruction_opcode(lines: list, instruction_addrs: list, start_from: int, stop_at: int):
    """This function retrieves the instruction opcode for the instruction. One thing to aware is
    that the opcode that this function differs from the machine code instruction opcode that
    code generator generates.

    args:
        lines (list): list of raw trace instructions.
        instruction_addrs (list): list of instruction addresses.
        start_from (int): line number of instructions to start scanning.
        stop_line (int): line number of instructions to stop scanning.

    returns:
        (dict) dictionary of instruction address-to-opcode.
        (dict) dictionary of instruction opcode-to-address.
    """

    address_to_opcode = {}
    opcode_to_addresses = {}
    
    for line in lines[start_from:stop_at]:

        # This is noot really needed, but for the efficiency purpose,
        # check the function name.
        if FL.INSTRUCTION not in line:
            continue

        re_inst = IREST.instruction_splitter(line)

        assert (
                re_inst[2] == FL.INSTRUCTION
        ), f"ERROR: Currently analysing instruction is not Instruction() - {re_inst[2]}"

        for op in re_inst[5:]:
            if op[0] == "mw" and op[1] in instruction_addrs:
                opcode = op[2].lstrip('0')
                assert (
                        op[1] not in address_to_opcode
                ), f"ERROR: Address {op[1]} already in the dictionary - {address_to_opcode}"
                address_to_opcode[op[1]] = opcode
                # Since there can be one-to-many relationship between one opcode to
                # instructions, keep the dictionary in such form.
                if opcode not in opcode_to_addresses:
                    opcode_to_addresses[opcode] = [op[1]]
                else:
                    opcode_to_addresses[opcode].append(op[1])

    return address_to_opcode, opcode_to_addresses

def node_to_instruction_mapper(
                                lines: list, start_from: int, stop_at: int,
                                instruction_to_opcode: dict, inst_addresses: list
):
    """This function will map the final node to the internal use purpose
    instruction address.

    args:
        lines (list): list of raw trace instructions.
        start_from (int): line number of instructions to start scanning.
        stop_line (int): line number of instructions to stop scanning.
        instruction_to_opcode (dict): dictionary of instruction address-to-opcode.

    returns:
        (dict) dictionary of node-to-instruction addresses.
        (dict) dictionary of instruction-to-node.
        (line) line number of the first encountered emit instructions in a reversed order.
    """

    # Dictionary for hold node to instruction addresses
    node_to_instruction = {}
    instruction_to_node = {}

    current_node = None
    inst_address = None

    # Flags:
    is_instruction_gen = False

    line_number = start_from
    for line in lines[start_from:]:
        re_inst = IREST.instruction_splitter(line)
        function = re_inst[2]
        X86Op = re_inst[3]
        X86Op_SP = re_inst[3].split(' ')
        asm_inst = re_inst[4]["asm_inst"]
        rw_insts = re_inst[5:]

        # Find and get the control node address that VisitContol function is visting.
        if function == FL.VISITCONTROL and X86Op == GET_CURRENT_VISITING_NODE_OP:
            node = None
            for op in rw_insts:
                if op[0] == "w" and op[1] == "rsi":
                    node = op[2]
            assert (
                    node
            ), f"ERROR: VisitControl Node is not valid - Node: {node} - Line: {line}"
            current_node = node
            is_instruction_gen = True
        elif function == FL.ISVISITNODE and X86Op == X86.PUSH_RBX:
            node = None
            for op in rw_insts:
                if op[0] == "r" and op[1] == "rbx":
                    node = op[2]
            assert (
                    node
            ), f"ERROR: VisitNode Node is not valid - Node: {node} - Line: {line}"
            current_node = node
            is_instruction_gen = True

        # If is_instruction_gen flag is true, it represents that either VisitControl or VisitNode
        # function was entered and visited some node to generate an instruction. Thus, following
        # code gets triggered only if this flag is true.
        if is_instruction_gen:
            assert (
                    current_node
            ), f"ERROR: current_node is None.\nLine: {line}"

            # If the scanning has reached the Emit() instruction that actually emits the instruction address
            # for the currnet opcode, we collect that instruction address and make a mapping with the node.
            if function == FL.EMIT and asm_inst[1][0] == "rbx":
                for op in rw_insts:
                    if op[0] == "w" and op[1] == "rbx":
                        if op[2] in inst_addresses:
                            inst_address = op[2]
            elif function == FL.EMIT and "ptr" in asm_inst[1][0] and "rbx" in asm_inst[1][0]:
                for op in rw_insts:
                    if op[0] == "mw":
                        if op[2] in inst_addresses:
                            inst_address = op[2]
            elif function != FL.EMIT and inst_address:
                assert (
                        inst_address
                ), f"ERROR: inst_address is None.\nLine: {line}"
                if current_node not in node_to_instruction:
                    node_to_instruction[current_node] = [inst_address]
                else:
                    node_to_instruction[current_node].append(inst_address)

                # Reset all holders and flags.
                current_node = None
                inst_address = None
                is_instruction_gen = False
        else:
            pass

        line_number += 1

    return node_to_instruction, instruction_to_node

def instruction_to_code_mapper(lines: list, start_from: int, stop_at: int):
    """This function identifies and map generated codes (opcodes and
     operands) to the instruction addresses.

     args:
        lines (list): list of raw trace instructions.
        start_from (int): line number of instructions to start scanning.
        stop_at (int): line number of instructions to stop scanning.

     returns:
        (dict) instruction-to-code map.
        (list) list of instruction addresses.
     """

    # Dictionary that holds instruction address-to-generated codes.
    # Note: One-to-One relationship.
    instruction_to_code = {}
    # List to hold previous addresses where opcodes were written.
    opcode_addresses = []
    # List of all the instruction addresses.
    inst_addresses = []
    # Instruction address holder to keep a track of which instruction the code is begin
    # generated for.
    cur_instruction = None
    # Current x86 code to generate.
    cur_code = None
    # Previous opcode holder.
    prev_opcode = None

    # Flag to set start seeking for code generation as well as identifying
    # the current instruction address.
    is_assemble_instruction = False
    # Flag to indicate whether currently found opcode is one instruction's code or not.
    is_one_code = False
    # Flag to indicate either the instruction address was found or not.
    has_found_inst = False
    # Flag to indicate turbo assembler has excuted.
    is_TurboAssembler = False

    for line in lines[start_from:stop_at]:
        re_inst = IREST.instruction_splitter(line)
        function = re_inst[2]
        x86op = re_inst[3]
        asm_inst = re_inst[4]["asm_inst"]

        # Extract instruction address.
        if function == FL.ADDINSTRUCTION and not has_found_inst:
            address, has_found_inst = instruction_address_identifier(re_inst)
            if address:
                inst_addresses.append(address)
        elif function == FL.ADDINSTRUCTION and asm_inst[0] == "ret":
            has_found_inst = False

        # We only need to consider the instructions between AssembleInstruction().
        # Thus, we mark a flag to true when entering the function and reset to false
        # when returning from the function.
        if function == FL.ASSEMBLEINSTRUCTION and x86op == X86.PUSH_RBP:
            assert (
                    asm_inst[0] == "push"
                    and asm_inst[1][0] == "rbp"
            ), f"ERROR: Assembly instruction for x86 opcode 55 is not 'push rbp' - {asm_inst}"
            is_assemble_instruction = True
        elif function == FL.ASSEMBLEINSTRUCTION and is_assemble_instruction and x86op not in X86.RET:
            # Identify and retrieve the instruction address that current
            # AssembleInstruction() is assembling the code.
            if asm_inst[1][0] == "eax" and "ptr" in asm_inst[1][1] and not cur_instruction:
                for op in re_inst[5:]:
                    if op[0] == "mr":
                        cur_instruction = op[1]
        elif function == FL.ASSEMBLEINSTRUCTION and x86op in X86.RET:
            is_assemble_instruction = False
            cur_instruction = None

        # Code generation is done by Assembler::X() after AssembleInstruction()
        # check for the instruction address and get the opcode for it.
        if is_assemble_instruction:
            if re.match(FL.ASSEMBLER_REGEX, function):
                # Retrieve the opcode information, if any exists.
                code, cur_dest = get_opcode(re_inst[5:], "mw")
                # If encountered the first opcode of the instruction, then set the flags to True
                # and assign the code to cur_code variable.
                if asm_inst[0] == "mov" and "byteptr" in asm_inst[1][0] and not is_one_code:
                    # Opcode is the first opcode for the first optimised code instruction.
                    if not opcode_addresses:
                        cur_code = code
                        is_one_code = True
                        opcode_addresses.append(cur_dest)
                        prev_opcode = code
                    else:
                        distance = int(cur_dest, 16) - int(opcode_addresses[-1], 16)
                        is_equal = cur_dest[0] == opcode_addresses[-1][0]
                        # Opcodes are written one next to each other. In other words,
                        # memory distance of one opcode and another is 1 unless a the previous
                        # opcode instruction was a jump instruction. Also, check for the base
                        # address (that is first 5 bytes) of current and previous opcodes'
                        # written memory locations.
                        if (
                                distance == 1
                                or ((prev_opcode in X86.ONE_BYTE_JX 
                                        or prev_opcode in X86.TWO_BYTE_JX
                                        or prev_opcode in X86.JMP)
                                     and is_equal)
                                or ((code in X86.ONE_BYTE_JX 
                                        or code in X86.TWO_BYTE_JX
                                        or code in X86.JMP)
                                     and is_equal)
                        ):
                            cur_code = code
                            is_one_code = True
                            opcode_addresses.append(cur_dest)
                            prev_opcode = code
                        else:
                            pass
                elif asm_inst[0] == "mov" and "byteptr" in asm_inst[1][0] and is_one_code:
                    distance = int(cur_dest, 16) - int(opcode_addresses[-1], 16)
                    is_equal = cur_dest[0] == opcode_addresses[-1][0]
                    if (
                            distance == 1
                            or ((prev_opcode in X86.ONE_BYTE_JX 
                                    or prev_opcode in X86.TWO_BYTE_JX
                                    or prev_opcode in X86.JMP)
                                 and is_equal)
                            or ((code in X86.ONE_BYTE_JX 
                                    or code in X86.TWO_BYTE_JX
                                    or code in X86.JMP)
                                 and is_equal)
                    ):
                        cur_code += f" {code}"
                        opcode_addresses.append(cur_dest)
                        prev_opcode = code
                elif asm_inst[0] == "ret" and is_one_code:
                    assert (
                            cur_instruction
                    ), f"ERROR: There is no instruction exists (None) - line: {line}"
                    if cur_instruction in instruction_to_code:
                        instruction_to_code[cur_instruction].append(cur_code)
                    else:
                        instruction_to_code[cur_instruction] = [cur_code]
                    cur_code = None
                    is_one_code = False

    return instruction_to_code, inst_addresses

def get_opcode(rw_insts: list, op: str):
    """This function finds the requested value from
    the memory or register read/write instructions.

    args:
        op (str): represents either read (r) or write (w) operation.

    returns:
        (str) found address.
    """

    opcode = None
    opcode_addr = None

    for inst in rw_insts:
        if inst[0] == op and len(inst[2]) == 2:
            opcode_addr = inst[1]
            opcode = inst[2]

    return opcode, opcode_addr

def instruction_to_optcode_mapper(instruction_to_codes: dict, optcodes: dict):
    """This function maps machine code to the instruction address.

    args:
        instruction_to_code (dict): One-to-many relationship mapping of generate
        codes and the instruction address.
        optcodes (dict): One-to-Many relationship mapping of optimised code
        function addresses to executed machine codes that belong to it.

    returns:
        (dict) One-to-One relationship mapping of instruction address and
        executed machine codes.
    """
    # Dictionary to hold instruction address to machine code.
    # Note: One-to-Many relationship.
    instruction_to_machine_code = {}

    # First, find the target optfunction.
    target_optfunction = find_target_optfunction(instruction_to_codes, optcodes)

    opt_instructions = optcodes[target_optfunction]

    for inst, codes in instruction_to_codes.items():
        opt_instruction, opt_instructions = get_opt_instruction(codes, opt_instructions)

        if inst not in instruction_to_machine_code:
            if opt_instruction:
                instruction_to_machine_code[inst] = opt_instruction
        else:
            if opt_instruction:
                instruction_to_machine_code[inst].append(opt_instruction)

    return instruction_to_machine_code

def get_opt_instruction(codes: list, opt_instructions: list):
    """This function will find the matching optimised instruction
    to the passed list of codes for one instruction address. Then,
    return the optimised instruction and remove it from the list.

    args:
        codes (list): collected opcode list.
        opt_instructions (list): list of optimised instructions belong
        to the target optfunction.

    returns:
        (list) optimised instructions
    """

    opt_instructions_copy = opt_instructions.copy()
    instructions = []
    insts_to_remove = []
    collected_codes = {}
    codes_len = len(codes)
    inst_number = 0
    collected_line = 0

    for inst in opt_instructions:
        x86op = get_x86_op(inst[3])

        # Two conditions in order to verify that current instruction belongs to
        # the current instruction address.
        # (1) x86 code matches one of the codes in the current instruction address.
        # (2) Optimised instructions must be in the order matching with the order in codes.
        if (
                x86op in codes
                and (collected_line == 0 or
                        (inst_number - collected_line) == 1)
        ):
            instructions.append(inst)
            collected_codes[x86op] = inst
            # In order to avoid scanning the same instructions again and again,
            # remove the instructions once added.
            # opt_instructions_copy.remove(inst)
            insts_to_remove.append(inst)
            collected_line = inst_number
            codes_len -= 1
        elif x86op in codes and collected_line > 0 and inst_number - collected_line > 1:
            if x86op in collected_codes:
                try:
                    instructions.remove(collected_codes[x86op])
                    insts_to_remove.remove(collected_codes[x86op])
                    collected_codes.pop(x86op)
                    codes_len += 1
                except:
                    assert False, f"ERROR: {x86op} - {collected_codes} - {instructions}"
            if codes_len > 0:
                instructions.append(inst)
                insts_to_remove.append(inst)
                collected_line = inst_number
                codes_len -= 1

        if codes_len == 0:
            break

        inst_number += 1
    print (f"DEBUG: - instructions: {instructions}")
    # To make sure the optcodes really belong to the current instruction address,
    # we make a safety guard that we keep the collected instruction only if the
    # 75% of the instructions are matching, else reset None.
    # This number (75%) may require up or down, so adjust it while running more benchmarks.
    if len(instructions) < len(codes)*0.75:
        instructions = []
    else:
        for inst in insts_to_remove:
            opt_instructions_copy.remove(inst)

    return instructions, opt_instructions_copy

def find_target_optfunction(instruction_to_codes: list, optcodes: dict):
    """This function finds the target optfunction by comparing the collected codes
    to the executed optimised instruction codes.

    args:
        instruction_to_code (dict): One-to-many relationship mapping of generate
        codes and the instruction address.
        optcodes (dict): One-to-Many relationship mapping of optimised code
        function addresses to executed machine codes that belong to it.

    returns:
        (str) address of optimised function. 
    """

    optfunction_counter = {}
    for inst, codes in instruction_to_codes.items():
        target_optfunction = find_optcode_match(codes, optcodes)
        if target_optfunction:
            if target_optfunction in optfunction_counter:
                optfunction_counter[target_optfunction] += 1
            else:
                optfunction_counter[target_optfunction] = 1

    # Optfunction that has the most match is the target optfunction.
    optfunction = max(optfunction_counter.keys(), key=(lambda k: optfunction_counter[k]))

    return optfunction

def find_optcode_match(codes: list, optcodes: dict):
    """This function finds the target optfunction by comparing the collected codes
    to the executed optimised instruction codes.

    args:
        codes (list): collected opcode list.
        optcodes (dict): executed optimised codes.

    returns:
        (str) address of optimised function.
    """

    code_len = len(codes)
    cur_optfunction = None
    target_optfunction = None
    matched_counter = 0
    for address, insts in optcodes.items():
        for inst in insts:
            x86op = get_x86_op(inst[3])
            if x86op in codes:
                matched_counter += 1

                if matched_counter == code_len:
                    target_optfunction = address
                    break

    return target_optfunction

def get_x86_op(x86op: str):
    """This function cleans of the unnecessary operands
    or simply return the original x86 opcode & operand
    string.

    args:
        x86op (str): x86 opcode & operand string.

    returns:
        (str) either cleaned or original form of x86 string.
    """
    x86op_sp = x86op.split(' ')
    # For JUMP instructions, executed codes have more
    # operands that are not collectible by the tool.
    # Thus, simply remove the operands that are not needed
    # and maintain the prefix '0f' and the opcode.
    if (
            x86op_sp[0] == X86.OF
            and (x86op_sp[1] in X86.ONE_BYTE_JX
                    or x86op_sp[1] in X86.TWO_BYTE_JX)
    ):
        return (' ').join(x86op_sp[0:2])
    elif x86op_sp[0] in X86.JMP[0]:
        return x86op_sp[0]
    elif len(x86op_sp) > 1 and x86op_sp[1] in X86.HEX_MOV:
        return (' ').join(x86op_sp[0:2])
    else:
        return x86op

def optimised_code_identifier(lines: list, start_from: int):
    """This function identifies optimised machine code
    executions in the trace.

    args:
        lines (list): list of raw trace instructions.

    returns:
        (list) list of optimised codes. 
    """

    # Main dictionary to hold
    # "opt.function address" = [optimised instructions, ...]
    optcodes = {}
    # Tracker dictionary to track collected opt. instructions
    collected_optcodes = {}
    # Flag variables to keep a track of current opt. function.
    cur_optfunction = None
    cur_optfunction_base = None
    is_optf_entry = False
    is_collecting = False
    is_within_optf = False
    stop_increment = False

    for_debug = {}

    line_number = start_from
    
    for line in lines[start_from:]:
        re_inst = IREST.instruction_splitter(line)
        # Store current instruction address after removing 0x.
        try:
            current_addr = re_inst[0][2:]
        except:
            assert (
                    False
            ), f"Something wrong with re_inst: {re_inst} - Line {line_number}; {line}"
        current_addr_base = (current_addr[:4]).ljust(len(current_addr),'0')

        if re_inst[2] == FL.FINALIZEJOBIMPL:
            address = get_opt_function_address(re_inst)
            if address:
                for_debug[address] = []
                optcodes[address] = []
                collected_optcodes[address] = []
                address_size = len(address)
                cur_optfunction = address
                # Considering first 4 bytes are the base address.
                # For example, 2ade from 0x2ade00082ce2.
                # Then, fill "0" for the rest of bytes.
                cur_optfunction_base = address[:4].ljust(address_size,'0')

        if re_inst[2] == FL.FUNCTION_ENTRY and not is_optf_entry and cur_optfunction:
            is_optf_entry = is_optfunction_entry(re_inst[5:], cur_optfunction.zfill(16))
            stop_increment = True
    
        if cur_optfunction and current_addr_base == cur_optfunction_base:
            if is_optf_entry:
                if (
                        cur_optfunction in collected_optcodes
                        and re_inst[0] not in collected_optcodes[cur_optfunction]
                ):
                    # Append all instructions and map to its main optimised function address.
                    for_debug[cur_optfunction].append(line.strip())
                    optcodes[cur_optfunction].append(re_inst)
                    collected_optcodes[cur_optfunction].append(re_inst[0])
                    is_collecting = True
            elif is_within_optf:
                if re_inst[4]["asm_inst"][0] == "call":
                    is_optf_entry = True
                    is_within_optf = False
            else:
                is_within_optf = is_optfunction_entry(re_inst[5:], cur_optfunction.zfill(16))
        else:
            # Reset all flag variables and value holder variables at the end of last
            # optimised code instruction collected.
            if is_optf_entry and is_collecting:
                is_optf_entry = False
                is_collecting = False
                address = None
                cur_optfunction = None
                cur_optfunction_base = None

        if not stop_increment:
            line_number += 1

    return optcodes, line_number, for_debug

def is_optfunction_entry(re_inst: list, cur_optfunction: str):
    """This function checks if the current function entry is an entry
    to the optimised code or not.

    args:
        re_inst (list): restructured instruction line.
        cur_optfunction (str): current optimised function entry.

    returns:
        (bool) true, current entry is an entry to the currently stroed optimised code.
               false, current entry is not an entry to the currently stroed
               optimised code.
    """
    
    is_entry = False
    for inst in re_inst:
        if inst[2] == cur_optfunction:
            is_entry = True

    return is_entry

def get_opt_function_address(line: list):
    """This function identifies the start address of optimised
    function and returns the address of it. This function is
    called only when the function name is FINALIZEJIBIMPL,
    which needs to be checked within the caller function.

    args:
        line (list): restructured instruction line.

    returns:
        (str) start address of optimised function.
    """
    assert (
            line
    ), f"ERROR: Restructured instruction line is empty."

    address = None
    asm_inst = line[4]["asm_inst"]
    asm_ops = line[3]
    asm_opcode = asm_ops.split(' ')[0]

    # If the assembly mnemonic is mov with optimised function setting
    # operations and the destination register is rsi,
    if (
            asm_inst[0] == MOV
            and asm_ops == OPTFUNCTION_SETTING_OP
            and asm_inst[1][0] in RSI
    ):
        # then retrieve the rsi value that is an address of optimised function.
        for inst in line[5:]:
            if inst[0] == "w" and inst[1] == RSI[1]:
                address = inst[2].lstrip('0')

    return address


def get_nodes(SFI: dict, bytecode: str):
    """This function returns the list of generated nodes for the bytecode.

    args:
        SFI (dict): dictionary holding all optimised info of a function.

    returns:
        (list) list of generated nodes.
    """

    nodes = []

    for node, phases in SFI[bytecode].items():
        if FL.INST_SELECT_PHASE in phases:
            nodes.append(node)

    return nodes

# =============================================================================================

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
        "-s",
        "--start",
        type=int,
        help="Line number to begin scanning the file."
    )
    parser.add_argument(
        "-e",
        "--end",
        type=int,
        help="Line number to end scanning the file."
    )
    args = parser.parse_args()

    return args.file, args.start, args.end

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

# =============================================================================================

if __name__ == "__main__":
    input_f, start_from, stop_at = argument_parser()

    lines = read_file(input_f)
    # Get executed optimised codes.
    optcodes, ignore, for_debug = optimised_code_identifier(lines, start_from)
    print ("Executed Optimised Code Instructions:")
    for address, codes in for_debug.items():
        print ("Address: ", address)
        print ("Codes:")
        for code in codes:
            print (code)
    print ("")

    # Map generated opcodes and oprands to instruction addresses. 
    instruction_to_opcodes, inst_addresses = instruction_to_code_mapper(lines, start_from, stop_at)
    print ("instruction_to_opcodes:")
    for inst, code in instruction_to_opcodes.items():
        print (inst, code)

    #
    inst_to_optcodes = instruction_to_optcode_mapper(instruction_to_opcodes, optcodes)
    # print ("Instruction_to_optcode: ", inst_to_optcodes)
    for inst, optcodes in inst_to_optcodes.items():
        print (f"0x{inst}")
        for optcode in optcodes:
            print (f" - {optcode}")
    print ("")
    
    node_to_instruction, instruction_to_nodes = node_to_instruction_mapper(
                                                                    lines, start_from, stop_at,
                                                                    instruction_to_opcodes, inst_addresses
    )
    print (f"node_to_instruction:")
    for node, insts in node_to_instruction.items():
        print (f"Node: {node}, Inst: {insts}")

    finals = {"nodes":list(node_to_instruction.keys())}
    with open ("final_nodes.json", "w") as json_f:
        json.dump(finals, json_f)
