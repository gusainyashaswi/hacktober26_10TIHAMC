def total(values):
    return sum(values)


def average(values):
    if not values:
        return 0
    return total(values) / len(values)

