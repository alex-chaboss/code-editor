import os
from main import Worker


class Test:
    ''' oneline comment '''
    def __init__(self):
        print('test')

    def test(self):
        print("test")


class TestChild(Test):
    def __init__(self):
        ### TODO: TestChild
        if True:
            print('TestChild')  # right comment
        else:
            print('TestChild')

    def test_child(self, param):
        # header comment
        try:
            param = 0
        except BaseException as e:
            print(param)
