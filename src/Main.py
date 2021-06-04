"""This Main.py program runs entire programs from running JS code with d8
to identifying and producing the localised bug candidates."

Example,
    $python Main.py\
        -f <Original PoC>\
        -b <Bytecode JSON>\
        -d <Output Directory>\
        -n <Number of PoC Modification>

Author: Terrence J. Lim
"""

import time
import json
import os, sys
import pickle
import argparse
import subprocess

import PhaseIdentifier as PI
import BytecodeIdentifier as BI
import OptimisationTracker as OT
import FunctionLists as FL
import NativeCodeMapper as NT
import GraphCreator as GC
import GraphAnalyser as GA
import Visualization.GraphRestructurer as GR
import Visualization.GraphMerger as GM

from Visualization.Simplifier import Simplifier

# Code to import modules from other directories.
# Soruce: https://codeolives.com/2020/01/10/python-reference-module-in-parent-directory/
currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)

import x86Tracer.backTracer.instruction_restructor as IR
import PoCModifier.PoCModifier as PoCM
import PoCModifier.JSAstGenerator as AstG

JSCODEGENERATOR = "/scratch/hlim1/scripts/ResearchTools/PoCModifier/JSCodeGenerator.js"

D8OPTIONS = [
        "--allow-natives-syntax",
        "--no-turbo-inlining",
        "--single-threaded",
        "--expose-gc",
]
TRACER = [
        "/scratch/hlim1/pin-3.7/pin",
        "-t",
        "/scratch/hlim1/pin-3.7/source/tools/ScienceUpToPar/Tools/tracer/obj-intel64/Tracer.so",
        "--",
]
TRACEOUTS = [
        "trace.out",
        "data.out",
        "errors.out",
]
TRACE2ASCII = "/scratch/hlim1/pin-3.7/source/tools/ScienceUpToPar/Tools/uacs-lynx/trace2ascii/trace2ascii"

def CheckUserInputs(PoC: str, bytecode: str, directory: str, number: int):
    """This function checks user inputs that was received via command-line
    arguments.

    args:
        PoC (str): Original PoC file path.
        bytecode (str): Bytecode JSON file path.
        directory (str): Directory to store generated outout files.
        number (int): A number of PoCs to modify & generate from the original PoC.

    returns:
        None.
    """
    assert os.path.exists(PoC), f"ERROR: PoC file '{PoC}' does not exist."
    assert os.path.exists(bytecode), f"ERROR: Bytecode file '{bytecode}' does not exist."
    assert number > 0, f"ERROR: Number of modification must be greater than 0."

    # If output directory does not exists already, generate it automatically.
    if not os.path.exists(directory):
        os.makedirs(directory)
    # Generate subdirectories to store specific files.
    if not os.path.exists(f"{directory}/asts"):
        os.makedirs(f"{directory}/asts")
    if not os.path.exists(f"{directory}/asciis"):
        os.makedirs(f"{directory}/asciis")
    if not os.path.exists(f"{directory}/pocs"):
        os.makedirs(f"{directory}/pocs")
    if not os.path.exists(f"{directory}/d8outs"):
        os.makedirs(f"{directory}/d8outs")
    if not os.path.exists(f"{directory}/traces"):
        os.makedirs(f"{directory}/traces")
    if not os.path.exists(f"{directory}/graphs"):
        os.makedirs(f"{directory}/graphs")
    if not os.path.exists(f"{directory}/etc"):
        os.makedirs(f"{directory}/etc")

def RunD8(directory: str, executable: str):
    """This function runs all the PoC files including the original file.
    It captures the stdouts from running the PoCs with d8 and write to files.

    args:
        orgPoC (str): original PoC file.
        directory (str): path to the directory where outputs will be stored.

    returns:
        None.
    """
    
    begin = time.time()

    D8 = executable

    pocsDir  = directory + "/pocs"
    d8outDir = directory + "/d8outs"

    # Retrieve all the PoC file names from the PoC directory.
    pocs = os.listdir(pocsDir)
    # Run all PoCs with d8 and write out the outputs to a file.
    for poc in pocs:
        pocPath = pocsDir + "/" + poc
        fileNumber = get_file_number(poc)
        output = subprocess.run(
                    [D8, D8OPTIONS[0], D8OPTIONS[1], D8OPTIONS[2], D8OPTIONS[3], pocPath],
                    capture_output=True,
                    text=True
        )

        # This code is not needed for all PoCs - Currently, only needed for Issue # 1072171.
        output = subprocess.run(["uniq", "-c"], input=output.stdout, capture_output=True, text=True)

        # If the output return code is not 0, the execution terminated abnormally or crashed.
        outputFile = d8outDir + f"/output_{str(fileNumber)}.out"

        if output.returncode != 0:
            with open(outputFile, 'w') as f:
                f.write("CRASHED")
        else:
            with open(outputFile, 'w') as f:
                f.write(output.stdout)

    end = time.time()
    print ("TIME: RunDB -", "{0:.2f}".format((end-begin)/60), " mins")


def get_file_number(filename: str):
    """This is a helper function to capture the file number
    from the PoC file.

    args:
        filename (str): PoC file name.

    return:
        (str) file number.
    """

    tmp = filename.split('_')[-1]
    filenumber = tmp.split('.')[0]

    return filenumber

def GetTraceAsciis(directory: str):
    """Run tracer and trace2ascii programs to get the trace of d8 execution
    on each PoCs in ascii format.

    args:
        directory (str): path to the directory where outputs will be stored.
        orgPoC (str): original PoC file.

    returns:
        None.
    """

    begin = time.time()

    traceDir = directory + "/traces"
    pocsDir  = directory + "/pocs"
    asciiDir  = directory + "/asciis"

    # Run tracer on the original PoC and generated PoCs.
    RunTracer(pocsDir, traceDir)

    # Run trace2ascii on all trace files.
    RunTrace2Ascii(asciiDir, traceDir)

    end = time.time()
    print ("TIME: GetTraceAsciis -", "{0:.2f}".format((end-begin)/60), " mins")

def RunTracer(pocsDir: str, traceDir: str):
    """This function runs tracer on the original PoC and all generated modified
    PoCs to get binary trace files.

    args:
        pocsDir (str) :directory where all pocs are stored.
        traceDir (str): directory where all traces are stored.

    returns:
        None.
    """

    # Retrieve all the PoC file names from the PoC directory.
    pocs = os.listdir(pocsDir)

    # Run the tracer on all PoCs including the original.
    for poc in pocs:
        pocPath = pocsDir + "/" + poc
        print ("RunTracer: pocPath:", pocPath)
        # Get the trace file from the original PoC.
        output = subprocess.run(
                    [
                       TRACER[0], TRACER[1], TRACER[2], TRACER[3],
                       D8, D8OPTIONS[0], D8OPTIONS[1], D8OPTIONS[2], D8OPTIONS[3],
                       pocPath 
                    ],
                    capture_output=True,
                    text=True
        )
        # Get the file number of each PoC and rename the trace file with
        # the PoC file number added to distinguish which trace is from which PoC.
        fileNumber = get_file_number(poc)
        mTraceFile = traceDir + f"/trace_{str(fileNumber)}.out"
        # All trace files are default to store at the location where the tracer was
        # ran with a default name 'trace.out'. Thus, we need to move all trace files
        # to the trace directory.
        subprocess.run(['mv', TRACEOUTS[0], mTraceFile])
        # Remove other files those are generated by default.
        subprocess.run(['rm', TRACEOUTS[1]])
        subprocess.run(['rm', TRACEOUTS[2]])

def RunTrace2Ascii(asciiDir: str, traceDir: str):
    """This function runs trace2ascii on all trace files in the trace directory.

    args:
        asciiDir (str): directory where all asciis are stored.
        traceDir (str): directory where all traces are stored.

    returns:
        None.
    """

    # Retrieve all ascii file names from the asciis directory.
    traces = os.listdir(traceDir)
    
    # Run trace2ascii on all trace files.
    for trace in traces:
        tracePath = traceDir + "/" + trace
        print ("RunTrace2Ascii: tracePath:", tracePath)
        output = subprocess.run (
                    [TRACE2ASCII, tracePath],
                    capture_output=True,
                    text=True
        )
        filenumber = get_file_number(trace)
        ascii_f = asciiDir + f"/ascii_{str(filenumber)}.out"
        with open(ascii_f, 'w') as f:
            f.write(output.stdout)

def GetPoCs(PoC: str, directory: str, number: int):
    """This function calls PoCModifier program to modify the original PoC
    and generate new PoCs.

    args:
        PoC (str): Original PoC file path.
        directory (str): Directory to store generated outout files.
        number (int): A number of PoCs to modify & generate from the original PoC.

    returns:
        None.
    """

    begin = time.time()

    with open(PoC) as JSFile:
        file = os.path.basename(PoC)
        filename, ext = os.path.splitext(file)

        JSCode = JSFile.read()
        # Get a syntax tree from the original JS PoC.    
        ast = AstG.AstGenerator(JSCode);
        # Convert syntax tree type from esprima object to python dict.
        ast_dict = ast.toDict()

        # Generate N number of PoCs and retrieve them in a list container.
        modifiedASTs = PoCM.PoCGenerator(ast_dict, number)
        # Dump generated syntax tress to JSON files.
        file_number = 1
        json_files = []
        for m_Ast in modifiedASTs:
            json_file = directory + "/asts/" + filename + f"_{str(file_number)}.json"
            with open(json_file, 'w') as json_f:
                json.dump(m_Ast, json_f)
            file_number += 1
            json_files.append(json_file)

        # Call JSCodeGenerator to generate new PoCs.
        for json_f in json_files:
            f = os.path.basename(json_f)
            of, ext = os.path.splitext(f)
            output_file = directory + "/pocs/" + of + ".js"
            subprocess.run(['node', JSCODEGENERATOR, json_f, output_file])

        # Copy the original PoC to the poc directory. Original PoC get file number 0 ALWAYS.
        movedPoC  = directory + "/pocs/" + filename + "_0.js"
        subprocess.run(["cp", PoC, movedPoC])

    end = time.time()
    print ("TIME: GetPoC -", "{0:.2f}".format((end-begin)/60), " mins")

def GetGraphs(directory: str, bytecode: str):
    """This function runs graph creator on each trace ascii files to create graphs.

    args:
        directory (str): Directory to store generated outout files.
        bytecode (str): bytecode file path.

    returns:
        (dict) file number-to-graphs.
        (dict) file number-to-jitted status.
    """

    begin = time.time()

    # Empty container to hold generated graphs.
    # {__filenumber__: (__tuple__)}.
    graphs = {}
    # Keep a track either the PoC was JIT compiled or not.
    # {__filenumber__: __bool__}.
    jitted = {}

    asciiDir  = directory + "/asciis"
    graphDir  = directory + "/graphs"
    etcDir    = directory + "/etc"

    # Get the list of bytecodes for current V8 version.
    bytecode_dict = read_file(bytecode)

    # Retrieve all ascii file names.
    asciis = os.listdir(asciiDir)

    # Process all ascii file one-by-one.
    for ascii in asciis:
        asciiPath = asciiDir + "/" + ascii
        print ("GetGraphs: asciiPath:", asciiPath)
        # Get file number, which will be the key for the graph dict.
        # container.
        filenumber = get_file_number(ascii)
        # Load the ascii file content.
        lines = read_file(asciiPath)
        # Identify the scope of each optimisation phases from
        # the GraphBuilderPhase.
        (
            phase_scopes,
            has_exception,
            line_number,
            first_and_last
        ) = PI.phase_identifier(lines)
        # Fill jitted with either each file was jit compiled
        # (True) or not (False).
        jitted[filenumber] = True if phase_scopes else False
        # If the PoC was not jit compiled, then there will be no graph
        # generated. Therefore, we just move on to the next file.
        # Otherwise, move to graph generation step.
        if not jitted[filenumber]: continue
        # Identify the optimised bytecode info based on V8 version.
        (
            bytecode_info,
            line_number
        ) = BI.bytecode_identifier(lines, bytecode_dict, phase_scopes)
        # Get the initial JS nodes generated during the GraphBuilderPhase.
        last_line = max(phase_scopes["GraphBuilderPhase"])
        GraphBuilderPhase_lines = lines[line_number:last_line]
        (
            initial_nodes,
            input_nodes
        ) = OT.initial_node_identifier(
                bytecode_info,
                GraphBuilderPhase_lines
            )
        # Generate graphs and collect their properties.
        graphs[filenumber] = GC.graph_former(
                                    lines, 0, first_and_last[1],
                                    initial_nodes["nodes"], phase_scopes
        )
        graph_file = graphDir + f"/graph_{str(filenumber)}.json"
        with open(graph_file, 'w') as f:
            json.dump(graphs[filenumber][0], f, indent=2)

    # Write JIT compilation status dictionary to a JSON file.
    Jitted_f = etcDir + "/Jitted.json"
    with open(Jitted_f, 'w') as jf:
        json.dump(jitted, jf)

    # Write graphs data to a file in byte.
    graphs_f = graphDir + "/Graphs.pkl"
    with open(graphs_f, "wb") as bin_file:
        pickle.dump(graphs, bin_file)

    end = time.time()
    print ("TIME: GetGraphs -", "{0:.2f}".format((end-begin)/60), " mins")

    return graphs, jitted

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
        if filename.endswith(".json"):
            with open(filename) as json_file:
                return json.load(json_file)
        else:
            with open(filename) as f:
                return f.readlines()
    except IOError as x:
        if x.errno == errno.ENOENT:
            assert False, "Error(" + str(errno.ENOENT) + "). " + filename + ' - does not exist'
        elif x.errno == errno.EACCES:
            assert False, "Error(" + str(errno.EACCESS) + "). " + filename + ' - cannot be read'
        else:
            assert False, "Error(" + str(x.errno) + "). " + filename + ' - some other error'

def write_csv(NodeSets: list, output_f: str):
    """
    """
    
    with open(output_f, 'w', newline='') as file:
        writer = csv.writer(file)
        for row in NodeSets:
            writer.writerow(row)


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
        help="Original PoC JS file."
    )
    parser.add_argument(
        "-e",
        "--executable",
        type=str,
        help="D8 executable."
    )
    parser.add_argument(
        "-b",
        "--bytecode",
        type=str,
        help="A path to JSON file holding all the list of opcodes."
    )
    parser.add_argument(
        "-d",
        "--directory",
        type=str,
        help="A path to store generated output files."
    )
    parser.add_argument(
        "-n",
        "--number",
        type=int,
        help="A number of PoCs to modify & generate from the original."
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Output CSV file name."
    )
    
    args = parser.parse_args()

    return args.file, args.bytecode, args.directory, args.number, args.csv, args.executable

if __name__ == "__main__":
    PoC, bytecode, directory, number, csv_f, executable = argument_parser()
    CheckUserInputs(PoC, bytecode, directory, number)
    # Get N number of modified PoCs from the original PoC.
    GetPoCs(PoC, directory, number)
    # Run d8 to get the outputs of each PoCs.
    Crashes = RunD8(directory, excutable)
    # Get ascii files for each PoC runs.
    GetTraceAsciis(directory)
    # Run graph creator to get graphs for each trace.
    Graphs, Jitted = GetGraphs(directory, bytecode)
    # Restructure a graph to an appropriate format.
    restructured_graphs = GR.RestructureGraphs(Graphs)
    # IR merging.
    MergedGraph, IdToNames = GM.GraphMerger(restructured_graphs)
    # IR simplification.
    Data = Simplifier(MergedGraph, IdToNames)
    # Output final data to CSV file.
    write_csv(Data, csv_f)
