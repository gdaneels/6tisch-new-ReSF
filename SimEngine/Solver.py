from math import ceil, floor
import random
from fractions import gcd
import sys

class CollisionSolver:
    def  __init__(self):
        pass

    # stolen from https://www.math.utah.edu/~carlson/hsp2004/PythonShortCourse.pdf
    # recursive linear diophantine equation solver
    def solveDiophantineEquation(self, a,b,c):
        q, r = divmod(a,b)
        if r == 0:
            return( [0,c/b] )
        else:
            sol = self.solveDiophantineEquation( b, r, c )
            u = sol[0]
            v = sol[1]
            return( [ v, u - q*v ] )

    def getCollisions(self, start_one, interval_one, start_two, interval_two, start_max, end, unique=False):

        # find the linear Diophantine equation coefficients
        a = interval_one
        b = -interval_two
        c = start_two -  start_one

        # 1) check if there are solutions
        gcd_val = gcd(abs(a), abs(b))
        if not (c % gcd_val == 0):
            return []

        # 2) if there are solutions, there are infinitly many
        x_zero, y_zero = self.solveDiophantineEquation(a, b, c)

        # 3) find intersection of start_two with sequence_one, and search for n
        n_start = (((start_max - start_one) / float(interval_one)) - x_zero) / float((float(b) / float(gcd_val)))

        # 4) find intersection of end_two with sequence_two, and search for n
        n_end = (((end - start_one) / float(interval_one)) - x_zero) / float((float(b) / float(gcd_val)))

        if n_end > n_start:
            raise -1

        # 6) find the n values that result in collisions when filled in x and y and are between start_two and end_two
        n_start_int = int(floor(n_start))
        n_end_int = int(ceil(n_end))

        if not unique:
            nrCollisions = n_start_int - n_end_int + 1
            return nrCollisions
        else:
            collisions = []
            # 7) calculate the actual collision ASNs
            quotientB = (b / float(gcd_val))
            collisions = [start_one + interval_one * (x_zero + n * quotientB) for n in range(n_end_int, n_start_int + 1)]
            return collisions

#
# solver = CollisionSolver()
# print solver.getCollisions(1, 25, 2, 5, 25, 5)
# # print solver.getCollisions(6, 60, 5, 24, 72, -22)
# print solver.getCollisions(1,389,4,1,231,3)
# # print solver.solveDiophantineEquation(5, 22, 18)
# print len(solver.getCollisions(5334, 15332, 300, 5334, 15332, 300))

# listX = []
# x = 5334
# y = 15332
# while x < y:
#     listX.append(x)
#     x += 300
# print listX
# print len(listX)

def main():
    solver = CollisionSolver()
    # random.seed(1)
    # count = 0
    # while count < 100000:
    #     print 'TO GO: %d' % (100000 - count)
    #     endOne = int(sys.argv[1])
    #     # startOne = 95333
    #     # intervalOne = 1331
    #     # startTwo = 46942
    #     # intervalTwo = 5936
    #     endTwo = int(sys.argv[2])
    #     startOne = random.randint(1, 100000)
    #     intervalOne = random.randint(1, 10000)
    #     startTwo = random.randint(1, 100000)
    #     intervalTwo = random.randint(1, 10000)
    #     print '(%d, %d, %d, %d, %d, %d)' % (startOne, endOne, intervalOne, startTwo, endTwo, intervalTwo)
    #     # endTwo = 10000000
    #     # 95333, 2000000, 1331, 46942, 10000000, 5936
    #     # 95333, 2000000, 1331, 46942, 10000000, 5936
    #     # print 'FIRST LIST:'
    #     firstList = []
    #     startCount = startOne
    #     while startCount <= endOne:
    #         firstList.append(startCount)
    #         startCount += intervalOne
    #     # print sorted(firstList)
    #
    #     # print 'SECOND LIST:'
    #     secondList = []
    #     startCountTwo = startTwo
    #     while startCountTwo <= endTwo:
    #         secondList.append(startCountTwo)
    #         startCountTwo += intervalTwo
    #
    #     bruteForce = sorted(list(set(firstList).intersection(secondList)))
    #     solver = solverCollisions.getCollisions(startOne, endOne, intervalOne, startTwo, endTwo, intervalTwo)
    #     # print solver
    #     print '(%d, %d, %d, %d, %d, %d)' % (startOne, endOne, intervalOne, startTwo, endTwo, intervalTwo)
    #
    #     if sorted(solver) != sorted(bruteForce):
    #         print 'Brute force collision list: %s' % sorted(bruteForce)
    #         print 'Solver collision list: %s' % sorted(solver)
    #         print '(%d, %d, %d, %d, %d, %d)' % (startOne, endOne, intervalOne, startTwo, endTwo, intervalTwo)
    #         raise -1
    #     count += 1

    # print solver.getCollisions(6, 60, 5, 24, 72, -22)
    # print solver.getCollisions(1, 25, 2, 5, 25, 5)

    count = 0
    while count < 100000:
        start_one = random.randint(1, 100000)
        start_two = random.randint(1, 100000)
        interval_one = random.randint(1, 1000)
        interval_two = random.randint(1, 1000)
        end = 20000000

        #### SOLVER ####

        l1 = solver.getCollisions(start_one, interval_one, start_two, interval_two, end)

        #### BRUTE FORCE ####
        l2_1 = set()
        start_one_count = start_one
        while start_one_count <= end:
            l2_1.add(start_one_count)
            start_one_count += interval_one

        l2_2 = set()
        start_two_count = start_two
        while start_two_count <= end:
            l2_2.add(start_two_count)
            start_two_count += interval_two

        l2 = sorted(list(set(l2_1).intersection(l2_2)))

        print 'len(bf) %d == len(solver) %d' % (len(l1), len(l2))
        # print 'Brute force collision list: %s' % sorted(l2)
        # print 'Solver collision list: %s' % sorted(l1)
        # print '(%d, %d, %d, %d, %d)' % (start_one, interval_one, start_two, interval_two, end)

        if sorted(l1) != l2:
            raise -1

        count += 1

    # print solver.getCollisions(113635, 151500, 5900, 114235, 119535, 5300)
    # print solver.getCollisions(5334, 15332, 300, 5334, 15332, 300)
    # print solver.getCollisions(122121,151500,7100, 105820,151500,7200)
if __name__=="__main__":
    main()