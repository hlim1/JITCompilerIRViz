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
3. Build V8 executable (D8) by following the instructions on V8 documentation.
4. 
