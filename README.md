
![Image](https://i.imgur.com/hEnU3MI.png)

<div align="center">

[![pip install grapycal grapycal-builtin](https://img.shields.io/badge/pip_install-grapycal_grapycal--builtin-purple)](https://pypi.org/project/grapycal/)
[![PyPI - Downloads](https://img.shields.io/pypi/dw/grapycal)](https://pypi.org/project/grapycal/)
[![License](https://img.shields.io/github/license/Grapycal/Grapycal)](./LICENSE)


[![Discord](https://img.shields.io/discord/1094532480721236041?logo=discord&labelColor=white&color=5865F2)](https://discord.gg/adNQcS42CT)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen)](https://github.com/Grapycal/Grapycal/pulls)
[![GitHub contributors](https://img.shields.io/github/contributors/Grapycal/grapycal)](https://github.com/Grapycal/Grapycal/graphs/contributors)
</div>
Grapycal is a general-purpose visual programming language based on Python. It provides a web-based editor for writing and running programs as a graph.

The goal of this project is to make a programming language align with human perception at best, while being powerful with the help of Python, its backend.


## Documentation

The full documentaition can be found [here](https://docs.grapycal.org/).

## Get Started

```bash
pip install grapycal grapycal-builtin
grapycal # Grapycal will open at localhost:9001
```

If you have any questions or ideas to share, feel free to join the [Discord server](https://discord.gg/adNQcS42CT).

## Contribute


Grapycal is still in its early stage. Any contribution is welcome! Currently, most of our efforts are on the backend (the core of Grapycal) and extensions (nodes with various functionalities), but it's also helpful to improve the frontend and the documentation.

To contribute, please refer to the [Contribution guide](https://docs.grapycal.org/contribution_guide/contribution.html) to get started. The [Discussion: Plans](https://github.com/Grapycal/Grapycal/discussions/categories/plans) forum contains the current plans for Grapycal and is a good place to start.

To discuss, feel free to go to [Discussion](https://github.com/Grapycal/Grapycal/discussions) or join the [Discord server](https://discord.gg/adNQcS42CT).


## Features:

- Interactive: On the GUI, users can run different parts of the graph in arbitrary order, watch variables in real-time, and easily track the active node while the program runs.

- Dynamic: Grapycal allows users to modify the running graph for instant changes in its behavior. That includes adjusting parameters, adding or removing nodes from a workflow, and terminating a loop.

- Extendable: Grapycal provides a set of API for creating custom nodes for arbitary domain, such as deep learning, robotics, or music synthesis.

- Collaborative: Custom nodes definitions can be shared as Python packages. Thus, nodes for various domains can be mixed in a graph to form a powerful tool or a creative artwork (I’ll create some examples when I have time). What’s more, Grapycal supports real-time collaboration, allowing a group of people to work on the same graph over the Internet.

Grapycal is not (yet):

- Fast: Grapycal is yet another layer of abstraction on top of Python. Some overhead is introduced for its interactivity and dynamics. However, the overhead would be relatively small if the graph doesn’t run at a high frequency ( less than ~1000 node runs per second ). For example, if your program mainly computes with C extensions (such as NumPy) or uses GPU heavily (such as deep learning tasks), there will be little impact on performance.

- Stable: Grapycal is not heavily tested to ensure the graph always runs as expected.

## Motivation

In our daily lives, countless ideas emerge in our minds, only to be dismissed because the perceived cost of realizing them is too high. Over time, sadly, we tend to forget our inherent creativity.

The mission of Grapycal is to push more ideas over the line to be worthy of trying out.

Grapycal is helpful for conducting experiments, including training AI, physical simulations, data analysis, computer art, and more. These experiments require repeated parameter adjustments, swapping certain components of models, while simultaneously observing the phenomena generated by different parameters. We then use human judgment combined with domain knowledge to deduce the best model or other conclusions.

In this back-and-forth process between humans and machines, using traditional Python execution methods or Jupyter notebooks can be cumbersome. Therefore, we need the higher interactivity provided by Grapycal.



## Dependencies

Grapycal and its dependences consist of the following 6 packages:

- [Grapycal/backend](https://github.com/Grapycal/Grapycal): Included in this repo, including the backend code of the Grapycal main application

- [Grapycal/frontend](https://github.com/Grapycal/Grapycal): Included in this repo, including the frontend code of the Grapycal main application

- [Topicsync](https://github.com/eri24816/Topicsync) and [ObjectSync](https://github.com/eri24816/ObjectSync): Backend dependencies. Python packages.

- [topicsync-client](https://github.com/eri24816/topicsync-client) and [objectsync-client](https://github.com/eri24816/ObjectSyncClient_ts): Frontend dependencies. npm packages.

## Acknowledgement

Grapycal is inspired by these amazing projects. Also take a look at them

- [Ryven](https://github.com/leon-thomm/Ryven)

- Unity shader graph

- Blender node editor

- [Scratch](https://scratch.mit.edu/)

- [Jupyter Notebook](https://github.com/jupyter/notebook)


These tools or libraries help Grapycal a lot:

- [Python](https://python.org/)

- [TypeScript](https://typescriptlang.org/)

- [Poetry](https://python-poetry.org/)

- [Commitizen](https://github.com/commitizen-tools/commitizen)

- [Three.js](https://threejs.org/)

- [Sphinx](https://www.sphinx-doc.org/)

## Star History

<a href="https://star-history.com/#Grapycal/Grapycal&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=Grapycal/Grapycal&type=Date&theme=dark" />
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=Grapycal/Grapycal&type=Date" />
    <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=Grapycal/Grapycal&type=Date" />
  </picture>
</a>
