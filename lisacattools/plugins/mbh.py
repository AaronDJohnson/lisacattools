# -*- coding: utf-8 -*-
# lisacattools - A small example package for using LISA catalogs
# Copyright (C) 2020 - 2025 - James I. Thorpe, Tyson B. Littenberg, Jean-Christophe Malapert
# This file is part of lisacattools <https://github.com/tlittenberg/lisacattools>
# SPDX-License-Identifier: Apache-2.0

"""Module implemented the MBH catalog."""

from typing import Optional

from .hdf5 import Hdf5Catalog
from .hdf5 import Hdf5Catalogs


class MbhCatalog(Hdf5Catalog):
    """Implementation of the Mbh catalog."""


class MbhCatalogs(Hdf5Catalogs):
    """Implementation of the MBH catalogs."""

    CATALOG_CLASS = MbhCatalog
    TIME_COLUMNS = ["observation week", "Observation Week"]
    LINEAGE_COLUMNS = [
        "Mass 1",
        "Mass 2",
        "Spin 1",
        "Spin 2",
        "Ecliptic Latitude",
        "Ecliptic Longitude",
        "Luminosity Distance",
        "Barycenter Merge Time",
        "Merger Phase",
        "Polarization",
        "cos inclination",
    ]

    def __init__(
        self,
        path: str,
        accepted_pattern: Optional[str] = "MBH_wk*C.h5",
        rejected_pattern: Optional[str] = None,
        *args,
        **kwargs,
    ):
        """Init the MbhCatalogs by reading all catalogs with a specific
        pattern in a given directory and rejecting files by another pattern.

        The list of catalogs is sorted by "observation week"

        Args:
            path (str): directory
            accepted_pattern (str, optional): pattern to accept files.
            Defaults to "MBH_wk*C.h5".
            rejected_pattern (str, optional): pattern to reject files.
            Defaults to None.

        Raises:
            ValueError: no files found matching the accepted and rejected
            patterns.
        """
        super().__init__(
            path, accepted_pattern, rejected_pattern, *args, **kwargs
        )
