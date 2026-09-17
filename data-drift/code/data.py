"""The paper's real-world streams: Electricity and CoverType, from MOA.

Read (2018) §6 evaluates on two benchmarks "from the data-streams literature
involving real-world data", sourced from https://moa.cms.waikato.ac.nz/datasets/:

    Electricity   45,312 instances   binary (UP/DOWN)     -- elecNormNew.arff
    CoverType    581,012 instances   7 classes            -- covtypeNorm.arff

Run ../data/fetch.sh first; the .arff files are gitignored (74 MB extracted).

CONTRACT. ArffStream yields the SAME 5-tuple as drift.Stream:

    (t, x_t, y_t, theta_t, C_t)

so every loop in experiments.py works unchanged. Two fields necessarily differ:

    theta_t  is always None -- real data has no ground-truth concept. Every
             theta-based metric -- tracking error, the angle between theta and
             theta_hat -- is therefore UNAVAILABLE here, by nature and not by
             omission. synthetic.py is where those questions can be asked.
    C_t      is not a latent concept id but a CANDIDATE CONTEXT: the observable
             periodic covariate (half-hour of day, day of week). That is exactly
             the c of context-driven distribution shift -- the thing the CDS
             literature says the model forgot to condition on. Whether it is the
             real explanation of Electricity's apparent drift is the question
             experiment B asks; here it is only a candidate.
"""
import os, zipfile

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")


def load_arff(path, max_rows=None):
    """Minimal ARFF reader -- pure stdlib, matching the rest of this repo.

    Returns (names, nominals, rows) where nominals maps an attribute name to its
    declared level list (None for numeric). Handles only what MOA's two files
    actually contain: numeric and nominal attributes, no quoting, no missing
    values (elecNormNew has already had ReplaceMissingValues applied -- see its
    @relation line, which records the Weka filter chain).
    """
    names, nominals, rows, in_data = [], {}, [], False
    with open(path) as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("%"):        # blank line or ARFF comment
                continue
            if not in_data:
                low = s.lower()
                if low.startswith("@attribute"):
                    # "@attribute day {1,2,3,4,5,6,7}" -> name="day", levels=[...]
                    # "@attribute period numeric"      -> name="period", levels=None
                    parts = s.split(None, 2)      # keep the type field intact
                    name, typ = parts[1], parts[2].strip()
                    names.append(name)
                    nominals[name] = ([v.strip() for v in typ[1:-1].split(",")]
                                      if typ.startswith("{") else None)
                elif low.startswith("@data"):
                    in_data = True                # everything after this is CSV
                continue
            rows.append(s.split(","))
            if max_rows and len(rows) >= max_rows:
                break                             # honour the paper's 10k subsets
    return names, nominals, rows


class ArffStream:
    """A prequential stream over an ARFF file, in original file order.

    Order matters and is never shuffled: these are time series, and the whole
    argument of the paper is that the ordering carries the drift.
    """

    def __init__(self, path, target, positive, drop=(), context=None,
                 max_rows=None, bias=True):
        self.names, self.nominals, self.rows = load_arff(path, max_rows)
        self.target   = target        # name of the class attribute
        self.positive = positive      # which level counts as y=1 (binarisation)
        self.bias     = bias          # append a constant 1.0 feature (intercept)
        self.context  = context       # attribute name used as C_t, or None
        # Feature columns: everything except the target and anything explicitly
        # dropped. Indices are resolved ONCE here, not per row.
        skip = set(drop) | {target}
        self.feat_idx = [i for i, n in enumerate(self.names) if n not in skip]
        self.ctx_idx  = self.names.index(context) if context else None
        # d is what the learners must be constructed with; +1 for the bias unit.
        self.d = len(self.feat_idx) + (1 if bias else 0)

    def __len__(self):
        return len(self.rows)

    def __iter__(self):
        for t, r in enumerate(self.rows, start=1):    # the paper indexes from 1
            # elecNormNew and covtypeNorm are both pre-normalised to [0,1] by
            # Weka's Normalize filter, so no scaling is applied here. Nominal
            # attributes that survive into feat_idx are read as their numeric
            # level label, which is meaningful for elec's day (1..7) only in the
            # ordinal sense -- see the note in fetch.sh.
            x = [float(r[i]) for i in self.feat_idx]
            if self.bias:
                x.append(1.0)                         # intercept: theta_hat has no
                                                      # separate bias term otherwise
            y = 1 if r[self.names.index(self.target)] == self.positive else 0
            c = r[self.ctx_idx] if self.ctx_idx is not None else None
            yield t, x, y, None, c                    # theta_t is None: see module docstring

    def take(self, n):
        out = []
        for row in self:
            out.append(row)
            if len(out) >= n: break                   # mirrors drift.Stream.take
        return out


# --- the two datasets, wired up exactly as the paper describes them ---------

def electricity(max_rows=None, context="period", drop=("date",)):
    """ELEC2. 45,312 instances; binary UP/DOWN.

    `date` is dropped by default: it is a monotone ramp 0->1 over the stream, so
    a linear model can use it to memorise the time index rather than the concept.

    NOTE a discrepancy worth flagging before citing: the paper says Electricity
    "has 6 attributes", but elecNormNew.arff declares 8 (date, day, period,
    nswprice, nswdemand, vicprice, vicdemand, transfer). Dropping date leaves 7.
    Which 6 the paper used is not stated. Our runs say 7 + bias; do not report
    them as matching the paper's feature set.
    """
    return ArffStream(os.path.join(DATA, "elecNormNew.arff"),
                      target="class", positive="UP", drop=drop,
                      context=context, max_rows=max_rows)


def covertype(max_rows=None, positive="2", context=None):
    """CoverType. 581,012 instances, 54 attributes, 7 forest-cover classes.

    The methods in methods.py are binary (predict returns P(y=1)), so the
    7-class problem is reduced to one-vs-rest on `positive`. Class 2 (Lodgepole
    Pine) is the majority at ~48.8%, which makes the binarised task closest to
    balanced. This is OUR reduction; the paper classifies all 7 classes, so our
    CoverType accuracies are NOT comparable to its Table 3 (92.6 - 93.9).
    """
    return ArffStream(os.path.join(DATA, "covtypeNorm.arff"),
                      target="class", positive=positive,
                      context=context, max_rows=max_rows)
