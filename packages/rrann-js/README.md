# @rrann/core (JS / three.js)

**OPEN_SEQUENCE step 2** (was open-list #2).

Browser helpers for deterministic forks, seed commits, and **soft residual harvest**
(WASM `rust_decimal` path — demos only; not CPython/MPFR-identical).

## Build WASM (optional, preferred)

```bash
export PATH="$HOME/.cargo/bin:$PATH"
rustup target add wasm32-unknown-unknown
cargo install wasm-pack   # once
cd packages/rrann-js
npm run build:wasm
```

## Demos

```bash
# from repo root
python3 -m http.server 8766
# open http://localhost:8766/web/three_scatter_demo.html
# open http://localhost:8766/web/seed_commit_demo.html
# open http://localhost:8766/web/extract_float_demo.html
```

## API

```js
import {
  init, streamSeed, commitSeedAsync, demoUnit,
  extractFloat, harvestDigits, divergenceIndex,
} from './src/index.js';
await init(); // load WASM
streamSeed(2.4, 0);
await commitSeedAsync(2.4, 'game', 's1');
demoUnit(2.4, 0, 12);       // [0,1) scatter helper
extractFloat(2.4, 2);       // culled residual (Rust harvest; not CPython-identical)
harvestDigits(2.4, 12);
divergenceIndex(2.4);
```

Rebuild WASM after Rust changes: `npm run build:wasm`.
