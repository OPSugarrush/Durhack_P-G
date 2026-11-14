"""NeedState Engine: local receipt research tools."""
import os
# Small repeated matrices perform better without a large BLAS thread pool.
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
