import sys
import struct


def main():
    data = sys.stdin.buffer.read()  # Read the entire binary input
    pos = 0  # Local pointer into data

    def read_int():
        nonlocal pos, data
        # Unpack a 4-byte integer from the current position
        value = struct.unpack('i', data[pos:pos+4])[0]
        pos += 4
        return value

    def process_numbers(n, acc):
        if n == 0:
            return acc
        num = read_int()
        if num >= 0:
            acc += num * num
        return process_numbers(n - 1, acc)

    def process_cases(n, output):
        if n == 0:
            return output
        # For each test case, first read the count (which we ignore aside from guiding how many numbers to read)
        _ = read_int()
        # Compute the sum of squares for non-negative numbers
        s = process_numbers(_, 0)
        result = str(s)
        new_output = result if output == "" else output + "\n" + result
        return process_cases(n - 1, new_output)

    test_count = read_int()
    final_output = process_cases(test_count, "")
    sys.stdout.write(final_output)


if __name__ == '__main__':
    main()
