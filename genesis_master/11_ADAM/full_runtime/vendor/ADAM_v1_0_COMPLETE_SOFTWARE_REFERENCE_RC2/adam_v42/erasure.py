from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from adam_v41.canonical import sha256_bytes


class ErasureError(RuntimeError):
    pass


_EXP = [0] * 512
_LOG = [0] * 256
_x = 1
for _i in range(255):
    _EXP[_i] = _x
    _LOG[_x] = _i
    _x <<= 1
    if _x & 0x100:
        _x ^= 0x11D
for _i in range(255, 512):
    _EXP[_i] = _EXP[_i - 255]


def gf_mul(a: int, b: int) -> int:
    if a == 0 or b == 0:
        return 0
    return _EXP[_LOG[a] + _LOG[b]]


def gf_inv(a: int) -> int:
    if a == 0:
        raise ZeroDivisionError
    return _EXP[255 - _LOG[a]]


def gf_pow(a: int, p: int) -> int:
    if p == 0:
        return 1
    if a == 0:
        return 0
    return _EXP[(_LOG[a] * p) % 255]


def mat_mul(a: list[list[int]], b: list[list[int]]) -> list[list[int]]:
    rows, inner, cols = len(a), len(b), len(b[0])
    if len(a[0]) != inner:
        raise ValueError("matrix dimensions")
    out = [[0] * cols for _ in range(rows)]
    for i in range(rows):
        for k in range(inner):
            if a[i][k] == 0:
                continue
            for j in range(cols):
                out[i][j] ^= gf_mul(a[i][k], b[k][j])
    return out


def mat_inv(matrix: list[list[int]]) -> list[list[int]]:
    n = len(matrix)
    aug = [row[:] + [1 if i == j else 0 for j in range(n)] for i, row in enumerate(matrix)]
    for col in range(n):
        pivot = next((r for r in range(col, n) if aug[r][col] != 0), None)
        if pivot is None:
            raise ErasureError("singular fragment matrix")
        aug[col], aug[pivot] = aug[pivot], aug[col]
        inv = gf_inv(aug[col][col])
        aug[col] = [gf_mul(v, inv) for v in aug[col]]
        for r in range(n):
            if r == col or aug[r][col] == 0:
                continue
            factor = aug[r][col]
            aug[r] = [x ^ gf_mul(factor, y) for x, y in zip(aug[r], aug[col])]
    return [row[n:] for row in aug]


def generator_matrix(k: int, m: int) -> list[list[int]]:
    n = k + m
    if not (1 <= k <= 32 and 0 <= m <= 32 and n <= 255):
        raise ValueError("unsupported Reed-Solomon geometry")
    vand = [[gf_pow(r + 1, c) for c in range(k)] for r in range(n)]
    top_inv = mat_inv([row[:] for row in vand[:k]])
    return mat_mul(vand, top_inv)


@dataclass(frozen=True)
class Fragment:
    index: int
    k: int
    m: int
    original_length: int
    shard_size: int
    object_sha256: str
    payload: bytes


class ReedSolomonCodec:
    """Systematic GF(256) Vandermonde Reed-Solomon development codec."""

    def __init__(self, k: int = 3, m: int = 2):
        self.k, self.m = k, m
        self.matrix = generator_matrix(k, m)

    def encode(self, data: bytes) -> list[Fragment]:
        shard_size = max(1, (len(data) + self.k - 1) // self.k)
        padded = data + b"\0" * (shard_size * self.k - len(data))
        source = [padded[i * shard_size:(i + 1) * shard_size] for i in range(self.k)]
        shards: list[bytes] = []
        for row in self.matrix:
            out = bytearray(shard_size)
            for source_index, coefficient in enumerate(row):
                if coefficient == 0:
                    continue
                src = source[source_index]
                for j, value in enumerate(src):
                    out[j] ^= gf_mul(coefficient, value)
            shards.append(bytes(out))
        digest = sha256_bytes(data)
        return [Fragment(i, self.k, self.m, len(data), shard_size, digest, payload) for i, payload in enumerate(shards)]

    def reconstruct(self, fragments: Iterable[Fragment]) -> bytes:
        unique = {f.index: f for f in fragments}
        if len(unique) < self.k:
            raise ErasureError(f"need at least {self.k} fragments")
        chosen = [unique[i] for i in sorted(unique)[:self.k]]
        first = chosen[0]
        if any((f.k, f.m, f.original_length, f.shard_size, f.object_sha256) !=
               (first.k, first.m, first.original_length, first.shard_size, first.object_sha256) for f in chosen):
            raise ErasureError("fragment metadata mismatch")
        rows = [self.matrix[f.index] for f in chosen]
        inverse = mat_inv([r[:] for r in rows])
        recovered: list[bytes] = []
        for row in inverse:
            out = bytearray(first.shard_size)
            for shard_index, coefficient in enumerate(row):
                if coefficient == 0:
                    continue
                src = chosen[shard_index].payload
                for j, value in enumerate(src):
                    out[j] ^= gf_mul(coefficient, value)
            recovered.append(bytes(out))
        data = b"".join(recovered)[:first.original_length]
        if sha256_bytes(data) != first.object_sha256:
            raise ErasureError("reconstructed digest mismatch")
        return data
