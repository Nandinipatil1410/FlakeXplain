==================
CANNIER-Experiment
==================

This is the replication package for the `ESE <https://www.springer.com/journal/10664>`_ paper "Empirically Evaluating Flaky Test Detection Techniques Combining Test Case Rerunning and Machine Learning Models". Before proceeding, we recommend that you read the documentation for `pytest-CANNIER <https://github.com/flake-it/pytest-cannier>`_ and `CANNIER-Framework <https://github.com/flake-it/cannier-framework>`_.

Contents
========

- ``cannier-framework/`` Submodule of the CANNIER-Framework repository.
- ``Dockerfile`` Dockerfile to produce the ``cannier-experiment`` Docker image.
- ``LICENSE`` MIT license.
- ``output.zip`` Contains all the data, results, and figures from the paper. See the CANNIER-Framework repository for more details on its contents.
- ``pytest-cannier/`` Submodule of the pytest-CANNIER repository.
- ``README.rst`` This file.
- ``requirements.txt`` Dependencies for a virtual environment to run the experiment.
- ``schema.sql`` Schema for the database used by pytest-CANNIER to store results.
- ``subjects/`` A directory with subdirectories for each subject project. These contain the dependencies of the project in a file named ``requirements.txt``.
- ``subjects.json`` A `JSON <https://www.json.org/json-en.html>`_ file with details about each project.

Prerequisites
=============

You must install ``docker`` and ``virtualenv`` before running the experiment. We have only performed the experiment on Ubuntu 20.04 and Python 3.8. We cannot guarantee correct results with other environments.

Installation
============

Create a virtual environment with ``virtualenv --python={EXECUTABLE} venv`` where EXECUTABLE is the path to a Python executable (e.g. ``/usr/bin/python3.8``). Then, install CANNIER-Framework and the dependencies with ``venv/bin/pip install ./canner-framework -r requirements.txt``.

Usage
=====

To perform the experiment from start to finish, issue these commands in order:

1. ``docker build -t cannier-experiment .``
2. ``venv/bin/cannier run churn baseline shuffle``
3. ``venv/bin/cannier run features victim``
4. ``venv/bin/cannier collate``
5. ``venv/bin/cannier shap``
6. ``venv/bin/cannier preds config``
7. ``venv/bin/cannier preds best``
8. ``venv/bin/cannier preds features``
9. ``venv/bin/cannier points``
10. ``venv/bin/cannier figures``

If you are having trouble building the Docker image, you can download it pre-built `here <https://drive.google.com/file/d/10CiV7KdRNP3X3BvFM5YuEovmjztl1CUD/view?usp=share_link>`_ (around 7 GiB compressed). Once downloaded, uncompress and load into Docker using ``docker load < cannier-experiment.tar``.