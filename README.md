# Visualizing The Intermediate Representation of Just-in-Time Compilers

### Requirements
* [Pin Tool](https://software.intel.com/content/www/us/en/develop/articles/pin-a-dynamic-binary-instrumentation-tool.html)
* [V8 executable - D8](https://v8.dev/docs)
* [Tracer and Trace Reader](https://github.com/skdebray/uacs-lynx.git)
  - You might need a permission to access the tracer tool.
* Python Version 3.7

### Chromium Bug Report
* [bug.chromium.org](https://bugs.chromium.org/p/v8/issues/list?q=component%3DCompiler%20type%3DBug)

### Steps
1. git clone https://github.com/hlim1/JITCompilerIRViz.git
2. Checkout to the target Git commit of V8 version that holds a bug.
    - e.g. git checkout 1006f3cd23d1cd7134452c987d10a124aab1d350
3. Modify the _GenerateBytecodeHandler_ function in _v8/src/interpreter/interpreter-generator.cc_ to print the list of bytecodes.
    - e.g. printf("%hhx;", bytecode); std::cout << bytecode << std::endl;
5. Build V8 executable (D8) using GN by following the instruction on V8 documentation.
    - list of bytecode (Hex:Ascii) will be printed during the build.
6. Convert printed bytecode list to hex to json file under the format _{"hex":"Ascii"}_.
    - We provide _bytecode_json_generator.py_ to generate the json file if the user used our example in the step 3.
    - python3 bytecode_json_generator.py -f _bytecode_list_
7. Collect Proof-of-Concept (PoC) code from the bug report.
8. Move to src file.
    - cd JITCompilerIRViz/src
10. Run Main.py with the options.
    - python3 Main.py 
              -f _PoC.js_
              -e _d8 executable_
              -b _bytecode json file_
              -d _directory to store generated temporary files_
              -n _number of PoCs to generate_
              -o _output csv file name_
