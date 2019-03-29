# Processor Functions

This directory contains a library of functions available to the credential processor.

Files can contain several functions. Subdirectories are supported if you wish to organize modules into directories.

Reference a function in the credential processor configuration using dot-notation. e.g., `relative.path.to.file.function_name`. In this example, the processor will look for a function called `function_name` in the file `relative/path/to/file.py`. Directory paths are relative to this directory.