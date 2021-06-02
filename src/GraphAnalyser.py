"""
This program analyses multiple graphs and compute the differences among them. Then,
it list out the phases that are candidates for bug location.

For example,
    let's say we have G = {G1, G2, G3, G4, G5, G6, G7, G8, G9}, where G1 is a graph
    from the original PoC, G2 - G6 are graphs from incorrectly executed PoC, and
    G7 - G9 are graphs from correctly executed PoC.

                                  |G2|G3|G4|G5|G6
                                G7|11|12|02|08|17
                                G8|13|07|09|12|16
                                G9|07|04|06|22|21

    The numbers represent the number of phase differences between two graphs.
    With the table, we find the graphs with the minimum differences. This is because
    it represents two graphs are (1) both 1 edit difference from the original graph,
    (2) the closest computation, (3) have clear unique differences that make one
    PoC to execute correctly while incorrectly for another, and (4) we can minimise
    the candidates for bugs. Graph G7 and G4 has only two phase differences between two.

Author: Terrence J. Lim
"""

import os, sys
import json
import argparse
import pickle
import numpy as np

# Code to import modules from other directories.
# Soruce: https://codeolives.com/2020/01/10/python-reference-module-in-parent-directory/
currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)

import FunctionLists as FL
import GraphCreator as GC

from sklearn.metrics.pairwise import cosine_similarity

# List of JSON files to open and load data from.
# The order of this list must be maintained.

NOT_OPTPHASES = [
        FL.GRAPHBUILDERPHASE,
        FL.COMPUTESCHEDULEPHASE,
        FL.OSRDECONSTRUCTIONPHASE,
]

ISSUE_ID = {
        0: "NoIssue",
        1: "Opcode",    
        2: "Input",
        3: "Phase",
        4: "RemovedUsage",
        5: "KilledAt",
        6: "NodeListSize"
}

ISSUES = {
        "NoIssue": 0,
        "Opcode": 1,    
        "Input": 2,
        "Phase": 3,
        "RemovedUsage": 4,
        "KilledAt": 5,
        "NodeListSize": 6
}

class Graph:
    def __init__(self):
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
        self.input_length = 0
        self.replaced_inputs = {}
        self.killed_at = None
        self.removed_usage_at = None
        self.append_inputs = {}
        self.opcode = []



def RestructureGraph(Org_Graph: list):
    """This function receives a list of multiple data structures, which
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
    Re_Graph.phase_to_nodes = Org_Graph[5]
    Re_Graph.id_to_phase = Org_Graph[9]

    Re_Graph.grouped_phases = GC.group_phases(Org_Graph[9])

    AddressToNode = {}
    
    for node_addr, inputs in Org_Graph[0].items():
        # Generate a new node object and populate data.
        node = Node()
        node.id = Re_Graph.size
        node.address = node_addr
        node.inputs = inputs
        node.input_length = len(inputs)
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

def GraphAnalyser(G1: Graph, G2: Graph):
    """This function analyse two graphs namely G and G'
    and compute the differences between two.

    args:
        G1 (Graph):
        G2 (Graph):

    returns:
        (dict) dictionary holding {phases:[diff. nodes]}.
    """

    ## REMOVE =======================
    PrintGraphByPhaseId(G1)
    #PrintGraphByPhaseId(G2)
    sys.exit()
    ## ==============================

    CommonPhaseIDs = CompareGraph(G1, G2)

    return CommonPhaseIDs


## GRAPH COMPARING FUNCTIONS==============================================

def CompareGraph(G1: Graph, G2: Graph):
    """This function will compare two passed graphs (G and G').

    args:
        G1 (Graph): A graph object G1.
        G2 (Graph): A graph object G2.

    returns:
        (dict) phase-to-node dictionary.
    """

    G1_Phases, G2_Phases = get_phase_order(G1.nodes, G2.nodes)
    GraphBuilderPhaseDiffNodes = CompareGraphBuilderPhase(G1, G2)

    # Find all the different nodes between two graphs within
    # the optimisation phases.
    (
        DiffNodes
    ) = CompareRemainingNodes(G1, G2, GraphBuilderPhaseDiffNodes)

    CommonPhaseIDs = ComputeEqualPhases(DiffNodes, G1_Phases)

    return CommonPhaseIDs

def CompareGraphBuilderPhase(G1: Graph, G2: Graph):
    """This function compares nodes those were generated at
    the GraphBuilderPhase in both graphs to find the differences

    args:
        G1 (Graph): A graph object G1.
        G2 (Graph): A graph object G2.

    returns:
        (dict) graph name (G or GP) to list of different nodes. 
    """

    # Dictionary to hold the result.
    DiffNodes = {'G1':[], 'G2':[]}

    # Gen the list of nodes generated at graph builder phase from
    # each graph. GBP: GraphBuilderPhase.
    V1_GBP = get_nodes(G1.nodes, G1.phase_to_nodes, FL.GRAPHBUILDERPHASE)
    V2_GBP = get_nodes(G2.nodes, G2.phase_to_nodes, FL.GRAPHBUILDERPHASE)

    # 1. Identify and collect all nodes in V1 those are different from V2.
    FindDiffNodesByPhase(
            V1_GBP, V2_GBP, len(V1_GBP), len(V2_GBP), DiffNodes['G1']
    )
    # 2. Identify and collect all nodes in V2 those are different from V1.
    FindDiffNodesByPhase(
            V2_GBP, V1_GBP, len(V2_GBP), len(V1_GBP), DiffNodes['G2']
    )

    return DiffNodes

def FindDiffNodesByPhase(
        V1: list, V2: list,
        End1: int, End2: int,
        DiffNodes: list
):
    """This function compares sequence of nodes in one graph to another
    and finds the nodes that are either different or not appearing.

    args:
        V1 (list): list of nodes in vertex list V1.
        V2 (list): list of nodes in vertex list V2.
        End1 (int): end number that will be used in the first for loop.
        End2 (int): end that will be used in the first for loop.
        DiffNodes (list): a list where found different nodes will
        be stored.

    returns:
        None.
    """

    l = 0
    # Traverse nodes (v) in V1 sequentially.
    for i in range(0, End1):
        v1_i = V1[i]
        is_equal = False
        # While sequentially traversing the v1 in V1, find the match V2.
        # If match was not found, then add v1 to the storage.
        for j in range(l, End2):
            v2_j = V2[j]
            is_equal, issue_id = CompareTwoNodes(v1_i, v2_j, [])
            if is_equal:
                l += 1
                break
        if not is_equal:
            DiffNodes.append(v1_i)

def CompareRemainingNodes(G1: Graph, G2: Graph, SkipNodes: dict):
    """
    """

    SkipNodes['G1'].extend(SkipNodes['G2'])

    DiffNodes = FindDiffNodes(G1, G2, SkipNodes['G1'])

    return DiffNodes

def FindDiffNodes(G1: Graph, G2: Graph, SkipNodes: list):
    """This function compares two graphs node-to-node by phase. Here
    are some assumptions made.

    Assumption(s):
        1. Two graphs are from same category (correct or incorrect).
        2. Both graphs (G1 & G2) have same number of phases.
        3. Two graphs' phase IDs are equal.
    """

    DiffNodes = []

    for phase_id, g1_nodes in G1.id_to_nodes.items():
        # We do not have to compare the initial IR generation phase nodes.
        if G1.id_to_phase[phase_id] == FL.GRAPHBUILDERPHASE:
            continue

        assert (
                phase_id in G2.id_to_nodes
        ), f"ERROR: Phase ID {phase_id} is not in Grouped_G2."

        g2_nodes = G2.id_to_nodes[phase_id]
        DiffNodes.extend(CompareNodeLists(g1_nodes, g2_nodes, SkipNodes))
        DiffNodes.extend(CompareNodeLists(g2_nodes, g1_nodes, SkipNodes))

    return DiffNodes

def CompareNodeLists(V1: list, V2: list, SkipNodes: list):
    """
    """

    DiffNodes = []

    end_1 = len(V1)
    end_2 = len(V2)

    last_found = 0
    issue_id = -1
    is_equal = False

    for i in range(0, end_1):
        if V1[i].address in SkipNodes:
            continue
        diff_info = {}
        for j in range(last_found, end_2):
            # Compare two nodes from two lists.
            is_equal, issue_id = CompareTwoNodes(V1[i], V2[j], SkipNodes)
            if issue_id == 6:
                SkipNodes.append(V1[i])
                break
            elif issue_id == 7:
                continue
            # If any time the same v2_j is found, then break out from
            # the loop.
            if is_equal:
                break
            elif not is_equal:
                diff_info[V1[i].address] = issue_id

        # If the same node of v1_i exists in V2 list, then we simply
        # increment last_found.
        if is_equal:
            last_found += 1
            is_equal = False
        else:
            DiffNodes.append(V1[i])
    
    return DiffNodes

def CompareTwoNodes(v1: Node, v2: Node, SkipNodes: list):
    """This function compares two nodes' properties. If they are equal
    nodes, it returns True; otherwise, False.

    args:
        v1 (Node): node from V1.
        v2 (N0de): node from V2.

    returns:
        (bool) True if two nodes are equal; otherwise, False.
    """

    # 1. Compare opcode of two nodes.
    if v1.opcode[0] != v2.opcode[0]:
        return False, 1

    # 2. Compare input nodes.
    if v1.input_length == v2.input_length:
        for i in range(0, v1.input_length):
            if v1.inputs[i].address in SkipNodes:
                return False, 6
            elif v2.inputs[i].address in SkipNodes:
                return False, 7
            # Compare the opcode of input nodes.
            if v1.inputs[i].opcode[0] != v2.inputs[i].opcode[0]:
                return False, 2
    else:
        return False, 2

    # 3. Compare the phases where two nodes were generated.
    if v1.phase != v2.phase:
        return False, 3

    # 4. Compare the phases where the nodes' usage was removed.
    if (    v1.removed_usage_at
            and v2.removed_usage_at
            and v1.removed_usage_at[0] != v2.removed_usage_at[0]
    ):
        return False, 4
    elif v1.removed_usage_at and not v2.removed_usage_at:
        return False, 4
    elif not v1.removed_usage_at and v2.removed_usage_at:
        return False, 4

    # 5. Compare the phases where the nodes' got killed.
    if (
            v1.killed_at
            and v2.killed_at
            and v1.killed_at[0] != v2.killed_at[0]
    ):
        return False, 5
    elif v1.killed_at and not v2.killed_at:
        return False, 5
    elif not v1.killed_at and v2.killed_at:
        return False, 5

    return True, 0

def ComputeEqualPhases(DiffNodes: list, PhaseOrder: list):
    """
    """
    
    PhaseIDs = []

    for node in DiffNodes:
        if node.phase not in PhaseIDs:
            PhaseIDs.append(node.phase_id)
            if (
                    node.removed_usage_at
                    and node.removed_usage_at[1]
                    not in PhaseIDs
            ):
                PhaseIDs.append(node.removed_usage_at[1])

    CommonPhaseIDs = [i for i in PhaseOrder if i not in PhaseIDs]

    return CommonPhaseIDs

def ComputeEqualIndices(DiffIdxToPhase: dict, IdxToPhase: dict):
    """
    """

    for idx in DiffIdxToPhase:
        if idx in IdxToPhase:
            IdxToPhase.pop(idx)

    return IdxToPhase

def CompareGraphByPhaseId(G1: Graph, G2: Graph, TargetPhaseIDs: list):
    """
    """

    DiffNodesById = {}

    for g1_id, g1_nodes in G1.id_to_nodes.items():
        if g1_id in TargetPhaseIDs:
            g2_nodes = G2.id_to_nodes[g1_id]
            DiffNodes = CompareNodeLists(g1_nodes, g2_nodes, [])
            if DiffNodes:
                DiffNodesById[g1_id] = DiffNodes

    return DiffNodesById


## HELPER FUNCTIONS========================================================

def get_nodes(Nodes: list, PhaseToNodes: dict, Phase: str):
    """This function scans the list of node objects to find the node object with the 
    address in the NodeAddreses list.

    args:
        Nodes (list): a list of node objects.
        PhaseToNodes (dict): phase-to-node list dictionary.
        Phase (str): target phase to retrieve nodes.

    return:
        (list) a list of found node objects.
    """

    CollectedNodes = []

    for node in Nodes:
        if node.address in PhaseToNodes[Phase]:
            CollectedNodes.append(node)
        else:
            break

    return CollectedNodes

def get_phase_order(V1: list, V2: list):
    """
    """

    G1_PhaseOrder = get_only_opt_phases(V1)
    G2_PhaseOrder = get_only_opt_phases(V2)

    return G1_PhaseOrder, G2_PhaseOrder


def get_only_opt_phases(V: list):
    """
    """

    phase_order = []

    for v in V:
        if v.phase not in NOT_OPTPHASES and v.phase_id not in phase_order:
            phase_order.append(v.phase_id)

    return phase_order

def get_last_node_id(AllPhases: list, MainPhases: list, LastNodeId: int, TargetNodeList: list):
    """
    """

    assert (
            len(TargetNodeList) > LastNodeId
    ), f"ERROR: Number of nodes in TargetNodeList ({len(TargetNodeList)})\
         \n< LastNodeId ({LastNodeId})."

    last_node_id = 0
    for phase in MainPhases:
        for node in TargetNodeList:
            if node.phase == phase:
                last_node_id += 1
            else:
                break

    return last_node_id

def is_skip(v: Node, SkipNodes: list):
    """This function decides either to skip the node for comparison or not.

    args:
        v (Node): a node object.
        SkipNodes (list): a list of node objects.

    returns:
        (bool) True if decide to skip; otherwise, False.
    """

    # Since we separately compared initial phase, 
    # we want to skip the initial nodes
    if v.phase in NOT_OPTPHASES:
        return True

    return False

def remove_diff_phases(phases: list, remove: list):
    """This function removes phases that are evaluated to be different
    from the main graph phase order list.

    args:
        phases (list): list of all phases executed during the generation of a graph.
        remove (list): list of phases that are evaluated to be different from another
        graph.

    returns:
        (list) list of phases after removing phases with different nodes.
    """

    return [i for i in phases if i not in remove]

def get_intersections(FinalResults: list):
    """This function computes and returns the intersections of all phase
    sets in the FinalResults list.

    This code is from source: https://blog.finxter.com/ how-to-intersect-multiple
    -sets-in-python/#:~:text=To%20intersect%20multiple%20sets%2C%20stored%20in%20a%
    20list,of%20the%20elements%20that%20exist%20in%20all%20sets.

    args:
        FinalResults (list): a list of finalised computed phases. Each
        element holds a set of phases.

    returns:
        (set) set of intersection phases.
    """

    return FinalResults[0].intersection(*FinalResults)

def get_diff_phases(intersection_A: set, intersection_B: set):
    """This function computes and returns the symmetric difference of two sets.

    args:
        intersection_A (set):
        intersection_B (set):

    returns:
        (set) a symmetric difference between phase A and B sets.
    """

    # Find the intersections of two intersection results.
    intersections = get_intersections([intersection_A, intersection_B])

    # Find the symmetric differences between two intersection results.
    SymmetricDifference = intersection_A.symmetric_difference(intersection_B)

    return SymmetricDifference, intersections

## ========================================================================

def GroupGraphs(Graphs: dict, Correctness: dict):
    """This function groups the graphs by correct or incorrect executions.

    args:
        Graphs (dict): dictionary of generated graphs and their properties,
        where key is the file number.
        Correctness (dict): each element represent whether the PoC was
        correctly executed or not.

    returns:
        (dict) holding grouped graphs.
    """

    # Storage for grouped graphs.
    groupedGraphs = {"correct":[], "incorrect":[]}
    original = None

    for filenumber, graph in Graphs.items():
        assert (
                filenumber in Correctness
        ), f"ERROR: filenumber {filenumber} is not in Correctness\
             \n{Correctness}"
        if filenumber == '0':
            original = graph

        if Correctness[filenumber]:
            groupedGraphs["correct"].append([filenumber, graph])
        else:
            groupedGraphs["incorrect"].append([filenumber, graph])

    return groupedGraphs

def FilterGraphs(GroupedGraphs: list, Original: Graph):
    """This function filters out graphs that are different from
    the original graph.

    args:
        groupedGraphs (list): a list of graphs to be filtered.
        original (Graph): original graph.

    returns:
        (list) list of filtered graphs.
    """

    # Retrieve the optimisation phase order of original graph to be used
    # for a standard graph for comparison.
    std_phase_order = get_only_opt_phases(Original.nodes)

    is_incorrect = False
    CS_Results = {}
    for elem in GroupedGraphs:
        filenumber = elem[0]
        if filenumber == '0':
            is_incorrect = True
            continue
        graph = elem[1]
        phase_order = get_only_opt_phases(graph.nodes)
        cs_result = ComputeCosineSimilarity(std_phase_order, phase_order)
        if cs_result not in CS_Results:
            CS_Results[cs_result] = [[filenumber, graph]]
        else:
            CS_Results[cs_result].append([filenumber, graph])

    keys = list(CS_Results.keys())
    keys.sort(reverse=True)
    max_key = None
    for key in keys:
        if len(CS_Results[key]) > 1:
            max_key = key
            break
        
    FilteredGroup = CS_Results[max_key]
    if is_incorrect:
        FilteredGroup.insert(0, ['0', Original])

    return FilteredGroup

def ComputeCosineSimilarity(Standard: list, Target: list):
    """This function computes cosine similarity between the standard
    (original) graph's optimisation phase list and other graph's
    optimisation phase list.

    args:
        Standard (list): a list of optimisation phases of original graph.
        Target (list): a list of optimisation phases of target graph.

    return:
        (float) cosine similarity result.
    """

    if len(Standard) > len(Target):
        difference = len(Standard) - len(Target)
        dummy = [-1] * difference
        Target.extend(dummy)
    elif len(Target) > len(Standard):
        difference = len(Target) - len(Standard)
        dummy = [-1] * difference
        Standard.extend(dummy)

    return cosine_similarity([Standard], [Target])[0][0]

def GetMaxPhase(Graphs: dict):
    """This function finds the maximum execution of phases among all
    graphs.

    args:
        Graphs (dict): dictionary of generated graphs and their properties,
        where key is the file number.

    returns:
        (list) list of phases in the order of execution.
    """

    # Holds max number of phase.
    PhaseMax   = 0
    # Max phase list.
    PhasesList = []

    for filenumber, graph_info in Graphs.items():
        # [5] is phaseToNodes. Get phases using keys().
        CurGraphPhases = list(graph_info[5].keys())
        if len(CurGraphPhases) > PhaseMax:
            PhaseMax = len(CurGraphPhases)
            PhasesList = CurGraphPhases

    return PhasesList

## ========================================================================

def PrintGraph(graph: Graph):
    """This function prints the graph.
    
    args:
        graph (Graph): graph object.

    returns:
        None.
    """
    
    print ("ID|Opcode|Address|Phase")
    print ('----------------------------------')
    for node in graph.nodes:
        print (f"{node.id}|{node.opcode[0]}|0x{node.address.lstrip('0')}|{node.phase}")
        inputs = []
        for input in node.inputs:
            inputs.append(f"{input.id}|{input.opcode[0]}")
        print ('Input Nodes: ', inputs)
        if node.removed_usage_at:
            print ('Usage removed at', node.removed_usage_at[0])
        else:
            print ('Usage removed at None')
        print('-')

    print ("========================================================================")

def PrintPhaseOrder(graph: Graph):
    """
    """

    print ("Phase Order")
    print ('----------------------------------')
    current = None
    for node in graph.nodes:
        if node.phase != current:
            current = node.phase
            print (current)
    print ('----------------------------------')

def PrintGraphByPhaseId(graph: Graph):
    """
    """

    id_to_nodes = graph.id_to_nodes

    for id, nodes in id_to_nodes.items():
        print (f"Phase - ID: {id} - Name: {graph.id_to_phase[id]}")
        opcodes = []
        for node in nodes:
            opcodes.append(node.opcode[0])
        print (opcodes)

## ========================================================================

def argument_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-d",
        "--directory",
        type=str,
        help="Directory where main graph files are saved."
    )
    args = parser.parse_args()

    return args.directory

def load_data(directory: str):
    """This function will load the data from the files in the specified
    directory and returns them to the caller.

    args:
        directory (str): directory where to scan the files.

    returns:
    """

    assert (
        os.path.isdir(directory)
    ), f"ERROR: Directory {directory} does not exist."

    data = None
    try:
        with open(f"{directory}/graph.json", "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        files = os.listdir(directory)
        sys.exit(f"ERROR: File {directory}/{json_f} does not exist.\
                   \nList of files in {directory}/: {files}")
    return data

## ========================================================================

if __name__ == "__main__":
    directory = argument_parser()

    Graphs = {}
    with open(f"{directory}/Graphs.pkl", "rb") as gf:
        Graphs = pickle.load(gf)

    CommonPhases, CommonIndicies = GraphAnalyser(Graphs['8'], Graphs['1'])
    #sys.exit()

    TESTS1 = ['0', '1', '3', '8', '5', '13', '14', '15', '16', '17']
    Result = []
    ResultIdx = []
    for i in TESTS1:
        for j in TESTS1:
            if j != i:
                (
                    CommonPhases, CommonIndicies 
                ) = GraphAnalyser(Graphs[i], Graphs[j])
                Result.append(set(CommonPhases))
                ResultIdx.append(set(CommonIndicies.keys()))

    Intersections1a = get_intersections(Result)
    print ("Intersection from correct list: ", Intersections1a)

    TESTS2 = ['4', '19', '6', '10', '11', '8', '18']
    Result = []
    ResultIdx = []
    for i in TESTS2:
        for j in TESTS2:
            if j != i:
                CommonPhases, CommonIndicies = GraphAnalyser(Graphs[i], Graphs[j])
                Result.append(set(CommonPhases))
                ResultIdx.append(set(CommonIndicies.keys()))

    Intersections2a = get_intersections(Result)
    print ("Intersection from incorrect list: ", Intersections2a)

    Final = get_diff_phases(Intersections1a, Intersections2a)
    print ("Symmetric difference of two phase sets: ", Final)
    
    MaxPhase = GetMaxPhase(Graphs)
    order = {}
    for phase in Final:
        idx = MaxPhase.index(phase)
        order[idx] = phase

    i = 1
    for idx in sorted(order):
       print (f"{i}. {order[idx]}")
       i += 1
