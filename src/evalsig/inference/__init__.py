"""Pure-math inference primitives. NumPy/SciPy only; no I/O."""
from evalsig.inference.paired import (
    PairedOutcome,
    paired_t_test,
    paired_permutation_test,
    paired_bootstrap_ci,
)
from evalsig.inference.unpaired import (
    UnpairedOutcome,
    unpaired_t_test,
    unpaired_permutation,
    unpaired_bootstrap,
)
from evalsig.inference.mcnemar import mcnemar_test, McNemarOutcome
from evalsig.inference.cluster_bootstrap import (
    cluster_bootstrap_ci,
    ClusterBootstrapOutcome,
)
from evalsig.inference.mde import mde, required_n, estimate_icc
from evalsig.inference.power import power_for_delta
from evalsig.inference.effect_size import (
    EffectSize,
    cohens_d,
    cohens_d_paired,
    cliffs_delta,
)
from evalsig.inference.sequential import (
    SequentialOutcome,
    confidence_sequence,
    sequential_gate,
)
from evalsig.inference.multiplicity import (
    MultipleTestResult,
    bonferroni,
    holm,
    benjamini_hochberg,
)

__all__ = [
    # paired
    "PairedOutcome",
    "paired_t_test",
    "paired_permutation_test",
    "paired_bootstrap_ci",
    # unpaired
    "UnpairedOutcome",
    "unpaired_t_test",
    "unpaired_permutation",
    "unpaired_bootstrap",
    # mcnemar
    "mcnemar_test",
    "McNemarOutcome",
    # cluster bootstrap
    "cluster_bootstrap_ci",
    "ClusterBootstrapOutcome",
    # mde / power
    "mde",
    "required_n",
    "estimate_icc",
    "power_for_delta",
    # effect size
    "EffectSize",
    "cohens_d",
    "cohens_d_paired",
    "cliffs_delta",
    # sequential
    "SequentialOutcome",
    "confidence_sequence",
    "sequential_gate",
    # multiplicity
    "MultipleTestResult",
    "bonferroni",
    "holm",
    "benjamini_hochberg",
]
