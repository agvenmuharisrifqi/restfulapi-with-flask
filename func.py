from random import randint, shuffle


def make_unique_string(lenght=10):
    character = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890?-+=!@#$%^&*abcdefghijklmnopqrstuvwxyz'
    result = ''
    for i in range(lenght):
        shuffle(list(character))
        result += character[randint(0, len(character))]
    return result


def data_parser(data, params, many=False):
    if many:
        result = [{param: getattr(d, param) for param in params} for d in data]
        return result
    else:
        result = { param: getattr(data, param) for param in params }
        return result

def slugify(string):
    string = string.lower().split(' ')
    return '-'.join(string)