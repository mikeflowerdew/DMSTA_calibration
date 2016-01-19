#!/usr/bin/env python

from math import sqrt

class valueWithError:
    """Value with error which is uncorrelated with other variables.
    For example, when two numbers are added, their errors are added in quadrature.
    The functions are defined so that normal operators (+,-,*,/) can be used
    to combine either two instances of the class, or one instance with a normal
    int or float.
    """
    printstring = '%f +- %f'
    def __init__(self, val=0, err=0):
        if isinstance(val,type(self)):
            self.value = val.value
            self.error = val.error
        else:
            self.value = val
            self.error = err
    def __add__(self, other):
        result = valueWithError(self.value, self.error)
        if isinstance(other,type(self)):
            error2 = self.error*self.error + other.error*other.error
            result.value += other.value
            result.error = sqrt(error2)
        else:
            result.value += other
        return result
    def __radd__(self, other):
        return self.__add__(other)
    def __sub__(self, other):
        result = valueWithError(self.value, self.error)
        if isinstance(other,type(self)):
            error2 = self.error*self.error + other.error*other.error
            result.value -= other.value
            result.error = sqrt(error2)
        else:
            result.value -= other
        return result
    def __rsub__(self, other):
        result = self.__sub__(other)
        result.value = -result.value
        return result
    def __mul__(self, other):
        result = valueWithError(self.value, self.error)
        if isinstance(other,type(self)):
            term1 = self.error*other.value
            term2 = other.error*self.value
            error2 = term1*term1 + term2*term2
            result.value *= other.value
            result.error = sqrt(error2)
        else:
            result.value *= other
            result.error *= other
        return result
    def __rmul__(self, other):
        return self.__mul__(other)
    def __div__(self, other):
        result = valueWithError(self.value, self.error)
        if isinstance(other,type(self)):
            term1 = self.error/other.value
            term2 = other.error*self.value/(other.value*other.value)
            error2 = term1*term1 + term2*term2
            result.value /= other.value
            result.error = sqrt(error2)
        else:
            result.value /= other
            result.error /= other
        return result
    def __rdiv__(self, other):
        result = valueWithError(other.value, other.error) if isinstance(other,type(self)) else valueWithError(other)
        result /= self
        return result
    def __str__(self):
        return valueWithError.printstring%(self.value,self.error)
    def __repr__(self):
        return valueWithError.printstring%(self.value,self.error)
    def __nonzero__(self):
        return 1 if self.value else 0
    def sqrt(self):
        from math import sqrt
        return valueWithError(sqrt(self.value), self.error/(2*self.value))
    def __float__(self):
        return float(self.value)
    def __int__(self):
        return int(self.value)
    def __abs__(self):
        return valueWithError(abs(self.value), self.error)
    def __cmp__(self, other):
        if self.value < float(other):
            return -1
        elif self.value > float(other):
            return 1
        else:
            return 0
    @classmethod
    def binomialDivision(cls, first, second):

        # By calling this function, we certainly want a floating point value
        result = valueWithError(float(first)/second)
        
        # Custom error calculation: delta^2 = [(1-2e)delta_p^2 + e^2 delta_tot^2]/N_tot^2
        err2 = (1.-2.*result.value)*first.error*first.error + result.value*result.value*second.error*second.error
        try:
            result.error = sqrt(err2)/second.value
        except ValueError:
            pass # Or set error to zero?
        return result
            
