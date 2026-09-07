"""Modern Lakeflow pipeline sources for NEMWEB.

This foundation module intentionally declares no datasets. Bronze, Silver and
Gold definitions are added by later implementation slices and must use
``pyspark.pipelines`` with supported Spark table reads.
"""
