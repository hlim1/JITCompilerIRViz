"""This eil does not hold any executable functions.
The purpose of this python file is to hold the X86 assembly instructions.
"""

# Prefix for two-byte instructions.
OF = "0f"

# Function entry instruction.
PUSH_RBP = "55"

# Function argument.
PUSH_RBX = "53"

# Function return.
RET = [
        "c2", "c3", "ca", "cb",
]

# List of all one-byte jump (i.e. JO or JNZ) opcodes.
ONE_BYTE_JX = [
        '70', '71', '72', '73',
        '74', '75', '76', '77',
        '78', '79', '7a', '7b',
        '7c', '7d', '7e', '7f',
]

# List of all two-byte jump (i.e. JO or JNZ) opcodes.
TWO_BYTE_JX = [
        '80', '81', '82', '83',
        '84', '85', '86', '87',
        '88', '89', '8a', '8b',
        '8c', '8d', '8e', '8f',
]

# List of jump (i.e. jmp) opcodes.
JMP = [
        'e9', 'eb',
]

# List of call opcodes.
CALL = [
        'e8'
]

# HEX MOVE
HEX_MOV = [
        'b0', 'b1', 'b2', 'b3',
        'b4', 'b5', 'b6', 'b7',
        'b8', 'b9', 'ba', 'bb', 
        'bc', 'bd', 'be', 'bf',
]

# Registers
RAX = ["rax", "eax"]
