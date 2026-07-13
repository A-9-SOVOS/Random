# RRann for game designers

## What it is

A **deterministic** RNG: same seed → same results. Built by harvesting residual
digits from dual-precision \(x^x\), then **culling the residual head** (default
2 digits) so run-biased leading digits are not used.

## Parallel model

```text
master_seed
   ├─ fork(0) / stream_seed(master, 0)  → chunk / region / worker 0
   ├─ fork(1)                           → worker 1
   └─ fork(n)                           → worker n
```

**Do not** share one advancing chain across threads/processes.  
**Do** give each unit of work its own `fork(id)` or `roll(seed, context, n)`.

`stream_seed(master, stream_id)` is the portable mix: `seed_i = mix(master, id)`.

## Value-bearing outcomes (max worry)

1. Roll on the **server** (or trusted service).
2. **Commit** seed before the roll window: `commit_seed(seed, game_id=..., season=...)`.
3. Issue **receipts**: `create_receipt(...)` → store/log JSON.
4. Optional **reveal**: publish seed; players run `python -m rrann verify receipt.json --seed ...`.

Never trust the client alone for paid loot / PvP rewards.

## Profiles

| Profile | Use |
|---------|-----|
| `cosmetic` | VFX, juice; soft health |
| `gameplay` | Default combat / proc-gen |
| `economy` | Stricter health (warn → fail); pair with receipts |

Continuous monitoring: `ContinuousHealth(window_bits=8192, profile="economy")` — ingest bits as you generate, call `check()` periodically.

## Loot rates & expected value

Theoretical rates come from **your table**, not from mysticism in the RNG.

```python
from rrann import simulate_loot, expected_value, normalize_weights

weights = [("common", 70), ("uncommon", 20), ("rare", 8), ("legendary", 2)]
report = simulate_loot(2.4, weights, trials=20_000, cumulative=False)
print(report.rates, report.expected_rates, report.max_abs_error)

values = {"common": 1, "uncommon": 5, "rare": 25, "legendary": 200}
print("EV (observed rates)", expected_value(report.rates, values))
print("EV (table rates)", expected_value(report.expected_rates, values))
```

CLI:

```bash
python -m rrann simulate --seed 2.4 --trials 10000
```

### Pity (design, not RNG)

Pity changes the **probability schedule** per pull. Use `pity_effective_rate` as a
design aid for long-run rate under hard/soft pity. Document pity rules in the
game UI; the RNG only supplies uniforms.

## Whitening (optional)

| Mode | Cost | Role |
|------|------|------|
| none (default) | 1× | Culled remainder as-is |
| `xor` adjacent | ~1× bits | Mild lag-1 scrub |
| `von_neumann` | ~¼ keep rate | Classic debias; slow for volume |

These are **mixers/filters**, not extra entropy from the universe.

## Cost

Each residual step uses high-precision `Decimal` power — roughly **millisecond-class**
per harvest on CPython (machine-dependent). Fine for loot/combat; for tight inner
loops, pre-bake with forks or use a faster mixer seeded from RRann offline.

## Cross-play / multiplayer

Native float diverge index can differ by platform if you ever depend on raw float
paths. Default remainder path still uses Decimal for the high-precision side.
For **bit-identical** cross-play, pin `algo_version`, same `cull_head`, and prefer
server authority. Soft-float / fixed-decimal ports are roadmap for engines.

## Local research artifacts

Optional lab outputs may live under `research/results/` (gitignored) — not required to
install or use the library.

## Non-claims

Not a CSPRNG, not FIPS, not a regulated casino RNG. See README.
