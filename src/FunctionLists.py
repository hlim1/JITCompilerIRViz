"""This file does not hold any executable functions.
The purpose of this python file is to hold the global
constant variables for each version of v8.

If a new variable needs to be added, locate the correct
version. If not exists, add a new version section and add
under there.
"""
# List of handled V8 versions.
V8_VERSIONS = [
        "6.1.534.32",
        "6.3.0",
        "8.0.0",
        "8.2.0",
        "8.2.297.3",
        "6.2.0",
]

V8_VERSION_6 = [
        "6.1.534.32",
        "6.3.0",
        "6.2.0",
]

V8_VERSION_7 = [
        "7.6.0",
]

V8_VERSION_8 = [
        "8.0.0",
        "8.2.0",
        "8.2.297.3",
]

# V8 COMMON PROGRAM NAMES
UNKNOWN = "unknown"

# V8 COMMON
PHASE_REGEX = r"v8::internal::compiler::\w+Phase::Run"
OPT_PHASE_REGEX = r"v8::internal::compiler::PipelineImpl::Run\<v8::internal::compiler::(?P<phase>\w+Phase)\>"
ASSEMBLER_REGEX = r"v8::internal::Assembler::\w+"
TURBOASSEMBLER_REGEX = r"v8::internal::TurboAssembler::\w+"
INSTRUCTIONSELECTOR_REGEX = "v8::internal::compiler::\w+::Visit\w+"

## NODE RELATED FUNCTIONS
NEW_STR = "v8::internal::compiler::Node::New"
NEWNODE_STR = "v8::internal::compiler::Graph::NewNode"
CLONENODE_STR = "v8::internal::compiler::Graph::CloneNode"
NEWNODEUNCHECKED_STR = "v8::internal::compiler::Graph::NewNodeUnchecked"
CURRENT_BYTECODE_STR = "v8::internal::interpreter::BytecodeArrayAccessor::current_bytecode"
APPENDINPUT = "v8::internal::compiler::Node::AppendInput"
REPLACEINPUT = "v8::internal::compiler::Node::ReplaceInput"
NODEKILL = "v8::internal::compiler::Node::Kill"
REMOVEUSE = "v8::internal::compiler::Node::RemoveUse"
APPENDUSE = "v8::internal::compiler::Node::AppendUse"

NATIVE_CODE_GENERATOR = "v8::internal::compiler::CodeGenerator::CodeGenerator"
ASSEMBLECODE = "v8::internal::compiler::CodeGenerator::AssembleCode"
INST_SELECT_PHASE = "InstructionSelectionPhase"
ADDOPTCODE = "v8::internal::NativeContext::AddOptimizedCode"
FINALIZEJOBIMPL = "v8::internal::compiler::PipelineCompilationJob::FinalizeJobImpl"
FUNCTION_ENTRY = "Builtins_CEntry_Return1_DontSaveFPRegs_ArgvOnStack_NoBuiltinExit"
EMIT = "v8::internal::compiler::InstructionSelector::Emit"
EMITWITHCONTINUATION = "v8::internal::compiler::InstructionSelector::EmitWithContinuation"
ADDINSTRUCTION = "v8::internal::compiler::InstructionSequence::AddInstruction"
INSTRUCTION = "v8::internal::compiler::Instruction::Instruction"
ASSEMBLEINSTRUCTION ="v8::internal::compiler::CodeGenerator::AssembleInstruction"
ISVISITNODE = "v8::internal::compiler::InstructionSelector::VisitNode"
RSVISITNODE = "v8::internal::compiler::RepresentationSelector::VisitNode"
VISITCONTROL = "v8::internal::compiler::InstructionSelector::VisitControl"
OPERATOR = "v8::internal::compiler::Operator::Operator"

# V8 VERSION 6.3.0
VERSION_ANALYZE = "v8::internal::compiler::BytecodeAnalysis::Analyze"
VERSION_ARRAYRANDOMITERATOR = "v8::internal::interpreter::BytecodeArrayRandomIterator::BytecodeArrayRandomIterator"
VERSION_ARRAYACCESSOR = "v8::internal::interpreter::BytecodeArrayAccessor::BytecodeArrayAccessor"
VERSION_BYTECODESIZE = "v8::internal::interpreter::BytecodeArrayAccessor::current_bytecode_size"
VERSION_UPDATEOFFSETFROMINDEX = "v8::internal::interpreter::BytecodeArrayRandomIterator::UpdateOffsetFromIndex"

# V8 VERSION 8.2.0
VERSION_READFIELD = "v8::internal::Object::ReadField"

# V8 VERSION 8.2.297.3
VERSION_GET = "v8::internal::interpreter::(anonymous namespace)::OnHeapBytecodeArray::get"
VERSION_REF = "v8::internal::compiler::BytecodeArrayRef::get"

# V8 OPT. PHASE NAMES
GRAPHBUILDERPHASE = "GraphBuilderPhase"
COMPUTESCHEDULEPHASE = "ComputeSchedulePhase"
OSRDECONSTRUCTIONPHASE = "OsrDeconstructionPhase"
