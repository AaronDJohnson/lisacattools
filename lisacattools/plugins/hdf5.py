# -*- coding: utf-8 -*-
# lisacattools - A small example package for using LISA catalogs
# Copyright (C) 2020 - 2025 - James I. Thorpe, Tyson B. Littenberg, Jean-Christophe Malapert
# This file is part of lisacattools <https://github.com/tlittenberg/lisacattools>
# SPDX-License-Identifier: Apache-2.0

"""Shared implementation of catalogs stored in HDF5 files.

Each catalog file contains:
- a ``metadata`` table, indexed by catalog name
- a ``detections`` table, indexed by source name
- a ``<source>_chain`` table with the posterior samples of each source

The posterior samples are read from the catalog file, unless the
``detections`` table has a ``chain file`` column. In that case, the samples
are read from that file, relative to the directory of the catalog.

Source types implement a plugin by subclassing ``Hdf5Catalogs`` and
``Hdf5Catalog`` and setting ``Hdf5Catalogs.CATALOG_CLASS``.
"""

import glob
import os
from itertools import chain
from typing import List
from typing import Optional
from typing import Set
from typing import Type
from typing import Union

import numpy as np
import pandas as pd

from ..catalog import GWCatalog
from ..catalog import GWCatalogs
from ..monitoring import UtilsMonitoring, LogLevel
from ..utils import CacheManager


def _find_column(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    """Returns the first candidate that is a column of the data frame.

    Args:
        df (pd.DataFrame): data frame
        candidates (List[str]): column names, in order of preference

    Returns:
        Optional[str]: the column name or None when no candidate is found
    """
    return next((col for col in candidates if col in df.columns), None)


def _is_name(value) -> bool:
    """Returns True when the value is a non-empty catalog or source name."""
    return isinstance(value, str) and value != ""


class Hdf5Catalog(GWCatalog):
    """Implementation of a catalog stored in an HDF5 file."""

    def __init__(self, name: str, location: str):
        """Init the catalog with a name and a location

        Args:
            name (str): name of the catalog
            location (str): location of the catalog
        """
        self._name = name
        self._location = location
        with pd.HDFStore(location, "r") as store:
            self._datasets = store.keys()

    @CacheManager.get_cache_pandas(
        keycache_argument=[1, 2], level=LogLevel.DEBUG
    )
    def _read_chain_file(
        self, source_name: str, chain_file: str
    ) -> pd.DataFrame:
        """Read the posterior samples of a source in a chain file

        Args:
            source_name (str): name of the source
            chain_file (str): path of the file to load

        Returns:
            pd.DataFrame: posterior samples of the source
        """
        return pd.read_hdf(chain_file, key=f"{source_name}_chain")

    def _chain_file(self, source_name: str) -> str:
        """Returns the path of the file holding the samples of a source.

        Args:
            source_name (str): name of the source

        Returns:
            str: path of the chain file
        """
        detections = self.get_dataset("detections")
        if "chain file" not in detections.columns:
            return self.location
        return os.path.join(
            os.path.dirname(self.location),
            detections.loc[source_name]["chain file"],
        )

    @property
    @UtilsMonitoring.log_io(level=LogLevel.DEBUG)
    def datasets(self):
        """dataset.

        :getter: Returns the list of datasets
        :type: List
        """
        return self._datasets

    @UtilsMonitoring.log_io(level=LogLevel.DEBUG)
    def get_dataset(self, name: str) -> pd.DataFrame:
        """Returns a dataset based on its name.

        Args:
            name (str): name of the dataset

        Returns:
            pd.DataFrame: the dataset
        """
        return pd.read_hdf(self.location, key=name)

    @property
    @UtilsMonitoring.log_io(level=LogLevel.DEBUG)
    def name(self) -> str:
        return self._name

    @property
    @UtilsMonitoring.log_io(level=LogLevel.DEBUG)
    def location(self) -> str:
        return self._location

    @UtilsMonitoring.log_io(level=LogLevel.DEBUG)
    def get_detections(
        self, attr: Union[List[str], str] = None
    ) -> Union[List[str], pd.DataFrame, pd.Series]:
        detections = self.get_dataset("detections")
        return (
            list(detections.index) if attr is None else detections[attr].copy()
        )

    @UtilsMonitoring.log_io(level=LogLevel.DEBUG)
    def get_attr_detections(self) -> List[str]:
        return list(self.get_dataset("detections").columns)

    @UtilsMonitoring.log_io(level=LogLevel.DEBUG)
    def get_median_source(self, attr: str) -> pd.DataFrame:
        detections = self.get_dataset("detections")
        values = detections[attr]
        source_idx = detections.index[
            np.argmin(np.abs(np.array(values) - values.median()))
        ]
        return detections.loc[[source_idx]]

    @UtilsMonitoring.log_io(level=LogLevel.DEBUG)
    @UtilsMonitoring.time_spent(level=LogLevel.DEBUG, threshold_in_ms=100)
    def get_source_samples(
        self, source_name: str, attr: List[str] = None
    ) -> pd.DataFrame:
        samples = self._read_chain_file(
            source_name, self._chain_file(source_name)
        )
        return samples if attr is None else samples[attr].copy()

    @UtilsMonitoring.log_io(level=LogLevel.DEBUG)
    def get_attr_source_samples(self, source_name: str) -> List[str]:
        return list(self.get_source_samples(source_name).columns)

    @UtilsMonitoring.log_io(level=LogLevel.TRACE)
    def describe_source_samples(self, source_name: str) -> pd.DataFrame:
        return self.get_source_samples(source_name).describe()

    def __repr__(self):
        return f"{type(self).__name__}({self._name!r}, {self._location!r})"

    def __str__(self):
        return f"{type(self).__name__}: {self._name} {self._location}"


class Hdf5Catalogs(GWCatalogs):
    """Implementation of time-evolving catalogs stored in HDF5 files."""

    EXTRA_DIR = "extra_directories"
    CATALOG_CLASS: Type[Hdf5Catalog] = Hdf5Catalog
    TIME_COLUMNS = ["Observation Week", "observation week", "Observation Time"]
    PARENT_COLUMNS = ["Parent", "parent"]
    # sample columns returned by get_lineage_data; None returns all of them
    LINEAGE_COLUMNS: Optional[List[str]] = None

    def __init__(
        self,
        path: str,
        accepted_pattern: Optional[str] = "*.h5",
        rejected_pattern: Optional[str] = "*chain*",
        *args,
        **kwargs,
    ):
        """Init the catalogs by reading all catalogs with a specific
        pattern in a given directory and rejecting files by another pattern.

        The list of catalogs is sorted by the first column of TIME_COLUMNS
        found in the metadata.

        Args:
            path (str): directory
            accepted_pattern (str, optional): pattern to accept files.
            Defaults to "*.h5".
            rejected_pattern (str, optional): pattern to reject files.
            Defaults to "*chain*".

        Raises:
            ValueError: no files found matching the accepted and rejected
            patterns.
        """
        self.path = path
        self.accepted_pattern = accepted_pattern
        self.rejected_pattern = rejected_pattern
        self.extra_directories = kwargs.get(self.EXTRA_DIR, list())
        directories = self.extra_directories + [self.path]
        self.cat_files = self._search_files(
            directories, accepted_pattern, rejected_pattern
        )
        if len(self.cat_files) == 0:
            raise ValueError(
                f"no files found matching the accepted "
                f"({self.accepted_pattern}) and rejected "
                f"({self.rejected_pattern}) patterns in {directories}"
            )
        self._metadata = pd.concat(
            [self._read_cats(cat_file) for cat_file in self.cat_files]
        )
        time_column = _find_column(self._metadata, self.TIME_COLUMNS)
        if time_column is not None:
            self._metadata = self._metadata.sort_values(by=time_column)

    @staticmethod
    def _glob(directories: List[str], pattern: Optional[str]) -> Set[str]:
        """Returns the files matching a pattern in a list of directories.

        Args:
            directories (List[str]): directories to scan
            pattern (Optional[str]): pattern; None matches no file

        Returns:
            Set[str]: matching files
        """
        if pattern is None:
            return set()
        return set(
            chain.from_iterable(
                glob.glob(os.path.join(path, pattern)) for path in directories
            )
        )

    @UtilsMonitoring.log_io(level=LogLevel.DEBUG)
    def _search_files(
        self, directories: List[str], accepted_pattern, rejected_pattern
    ) -> List[str]:
        """Search files in directories according to a set of constraints :
        accepted and rejected patterns

        Args:
            directories (List[str]): List of directories to scan
            accepted_pattern ([type]): pattern to get files
            rejected_pattern ([type]): pattern to reject files

        Returns:
            List[str]: List of files
        """
        return sorted(
            self._glob(directories, accepted_pattern)
            - self._glob(directories, rejected_pattern)
        )

    @UtilsMonitoring.log_io(level=LogLevel.DEBUG)
    def _read_cats(self, cat_file: str) -> pd.DataFrame:
        """Reads the metadata of a given catalog and the location of the file.

        Args:
            cat_file (str): catalog to load

        Returns:
            pd.DataFrame: pandas data frame
        """
        df = pd.read_hdf(cat_file, key="metadata")
        df["location"] = cat_file
        return df

    def _metadata_value(self, cat_name: str, candidates: List[str]):
        """Returns a metadata value of a catalog.

        Args:
            cat_name (str): name of the catalog
            candidates (List[str]): column names, in order of preference

        Raises:
            KeyError: none of the candidates is a metadata column

        Returns:
            the value of the first candidate found in the metadata
        """
        column = _find_column(self.metadata, candidates)
        if column is None:
            raise KeyError(f"metadata has none of the columns {candidates}")
        return self.metadata.loc[cat_name][column]

    def _parent(self, df: pd.DataFrame, name: str) -> Optional[str]:
        """Returns the parent of a catalog or a source.

        Args:
            df (pd.DataFrame): metadata or detections
            name (str): name of the catalog or the source

        Returns:
            Optional[str]: the parent or None when df has no parent column
        """
        column = _find_column(df, self.PARENT_COLUMNS)
        return None if column is None else df.loc[name][column]

    @property
    @UtilsMonitoring.log_io(level=LogLevel.DEBUG)
    def metadata(self) -> pd.DataFrame:
        return self._metadata

    @property
    @UtilsMonitoring.log_io(level=LogLevel.TRACE)
    def count(self) -> int:
        return len(self.metadata.index)

    @property
    @UtilsMonitoring.log_io(level=LogLevel.TRACE)
    def files(self) -> List[str]:
        return self.cat_files

    @UtilsMonitoring.log_io(level=LogLevel.TRACE)
    def get_catalogs_name(self) -> List[str]:
        return list(self.metadata.index)

    @UtilsMonitoring.log_io(level=LogLevel.TRACE)
    def get_first_catalog(self) -> GWCatalog:
        return self.get_catalog(0)

    @UtilsMonitoring.log_io(level=LogLevel.TRACE)
    def get_last_catalog(self) -> GWCatalog:
        return self.get_catalog(self.count - 1)

    @UtilsMonitoring.log_io(level=LogLevel.TRACE)
    def get_catalog(self, idx: int) -> GWCatalog:
        location = self.metadata.iloc[idx]["location"]
        name = self.metadata.index[idx]
        return self.CATALOG_CLASS(name, location)

    @UtilsMonitoring.log_io(level=LogLevel.TRACE)
    def get_catalog_by(self, name: str) -> GWCatalog:
        return self.get_catalog(self.metadata.index.get_loc(name))

    @UtilsMonitoring.log_io(level=LogLevel.TRACE)
    @UtilsMonitoring.time_spent(level=LogLevel.DEBUG, threshold_in_ms=100)
    def get_lineage(self, cat_name: str, src_name: str) -> pd.DataFrame:
        dfs: List[pd.DataFrame] = list()
        while _is_name(src_name) and _is_name(cat_name):
            src = self.get_catalog_by(cat_name).get_dataset("detections")
            src = src.loc[[src_name]]
            week = self._metadata_value(cat_name, self.TIME_COLUMNS)
            src.insert(0, "Observation Week", week, True)
            src.insert(1, "Catalog", cat_name, True)
            dfs.append(src)
            cat_name = self._parent(self.metadata, cat_name)
            src_name = self._parent(src, src_name)

        lineage = pd.concat(dfs, axis=0)
        if "Log Likelihood" in lineage.columns:
            lineage = lineage.drop_duplicates(
                subset="Log Likelihood", keep="last"
            )
        return lineage.sort_values(by="Observation Week", ascending=True)

    @UtilsMonitoring.log_io(level=LogLevel.TRACE)
    @UtilsMonitoring.time_spent(level=LogLevel.DEBUG, threshold_in_ms=100)
    def get_lineage_data(self, lineage: pd.DataFrame) -> pd.DataFrame:
        epochs = list()
        for source_epoch in lineage.index:
            samples = self.get_catalog_by(
                lineage.loc[source_epoch]["Catalog"]
            ).get_source_samples(source_epoch)
            samples.insert(0, "Source", source_epoch)
            samples.insert(
                1,
                "Observation Week",
                lineage.loc[source_epoch]["Observation Week"],
            )
            epochs.append(samples)
        data = pd.concat(epochs)
        if self.LINEAGE_COLUMNS is None:
            return data
        return data[["Source", "Observation Week"] + self.LINEAGE_COLUMNS]

    def __repr__(self):
        return (
            f"{type(self).__name__}({self.path!r}, "
            f"{self.accepted_pattern!r}, {self.rejected_pattern!r}, "
            f"{self.extra_directories!r})"
        )

    def __str__(self):
        return (
            f"{type(self).__name__}: {self.path} {self.accepted_pattern!r} "
            f"{self.rejected_pattern!r} {self.extra_directories!r}"
        )
