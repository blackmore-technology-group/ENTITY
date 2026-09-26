#include <errno.h>
#include <fcntl.h>
#include <openssl/sha.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define MAX_LINE 1048576
#define FRAME_MAGIC "A43F"
#define FRAME_HEADER_BYTES (4 + 4 + 8 + SHA256_DIGEST_LENGTH + SHA256_DIGEST_LENGTH)

static void hex_encode(const unsigned char *input, size_t len, char *output) {
    static const char table[] = "0123456789abcdef";
    for (size_t i = 0; i < len; ++i) {
        output[i * 2] = table[input[i] >> 4];
        output[i * 2 + 1] = table[input[i] & 0x0f];
    }
    output[len * 2] = '\0';
}

static int hex_value(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}

static int hex_decode(const char *hex, unsigned char **out, size_t *out_len) {
    size_t len = strlen(hex);
    if (len % 2 != 0) return 0;
    unsigned char *buffer = malloc(len / 2 + 1);
    if (!buffer) return 0;
    for (size_t i = 0; i < len; i += 2) {
        int high = hex_value(hex[i]);
        int low = hex_value(hex[i + 1]);
        if (high < 0 || low < 0) { free(buffer); return 0; }
        buffer[i / 2] = (unsigned char)((high << 4) | low);
    }
    *out = buffer;
    *out_len = len / 2;
    return 1;
}

static void u32_be(uint32_t value, unsigned char out[4]) {
    out[0] = (unsigned char)(value >> 24);
    out[1] = (unsigned char)(value >> 16);
    out[2] = (unsigned char)(value >> 8);
    out[3] = (unsigned char)value;
}

static uint32_t read_u32_be(const unsigned char in[4]) {
    return ((uint32_t)in[0] << 24) | ((uint32_t)in[1] << 16) |
           ((uint32_t)in[2] << 8) | (uint32_t)in[3];
}

static void u64_be(uint64_t value, unsigned char out[8]) {
    for (int i = 0; i < 8; ++i) out[7 - i] = (unsigned char)((value >> (i * 8)) & 0xff);
}

static uint64_t read_u64_be(const unsigned char in[8]) {
    uint64_t value = 0;
    for (int i = 0; i < 8; ++i) value = (value << 8) | in[i];
    return value;
}

static void frame_root(uint64_t sequence, const unsigned char previous[SHA256_DIGEST_LENGTH],
                       const unsigned char *payload, size_t payload_len,
                       unsigned char result[SHA256_DIGEST_LENGTH]) {
    unsigned char seqbuf[8];
    u64_be(sequence, seqbuf);
    SHA256_CTX ctx;
    SHA256_Init(&ctx);
    SHA256_Update(&ctx, "ADAM43:NATIVE_FRAME\0", 20);
    SHA256_Update(&ctx, seqbuf, sizeof(seqbuf));
    SHA256_Update(&ctx, previous, SHA256_DIGEST_LENGTH);
    SHA256_Update(&ctx, payload, payload_len);
    SHA256_Final(result, &ctx);
}

static int sync_file(FILE *file) {
    if (fflush(file) != 0) return 0;
    int fd = fileno(file);
    return fd >= 0 && fsync(fd) == 0;
}

static int append_frame(FILE *log, uint64_t sequence,
                        const unsigned char root[SHA256_DIGEST_LENGTH],
                        const unsigned char *payload, size_t payload_len,
                        unsigned char new_root[SHA256_DIGEST_LENGTH]) {
    if (payload_len > UINT32_MAX) return 0;
    unsigned char lenbuf[4], seqbuf[8];
    u32_be((uint32_t)payload_len, lenbuf);
    u64_be(sequence, seqbuf);
    frame_root(sequence, root, payload, payload_len, new_root);
    if (fseek(log, 0, SEEK_END) != 0) return 0;
    if (fwrite(FRAME_MAGIC, 1, 4, log) != 4) return 0;
    if (fwrite(lenbuf, 1, sizeof(lenbuf), log) != sizeof(lenbuf)) return 0;
    if (fwrite(seqbuf, 1, sizeof(seqbuf), log) != sizeof(seqbuf)) return 0;
    if (fwrite(root, 1, SHA256_DIGEST_LENGTH, log) != SHA256_DIGEST_LENGTH) return 0;
    if (fwrite(new_root, 1, SHA256_DIGEST_LENGTH, log) != SHA256_DIGEST_LENGTH) return 0;
    if (payload_len && fwrite(payload, 1, payload_len, log) != payload_len) return 0;
    return sync_file(log);
}

static int replay(FILE *log, uint64_t *sequence, unsigned char root[SHA256_DIGEST_LENGTH]) {
    if (fseek(log, 0, SEEK_SET) != 0) return 0;
    *sequence = 0;
    memset(root, 0, SHA256_DIGEST_LENGTH);
    for (;;) {
        unsigned char header[FRAME_HEADER_BYTES];
        size_t got = fread(header, 1, sizeof(header), log);
        if (got == 0) {
            if (feof(log)) { clearerr(log); return 1; }
            return 0;
        }
        if (got != sizeof(header)) return 0;
        if (memcmp(header, FRAME_MAGIC, 4) != 0) return 0;
        uint32_t payload_len = read_u32_be(header + 4);
        uint64_t frame_sequence = read_u64_be(header + 8);
        const unsigned char *previous = header + 16;
        const unsigned char *recorded_root = header + 16 + SHA256_DIGEST_LENGTH;
        if (frame_sequence != *sequence + 1) return 0;
        if (memcmp(previous, root, SHA256_DIGEST_LENGTH) != 0) return 0;
        unsigned char *payload = malloc(payload_len ? payload_len : 1);
        if (!payload) return 0;
        if (payload_len && fread(payload, 1, payload_len, log) != payload_len) {
            free(payload);
            return 0;
        }
        unsigned char computed[SHA256_DIGEST_LENGTH];
        frame_root(frame_sequence, root, payload, payload_len, computed);
        free(payload);
        if (memcmp(computed, recorded_root, SHA256_DIGEST_LENGTH) != 0) return 0;
        memcpy(root, computed, SHA256_DIGEST_LENGTH);
        *sequence = frame_sequence;
    }
}

static int parse_append(const char *input, const unsigned char current_root[SHA256_DIGEST_LENGTH],
                        unsigned char **payload, size_t *payload_len) {
    const char *space = strchr(input, ' ');
    if (!space) return hex_decode(input, payload, payload_len);
    size_t expected_len = (size_t)(space - input);
    if (expected_len != SHA256_DIGEST_LENGTH * 2) return 0;
    char expected_hex[SHA256_DIGEST_LENGTH * 2 + 1];
    memcpy(expected_hex, input, expected_len);
    expected_hex[expected_len] = '\0';
    unsigned char *expected = NULL;
    size_t expected_bytes = 0;
    if (!hex_decode(expected_hex, &expected, &expected_bytes) || expected_bytes != SHA256_DIGEST_LENGTH) {
        free(expected);
        return 0;
    }
    int matches = memcmp(expected, current_root, SHA256_DIGEST_LENGTH) == 0;
    free(expected);
    if (!matches) return -1;
    return hex_decode(space + 1, payload, payload_len);
}

int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s LOG_PATH\n", argv[0]);
        return 64;
    }
    FILE *log = fopen(argv[1], "a+b");
    if (!log) { perror("fopen"); return 1; }
    unsigned char root[SHA256_DIGEST_LENGTH];
    uint64_t sequence = 0;
    if (!replay(log, &sequence, root)) {
        fprintf(stderr, "integrity failure while replaying %s\n", argv[1]);
        fclose(log);
        return 65;
    }
    char *line = malloc(MAX_LINE);
    if (!line) { fclose(log); return 1; }
    printf("READY ADAM43-NATIVE-FRAMING-REFERENCE %llu\n", (unsigned long long)sequence);
    fflush(stdout);
    while (fgets(line, MAX_LINE, stdin)) {
        size_t n = strlen(line);
        while (n && (line[n - 1] == '\n' || line[n - 1] == '\r')) line[--n] = '\0';
        if (strcmp(line, "QUIT") == 0) {
            printf("OK BYE\n"); fflush(stdout); break;
        }
        if (strcmp(line, "ROOT") == 0 || strcmp(line, "VERIFY") == 0) {
            if (strcmp(line, "VERIFY") == 0 && !replay(log, &sequence, root)) {
                printf("ERR INTEGRITY\n"); fflush(stdout); continue;
            }
            char root_hex[SHA256_DIGEST_LENGTH * 2 + 1];
            hex_encode(root, sizeof(root), root_hex);
            printf("OK %llu %s\n", (unsigned long long)sequence, root_hex); fflush(stdout); continue;
        }
        if (strncmp(line, "HASH ", 5) == 0) {
            unsigned char *payload = NULL; size_t payload_len = 0; unsigned char hash[SHA256_DIGEST_LENGTH];
            if (!hex_decode(line + 5, &payload, &payload_len)) { printf("ERR BAD_HEX\n"); fflush(stdout); continue; }
            SHA256(payload, payload_len, hash); free(payload);
            char hash_hex[SHA256_DIGEST_LENGTH * 2 + 1]; hex_encode(hash, sizeof(hash), hash_hex);
            printf("OK %s\n", hash_hex); fflush(stdout); continue;
        }
        if (strncmp(line, "APPEND ", 7) == 0) {
            unsigned char *payload = NULL; size_t payload_len = 0; unsigned char next[SHA256_DIGEST_LENGTH];
            int parsed = parse_append(line + 7, root, &payload, &payload_len);
            if (parsed == -1) { printf("ERR STALE_ROOT\n"); fflush(stdout); continue; }
            if (!parsed) { printf("ERR BAD_APPEND\n"); fflush(stdout); continue; }
            if (!append_frame(log, sequence + 1, root, payload, payload_len, next)) {
                free(payload); printf("ERR WRITE_FAILED\n"); fflush(stdout); continue;
            }
            free(payload); sequence += 1; memcpy(root, next, sizeof(root));
            char root_hex[SHA256_DIGEST_LENGTH * 2 + 1]; hex_encode(root, sizeof(root), root_hex);
            printf("OK %llu %s\n", (unsigned long long)sequence, root_hex); fflush(stdout); continue;
        }
        printf("ERR UNKNOWN_COMMAND\n"); fflush(stdout);
    }
    free(line);
    fclose(log);
    return 0;
}
