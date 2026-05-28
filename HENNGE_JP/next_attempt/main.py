import sys


def read_iterations():
    return int(sys.stdin.readline().strip())


def process_numbers_recursive(lines, calculated_values, iteration, iterations):
    if iteration > (iterations - 1):
        return

    # First line: declared count X
    declared_count = int(lines.pop(0))

    # Second line: actual integers
    numbers_line = lines.pop(0)
    numbers_slice = numbers_line.split()

    # Check mismatch condition
    if declared_count != len(numbers_slice):
        solution = -1
    else:
        solution = calculate_power_four_recursive(numbers_slice)

    calculated_values[iteration] = solution

    process_numbers_recursive(lines, calculated_values,
                              iteration + 1, iterations)


def calculate_power_four_recursive(number_slice):
    if len(number_slice) == 0:
        return 0

    number = int(number_slice[0])

    if number >= 0:
        return calculate_power_four_recursive(number_slice[1:])

    return (number * number * number * number) + calculate_power_four_recursive(number_slice[1:])


def print_values_recursive(calculated_values):
    if len(calculated_values) < 1:
        return
    print(calculated_values[0])
    print_values_recursive(calculated_values[1:])


def main():
    iterations = read_iterations()
    calculated_values = [0] * iterations

    # Read exactly 2*iterations lines (no EOF assumption)
    lines = [sys.stdin.readline().strip() for _ in range(2 * iterations)]

    process_numbers_recursive(lines, calculated_values, 0, iterations)
    print_values_recursive(calculated_values)


if __name__ == "__main__":
    main()
