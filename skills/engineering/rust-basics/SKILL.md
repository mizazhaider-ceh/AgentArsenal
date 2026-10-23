---
name: rust-basics
description: Use when writing, building, or reviewing Rust programs on an
  authorized engineering task. Covers cargo project setup, build profiles,
  ownership and borrowing rules, Result and Option error handling, structs
  enums and pattern matching, unit and integration tests, clippy lints,
  rustfmt formatting, dependency auditing with cargo audit, and release
  binaries. Use when starting a Rust CLI or tool, or when reviewing Rust
  code for memory safety and correctness.
version: 1.0.0
domain: engineering
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [secure-coding, code-reviewer]
tools:
  - name: Rust
    version: 1.82
  - name: rustup
    version: 1.27
---

Rust gives C-like performance with compile-time memory safety: no null
pointer dereferences, no data races, no use-after-free, all enforced by
the borrow checker instead of a garbage collector. This skill covers
the working basics: setting up projects with cargo, thinking in
ownership, handling errors with `Result` and `Option`, testing, and
shipping audited release binaries. All examples target Rust 1.82.

## Quick Workflow

1. Install the toolchain with `rustup` and pin the channel per
   project with `rust-toolchain.toml` when reproducibility matters.
2. Scaffold with `cargo new` and keep `src/main.rs` (binary) or
   `src/lib.rs` (library) as the entry point.
3. Write small functions that take borrows (`&str`, `&[u8]`) instead
   of owned values where possible.
4. Return `Result` for fallible operations and `Option` for absent
   values; never `unwrap()` on untrusted paths.
5. Run `cargo fmt`, `cargo clippy`, and `cargo test` before every
   commit.
6. Audit dependencies with `cargo audit` and keep `Cargo.lock`
   committed for binaries.
7. Build release binaries with `cargo build --release` and strip
   symbols for deployment.
8. Document public APIs; the compiler enforces the rest.

## 1. Toolchain and first project

```bash
# Install rustup (the official toolchain manager)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source "$HOME/.cargo/env"
rustc --version
cargo --version

# Keep the toolchain current
rustup update

# Scaffold a binary project
cargo new portcheck --bin
cd portcheck
find . -type f | sort
```

```bash
cat > src/main.rs <<'EOF'
use std::net::{TcpStream, ToSocketAddrs};
use std::time::Duration;

fn check_port(host: &str, port: u16) -> bool {
    let addr = format!("{}:{}", host, port);
    match addr.to_socket_addrs() {
        Ok(mut addrs) => match addrs.next() {
            Some(sock) => {
                TcpStream::connect_timeout(&sock, Duration::from_secs(2)).is_ok()
            }
            None => false,
        },
        Err(_) => false,
    }
}

fn main() {
    for port in [22u16, 80, 443, 8080] {
        println!("port {} open={}", port, check_port("127.0.0.1", port));
    }
}
EOF

cargo run
```

`cargo run` builds a debug binary and runs it. Debug builds compile
fast and include full checks; release builds optimize.

## 2. Ownership and borrowing in practice

Ownership is the core idea: each value has exactly one owner, and
when the owner goes out of scope the value is dropped. Borrowing lets
functions use data without taking ownership.

```rust
fn count_bytes(data: &[u8]) -> usize {
    // Borrows the slice: caller keeps ownership, no copy made.
    data.len()
}

fn main() {
    let payload = vec![1u8, 2, 3, 4];
    let n = count_bytes(&payload); // immutable borrow
    println!("{} bytes, vec still usable: {:?}", n, payload);

    let mut log = String::new();
    append_line(&mut log, "scan started"); // mutable borrow: exclusive
    println!("{}", log);
}

fn append_line(buf: &mut String, line: &str) {
    buf.push_str(line);
    buf.push('\n');
}
```

The rules the compiler enforces: one mutable borrow OR any number of
immutable borrows, never both at once; borrows cannot outlive the
owner. When the compiler rejects code, it is usually pointing at a
real aliasing bug. Prefer `&str` over `String` and `&[u8]` over
`Vec<u8>` in function parameters to avoid needless cloning.

## 3. Error handling with Result and Option

```rust
use std::fs;
use std::io;

fn read_config(path: &str) -> Result<String, io::Error> {
    // The ? operator returns early on Err, propagating the error.
    let data = fs::read_to_string(path)?;
    if data.trim().is_empty() {
        return Err(io::Error::new(io::ErrorKind::InvalidData, "config is empty"));
    }
    Ok(data)
}

fn first_port(ports: &[u16]) -> Option<u16> {
    ports.first().copied() // None when the slice is empty, no panic
}

fn main() {
    match read_config("config.yaml") {
        Ok(data) => println!("loaded {} bytes", data.len()),
        Err(e) => eprintln!("error: {}", e),
    }
    println!("first port: {:?}", first_port(&[]));
}
```

Guidelines: use `?` to propagate errors up to a layer that can decide;
reserve `unwrap()` and `expect()` for tests and for invariants you can
prove (with a message in `expect` that says why it cannot fail); use
`anyhow::Result` in applications for easy context, and custom error
enums in libraries.

## 4. Structs, enums, and pattern matching

```rust
#[derive(Debug, Clone, PartialEq)]
struct Host {
    address: String,
    open_ports: Vec<u16>,
}

#[derive(Debug)]
enum ScanOutcome {
    Open(u16),
    Closed(u16),
    Filtered { port: u16, reason: String },
}

fn describe(outcome: &ScanOutcome) -> String {
    // match must cover every variant: the compiler checks exhaustiveness
    match outcome {
        ScanOutcome::Open(p) => format!("port {} is open", p),
        ScanOutcome::Closed(p) => format!("port {} is closed", p),
        ScanOutcome::Filtered { port, reason } => {
            format!("port {} filtered ({})", port, reason)
        }
    }
}
```

Exhaustive matching means adding a variant forces every `match` to
handle it, which is how Rust makes protocol and state-machine changes
safe.

## 5. Testing, clippy, and formatting

```bash
cat > src/lib.rs <<'EOF'
pub fn is_valid_port(port: u32) -> bool {
    (1..=65535).contains(&port)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn valid_ports() {
        assert!(is_valid_port(80));
        assert!(is_valid_port(65535));
    }

    #[test]
    fn invalid_ports() {
        assert!(!is_valid_port(0));
        assert!(!is_valid_port(70000));
    }
}
EOF

# Format, lint with extra checks, run tests
cargo fmt
cargo clippy --all-targets -- -D warnings
cargo test
```

`cargo clippy -- -D warnings` turns lints into hard errors, which is
the right setting for CI. Fix the lint instead of allowing it unless
you can write down why the lint is wrong for that line.

## 6. Dependencies and auditing

```bash
# Add a dependency at a pinned version
cargo add anyhow@1.0
cargo add tokio@1 --features full

# Inspect what you pulled in
cargo tree | head -30
cargo tree --depth 1

# Audit for known vulnerabilities in the dependency tree
cargo install cargo-audit
cargo audit

# Update dependencies within semver-compatible ranges, then re-audit
cargo update
cargo audit
```

Commit `Cargo.lock` for binaries so every build uses the exact same
dependency versions. Review `cargo tree` output when adding a new
dependency: a small utility crate that pulls in thirty transitive
dependencies is a supply-chain surface you are choosing to accept.

## 7. Release builds and deployment

```bash
# Optimized build
cargo build --release
ls -lh target/release/portcheck

# Smaller binary: strip symbols and optimize for size in Cargo.toml
cat >> Cargo.toml <<'EOF'

[profile.release]
strip = true
opt-level = "z"
lto = true
EOF

cargo build --release
ls -lh target/release/portcheck

# What the binary links against (should be minimal on Linux)
ldd target/release/portcheck | head -5
```

Cross-compilation uses rustup targets:

```bash
rustup target add x86_64-pc-windows-gnu
cargo build --release --target x86_64-pc-windows-gnu
ls target/x86_64-pc-windows-gnu/release/portcheck.exe
```

## Edge cases

- The borrow checker rejects code that "obviously works". Read the
  error fully: it names the conflicting borrows and their spans. The
  usual fix is narrowing a borrow's scope with a block or cloning a
  small value instead of holding a borrow across the mutation.
- `cargo build` fails on a fresh machine with linker errors. Install
  a C linker (`build-essential` on Debian/Ubuntu, Xcode tools on
  macOS); Rust still needs `cc` for the final link step.
- Compile times explode on large projects. Use `cargo build` with
  the default dev profile during iteration, split code into
  workspace crates so unchanged crates are not rebuilt, and consider
  `sccache` for shared CI caches.
- `cargo audit` flags a vulnerability with no fixed version. Options:
  replace the crate, vendor and patch it locally, or document the
  accepted risk with the exposure analysis (is the vulnerable code
  path reachable from your inputs?).
- Async code needs a runtime. Rust has no built-in async runtime;
  `tokio` is the standard choice. Mark the entry with
  `#[tokio::main]` and never block the runtime with `std::thread::sleep`
  inside async functions.
- `unwrap()` panics in production on unexpected input. Audit for
  `unwrap` and `expect` in release paths; each one is a potential
  denial of service if reachable from untrusted data.
- Two crates export the same name after an update. Use explicit
  renaming in `Cargo.toml` (`mycrate = { package = "real-name",
  version = "1.0" }`) instead of forking code.

## Detection and defender view

For engineering skills this section covers detecting misuse and
misconfiguration. A Rust binary built with `strip = true` and
`opt-level = "z"` is small and quiet, which is also what malware
authors want; check provenance (signed artifacts, reproducible build
logs) rather than judging the binary alone. Misconfiguration shows
up as services running as root, `unsafe` blocks used without a
documented safety argument (audit every `unsafe` in review: it is
where the compiler's guarantees are manually suspended), and
dependencies never audited. Detect supply-chain risk by running
`cargo audit` in CI and failing the build on new advisories, and by
reviewing `Cargo.lock` diffs in pull requests the same way you
review code diffs. Panics in logs (`panicked at ...`) reveal
unhandled edge cases; a service that restarts on panic loops is a
denial-of-service pattern worth alerting on.

## Key references

- Rust 1.82 documentation: https://doc.rust-lang.org/
- The Rust Programming Language (the Book): https://doc.rust-lang.org/book/
- cargo book: https://doc.rust-lang.org/cargo/
- clippy lints: https://rust-lang.github.io/rust-clippy/
- rustup documentation: https://rust-lang.github.io/rustup/
- CWE-119 (Improper Restriction of Operations within the Bounds of a
  Memory Buffer): what safe Rust prevents by construction.
- CWE-416 (Use After Free): prevented by the borrow checker.
- CWE-362 (Concurrent Execution using Shared Resource with Improper
  Synchronization): `Send`/`Sync` traits gate cross-thread sharing.
