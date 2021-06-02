"""
"""
import os
import sys

# Code to import modules from other directories.
# Soruce: https://codeolives.com/2020/01/10/python-reference-module-in-parent-directory/
currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)

import FunctionLists as FL
import X86ASM as X86

class Graph:
    def __init__(self):
        self.id = -1
        self.nodes = []
        self.size = 0
        self.phase_to_nodes = {}
        self.id_to_nodes = {}
        self.id_to_phase = {}
        self.grouped_phases = {}

class Node:
    def __init__(self):
        self.id = -1
        self.address = None
        self.phase = None
        self.phase_id = -1
        self.inputs = []
        self.replaced_inputs = {}
        self.killed_at = []
        self.removed_usage_at = []
        self.append_inputs = []
        self.opcode = []
        self.difference_id = -1
        self.graph_id = -1

def GroupPhases(id_to_phases: dict):
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

def RestructureGraph(Org_Graph: list, filenumber: str):
    """This function received a list of multiple data structures, which
    represent a graph, and restructure them to a class object graph.

    args:
        Org_Graph (list): a list of multiple data structures representing
        a graph.

        NodeInputs    = Org_Graph[0]
        AppendInputs  = Org_Graph[1]
        ReplaceInputs = Org_Graph[2]
        KilledNodes   = Org_Graph[3]
        RemovedUsage  = Org_Graph[4]
        PhaseToNodes  = Org_Graph[5]
        NodeToPhase   = Org_Graph[6]
        NodeToOpcode  = Org_Graph[7]
        NodeToLine    = Org_Graph[8]
        IdToPhase     = Org_Graph[9]
        NodeToPhaseId = Org_Graph[10]

    returns:
        (Graph) restructured graph object. 
    """

    Re_Graph = Graph()
    Re_Graph.id = int(filenumber)
    Re_Graph.phase_to_nodes = Org_Graph[5]
    Re_Graph.id_to_phase = Org_Graph[9]

    Re_Graph.grouped_phases = GroupPhases(Org_Graph[9])

    AddressToNode = {}
    
    for node_addr, inputs in Org_Graph[0].items():
        # Generate a new node object and populate data.
        node = Node()
        node.id = Re_Graph.size
        node.address = node_addr
        node.inputs = inputs
        node.input_length = len(inputs)
        node.graph_id = int(filenumber)
        if node_addr in Org_Graph[1]:
            node.append_inputs = Org_Graph[1][node_addr]
        if node_addr in Org_Graph[2]:
            node.replaced_inputs = Org_Graph[2][node_addr]
        if node_addr in Org_Graph[3]:
            node.killed_at = Org_Graph[3][node_addr]
        if node_addr in Org_Graph[4]:
            node.removed_usage_at = Org_Graph[4][node_addr]
        node.phase = Org_Graph[6][node_addr]
        node.opcode = Org_Graph[7][node_addr]
        node.phase_id = Org_Graph[10][node_addr]
        # Add constructed node to graph object.
        Re_Graph.nodes.append(node)
        Re_Graph.size += 1
        # Populate AddressToNode dictionary.
        AddressToNode[node_addr] = node

        if node.phase_id not in Re_Graph.id_to_nodes:
            Re_Graph.id_to_nodes[node.phase_id] = [node]
        else:
            Re_Graph.id_to_nodes[node.phase_id].append(node)
    
    for node in Re_Graph.nodes:
        # If the node has input nodes, replace the list content from
        # only addresses in string to actual node objects.
        if node.inputs:
            _inputs = []
            for input_addr in node.inputs:
                assert (
                        type(input_addr) == str
                ), f"ERROR: input_addr = {input_addr.address}"
                ipt_node = AddressToNode[input_addr]
                _inputs.append(ipt_node)
            node.inputs = _inputs

    return Re_Graph

def RestructureGraphs(Graphs: list):
    """
    """

    restructured_graphs = []

    for filenumber, graph in Graphs.items():
        restructured_graph = RestructureGraph(graph, filenumber)
        # 0th index must hold the original graph.
        if filenumber == '0':
            restructured_graphs.insert(0, restructured_graph)
        else:
            restructured_graphs.append(restructured_graph)

    return restructured_graphs
