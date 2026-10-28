# -*- coding: utf-8 -*-
# lisacattools - A small example package for using LISA catalogs
# Copyright (C) 2020 - 2025 - James I. Thorpe, Tyson B. Littenberg, Jean-Christophe Malapert
# This file is part of lisacattools <https://github.com/tlittenberg/lisacattools>
# SPDX-License-Identifier: Apache-2.0

"""Module implemented the SOBBH (stellar origin black hole binary)
catalog."""

from .hdf5 import Hdf5Catalog
from .hdf5 import Hdf5Catalogs


class SobbhCatalog(Hdf5Catalog):
    """Implementation of the SOBBH catalog."""


class SobbhCatalogs(Hdf5Catalogs):
    """Implementation of the SOBBH catalogs."""

    CATALOG_CLASS = SobbhCatalog
