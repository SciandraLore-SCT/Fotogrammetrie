# Objective

A project to enable the visualization of photogrammetry in environments such as caving and environments with low hardware levels and low energy consumption, as well as being a plug-in.

# Photogrammetry

An html page for viewing .glb files with textures

A standalone program featured in python for any devices

# Limitations and issues

Limitations of html version:
- Does not support files larger than 600 MB
- Supports textures via .jpg, .png, .bmp, and .webp files 

Limitations of standalone file:
- Working progress for a Windows version
- Work in progress for a Linux distro version
- No Apple version available
- Not compatible with Android devices

# Working progress

### Standalone programm

- Working whit python library 
    - PyOpenGL 
    - trimesh   
    - numpy
    - pyglet

- Issues and bugs
    - Very long loading
    - Small bug whit visualize the 3D model
    - problem with the opacity of the obj file
    - Ineffency whit very large file like >1GB

- Working progress
    - Fixing problem with obj file opacity
    - Builder for the final standalone
    - Windows version
    - Windows GUI version
    

### HTML version 

- Issues and bugs
    - Can't visualize obj file more than 1.5 GB
    - Little buggy

- NOT anymore working in progress
    - browser usually limits itself to only 2 GB of RAM per tab, so only small obj files 


