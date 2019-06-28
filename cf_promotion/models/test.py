# -*- coding: utf-8 -*-
# def main():
#     arr = [
#         {'.com': ['phuc.com', 'hai.com', 'aaa.com']},
#         {'.net': ['test.net', 'hai.net', 'aaa.net']},
#         {'.org': ['hai.org', 'aaa.org', 'test.org']},
#         {'HP1546512465': ['hai.com']},
#     ]
#     arr = sorted(arr, key=lambda key: key)
#     first = arr[0]
#     remain = arr[1:]
#     first_key, first_values = first.items()[0]
#     result = []
#     for item in first_values:
#         def group_by(remain, rsl):
#             if not remain:
#                 return rsl
#             item2 = remain[0]
#             key, values = item2.items()[0]
#             if key[:1] <> '.' or first_key[:1] <> '.':
#                 for i in values:
#                     # if i == item:
#                     if any(i == x for x in rsl):
#                         rsl.append(i)
#                 if len(rsl) > 1:
#                     return group_by(remain[1:], rsl)
#                 return []
#             else:
#                 for i in values:
#                     if i.replace(key, '') == item.replace(first_key, ''):
#                         rsl.append(i)
#                 if len(rsl) > 1:
#                     return group_by(remain[1:], rsl)
#                 return []
#
#         temp = group_by(remain, [item])
#         if len(temp) >= len(arr):
#             result.append(temp)
#     return result
# print 111111, main()


# def combine(a):
#     rsl = a
#     if len(a) > 1:
#         rsl = []
#         for i in range(0, len(a[0])):
#             rsl.append([x[i] for x in a])
#     return rsl
#
# print combine([[1017380], [1017378]])
# a = [[1017380, 1017378], [123, 4556]]
# b = []
# for x in a:
#     b += x
# print b
# import copy
# def test():
#     a = [1,2,3,4]
#     b = list(a)
#     c = []
#     for i in a:
#         c.append(i)
#         if i in c:
#             b.remove(i)
#         print c, b
# test()
import random
def get_random(arr, amount):
    # print arr, amount
    over = random.randint(1, 9)
    if not arr:
        return over
    if (amount + over) in arr:
        return get_random(arr, amount)
    return over
get_random([10, 11, 12, 13, 14, 15, 16], 8)