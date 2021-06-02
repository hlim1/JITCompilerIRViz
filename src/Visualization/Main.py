import argparse
import pickle
import sys
import csv

import GraphRestructurer as GR
import GraphMerger as GM
from Simplifier import Simplifier

def argument_parser():
    """This function is for a safe command line
    input. It should receive the trace file name.

    returns:
        (str) path to trace ascii file.
        (str) path to bytecode json file.
    """

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-f",
        "--file",
        type=str,
        help="Graph file."
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Output CSV file name."
    )
    
    args = parser.parse_args()

    return args.file, args.output

def write_csv(NodeSets: list, output_f: str):
    """
    """
    
    with open(output_f, 'w', newline='') as file:
        writer = csv.writer(file)
        for row in NodeSets:
            writer.writerow(row)

if __name__ == "__main__":
    graph_f, output_f = argument_parser()

    assert (
            ".csv" in output_f
    ), f"ERROR: Output file name must contain *.csv extension."

    Graphs = {}
    with open(graph_f, "rb") as gf:
        Graphs = pickle.load(gf)

    restructured_graphs = GR.RestructureGraphs(Graphs)
    MergedGraph, IdToNames = GM.GraphMerger(restructured_graphs)
    Data = Simplifier(MergedGraph, IdToNames)
    write_csv(Data, output_f)
