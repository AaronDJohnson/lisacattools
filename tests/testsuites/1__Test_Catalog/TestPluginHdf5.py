import os
import tempfile

import numpy as np
import pandas as pd

from lisacattools import GWCatalogs
from lisacattools import GWCatalogType

NB_SAMPLES = 50


def _samples(seed):
    rng = np.random.default_rng(seed)
    return pd.DataFrame(
        {
            "Luminosity Distance": rng.normal(1000.0, 10.0, NB_SAMPLES),
            "Ecliptic Latitude": rng.normal(0.1, 0.01, NB_SAMPLES),
        }
    )


def _write_catalog(directory, prefix, week, parent, sources, chain_file):
    """Write a catalog for a given week. Each source is a tuple
    (name, parent). When chain_file is True, the samples are written in a
    separate file referenced by the "chain file" column."""
    path = os.path.join(directory, f"{prefix}_wk{week:03d}.h5")
    name = f"{prefix}catalog_week{week:03d}"
    pd.DataFrame(
        {"Observation Week": [week], "Parent": [parent]}, index=[name]
    ).to_hdf(path, key="metadata")
    detections = pd.DataFrame(
        {
            "Parent": [src_parent for _, src_parent in sources],
            "Luminosity Distance": [1000.0 + week for _ in sources],
        },
        index=[src for src, _ in sources],
    )
    if chain_file:
        chain_name = f"{prefix}_wk{week:03d}_chain.h5"
        detections["chain file"] = chain_name
        chain_path = os.path.join(directory, chain_name)
    else:
        chain_path = path
    detections.to_hdf(path, key="detections")
    for seed, (src, _) in enumerate(sources):
        _samples(week * 100 + seed).to_hdf(chain_path, key=f"{src}_chain")
    return name


class TestPluginHdf5:
    """Synthetic EMRI catalogs with samples in the catalog files and SOBBH
    catalogs with samples in separate chain files. Source S1 is followed
    over 3 weeks; the catalogs are written in reverse order to check the
    sorting."""

    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dirs = {}
        for prefix, chain_file in [("EMRI", False), ("SOBBH", True)]:
            directory = os.path.join(self.tmp.name, prefix.lower())
            os.makedirs(directory)
            names = [f"{prefix}catalog_week{wk:03d}" for wk in (1, 2, 3)]
            _write_catalog(
                directory,
                prefix,
                3,
                names[1],
                [("S1_w3", "S1_w2"), ("S2_w3", "")],
                chain_file,
            )
            _write_catalog(
                directory,
                prefix,
                2,
                names[0],
                [("S1_w2", "S1_w1")],
                chain_file,
            )
            _write_catalog(
                directory, prefix, 1, "", [("S1_w1", "")], chain_file
            )
            self.dirs[prefix] = directory

    def _catalogs(self, prefix):
        return GWCatalogs.create(
            getattr(GWCatalogType, prefix), self.dirs[prefix]
        )

    def get_number(self, prefix):
        return self._catalogs(prefix).count

    def get_catalog_class(self, prefix):
        return type(self._catalogs(prefix).get_last_catalog()).__name__

    def get_catalogs_name(self, prefix):
        return self._catalogs(prefix).get_catalogs_name()

    def get_detections(self, prefix):
        return self._catalogs(prefix).get_last_catalog().get_detections()

    def get_samples_shape(self, prefix, source):
        catalog = self._catalogs(prefix).get_last_catalog()
        return list(catalog.get_source_samples(source).shape)

    def get_samples_differ(self, prefix):
        catalog = self._catalogs(prefix).get_last_catalog()
        s1 = catalog.get_source_samples("S1_w3")
        s2 = catalog.get_source_samples("S2_w3")
        return not s1.equals(s2)

    def get_lineage_weeks(self, prefix, source):
        catalogs = self._catalogs(prefix)
        lineage = catalogs.get_lineage(
            catalogs.get_catalogs_name()[-1], source
        )
        return [int(week) for week in lineage["Observation Week"]]

    def get_lineage_data_shape(self, prefix):
        catalogs = self._catalogs(prefix)
        lineage = catalogs.get_lineage(
            catalogs.get_catalogs_name()[-1], "S1_w3"
        )
        data = catalogs.get_lineage_data(lineage)
        return list(data.shape)
