def main():
    import sys
    input_tokens = sys.stdin.read().split()
    print(input_tokens)
    ptr = 0
    N = int(input_tokens[ptr])
    ptr += 1

    def process_test_cases(n, ptr):
        if n == 0:
            return
        X = int(input_tokens[ptr])
        ptr += 1
        numbers = list(map(int, input_tokens[ptr:ptr+X]))
        ptr += X
        # Calculate sum of squares of non-negative numbers
        non_negatives = filter(lambda y: y >= 0, numbers)
        squares = map(lambda y: y * y, non_negatives)
        total = sum(squares)
        print(total)
        process_test_cases(n - 1, ptr)

    process_test_cases(N, ptr)


test = """
        2
        4
        3 -1 1 14
        5
        9 6 -53 32 16
    """


if __name__ == "__main__":
    main()
