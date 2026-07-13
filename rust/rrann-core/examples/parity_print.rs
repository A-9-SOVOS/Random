//! Print JSON array of harvest values for Python parity script.
//! Seeds come from tests/vectors.json when present, else a built-in set.
use rrann_core::harvest::{extract_bits, extract_float, harvest};
use std::fs;
use std::path::PathBuf;

fn seeds() -> Vec<f64> {
    let mut path = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    path.push("../../tests/vectors.json");
    if let Ok(data) = fs::read_to_string(&path) {
        if let Ok(v) = serde_json::from_str::<serde_json::Value>(&data) {
            if let Some(cases) = v["cases"].as_array() {
                return cases
                    .iter()
                    .filter_map(|c| c["seed"].as_f64())
                    .collect();
            }
        }
    }
    vec![2.4, 1.1, std::f64::consts::PI, 0.5]
}

fn main() {
    let mut cases = Vec::new();
    for seed in seeds() {
        let h = harvest(seed, 12);
        let bits = extract_bits(seed, 32, 2);
        cases.push(serde_json::json!({
            "seed": seed,
            "divergence_index": h.divergence_index,
            "digits": h.digits,
            "used_fallback": h.used_fallback,
            "extract_float_cull2": extract_float(seed, 2),
            "extract_bits32_cull2": bits,
        }));
    }
    print!("{}", serde_json::to_string(&cases).unwrap());
}
