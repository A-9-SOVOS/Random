cmake_minimum_required(VERSION 3.16)
project(rrann_cpp_smoke C CXX)

# Expect Rust staticlib built as:
#   cargo build --release -p rrann-core
# producing target/release/librrann_core.a

set(RRANN_RUST_DIR "${CMAKE_SOURCE_DIR}/../rust/rrann-core")
set(RRANN_LIB_DIR "${RRANN_RUST_DIR}/target/release")

add_executable(rrann_c_smoke smoke_test.c)
target_include_directories(rrann_c_smoke PRIVATE ${CMAKE_SOURCE_DIR})
target_link_directories(rrann_c_smoke PRIVATE ${RRANN_LIB_DIR})
target_link_libraries(rrann_c_smoke PRIVATE rrann_core m dl pthread)

# On some platforms the staticlib is librann_core.a from crate name rrann_core
# Cargo emits librrann_core.a for package rrann-core.
