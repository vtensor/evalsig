# Clustered standard errors

If items in your eval naturally belong to groups (a passage with multiple
questions, a template that spawns many problems, a stem with several
follow-ups), you cannot treat them as independent. The naive standard
error will be too narrow and your false-positive rate will be much higher
than the alpha you asked for.

## The model

Suppose the per-item difference between two runs decomposes as

```
d_i = w_{cluster(i)} + e_i
```

`w_k` is a *cluster-level* shift: every item in cluster `k` gets the same
push. `e_i` is the per-item residual. Even under the null (mean of d is
zero), a single eval run sees one realization of the `w_k` draws, which
biases item-level inference.

## What goes wrong without clustering

We ran 600 simulations under the null with 50 clusters of 10 items
(mean within-cluster correlation 0.71). The naive paired bootstrap
rejected the null in 43.2% of runs. The target was 5%.

In other words: ship 100 candidates that are not actually better and the
naive test would let about 43 of them through. The cluster bootstrap
brings that back down to 5.5%, which is what you wanted.

You can reproduce this with:

```bash
python research/validate.py
```

See `experiment_2_clustered_typeI` in `research/validate.py`.

## How EVALSIG handles it

If your RunFrame items have `cluster_id` set and you pass `cluster=<name>`
to `compare()` (or `--cluster <name>` on the CLI), EVALSIG switches the
auto method to the cluster bootstrap, which resamples *whole clusters*
with replacement.

```python
from evalsig import compare

result = compare(a, b, cluster="passage_id", alpha=0.05)
print(result.method)        # 'cluster_bootstrap'
print(result.n_clusters)    # e.g. 200
```

The MDE returned in this case includes a design-effect correction:

```
deff   = 1 + (mean_cluster_size - 1) * icc
n_eff  = n_pairs / deff
MDE    = (z_alpha + z_beta) * sd_diff / sqrt(n_eff)
```

`icc` is the within-cluster correlation, estimated automatically from the
data. The design effect tells you how much the clustering "wastes" your
sample: with ICC = 0.20 and 10-item clusters, the design effect is 2.8,
so your effective N is roughly a third of your nominal N.

## The CLI flag

```bash
evalsig gate \
  --baseline a.json --candidate b.json \
  --cluster passage_id \
  --min-delta 0.005 --alpha 0.05 --power 0.80
```

`--cluster` accepts any field name that exists as `cluster_id` on the
items.

## How to estimate cluster size and ICC in advance

When planning a new eval suite, use:

```python
from evalsig.inference.mde import required_n

n = required_n(target_delta=0.01, sd_diff=0.3,
               icc=0.15, mean_cluster_size=8,
               alpha=0.05, power=0.80, one_sided=True)
print(n)  # 1437 items (vs ~588 without clustering)
```

The clustering inflates your required sample size; planning for it up
front avoids a "we have 1000 items, why is everything inconclusive?"
debugging round.

## What you should not do

* Do **not** drop the cluster id and pretend items are independent. The
  CI will be too narrow.
* Do **not** average within clusters and then run an item-level test on
  the averages. That throws away the within-cluster information and
  usually loses more power than the clustering would have cost.
* Do **not** "fix" the cluster bootstrap by using more resamples. The
  resamples need to resample clusters, not items.

## See also

* [MDE and power](mde-and-power.md): how the design effect propagates.
* [What evalsig solves](what-evalsig-solves.md): why we put cluster-aware
  inference front and center.
