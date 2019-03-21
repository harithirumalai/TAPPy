# TAPPy - The Temporal Analysis of Products(TAP) Analysis Web-App

### Authors: Hari Thirumalai and Lars. C Grabow
#### Chemical and Biomolecular Engineering, University of Houston, Houston, Texas

This is the repo containing ```TAPPy```, a ```Plotly Dash``` web-app that can process data recorded from TAP experiments. The app is under development, with new features and analysis tools implemented and pushed to the repo on a regular basis.

The structure of the app is as follows:
- ```app.py```: The main ```.py``` file that renders and functionalizes the app. Callbacks are defined for ```HTML``` and ```Javascript``` based interactive components and actions are performed based on user-selected arguments.
- ```workers.py```: The core processing modules including data processing and storage.
- ```layouts.py```: Consists of the ```HTML``` and ```Dash``` components that render the UI of the app.
- ```figures.py```: The code and structure used to render the scatter and scatter3D figures in the app.


