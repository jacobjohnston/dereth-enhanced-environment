//! `ee-pack`: packs an art pack's folder into the one file the Dereth client opens, byte for byte
//! as Pyreal's `pyreal-art pack` packs it, with only the code that packing runs.
//!
//! ```text
//! ee-pack <folder> [--out <file>] [--layout 1|2] [--check]
//! ```
//!
//! The file is `--out`, or `<folder>.dat` beside the folder. `--layout 2` stores each record as a
//! zstd frame where that is shorter; layout 1, the default, stores each as it is. With `--check`
//! it writes nothing and says whether that file is what the folder packs into now, and which
//! records are not.
//!
//! Where each module comes from in Pyreal, trimmed to what packing runs:
//!
//! - `pack`: `tools/art/src/pack.rs`, and this file from `tools/art/src/main.rs`.
//! - `art_pack`, `packed`, `images`, `materials`, `gltf`, `cards`: the `pyreal-art-pack` crate
//!   (`pyreal/client/crates/art-pack/src/`), `art_pack` from its `lib.rs`.
//! - `block_codec`: `pyreal-codecs` (`pyreal/client/crates/codecs/src/block_codec.rs`).
//! - `manifest`: `pyreal-assets` (`core/assets/src/art_pack.rs`, `fingerprint.rs`).
//! - `dat`: `pyreal-dat` (`core/dat/src/write.rs`, `container.rs`, `layout.rs`, `btree.rs`).
//! - `math`: `pyreal-primitives` (`core/primitives/src/num/math.rs`).

mod art_pack;
mod block_codec;
mod cards;
mod dat;
mod gltf;
mod images;
mod manifest;
mod materials;
mod math;
mod pack;
mod packed;

use std::path::PathBuf;
use std::process::ExitCode;

use images::Image;
use pack::Freshness;

const USAGE: &str = "ee-pack <folder> [--out <file>] [--layout 1|2] [--check]";

/// The folder, its file, its layout (1 unless `--layout` says) and whether it only checks.
fn options(args: &[String]) -> Result<(PathBuf, PathBuf, u32, bool), String> {
    let mut dir = None;
    let mut out = None;
    let mut layout = packed::PLAIN;
    let mut check = false;
    let mut it = args.iter();
    while let Some(a) = it.next() {
        match a.as_str() {
            "--out" => {
                out = Some(PathBuf::from(
                    it.next().ok_or_else(|| format!("{a} needs a value"))?,
                ));
            }
            "--layout" => {
                layout = it
                    .next()
                    .and_then(|v| v.parse().ok())
                    .ok_or_else(|| format!("{a} needs 1 or 2"))?;
            }
            "--check" => check = true,
            other if dir.is_none() && !other.starts_with("--") => dir = Some(PathBuf::from(other)),
            other => return Err(format!("unknown argument {other:?}")),
        }
    }
    let dir = dir.ok_or("no folder named")?;
    let out = out.unwrap_or_else(|| pack::default_out(&dir));
    Ok((dir, out, layout, check))
}

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let (dir, out, layout, check) = match options(&args) {
        Ok(o) => o,
        Err(e) => {
            eprintln!("ee-pack: {e}\nusage: {USAGE}");
            return ExitCode::FAILURE;
        }
    };
    let started = std::time::Instant::now();
    if check {
        return match pack::check(&dir, &out, layout) {
            Ok(Freshness::Current) => {
                println!("{} is what {} packs into", out.display(), dir.display());
                ExitCode::SUCCESS
            }
            Ok(Freshness::Stale(lines)) => {
                eprintln!("{} is stale; pack {} again", out.display(), dir.display());
                for line in lines {
                    eprintln!("  {line}");
                }
                ExitCode::FAILURE
            }
            Ok(Freshness::Missing) => {
                eprintln!("{} is not there; pack {}", out.display(), dir.display());
                ExitCode::FAILURE
            }
            Err(e) => {
                eprintln!("ee-pack: {e}");
                ExitCode::FAILURE
            }
        };
    }
    match pack::pack(&dir, &out, layout) {
        Ok(r) => {
            for problem in &r.problems {
                eprintln!("left out: {problem}");
            }
            println!(
                "wrote {}: the {:?} pack, {} records, {} MB, in {:.1} s",
                r.out.display(),
                r.name,
                r.records,
                r.bytes.div_ceil(1 << 20),
                started.elapsed().as_secs_f64()
            );
            ExitCode::SUCCESS
        }
        Err(e) => {
            eprintln!("ee-pack: {e}");
            ExitCode::FAILURE
        }
    }
}
