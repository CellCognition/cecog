
class ValueCounter(object):
    def __init__(self, value):
        self.value = value

    def __call__(self, vec):
        res = vec.count(self.value)
        return res

class ConditionalValueCounter(object):
    def __init__(self, value, condval):
        self.value = value
        self.firstval = condval

    def __call__(self, vec, vec_control):
        if self.firstval in vec_control:
            index = vec_control.index(self.firstval)
        else:
            index = len(vec) - 1
        res = vec[:index].count(self.value)
        return res

class ConditionalValueCounterList(object):
    def __init__(self, value, condval_list):
        self.value = value
        self.firstval_list = condval_list

    def __call__(self, vec, vec_control):
        index = len(vec) - 1
        for i in range(len(vec)):
            if vec[i] in self.firstval_list:
                index = i
                break
        res = vec[:index].count(self.value)
        return res

#class ValueCounterIndex(object):
#    def __init__(self, value, index):
#
#