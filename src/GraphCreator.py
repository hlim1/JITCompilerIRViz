"""
    This program generates a graph with the identified
    nodes and its input nodes.

    Author: Terrence J. Lim
"""

import os, sys
import json
import argparse

# Code to import modules from other directories.
# Soruce: https://codeolives.com/2020/01/10/python-reference-module-in-parent-directory/
currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)

import X86ASM as X86
import FunctionLists as FL
import PhaseIdentifier as PI
import OptimisationTracker as OT
import NodeToOpcode as NTO

import x86Tracer.backTracer.instruction_restructor as IREST

# List of X86 operations.
ATTACH_INPUT_NODE = "49 89 1c b8"
FROMNODE = "48 8b 44 cf 20"
ARGUMENT_PUSHES = [
        "41 54",
        "41 55",
        "41 56",
        "41 57",
]

def graph_former(lines: list, start_from: int, end_at: int, initial_nodes: list, phase_scopes: dict):
    """This function identifies all generated nodes, their input
    nodes, if exist, and their direct parent node, if exist as well.
    Then, constructs two different data structures to hold those
    information to generate a graph.

    args:
        lines (list): list of raw trace lines.
        start_from (int): trace line number to start scanning.
        end_at (int): trace line number to stop scanning.
        initial_nodes (list): list of initial bytecode node addresses.

    returns:
        (dict) generated node and its input nodes map.
        (dict) generated node and its direct parent node map.
    """

    # Data structure to hold each node to its inputs.
    # There may be no input nodes to generate the new node,
    # so some node might have an empty list mapped to it.
    node_and_inputs = {}
    # Dict. to hold generated node-to-phase data.
    node_to_phase = {}
    # Dict. to hold phase-to-nodes data.
    phase_to_nodes = {}
    # Dict. to hold the both read and write values if two differ.
    new_node_map = {}
    # Dict. to hold the node input phases for each node, if exists.
    append_input_phase = {}
    # Dict. to hold the node replacement phases for each node, if exists.
    replace_input_phase = {}
    # Dict. to hold the nodes that were killed.
    killed_nodes = {}
    # Dict. to hold the node to generate instruction line number.
    node_gen_line = {}
    # Dict. to hold the node to usage removed phase.
    removed_usage_nodes = {}
    # Dict. to hold the node to opcode.
    NodeToOpcode = {}
    # Dict. to hold the opcode address to opcode.
    OpAddressToOpcode = {}

    # List to hold the input nodes.
    input_nodes = []
    # Temporary holder for initial bytecode nodes.
    bytecode_nodes = []

    # Flag list for AppendInput - If both are True, then both nodes are collected.
    append_completed = [False,False]
    # Flag list for ReplaceInput - If all three are True, then all nodes are collected.
    replace_completed = [False,False,False,False]
    # Flag to indicate whether node kill has completed or not.
    node_kill_completed = [False]
    # Flag to indicate whether node's usage was removed or not.
    remove_use_completed = [False]

    # Variable to hold currently handling node address.
    current_node = [None]
    # Variable to hold the target node that a new input will be added.
    target_node = [None]
    # Variable to hold the node that will be appended to the target node.
    append_node = [None]
    # Variable to hold the node that will have input node replacement.
    main_node = [None]
    # Variable to hold the node in the input list to be replaced.
    from_node = [None]
    # Variable to hold the node that will replace the from_node.
    to_node = [None]
    # instruction line holders for assert.
    target_line = [None]
    # Previous function name holder
    prev_function = [None]
    append_line = [None]
    from_node_line = [None]
    main_node_line = [None]
    to_node_line = [None]
    
    # Variable to hold the current opcode.
    current_op = None
    # Variable to hold the current opcode address.
    current_addr = None

    # A unique id tracker assigned to each phase.
    phase_id = 0
    id_to_phase = {}
    node_to_phase_id = {}

    line_number = start_from
    for line in lines[start_from:end_at]:
        re_inst = IREST.instruction_splitter(line)

        # Get current phase.
        phase = get_current_phase(line_number, phase_scopes)
        
        # Assign id numbers to each phases in a sequential order.
        if phase:
            if phase_id not in id_to_phase:
                id_to_phase[phase_id] = phase
            elif phase_id in id_to_phase and id_to_phase[phase_id] != phase:
                phase_id += 1
                id_to_phase[phase_id] = phase
        else:
            pass

        # Populate OpAddressToOpcode dictionary.
        NTO.address_to_opcode(re_inst, OpAddressToOpcode)

        function = re_inst[2]
        if function == FL.NEWNODE_STR or function == FL.NEWNODEUNCHECKED_STR:
            new_op, new_addr = NTO.get_opcode(re_inst, line, OpAddressToOpcode)
            if new_op:
                # If current_op already exists, we replace the value of current_op with the new_op.
                # This is because of the assumption that the last opcode appeared is the opcode
                # for currently generating node.
                current_op = new_op
                current_addr = new_addr
        elif function == FL.CLONENODE_STR:
            org_node = NTO.get_clone_node(re_inst, line, NodeToOpcode)
            if org_node:
                current_op = NodeToOpcode[org_node][0]
                current_addr = NodeToOpcode[org_node][1]
        elif function == FL.NEW_STR:
            assert current_op, f"ERROR: current_op is None - {line}"
            input_nodes, bytecode_nodes = new_node_gen(
                                            re_inst, line, input_nodes, initial_nodes, bytecode_nodes,
                                            node_and_inputs, current_node, new_node_map, phase,
                                            node_to_phase, phase_to_nodes, line_number, node_gen_line,
                                            node_to_phase_id, phase_id
            )
            if re_inst[4]['asm_inst'][0] == "ret":
                assert current_node[0], f"ERROR: current_node[0] is None - {line}"
                NodeToOpcode[current_node[0]] = [current_op, current_addr]
                current_op = None
                current_addr = None
        elif function == FL.APPENDINPUT:
            append_input(
                re_inst, line, append_completed, target_node,
                append_node, target_line, append_line, node_and_inputs,
                phase, append_input_phase, phase_id
            )
        elif function == FL.REPLACEINPUT:
            replace_input(
                re_inst, line, replace_completed, main_node, main_node_line, to_node,
                to_node_line, from_node, from_node_line, new_node_map, node_and_inputs,
                phase, replace_input_phase, phase_id
            )
        elif function == FL.NODEKILL:
            node_kill(re_inst, killed_nodes, node_kill_completed, node_and_inputs, phase, phase_id)
        elif function == FL.REMOVEUSE:
            removeuse(re_inst, removed_usage_nodes, remove_use_completed, node_and_inputs, phase, phase_id)
        elif function == FL.APPENDUSE:
            pass

        line_number += 1
        prev_function[0] = function

    return (
            node_and_inputs, append_input_phase, replace_input_phase,
            killed_nodes, removed_usage_nodes, phase_to_nodes, node_to_phase,
            NodeToOpcode, node_gen_line, id_to_phase, node_to_phase_id
    )

def removeuse(
        re_inst: list, removed_usage_nodes: dict, remove_use_completed: list,
        node_and_inputs: dict, phase: str, phase_id: int
):
    """This function identifies an instruction that node is still alive,
    but the usage of it has been removed that the node will not be
    translated into an optimised code instruction(s).

    args:
        re_inst (list): restructured trace line.
        removed_usage_nodes (dict): holder for nodes that was removed with the usage.
        remove_use_completed (list): boolean holder list.
        node_and_inputs (dict): dictionary of node and its input node list.
        phase (str): current phase.

    returns:
        None.
    """

    X86Op = re_inst[3]
    asm_inst = re_inst[4]["asm_inst"]
    rw_insts = re_inst[5:]

    if asm_inst[0] == "add" and asm_inst[1][0] == "rdi" and not remove_use_completed[0]:
        value = get_value(rw_insts, "r", "rdi")
        if value in node_and_inputs:
            removed_usage_nodes[value] = [phase, phase_id]
        remove_use_completed[0] = True
    elif X86Op == X86.RET[1]:
        remove_use_completed[0] = False

def node_kill(
        re_inst: list, killed_nodes: dict, node_kill_completed: list,
        node_and_inputs: dict, phase: str, phase_id: int
):
    """This function handles node kill instructions.

    args:
        re_inst (list): restructured instruction.
        killed_nodes (dict): dictionary of killed nodes mapped with phase that it was killed.
        node_kill_completed (list): flag holder.
        node_and_inputs (dict): dictionary of node and its input node list.
        phase (str): current phase.

    returns:
        None.
    """

    X86Op = re_inst[3]
    asm_inst = re_inst[4]["asm_inst"]
    rw_insts = re_inst[5:]

    if asm_inst[0] == "mov" and "rdi" in asm_inst[1][1] and not node_kill_completed[0]:
        value = get_value(rw_insts, "r", "rdi")
        if value in node_and_inputs:
            killed_nodes[value] = [phase, phase_id]
        node_kill_completed[0] = True
    elif X86Op == X86.RET[1]:
        node_kill_completed[0] = False


def new_node_gen(
                    re_inst: list, line: str, input_nodes: list, initial_nodes: list, bytecode_nodes: list,
                    node_and_inputs: dict, current_node: list, new_node_map: dict, phase: str,
                    node_to_phase: dict, phase_to_nodes: dict, line_number: int, node_gen_line: dict,
                    node_to_phase_id: dict, phase_id: int
):
    """This function handles new node generation instructions.

    args:
        re_inst (list): restructured instruction.
        input_nodes (list): list of input nodes.
        initial_nodes (list): list of initial bytecode node addresses.
        bytecode_nodes (list): list of initial bytecode nodes that are input to the new node.
        node_and_inputs (dict): dictionary of node and its input node list.
        current_node (list): current new node.
        new_node_map (dict): dictionary holding weired instruction's node adddresses.
        phase (str): current phase name.
        node_to_phase (dict): generated node-to-phase dictionary.

    returns:
        (list, list) list of input nodes and list of bytecode nodes in input nodes list.
    """

    X86Op = re_inst[3]
    asm_inst = re_inst[4]["asm_inst"]
    rw_insts = re_inst[5:]

    if X86Op in ARGUMENT_PUSHES:
        get_input_nodes_from_parameter(
                                        re_inst, input_nodes, initial_nodes,
                                        bytecode_nodes, node_and_inputs)
    elif asm_inst[0] == "mov" and "ptr" in asm_inst[1][0]:
        # Across all versions of V8, input attachments are done with a memory write
        # operation, so analyse the instruction if it has such operation.
        get_input_nodes(re_inst, input_nodes, bytecode_nodes, node_and_inputs, initial_nodes) 
    elif asm_inst[1][0] == "rax":
        # If writing some value into rax register, grap that value as it is
        # a candidate of new node address. The last write before returning
        # from the Node::New function is the node address, so we update until then.
        get_new_node(current_node, re_inst, line, new_node_map)
    elif X86Op in X86.RET:
        input_nodes, bytecode_nodes = complete_node_gen(
                                        current_node, initial_nodes, bytecode_nodes,
                                        input_nodes, node_and_inputs, node_to_phase,
                                        phase_to_nodes, phase, line_number, node_gen_line,
                                        node_to_phase_id, phase_id
        )
    return input_nodes, bytecode_nodes

def get_input_nodes_from_parameter(
                                    re_inst: list, input_nodes: list, initial_nodes: list,
                                    bytecode_nodes: list, node_and_inputs: dict
):
    """This function collects the input nodes that are passed to the New function
    via function parameter.

    args:
        re_inst(list): restructured instruction line.
        input_nodes(list): list of input nodes.
        initial_nodes(list): list of initial bytecode node addresses.
        bytecode_nodes(list): list of initial bytecode nodes that are input to the new node.
        node_and_inputs(dict): dictionary of node and its input node list.

    returns:
        None.
    """

    X86Op = re_inst[3]
    asm_inst = re_inst[4]["asm_inst"]
    rw_insts = re_inst[5:]
    
    # Get the register name to obtain the value from.
    reg = None
    if X86Op == ARGUMENT_PUSHES[0]:
        reg = "r12"
    elif X86Op == ARGUMENT_PUSHES[1]:
        reg = "r13"
    elif X86Op == ARGUMENT_PUSHES[2]:
        reg = "r14"
    elif X86Op == ARGUMENT_PUSHES[3]:
        reg = "r15"
    assert (
            reg
    ), f"ERROR: Register (reg) is empty - {line}"

    # Check if newly generated node has a direct parent.
    # If the retrieved value is in the previously generated
    # node list, then the value is a node and direct parent.
    value = get_value(rw_insts, "r", reg)
    # Only previously generated nodes can be an input node.
    if (
            value in node_and_inputs
            and value not in input_nodes
    ):
        input_nodes.append(value)
        # If input node is an initial bytecode node, then hold it.
        if value in initial_nodes:
            bytecode_nodes.append(value)

def get_input_nodes(
                    re_inst: list, input_nodes: list, bytecode_nodes: list,
                    node_and_inputs: dict, initial_nodes: list
):
    """This function collects all input nodes to the newly generated node.

    args:
        re_inst (list): restructured instruction line.
        input_nodes(list): list of input nodes.
        initial_nodes(list): list of initial bytecode node addresses.
        bytecode_nodes(list): list of initial bytecode nodes that are input to the new node.
        node_and_inputs(dict): dictionary of node and its input node list.

    returns:
        None.
    """
    rw_insts = re_inst[5:]

    # Get the input node address and store to input_node variable.
    # Then, append to input_nodes list.
    value = get_value(rw_insts, "mw", None)
    # Only previously generated nodes can be an input node.
    if (
            value in node_and_inputs
            and value not in input_nodes
    ):
        input_nodes.append(value)
        # If input node is an initial bytecode node, then hold it.
        if value in initial_nodes:
            bytecode_nodes.append(value)

def get_new_node(current_node: list, re_inst: list, line: str, new_node_map: dict):
    """This function identify and collect new node address.

    args:
        current_node (list): current new node.
        re_inst (list): restructured instruction line.
        new_node_map (dict): dictionary holding weired instruction's node adddresses.

    returns:
        None.
    """

    asm_inst = re_inst[4]["asm_inst"]
    rw_insts = re_inst[5:]

    # Get the generated node address and store to current_node variable.
    try:
        if len(asm_inst[1]) > 1:
            read_from = asm_inst[1][1]
        else:
            read_from = asm_inst[1][0]
    except:
        assert (
                False
        ), f"ERROR: list out of range - {line} - {asm_inst}"

    if "ptr" in read_from:
        r_value = get_value(rw_insts, "mr", None)
    else:
        r_value = get_value(rw_insts, "r", read_from)

    w_value = get_value(rw_insts, "w", "rax")
    current_node[0] = w_value
    if w_value and r_value != w_value:
       new_node_map[r_value] = w_value
    if not current_node[0] and asm_inst[0] == "push":
        current_node[0] = r_value
    # BELOW EXPLANATION DOES NOT APPLY IF WE RUN D8 WITH --single-threaded flag on.
    # I suspect there is a tracing tool issues that read and write values differ
    # (e.g. mov rax, rcx; R:RCX=00007f5494007ea8 W:RAX=00005600cc254670), and I've
    # verified that read value is the correct node address, so I'm storing read
    # value to current_node variable and but mapping w_value with r_value as a record.
    # current_node[0] = r_value
    # if r_value != w_value:
    #    new_node_map[w_value] = r_value

    assert (current_node[0]), f"ERROR: current_node is empty - {line} - {read_from}"

def complete_node_gen(
                        current_node: list, initial_nodes: list, bytecode_nodes: list,
                        input_nodes: list, node_and_inputs: dict, node_to_phase: dict,
                        phase_to_nodes: dict, phase: str, line_number: int, node_gen_line: dict,
                        node_to_phase_id: dict, phase_id: int
):
    """This function add new node to node_and_inputs dict as key and input_nodes
    as key's value.

    args:
        current_node (list): new node that newly generated.
        initial_nodes (list): initial bytecode nodes.
        bytecode_nodes (list): initial bytecode node in the input nodes.
        input_nodes (list): input nodes to the new node.
        node_and_inputs(dict): dictionary of node and its input node list.
        node_to_phase (dict): generated node-to-phase dictionary.
        phase (str): current phase name.

    returns:
        (list, list) empty lists.
    """

    # If current_node is an initial node, then we do not want
    # to keep the previous bytecode node as an input node.
    # Thus, we remove them from the input_nodes list.
    if current_node[0] in initial_nodes and bytecode_nodes:
        for node in bytecode_nodes:
            input_nodes.remove(node)

    # Populate node_and_inputs dictionary.
    node_and_inputs[current_node[0]] = input_nodes
    assert (
            phase
            ), f"ERROR: Phase cannot be None if a\
                \nnew node is being generated.\
                \nline number: {line_number}"

    # Populate phase_to_nodes dictionary.
    if phase not in phase_to_nodes:
        phase_to_nodes[phase] = [current_node[0]]
    else:
        phase_to_nodes[phase].append(current_node[0])
    # Populate node_to_phase dictionary.
    if current_node[0] not in node_to_phase:
        node_to_phase[current_node[0]] = phase
    # Populate node_gen_line dictionary
    if current_node[0] not in node_gen_line:
        node_gen_line[current_node[0]] = line_number
    if current_node[0] not in node_to_phase_id:
        node_to_phase_id[current_node[0]] = phase_id

    # Reset temporary holders to their default.
    # current_node[0] = None

    return [], []

def append_input(
                re_inst: list, line: str, append_completed: list,
                target_node: list, append_node: list, target_line: str,
                append_line: str, node_and_inputs: dict,
                phase: str, append_input_phase: dict, phase_id: int
):
    """This function handled input appending instructions and update
    node_and_inputs dictionary.

    args:
        re_inst (list): restructured instruction.
        line (str): raw instruction string.
        append_completed (list): flag list.
        target_node (list): node to append input.
        append_node (list): node that will be appended.
        target_line (str): line that target node was collected.
        append_node (str): line that append node was collected.
        node_and_inputs(dict): dictionary of node and its input node list.
        phase (str): current phase name.
        append_input_phase (dict): append input occured phase dictionary.

    returns:
        None.
    """

    X86Op = re_inst[3]
    asm_inst = re_inst[4]["asm_inst"]
    rw_insts = re_inst[5:]

    if (
            asm_inst[0] == "mov"
            and asm_inst[1][1] == "rdi"
            and not append_completed[0]
    ):
        # Identify the target node that the function is trying to
        # append new node to. Then, get the node address and store
        # it into the temp. holder. We can identify by finding the
        # very first 'rdi' read.
        target_node[0] = get_value(rw_insts, "r", "rdi")
        append_completed[0] = True
        target_line[0] = line
    elif (
            asm_inst[0] == "mov"
            and asm_inst[1][1] == "rdx"
            and not append_completed[1]
    ):
        # Identify the append node that the function is trying to
        # append to the target node. Then, get the node address and store
        # it into the temp. holder. We can identify by finding the very
        # first 'rdx' read.
        append_node[0] = get_value(rw_insts, "r", "rdx")
        append_completed[1] = True
        append_line[0] = line
    elif X86Op == X86.RET[1]:
        assert (
                target_node[0]
                and target_node[0] in node_and_inputs
        ), f"ERROR: target_node [{target_node[0]}] is not in\
             \nnode_and_inputs dictionary - {target_line[0]}\
             \n{list(node_and_inputs.keys())}"
        assert (
                append_node[0]
                and append_node[0] in node_and_inputs
        ), f"ERROR: append_node [{append_node[0]}] is not in\
             \nnode_and_inputs dictionary - {append_line[0]}"

        # Append node to the target node's input list.
        if append_node[0] not in node_and_inputs[target_node[0]]:
            node_and_inputs[target_node[0]].append(append_node[0])
            # Keep track at which phase a new input was appended.
            info = [phase, append_node[0], phase_id]
            if target_node[0] in append_input_phase:
                append_input_phase[target_node[0]].append(info)
            else:
                append_input_phase[target_node[0]] = [info]

        # Reset flag list.
        append_completed[0] = False
        append_completed[1] = False

def replace_input(
                 re_inst: list, line: str, replace_completed: list,
                 main_node: list, main_node_line: list, to_node: list,
                 to_node_line: list, from_node: list,
                 from_node_line: list, new_node_map: list,
                 node_and_inputs: list, phase: str,
                 replace_input_phase: dict, phase_id: int
):
    """This function handles replace input instructions.

    args:
        re_inst (list): restructured instruction.
        line (str): raw instruction line.
        replace_completed (list): flag list.
        main_node (list): node to replace input.
        main_node_line (str): line where main node was collected.
        to_node (list): node to replace.
        to_node_line (list): line where replace node was collected.
        from_node (list): node to be replaced.
        from_node_line (list): line where node to be replaced was collected.
        new_node_map (dict): dictionary holding weired instruction's node adddresses.
        node_and_inputs (dict): dictionary of node and its input node list.
        phase (str): current phase name.
        replace_input_phase (dict): phase where input node was replaced.

    returns:
        None.
    """

    X86Op = re_inst[3]
    asm_inst = re_inst[4]["asm_inst"]
    rw_insts = re_inst[5:]

    if X86Op == X86.PUSH_RBP:
        if (
                replace_completed[0]
                and replace_completed[1]
                and replace_completed[2]
                and not replace_completed[3]
        ):
            finalise_replace(
                    main_node, from_node, to_node,
                    new_node_map, node_and_inputs, replace_input_phase,
                    phase, phase_id
            )
            replace_completed[3] = True
        # Reset flag list.
        replace_completed[0] = False
        replace_completed[1] = False
        replace_completed[2] = False
        replace_completed[3] = False
    elif asm_inst[0] == "mov" and "rdi" in asm_inst[1][1] and not replace_completed[0]:
        main_node[0] = get_value(rw_insts, "r", "rdi")
        replace_completed[0] = True
        main_node_line[0] = line
    elif asm_inst[0] == "mov" and asm_inst[1][1] == "rdx" and not replace_completed[1]:
        to_node[0] = get_value(rw_insts, "r", "rdx")
        replace_completed[1] = True
        to_node_line[0] = line
    elif X86Op == FROMNODE and not replace_completed[2]:
        from_node[0] = get_value(rw_insts, "mr", None)
        replace_completed[2] = True
        from_node_line[0] = line
    elif X86Op == X86.RET[1]:
        finalise_replace(
                main_node, from_node, to_node, new_node_map,
                node_and_inputs, replace_input_phase, phase,
                phase_id
        )
        replace_completed[3] = True

def finalise_replace(
        main_node: list, from_node: list, to_node: list,
        new_node_map: dict, node_and_inputs: dict, replace_input_phase: dict,
        phase: str, phase_id: int
):
    """This function finalises replacing input nodes.

    args:
        main_node (list): node to replace input.
        from_node (list): node to be replaced.
        to_node (list): node to replace.
        new_node_map (dict): dictionary holding weired instruction's node adddresses.
        node_and_inputs (dict): dictionary of node and its input node list.
        replace_input_phase (dict): phase where input node was replaced.
        phase (str): current phase name.
    
    returns:
        None.
    """
    assert (
            main_node[0]
            and main_node[0] in node_and_inputs
    ), f"ERROR: main_node [{main_node[0]}] is not in node_and_inputs dictionary - {main_node_line}"

    assert (
            from_node[0]
            and from_node[0] in node_and_inputs
    ), f"ERROR: from_node [{from_node[0]}] is not in node_and_inputs\
            \n- {from_node_line[0]}"
    # To handle tracing tool's read & write value difference issue, check if the noded
    # exists in the node_and_inputs dictionary. If yes, then replace the to_node value
    # with the dictionary's value.
    if to_node[0] not in node_and_inputs:
        assert (
                to_node[0] in new_node_map
        ), f"ERROR: to_noed is neither in node_and_inputs and new_node_map - {to_node_line[0]}"
        to_node[0] = new_node_map[to_node]
    assert (
            to_node[0]
            and to_node[0] in node_and_inputs
    ), f"ERROR: to_node [{to_node[0]}] is not in node_and_inputs dictionary - {to_node_line[0]}"

    info = [phase, None, None, phase_id]
    # Not all nodes are part of the input nodes. Thus, remove them
    # only if they exist in the list.
    if from_node[0] in node_and_inputs[main_node[0]]:
        node_and_inputs[main_node[0]].remove(from_node[0])
        info[1] = from_node[0]
    if to_node[0] not in node_and_inputs[main_node[0]]:
        node_and_inputs[main_node[0]].append(to_node[0])
        info[2] = to_node[0]
        if main_node[0] in replace_input_phase:
            replace_input_phase[main_node[0]].append(info)
        else:
            replace_input_phase[main_node[0]] = [info]

def get_value(rw_insts: list, op: str, reg: str):
    """This function finds the requested value from
    the memory or register read/write instructions.

    args:
        op (str): represents either read (r) or write (w) operation.
        reg (str): name of register to seek.

    returns:
        (str) found address.
    """

    value = None
    if reg:
        for inst in rw_insts:
            if inst[0] == op and inst[1] == reg:
                value = inst[2]
    else:
        for inst in rw_insts:
            if inst[0] == op:
                value = inst[2]

    return value

def compose_all_paths(node_and_inputs: dict):
    """This function composes paths from given node
    , as leaf, to the root node.

    args:
        node_and_inputs (dict): generated node and its input nodes map.

    returns:
        (dict) Paths of all nodes.
    """
    
    AllPaths = {}

    for node, inputs in node_and_inputs.items():
        paths = {}
        paths[node] = inputs
        AllPaths[node] = get_node_paths(paths[node], node, node_and_inputs, paths)
    
    return AllPaths

def get_node_paths(input_nodes: list, node: str, node_and_inputs: dict, paths: dict):
    """This function recursively scans and find paths of main node and its input
    nodes.

    args:
        input_nodes (list): list of input nodes of node.
        node (str): Address of node.
        node_and_inputs (dict): dictionary of all nodes and their input nodes.
        paths (dict): dictionary of node and paths.

    returns:
        (dict) structured paths node nodes.
    """

    if not input_nodes:
        return paths
    else:
        for nd in input_nodes:
            if nd not in paths:
                paths[nd] = node_and_inputs[nd]
                get_node_paths(paths[nd], nd, node_and_inputs, paths)

    return paths

def get_current_phase(line_number: int, phase_scopes: dict):
    """This function identifies the optimisation phase, if
    any, that the current trace line instruction belongs.
    Then, it returns the phase name.

    args:
        line_number (int): trace line number of current
        trace instruction.
        phase_scopes (dict): a dictionary holding scope
        information of each optimisation phase.

    returns:
        (str) current phase name that the instruction belongs.
        (None) if current line is not within any phase scope.
    """
    
    for phase, scopes in phase_scopes.items():
        assert (
                len(scopes) % 2 == 0
        ), f"ERROR: Scope length for phase [{phase}] is odd - [{scopes}]"
        for i in range(0, len(scopes), 2):
            if line_number > scopes[i] and line_number < scopes[i+1]:
                return phase

    return None

def RerepresentGraph(Graph: dict):
    """This function assigns unique numbers to each node to re-represent the graph
    from hex node address so that we can compare multiple graphs accordingly.

    args:
        Graph (dict): Target graph to re-represent.

    returns:
        (dict) dictionary of re-represented graph.
    """

    Addr_to_Num = {}
    Rest_Graph = {}
    
    counter = 0
    for node, inputs in Graph.items():
        Addr_to_Num[node] = counter
        Rest_Inputs = []
        for ipt in inputs:
            if ipt in Addr_to_Num:
                Rest_Inputs.append(Addr_to_Num[ipt])
        Rest_Graph[counter] = Rest_Inputs
        counter += 1

    return Rest_Graph, Addr_to_Num

def group_phases(id_to_phases: dict):
    """This function groups phases by group id to phase ids.

    args:
        id_to_phases (dict): phase id to phase name dictionary.

    returns:
        (dict) grouped phase dictionary.
    """

    group_id = -1
    grouped_phases = {}
    is_new_group = False

    for id, phase in id_to_phases.items():
        if not is_new_group and phase == FL.GRAPHBUILDERPHASE:
            is_new_group = True
            group_id += 1
        elif is_new_group:
            is_new_group = False

        if group_id not in grouped_phases:
            grouped_phases[group_id] = [id]
        else:
            grouped_phases[group_id].append(id)

    return grouped_phases

# =============================================================================================

def restructure_dict(node_and_inputs: dict):
    """This function is not related to other analysis functions.
    This function is to restucture dictionary to have a form
    that is suitable for a NetworkX to draw a graph.

    args:
        node_and_inputs (dict): dictionary holding node and input nodes.

    retuns:
        (dict) restuctured dictionary.
    """

    restructured_dict = {"nodes":[]}
    for node, inputs in node_and_inputs.items():
        if inputs:
            for inode in inputs:
                src = inode.lstrip('0')
                des = node.lstrip('0')
                if src and des:
                    linked_nodes = [f"0x{src}", f"0x{des}"]
                    restructured_dict["nodes"].append(linked_nodes)

    return restructured_dict


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
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-f",
        "--file",
        type=str,
        help="An input trace file."
    )
    parser.add_argument(
        "-d",
        "--directory",
        type=str,
        help="Directory where all generated files will be stored."
    )
    args = parser.parse_args()

    return args.file, args.directory

# =============================================================================================

if __name__ == "__main__":
    filename, directory = argument_parser()
    V8_VERSION = "8.2.297.3"
    
    # Read in the lines in trace file.
    lines = read_file(filename)
    # Get each phase scope.
    phase_scopes, has_exception, line_number, first_and_last = PI.phase_identifier(lines)
    
    # Load initial nodes list.
    initial_nodes = None
    with open ("initial_nodes.json") as json_f:
        initial_nodes = json.load(json_f)
    print ("Initial Nodes============")
    print (initial_nodes)
    print ("=========================\n")

    # Identify all nodes and their input nodes for graph generation.
    (
            node_and_inputs,
            append_input_phase,
            replace_input_phase,
            killed_nodes,
            removed_usage_nodes,
            phase_to_nodes,
            node_to_phase,
            node_to_opcode,
            node_gen_line,
            id_to_phase,
            node_to_phase_id
    ) = graph_former(
            lines,
            0,
            first_and_last[1],
            initial_nodes["nodes"],
            phase_scopes
        )

    # Group phase ids.
    grouped_phases = group_phases(id_to_phase)

    # All print outs
    print ("Phase IDs: ")
    for id, phase in id_to_phase.items():
        print (id, phase)
    print ("=========================\n")
    print ("Grouped Phases: ")
    for group_id, phase_ids in grouped_phases.items():
        print (group_id, phase_ids)
    print ("=========================\n")
    print ("All Nodes and Inputs=====")
    print ("Total number of generated nodes: ", len(node_and_inputs))
    for node in node_and_inputs:
        print (node.lstrip('0'))
    print ("=========================\n")
    phase_id_to_phase = {}
    for node, input_nodes in node_and_inputs.items():
        phase = node_to_phase[node]
        phase_id = node_to_phase_id[node]
        print ("Node: ", node, ", Inputs: ", input_nodes,
               ", Phase: ", phase,
               ", Phase ID: ", phase_id
        )
        if node in append_input_phase:
            print ("Input append info: ", append_input_phase[node])
        if node in replace_input_phase:
            print ("Input replace inof: ", replace_input_phase[node])

        if phase_id not in phase_id_to_phase:
            phase_id_to_phase[phase_id] = phase
    print ("=========================\n")
    print ("Node Generated Phases: ")
    for phase_id, phase in phase_id_to_phase.items():
        print (phase_id, phase)
    print ("=========================\n")
    print ("Killed Nodes=============")
    for node, phase in killed_nodes.items():
        print (f"Node: {node} Killed at Phase {phase}")
    print ("=========================\n")
    print ("Removed Use Nodes=============")
    for node, phase in removed_usage_nodes.items():
        #print (f"Node: {node} usage removed at Phase {phase}")
        print (f"{phase}")
    print ("=========================\n")
    print ("All Paths================\n")
    final_to_init = {}
    AllPaths = compose_all_paths(node_and_inputs)
    for node, paths in AllPaths.items():
        print ("Node: ", node)
        for input_node, path in paths.items():
            print (input_node, path)
    print ("=========================")

    # Write and save data to files.
    restructured_dict = restructure_dict(node_and_inputs)
    with open(f"{directory}/Graph.json", "w") as json_file:
        json.dump(node_and_inputs, json_file)
    with open(f"{directory}/PhaseToNodes.json", "w") as json_file:
        json.dump(phase_to_nodes, json_file)
    with open(f"{directory}/NodeToPhase.json", "w") as json_file:
        json.dump(node_to_phase, json_file)
    with open(f"{directory}/AppendInputs.json", "w") as json_file:
        json.dump(append_input_phase, json_file)
    with open(f"{directory}/ReplaceInputs.json", "w") as json_file:
        json.dump(replace_input_phase, json_file)
    with open(f"{directory}/KilledNodes.json", "w") as json_file:
        json.dump(killed_nodes, json_file)
    with open(f"{directory}/RemoveUsage.json", "w") as json_file:
        json.dump(removed_usage_nodes, json_file)
    with open(f"{directory}/Data.json", "w") as json_file:
        json.dump(restructured_dict, json_file)
    with open(f"{directory}/RawData.json", "w") as json_file:
        json.dump(AllPaths, json_file)
    with open(f"{directory}/NodeToOpcode.json", "w") as json_file:
        json.dump(node_to_opcode, json_file)
