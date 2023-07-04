# Visualizing The Intermediate Representation JIT Compilers

### Publication

Lim, H., Kobourov, S. (2021). Visualizing JIT Compiler Graphs. In: Purchase, H.C., Rutter, I. (eds) Graph Drawing and Network Visualization. GD 2021. Lecture Notes in Computer Science(), vol 12868. Springer, Cham. https://doi.org/10.1007/978-3-030-92931-2_10

### Requirements
* [Pin Tool](https://software.intel.com/content/www/us/en/develop/articles/pin-a-dynamic-binary-instrumentation-tool.html)
* [V8 executable - D8](https://v8.dev/docs)
* [Tracer and Trace Reader](https://github.com/skdebray/uacs-lynx.git)
  - You might need a permission to access the tracer tool.
* Python Version 3.7

### Chromium Bug Report Site
* [bug.chromium.org](https://bugs.chromium.org/p/v8/issues/list?q=component%3DCompiler%20type%3DBug)

### Steps
1. git clone https://github.com/hlim1/JITCompilerIRViz.git
2. Checkout to the target Git commit of V8 version that holds a bug.
    - e.g. _git checkout 1006f3cd23d1cd7134452c987d10a124aab1d350_
3. Modify the _GenerateBytecodeHandler_ function in _v8/src/interpreter/interpreter-generator.cc_ to print the list of bytecodes.
    - e.g. _printf("%hhx;", bytecode); std::cout << bytecode << std::endl;_
4. Build V8 executable (D8) using GN by following the instruction on V8 documentation.
    - list of bytecode (Hex:Ascii) will be printed during the build.
5. Convert printed bytecode list to hex to json file under the format _{"hex":"Ascii"}_.
    - We provide _bytecode_json_generator.py_ to generate the json file if the user used our example in the step 3.
    - _python3 bytecode_json_generator.py -f _bytecode_list__
6. Collect Proof-of-Concept (PoC) code from the bug report.
7. Move to src file.
    - cd JITCompilerIRViz/src
8. Run Main.py with the options.
    - _python3 Main.py 
              -f _PoC.js_
              -e _d8_executable_
              -b _bytecode_json_file_
              -d _directory_to_store_generated_temporary_files_
              -n _number_of PoCs_to_generate_
              -o _output_csv_file_name__
9. Navigate to [MetroSet](https://metrosets.ac.tuwien.ac.at/)
10. Check the CSV file was generated.
11. Follow the instruction on MetroSet to generate the map.
