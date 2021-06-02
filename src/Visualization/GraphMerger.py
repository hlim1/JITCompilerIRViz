"""
This program merges intermediate representation graphs to
a single graph.
"""
import os
import sys
import copy
import GraphRestructurer as GR

# Code to import modules from other directories.
# Soruce: https://codeolives.com/2020/01/10/python-reference-module-in-parent-directory/
currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)

import GraphAnalyser as GA

METADATA_LEN = 4

def GraphMerger(GraphList: list):
    """
    """

    MergedGraph = copy.deepcopy(GraphList[0])
    MergedDiffGraph = GR.Graph()
    PhaseList = GraphList[0].id_to_phase
    OriginalG = GraphList[0]
    DiffPhaseIdToNodes = {}
    PhaseToConcatId = {}

    for idx in range(1, len(GraphList)):
        TargetPhaseIDs = GA.get_intersections(
                            [set(OriginalG.id_to_nodes.keys()), set(GraphList[idx].id_to_nodes.keys())]
                         )
        # Compare non-original PoC graphs to original PoC graph and retreive the nodes
        # that are different from the original.
        DiffNodesById = GA.CompareGraphByPhaseId(GraphList[idx], OriginalG, TargetPhaseIDs)
        MergeNodesToOrigin(MergedGraph, DiffNodesById)
        SymmetricDiffIDs = set(GraphList[idx].id_to_nodes.keys()).symmetric_difference(set(OriginalG.id_to_nodes.keys()))
        if SymmetricDiffIDs:
            for id in SymmetricDiffIDs:
                if id in GraphList[idx].id_to_nodes:
                    MergeNodesToOrigin(MergedGraph, {id: GraphList[idx].id_to_nodes[id]})
                    PhaseList[id] = GraphList[idx].id_to_phase[id]

    GroupedPhases, IdToNames = GroupPhases(MergedGraph, PhaseList)

    print_graph(MergedGraph)

    return GroupedPhases, IdToNames

def MergeNodesToOrigin(MergedGraph: GR.Graph, DiffNodesById: dict):
    """
    """

    # Add identified differences in nodes to the original graph by each phases.
    AddNodesToPhaseList(MergedGraph.id_to_nodes, DiffNodesById)

    return

def AddNodesToPhaseList(MergedPhaseIdToNodes: dict, DiffNodesById: dict):
    """
    """

    for id, nodes in DiffNodesById.items():
        if id in MergedPhaseIdToNodes:
            MergedPhaseIdToNodes[id].extend(nodes)
        else:
            MergedPhaseIdToNodes[id] = nodes

    return

def MergeDiffNodes(MergedDiffGraph: GR.Graph, DiffNodesById: dict, Phase_List: dict):
    """
    """

    for id, nodes in DiffNodesById.items():
        if Phase_List[id] != 'GraphBuilderPhase':
            if id not in MergedDiffGraph.id_to_nodes:
                MergedDiffGraph.id_to_nodes[id] = nodes
                MergedDiffGraph.id_to_phase[id] = Phase_List[id]
            else:
                MergedDiffGraph.id_to_nodes[id].extend(nodes)

    return

def GroupPhases(MergedGraph: GR.Graph, PhaseList: dict):
    """This function groups (merges) phases by their operation.
    The phase ids will be merged (concatenated) with a special symbol '@'.

    args:
        MergedGraph (Graph): a naively merged graphs.
        PhaseList (dict):

    returns:
        (dict) dictionary of grouped phases, where keys are concatenated ids
        and values are list of nodes.
        (dict) dictionary of concatenated ids as key and phase name as value.
    """

    GroupedPhases = {}
    NameToID = {}
    NameToNodes = {}
    IdToName = {}

    # Group phases by which holding generated node list.
    for phase_id, node_list in MergedGraph.id_to_nodes.items():
        phase_name = MergedGraph.id_to_phase[phase_id]
        # Merge phase ids by phase names.
        if phase_name not in NameToID:
            NameToID[phase_name] = str(phase_id)
        else:
            NameToID[phase_name] = NameToID[phase_name] + '@' + str(phase_id)
        # Group nodes by phase names.
        if phase_name not in NameToNodes:
            NameToNodes[phase_name] = node_list
        else:
            NameToNodes[phase_name].extend(node_list)
    # After grouping the phases by node list, group remaining phases,
    # which may or may not hold node list.
    for phase_id, phase_name in PhaseList.items():
        if phase_name not in NameToID:
            NameToID[phase_name] = str(phase_id)
        else:
            NameToID[phase_name] = NameToID[phase_name] + '@' + str(phase_id)
        # Initialize element values with empty list.
        if phase_name not in NameToNodes:
            NameToNodes[phase_name] = []

    for name, concat_id in NameToID.items():
        GroupedPhases[concat_id] = NameToNodes[name]
        IdToName[concat_id] = name

    return GroupedPhases, IdToName

## ====================================================

def print_graph(graph: GR.Graph()):
    """
    """
    print ("Graph ID: ", graph.id)
    print ("node id, graph id, address, opcode, input-list")
    print ("    replaced-input-list, killed-at, removed-usage-at, append-inputs-list")
    for id, nodes in graph.id_to_nodes.items():
        print ("ID: ", id, graph.id_to_phase[id])
        for node in nodes:
            inputs = []
            for n in node.inputs:
                inputs.append([n.opcode[0], n.phase_id, n.id])
            print (node.id, node.graph_id, node.address, node.opcode[0], inputs)
            print ("    ", node.replaced_inputs, node.killed_at, node.removed_usage_at, node.append_inputs)
