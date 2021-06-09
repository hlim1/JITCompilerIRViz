import os
import json
import argparse

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

if __name__ == "__main__":
    filename = argument_parser()

    with open (filename) as f:
        lines = f.readlines()

        opcode_to_bytecode = {}
        for line in lines:
            s = line.split(";")
            opcode = s[0].strip()
            if len(opcode) < 2:
                opcode = f"0{opcode}"
            bytecode = s[1].strip()

            opcode_to_bytecode[opcode] = bytecode

        output_dir = os.path.dirname(filename)
        output = os.path.join(output_dir, "Bytecode_List.json")
        with open (output, "w") as json_file:
            json.dump(opcode_to_bytecode, json_file, indent=2)
