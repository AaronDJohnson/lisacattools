# -*- coding: utf-8 -*-
# lisacattools - A small example package for using LISA catalogs
# Copyright (C) 2020 - 2025 - James I. Thorpe, Tyson B. Littenberg, Jean-Christophe Malapert
# This file is part of lisacattools <https://github.com/tlittenberg/lisacattools>
# SPDX-License-Identifier: Apache-2.0

"""Module implemented the UCB catalog."""

import pandas as pd

from .hdf5 import Hdf5Catalog
from .hdf5 import Hdf5Catalogs


class UcbCatalog(Hdf5Catalog):
    """Implementation of the Ucb catalog."""


class UcbCatalogs(Hdf5Catalogs):
    """Implementation of the UCB catalogs.

    The catalogs are sorted by "Observation Time". The posterior samples
    of each source are read from the file in the "chain file" column of the
    detections.
    """

    CATALOG_CLASS = UcbCatalog
    TIME_COLUMNS = ["Observation Time"]

    def get_lineage(self, cat_name: str, src_name: str) -> pd.DataFrame:
        raise NotImplementedError(
            "Get_lineage is not implemented for this catalog !"
        )

    def get_lineage_data(self, lineage: pd.DataFrame) -> pd.DataFrame:
        raise NotImplementedError(
            "Get_lineage_data is not implemented for this catalog !"
        )
