# This file is part of the pyMor project (http://www.pymor.org).
# Copyright Holders: Felix Albrecht, Rene Milk, Stephan Rave
# License: BSD 2-Clause License (http://opensource.org/licenses/BSD-2-Clause)

from __future__ import absolute_import, division, print_function

from numbers import Number
from itertools import izip

import numpy as np

from pymor.tools import float_cmp_all


class ParameterType(dict):

    __keys = None

    def __init__(self, *args, **kwargs):
        # calling dict.__init__ breaks multiple inheritance but is faster than
        # the super() call
        dict.__init__(self, *args, **kwargs)
        assert all(isinstance(v, tuple) for v in self.itervalues())
        assert all(all(isinstance(v, Number) for v in t) for t in self.itervalues())

    def clear(self):
        dict.clear(self)
        self.__keys = None

    def copy(self):
        c = ParameterType(self)
        if self.__keys is not None:
            c.__keys = list(self.__keys)
        return c

    def __setitem__(self, key, value):
        assert isinstance(value, tuple)
        assert all(isinstance(v, Number) for v in value)
        if key not in self:
            self.__keys = None
        dict.__setitem__(self, key, value)

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        self.__keys.remove(key)

    def __iter__(self):
        if self.__keys is None:
            self.__keys = sorted(dict.keys(self))
        return iter(self.__keys)

    def keys(self):
        if self.__keys is None:
            self.__keys = sorted(dict.keys(self))
        return list(self.__keys)

    def iterkeys(self):
        return iter(self)

    def fromkeys(self, S, v=None):
        raise NotImplementedError

    def pop(self, k, d=None):
        raise NotImplementedError

    def popitem(self):
        raise NotImplementedError

    def update(self, *args, **kwargs):
        raise NotImplementedError

    def __str__(self):
        if self.__keys is None:
            self.__keys = sorted(self.keys())
        return '{' +  ', '.join('{}: {}'.format(k, self[k]) for k in self.__keys) + '}'


class Parameter(dict):
    '''Class representing a parameter.

    A parameter is simply a dict of numpy arrays. We overwrite copy() to
    ensure that not only the dict but also the arrays are copied. Moreover
    an allclose() method is provided to compare parameters for equality.
    Finally __str__() ensures an alphanumerical ordering of the keys. This
    is not true, however, for keys() or iteritems().
    '''

    __keys = None

    def __init__(self, v):
        # calling dict.__init__ breaks multiple inheritance but is faster than
        # the super() call
        dict.__init__(self, v)
        assert all(isinstance(v, np.ndarray) for v in self.itervalues())

    def allclose(self, mu):
        assert isinstance(mu, Parameter)
        if set(self.keys()) != set(mu.keys()):
            return False
        if not all(float_cmp_all(v, mu[k]) for k, v in self.iteritems()):
            return False
        else:
            return True

    def clear(self):
        dict.clear(self)
        self.__keys = None

    def copy(self):
        c = Parameter({k: v.copy() for k, v in self.iteritems()})
        if self.__keys is not None:
            c.__keys = list(self.__keys)
        return c

    def __setitem__(self, key, value):
        if key not in self:
            self.__keys = None
        if not isinstance(value, np.ndarray):
            value = np.array(value)
        dict.__setitem__(self, key, value)

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        self.__keys.remove(key)

    def fromkeys(self, S, v=None):
        raise NotImplementedError

    def pop(self, k, d=None):
        raise NotImplementedError

    def popitem(self):
        raise NotImplementedError

    def update(self, *args, **kwargs):
        dict.update(self, *args, **kwargs)
        self.__keys = None

    @property
    def parameter_type(self):
        return ParameterType({k: v.shape for k in self._keys})

    def __str__(self):
        if self.__keys is None:
            self.__keys = sorted(self.keys())
        s = '{'
        for k in self.__keys:
            v = self[k]
            if v.ndim > 1:
                v = v.ravel()
            if s == '{':
                s += '{}: {}'.format(k, v)
            else:
                s += ', {}: {}'.format(k, v)
        s += '}'
        return s

def parse_parameter(mu, parameter_type=None):
    '''Takes a parameter specification `mu` and makes it a `Parameter` according to `parameter_type`.

    Depending on the `parameter_type`, `mu` can be given as a `Parameter`, dict, tuple,
    list, array or scalar.

    Parameters
    ----------
    mu
        The parameter specification.
    parameter_type
        The parameter type w.r.t. which `mu` is to be interpreted.

    Returns
    -------
    The corresponding `Parameter`.

    Raises
    ------
    ValueError
        Is raised if `mu` cannot be interpreted as a `Paramter` of `parameter_type`.
    '''
    if not parameter_type:
        assert mu is None
        return None

    if isinstance(mu, Parameter):
        assert mu.parameter_type == parameter_type
        return mu

    if not isinstance(mu, dict):
        if isinstance(mu, (tuple, list)):
            if len(parameter_type) == 1 and len(mu) != 1:
                mu = (mu,)
        else:
            mu = (mu,)
        if len(mu) != len(parameter_type):
            raise ValueError('Parameter length does not match.')
        mu = dict(izip(parameter_type, mu))
    elif set(mu.keys()) != set(parameter_type.keys()):
        raise ValueError('Components do not match')
    for k, v in mu.iteritems():
        if not isinstance(v, np.ndarray):
            mu[k] = np.array(v)
    if not all(mu[k].shape == parameter_type[k] for k in mu):
        raise ValueError('Component dimensions do not match')
    return Parameter(mu)


def parse_parameter_type(parameter_type):
    '''Takes a parameter type specification and makes it a `ParameterType`.

    A `ParameterType` is an ordered dict whose values are tuples of natural numbers
    defining the shape of the corresponding parameter component.

    Parameters
    ----------
    parameter_type
        The parameter type specification. Can be a dict or OrderedDict, in which case
        scalar values are made tuples of length 1, or a `ParameterSpace` whose
        parameter_type is taken.

    Returns
    -------
    The corresponding parameter type.
    '''

    from pymor.parameters.interfaces import ParameterSpaceInterface
    if parameter_type is None:
        return ParameterType()
    if isinstance(parameter_type, ParameterSpaceInterface):
        return ParameterType(parameter_type.parameter_type)
    parameter_type = dict(parameter_type)
    for k, v in parameter_type.iteritems():
        if not isinstance(v, tuple):
            assert isinstance(v, Number)
            if v == 0 or v == 1:
                parameter_type[k] = tuple()
            else:
                parameter_type[k] = tuple((v,))
    return ParameterType(parameter_type)


class Parametric(object):
    '''Mixin class for objects whose evaluations depend on a parameter.

    Parameters
    ----------
    parameter_type
        The parameter type of the parameters the object takes.
    global_parameter_type
        The parameter type without any renamings by the user.
    local_parameter_type
        The parameter type of the parameter components which are introduced
        by the object itself and are not inherited by other objects it
        depends on.
    parameter_space
        If not `None` the `ParameterSpace` the parameter is expected to lie in.
    parametric:
        Is True if the object has a nontrivial parameter type.
    '''

    parameter_type = None
    parameter_local_type = None
    parameter_global_names = None
    parameter_provided = None
    _parameter_space = None

    @property
    def parameter_space(self):
        return self._parameter_space

    @parameter_space.setter
    def parameter_space(self, ps):
        assert ps is None or self.parameter_type == ps.parameter_type
        self._parameter_space = ps

    @property
    def parametric(self):
        return self.parameter_type is not None

    def parse_parameter(self, mu):
        if mu is None:
            assert self.parameter_type is None
            return None
        if mu.__class__ is not Parameter:
            mu = parse_parameter(mu, self.parameter_type)
        assert self.parameter_type is None or all(getattr(mu.get(k, None), 'shape', None) == v for k, v in self.parameter_type.iteritems())
        return mu

    def local_parameter(self, mu):
        assert mu.__class__ is Parameter
        return None if self.parameter_local_type is None else {k: mu[v] for k, v in self.parameter_global_names.iteritems()}

    def strip_parameter(self, mu):
        if not isinstance(mu, Parameter):
            mu_ = parse_parameter(mu, self.parameter_type)
        assert self.parameter_type is None or all(getattr(mu.get(k, None), 'shape', None) == v for k, v in self.parameter_type.iteritems())
        return None if self.parameter_type is None else Parameter({k: mu[k] for k in self.parameter_type})

    def build_parameter_type(self, local_type=None, global_names=None, local_global=False, inherits=None, provides=None):
        '''Builds the parameter type of the object. To be called by __init__.

        Parameters
        ----------
        local_type
            Parameter type for the parameter components introduced by the object itself.
        global_names
            A dict of the form `{'localname': 'globalname', ...}` defining a name mapping specifying global
            parameter names for the keys of local_type
        local_global
            If True, use the identity mapping `{'localname': 'localname', ...}` as global_names, i.e. each local
            parameter name should be treated as a global parameter name.
        inherits
            List where each entry is a Parametric object whose parameter type shall become part of the
            built parameter type.
        provides
            Dict where the keys specify parameter names and the values are corresponding shapes. The
            parameters listed in `provides` will not become part of the parameter type. Instead they
            have to be provided by the class implementor.

        Returns
        -------
        The parameter type of the object.
        '''
        assert not local_global or global_names is None
        local_type = parse_parameter_type(local_type)
        if local_global and local_type is not None:
            global_names = {k: k for k in local_type}
        if local_type and not (global_names and all(k in global_names for k in local_type)):
            if not global_names:
                raise ValueError('Must specify a global name for each key of local_type')
            else:
                for k in local_type:
                    if not k in global_names:
                        raise ValueError('Must specify a global name for {}'.format(k))

        parameter_maps = {}

        global_type = local_type.copy()

        provides = parse_parameter_type(provides) or {}
        provides = provides or {}

        if inherits:
            for op in (o for o in inherits if o.parametric):
                for name, shape in op.parameter_type.iteritems():
                    if name in global_type and global_type[name] != shape:
                        raise ValueError('Component dimensions of global name {} do not match ({} and {})'.format(name,
                            global_type[name], shape))
                    if name in provides:
                        if provides[global_name] != shape:
                            raise ValueError('Component dimensions of provided name {} do not match'.format(name))
                    else:
                        global_type[name] = shape

        self.parameter_type = global_type or None
        self.parameter_local_type = local_type or None
        self.parameter_provided = provides or None
        self.parameter_global_names = global_names

    def parameter_info(self):
        '''Return an info string about the object's parameter type and how it is built.'''

        if not self.parametric:
            return 'The parameter_type is None\n'
        else:
            return 'The parameter_type is: {}\n\n'.format(self.parameter_type)
