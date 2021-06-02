"""
"""
import os
import sys
import copy
import random

import GraphRestructurer as GR

# Code to import modules from other directories.
# Soruce: https://codeolives.com/2020/01/10/python-reference-module-in-parent-directory/
currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)

METADATA_LEN = 6
OPCODE_POS = 2

def Simplifier(GroupedPhases: dict, IdToNames: dict):

    """This function simplifies the graph to meet the requirements
    of MetroSet.

    args:
        GroupedPhases (dict): grouped phase id to node list.
        IdToNames (dict): grouped phase id to its phase name.

    returns:
        (list) simplification completed set. 
    """

    SimplifiedGraph = SimplifyGraph(GroupedPhases, IdToNames)
    NodeSets = AddNodesToSets(SimplifiedGraph, IdToNames)
    CleanedDataSets = CleanData(NodeSets)
    AddDummyNodes(CleanedDataSets)

    return CleanedDataSets

def SimplifyGraph(GroupedPhases: dict, IdToNames: dict):
    """
    """

    SimplifiedGraph = {}

    for concat_id, nodes in GroupedPhases.items():
        cleaned_nodes = CleanNodes(nodes)
        merged = MergeNodes(nodes)
        SimplifiedGraph[concat_id] = merged

    return SimplifiedGraph

def CleanNodes(nodes: list):
    """This function cleans nodes for visualization.
        (1) Removes edge(s) pointing to itself.

    args:
        nodes (list): list of nodes.

    return:
        (dict) list of cleaned nodes.
    """

    cleaned_nodes = []

    for node in nodes:
        # Remove edge that's pointing to itself.
        for ipt_node in node.inputs:
            if ipt_node.id == node.id:
                node.inputs.remove(ipt_node)

    return cleaned_nodes

def MergeNodes(nodes: list):
    """
    """

    MergedNodes = copy.deepcopy(nodes)
    skip_nodes = []

    for n1 in nodes:
        if n1.id not in skip_nodes:
            for n2 in nodes:
                if n2.id not in skip_nodes and CheckMergeableStat(n1, n2):
                    for n in MergedNodes:
                        if n.id == n2.id:
                            MergedNodes.remove(n)
                    skip_nodes.append(n2.id)

    return MergedNodes

def CheckMergeableStat(n1: GR.Node, n2: GR.Node):
    """This function checks if any two nodes can be merged into one.
    
    args:
        n1 (Node):
        n2 (Node):

    return:
        (bool) True, if two nodes can be merged. False, if two nodes
        cannot be merged.
    """

    if n1 == n2:
        return False

    if (
            n1.graph_id == n2.graph_id
            and n1.opcode[0] == n2.opcode[0]
    ):
        if len(n1.inputs) != len(n2.inputs):
            return False
        elif len(n1.inputs) == len(n2.inputs) and len(n1.inputs) == 0:
            return CheckNodeAttributes(n1, n2)
        else:
            assert (
                    len(n1.inputs) == len(n2.inputs)
            ), f"ERROR: lenth of n1 input list and n2 input list must be equal"
            length = len(n1.inputs)
            for i in range(0, length):
                if n1.inputs[i].id != n2.inputs[i].id:
                    return False
            return CheckNodeAttributes(n1, n2)

    return False

def AddNodesToSets(SimplifiedGraph: dict, IdToNames: dict):
    """
    """

    ConcatIds = list(SimplifiedGraph.keys())
    PhaseNames = list(IdToNames.values())
    # Populate the title row with addres, attributes, and concatenated phase ids.
    NodeSets = [['id', '{address}','{opcode}','{phaseid}','{graphid}','{phase}']+PhaseNames]

    # Add nodes to sets based on their optimization.
    number_of_sets = len(NodeSets[0])
    for concat_id, nodes in SimplifiedGraph.items():
        for node in nodes:
            # Generate a new row initilized with 0 values.
            NewRow = [0]*number_of_sets
            NewRow[0] = str(node.id)
            NewRow[1] = f"0x{node.address.lstrip('0')}"
            NewRow[2] = f"0x{node.opcode[0]}"
            NewRow[3] = str(node.phase_id)
            NewRow[4] = str(node.graph_id)
            NewRow[5] = f"{node.phase.split('Phase')[0]}"

            PopulateRow(NodeSets[0], IdToNames, NewRow, ConcatIds, NewRow[3])

            # Check killed phase.
            if len(node.killed_at) > 0:
                # Retrieve the single phase id where the node was killed.
                OptPhaseId = str(node.killed_at[-1])
                PopulateRow(NodeSets[0], IdToNames, NewRow, ConcatIds, OptPhaseId)
            # Check removed usage phase:
            if len(node.removed_usage_at) > 0:
                OptPhaseId = str(node.removed_usage_at[-1])
                PopulateRow(NodeSets[0], IdToNames, NewRow, ConcatIds, OptPhaseId)
            # Check append input phases.
            if len(node.append_inputs) > 0:
                for ipt in node.append_inputs:
                    OptPhaseId = str(ipt[-1])
                    PopulateRow(NodeSets[0], IdToNames, NewRow, ConcatIds, OptPhaseId)
            # Check replaced input phases.
            if len(node.replaced_inputs) > 0:
                for ipt in node.replaced_inputs:
                    OptPhaseId = str(ipt[-1])
                    PopulateRow(NodeSets[0], IdToNames, NewRow, ConcatIds, OptPhaseId)

            NodeSets.append(NewRow)

    return NodeSets

def PopulateRow(TitleRow: list, IdToNames: dict, NewRow: list, ConcatIds: list, SinglePhaseId: str):
    """
    """

    group_id = VerifyGroup(ConcatIds, SinglePhaseId)
    phase_name = IdToNames[group_id]
    col_idx = TitleRow.index(phase_name)
    NewRow[col_idx] = 1

def VerifyGroup(ConcatIds: list, SingleId: str):
    """
    """

    assert (
            type(SingleId) == str
    ), f"ERROR: SingleId must be string type - {type(SingleId)}"

    for concat_id in ConcatIds:
        if SingleId in concat_id.split('@'):
            return concat_id

    assert (
            False
    ), f"ERROR: Single ID {SingleId} does not exist in the group - {ConcatIds}"

def CleanData(NodeSets: dict):
    """
    """

    CleanedNodeSets = []
    IndicesToRemove = []
    ColumnOccupied = [0]*len(NodeSets[0])

    # Find all column indices that have no elements.
    for row in NodeSets[1:]:
        col_idx = METADATA_LEN
        for col in row[METADATA_LEN:]:
            if col == 1:
                ColumnOccupied[col_idx] += 1
            col_idx += 1
    for idx in range (METADATA_LEN, len(NodeSets[0])):
        if ColumnOccupied[idx] == 0:
            print (idx, NodeSets[0][idx])
            IndicesToRemove.append(idx)

    # Remove all columns that have no elements.
    for row in NodeSets:
        cleaned_row = []
        for idx in range(0, len(row)):
            if idx not in IndicesToRemove:
                cleaned_row.append(row[idx])
        CleanedNodeSets.append(cleaned_row)
    
    ## =============================
    percentage = compute_percentage_reduce(len(NodeSets[0]), len(CleanedNodeSets[0]))
    print (f"Number of Original Sets: {len(NodeSets[0])-4}")
    print (f"Number of Reduced Sets: {len(CleanedNodeSets[0])-4}")
    print (f"Percentage of Sets Decreased by {percentage}%")
    ## =============================

    # Clean title row by removing "Phase" from the column names.
    Title = []
    for col_name in CleanedNodeSets[0]:
        if "Phase" in col_name:
            idx = col_name.index("Phase")
            Title.append(col_name[0:idx])
        else:
            Title.append(col_name)
    CleanedNodeSets[0] = Title

    ## =============================
    OriginalElems = CalculateElemsInASet(CleanedNodeSets)
    #print (CleanedNodeSets[0])
    #print (OriginalElems)
    ## =============================

    # Remove initial phase (GraphBuilderPhase) only node.
    # In other words, nodes that do not get optimized.
    # Currently not in use.
    #CleanedNodeSets = RemoveOnlyGraphBuilder(CleanedNodeSets)

    # Merge similar nodes in terms of operation and optimization.
    CleanedNodeSets = MergeSimilarNodes(CleanedNodeSets)
    ## =============================
    DecreasedElems = CalculateElemsInASet(CleanedNodeSets)
    #print (CleanedNodeSets[0])
    #print (DecreasedElems)
    ## =============================

    ## =============================
    percentage = compute_percentage_reduce(sum(OriginalElems), sum(DecreasedElems))
    print (f"Total number of elements in the original: {sum(OriginalElems)}")
    print (f"Total number of elements in the reduced: {sum(DecreasedElems)}")
    print (f"Percentage of Elements Decreased by {percentage}%")
    ## =============================

    return CleanedNodeSets

def MergeSimilarNodes(CleanedNodeSets: list):
    """This function merges nodes that are similar in terms
    of the operation, which is identifiable with the opcode,
    and the optimization, which is identifiable with the set(s)
    it's belong to.

    args:
        CleanedNodeSets (list): list of data sets.

    returns:
        (list) list of merged data set.
    """

    MergedDataSet = [CleanedNodeSets[0]]
    MergedNodes = []
    # This dict. is keeping track of which nodes were merged by grouping.
    # Currently, has no specific usage, but will be used in the future.
    MergedNodeDict = {}

    for idx in range(1, len(CleanedNodeSets)):
        MergedNodeDict[CleanedNodeSets[idx][OPCODE_POS]] = [CleanedNodeSets[idx]]
        for idx2 in range(idx+1, len(CleanedNodeSets)):
            if (
                    CleanedNodeSets[idx][OPCODE_POS] == CleanedNodeSets[idx2][OPCODE_POS]
                    and CleanedNodeSets[idx][METADATA_LEN:] == CleanedNodeSets[idx2][METADATA_LEN:]
            ):
                MergedNodes.append(CleanedNodeSets[idx2])
                MergedNodeDict[CleanedNodeSets[idx][OPCODE_POS]].append(CleanedNodeSets[idx2])
        if CleanedNodeSets[idx] not in MergedNodes:
            MergedDataSet.append(CleanedNodeSets[idx])
            MergedNodes.append(CleanedNodeSets[idx])

    return MergedDataSet


def AddDummyNodes(DataSet: list):
    """This function is to handle the case where any sets
    have single element by adding additional dummy node
    to overcome the restriction on MetroSet tool.

    args:
        DataSet (list): list of data sets.

    return:
        (list): list of data set that may may have added
        with dummy nodes.
    """

    ElemCounter = CalculateElemsInASet(DataSet)
    SetsToAddDummies = []

    # Seek for the sets with a single element.
    idx = 0
    for elem_amount in ElemCounter:
        if elem_amount == 1:
            SetsToAddDummies.append(idx)
        idx += 1

    if len(SetsToAddDummies) > 0:
        for idx in SetsToAddDummies:
            dummy = [0]*len(DataSet[0])
            dummy[0] = f'-{random.randint(1,99999)}'
            dummy[1] = "0xDummy"
            dummy[2] = f'0x{random.randint(1,99999)}'
            dummy[3] = '-1'
            dummy[4] = '-1'
            dummy[5] = "DummyPhase"
            dummy[idx] = 1
            DataSet.append(dummy)
        # To handle disconnected components, the elements in the single
        # element sets will be added to the initial phase as well.
        # This is TODO to come up with how to properly handle this case.
        for idx in SetsToAddDummies:
            for row in DataSet[1:]:
                if row[idx] == 1:
                    row[METADATA_LEN] = 1

def CheckNodeAttributes(n1: GR.Node, n2: GR.Node):
    """
    """

    # Check replaced input phases.
    if len(n1.replaced_inputs) != len(n2.replaced_inputs):
        return False
    else:
        for i in range(0, len(n1.replaced_inputs)):
            if n1.replaced_inputs[i][0] != n2.replaced_inputs[i][0]:
                return False
    # Check killed at phase.
    if len(n1.killed_at) != len(n2.killed_at):
        return False
    elif len(n1.killed_at) == len(n2.killed_at) and len(n1.killed_at) > 0:
        if n1.killed_at[0] != n2.killed_at[0]:
            return False
    # Check append input phases.
    if len(n1.append_inputs) != len(n2.append_inputs):
        return False
    else:
        for i in range(0, len(n1.append_inputs)):
            if n1.append_inputs[i][0] != n2.append_inputs[i][0]:
                return False
    # Check removed usage phase:
    if len(n1.removed_usage_at) != len(n2.removed_usage_at):
        return False
    elif len(n1.removed_usage_at) == len(n2.removed_usage_at) and len(n1.removed_usage_at) > 0:
        if n1.removed_usage_at[0] != n2.removed_usage_at[0]:
            return False

    return True

def RemoveOnlyGraphBuilder(CleanedNodeSets: list):
    """
    """
    
    RowsToRemove = []
    idx = 1
    for row in CleanedNodeSets[1:]:
        is_remove = True
        for col in row[5:]:
            if col == 1:
                is_remove = False
                break
        if is_remove:
            RowsToRemove.append(idx)
        idx += 1

    RemovedNodeSets = []
    for idx in range(0, len(CleanedNodeSets)):
        if idx not in RowsToRemove:
            RemovedNodeSets.append(CleanedNodeSets[idx])

    return RemovedNodeSets

## ====================================================

def CalculateElemsInASet(SetList: list):
    """
    """

    ElemCounter = [0]*len(SetList[0])
    for row in SetList[1:]:
        idx = 0
        for col in row:
            if idx >= METADATA_LEN and col == 1:
                ElemCounter[idx] += 1
            idx += 1

    return ElemCounter

def compute_percentage_reduce(StartValue: int, FinalValue: int):
    """This function computes the percentage decrease from the start value
    to final value.

    args:
        StartValue (int): original value.
        FinalValue (int): last value after decreased.

    returns:
        (str) percentage decrease in 2 decimal points.
    """

    percentage = ((StartValue-FinalValue)/StartValue)*100

    return "{0:.2f}".format(percentage)
