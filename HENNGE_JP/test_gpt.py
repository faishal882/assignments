import sys


def main():
    data = sys.stdin.buffer.read()
    pos = 0

    def read_line():
        nonlocal pos, data
        if pos >= len(data):
            return b""
        nl = data.find(b"\n", pos)
        if nl == -1:
            line = data[pos:]
            pos = len(data)
        else:
            line = data[pos:nl]
            pos = nl + 1
        return line

    def process_line_bytes(line):
        line = line.lstrip(b" ")
        if not line:
            return 0
        sp = line.find(b" ")
        token = line if sp == -1 else line[:sp]
        rest = b"" if sp == -1 else line[sp+1:]
        try:
            v = int(token.decode("ascii"))
        except:
            v = 0
        return (v * v if v >= 0 else 0) + process_line_bytes(rest)

    def process_cases(n, output):
        if n == 0:
            return output
        read_line()  # skip the count line for this test case
        line_numbers = read_line()
        s = process_line_bytes(line_numbers)
        result_bytes = str(s).encode("ascii")
        new_output = result_bytes if output == b"" else output + b"\n" + result_bytes
        return process_cases(n - 1, new_output)

    test_count = int(read_line().decode("ascii"))
    final_output = process_cases(test_count, b"")
    sys.stdout.buffer.write(final_output)


if __name__ == "__main__":
    main()
