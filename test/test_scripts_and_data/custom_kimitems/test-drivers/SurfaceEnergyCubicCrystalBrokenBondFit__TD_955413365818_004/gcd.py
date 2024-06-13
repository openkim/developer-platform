# the function to calculate the GCD
def gcd(num1, num2):

    num1 = abs(num1)
    num2 = abs(num2)

    if num1 * num2 == 0:
        return max(num1, num2)
    if num1 > num2:
        for i in range(1, num2 + 1):
            if num2 % i == 0:
                if num1 % i == 0:
                    result = i
        return result

    elif num2 > num1:
        for i in range(1, num1 + 1):
            if num1 % i == 0:
                if num2 % i == 0:
                    result = i

        return result

    else:
        result = round(num1 * num2 / num1)

        return result
