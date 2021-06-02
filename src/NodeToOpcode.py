import os, sys
import argparse

# Code to import modules from other directories.
# Soruce: https://codeolives.com/2020/01/10/python-reference-module-in-parent-directory/
currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)

import X86ASM as X86
import FunctionLists as FL
import GraphCreator as GC

import x86Tracer.backTracer.instruction_restructor as IREST

PUSH_OP_INSTS = [
        "41 57",        # push r15
#        "41 56",       # push r14
#        "53",          # push rbx
        "50",           # push rax
        "48 89 f2",     # mov rdx, rsi
        "48 89 f0",     # mov rax, rsi
]

def NodeToOpcode_Mapper(lines: list):
    """
    """

    node = [None]
    current_op = None
    current_addr = None
    NodeToOpcode = {}
    OpAddressToOpcode = {}

    for line in lines:
        re_inst = IREST.instruction_splitter(line)
        
        image = re_inst[1]
        function = re_inst[2]

        if image != "d8":
            continue

        address_to_opcode(re_inst, OpAddressToOpcode)

        if function == FL.NEWNODE_STR or function == FL.NEWNODEUNCHECKED_STR:
            new_op, new_addr = get_opcode(re_inst, line, OpAddressToOpcode)
            if new_op:
                # If current_op already exists, we replace the value of current_op with the new_op.
                # This is because of the assumption that the last opcode appeared is the opcode
                # for currently generating node.
                current_op = new_op
                current_addr = new_addr
        elif function == FL.CLONENODE_STR:
            org_node = get_clone_node(re_inst, line, NodeToOpcode)
            if org_node:
                current_op = NodeToOpcode[org_node][0]
                current_addr = NodeToOpcode[org_node][1]
        elif function == FL.NEW_STR:
            assert current_op, f"ERROR: current_op is None - {line}"
            if re_inst[4]['asm_inst'][1][0] == "rax":
                GC.get_new_node(node, re_inst, line, {})
            elif re_inst[4]['asm_inst'][0] == "ret":
                assert node, f"ERROR: node[0] is None - {line}"
                NodeToOpcode[node[0]] = [current_op, current_addr]
                current_op = None
                current_addr = None

    return NodeToOpcode

def get_clone_node(re_inst: list, line: str, NodeToOpcode: dict):
    """
    """
    node = None

    if re_inst[3] in PUSH_OP_INSTS:
        address = get_address(re_inst)
        if address in NodeToOpcode:
            node = address

    return node

def get_node_address(rw_inst: list):
    """
    """

    for inst in rw_inst:
        if inst[0] == "r" and inst[1] == "rax":
            return inst[2]

    return None

def get_opcode(re_inst: list, line: str, OpAddressToOpcode: dict):
    """
    """

    address = None
    current_op = None
    
    if re_inst[3] in PUSH_OP_INSTS:
        address = get_address(re_inst)
        if address in OpAddressToOpcode:
            current_op = OpAddressToOpcode[address]

    return current_op, address

def address_to_opcode(re_inst: list, OpAddressToOpcode: dict):
    """
    """

    function = re_inst[2]
    asm_inst = re_inst[4]['asm_inst']
    if (
            function == FL.OPERATOR
            and asm_inst[0] == "mov"
            and "wordptr" in asm_inst[1][0]
            and "rdi+0x10" in asm_inst[1][0]
            and asm_inst[1][1] == "si"
    ):
        opcode, op_address = get_op(re_inst[5:])
        assert (
                len(opcode) == 4
        ), f"ERROR: opcode {opcode} is not in the correct form."
        # This assert's been commented out with an assumption that the opcode address
        # can be overwritten after used. Thus, we do not have to prohibit overwriting yet.
        # Though, it may require further investigation, so we are commenting this code out
        # rather than removing it until we have a solid answer to it.
        #assert (
        #        (op_address not in OpAddressToOpcode)
        #        or (opcode == OpAddressToOpcode[op_address]) 
        #), f"ERROR: op_address {op_address} already in the dictionary\n\
        #        with value {OpAddressToOpcode[op_address]}. New opcode {opcode}."
        OpAddressToOpcode[op_address] = opcode

def get_op(rw_insts: list):
    """
    """

    opcode = None
    op_address = None
    for inst in rw_insts:
        if inst[0] == "mw":
            opcode = inst[2]
        elif inst[0] == "r" and inst[1] == "rdi":
            op_address = inst[2]

    return opcode, op_address

def get_address(re_insts: list):
    """
    """
    target_regs = ["r14", "r15", "rbx", "rax", "rsi"]
    for inst in re_insts[5:]:
        if inst[0] == "r" and inst[1] in target_regs:
            return inst[2]

def read_file(filename: str) -> list:

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

def argument_parser():
    """This function is for a safe command line
    input. It should receive the trace file name.

    returns:
        (str) path to trace ascii file.
    """

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-f",
        "--file",
        type=str,
        help="Original PoC JS file."
    )
    
    args = parser.parse_args()

    return args.file

if __name__ == "__main__":
    ascii_f = argument_parser()
    lines = read_file(ascii_f)
    NodeToOpcode = NodeToOpcode_Mapper(lines)
    for node, opcode in NodeToOpcode.items():
        print(opcode[0])    # Prints only opcodes
        #print (f"{node} = {opcode}") # Prints node address, opcode, and opcode address
