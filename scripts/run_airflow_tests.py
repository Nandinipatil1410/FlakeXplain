"""Prioritize Airflow's SDK imports only in the outer pytest interpreter."""
import runpy
import sys
import sysconfig


def prioritize_dependencies():
    paths = sysconfig.get_paths()
    first = [paths['stdlib'], paths['platstdlib'],
             sysconfig.get_config_var('DESTSHARED'), paths['purelib'], paths['platlib']]
    first = list(dict.fromkeys(path for path in first if path))
    sys.path[:] = first + [path for path in sys.path if path not in first]


if __name__ == '__main__':
    prioritize_dependencies()
    runpy.run_module('pytest', run_name='__main__')
