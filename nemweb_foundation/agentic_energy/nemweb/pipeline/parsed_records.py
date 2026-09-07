"""Single declaration of the shared parsed-records fan-out view.

This module exists solely so the ``_nemweb_parsed_records`` temporary view is
declared exactly once.  ``io.py`` holds the reusable reader logic and is
imported by every Bronze dataset module; a ``pyspark.pipelines`` decorator
registers its dataset globally when the decorated function is evaluated, so
declaring the view inside ``io.py`` registered it once per importing module and
failed the update with ``Found duplicate dataset `_nemweb_parsed_records```
(observed on pipeline update 19d20ebe, 2026-09-02).

Only this file is listed as the pipeline library for the view.  Every Bronze
module reads it by name through ``io.section_stream``.
"""

from __future__ import annotations

from pyspark import pipelines as dp

from agentic_energy.nemweb.pipeline.io import read_parsed_records


@dp.temporary_view(name="_nemweb_parsed_records")
def nemweb_parsed_records():
    """Pipeline-private fan-out point; each parsed source file is read once."""

    return read_parsed_records(spark)  # noqa: F821 - pipeline-injected session
